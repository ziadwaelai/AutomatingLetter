"""
Google Drive Logger
Handles uploading files to Google Drive and logging to Google Sheets.
"""

import logging
import os
import tempfile
import time
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from .google_services import GoogleSheetsService

logger = logging.getLogger(__name__)

class DriveLoggerService:
    """Service for uploading files to Google Drive and logging to sheets."""
    
    def __init__(self):
        """Initialize Drive Logger service."""
        self.service_account_file = 'automating-letter-creations.json'
        self.scopes = [
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        self.sheets_service = GoogleSheetsService()
        logger.info("Drive Logger service initialized")
    
    def upload_file_to_drive(self, file_path: str, folder_id: str, filename: Optional[str] = None) -> Tuple[str, str]:
        """
        Upload a file to Google Drive and return its ID and web view link.
        
        Args:
            file_path: Path to the file to upload
            folder_id: Google Drive folder ID
            filename: Custom filename (optional)
            
        Returns:
            Tuple of (file_id, web_view_link)
        """
        try:
            # Initialize credentials and service
            creds = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=self.scopes
            )
            drive_service = build('drive', 'v3', credentials=creds)
            
            # Use provided filename or extract from path
            if filename is None:
                filename = os.path.basename(file_path)
            
            # Prepare file metadata
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            # Create media upload
            media = MediaFileUpload(
                file_path,
                mimetype='application/pdf',
                resumable=True
            )
            
            # Upload file
            uploaded = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            # Small delay to ensure file is ready
            time.sleep(0.5)
            
            logger.info(f"File uploaded to Drive: {filename} (ID: {uploaded['id']})")
            return uploaded['id'], uploaded['webViewLink']
            
        except Exception as e:
            logger.error(f"Error uploading file to Drive: {e}")
            raise
    
    def log_to_sheet(self, log_entry: Dict[str, Any], spreadsheet_name: str = "AI Letter Generating", 
                     worksheet_name: str = "Submissions") -> Dict[str, Any]:
        """
        Log entry to Google Sheets.
        
        Args:
            log_entry: Dictionary containing log data
            spreadsheet_name: Name of the spreadsheet
            worksheet_name: Name of the worksheet
            
        Returns:
            Result dictionary
        """
        try:
            return self.sheets_service.log_entries(
                spreadsheet_name=spreadsheet_name,
                worksheet_name=worksheet_name,
                entries=[log_entry]
            )
        except Exception as e:
            logger.error(f"Error logging to sheet: {e}")
            raise
    
    def save_letter_to_drive_and_log(self, 
                                     letter_file_path: str,
                                     letter_content: str,
                                     letter_type: str,
                                     recipient: str,
                                     title: str,
                                     is_first: bool,
                                     folder_id: str,
                                     letter_id: str,
                                     username: str) -> Dict[str, Any]:
        """
        Complete workflow: Upload PDF to Drive and log to sheets.
        
        Args:
            letter_file_path: Path to the PDF file
            letter_content: Text content of the letter
            letter_type: Category/type of letter
            recipient: Letter recipient
            title: Letter title
            is_first: Whether this is first communication
            folder_id: Google Drive folder ID
            letter_id: Unique letter ID
            username: Username of creator
            
        Returns:
            Result dictionary with file info and log result
        """
        try:
            # Upload to Drive
            filename = f"{title}_{letter_id}.pdf" if title != 'undefined' else f"letter_{letter_id}.pdf"
            file_id, file_url = self.upload_file_to_drive(letter_file_path, folder_id, filename)
            
            # Prepare log entry
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = {
                "Timestamp": timestamp,
                "Type of Letter": letter_type,
                "Recipient": recipient,
                "Title": title,
                "First Time?": "Yes" if is_first else "No",
                "Content": letter_content,
                "URL": file_url,
                "Revision": "في الانتظار",
                "ID": letter_id,
                "Username": username
            }
            
            # Log to sheet
            log_result = self.log_to_sheet(log_entry)
            
            logger.info(f"Successfully archived letter {letter_id} to Drive and logged to sheets")
            
            return {
                "status": "success",
                "file_id": file_id,
                "file_url": file_url,
                "log_result": log_result,
                "filename": filename
            }
            
        except Exception as e:
            error_message = f"Error saving letter to Drive and logging: {str(e)}"
            logger.error(error_message)
            return {
                "status": "error",
                "message": error_message
            }
    
    def cleanup_temp_file(self, file_path: str, max_retries: int = 3) -> None:
        """
        Clean up temporary file with retry logic.
        
        Args:
            file_path: Path to file to delete
            max_retries: Maximum number of retry attempts
        """
        for attempt in range(max_retries):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temporary file: {file_path}")
                    break
            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait before retry
                else:
                    logger.warning(f"Could not delete temporary file after {max_retries} attempts: {file_path}")
            except Exception as e:
                logger.warning(f"Error deleting temporary file {file_path}: {e}")
                break

# Service instance
_drive_logger_service = None

def get_drive_logger_service() -> DriveLoggerService:
    """Get or create drive logger service instance."""
    global _drive_logger_service
    if _drive_logger_service is None:
        _drive_logger_service = DriveLoggerService()
    return _drive_logger_service
