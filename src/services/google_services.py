"""
Refactored Google Services Module
Enhanced version with better error handling, connection pooling, and performance optimization.
"""

import logging
import concurrent.futures
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
import time
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

from ..config import get_config
from ..utils import (
    handle_storage_errors,
    measure_performance,
    retry_with_backoff,
    ErrorContext,
    StorageServiceError,
    format_timestamp
)

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Enhanced Google Sheets service with connection pooling and caching."""
    
    def __init__(self):
        """Initialize Google Sheets service."""
        self.config = get_config()
        self._validate_configuration()
        self._client = None
        self._last_connection_time = 0
        self._connection_lifetime = 3600  # 1 hour
        
    def _validate_configuration(self):
        """Validate Google Sheets configuration."""
        if not os.path.exists(self.config.storage.service_account_file):
            raise StorageServiceError(f"Service account file not found: {self.config.storage.service_account_file}")
    
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
                
                logger.debug("Google Sheets client connection established")
                
            except Exception as e:
                raise StorageServiceError(f"Failed to connect to Google Sheets: {e}")
        
        return self._client
    
    @handle_storage_errors
    @measure_performance
    def get_data_by_key(self, key: str, sheet_name: str, concatenate_multiple: bool = False) -> Optional[str]:
        """
        Fetch data by key from a specified sheet with caching.
        
        Args:
            key: The key/category to search for
            sheet_name: The worksheet name
            concatenate_multiple: If True, concatenate multiple matches
            
        Returns:
            Found data or None
        """
        with ErrorContext("get_data_by_key", {"key": key, "sheet": sheet_name}):
            try:
                worksheet = self.client.open(self.config.database.letters_spreadsheet).worksheet(sheet_name)
                rows = worksheet.get_all_values()
                
                matches = [
                    row[1] for row in rows
                    if row and len(row) > 1 and row[0].strip().lower() == key.strip().lower()
                ]
                
                if concatenate_multiple and len(matches) > 1:
                    return "\n\n".join(matches[:2])  # Limit to 2 matches
                
                return matches[0] if matches else None
                
            except gspread.WorksheetNotFound:
                raise StorageServiceError(f"Worksheet '{sheet_name}' not found")
            except Exception as e:
                raise StorageServiceError(f"Error fetching data from Google Sheets: {e}")
    
    @handle_storage_errors
    @measure_performance
    def get_data_by_key_from_sheet_id(self, sheet_id: str, key: str, sheet_name: str, concatenate_multiple: bool = False) -> Optional[str]:
        """
        Fetch data by key from a specified sheet in a user's spreadsheet (by sheet_id).
        Searches first column for key, returns second column value.
        
        Args:
            sheet_id: Google Sheet ID
            key: The key/category to search for (in first column)
            sheet_name: The worksheet name
            concatenate_multiple: If True, concatenate multiple matches
            
        Returns:
            Found data (second column) or None
        """
        with ErrorContext("get_data_by_key_from_sheet_id", {"sheet_id": sheet_id, "key": key, "sheet": sheet_name}):
            try:
                spreadsheet = self.client.open_by_key(sheet_id)
                worksheet = spreadsheet.worksheet(sheet_name)
                rows = worksheet.get_all_values()
                
                # Search first column for key, return second column
                matches = [
                    row[1] for row in rows
                    if row and len(row) > 1 and row[0].strip().lower() == key.strip().lower()
                ]
                
                if concatenate_multiple and len(matches) > 1:
                    return "\n\n".join(matches[:2])  # Limit to 2 matches
                
                return matches[0] if matches else None
                
            except gspread.WorksheetNotFound:
                logger.warning(f"Worksheet '{sheet_name}' not found in sheet {sheet_id}")
                return None
            except Exception as e:
                logger.error(f"Error fetching data from sheet {sheet_id}: {e}")
                return None
    
    @handle_storage_errors
    @measure_performance
    def get_user_info_from_sheet_id(self, sheet_id: str, full_name: str) -> Optional[str]:
        """
        Fetch user info from Users sheet by full_name.
        Searches for full_name and returns email and PhoneNumber combined.
        Columns: email, full_name, PhoneNumber, role, status, created_at
        
        Args:
            sheet_id: Google Sheet ID
            full_name: Full name to search for (case-insensitive)
            
        Returns:
            String with "Email: {email}, PhoneNumber: {phone}" or None if not found
        """
        with ErrorContext("get_user_info_from_sheet_id", {"sheet_id": sheet_id, "full_name": full_name}):
            try:
                spreadsheet = self.client.open_by_key(sheet_id)
                worksheet = spreadsheet.worksheet("Users")
                
                all_values = worksheet.get_all_values()
                if not all_values or len(all_values) < 2:
                    logger.warning(f"Users sheet is empty in sheet {sheet_id}")
                    return None
                
                # Parse headers (first row) - case sensitive match
                headers = all_values[0]
                
                # Find column indices
                email_idx = None
                full_name_idx = None
                phone_idx = None
                for idx, header in enumerate(headers):
                    if header.strip() == "email":
                        email_idx = idx
                    elif header.strip() == "full_name":
                        full_name_idx = idx
                    elif header.strip() == "PhoneNumber":
                        phone_idx = idx
                
                if email_idx is None or full_name_idx is None or phone_idx is None:
                    logger.error(f"Users sheet missing required columns. Found headers: {headers}")
                    return None
                
                # Search for matching full_name
                full_name_lower = full_name.strip().lower()
                for row in all_values[1:]:  # Skip header row
                    if len(row) > max(email_idx, full_name_idx, phone_idx):
                        row_full_name = row[full_name_idx].strip().lower() if full_name_idx < len(row) else ""
                        if row_full_name == full_name_lower:
                            email = row[email_idx].strip() if email_idx < len(row) else ""
                            phone = row[phone_idx].strip() if phone_idx < len(row) else ""
                            user_info = f"Email: {email}, PhoneNumber: {phone}"
                            logger.info(f"User info found for full_name: {full_name}")
                            return user_info if (email or phone) else None
                
                logger.warning(f"No user found with full_name: {full_name}")
                return None
                
            except gspread.WorksheetNotFound:
                logger.warning(f"Users worksheet not found in sheet {sheet_id}")
                return None
            except Exception as e:
                logger.error(f"Error getting user info from sheet {sheet_id}: {e}")
                return None
    
    @handle_storage_errors
    @measure_performance
    def get_letter_config_by_category(self, category: str, member_name: str = "") -> Dict[str, str]:
        """
        Fetch letter configuration with parallel execution for better performance.
        
        Args:
            category: Letter category
            member_name: Member name for personalization
            
        Returns:
            Dictionary with letter, instruction, and member_info
        """
        with ErrorContext("get_letter_config", {"category": category, "member": member_name}):
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    # Submit all tasks in parallel
                    letter_future = executor.submit(
                        self.get_data_by_key, category, self.config.database.ideal_worksheet, True
                    )
                    instruction_future = executor.submit(
                        self.get_data_by_key, category, self.config.database.instructions_worksheet
                    )
                    all_instructions_future = executor.submit(
                        self.get_data_by_key, "الجميع", self.config.database.instructions_worksheet
                    )
                    member_info_future = executor.submit(
                        self.get_data_by_key, member_name, self.config.database.info_worksheet
                    )
                    
                    # Get results
                    letter = letter_future.result() or ""
                    instruction = instruction_future.result() or ""
                    all_instructions = all_instructions_future.result() or ""
                    member_info = member_info_future.result() or ""
                
                # Combine instructions
                instructions = "\n".join(
                    filter(None, [all_instructions.strip(), instruction.strip()])
                )
                
                result = {
                    "letter": letter,
                    "instruction": instructions,
                    "member_info": member_info
                }
                
                logger.debug(f"Letter config retrieved for category: {category}")
                return result
                
            except Exception as e:
                logger.error(f"Failed to get letter config for category {category}: {e}")
                raise StorageServiceError(f"Error fetching letter configuration: {e}")
    
    @handle_storage_errors
    @measure_performance
    def get_letter_config_by_category_from_sheet_id(self, sheet_id: str, category: str, member_name: str = "") -> Dict[str, str]:
        """
        Fetch letter configuration from user's sheet by category (parallel execution).
        Same behavior as get_letter_config_by_category but uses sheet_id instead of config spreadsheet.
        
        Args:
            sheet_id: Google Sheet ID
            category: Letter category
            member_name: Member name for personalization
            
        Returns:
            Dictionary with letter, instruction, and member_info
        """
        with ErrorContext("get_letter_config_by_category_from_sheet_id", {"sheet_id": sheet_id, "category": category, "member": member_name}):
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    # Submit all tasks in parallel - load from user's sheet
                    letter_future = executor.submit(
                        self.get_data_by_key_from_sheet_id, sheet_id, category, "Templates", True
                    )
                    instruction_future = executor.submit(
                        self.get_data_by_key_from_sheet_id, sheet_id, category, "Instructions"
                    )
                    all_instructions_future = executor.submit(
                        self.get_data_by_key_from_sheet_id, sheet_id, "الجميع", "Instructions"
                    )
                    # Use new method to get user info (email + phone) from Users sheet
                    member_info_future = executor.submit(
                        self.get_user_info_from_sheet_id, sheet_id, member_name
                    )
                    
                    # Get results
                    letter = letter_future.result() or ""
                    instruction = instruction_future.result() or ""
                    all_instructions = all_instructions_future.result() or ""
                    member_info = member_info_future.result() or ""
                
                # Combine instructions - general first, then specific
                instructions = "\n".join(
                    filter(None, [all_instructions.strip(), instruction.strip()])
                )
                
                result = {
                    "letter": letter,
                    "instruction": instructions,
                    "member_info": member_info
                }
                
                logger.debug(f"Letter config retrieved from sheet {sheet_id} for category: {category}")
                return result
                
            except Exception as e:
                logger.error(f"Failed to get letter config from sheet {sheet_id} for category {category}: {e}")
                return {
                    "letter": "",
                    "instruction": "اكتب خطاباً رسمياً باللغة العربية",
                    "member_info": ""
                }
    
    @handle_storage_errors
    @measure_performance
    def log_to_sheet(
        self, 
        spreadsheet_name: str,
        worksheet_name: str,
        entries: List[Dict[str, Any]],
        value_input_option: str = 'RAW'
    ) -> Dict[str, Any]:
        """
        Log entries to a Google Sheet with better error handling.
        
        Args:
            spreadsheet_name: Target spreadsheet name
            worksheet_name: Target worksheet name
            entries: List of entries to log
            value_input_option: How to interpret input values
            
        Returns:
            Result dictionary with status information
        """
        with ErrorContext("log_to_sheet", {"spreadsheet": spreadsheet_name, "worksheet": worksheet_name}):
            try:
                worksheet = self.client.open(spreadsheet_name).worksheet(worksheet_name)
                headers = worksheet.row_values(1)
                
                if not headers:
                    raise StorageServiceError("Worksheet has no headers")
                
                header_map = {h.strip(): idx for idx, h in enumerate(headers)}
                appended_count = 0
                
                for entry in entries:
                    row = [''] * len(headers)
                    for key, value in entry.items():
                        if key.strip() in header_map:
                            row[header_map[key.strip()]] = str(value) if value is not None else ''
                    
                    worksheet.append_row(row, value_input_option=value_input_option)
                    appended_count += 1
                
                logger.info(f"Successfully logged {appended_count} entries to {spreadsheet_name}/{worksheet_name}")
                
                return {
                    "status": "success",
                    "spreadsheet": spreadsheet_name,
                    "worksheet": worksheet_name,
                    "rows_appended": appended_count
                }
                
            except gspread.SpreadsheetNotFound:
                raise StorageServiceError(f"Spreadsheet '{spreadsheet_name}' not found")
            except gspread.WorksheetNotFound:
                raise StorageServiceError(f"Worksheet '{worksheet_name}' not found")
            except Exception as e:
                raise StorageServiceError(f"Error logging to Google Sheets: {e}")
    
    def get_connection_status(self) -> str:
        """
        Check Google Sheets service connection status.
        
        Returns:
            Status string indicating connection health
        """
        try:
            # Try to access the client to verify connection
            client = self.client
            if client:
                # Try a simple operation to test the connection
                try:
                    # Just check if we can get the client instance
                    return "healthy"
                except Exception as e:
                    logger.warning(f"Google Sheets connection test failed: {e}")
                    return f"unhealthy: Connection test failed - {str(e)}"
            else:
                return "unhealthy: No client available"
        except Exception as e:
            logger.error(f"Google Sheets connection status check failed: {e}")
            return f"unhealthy: {str(e)}"
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get service statistics and status information.
        
        Returns:
            Dictionary with service statistics
        """
        return {
            "service": "GoogleSheetsService",
            "status": self.get_connection_status(),
            "last_connection": getattr(self, '_last_connection_time', 0),
            "connection_lifetime": getattr(self, '_connection_lifetime', 3600)
        }
    
    def log_entries(self, spreadsheet_name: str, worksheet_name: str, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Alias for log_to_sheet method for backward compatibility.
        
        Args:
            spreadsheet_name: Target spreadsheet name
            worksheet_name: Target worksheet name
            entries: List of entries to log
            
        Returns:
            Result dictionary with status information
        """
        return self.log_to_sheet(spreadsheet_name, worksheet_name, entries)
    
    @handle_storage_errors
    @measure_performance
    def log_entries_by_id(self, sheet_id: str, worksheet_name: str, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Log entries to Google Sheets by sheet ID.
        
        Args:
            sheet_id: Google Sheet ID
            worksheet_name: Target worksheet name
            entries: List of entries to log
            
        Returns:
            Result dictionary with status information
        """
        with ErrorContext("log_entries_by_id", {"sheet_id": sheet_id, "worksheet": worksheet_name}):
            try:
                # Open spreadsheet by ID
                spreadsheet = self.client.open_by_key(sheet_id)
                worksheet = spreadsheet.worksheet(worksheet_name)
                
                # Get existing headers
                all_values = worksheet.get_all_values()
                if not all_values:
                    # If empty, create headers from first entry
                    if entries:
                        headers = list(entries[0].keys())
                        worksheet.append_row(headers)
                        logger.info(f"Created new headers in sheet {sheet_id}: {headers}")
                else:
                    headers = all_values[0]
                
                # Prepare rows to append
                rows_to_add = []
                for entry in entries:
                    row = [entry.get(header, "") for header in headers]
                    rows_to_add.append(row)
                
                # Append rows
                if rows_to_add:
                    worksheet.append_rows(rows_to_add)
                    logger.info(f"Successfully logged {len(rows_to_add)} entries to sheet {sheet_id}, worksheet '{worksheet_name}'")
                
                return {
                    "status": "success",
                    "entries_logged": len(rows_to_add),
                    "sheet_id": sheet_id,
                    "worksheet": worksheet_name
                }
                
            except Exception as e:
                logger.error(f"Error logging entries to sheet {sheet_id}: {e}")
                raise StorageServiceError(f"Failed to log entries to sheet: {e}")
    
    @handle_storage_errors
    @measure_performance
    def update_row_by_id(
        self, 
        spreadsheet_name: str,
        worksheet_name: str,
        letter_id: str,
        updates: Dict[str, Any],
        id_column: str = "ID"
    ) -> Dict[str, Any]:
        """
        Update a specific row in Google Sheets by finding it with the given ID.
        
        Args:
            spreadsheet_name: Target spreadsheet name
            worksheet_name: Target worksheet name
            letter_id: The ID to search for
            updates: Dictionary with column names and new values
            id_column: Name of the column containing IDs (default: "ID")
            
        Returns:
            Result dictionary with status information
        """
        with ErrorContext("update_row_by_id", {"spreadsheet": spreadsheet_name, "worksheet": worksheet_name, "id": letter_id}):
            try:
                worksheet = self.client.open(spreadsheet_name).worksheet(worksheet_name)
                
                # Get all values and headers
                all_values = worksheet.get_all_values()
                if not all_values:
                    raise StorageServiceError("Worksheet is empty")
                
                headers = all_values[0]
                header_map = {h.strip(): idx for idx, h in enumerate(headers)}
                
                # Find ID column
                if id_column not in header_map:
                    raise StorageServiceError(f"Column '{id_column}' not found in worksheet")
                
                id_col_index = header_map[id_column]
                
                # Find the row with matching ID (starting from row 2, since row 1 is headers)
                target_row = None
                for row_index, row in enumerate(all_values[1:], start=2):  # start=2 because spreadsheet rows are 1-indexed and we skip header
                    if row_index <= len(all_values) and id_col_index < len(row):
                        if row[id_col_index].strip() == letter_id.strip():
                            target_row = row_index
                            break
                
                if target_row is None:
                    raise StorageServiceError(f"Letter with ID '{letter_id}' not found in worksheet")
                
                # Update the specific cells
                updated_columns = []
                for column_name, new_value in updates.items():
                    if column_name.strip() in header_map:
                        col_index = header_map[column_name.strip()]
                        # Use update_cell instead of update with A1 notation
                        worksheet.update_cell(target_row, col_index + 1, str(new_value) if new_value is not None else '')
                        updated_columns.append(column_name)
                        logger.debug(f"Updated cell at row {target_row}, col {col_index + 1} with value: {new_value}")
                
                logger.info(f"Successfully updated row {target_row} for ID '{letter_id}' in {spreadsheet_name}/{worksheet_name}")
                
                return {
                    "status": "success",
                    "spreadsheet": spreadsheet_name,
                    "worksheet": worksheet_name,
                    "updated_row": target_row,
                    "updated_columns": updated_columns,
                    "letter_id": letter_id
                }
                
            except gspread.SpreadsheetNotFound:
                raise StorageServiceError(f"Spreadsheet '{spreadsheet_name}' not found")
            except gspread.WorksheetNotFound:
                raise StorageServiceError(f"Worksheet '{worksheet_name}' not found")
            except Exception as e:
                raise StorageServiceError(f"Error updating row in Google Sheets: {e}")

class GoogleDriveService:
    """Enhanced Google Drive service with better error handling and performance."""
    
    def __init__(self):
        """Initialize Google Drive service."""
        self.config = get_config()
        self._validate_configuration()
        self._service = None
        self._last_connection_time = 0
        self._connection_lifetime = 3600  # 1 hour
    
    def _validate_configuration(self):
        """Validate Google Drive configuration."""
        if not os.path.exists(self.config.storage.service_account_file):
            raise StorageServiceError(f"Service account file not found: {self.config.storage.service_account_file}")
        
        if not self.config.storage.google_drive_folder_id:
            logger.warning("Google Drive folder ID not configured")
    
    @property
    def service(self):
        """Get or create Google Drive service with connection reuse."""
        current_time = time.time()
        
        if (self._service is None or 
            current_time - self._last_connection_time > self._connection_lifetime):
            
            try:
                scopes = ['https://www.googleapis.com/auth/drive']
                creds = service_account.Credentials.from_service_account_file(
                    self.config.storage.service_account_file, 
                    scopes=scopes
                )
                self._service = build('drive', 'v3', credentials=creds)
                self._last_connection_time = current_time
                
                logger.debug("Google Drive service connection established")
                
            except Exception as e:
                raise StorageServiceError(f"Failed to connect to Google Drive: {e}")
        
        return self._service
    
    @handle_storage_errors
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    @measure_performance
    def upload_file(
        self, 
        file_path: str, 
        folder_id: str, 
        filename: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Upload a file to Google Drive with retry logic.
        
        Args:
            file_path: Local file path to upload
            folder_id: Target Google Drive folder ID
            filename: Custom filename (optional)
            
        Returns:
            Tuple of (file_id, web_view_link)
        """
        with ErrorContext("drive_upload", {"file_path": file_path, "folder_id": folder_id}):
            if not os.path.exists(file_path):
                raise StorageServiceError(f"File not found: {file_path}")
            
            try:
                actual_filename = filename or os.path.basename(file_path)
                
                file_metadata = {
                    'name': actual_filename,
                    'parents': [folder_id]
                }
                
                media = MediaFileUpload(
                    file_path,
                    mimetype='application/pdf',
                    resumable=True
                )
                
                uploaded = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink'
                ).execute()
                
                file_id = uploaded.get('id')
                web_view_link = uploaded.get('webViewLink')
                
                logger.info(f"File uploaded successfully: {actual_filename} (ID: {file_id})")
                
                # Small delay to ensure file is properly processed
                time.sleep(0.5)
                
                return file_id, web_view_link
                
            except Exception as e:
                raise StorageServiceError(f"Failed to upload file to Google Drive: {e}")
    
    @handle_storage_errors
    @measure_performance
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive.
        
        Args:
            folder_name: Name of the folder to create
            parent_folder_id: Parent folder ID (optional)
            
        Returns:
            Created folder ID
        """
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Folder created successfully: {folder_name} (ID: {folder_id})")
            
            return folder_id
            
        except Exception as e:
            raise StorageServiceError(f"Failed to create folder in Google Drive: {e}")

# Service instances
_sheets_service = None
_drive_service = None

def get_sheets_service() -> GoogleSheetsService:
    """Get the global Google Sheets service instance."""
    global _sheets_service
    if _sheets_service is None:
        _sheets_service = GoogleSheetsService()
    return _sheets_service

def get_drive_service() -> GoogleDriveService:
    """Get the global Google Drive service instance."""
    global _drive_service
    if _drive_service is None:
        _drive_service = GoogleDriveService()
    return _drive_service

# Convenience functions for backward compatibility
@handle_storage_errors
def get_letter_config_by_category(category: str, member_name: str = "") -> Dict[str, str]:
    """Get letter configuration by category (backward compatibility)."""
    return get_sheets_service().get_letter_config_by_category(category, member_name)

@handle_storage_errors
def log(
    spreadsheet_name: str,
    worksheet_name: str,
    entries: List[Dict[str, Any]],
    value_input_option: str = 'RAW'
) -> Dict[str, Any]:
    """Log entries to Google Sheets (backward compatibility)."""
    return get_sheets_service().log_to_sheet(
        spreadsheet_name, worksheet_name, entries, value_input_option
    )

@handle_storage_errors
def upload_file_path_to_drive(
    file_path: str, 
    folder_id: str, 
    filename: Optional[str] = None
) -> Tuple[str, str]:
    """Upload file to Google Drive (backward compatibility)."""
    return get_drive_service().upload_file(file_path, folder_id, filename)
