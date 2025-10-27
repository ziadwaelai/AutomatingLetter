"""
Token Manager for Secure Password Reset
Handles token generation, validation, and expiration.
"""

import logging
import secrets
import time
import threading
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ResetToken:
    """Represents a password reset token with metadata."""
    token: str
    email: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)  # 1 hour default
    used: bool = False
    used_at: Optional[float] = None

    def is_expired(self) -> bool:
        """Check if token has expired."""
        return time.time() > self.expires_at

    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not used)."""
        return not self.is_expired() and not self.used

    def mark_as_used(self) -> None:
        """Mark token as used."""
        self.used = True
        self.used_at = time.time()

    def get_age_seconds(self) -> float:
        """Get age of token in seconds."""
        return time.time() - self.created_at

    def get_remaining_seconds(self) -> float:
        """Get remaining lifetime in seconds."""
        remaining = self.expires_at - time.time()
        return max(0, remaining)


class TokenManager:
    """
    Secure token manager for password reset.

    Features:
    - Cryptographically secure token generation
    - Token expiration (default 1 hour)
    - One-time use tokens
    - Automatic cleanup of expired tokens
    - Thread-safe operations
    """

    def __init__(self, token_lifetime: int = 3600, cleanup_interval: int = 300):
        """
        Initialize token manager.

        Args:
            token_lifetime: Token validity duration in seconds (default: 1 hour)
            cleanup_interval: How often to cleanup expired tokens in seconds (default: 5 minutes)
        """
        self._tokens: Dict[str, ResetToken] = {}
        self._lock = threading.RLock()
        self._token_lifetime = token_lifetime
        self._cleanup_interval = cleanup_interval
        self._stats = {
            'tokens_generated': 0,
            'tokens_validated': 0,
            'tokens_expired': 0,
            'tokens_reused': 0,
            'tokens_cleanup': 0
        }

        # Start cleanup thread
        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            daemon=True,
            name="TokenManager-Cleanup"
        )
        self._cleanup_thread.start()

    def generate_token(self, email: str, lifetime: Optional[int] = None) -> str:
        """
        Generate a secure password reset token.

        Args:
            email: User email address
            lifetime: Token lifetime in seconds (uses default if not provided)

        Returns:
            Secure token string
        """
        with self._lock:
            # Generate secure random token (32 bytes = 256 bits)
            token = secrets.token_urlsafe(32)

            # Set expiration time
            lifetime = lifetime or self._token_lifetime
            expires_at = time.time() + lifetime

            # Store token
            reset_token = ResetToken(
                token=token,
                email=email,
                expires_at=expires_at
            )
            self._tokens[token] = reset_token
            self._stats['tokens_generated'] += 1

            logger.info(f"Generated password reset token for {email} (expires in {lifetime}s)")
            return token

    def validate_token(self, token: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate a password reset token.

        Args:
            token: Token to validate

        Returns:
            Tuple of (is_valid: bool, message: str, email: Optional[str])
        """
        with self._lock:
            # Check if token exists
            if token not in self._tokens:
                logger.warning(f"Token validation failed - token not found")
                return False, "الرمز غير صالح أو غير موجود", None

            reset_token = self._tokens[token]
            self._stats['tokens_validated'] += 1

            # Check if token is expired
            if reset_token.is_expired():
                logger.warning(f"Token validation failed - token expired for {reset_token.email}")
                self._stats['tokens_expired'] += 1
                return False, f"انتهت صلاحية الرمز. تاريخ انتهاء الصلاحية: {datetime.fromtimestamp(reset_token.expires_at).strftime('%Y-%m-%d %H:%M:%S')}", None

            # Check if token already used
            if reset_token.used:
                logger.warning(f"Token validation failed - token already used for {reset_token.email}")
                self._stats['tokens_reused'] += 1
                return False, "تم استخدام هذا الرمز مسبقاً. يرجى طلب رمز جديد", None

            # Token is valid
            logger.info(f"Token validated successfully for {reset_token.email}")
            return True, "الرمز صالح", reset_token.email

    def use_token(self, token: str) -> bool:
        """
        Mark token as used (can only be used once).

        Args:
            token: Token to mark as used

        Returns:
            True if token was marked as used, False if token not found
        """
        with self._lock:
            if token not in self._tokens:
                return False

            reset_token = self._tokens[token]
            reset_token.mark_as_used()
            logger.info(f"Token marked as used for {reset_token.email}")
            return True

    def revoke_token(self, token: str) -> bool:
        """
        Revoke (delete) a token.

        Args:
            token: Token to revoke

        Returns:
            True if token was revoked, False if token not found
        """
        with self._lock:
            if token in self._tokens:
                email = self._tokens[token].email
                del self._tokens[token]
                logger.info(f"Token revoked for {email}")
                return True
            return False

    def cleanup_expired(self) -> int:
        """
        Remove all expired and used tokens.

        Returns:
            Number of tokens removed
        """
        with self._lock:
            expired_tokens = [
                token for token, reset_token in self._tokens.items()
                if reset_token.is_expired() or reset_token.used
            ]

            for token in expired_tokens:
                del self._tokens[token]

            if expired_tokens:
                self._stats['tokens_cleanup'] += len(expired_tokens)
                logger.debug(f"Cleaned up {len(expired_tokens)} expired/used tokens")

            return len(expired_tokens)

    def _cleanup_worker(self) -> None:
        """Background worker for automatic token cleanup."""
        while self._running:
            try:
                time.sleep(self._cleanup_interval)
                self.cleanup_expired()
            except Exception as e:
                logger.error(f"Error in token cleanup worker: {e}")

    def get_token_info(self, token: str) -> Optional[Dict]:
        """
        Get information about a token.

        Args:
            token: Token to get info for

        Returns:
            Dictionary with token info or None if token not found
        """
        with self._lock:
            if token not in self._tokens:
                return None

            reset_token = self._tokens[token]
            return {
                'email': reset_token.email,
                'created_at': datetime.fromtimestamp(reset_token.created_at).isoformat(),
                'expires_at': datetime.fromtimestamp(reset_token.expires_at).isoformat(),
                'remaining_seconds': reset_token.get_remaining_seconds(),
                'is_valid': reset_token.is_valid(),
                'is_expired': reset_token.is_expired(),
                'used': reset_token.used,
                'age_seconds': reset_token.get_age_seconds()
            }

    def get_stats(self) -> Dict:
        """Get token manager statistics."""
        with self._lock:
            return {
                'tokens_generated': self._stats['tokens_generated'],
                'tokens_validated': self._stats['tokens_validated'],
                'tokens_expired': self._stats['tokens_expired'],
                'tokens_reused': self._stats['tokens_reused'],
                'tokens_cleanup': self._stats['tokens_cleanup'],
                'active_tokens': len(self._tokens),
                'token_lifetime': self._token_lifetime
            }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self._stats = {
                'tokens_generated': 0,
                'tokens_validated': 0,
                'tokens_expired': 0,
                'tokens_reused': 0,
                'tokens_cleanup': 0
            }

    def stop(self) -> None:
        """Stop the token manager and cleanup thread."""
        self._running = False
        logger.info("Token manager stopped")


# Global token manager instance
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """Get the global token manager instance."""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
        logger.info("Initialized global token manager")
    return _token_manager
