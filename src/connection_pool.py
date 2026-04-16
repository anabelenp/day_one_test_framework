#!/usr/bin/env python3
"""
Connection Pooling Implementation for Day-1 Framework

Provides efficient connection pooling for HTTP clients and service connections
to optimize resource usage and improve performance.
"""

from __future__ import annotations

import threading
import queue
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Generic, Optional, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class PoolConfig:
    """Configuration for connection pool"""

    min_size: int = 5
    max_size: int = 20
    max_idle_time: int = 300
    max_lifetime: int = 3600
    acquisition_timeout: int = 30
    validation_interval: int = 60
    name: str = "default"


@dataclass
class PoolStats:
    """Statistics for connection pool monitoring"""

    total_acquisitions: int = 0
    successful_acquisitions: int = 0
    failed_acquisitions: int = 0
    total_releases: int = 0
    total_connections_created: int = 0
    total_connections_destroyed: int = 0
    current_size: int = 0
    available_connections: int = 0
    in_use_connections: int = 0
    timeouts: int = 0
    validation_failures: int = 0


class PooledConnection(Generic[T]):
    """Wrapper for a pooled connection with metadata"""

    def __init__(
        self,
        connection: T,
        pool: ConnectionPool[T],
        created_at: datetime,
    ):
        self._connection = connection
        self._pool = pool
        self._created_at = created_at
        self._last_used = datetime.now()
        self._use_count = 0
        self._released = False

    @property
    def connection(self) -> T:
        """Get the underlying connection"""
        return self._connection

    @property
    def age(self) -> float:
        """Get the age of this connection in seconds"""
        return (datetime.now() - self._created_at).total_seconds()

    @property
    def idle_time(self) -> float:
        """Get the idle time in seconds"""
        return (datetime.now() - self._last_used).total_seconds()

    def touch(self) -> None:
        """Update last used timestamp"""
        self._last_used = datetime.now()
        self._use_count += 1

    def is_valid(self, max_lifetime: int, max_idle_time: int) -> bool:
        """Check if connection is still valid"""
        if self.age > max_lifetime:
            return False
        if self.idle_time > max_idle_time:
            return False
        return True

    def release(self) -> None:
        """Release this connection back to the pool"""
        if not self._released:
            self._released = True
            self._pool._return_connection(self)


class ConnectionPool(Generic[T]):
    """
    Generic connection pool implementation.

    Features:
    - Configurable min/max pool size
    - Connection lifecycle management
    - Automatic validation and cleanup
    - Thread-safe operations
    - Statistics tracking
    """

    def __init__(
        self,
        factory: Callable[[], T],
        config: Optional[PoolConfig] = None,
        validator: Optional[Callable[[T], bool]] = None,
        destroyer: Optional[Callable[[T], None]] = None,
    ):
        self.config = config or PoolConfig()
        self._factory = factory
        self._validator = validator or (lambda x: True)
        self._destroyer = destroyer or (lambda x: None)

        self._available: queue.Queue[PooledConnection[T]] = queue.Queue()
        self._in_use: set[PooledConnection[T]] = set()
        self._lock = threading.Lock()
        self._all_connections: list[PooledConnection[T]] = []
        self._stats = PoolStats()
        self._shutdown = False
        self._validation_thread: Optional[threading.Thread] = None

        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Initialize the pool with minimum connections"""
        for _ in range(self.config.min_size):
            try:
                conn = self._create_connection()
                self._available.put(conn)
                self._all_connections.append(conn)
                self._stats.total_connections_created += 1
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")

        self._start_validation_thread()

    def _create_connection(self) -> PooledConnection[T]:
        """Create a new pooled connection"""
        conn = self._factory()
        return PooledConnection(conn, self, datetime.now())

    def _destroy_connection(self, pooled: PooledConnection[T]) -> None:
        """Destroy a connection"""
        try:
            self._destroyer(pooled.connection)
            self._stats.total_connections_destroyed += 1
        except Exception as e:
            logger.error(f"Error destroying connection: {e}")

    def _return_connection(self, pooled: PooledConnection[T]) -> None:
        """Return a connection to the pool"""
        with self._lock:
            self._in_use.discard(pooled)
            self._stats.total_releases += 1

            if self._shutdown:
                self._destroy_connection(pooled)
                return

            if pooled.is_valid(self.config.max_lifetime, self.config.max_idle_time):
                pooled._released = False
                pooled.touch()
                self._available.put(pooled)
            else:
                self._destroy_connection(pooled)
                self._all_connections.remove(pooled)

            self._update_stats()

    def acquire(self, timeout: Optional[float] = None) -> PooledConnection[T]:
        """
        Acquire a connection from the pool.

        Raises:
            TimeoutError: If connection cannot be acquired within timeout
            RuntimeError: If pool is shutdown
        """
        if self._shutdown:
            raise RuntimeError("Connection pool is shutdown")

        timeout = timeout or self.config.acquisition_timeout
        self._stats.total_acquisitions += 1

        start_time = time.time()

        while True:
            try:
                pooled = self._available.get(timeout=1)
            except queue.Empty:
                if time.time() - start_time >= timeout:
                    self._stats.timeouts += 1
                    raise TimeoutError(
                        f"Failed to acquire connection within {timeout}s"
                    )
                continue

            with self._lock:
                if pooled in self._all_connections and pooled.is_valid(
                    self.config.max_lifetime, self.config.max_idle_time
                ):
                    if self._validator(pooled.connection):
                        pooled._released = False
                        pooled.touch()
                        self._in_use.add(pooled)
                        self._stats.successful_acquisitions += 1
                        self._update_stats()
                        return pooled
                    else:
                        self._stats.validation_failures += 1
                        self._destroy_connection(pooled)
                        self._all_connections.remove(pooled)
                        continue
                else:
                    if pooled in self._all_connections:
                        self._destroy_connection(pooled)
                        self._all_connections.remove(pooled)

            if time.time() - start_time >= timeout:
                self._stats.timeouts += 1
                raise TimeoutError(
                    f"Failed to acquire valid connection within {timeout}s"
                )

    def release(self, pooled: PooledConnection[T]) -> None:
        """Release a connection back to the pool"""
        self._return_connection(pooled)

    def _update_stats(self) -> None:
        """Update pool statistics"""
        self._stats.current_size = len(self._all_connections)
        self._stats.available_connections = self._available.qsize()
        self._stats.in_use_connections = len(self._in_use)

    def _validation_loop(self) -> None:
        """Background thread for connection validation"""
        while not self._shutdown:
            time.sleep(self.config.validation_interval)

            with self._lock:
                to_remove = []

                for pooled in self._all_connections:
                    if pooled._released and pooled in self._available.queue:
                        if not pooled.is_valid(
                            self.config.max_lifetime, self.config.max_idle_time
                        ):
                            to_remove.append(pooled)

                for pooled in to_remove:
                    try:
                        self._available.queue.remove(pooled)
                        self._destroy_connection(pooled)
                        self._all_connections.remove(pooled)
                        logger.debug(f"Removed idle connection from pool")
                    except ValueError:
                        pass

                while len(self._all_connections) < self.config.min_size:
                    try:
                        conn = self._create_connection()
                        self._available.put(conn)
                        self._all_connections.append(conn)
                        self._stats.total_connections_created += 1
                    except Exception:
                        break

    def _start_validation_thread(self) -> None:
        """Start the background validation thread"""
        self._validation_thread = threading.Thread(
            target=self._validation_loop,
            daemon=True,
            name=f"pool-validator-{self.config.name}",
        )
        self._validation_thread.start()

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the connection pool"""
        self._shutdown = True

        with self._lock:
            for pooled in self._all_connections:
                self._destroy_connection(pooled)
            self._all_connections.clear()
            self._in_use.clear()

        if wait and self._validation_thread:
            self._validation_thread.join(timeout=5)

    @property
    def stats(self) -> PoolStats:
        """Get pool statistics"""
        with self._lock:
            return PoolStats(
                total_acquisitions=self._stats.total_acquisitions,
                successful_acquisitions=self._stats.successful_acquisitions,
                failed_acquisitions=self._stats.failed_acquisitions,
                total_releases=self._stats.total_releases,
                total_connections_created=self._stats.total_connections_created,
                total_connections_destroyed=self._stats.total_connections_destroyed,
                current_size=len(self._all_connections),
                available_connections=self._available.qsize(),
                in_use_connections=len(self._in_use),
                timeouts=self._stats.timeouts,
                validation_failures=self._stats.validation_failures,
            )

    def get_info(self) -> dict[str, Any]:
        """Get pool information"""
        stats = self.stats
        return {
            "name": self.config.name,
            "config": {
                "min_size": self.config.min_size,
                "max_size": self.config.max_size,
                "max_idle_time": self.config.max_idle_time,
                "max_lifetime": self.config.max_lifetime,
                "acquisition_timeout": self.config.acquisition_timeout,
            },
            "stats": {
                "total_acquisitions": stats.total_acquisitions,
                "successful_acquisitions": stats.successful_acquisitions,
                "current_size": stats.current_size,
                "available": stats.available_connections,
                "in_use": stats.in_use_connections,
                "timeouts": stats.timeouts,
                "validation_failures": stats.validation_failures,
                "success_rate": (
                    stats.successful_acquisitions / stats.total_acquisitions * 100
                    if stats.total_acquisitions > 0
                    else 0
                ),
            },
        }


class HTTPConnectionPool(ConnectionPool):
    """Connection pool specialized for HTTP requests.Session"""

    @staticmethod
    def create_session() -> Any:
        """Create a new requests.Session with connection pooling"""
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=retry_strategy,
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def __init__(
        self,
        config: Optional[PoolConfig] = None,
    ):
        super().__init__(
            factory=self.create_session,
            config=config or PoolConfig(name="http"),
            validator=self._validate_session,
            destroyer=self._close_session,
        )

    @staticmethod
    def _validate_session(session: Any) -> bool:
        """Validate that a session is still usable"""
        try:
            return hasattr(session, "headers") and hasattr(session, "get")
        except Exception:
            return False

    @staticmethod
    def _close_session(session: Any) -> None:
        """Close a session"""
        try:
            session.close()
        except Exception:
            pass


class PoolManager:
    """Manager for multiple connection pools"""

    def __init__(self):
        self._pools: dict[str, ConnectionPool] = {}
        self._lock = threading.Lock()

    def create_pool(
        self,
        name: str,
        factory: Callable[[], T],
        config: Optional[PoolConfig] = None,
        validator: Optional[Callable[[T], bool]] = None,
        destroyer: Optional[Callable[[T], None]] = None,
    ) -> ConnectionPool[T]:
        """Create a new named pool"""
        with self._lock:
            if name in self._pools:
                return self._pools[name]

            pool = ConnectionPool(factory, config, validator, destroyer)
            self._pools[name] = pool
            return pool

    def get_pool(self, name: str) -> Optional[ConnectionPool]:
        """Get a pool by name"""
        return self._pools.get(name)

    def get_all_info(self) -> list[dict[str, Any]]:
        """Get information for all pools"""
        return [pool.get_info() for pool in self._pools.values()]

    def shutdown_all(self) -> None:
        """Shutdown all pools"""
        for pool in self._pools.values():
            pool.shutdown()
        self._pools.clear()


_manager = None
_manager_lock = threading.Lock()


def get_pool_manager() -> PoolManager:
    """Get the global pool manager"""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = PoolManager()
    return _manager
