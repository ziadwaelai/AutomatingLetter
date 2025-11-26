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
    
    def upload_file_to_drive(self, file_path: str, folder_id: str, filename: Optional[str] = None, mimetype: str = 'application/pdf') -> Tuple[str, str]:
        """
        Upload a file to Google Drive and return its ID and web view link.

        Args:
            file_path: Path to the file to upload
            folder_id: Google Drive folder ID
            filename: Custom filename (optional)
            mimetype: MIME type of the file (default: 'application/pdf')

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
                mimetype=mimetype,
                resumable=True
            )
            
            # Upload file
            uploaded = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()

            file_id = uploaded['id']

            # Make file publicly accessible (anyone with link can view)
            try:
                permission = {
                    'type': 'anyone',
                    'role': 'writer'
                }
                drive_service.permissions().create(
                    fileId=file_id,
                    body=permission
                ).execute()
                logger.info(f"File made public: {filename} (ID: {file_id})")
            except Exception as perm_error:
                logger.warning(f"Could not make file public (file still uploaded): {perm_error}")

            # Small delay to ensure file is ready
            time.sleep(0.5)

            logger.info(f"File uploaded to Drive: {filename} (ID: {file_id})")
            return file_id, uploaded['webViewLink']
            
        except Exception as e:
            logger.error(f"Error uploading file to Drive: {e}")
            raise
    
    def log_to_sheet(self, log_entry: Dict[str, Any], spreadsheet_name: str = "AI Letter Generating", 
                     worksheet_name: str = "Submissions") -> Dict[str, Any]:
        """
        Log entry to Google Sheets by spreadsheet name.
        
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
    
    def log_to_sheet_by_id(self, sheet_id: str, log_entry: Dict[str, Any], 
                           worksheet_name: str = "Submissions") -> Dict[str, Any]:
        """
        Log entry to Google Sheets by sheet ID.
        
        Args:
            sheet_id: Google Sheet ID
            log_entry: Dictionary containing log data
            worksheet_name: Name of the worksheet
            
        Returns:
            Result dictionary
        """
        try:
            return self.sheets_service.log_entries_by_id(
                sheet_id=sheet_id,
                worksheet_name=worksheet_name,
                entries=[log_entry]
            )
        except Exception as e:
            logger.error(f"Error logging to sheet {sheet_id}: {e}")
            raise
    
    def save_letter_to_drive_and_log(self, 
                                     letter_file_path: str,
                                     letter_content: str,
                                     letter_type: str,
                                     recipient: str,
                                     title: str,
                                     is_first: bool,
                                     sheet_id: str,
                                     letter_id: str,
                                     user_email: str,
                                     folder_id: str = None) -> Dict[str, Any]:
        """
        Complete workflow: Upload PDF to Drive and log to sheets.
        
        Args:
            letter_file_path: Path to the PDF file
            letter_content: Text content of the letter
            letter_type: Category/type of letter
            recipient: Letter recipient
            title: Letter title
            is_first: Whether this is first communication
            sheet_id: Google Sheet ID for logging (from JWT token)
            letter_id: Unique letter ID
            user_email: User email from JWT token (for Created_by field)
            folder_id: Optional Google Drive folder ID (if None, use from environment)
            
        Returns:
            Result dictionary with file info and log result
        """
        try:
            # Validate folder_id is provided (required for Drive upload)
            if folder_id is None:
                error_msg = "folder_id (google_drive_id from JWT token) is required for Drive upload"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg,
                    "file_id": None,
                    "file_url": None,
                    "letter_id": letter_id
                }
            
            # Upload to Drive
            filename = f"{title}_{letter_id}.pdf" if title != 'undefined' else f"letter_{letter_id}.pdf"

            try:
                file_id, file_url = self.upload_file_to_drive(letter_file_path, folder_id, filename, mimetype='application/pdf')
            except Exception as upload_error:
                logger.error(f"Failed to upload letter {letter_id} to Drive: {upload_error}")
                return {
                    "status": "error",
                    "message": f"Drive upload failed: {str(upload_error)}",
                    "file_id": None,
                    "file_url": None,
                    "letter_id": letter_id
                }
            
            # Prepare log entry matching Submissions sheet columns
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = {
                "ID": letter_id,
                "Timestamp": timestamp,
                "Created_by": user_email,
                "Letter_type": letter_type,
                "Recipient_name": recipient,
                "Subject": title,
                "Letter_content": letter_content,
                "Is_new_letter": "Yes" if is_first else "No",
                "Review_status": "Pending",
                "Review_notes": "",
                "Reviewer_email": "",
                "Final_letter_url": file_url,
                "Send_status": "Not Sent",
                "Token_usage": "",
                "Cost_usd": ""
            }
            
            # Log to sheet using sheet_id
            log_result = self.log_to_sheet_by_id(sheet_id, log_entry)
            
            logger.info(f"Successfully archived letter {letter_id} to Drive and logged to sheet {sheet_id}")
            
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

    def save_letter_to_drive_and_log_docx(self,
                                          letter_file_path: str,
                                          letter_content: str,
                                          letter_type: str,
                                          recipient: str,
                                          title: str,
                                          is_first: bool,
                                          sheet_id: str,
                                          letter_id: str,
                                          user_email: str,
                                          folder_id: str = None) -> Dict[str, Any]:
        """
        Complete workflow: Upload DOCX to Drive and log to sheets.
        Similar to save_letter_to_drive_and_log but for DOCX files.

        Args:
            letter_file_path: Path to the DOCX file
            letter_content: Text content of the letter
            letter_type: Category/type of letter
            recipient: Letter recipient
            title: Letter title
            is_first: Whether this is first communication
            sheet_id: Google Sheet ID for logging (from JWT token)
            letter_id: Unique letter ID
            user_email: User email from JWT token (for Created_by field)
            folder_id: Optional Google Drive folder ID (if None, use from environment)

        Returns:
            Result dictionary with file info and log result
        """
        try:
            # Validate folder_id is provided (required for Drive upload)
            if folder_id is None:
                error_msg = "folder_id (google_drive_id from JWT token) is required for Drive upload"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg,
                    "file_id": None,
                    "file_url": None,
                    "letter_id": letter_id
                }

            # Upload to Drive with DOCX mimetype
            filename = f"{title}_{letter_id}.docx" if title != 'undefined' else f"letter_{letter_id}.docx"

            try:
                file_id, file_url = self.upload_file_to_drive(
                    letter_file_path,
                    folder_id,
                    filename,
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
            except Exception as upload_error:
                logger.error(f"Failed to upload DOCX letter {letter_id} to Drive: {upload_error}")
                return {
                    "status": "error",
                    "message": f"Drive upload failed: {str(upload_error)}",
                    "file_id": None,
                    "file_url": None,
                    "letter_id": letter_id
                }

            # Prepare log entry matching Submissions sheet columns
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = {
                "ID": letter_id,
                "Timestamp": timestamp,
                "Created_by": user_email,
                "Letter_type": letter_type,
                "Recipient_name": recipient,
                "Subject": title,
                "Letter_content": letter_content,
                "Is_new_letter": "Yes" if is_first else "No",
                "Review_status": "Pending",
                "Review_notes": "",
                "Reviewer_email": "",
                "Final_letter_url": file_url,
                "Send_status": "Not Sent",
                "Token_usage": "",
                "Cost_usd": ""
            }

            # Log to sheet using sheet_id
            log_result = self.log_to_sheet_by_id(sheet_id, log_entry)

            logger.info(f"Successfully archived DOCX letter {letter_id} to Drive and logged to sheet {sheet_id}")

            return {
                "status": "success",
                "file_id": file_id,
                "file_url": file_url,
                "log_result": log_result,
                "filename": filename
            }

        except Exception as e:
            error_message = f"Error saving DOCX letter to Drive and logging: {str(e)}"
            logger.error(error_message)
            return {
                "status": "error",
                "message": error_message
            }

    def update_letter_pdf_and_log(self,
                                  letter_id: str,
                                  new_content: str,
                                  folder_id: str,
                                  template: str = "default_template",
                                  spreadsheet_name: str = "AI Letter Generating",
                                  worksheet_name: str = "Submissions") -> Dict[str, Any]:
        """
        Update an existing letter: regenerate PDF, replace old file in Drive, and update Google Sheets.
        
        Args:
            letter_id: ID of the letter to update
            new_content: New letter content
            folder_id: Google Drive folder ID
            template: Template name for PDF generation
            spreadsheet_name: Name of the spreadsheet
            worksheet_name: Name of the worksheet
            
        Returns:
            Result dictionary with file info and update result
        """
        try:
            from .enhanced_pdf_service import get_enhanced_pdf_service
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            # First, get the current file URL from Google Sheets to extract the old file ID
            try:
                with self.sheets_service.get_client_context() as client:
                    worksheet = client.open(spreadsheet_name).worksheet(worksheet_name)
                    all_values = worksheet.get_all_values()
                    headers = all_values[0]
                    header_map = {h.strip(): idx for idx, h in enumerate(headers)}

                    old_file_url = None
                    old_file_id = None
                    original_filename = None

                    # Find the current row and get the old file URL
                    if "ID" in header_map and "URL" in header_map:
                        id_col_index = header_map["ID"]
                        url_col_index = header_map["URL"]

                        for row in all_values[1:]:
                            if id_col_index < len(row) and row[id_col_index].strip() == letter_id.strip():
                                if url_col_index < len(row):
                                    old_file_url = row[url_col_index].strip()
                                    # Extract file ID from Google Drive URL
                                    if "/d/" in old_file_url:
                                        old_file_id = old_file_url.split("/d/")[1].split("/")[0]
                                        logger.info(f"Found old file ID: {old_file_id}")
                                    break

                    # Get original filename from Drive if we have the file ID
                    if old_file_id:
                        try:
                            creds = service_account.Credentials.from_service_account_file(
                                self.service_account_file, scopes=self.scopes
                            )
                            drive_service = build('drive', 'v3', credentials=creds)

                            # Get the original filename
                            file_metadata = drive_service.files().get(fileId=old_file_id, fields='name').execute()
                            original_filename = file_metadata.get('name')
                            logger.info(f"Original filename: {original_filename}")

                        except Exception as e:
                            logger.warning(f"Could not get original filename: {e}")
                            original_filename = f"letter_{letter_id}.pdf"

            except Exception as e:
                logger.warning(f"Could not retrieve old file info: {e}")
                original_filename = f"letter_{letter_id}.pdf"
            
            # Generate new PDF
            pdf_service = get_enhanced_pdf_service()
            pdf_result = pdf_service.generate_pdf(
                title=letter_id,  # Use just the ID for cleaner filename
                content=new_content,
                template_name=template
            )
            
            logger.info(f"New PDF generated for letter ID {letter_id}: {pdf_result.filename}")
            
            # Delete old file from Drive if we found it
            if old_file_id:
                try:
                    creds = service_account.Credentials.from_service_account_file(
                        self.service_account_file, scopes=self.scopes
                    )
                    drive_service = build('drive', 'v3', credentials=creds)
                    drive_service.files().delete(fileId=old_file_id).execute()
                    logger.info(f"Deleted old file from Drive: {old_file_id}")
                except Exception as e:
                    logger.warning(f"Could not delete old file {old_file_id}: {e}")
            
            # Upload new PDF with original filename (or generate one if not found)
            filename = original_filename if original_filename else f"letter_{letter_id}.pdf"
            file_id, file_url = self.upload_file_to_drive(pdf_result.file_path, folder_id, filename)
            
            # Update the row in Google Sheets with new content and URL
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updates = {
                "Content": new_content,
                "URL": file_url,
                "Timestamp": timestamp  # Update timestamp to reflect when it was updated
            }
            
            update_result = self.sheets_service.update_row_by_id(
                spreadsheet_name=spreadsheet_name,
                worksheet_name=worksheet_name,
                letter_id=letter_id,
                updates=updates
            )
            
            # Clean up temporary PDF file
            try:
                self.cleanup_temp_file(pdf_result.file_path)
            except Exception as cleanup_error:
                logger.warning(f"Error cleaning up temporary file for {letter_id}: {cleanup_error}")
            
            logger.info(f"Successfully updated letter {letter_id} - replaced PDF in Drive and updated sheet entry")
            
            return {
                "status": "success",
                "letter_id": letter_id,
                "file_id": file_id,
                "file_url": file_url,
                "filename": filename,
                "old_file_deleted": old_file_id is not None,
                "old_file_id": old_file_id,
                "update_result": update_result,
                "pdf_info": {
                    "pdf_id": pdf_result.pdf_id,
                    "file_size": pdf_result.file_size,
                    "generated_at": pdf_result.generated_at.isoformat()
                }
            }
            
        except Exception as e:
            error_message = f"Error updating letter PDF and log for ID {letter_id}: {str(e)}"
            logger.error(error_message)
            return {
                "status": "error",
                "letter_id": letter_id,
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
