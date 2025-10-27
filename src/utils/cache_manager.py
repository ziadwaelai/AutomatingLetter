"""
Cache Manager for Google Sheets Data
Reduces API quota usage by caching frequently accessed data with configurable TTLs.
"""

import logging
import time
from typing import Any, Dict, Optional, Callable
from threading import RLock
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached entry with metadata."""
    value: Any
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 300)  # 5 min default
    hit_count: int = 0
    miss_count: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() > self.expires_at

    def mark_hit(self):
        """Record a cache hit."""
        self.hit_count += 1

    def mark_miss(self):
        """Record a cache miss."""
        self.miss_count += 1

    def get_age(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.created_at

    def get_hit_ratio(self) -> float:
        """Get hit ratio (hits / total accesses)."""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0


class CacheManager:
    """
    Thread-safe cache manager for reducing Google API quota usage.

    Features:
    - Configurable TTL (Time To Live) per cache entry
    - Automatic expiration of old entries
    - Hit/miss statistics for optimization
    - Thread-safe operations
    - Memory-efficient LRU-style cleanup
    """

    # Cache TTL defaults (in seconds)
    DEFAULT_SHEET_SETTINGS_TTL = 600  # 10 minutes
    DEFAULT_SHEET_DATA_TTL = 300  # 5 minutes
    DEFAULT_MASTER_DATA_TTL = 900  # 15 minutes
    DEFAULT_USER_INFO_TTL = 600  # 10 minutes

    def __init__(self, max_cache_size: int = 1000):
        """
        Initialize cache manager.

        Args:
            max_cache_size: Maximum number of cache entries
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = RLock()
        self._max_size = max_cache_size
        self._stats = {
            'total_hits': 0,
            'total_misses': 0,
            'evictions': 0,
            'expirations': 0
        }

    def get(self, key: str, ttl: int = None) -> Optional[Any]:
        """
        Get value from cache if it exists and hasn't expired.

        Args:
            key: Cache key
            ttl: Optional TTL in seconds (ignored if key exists)

        Returns:
            Cached value if found and valid, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                self._stats['total_misses'] += 1
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                self._stats['expirations'] += 1
                self._stats['total_misses'] += 1
                logger.debug(f"Cache entry '{key}' expired (age: {entry.get_age():.1f}s)")
                return None

            # Return cached value
            entry.mark_hit()
            self._stats['total_hits'] += 1
            logger.debug(f"Cache hit for '{key}' (hits: {entry.hit_count}, age: {entry.get_age():.1f}s)")
            return entry.value

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        with self._lock:
            # Check if we need to evict entries
            if len(self._cache) >= self._max_size:
                self._evict_oldest()

            expires_at = time.time() + ttl
            entry = CacheEntry(value=value, expires_at=expires_at)
            self._cache[key] = entry
            logger.debug(f"Cached '{key}' with TTL {ttl}s")

    def delete(self, key: str) -> bool:
        """
        Delete a cache entry.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            size = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {size} cache entries")

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats['expirations'] += 1

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def _evict_oldest(self) -> None:
        """Evict oldest entry when cache is full."""
        if not self._cache:
            return

        # Find oldest entry by creation time
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at
        )

        del self._cache[oldest_key]
        self._stats['evictions'] += 1
        logger.debug(f"Evicted oldest cache entry: '{oldest_key}'")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_accesses = self._stats['total_hits'] + self._stats['total_misses']
            hit_ratio = (self._stats['total_hits'] / total_accesses * 100
                        if total_accesses > 0 else 0.0)

            return {
                'cache_size': len(self._cache),
                'max_size': self._max_size,
                'total_hits': self._stats['total_hits'],
                'total_misses': self._stats['total_misses'],
                'total_accesses': total_accesses,
                'hit_ratio': f"{hit_ratio:.1f}%",
                'evictions': self._stats['evictions'],
                'expirations': self._stats['expirations']
            }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self._stats = {
                'total_hits': 0,
                'total_misses': 0,
                'evictions': 0,
                'expirations': 0
            }


# Global cache instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
        logger.info("Initialized global cache manager")
    return _cache_manager


class CachedCall:
    """
    Decorator for caching function results.

    Usage:
        @CachedCall(ttl=300)
        def get_user_data(sheet_id, user_id):
            # ... expensive API call ...
            return data
    """

    def __init__(self, ttl: int = 300, key_builder: Optional[Callable] = None):
        """
        Initialize decorator.

        Args:
            ttl: Time to live in seconds
            key_builder: Optional function to build cache key from args/kwargs
        """
        self.ttl = ttl
        self.key_builder = key_builder
        self.cache = get_cache_manager()

    def __call__(self, func):
        """Decorate function."""
        def wrapper(*args, **kwargs):
            # Build cache key
            if self.key_builder:
                cache_key = self.key_builder(*args, **kwargs)
            else:
                # Default: use function name + str representation of args
                cache_key = f"{func.__name__}:{args}:{kwargs}"

            # Try to get from cache
            cached_value = self.cache.get(cache_key, self.ttl)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                self.cache.set(cache_key, result, self.ttl)

            return result

        return wrapper
