"""Utils package initialization."""

from .helpers import (
    generate_letter_id,
    generate_session_id,
    get_current_arabic_date,
    format_timestamp,
    parse_datetime,
    sanitize_text,
    extract_preview,
    validate_arabic_text,
    Timer,
    measure_performance,
    retry_with_backoff,
    ensure_directory,
    safe_file_name,
    get_file_hash,
    ThreadSafeCounter,
    timeout_context,
    validate_required_fields,
    clean_dict,
    log_function_call,
    setup_module_logger
)

from .exceptions import (
    # Custom Exceptions
    AutomatingLetterException,
    ConfigurationError,
    ValidationError,
    AIServiceError,
    StorageServiceError,
    SessionError,
    LetterGenerationError,
    PDFGenerationError,
    GoogleServicesError,
    RateLimitError,
    AuthenticationError,
    
    # Decorators
    handle_exceptions,
    handle_ai_service_errors,
    handle_storage_errors,
    handle_session_errors,
    service_error_handler,
    
    # Utilities
    ErrorContext,
    build_error_response,
    log_error_with_context,
    validate_and_raise,
    safe_execute,
    ErrorRecovery
)

__all__ = [
    # Helper functions
    "generate_letter_id",
    "generate_session_id", 
    "get_current_arabic_date",
    "format_timestamp",
    "parse_datetime",
    "sanitize_text",
    "extract_preview",
    "validate_arabic_text",
    "Timer",
    "measure_performance",
    "retry_with_backoff",
    "ensure_directory",
    "safe_file_name",
    "get_file_hash",
    "ThreadSafeCounter",
    "timeout_context",
    "validate_required_fields",
    "clean_dict",
    "log_function_call",
    "setup_module_logger",
    
    # Exceptions
    "AutomatingLetterException",
    "ConfigurationError",
    "ValidationError", 
    "AIServiceError",
    "StorageServiceError",
    "SessionError",
    "LetterGenerationError",
    "PDFGenerationError",
    "GoogleServicesError",
    "RateLimitError",
    "AuthenticationError",
    
    # Error handling
    "handle_exceptions",
    "handle_ai_service_errors",
    "handle_storage_errors", 
    "handle_session_errors",
    "service_error_handler",
    "ErrorContext",
    "build_error_response",
    "log_error_with_context",
    "validate_and_raise",
    "safe_execute",
    "ErrorRecovery"
]
