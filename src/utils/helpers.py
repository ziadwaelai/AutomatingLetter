"""
Utility functions for the AutomatingLetter application.
Common helpers and utility functions used across the application.
"""

import os
import time
import uuid
import hashlib
import logging
import functools
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from contextlib import contextmanager
import threading
import jwt
from flask import request

logger = logging.getLogger(__name__)

# ID Generation
def generate_letter_id(prefix: str = "LET") -> str:
    """
    Generate a unique letter ID in the format PREFIX-YYYYMMDD-XXXXX.
    
    Args:
        prefix: Prefix for the ID (default: LET)
        
    Returns:
        Unique letter ID string
    """
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = str(uuid.uuid4().int)[-5:]  # Last 5 digits of UUID
    return f"{prefix}-{date_part}-{random_part}"

def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())

# Date and Time Utilities
def get_current_arabic_date() -> str:
    """Get current date in Arabic format."""
    months_arabic = {
        1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
        5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
        9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
    }
    
    now = datetime.now()
    arabic_numerals = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
    
    day = str(now.day).translate(arabic_numerals)
    month = months_arabic[now.month]
    year = str(now.year).translate(arabic_numerals)
    
    return f"{day} {month} {year}"

def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format datetime for logging and display."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_datetime(date_string: str) -> Optional[datetime]:
    """Parse datetime string safely."""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    logger.warning(f"Could not parse datetime: {date_string}")
    return None

# Text Processing
def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize text input by removing unwanted characters and limiting length.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove null bytes and control characters except newlines and tabs
    sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    
    # Normalize whitespace
    sanitized = ' '.join(sanitized.split())
    
    # Limit length if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length-3] + "..."
    
    return sanitized

def extract_preview(text: str, max_length: int = 200) -> str:
    """Extract a preview from text content."""
    if not text:
        return ""
    
    text = sanitize_text(text)
    if len(text) <= max_length:
        return text
    
    # Try to break at word boundary
    preview = text[:max_length]
    last_space = preview.rfind(' ')
    
    if last_space > max_length * 0.8:  # If space is not too far back
        preview = preview[:last_space]
    
    return preview + "..."

def validate_arabic_text(text: str) -> bool:
    """Check if text contains Arabic characters."""
    if not text:
        return False
    
    arabic_range = range(0x0600, 0x06FF + 1)
    return any(ord(char) in arabic_range for char in text)

# Performance Monitoring
class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, operation_name: str = "Operation"):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.elapsed_time()
        logger.info(f"{self.operation_name} completed in {duration:.3f}s")
        
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time
    
    def elapsed(self) -> float:
        """Alias for elapsed_time() for convenience."""
        return self.elapsed_time()

def measure_performance(func: Callable) -> Callable:
    """Decorator to measure function performance."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func.__name__} executed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.3f}s: {e}")
            raise
    return wrapper

# Retry Logic
def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_multiplier: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay = base_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s")
                    time.sleep(delay)
                    delay = min(delay * backoff_multiplier, max_delay)
            
            raise last_exception
        return wrapper
    return decorator

# File and Path Utilities
def ensure_directory(path: str) -> str:
    """Ensure directory exists, create if it doesn't."""
    os.makedirs(path, exist_ok=True)
    return path

def safe_file_name(name: str) -> str:
    """Convert string to safe filename."""
    # Remove/replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        name = name.replace(char, '_')
    
    # Limit length
    if len(name) > 200:
        name = name[:200]
    
    return name.strip()

def get_file_hash(file_path: str) -> str:
    """Get MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}")
        return ""

# Thread Safety Utilities
class ThreadSafeCounter:
    """Thread-safe counter implementation."""
    
    def __init__(self, initial_value: int = 0):
        self._value = initial_value
        self._lock = threading.Lock()
    
    def increment(self) -> int:
        """Increment counter and return new value."""
        with self._lock:
            self._value += 1
            return self._value
    
    def decrement(self) -> int:
        """Decrement counter and return new value."""
        with self._lock:
            self._value -= 1
            return self._value
    
    @property
    def value(self) -> int:
        """Get current counter value."""
        with self._lock:
            return self._value

@contextmanager
def timeout_context(seconds: float):
    """Context manager for operations with timeout."""
    start_time = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start_time
        if elapsed > seconds:
            logger.warning(f"Operation took {elapsed:.2f}s, exceeded timeout of {seconds}s")

# Data Validation
def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """
    Validate that required fields are present in data.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        
    Returns:
        List of missing field names
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
            missing_fields.append(field)
    return missing_fields

def clean_dict(data: Dict[str, Any], remove_none: bool = True, remove_empty_strings: bool = True) -> Dict[str, Any]:
    """
    Clean dictionary by removing None values and empty strings.
    
    Args:
        data: Dictionary to clean
        remove_none: Remove None values
        remove_empty_strings: Remove empty string values
        
    Returns:
        Cleaned dictionary
    """
    cleaned = {}
    for key, value in data.items():
        if remove_none and value is None:
            continue
        if remove_empty_strings and isinstance(value, str) and not value.strip():
            continue
        cleaned[key] = value
    return cleaned

# Logging Utilities
def log_function_call(func: Callable) -> Callable:
    """Decorator to log function calls with arguments."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Don't log sensitive data
        safe_kwargs = {k: "***" if "password" in k.lower() or "key" in k.lower() or "token" in k.lower() else v 
                      for k, v in kwargs.items()}
        
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={safe_kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed with error: {e}")
            raise
    
    return wrapper

def setup_module_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Setup a logger for a specific module."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


# JWT Token Utilities
def extract_token_from_request() -> Optional[str]:
    """
    Extract JWT token from request Authorization header.
    
    Returns:
        Token string if found, None otherwise
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    # Support both "Bearer <token>" and just "<token>"
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1]
    elif len(parts) == 1:
        return parts[0]
    
    return None


def decode_jwt_token(token: str, secret: str, algorithm: str = "HS256") -> Optional[Dict[str, Any]]:
    """
    Decode JWT token and return payload.
    
    Args:
        token: JWT token string
        secret: Secret key for decoding
        algorithm: JWT algorithm (default: HS256)
    
    Returns:
        Decoded payload dictionary if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error decoding JWT token: {e}")
        return None


def get_user_from_token() -> Optional[Dict[str, Any]]:
    """
    Extract and decode JWT token from current request, return user info.
    
    Returns:
        Dictionary with user info (sheet_id, client_id, user, etc.) if valid, None otherwise
    """
    from ..config import get_config
    
    # Extract token from request
    token = extract_token_from_request()
    if not token:
        logger.warning("No authorization token found in request")
        return None
    
    # Get config for JWT secret
    config = get_config()
    
    # Decode token
    payload = decode_jwt_token(token, config.auth.jwt_secret, config.auth.jwt_algorithm)
    if not payload:
        return None
    
    return payload


def require_auth(f: Callable) -> Callable:
    """
    Decorator to require JWT authentication for an endpoint.
    Adds 'user_info' to kwargs containing decoded token payload.
    
    Usage:
        @require_auth
        def my_endpoint(user_info):
            sheet_id = user_info['sheet_id']
            ...
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user_info = get_user_from_token()
        
        if not user_info:
            from flask import jsonify
            return jsonify({
                "status": "error",
                "message": "غير مصرح",
                "error": "يجب تسجيل الدخول للوصول إلى هذه الصفحة"
            }), 401
        
        # Add user_info to kwargs
        kwargs['user_info'] = user_info
        return f(*args, **kwargs)
    
    return decorated_function
