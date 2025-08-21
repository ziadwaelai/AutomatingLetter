"""
Exception handling utilities for the AutomatingLetter application.
Custom exceptions and error handling decorators.
"""

import logging
import traceback
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

# Custom Exceptions
class AutomatingLetterException(Exception):
    """Base exception for AutomatingLetter application."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.timestamp = datetime.now()

class ConfigurationError(AutomatingLetterException):
    """Raised when there's a configuration error."""
    pass

class ValidationError(AutomatingLetterException):
    """Raised when input validation fails."""
    pass

class AIServiceError(AutomatingLetterException):
    """Raised when AI service encounters an error."""
    pass

class StorageServiceError(AutomatingLetterException):
    """Raised when storage service encounters an error."""
    pass

class SessionError(AutomatingLetterException):
    """Raised when session management encounters an error."""
    pass

class LetterGenerationError(AutomatingLetterException):
    """Raised when letter generation fails."""
    pass

class PDFGenerationError(AutomatingLetterException):
    """Raised when PDF generation fails."""
    pass

class GoogleServicesError(AutomatingLetterException):
    """Raised when Google services encounter an error."""
    pass

class RateLimitError(AutomatingLetterException):
    """Raised when rate limits are exceeded."""
    pass

class AuthenticationError(AutomatingLetterException):
    """Raised when authentication fails."""
    pass

# Error Handler Decorators
def handle_exceptions(
    default_return=None,
    log_error: bool = True,
    reraise: bool = True,
    custom_message: Optional[str] = None
):
    """
    Decorator to handle exceptions in functions.
    
    Args:
        default_return: Value to return if exception occurs and reraise=False
        log_error: Whether to log the error
        reraise: Whether to reraise the exception
        custom_message: Custom error message to log
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = custom_message or f"Error in {func.__name__}: {str(e)}"
                
                if log_error:
                    logger.error(error_msg, exc_info=True)
                
                if reraise:
                    raise
                else:
                    return default_return
        return wrapper
    return decorator

def handle_ai_service_errors(func: Callable) -> Callable:
    """Decorator specifically for handling AI service errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_details = {
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
                "original_error": str(e),
                "error_type": type(e).__name__
            }
            
            # Check for specific error types
            if "rate limit" in str(e).lower():
                raise RateLimitError(
                    "AI service rate limit exceeded",
                    error_code="RATE_LIMIT_EXCEEDED",
                    details=error_details
                )
            elif "authentication" in str(e).lower() or "api key" in str(e).lower():
                raise AuthenticationError(
                    "AI service authentication failed",
                    error_code="AUTH_FAILED",
                    details=error_details
                )
            else:
                raise AIServiceError(
                    f"AI service error: {str(e)}",
                    error_code="AI_SERVICE_ERROR",
                    details=error_details
                )
    return wrapper

def handle_storage_errors(func: Callable) -> Callable:
    """Decorator specifically for handling storage errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_details = {
                "function": func.__name__,
                "original_error": str(e),
                "error_type": type(e).__name__
            }
            
            if "permission" in str(e).lower() or "access" in str(e).lower():
                raise StorageServiceError(
                    "Storage access denied",
                    error_code="STORAGE_ACCESS_DENIED",
                    details=error_details
                )
            elif "not found" in str(e).lower():
                raise StorageServiceError(
                    "Storage resource not found",
                    error_code="STORAGE_NOT_FOUND",
                    details=error_details
                )
            else:
                raise StorageServiceError(
                    f"Storage service error: {str(e)}",
                    error_code="STORAGE_ERROR",
                    details=error_details
                )
    return wrapper

def handle_session_errors(func: Callable) -> Callable:
    """Decorator specifically for handling session errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_details = {
                "function": func.__name__,
                "original_error": str(e),
                "error_type": type(e).__name__
            }
            
            if "not found" in str(e).lower() or "expired" in str(e).lower():
                raise SessionError(
                    "Session not found or expired",
                    error_code="SESSION_EXPIRED",
                    details=error_details
                )
            else:
                raise SessionError(
                    f"Session error: {str(e)}",
                    error_code="SESSION_ERROR",
                    details=error_details
                )
    return wrapper

def service_error_handler(func: Callable) -> Callable:
    """
    General purpose service error handler decorator.
    Provides comprehensive error handling for service methods.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AutomatingLetterException:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Convert other exceptions to our custom ones
            error_details = {
                "function": func.__name__,
                "module": func.__module__,
                "original_error": str(e),
                "error_type": type(e).__name__
            }
            
            # Try to determine the appropriate error type based on context
            if "ai" in func.__name__.lower() or "gpt" in str(e).lower():
                raise AIServiceError(
                    f"AI service error in {func.__name__}: {str(e)}",
                    error_code="AI_SERVICE_ERROR",
                    details=error_details
                )
            elif "google" in func.__name__.lower() or "drive" in func.__name__.lower():
                raise GoogleServicesError(
                    f"Google services error in {func.__name__}: {str(e)}",
                    error_code="GOOGLE_SERVICES_ERROR",
                    details=error_details
                )
            elif "pdf" in func.__name__.lower():
                raise PDFGenerationError(
                    f"PDF generation error in {func.__name__}: {str(e)}",
                    error_code="PDF_GENERATION_ERROR",
                    details=error_details
                )
            elif "session" in func.__name__.lower() or "chat" in func.__name__.lower():
                raise SessionError(
                    f"Session error in {func.__name__}: {str(e)}",
                    error_code="SESSION_ERROR",
                    details=error_details
                )
            else:
                # Generic service error
                raise AutomatingLetterException(
                    f"Service error in {func.__name__}: {str(e)}",
                    error_code="SERVICE_ERROR",
                    details=error_details
                )
    return wrapper

# Error Context Manager
class ErrorContext:
    """Context manager for error handling with additional context."""
    
    def __init__(self, operation: str, context: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.context = context or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        logger.debug(f"Starting operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            logger.debug(f"Operation completed successfully: {self.operation} ({duration:.2f}s)")
        else:
            error_info = {
                "operation": self.operation,
                "duration_seconds": duration,
                "context": self.context,
                "error_type": exc_type.__name__,
                "error_message": str(exc_val)
            }
            
            logger.error(f"Operation failed: {self.operation}", extra=error_info)
        
        return False  # Don't suppress exceptions

# Error Response Builders
def build_error_response(
    error: Exception,
    include_traceback: bool = False,
    include_details: bool = True
) -> Dict[str, Any]:
    """
    Build a standardized error response dictionary.
    
    Args:
        error: The exception that occurred
        include_traceback: Whether to include stack trace
        include_details: Whether to include error details
        
    Returns:
        Dictionary with error information
    """
    response = {
        "error": str(error),
        "error_type": type(error).__name__,
        "timestamp": datetime.now().isoformat()
    }
    
    if isinstance(error, AutomatingLetterException):
        response["error_code"] = error.error_code
        if include_details and error.details:
            response["details"] = error.details
    
    if include_traceback:
        response["traceback"] = traceback.format_exc()
    
    return response

def log_error_with_context(
    error: Exception,
    context: Dict[str, Any],
    level: str = "ERROR"
):
    """
    Log error with additional context information.
    
    Args:
        error: The exception that occurred
        context: Additional context information
        level: Logging level (ERROR, WARNING, etc.)
    """
    log_level = getattr(logging, level.upper())
    
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context
    }
    
    if isinstance(error, AutomatingLetterException):
        error_info["error_code"] = error.error_code
        error_info["error_details"] = error.details
    
    logger.log(log_level, f"Error occurred: {str(error)}", extra=error_info)

# Validation Utilities
def validate_and_raise(condition: bool, message: str, error_class=ValidationError, **kwargs):
    """
    Validate condition and raise error if false.
    
    Args:
        condition: Condition to validate
        message: Error message if condition is false
        error_class: Exception class to raise
        **kwargs: Additional arguments for exception
    """
    if not condition:
        raise error_class(message, **kwargs)

def safe_execute(func: Callable, *args, default=None, log_errors: bool = True, **kwargs):
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        *args: Function arguments
        default: Default value to return on error
        log_errors: Whether to log errors
        **kwargs: Function keyword arguments
        
    Returns:
        Function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Error executing {func.__name__}: {e}")
        return default

# Error Recovery
class ErrorRecovery:
    """Utility class for error recovery strategies."""
    
    @staticmethod
    def retry_on_failure(
        func: Callable,
        max_attempts: int = 3,
        delay: float = 1.0,
        exceptions: tuple = (Exception,)
    ):
        """
        Retry function execution on failure.
        
        Args:
            func: Function to retry
            max_attempts: Maximum number of attempts
            delay: Delay between attempts in seconds
            exceptions: Exceptions to catch and retry on
            
        Returns:
            Function result if successful
            
        Raises:
            Last exception if all attempts fail
        """
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return func()
            except exceptions as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    import time
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_attempts} attempts failed")
        
        raise last_exception
