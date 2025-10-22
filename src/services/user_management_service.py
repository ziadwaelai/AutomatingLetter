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

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from ..config import get_config
from ..utils import (
    handle_storage_errors,
    measure_performance,
    ErrorContext,
    StorageServiceError
)

logger = logging.getLogger(__name__)

# Master sheet ID (hardcoded as per requirements)
MASTER_SHEET_ID = "11eCtNuW4cl03TX0G20alx3_6B5DI7IbpQPnPDeRGKlI"

# Cache TTL in seconds (5 minutes)
CACHE_TTL = 300


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

    def __init__(self):
        """Initialize User Management service."""
        self.config = get_config()
        self._validate_configuration()
        self._client = None
        self._last_connection_time = 0
        self._connection_lifetime = 3600  # 1 hour

        # Cache for client data
        self._client_cache: Dict[str, tuple[ClientInfo, float]] = {}
        self._master_data_cache: Optional[tuple[List[List[str]], float]] = None

    def _validate_configuration(self):
        """Validate configuration."""
        import os
        if not os.path.exists(self.config.storage.service_account_file):
            raise StorageServiceError(
                f"Service account file not found: {self.config.storage.service_account_file}"
            )

    @property
    def client(self):
        """Get or create Google Sheets client with connection reuse."""
        current_time = time.time()

        if (self._client is None or
            current_time - self._last_connection_time > self._connection_lifetime):

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
                self._client = gspread.authorize(creds)
                self._last_connection_time = current_time

                logger.debug("User Management Google Sheets client connection established")

            except Exception as e:
                raise StorageServiceError(f"Failed to connect to Google Sheets: {e}")

        return self._client

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
            spreadsheet = self.client.open_by_key(MASTER_SHEET_ID)
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
        Get client information by user email.
        Matches email domain against primary domain and extra domains.

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

                # Extract domain from email
                email_domain = self._extract_domain_from_email(email)

                # Get master sheet data
                all_values = self._get_master_sheet_data()

                if not all_values or len(all_values) < 2:
                    raise StorageServiceError("Master sheet is empty or has no data rows")

                # Parse headers (first row)
                headers = [h.strip() for h in all_values[0]]

                # Find column indices
                try:
                    client_id_idx = headers.index("clientId")
                    display_name_idx = headers.index("displayName")
                    primary_domain_idx = headers.index("primaryDomain")
                    extra_domains_idx = headers.index("extraDomains")
                    sheet_id_idx = headers.index("sheetId")
                    drive_id_idx = headers.index("GoogleDriveId")
                    sheet_url_idx = headers.index("sheeturl")
                    admin_email_idx = headers.index("admin email")
                    created_at_idx = headers.index("createdAt")
                    letter_template_idx = headers.index("letter template")
                    letter_type_idx = headers.index("letter type")
                except ValueError as e:
                    raise StorageServiceError(f"Master sheet missing required column: {e}")

                # Search for matching client
                for row in all_values[1:]:  # Skip header row
                    if len(row) <= max(client_id_idx, primary_domain_idx, extra_domains_idx):
                        continue  # Skip incomplete rows

                    primary_domain = row[primary_domain_idx].strip().lower() if primary_domain_idx < len(row) else ""
                    extra_domains_str = row[extra_domains_idx].strip() if extra_domains_idx < len(row) else ""

                    # Check if email domain matches primary domain
                    if email_domain == primary_domain:
                        client_info = self._create_client_info(row, headers)
                        # Cache the result
                        self._client_cache[email] = (client_info, current_time)
                        logger.info(f"Client found for email {email}: {client_info.display_name}")
                        return client_info

                    # Check if email domain matches any extra domain
                    extra_domains = self._parse_extra_domains(extra_domains_str)
                    if email_domain in extra_domains:
                        client_info = self._create_client_info(row, headers)
                        # Cache the result
                        self._client_cache[email] = (client_info, current_time)
                        logger.info(f"Client found for email {email}: {client_info.display_name}")
                        return client_info

                logger.warning(f"No client found for email: {email} (domain: {email_domain})")
                return None

            except Exception as e:
                logger.error(f"Error getting client by email {email}: {e}")
                raise

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
    def validate_user_access(self, email: str) -> tuple[bool, Optional[ClientInfo]]:
        """
        Validate if user has access based on email.

        Args:
            email: User email address

        Returns:
            Tuple of (has_access, client_info)
        """
        with ErrorContext("validate_user_access", {"email": email}):
            try:
                client_info = self.get_client_by_email(email)
                has_access = client_info is not None

                if has_access:
                    logger.info(f"User access granted for {email}: {client_info.display_name}")
                else:
                    logger.warning(f"User access denied for {email}: No matching client found")

                return has_access, client_info

            except Exception as e:
                logger.error(f"Error validating user access for {email}: {e}")
                return False, None

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

    def _create_access_token(self, client_info: ClientInfo, has_access: bool) -> str:
        import time
        token = jwt.encode(
            {
                "client_id": client_info.client_id,
                "admin_email": client_info.admin_email,
                "exp": time.time() + (self.config.auth.token_expiry_hours * 3600),
                "sheet_id" : client_info.sheet_id,
                "letter_template": client_info.letter_template,
                "has_access": has_access,
                "letter_type": client_info.letter_type
            },
            self.config.auth.jwt_secret,
            algorithm=self.config.auth.jwt_algorithm
        )
        return token


# Global service instance
_user_management_service = None


def get_user_management_service() -> UserManagementService:
    """Get the global User Management service instance."""
    global _user_management_service
    if _user_management_service is None:
        _user_management_service = UserManagementService()
    return _user_management_service
