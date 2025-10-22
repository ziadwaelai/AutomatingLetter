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
from .drive_logger import DriveLoggerService, get_drive_logger_service
from .chat_service import ChatService, get_chat_service
from .memory_service import MemoryService, get_memory_service
from .session_storage import SessionStorage, get_session_storage
from .session_manager import SessionManager, get_session_manager
from .user_management_service import UserManagementService, get_user_management_service, ClientInfo

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

    # User Management Services
    "UserManagementService",
    "get_user_management_service",
    "ClientInfo",

    # Helper Functions
    "get_letter_config_by_category",
    "log",
    "upload_file_path_to_drive"
]
