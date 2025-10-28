"""
Configuration Management Module
Centralized configuration for the AutomatingLetter application.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Import will happen later to avoid circular imports
# from ..utils.log_manager import CustomTimedRotatingHandler

# Load environment variables
load_dotenv()

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    spreadsheet_name: str = "AI Letter Generating"
    submissions_worksheet: str = "Submissions"
    logs_worksheet: str = "Logs"
    letters_spreadsheet: str = "Letters"
    instructions_worksheet: str = "Instructions"
    ideal_worksheet: str = "Ideal"
    info_worksheet: str = "Info"

@dataclass
class AIConfig:
    """AI model configuration settings."""
    model_name: str = "gpt-4.1"
    temperature: float = 0.2
    timeout: int = 30
    max_retries: int = 3
    max_tokens: Optional[int] = None
    
    def __post_init__(self):
        """Validate AI configuration."""
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")

@dataclass
class ChatConfig:
    """Interactive chat configuration settings."""
    memory_window: int = 10
    session_timeout_minutes: int = 60  # Changed to 1 hour (60 minutes)
    cleanup_interval_minutes: int = 5
    max_concurrent_sessions: int = 100
    
    def __post_init__(self):
        """Validate chat configuration."""
        if self.memory_window <= 0:
            raise ValueError("Memory window must be positive")
        if self.session_timeout_minutes <= 0:
            raise ValueError("Session timeout must be positive")

@dataclass
class StorageConfig:
    """Storage configuration settings."""
    google_drive_folder_id: str = field(default_factory=lambda: os.getenv("GOOGLE_DRIVE_FOLDER_ID", ""))
    service_account_file: str = "automating-letter-creations.json"
    pdf_template_dir: str = "LetterToPdf/templates"
    default_template: str = "default_template.html"
    
    def __post_init__(self):
        """Validate storage configuration."""
        if not self.google_drive_folder_id:
            logging.warning("Google Drive folder ID not configured")
        if not os.path.exists(self.service_account_file):
            raise FileNotFoundError(f"Service account file not found: {self.service_account_file}")

@dataclass
class AuthConfig:
    """Authentication configuration settings."""
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "default-jwt-secret-change-in-production"))
    jwt_algorithm: str = "HS256"
    token_expiry_hours: int = 24
    
    def __post_init__(self):
        """Validate auth configuration."""
        if not self.jwt_secret or self.jwt_secret == "default-jwt-secret-change-in-production":
            logging.warning("Using default JWT secret - change in production!")


@dataclass
class ServerConfig:
    """Server configuration settings."""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    max_content_length: int = 16 * 1024 * 1024  # 16MB
    
    def __post_init__(self):
        """Load from environment variables."""
        self.host = os.getenv("SERVER_HOST", self.host)
        self.port = int(os.getenv("SERVER_PORT", self.port))
        self.debug = os.getenv("DEBUG", "False").lower() == "true"

@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = "logs/app.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    retention_days: int = 30  # Keep logs for 30 days (1 month)
    rotation_type: str = "time"  # "time" for daily rotation, "size" for size-based

    def __post_init__(self):
        """Load from environment variables."""
        self.level = os.getenv("LOG_LEVEL", self.level).upper()
        self.retention_days = int(os.getenv("LOG_RETENTION_DAYS", self.retention_days))
        self.rotation_type = os.getenv("LOG_ROTATION_TYPE", self.rotation_type).lower()

        if self.file_path and not os.path.exists(os.path.dirname(self.file_path)):
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

class AppConfig:
    """Main application configuration."""
    
    def __init__(self):
        """Initialize configuration with validation."""
        self._validate_environment()
        
        self.database = DatabaseConfig()
        self.ai = AIConfig()
        self.chat = ChatConfig()
        self.storage = StorageConfig()
        self.auth = AuthConfig()
        self.server = ServerConfig()
        self.logging = LoggingConfig()
        
        # Security settings
        self.openai_api_key = self._get_required_env("OPENAI_API_KEY")
        self.secret_key = os.getenv("SECRET_KEY", "dev-key-change-in-production")
        self.flask_secret_key = self.secret_key  # Alias for Flask
        
        # Server settings 
        self.host = os.getenv("HOST", "localhost")
        self.port = int(os.getenv("PORT", "5000"))
        self.debug_mode = os.getenv("DEBUG_MODE", "true").lower() == "true"
        self.cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        
        # Chat settings (aliases for easier access)
        self.chat_session_timeout_minutes = int(os.getenv("CHAT_SESSION_TIMEOUT_MINUTES", self.chat.session_timeout_minutes))
        self.chat_max_memory_size = self.chat.memory_window
        
        # Logging settings
        self.log_requests = os.getenv("LOG_REQUESTS", "true").lower() == "true"
        
        # Feature flags
        self.enable_chat = os.getenv("ENABLE_CHAT", "true").lower() == "true"
        self.enable_pdf_generation = os.getenv("ENABLE_PDF", "true").lower() == "true"
        self.enable_drive_storage = os.getenv("ENABLE_DRIVE", "true").lower() == "true"
        self.legacy_endpoints = os.getenv("ENABLE_LEGACY_ENDPOINTS", "true").lower() == "true"
        
        # Performance settings
        self.max_workers = int(os.getenv("MAX_WORKERS", "4"))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    def _validate_environment(self):
        """Validate required environment variables."""
        required_vars = ["OPENAI_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
    
    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error."""
        value = os.getenv(key)
        if not value:
            raise EnvironmentError(f"Required environment variable {key} is not set")
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        return {
            "database": self.database.__dict__,
            "ai": {k: v for k, v in self.ai.__dict__.items() if k != "api_key"},
            "chat": self.chat.__dict__,
            "storage": {k: v for k, v in self.storage.__dict__.items() if "key" not in k.lower()},
            "server": self.server.__dict__,
            "logging": self.logging.__dict__,
            "features": {
                "chat_enabled": self.enable_chat,
                "pdf_enabled": self.enable_pdf_generation,
                "drive_enabled": self.enable_drive_storage
            }
        }
    
    def setup_logging(self):
        """Setup application logging with time-based rotation (daily, 30-day retention)."""
        from logging.handlers import TimedRotatingFileHandler

        log_level = getattr(logging, self.logging.level)
        formatter = logging.Formatter(self.logging.format)

        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Remove existing handlers to prevent duplicates on reload
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)

        # Add file handler with time-based rotation
        if self.logging.file_path:
            try:
                # Use time-based rotation (daily) to keep only last month of logs
                file_handler = TimedRotatingFileHandler(
                    self.logging.file_path,
                    when='midnight',        # Rotate at midnight (daily)
                    interval=1,             # Every 1 day
                    backupCount=self.logging.retention_days,  # Keep 30 days of logs
                    encoding='utf-8'
                )
                file_handler.setFormatter(formatter)
                file_handler.setLevel(log_level)
                root_logger.addHandler(file_handler)
            except Exception as e:
                logging.error(f"Failed to setup file logging: {e}")

        # Set specific logger levels
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("werkzeug").setLevel(logging.INFO)

# Global configuration instance
config = AppConfig()

def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return config

def reload_config() -> AppConfig:
    """Reload configuration from environment."""
    global config
    config = AppConfig()
    return config

def setup_logging():
    """Setup application logging using global config with time-based rotation."""
    from logging.handlers import TimedRotatingFileHandler

    cfg = get_config()
    log_level = getattr(logging, cfg.logging.level)
    formatter = logging.Formatter(cfg.logging.format)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to prevent duplicates on reload
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # Add file handler with time-based rotation
    if cfg.logging.file_path:
        try:
            # Use time-based rotation (daily) instead of size-based
            # This keeps logs for 30 days (1 month)
            file_handler = TimedRotatingFileHandler(
                cfg.logging.file_path,
                when='midnight',        # Rotate at midnight (daily)
                interval=1,             # Every 1 day
                backupCount=cfg.logging.retention_days,  # Keep 30 days of logs
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            root_logger.addHandler(file_handler)
            logging.info(f"Logging initialized: {cfg.logging.file_path} (time-based rotation, {cfg.logging.retention_days} day retention)")
        except Exception as e:
            logging.error(f"Failed to setup file logging: {e}")

    # Run initial log cleanup and archiving
    try:
        from ..utils.log_manager import setup_log_cleanup, setup_log_archiving
        log_dir = os.path.dirname(cfg.logging.file_path) or "logs"

        # Setup cleanup (keeps last 30 days)
        setup_log_cleanup(
            log_dir=log_dir,
            retention_days=cfg.logging.retention_days
        )

        # Setup archiving (archives logs older than 7 days)
        setup_log_archiving(
            log_dir=log_dir,
            archive_dir=os.path.join(log_dir, "archive"),
            days_before_archive=7
        )
    except Exception as e:
        logging.debug(f"Log management initialization: {e}")

    # Set specific logger levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.INFO)
