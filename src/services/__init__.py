"""Services package initialization."""

from .letter_generator import ArabicLetterGenerationService, LetterGenerationContext, get_letter_service
from .google_services import (
    GoogleSheetsService,
    GoogleDriveService,
    get_sheets_service,
    get_drive_service,
    get_letter_config_by_category,
    log,
    upload_file_path_to_drive
)
from .enhanced_pdf_service import EnhancedPDFService, get_enhanced_pdf_service
from .enhanced_doc_service import EnhancedDOCXService, get_enhanced_docx_service
from .drive_logger import DriveLoggerService, get_drive_logger_service
from .chat_service import ChatService, get_chat_service
from .memory_service import MemoryService, get_memory_service
from .session_storage import SessionStorage, get_session_storage
from .session_manager import SessionManager, get_session_manager

__all__ = [
    # Letter Generation
    "ArabicLetterGenerationService",
    "LetterGenerationContext", 
    "get_letter_service",
    
    # Google Services
    "GoogleSheetsService",
    "GoogleDriveService",
    "get_sheets_service",
    "get_drive_service",
    
    # PDF Services
    "EnhancedPDFService",
    "get_enhanced_pdf_service",

    # DOCX Services
    "EnhancedDOCXService",
    "get_enhanced_docx_service",
    
    # Drive Logger
    "DriveLoggerService",
    "get_drive_logger_service",
    
    # Chat Services
    "ChatService",
    "get_chat_service",
    
    # Memory Services
    "MemoryService",
    "get_memory_service",
    
    # Session Services
    "SessionStorage",
    "get_session_storage",
    "SessionManager", 
    "get_session_manager",
    
    # Helper Functions
    "get_letter_config_by_category",
    "log",
    "upload_file_path_to_drive"
]
