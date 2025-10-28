"""
Log Management Module
Handles log rotation, cleanup, and maintenance to keep logs manageable.
"""

import os
import logging
import time
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
