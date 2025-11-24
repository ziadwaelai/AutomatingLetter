"""
User Management Service
Handles user authentication, client lookup, and access control based on master sheet.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from functools import lru_cache
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from ..config import get_config
from ..utils import (
    handle_storage_errors,
    measure_performance,
    ErrorContext,
    StorageServiceError
)
from ..utils.connection_pool import ConnectionPool

logger = logging.getLogger(__name__)

# Master sheet ID (hardcoded as per requirements)
MASTER_SHEET_ID = "11eCtNuW4cl03TX0G20alx3_6B5DI7IbpQPnPDeRGKlI"

# Worksheet names
EMAIL_MAPPINGS_WORKSHEET = "EmailMappings"
CLIENTS_WORKSHEET = "ClientRegistry"  # Default worksheet name for clients

# Cache TTL in seconds (1 minute)
CACHE_TTL = 60


@dataclass
@dataclass
class UserInfo:
    """User information from client sheet."""
    email: str
    full_name: str
    role: str
    status: str
    created_at: str
    password: str = ""  # Hashed password

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at
        }


@dataclass
class ClientInfo:
    """Client information from master sheet."""
    client_id: str
    display_name: str
    primary_domain: str
    extra_domains: List[str]
    sheet_id: str
    google_drive_id: str
    sheet_url: str
    admin_email: str
    created_at: str
    letter_template: str
    letter_type: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "client_id": self.client_id,
            "display_name": self.display_name,
            "primary_domain": self.primary_domain,
            "extra_domains": self.extra_domains,
            "sheet_id": self.sheet_id,
            "google_drive_id": self.google_drive_id,
            "sheet_url": self.sheet_url,
            "admin_email": self.admin_email,
            "created_at": self.created_at,
            "letter_template": self.letter_template,
            "letter_type": self.letter_type
        }


class UserManagementService:
    """
    Service for managing user authentication and client lookup.
    Validates user emails against master sheet and returns client configuration.
    """

    def __init__(self, pool_size: int = 5):
        """
        Initialize User Management service with connection pooling.

        Args:
            pool_size: Maximum number of concurrent connections (default: 5)
        """
        self.config = get_config()
        self._validate_configuration()

        # Create connection pool
        self._pool = ConnectionPool(
            connection_factory=self._create_sheets_client,
            cleanup_func=None,  # gspread clients don't need explicit cleanup
            pool_size=pool_size,
            connection_timeout=30,
            max_connection_lifetime=3600,  # 1 hour
            max_connection_idle_time=300  # 5 minutes
        )

        # Master sheet configuration
        self.master_sheet_id = MASTER_SHEET_ID

        # Cache for client data
        self._client_cache: Dict[str, tuple[ClientInfo, float]] = {}
        self._master_data_cache: Optional[tuple[List[List[str]], float]] = None
        self._email_mappings_cache: Optional[tuple[List[List[str]], float]] = None

    def _validate_configuration(self):
        """Validate configuration."""
        import os
        if not os.path.exists(self.config.storage.service_account_file):
            raise StorageServiceError(
                f"Service account file not found: {self.config.storage.service_account_file}"
            )

    def _create_sheets_client(self):
        """Create a new Google Sheets client."""
        try:
            scopes = [
                'https://www.googleapis.com/auth/drive.file',
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            creds = ServiceAccountCredentials.from_json_keyfile_name(
                self.config.storage.service_account_file,
                scopes
            )
            client = gspread.authorize(creds)
            logger.debug("User Management Google Sheets client created from pool factory")
            return client

        except Exception as e:
            logger.error(f"Failed to create Google Sheets client: {e}")
            raise StorageServiceError(f"Failed to connect to Google Sheets: {e}")

    @property
    def client(self):
        """Get a Google Sheets client from the pool."""
        try:
            return self._pool.acquire()
        except Exception as e:
            logger.error(f"Failed to acquire client from pool: {e}")
            raise

    def _release_client(self, client):
        """Release a client back to the pool."""
        self._pool.release(client)

    def get_client_context(self):
        """
        Get a context manager for safe client acquisition and release.

        Usage:
            with service.get_client_context() as client:
                spreadsheet = client.open_by_key(sheet_id)
                # Client automatically released when exiting context
        """
        from ..utils.connection_pool import PooledConnectionManager
        return PooledConnectionManager(self._pool)

    def _get_master_sheet_data(self, force_refresh: bool = False) -> List[List[str]]:
        """
        Get master sheet data with caching.

        Args:
            force_refresh: Force refresh of cached data

        Returns:
            List of rows from master sheet
        """
        current_time = time.time()

        # Check cache
        if not force_refresh and self._master_data_cache:
            cached_data, cache_time = self._master_data_cache
            if current_time - cache_time < CACHE_TTL:
                logger.debug("Using cached master sheet data")
                return cached_data

        # Fetch fresh data
        try:
            with self.get_client_context() as client:
                spreadsheet = client.open_by_key(MASTER_SHEET_ID)
                worksheet = spreadsheet.get_worksheet(0)  # First worksheet
                all_values = worksheet.get_all_values()

                # Cache the data
                self._master_data_cache = (all_values, current_time)

                logger.debug(f"Fetched master sheet data: {len(all_values)} rows")
                return all_values

        except Exception as e:
            logger.error(f"Failed to fetch master sheet data: {e}")
            raise StorageServiceError(f"Cannot access master sheet: {e}")

    def _extract_domain_from_email(self, email: str) -> str:
        """
        Extract domain from email address.

        Args:
            email: Email address

        Returns:
            Domain part of email
        """
        if '@' not in email:
            raise ValueError("Invalid email format")
        return email.split('@')[1].lower()

    def _parse_extra_domains(self, extra_domains_str: str) -> List[str]:
        """
        Parse extra domains string into list.

        Args:
            extra_domains_str: Comma-separated or semicolon-separated domains

        Returns:
            List of domains
        """
        if not extra_domains_str or not extra_domains_str.strip():
            return []

        # Support both comma and semicolon separators
        domains = []
        for separator in [',', ';']:
            if separator in extra_domains_str:
                domains = [d.strip().lower() for d in extra_domains_str.split(separator) if d.strip()]
                break

        # If no separator found, treat as single domain
        if not domains and extra_domains_str.strip():
            domains = [extra_domains_str.strip().lower()]

        return domains

    @handle_storage_errors
    @measure_performance
    def get_client_by_email(self, email: str) -> Optional[ClientInfo]:
        """
        Get client information by user email using two-tier lookup.

        Priority:
        1. Check EmailMappings worksheet first (for explicit email → sheet mappings)
        2. Fall back to domain matching (for organizational domains)

        Args:
            email: User email address

        Returns:
            ClientInfo if found, None otherwise
        """
        with ErrorContext("get_client_by_email", {"email": email}):
            try:
                # Validate email format
                email = email.strip().lower()
                if not email or '@' not in email:
                    raise ValueError("Invalid email format")

                # Check cache first
                current_time = time.time()
                if email in self._client_cache:
                    cached_client, cache_time = self._client_cache[email]
                    if current_time - cache_time < CACHE_TTL:
                        logger.debug(f"Using cached client info for email: {email}")
                        return cached_client

                # ===================================================
                # TIER 1: Check EmailMappings worksheet first
                # ===================================================
                client_info = self._get_client_from_email_mappings(email)
                if client_info:
                    logger.info(f"Client found via EmailMappings for {email}: {client_info.display_name}")
                    # Cache the result
                    self._client_cache[email] = (client_info, current_time)
                    return client_info

                # ===================================================
                # TIER 2: Fall back to domain matching
                # ===================================================
                email_domain = self._extract_domain_from_email(email)
                client_info = self._get_client_by_domain(email_domain)

                if client_info:
                    logger.info(f"Client found via domain matching for {email}: {client_info.display_name}")
                    # Cache the result
                    self._client_cache[email] = (client_info, current_time)
                    return client_info

                # No client found
                logger.warning(f"No client found for email: {email} (domain: {email_domain})")
                return None

            except Exception as e:
                logger.error(f"Error getting client by email {email}: {e}")
                raise

    def _get_client_from_email_mappings(self, email: str) -> Optional[ClientInfo]:
        """
        Check if email exists in EmailMappings worksheet.
        This allows multiple users with public email domains (gmail, yahoo, etc.)
        to be explicitly mapped to specific client sheets.

        Args:
            email: User email address (already normalized)

        Returns:
            ClientInfo if email is mapped, None otherwise
        """
        try:
            # Check cache first
            current_time = time.time()
            if self._email_mappings_cache:
                cached_data, cache_time = self._email_mappings_cache
                if current_time - cache_time < CACHE_TTL:
                    logger.debug("Using cached EmailMappings data")
                    return self._search_email_in_mappings(email, cached_data)

            # Fetch fresh data
            with self.get_client_context() as client:
                try:
                    master_sheet = client.open_by_key(self.master_sheet_id)
                    email_mappings_ws = master_sheet.worksheet(EMAIL_MAPPINGS_WORKSHEET)
                    all_mappings = email_mappings_ws.get_all_values()

                    # Cache the mappings data
                    self._email_mappings_cache = (all_mappings, current_time)
                    logger.debug(f"Fetched EmailMappings data: {len(all_mappings)} rows")

                    return self._search_email_in_mappings(email, all_mappings)

                except gspread.exceptions.WorksheetNotFound:
                    logger.debug(f"EmailMappings worksheet not found in master sheet")
                    return None

        except Exception as e:
            logger.warning(f"Error checking email mappings for {email}: {e}")
            return None

    def _search_email_in_mappings(self, email: str, mappings_data: List[List[str]]) -> Optional[ClientInfo]:
        """
        Search for email in mappings data and create ClientInfo if found.

        Args:
            email: User email address (normalized)
            mappings_data: EmailMappings worksheet data

        Returns:
            ClientInfo if found, None otherwise
        """
        if not mappings_data or len(mappings_data) < 2:
            return None  # No data or only headers

        try:
            # Parse headers (first row)
            headers = [h.strip().lower() for h in mappings_data[0]]

            # Find required column indices
            try:
                email_idx = headers.index("email")
                sheet_id_idx = headers.index("sheetid")
            except ValueError as e:
                logger.warning(f"EmailMappings sheet missing required column: {e}")
                return None

            # Optional columns with defaults
            drive_id_idx = headers.index("googledriveid") if "googledriveid" in headers else None
            display_name_idx = headers.index("displayname") if "displayname" in headers else None
            letter_template_idx = headers.index("lettertemplate") if "lettertemplate" in headers else None
            letter_type_idx = headers.index("lettertype") if "lettertype" in headers else None

            # Search for matching email
            for row in mappings_data[1:]:  # Skip header row
                if len(row) <= email_idx:
                    continue

                row_email = row[email_idx].strip().lower()

                if row_email == email:
                    # Found! Extract data with safe defaults
                    sheet_id = row[sheet_id_idx].strip() if sheet_id_idx < len(row) else ""

                    if not sheet_id:
                        logger.warning(f"Email mapping for {email} has no sheet_id")
                        continue

                    # Create ClientInfo from mapping
                    client_info = ClientInfo(
                        client_id=f"EMAIL-MAP-{email.split('@')[0]}",  # Generate unique ID
                        display_name=row[display_name_idx].strip() if display_name_idx and display_name_idx < len(row) else email.split('@')[0].title(),
                        primary_domain="",  # Not applicable for email mappings
                        extra_domains=[],
                        sheet_id=sheet_id,
                        google_drive_id=row[drive_id_idx].strip() if drive_id_idx and drive_id_idx < len(row) else "",
                        sheet_url=f"https://docs.google.com/spreadsheets/d/{sheet_id}",
                        admin_email=email,  # User is their own admin
                        created_at="",
                        letter_template=row[letter_template_idx].strip() if letter_template_idx and letter_template_idx < len(row) else "default",
                        letter_type=row[letter_type_idx].strip() if letter_type_idx and letter_type_idx < len(row) else "formal"
                    )

                    logger.info(f"Found email mapping: {email} → Sheet: {client_info.sheet_id}, Display: {client_info.display_name}")
                    return client_info

            # Email not found in mappings
            return None

        except Exception as e:
            logger.error(f"Error searching email in mappings for {email}: {e}")
            return None

    def _get_client_by_domain(self, domain: str) -> Optional[ClientInfo]:
        """
        Get client by domain matching (existing logic).
        Searches the Clients worksheet for matching primary or extra domains.

        Args:
            domain: Email domain (e.g., "moe.gov.sa")

        Returns:
            ClientInfo if domain matches, None otherwise
        """
        try:
            # Get master sheet data (uses cache)
            all_values = self._get_master_sheet_data()

            if not all_values or len(all_values) < 2:
                return None

            # Parse headers (first row)
            headers = [h.strip() for h in all_values[0]]

            # Find required column indices
            try:
                primary_domain_idx = headers.index("primaryDomain")
                extra_domains_idx = headers.index("extraDomains")
            except ValueError:
                logger.error("Master sheet missing required domain columns")
                return None

            # Search for matching domain
            for row in all_values[1:]:  # Skip header row
                if len(row) <= max(primary_domain_idx, extra_domains_idx):
                    continue

                primary_domain = row[primary_domain_idx].strip().lower() if primary_domain_idx < len(row) else ""
                extra_domains_str = row[extra_domains_idx].strip() if extra_domains_idx < len(row) else ""

                # Check primary domain match
                if domain == primary_domain:
                    logger.debug(f"Domain {domain} matched primary domain")
                    return self._create_client_info(row, headers)

                # Check extra domains match
                extra_domains = self._parse_extra_domains(extra_domains_str)
                if domain in extra_domains:
                    logger.debug(f"Domain {domain} matched extra domains")
                    return self._create_client_info(row, headers)

            return None

        except Exception as e:
            logger.error(f"Error getting client by domain {domain}: {e}")
            return None

    def _create_client_info(self, row: List[str], headers: List[str]) -> ClientInfo:
        """
        Create ClientInfo object from sheet row.

        Args:
            row: Sheet row data
            headers: Sheet headers

        Returns:
            ClientInfo object
        """
        def get_value(header_name: str, default: str = "") -> str:
            """Get value from row by header name."""
            try:
                idx = headers.index(header_name)
                return row[idx].strip() if idx < len(row) else default
            except (ValueError, IndexError):
                return default

        extra_domains_str = get_value("extraDomains")
        extra_domains = self._parse_extra_domains(extra_domains_str)

        return ClientInfo(
            client_id=get_value("clientId"),
            display_name=get_value("displayName"),
            primary_domain=get_value("primaryDomain"),
            extra_domains=extra_domains,
            sheet_id=get_value("sheetId"),
            google_drive_id=get_value("GoogleDriveId"),
            sheet_url=get_value("sheeturl"),
            admin_email=get_value("admin email"),
            created_at=get_value("createdAt"),
            letter_template=get_value("letter template"),
            letter_type=get_value("letter type")
        )

    @handle_storage_errors
    @measure_performance
    def validate_user_access(self, email: str) -> tuple[bool, Optional[ClientInfo], Optional[UserInfo]]:
        """
        Validate if user has access based on email.
        First finds the client by email domain, then checks user details in client's Users sheet.

        Args:
            email: User email address

        Returns:
            Tuple of (has_access, client_info, user_info)
        """
        with ErrorContext("validate_user_access", {"email": email}):
            try:
                # First, get client info by email domain
                client_info = self.get_client_by_email(email)
                if not client_info:
                    logger.warning(f"User access denied for {email}: No matching client found")
                    return False, None, None

                # Then, check user details in client's Users sheet
                user_info = self.get_user_details_from_client_sheet(client_info.sheet_id, email)
                if not user_info:
                    logger.warning(f"User access denied for {email}: User not found in client sheet")
                    return False, client_info, None

                # Check if user status allows access
                if user_info.status.lower() != "active":
                    logger.warning(f"User access denied for {email}: User status is {user_info.status}")
                    return False, client_info, user_info

                logger.info(f"User access granted for {email}: {client_info.display_name} - {user_info.full_name}")
                return True, client_info, user_info

            except Exception as e:
                logger.error(f"Error validating user access for {email}: {e}")
                return False, None, None

    @handle_storage_errors
    @measure_performance
    def get_user_details_from_client_sheet(self, sheet_id: str, email: str) -> Optional[UserInfo]:
        """
        Get user details from client's Users worksheet.

        Args:
            sheet_id: Google Sheet ID of the client
            email: User email to search for

        Returns:
            UserInfo if found, None otherwise
        """
        with ErrorContext("get_user_details_from_client_sheet", {"sheet_id": sheet_id, "email": email}):
            try:
                # Open the client's spreadsheet using context manager
                with self.get_client_context() as client:
                    spreadsheet = client.open_by_key(sheet_id)

                    # Try to get the "Users" worksheet
                    try:
                        worksheet = spreadsheet.worksheet("Users")
                    except gspread.WorksheetNotFound:
                        logger.warning(f"Users worksheet not found in sheet {sheet_id}")
                        return None

                    # Get all values
                    all_values = worksheet.get_all_values()
                    if not all_values or len(all_values) < 2:
                        logger.warning(f"Users worksheet is empty in sheet {sheet_id}")
                        return None

                    # Parse headers
                    headers = [h.strip().lower() for h in all_values[0]]

                    # Find column indices
                    try:
                        email_idx = headers.index("email")
                        full_name_idx = headers.index("full_name")
                        role_idx = headers.index("role")
                        status_idx = headers.index("status")
                        created_at_idx = headers.index("created_at")
                        password_idx = headers.index("password")
                    except ValueError as e:
                        logger.error(f"Users sheet missing required column in {sheet_id}: {e}")
                        return None

                    # Search for the user email
                    email_search = email.strip().lower()
                    for row in all_values[1:]:  # Skip header row
                        if len(row) <= email_idx:
                            continue

                        row_email = row[email_idx].strip().lower() if email_idx < len(row) else ""
                        if row_email == email_search:
                            # Found the user
                            user_info = UserInfo(
                                email=row[email_idx].strip() if email_idx < len(row) else "",
                                full_name=row[full_name_idx].strip() if full_name_idx < len(row) else "",
                                role=row[role_idx].strip() if role_idx < len(row) else "",
                                status=row[status_idx].strip() if status_idx < len(row) else "",
                                created_at=row[created_at_idx].strip() if created_at_idx < len(row) else "",
                                password=row[password_idx].strip() if password_idx < len(row) else ""
                            )
                            logger.info(f"User details found for {email} in sheet {sheet_id}")
                            return user_info

                    logger.warning(f"User {email} not found in Users worksheet of sheet {sheet_id}")
                    return None

            except Exception as e:
                logger.error(f"Error getting user details from client sheet {sheet_id} for {email}: {e}")
                return None

    @handle_storage_errors
    @measure_performance
    def get_all_clients(self) -> List[ClientInfo]:
        """
        Get all clients from master sheet.

        Returns:
            List of ClientInfo objects
        """
        with ErrorContext("get_all_clients"):
            try:
                all_values = self._get_master_sheet_data()

                if not all_values or len(all_values) < 2:
                    return []

                headers = [h.strip() for h in all_values[0]]
                clients = []

                for row in all_values[1:]:  # Skip header row
                    if not row or not row[0]:  # Skip empty rows
                        continue

                    try:
                        client_info = self._create_client_info(row, headers)
                        clients.append(client_info)
                    except Exception as e:
                        logger.warning(f"Failed to parse client row: {e}")
                        continue

                logger.info(f"Retrieved {len(clients)} clients from master sheet")
                return clients

            except Exception as e:
                logger.error(f"Error getting all clients: {e}")
                raise

    def clear_cache(self):
        """Clear all cached data."""
        self._client_cache.clear()
        self._master_data_cache = None
        logger.info("User management cache cleared")

    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get service statistics and status information.

        Returns:
            Dictionary with service statistics
        """
        return {
            "service": "UserManagementService",
            "master_sheet_id": MASTER_SHEET_ID,
            "cache_size": len(self._client_cache),
            "cache_ttl_seconds": CACHE_TTL,
            "last_connection": self._last_connection_time,
            "connection_lifetime": self._connection_lifetime
        }

    @handle_storage_errors
    @measure_performance
    def get_user_info(self, client_sheet_id: str, email: str) -> Optional[UserInfo]:
        """
        Get user information from client's Users sheet.

        Args:
            client_sheet_id: The client's Google Sheet ID
            email: User email to look up

        Returns:
            UserInfo if found, None otherwise
        """
        with ErrorContext("get_user_info", {"client_sheet_id": client_sheet_id, "email": email}):
            try:
                # Open the client's spreadsheet using context manager
                with self.get_client_context() as client:
                    spreadsheet = client.open_by_key(client_sheet_id)

                    # Try to get the "Users" worksheet
                    try:
                        worksheet = spreadsheet.worksheet("Users")
                    except gspread.WorksheetNotFound:
                        logger.warning(f"Users worksheet not found in client sheet {client_sheet_id}")
                        return None

                    all_values = worksheet.get_all_values()

                    if not all_values or len(all_values) < 2:
                        logger.warning(f"Users sheet is empty for client {client_sheet_id}")
                        return None

                    # Parse headers
                    headers = [h.strip().lower() for h in all_values[0]]

                    # Find column indices
                    try:
                        email_idx = headers.index("email")
                        full_name_idx = headers.index("full_name")
                        role_idx = headers.index("role")
                        status_idx = headers.index("status")
                        created_at_idx = headers.index("created_at")
                        password_idx = headers.index("password")
                    except ValueError as e:
                        logger.error(f"Users sheet missing required column: {e}")
                        return None

                    # Search for the user
                    for row in all_values[1:]:  # Skip header
                        if len(row) <= email_idx:
                            continue

                        row_email = row[email_idx].strip().lower()
                        if row_email == email.lower():
                            user_info = UserInfo(
                                email=row[email_idx].strip(),
                                full_name=row[full_name_idx].strip() if full_name_idx < len(row) and row[full_name_idx] else "",
                                role=row[role_idx].strip() if role_idx < len(row) and row[role_idx] else "user",
                                status=row[status_idx].strip() if status_idx < len(row) and row[status_idx] else "inactive",
                                created_at=row[created_at_idx].strip() if created_at_idx < len(row) and row[created_at_idx] else "",
                                password=row[password_idx].strip() if password_idx < len(row) and row[password_idx] else ""
                            )
                            logger.info(f"User found: {email} in client sheet {client_sheet_id}")
                            return user_info

                    logger.info(f"User not found: {email} in client sheet {client_sheet_id}")
                    return None

            except Exception as e:
                logger.error(f"Error getting user info for {email}: {e}")
                return None

    @handle_storage_errors
    @measure_performance
    def create_user(self, email: str, password: str, full_name: str, phone_number: str = "") -> tuple[bool, Optional[ClientInfo], Optional[UserInfo]]:
        """
        Create a new user in the appropriate client sheet.

        Args:
            email: User email
            password: User password
            full_name: User's full name
            phone_number: User's phone number (optional)

        Returns:
            Tuple of (success, client_info, user_info)
        """
        with ErrorContext("create_user", {"email": email}):
            try:
                # First, find which client this email belongs to
                client_info = self.get_client_by_email(email)
                if not client_info:
                    logger.warning(f"Cannot create user {email}: no matching client found")
                    return False, None, None
                
                # Check if user already exists
                existing_user = self.get_user_info(client_info.sheet_id, email)
                if existing_user:
                    logger.warning(f"User {email} already exists in client {client_info.display_name}")
                    return False, client_info, existing_user

                # Open the client's spreadsheet using context manager
                with self.get_client_context() as client:
                    spreadsheet = client.open_by_key(client_info.sheet_id)

                    # Get or create the "Users" worksheet
                    try:
                        worksheet = spreadsheet.worksheet("Users")
                    except gspread.WorksheetNotFound:
                        # Create the Users worksheet with headers
                        # Headers must match the actual sheet structure: email, full_name, PhoneNumber, role, status, created_at, password
                        worksheet = spreadsheet.add_worksheet(title="Users", rows=1000, cols=7)
                        worksheet.append_row(["email", "full_name", "PhoneNumber", "role", "status", "created_at", "password"])
                        logger.info(f"Created Users worksheet for client {client_info.display_name}")

                    # Add the new user
                    from datetime import datetime
                    created_at = datetime.now().isoformat()

                    # Hash the password
                    hashed_password = generate_password_hash(password)

                    # Match the exact sheet structure: email, full_name, PhoneNumber, role, status, created_at, password
                    new_row = [
                        email,
                        full_name,
                        phone_number,  # PhoneNumber (position 3)
                        "user",        # Default role (position 4)
                        "inactive",      # Initial status (position 5)
                        created_at,    # (position 6)
                        hashed_password  # password (position 7)
                    ]

                    worksheet.append_row(new_row)

                # Create UserInfo object (outside context since we just need local data)
                user_info = UserInfo(
                    email=email,
                    full_name=full_name,
                    role="user",
                    status="active",
                    created_at=created_at,
                    password=hashed_password
                )

                logger.info(f"User created successfully: {email} in client {client_info.display_name}")
                return True, client_info, user_info
                
            except Exception as e:
                logger.error(f"Error creating user {email}: {e}")
                return False, None, None

    def _create_access_token(self, client_info: ClientInfo, user_info: UserInfo, has_access: bool) -> str:
        import time
        token = jwt.encode(
            {
                "client_id": client_info.client_id,
                "admin_email": client_info.admin_email,
                "exp": time.time() + (self.config.auth.token_expiry_hours * 3600),
                "sheet_id": client_info.sheet_id,
                "google_drive_id": client_info.google_drive_id,
                "letter_template": client_info.letter_template,
                "has_access": has_access,
                "letter_type": client_info.letter_type,
                "user": user_info.to_dict()
            },
            self.config.auth.jwt_secret,
            algorithm=self.config.auth.jwt_algorithm
        )
        return token

    @handle_storage_errors
    @measure_performance
    def validate_user_credentials(self, email: str, password: str) -> tuple[bool, Optional[ClientInfo], Optional[UserInfo]]:
        """
        Validate user credentials (email and password).

        Args:
            email: User email
            password: User password

        Returns:
            Tuple of (success, client_info, user_info)
        """
        with ErrorContext("validate_user_credentials", {"email": email}):
            try:
                # First, find which client this email belongs to
                client_info = self.get_client_by_email(email)
                if not client_info:
                    logger.warning(f"Validation failed {email}: no matching client found")
                    return False, None, None
                
                # Get user info from the client's Users sheet
                user_info = self.get_user_info(client_info.sheet_id, email)
                if not user_info:
                    logger.warning(f"Validation failed {email}: user not found in client {client_info.display_name}")
                    return False, client_info, None
                
                # Check if user is active
                if user_info.status.lower() != "active":
                    logger.warning(f"Validation failed {email}: user account is {user_info.status}")
                    return False, client_info, user_info
                
                # Verify password
                password_valid = False
                needs_rehash = False
                
                # Debug logging
                print(f"\n[DEBUG] Password verification for {email}:")
                print(f"[DEBUG]   Stored password length: {len(user_info.password) if user_info.password else 0}")
                print(f"[DEBUG]   Stored password first 30 chars: {user_info.password[:30] if user_info.password else 'EMPTY'}...")
                print(f"[DEBUG]   Provided password: {password}")
                
                # Check if it's a werkzeug hash (supports pbkdf2, scrypt, bcrypt, etc.)
                is_hashed = user_info.password and (':' in user_info.password and '$' in user_info.password)
                print(f"[DEBUG]   Is hashed password: {is_hashed}")
                
                logger.debug(f"Password verification for {email}:")
                logger.debug(f"  Stored password starts with: {user_info.password[:20] if user_info.password else 'EMPTY'}...")
                logger.debug(f"  Provided password: {password}")
                logger.debug(f"  Is hashed: {is_hashed}")
                
                if is_hashed:  # It's a werkzeug hash (pbkdf2, scrypt, bcrypt, etc.)
                    password_valid = check_password_hash(user_info.password, password)
                    print(f"[DEBUG]   Hash verification result: {password_valid}")
                    logger.debug(f"  Hash verification result: {password_valid}")
                elif user_info.password:  # Plain text password (backward compatibility)
                    password_valid = user_info.password == password
                    if password_valid:
                        needs_rehash = True
                        logger.info(f"Plain text password detected for {email}, will re-hash")
                    print(f"[DEBUG]   Plain text comparison result: {password_valid}")
                    logger.debug(f"  Plain text comparison result: {password_valid}")
                else:
                    logger.warning(f"Empty password for user {email}")
                
                if not password_valid:
                    print(f"[DEBUG]   ❌ VALIDATION FAILED\n")
                    logger.warning(f"Validation failed {email}: invalid password")
                    return False, client_info, user_info
                else:
                    print(f"[DEBUG]   ✅ VALIDATION SUCCESS\n")
                
                # Re-hash plain text password for security
                if needs_rehash:
                    self._update_user_password(client_info.sheet_id, email, password)
                
                logger.info(f"User credentials validated successfully: {email} for client {client_info.display_name}")
                return True, client_info, user_info
                
            except Exception as e:
                logger.error(f"Error validating user credentials {email}: {e}")
                return False, None, None

    # Alias for backward compatibility with the validate endpoint
    def login_user(self, email: str, password: str) -> tuple[bool, Optional[ClientInfo], Optional[UserInfo]]:
        """Alias for validate_user_credentials for backward compatibility."""
        return self.validate_user_credentials(email, password)
    
    def _update_user_password(self, sheet_id: str, email: str, new_password: str):
        """
        Update user password in the sheet (used for re-hashing plain text passwords).

        Args:
            sheet_id: Google Sheet ID
            email: User email
            new_password: New password to hash and store
        """
        try:
            with self.get_client_context() as client:
                spreadsheet = client.open_by_key(sheet_id)
                worksheet = spreadsheet.worksheet("Users")
                all_values = worksheet.get_all_values()

                if not all_values or len(all_values) < 2:
                    return

                headers = [h.strip().lower() for h in all_values[0]]
                email_idx = headers.index("email")
                password_idx = headers.index("password")

                # Find and update the user
                for i, row in enumerate(all_values[1:], 1):  # Skip header, i starts from 1
                    if len(row) > email_idx and row[email_idx].strip().lower() == email.lower():
                        hashed_password = generate_password_hash(new_password)
                        worksheet.update_cell(i + 1, password_idx + 1, hashed_password)  # +1 because worksheet is 1-indexed
                        logger.info(f"Password re-hashed for user {email}")
                        break

        except Exception as e:
            logger.error(f"Error updating password for {email}: {e}")

    def reset_password(self, email: str, old_password: str, new_password: str) -> tuple[bool, str]:
        """
        Reset user password (requires old password for verification).

        Args:
            email: User email
            old_password: Current password (for verification)
            new_password: New password to set

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate inputs
            if not email or not old_password or not new_password:
                return False, "البريد الإلكتروني وكلمات المرور مطلوبة"

            if len(new_password) < 6:
                return False, "كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل"

            if old_password == new_password:
                return False, "كلمة المرور الجديدة يجب أن تختلف عن كلمة المرور القديمة"

            # Verify old password first
            success, client_info, user_info = self.validate_user_credentials(email, old_password)

            if not success or not client_info or not user_info:
                logger.warning(f"Password reset failed - invalid credentials for: {email}")
                return False, "البريد الإلكتروني أو كلمة المرور غير صحيحة"

            # Update password
            self._update_user_password(client_info.sheet_id, email, new_password)

            logger.info(f"Password reset successfully for user: {email}")
            return True, "تم تحديث كلمة المرور بنجاح"

        except Exception as e:
            logger.error(f"Error resetting password for {email}: {e}")
            return False, f"حدث خطأ في تحديث كلمة المرور: {str(e)}"

    def forgot_password_reset(self, email: str, new_password: str) -> tuple[bool, str]:
        """
        Reset password for forgotten password scenario (without old password verification).
        This should be used with additional security measures (email verification, security questions, etc.)

        Args:
            email: User email
            new_password: New password to set

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate inputs
            if not email or not new_password:
                return False, "البريد الإلكتروني وكلمة المرور مطلوبة"

            if len(new_password) < 6:
                return False, "كلمة المرور يجب أن تكون 6 أحرف على الأقل"

            # Check if user exists
            client_info = self.get_client_by_email(email)
            if not client_info:
                logger.warning(f"Forgot password reset failed - no client found for: {email}")
                return False, "لا يوجد عميل مطابق لهذا البريد الإلكتروني"

            # Get user from client sheet
            user_info = self.get_user_details_from_client_sheet(client_info.sheet_id, email)
            if not user_info:
                logger.warning(f"Forgot password reset failed - user not found: {email}")
                return False, "المستخدم غير موجود"

            # Update password
            self._update_user_password(client_info.sheet_id, email, new_password)

            logger.info(f"Password reset successfully (forgot password) for user: {email}")
            return True, "تم تحديث كلمة المرور بنجاح"

        except Exception as e:
            logger.error(f"Error resetting forgotten password for {email}: {e}")
            return False, f"حدث خطأ في تحديث كلمة المرور: {str(e)}"

    @handle_storage_errors
    @measure_performance
    def add_email_mapping(self, email: str, sheet_id: str, google_drive_id: str = "",
                         display_name: str = "", letter_template: str = "default",
                         letter_type: str = "formal") -> bool:
        """
        Add or update an email mapping in the EmailMappings worksheet.
        This allows a user with a public email domain to be mapped to a specific client sheet.

        Args:
            email: User email address
            sheet_id: Client's Google Sheet ID
            google_drive_id: Client's Google Drive folder ID (optional)
            display_name: Display name for the client (optional)
            letter_template: Letter template type (default: "default")
            letter_type: Letter type (default: "formal")

        Returns:
            True if successful, False otherwise
        """
        try:
            email = email.strip().lower()

            with self.get_client_context() as client:
                master_sheet = client.open_by_key(self.master_sheet_id)

                # Get or create EmailMappings worksheet
                try:
                    email_mappings_ws = master_sheet.worksheet(EMAIL_MAPPINGS_WORKSHEET)
                except gspread.exceptions.WorksheetNotFound:
                    # Create the worksheet if it doesn't exist
                    logger.info(f"Creating EmailMappings worksheet in master sheet")
                    email_mappings_ws = master_sheet.add_worksheet(
                        title=EMAIL_MAPPINGS_WORKSHEET,
                        rows=100,
                        cols=10
                    )
                    # Add headers
                    email_mappings_ws.append_row([
                        "email", "sheetId", "GoogleDriveId",
                        "displayName", "letterTemplate", "letterType"
                    ])

                # Check if email already exists
                all_mappings = email_mappings_ws.get_all_values()
                email_exists = False
                row_index = None

                for idx, row in enumerate(all_mappings[1:], start=2):  # Skip header
                    if len(row) > 0 and row[0].strip().lower() == email:
                        email_exists = True
                        row_index = idx
                        break

                # Prepare row data
                row_data = [
                    email,
                    sheet_id,
                    google_drive_id,
                    display_name or email.split('@')[0].title(),
                    letter_template,
                    letter_type
                ]

                if email_exists:
                    # Update existing mapping
                    email_mappings_ws.update(f'A{row_index}:F{row_index}', [row_data])
                    logger.info(f"Updated email mapping: {email} → {sheet_id}")
                else:
                    # Add new mapping
                    email_mappings_ws.append_row(row_data)
                    logger.info(f"Added email mapping: {email} → {sheet_id}")

                # Invalidate cache
                self._email_mappings_cache = None
                if email in self._client_cache:
                    del self._client_cache[email]

                return True

        except Exception as e:
            logger.error(f"Error adding email mapping for {email}: {e}")
            return False

    @handle_storage_errors
    @measure_performance
    def remove_email_mapping(self, email: str) -> bool:
        """
        Remove an email mapping from the EmailMappings worksheet.

        Args:
            email: User email address to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            email = email.strip().lower()

            with self.get_client_context() as client:
                master_sheet = client.open_by_key(self.master_sheet_id)

                try:
                    email_mappings_ws = master_sheet.worksheet(EMAIL_MAPPINGS_WORKSHEET)
                except gspread.exceptions.WorksheetNotFound:
                    logger.warning(f"EmailMappings worksheet not found when trying to remove {email}")
                    return False

                # Find and delete the email mapping
                all_mappings = email_mappings_ws.get_all_values()

                for idx, row in enumerate(all_mappings[1:], start=2):  # Skip header
                    if len(row) > 0 and row[0].strip().lower() == email:
                        email_mappings_ws.delete_rows(idx)
                        logger.info(f"Removed email mapping: {email}")

                        # Invalidate cache
                        self._email_mappings_cache = None
                        if email in self._client_cache:
                            del self._client_cache[email]

                        return True

                logger.warning(f"Email mapping not found for removal: {email}")
                return False

        except Exception as e:
            logger.error(f"Error removing email mapping for {email}: {e}")
            return False

    @handle_storage_errors
    @measure_performance
    def check_if_email_needs_mapping(self, email: str) -> bool:
        """
        Check if an email address requires an EmailMappings entry.
        Public email domains (gmail, yahoo, outlook, etc.) need explicit mapping.

        Args:
            email: User email address

        Returns:
            True if email needs mapping (public domain), False if organizational domain
        """
        PUBLIC_EMAIL_DOMAINS = {
            'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
            'aol.com', 'icloud.com', 'live.com', 'msn.com',
            'mail.com', 'protonmail.com', 'zoho.com'
        }

        try:
            domain = self._extract_domain_from_email(email.strip().lower())
            return domain in PUBLIC_EMAIL_DOMAINS
        except Exception:
            return False

    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get service statistics and status information.

        Returns:
            Dictionary with service statistics
        """
        pool_stats = self._pool.get_stats()
        return {
            "service": "UserManagementService",
            "pool_stats": pool_stats,
            "cache_size": len(self._client_cache),
            "master_data_cached": self._master_data_cache is not None,
            "email_mappings_cached": self._email_mappings_cache is not None,
            "connection_lifetime": 3600,
            "max_idle_time": 300,
            "cache_ttl": CACHE_TTL
        }

    def close_pool(self) -> None:
        """Close all connections in the pool."""
        self._pool.close_all()
        logger.info("User Management connection pool closed")


# Global service instance
_user_management_service = None


def get_user_management_service() -> UserManagementService:
    """Get the global User Management service instance."""
    global _user_management_service
    if _user_management_service is None:
        _user_management_service = UserManagementService()
    return _user_management_service
