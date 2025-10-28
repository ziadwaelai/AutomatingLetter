"""
Log Management Module
Handles log rotation, cleanup, maintenance, archiving, and specialized logging for all operations.
Supports:
- Endpoint-specific logs
- Action logs (user operations)
- Authentication logs
- Error logs
- Automatic archiving of old logs
"""

import os
import logging
import time
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class LogCleanupManager:
    """Manages log file cleanup and rotation."""

    def __init__(self, log_dir: str = "logs", retention_days: int = 30):
        """
        Initialize log cleanup manager.

        Args:
            log_dir: Directory containing log files
            retention_days: Number of days to keep logs (default: 30 days = 1 month)
        """
        self.log_dir = log_dir
        self.retention_days = retention_days
        self.retention_seconds = retention_days * 24 * 60 * 60

    def cleanup_old_logs(self) -> int:
        """
        Delete log files older than retention period.

        Returns:
            Number of files deleted
        """
        if not os.path.exists(self.log_dir):
            return 0

        deleted_count = 0
        current_time = time.time()
        cutoff_time = current_time - self.retention_seconds

        try:
            for filename in os.listdir(self.log_dir):
                if filename.startswith('app.log') and not filename == 'app.log':
                    filepath = os.path.join(self.log_dir, filename)

                    if os.path.isfile(filepath):
                        file_mtime = os.path.getmtime(filepath)

                        # Delete if older than retention period
                        if file_mtime < cutoff_time:
                            try:
                                os.remove(filepath)
                                deleted_count += 1
                                logging.info(f"Deleted old log file: {filename}")
                            except Exception as e:
                                logging.error(f"Failed to delete log file {filename}: {e}")
        except Exception as e:
            logging.error(f"Error during log cleanup: {e}")

        return deleted_count

    def get_log_statistics(self) -> dict:
        """
        Get statistics about log files.

        Returns:
            Dictionary with log file statistics
        """
        if not os.path.exists(self.log_dir):
            return {"total_size_mb": 0, "file_count": 0, "files": []}

        total_size = 0
        file_count = 0
        files = []

        try:
            for filename in os.listdir(self.log_dir):
                if filename.startswith('app.log') or filename == 'app.log':
                    filepath = os.path.join(self.log_dir, filename)

                    if os.path.isfile(filepath):
                        file_size = os.path.getsize(filepath)
                        mtime = os.path.getmtime(filepath)
                        mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

                        total_size += file_size
                        file_count += 1

                        files.append({
                            "name": filename,
                            "size_mb": file_size / 1024 / 1024,
                            "modified": mtime_str
                        })
        except Exception as e:
            logging.error(f"Error getting log statistics: {e}")

        return {
            "total_size_mb": total_size / 1024 / 1024,
            "file_count": file_count,
            "files": sorted(files, key=lambda x: x['name'], reverse=True)
        }


class CustomTimedRotatingHandler(TimedRotatingFileHandler):
    """
    Custom timed rotating handler that also performs cleanup.
    Rotates logs daily and keeps only the last 30 days of logs.
    """

    def __init__(self, filename, when='midnight', interval=1,
                 backupCount=30, encoding=None, delay=False, utc=False):
        """
        Initialize custom timed rotating handler.

        Args:
            filename: Log file path
            when: Type of interval ('midnight' for daily rotation)
            interval: Interval for rotation (1 = every day)
            backupCount: Number of backup files to keep (30 = last month)
            encoding: File encoding
            delay: Delay file opening
            utc: Use UTC time
        """
        super().__init__(filename, when=when, interval=interval,
                        backupCount=backupCount, encoding=encoding,
                        delay=delay, utc=utc)
        self.backupCount = backupCount
        self.cleanup_manager = LogCleanupManager(
            log_dir=os.path.dirname(filename) or "logs",
            retention_days=backupCount
        )

    def doRollover(self):
        """Perform rollover and cleanup old logs."""
        super().doRollover()

        # Cleanup old logs
        try:
            deleted = self.cleanup_manager.cleanup_old_logs()
            if deleted > 0:
                logging.info(f"Log cleanup: deleted {deleted} old log file(s)")
        except Exception as e:
            logging.error(f"Error during log rollover cleanup: {e}")


class LogArchiver:
    """Manages log file archiving for long-term storage."""

    def __init__(self, log_dir: str = "logs", archive_dir: str = "logs/archive"):
        """
        Initialize log archiver.

        Args:
            log_dir: Directory containing log files
            archive_dir: Directory to store archived logs
        """
        self.log_dir = log_dir
        self.archive_dir = archive_dir

        # Create archive directory if it doesn't exist
        if not os.path.exists(self.archive_dir):
            os.makedirs(self.archive_dir, exist_ok=True)

    def archive_old_logs(self, days_before_archive: int = 7) -> int:
        """
        Archive log files older than specified days as gzip files.

        Args:
            days_before_archive: Days before archiving a log file

        Returns:
            Number of files archived
        """
        if not os.path.exists(self.log_dir):
            return 0

        archived_count = 0
        current_time = time.time()
        archive_cutoff = current_time - (days_before_archive * 24 * 60 * 60)

        try:
            for filename in os.listdir(self.log_dir):
                if filename.startswith('app.log') and filename != 'app.log':
                    filepath = os.path.join(self.log_dir, filename)

                    if os.path.isfile(filepath):
                        file_mtime = os.path.getmtime(filepath)

                        # Archive if older than cutoff
                        if file_mtime < archive_cutoff:
                            try:
                                archive_name = f"{filename}.{datetime.fromtimestamp(file_mtime).strftime('%Y%m%d')}.gz"
                                archive_path = os.path.join(self.archive_dir, archive_name)

                                # Compress and archive
                                with open(filepath, 'rb') as f_in:
                                    with gzip.open(archive_path, 'wb') as f_out:
                                        f_out.writelines(f_in)

                                # Remove original after successful archiving
                                os.remove(filepath)
                                archived_count += 1
                                logging.info(f"Archived log file: {filename} -> {archive_name}")
                            except Exception as e:
                                logging.error(f"Failed to archive log file {filename}: {e}")
        except Exception as e:
            logging.error(f"Error during log archiving: {e}")

        return archived_count

    def get_archive_statistics(self) -> dict:
        """
        Get statistics about archived logs.

        Returns:
            Dictionary with archive statistics
        """
        if not os.path.exists(self.archive_dir):
            return {"total_size_mb": 0, "file_count": 0, "files": []}

        total_size = 0
        file_count = 0
        files = []

        try:
            for filename in os.listdir(self.archive_dir):
                if filename.endswith('.gz'):
                    filepath = os.path.join(self.archive_dir, filename)

                    if os.path.isfile(filepath):
                        file_size = os.path.getsize(filepath)
                        mtime = os.path.getmtime(filepath)
                        mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')

                        total_size += file_size
                        file_count += 1

                        files.append({
                            "name": filename,
                            "size_mb": file_size / 1024 / 1024,
                            "archived_date": mtime_str
                        })
        except Exception as e:
            logging.error(f"Error getting archive statistics: {e}")

        return {
            "total_size_mb": total_size / 1024 / 1024,
            "file_count": file_count,
            "files": sorted(files, key=lambda x: x['name'], reverse=True)
        }


class SpecializedLogger:
    """Factory for creating specialized loggers for different parts of the application."""

    _loggers = {}

    @staticmethod
    def get_endpoint_logger(endpoint_name: str) -> logging.Logger:
        """
        Get or create a logger for a specific endpoint.

        Args:
            endpoint_name: Name of the endpoint (e.g., 'user.login', 'letter.generate')

        Returns:
            Logger instance for the endpoint
        """
        logger_name = f"endpoints.{endpoint_name}"
        if logger_name not in SpecializedLogger._loggers:
            logger = logging.getLogger(logger_name)
            SpecializedLogger._loggers[logger_name] = logger
        return SpecializedLogger._loggers[logger_name]

    @staticmethod
    def get_action_logger(action_type: str) -> logging.Logger:
        """
        Get or create a logger for user actions.

        Args:
            action_type: Type of action (e.g., 'user.create', 'user.delete', 'letter.generate')

        Returns:
            Logger instance for the action
        """
        logger_name = f"actions.{action_type}"
        if logger_name not in SpecializedLogger._loggers:
            logger = logging.getLogger(logger_name)
            SpecializedLogger._loggers[logger_name] = logger
        return SpecializedLogger._loggers[logger_name]

    @staticmethod
    def get_auth_logger() -> logging.Logger:
        """Get or create the authentication logger."""
        logger_name = "auth"
        if logger_name not in SpecializedLogger._loggers:
            logger = logging.getLogger(logger_name)
            SpecializedLogger._loggers[logger_name] = logger
        return SpecializedLogger._loggers[logger_name]

    @staticmethod
    def get_error_logger() -> logging.Logger:
        """Get or create the error logger."""
        logger_name = "errors"
        if logger_name not in SpecializedLogger._loggers:
            logger = logging.getLogger(logger_name)
            SpecializedLogger._loggers[logger_name] = logger
        return SpecializedLogger._loggers[logger_name]

    @staticmethod
    def log_action(action_type: str, user_email: str, action: str, details: dict = None, status: str = "success"):
        """
        Log a user action with context.

        Args:
            action_type: Type of action (e.g., 'user', 'letter', 'chat')
            user_email: Email of user performing action
            action: Description of the action
            details: Additional details as dictionary
            status: Status of the action ('success', 'failure', 'warning')
        """
        logger = SpecializedLogger.get_action_logger(action_type)

        log_message = f"{action} | User: {user_email}"
        if details:
            log_message += f" | {json.dumps(details)}"

        if status == "success":
            logger.info(log_message)
        elif status == "warning":
            logger.warning(log_message)
        else:
            logger.error(log_message)

    @staticmethod
    def log_endpoint(endpoint: str, method: str, user_email: str = None, status_code: int = None, details: dict = None):
        """
        Log an endpoint request.

        Args:
            endpoint: Endpoint path (e.g., '/api/v1/user/validate')
            method: HTTP method (GET, POST, etc.)
            user_email: Email of user making request
            status_code: HTTP response status code
            details: Additional details
        """
        logger = SpecializedLogger.get_endpoint_logger(endpoint.replace('/', '.'))

        log_message = f"{method} {endpoint}"
        if user_email:
            log_message += f" | User: {user_email}"
        if status_code:
            log_message += f" | Status: {status_code}"
        if details:
            log_message += f" | {json.dumps(details)}"

        logger.info(log_message)


def setup_log_cleanup(log_dir: str = "logs", retention_days: int = 30) -> LogCleanupManager:
    """
    Setup and run initial log cleanup.

    Args:
        log_dir: Directory containing log files
        retention_days: Number of days to keep logs

    Returns:
        LogCleanupManager instance
    """
    manager = LogCleanupManager(log_dir, retention_days)

    # Run initial cleanup
    try:
        deleted = manager.cleanup_old_logs()
        if deleted > 0:
            logging.info(f"Initial log cleanup: deleted {deleted} old log file(s)")
    except Exception as e:
        logging.error(f"Error during initial log cleanup: {e}")

    return manager


def setup_log_archiving(log_dir: str = "logs", archive_dir: str = "logs/archive", days_before_archive: int = 7):
    """
    Setup and run initial log archiving.

    Args:
        log_dir: Directory containing log files
        archive_dir: Directory to store archived logs
        days_before_archive: Days before archiving a log file
    """
    archiver = LogArchiver(log_dir, archive_dir)

    # Run initial archiving
    try:
        archived = archiver.archive_old_logs(days_before_archive)
        if archived > 0:
            logging.info(f"Initial log archiving: archived {archived} old log file(s)")
    except Exception as e:
        logging.error(f"Error during initial log archiving: {e}")

    return archiver
