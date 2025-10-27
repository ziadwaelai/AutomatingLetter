"""
Connection Pool Manager for Google APIs
Provides efficient connection pooling with thread safety and automatic cleanup.
"""

import logging
import threading
import time
from typing import Dict, Optional, Callable, Any, Generic, TypeVar
from queue import Queue, Empty
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class PooledConnection:
    """Represents a pooled connection with metadata."""
    connection: Any
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int = 0

    def mark_used(self):
        """Mark the connection as used."""
        self.last_used_at = time.time()
        self.use_count += 1

    def is_expired(self, max_lifetime_seconds: int) -> bool:
        """Check if connection has exceeded max lifetime."""
        return (time.time() - self.created_at) > max_lifetime_seconds

    def is_idle(self, max_idle_seconds: int) -> bool:
        """Check if connection has been idle too long."""
        return (time.time() - self.last_used_at) > max_idle_seconds


class ConnectionPool(Generic[T]):
    """
    Thread-safe connection pool for managing Google API connections.

    Features:
    - Thread-safe operations using locks
    - Automatic connection lifecycle management
    - Connection reuse to reduce overhead
    - Configurable pool size and timeout limits
    - Health monitoring and statistics
    """

    def __init__(
        self,
        connection_factory: Callable[[], T],
        cleanup_func: Optional[Callable[[T], None]] = None,
        pool_size: int = 5,
        connection_timeout: int = 30,
        max_connection_lifetime: int = 3600,  # 1 hour
        max_connection_idle_time: int = 300,  # 5 minutes
    ):
        """
        Initialize the connection pool.

        Args:
            connection_factory: Callable that creates new connections
            cleanup_func: Optional function to call when closing connections
            pool_size: Maximum number of connections in the pool
            connection_timeout: Timeout in seconds for acquiring a connection
            max_connection_lifetime: Max lifetime of a connection in seconds
            max_connection_idle_time: Max idle time before connection is recycled
        """
        self.connection_factory = connection_factory
        self.cleanup_func = cleanup_func
        self.pool_size = pool_size
        self.connection_timeout = connection_timeout
        self.max_connection_lifetime = max_connection_lifetime
        self.max_connection_idle_time = max_connection_idle_time

        # Queue of available connections
        self._available_connections: Queue[PooledConnection] = Queue(maxsize=pool_size)

        # Lock for thread safety
        self._lock = threading.RLock()

        # Track all connections for cleanup
        self._all_connections: list[PooledConnection] = []

        # Statistics
        self._stats = {
            'connections_created': 0,
            'connections_reused': 0,
            'connections_created_wait': 0,
            'acquisitions': 0,
            'failures': 0,
            'last_reset': time.time()
        }

        # Health check thread
        self._health_check_thread: Optional[threading.Thread] = None
        self._running = True
        self._start_health_check()

    def acquire(self) -> T:
        """
        Acquire a connection from the pool.

        Returns:
            A connection ready to use

        Raises:
            TimeoutError: If unable to get a connection within timeout
        """
        with self._lock:
            self._stats['acquisitions'] += 1

        start_time = time.time()

        try:
            # Try to get an available connection
            try:
                pooled_conn = self._available_connections.get(timeout=0.1)

                # Check if connection is still valid
                if not pooled_conn.is_expired(self.max_connection_lifetime) and \
                   not pooled_conn.is_idle(self.max_connection_idle_time):
                    pooled_conn.mark_used()
                    with self._lock:
                        self._stats['connections_reused'] += 1
                    logger.debug(f"Reused connection from pool (use_count: {pooled_conn.use_count})")
                    return pooled_conn.connection
                else:
                    # Connection expired or idle too long, close it
                    self._close_connection(pooled_conn)
                    logger.debug("Closed expired/idle connection")

            except Empty:
                pass

            # No available connection, create new one if under limit
            with self._lock:
                if len(self._all_connections) < self.pool_size:
                    # Create new connection
                    try:
                        conn = self.connection_factory()
                        pooled_conn = PooledConnection(connection=conn)
                        self._all_connections.append(pooled_conn)
                        pooled_conn.mark_used()

                        with self._lock:
                            self._stats['connections_created'] += 1

                        logger.debug(f"Created new connection (pool size: {len(self._all_connections)}/{self.pool_size})")
                        return conn

                    except Exception as e:
                        with self._lock:
                            self._stats['failures'] += 1
                        logger.error(f"Failed to create new connection: {e}")
                        raise
                else:
                    # Pool is full, wait for connection with timeout
                    with self._lock:
                        self._stats['connections_created_wait'] += 1

            remaining_time = self.connection_timeout - (time.time() - start_time)
            if remaining_time > 0:
                try:
                    pooled_conn = self._available_connections.get(timeout=remaining_time)

                    # Validate connection
                    if not pooled_conn.is_expired(self.max_connection_lifetime) and \
                       not pooled_conn.is_idle(self.max_connection_idle_time):
                        pooled_conn.mark_used()
                        with self._lock:
                            self._stats['connections_reused'] += 1
                        logger.debug(f"Reused connection from pool after wait (use_count: {pooled_conn.use_count})")
                        return pooled_conn.connection
                    else:
                        self._close_connection(pooled_conn)
                        # Try again recursively
                        return self.acquire()

                except Empty:
                    with self._lock:
                        self._stats['failures'] += 1
                    raise TimeoutError(f"Could not acquire connection within {self.connection_timeout} seconds")
            else:
                with self._lock:
                    self._stats['failures'] += 1
                raise TimeoutError(f"Connection acquisition timeout")

        except Exception as e:
            logger.error(f"Error acquiring connection: {e}")
            raise

    def release(self, connection: T) -> None:
        """
        Release a connection back to the pool.

        Args:
            connection: The connection to release
        """
        # Find the pooled connection wrapper
        with self._lock:
            for pooled_conn in self._all_connections:
                if pooled_conn.connection is connection:
                    # Return to pool if it's still valid
                    if not pooled_conn.is_expired(self.max_connection_lifetime):
                        try:
                            self._available_connections.put_nowait(pooled_conn)
                            logger.debug("Connection released back to pool")
                            return
                        except:
                            pass

                    # Connection no longer valid, close it
                    self._close_connection(pooled_conn)
                    return

        logger.warning("Attempted to release unknown connection")

    def _close_connection(self, pooled_conn: PooledConnection) -> None:
        """Close a connection and remove it from tracking."""
        try:
            if self.cleanup_func:
                self.cleanup_func(pooled_conn.connection)
            logger.debug(f"Closed connection (lifetime: {time.time() - pooled_conn.created_at:.1f}s, uses: {pooled_conn.use_count})")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
        finally:
            if pooled_conn in self._all_connections:
                self._all_connections.remove(pooled_conn)

    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            self._running = False

            # Close all available connections
            while True:
                try:
                    pooled_conn = self._available_connections.get_nowait()
                    self._close_connection(pooled_conn)
                except Empty:
                    break

            # Close all connections (including in-use)
            for pooled_conn in self._all_connections[:]:  # Copy list to avoid modification during iteration
                self._close_connection(pooled_conn)

            logger.info(f"Closed all connections. Stats: {self._stats}")

    def _start_health_check(self) -> None:
        """Start background health check thread."""
        self._health_check_thread = threading.Thread(
            target=self._health_check_worker,
            daemon=True,
            name="ConnectionPool-HealthCheck"
        )
        self._health_check_thread.start()

    def _health_check_worker(self) -> None:
        """Background worker for health checks and cleanup."""
        while self._running:
            try:
                time.sleep(30)  # Check every 30 seconds

                with self._lock:
                    if not self._running:
                        break

                    # Remove expired/idle connections from available queue
                    expired_conns = []
                    temp_conns = []

                    while True:
                        try:
                            pooled_conn = self._available_connections.get_nowait()
                            if pooled_conn.is_expired(self.max_connection_lifetime) or \
                               pooled_conn.is_idle(self.max_connection_idle_time):
                                expired_conns.append(pooled_conn)
                            else:
                                temp_conns.append(pooled_conn)
                        except Empty:
                            break

                    # Return valid connections
                    for conn in temp_conns:
                        try:
                            self._available_connections.put_nowait(conn)
                        except:
                            expired_conns.append(conn)

                    # Close expired connections
                    for conn in expired_conns:
                        self._close_connection(conn)
                        if conn in self._all_connections:
                            logger.debug("Removed expired/idle connection during health check")

            except Exception as e:
                logger.error(f"Error in health check: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                **self._stats,
                'pool_size': len(self._all_connections),
                'available_connections': self._available_connections.qsize(),
                'max_pool_size': self.pool_size,
                'uptime_seconds': time.time() - self._stats['last_reset']
            }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self._stats['connections_created'] = 0
            self._stats['connections_reused'] = 0
            self._stats['connections_created_wait'] = 0
            self._stats['acquisitions'] = 0
            self._stats['failures'] = 0
            self._stats['last_reset'] = time.time()


class PooledConnectionManager:
    """
    High-level manager for pooled connections using context manager pattern.
    """

    def __init__(self, pool: ConnectionPool):
        """Initialize with a pool."""
        self.pool = pool
        self.connection: Optional[Any] = None

    def __enter__(self) -> Any:
        """Acquire connection on context enter."""
        self.connection = self.pool.acquire()
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Release connection on context exit."""
        if self.connection:
            self.pool.release(self.connection)
        return False
