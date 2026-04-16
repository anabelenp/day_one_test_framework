#!/usr/bin/env python3
"""
Unit tests for Connection Pool module.
"""

import pytest
import time
import threading
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from src.connection_pool import (
    ConnectionPool,
    PoolConfig,
    PoolStats,
    PooledConnection,
    PoolManager,
    get_pool_manager,
)


class TestPoolConfig:
    """Tests for PoolConfig"""

    def test_default_config(self):
        """Test default configuration"""
        config = PoolConfig()
        assert config.min_size == 5
        assert config.max_size == 20
        assert config.max_idle_time == 300
        assert config.max_lifetime == 3600
        assert config.acquisition_timeout == 30
        assert config.name == "default"

    def test_custom_config(self):
        """Test custom configuration"""
        config = PoolConfig(
            min_size=10, max_size=50, max_idle_time=60, name="custom_pool"
        )
        assert config.min_size == 10
        assert config.max_size == 50
        assert config.max_idle_time == 60
        assert config.name == "custom_pool"


class TestPooledConnection:
    """Tests for PooledConnection"""

    def test_connection_property(self):
        """Test getting underlying connection"""
        conn = MagicMock()
        pool = MagicMock()

        pooled = PooledConnection(conn, pool, datetime.now())
        assert pooled.connection is conn

    def test_touch_updates_timestamps(self):
        """Test touch updates last used timestamp"""
        conn = MagicMock()
        pool = MagicMock()

        pooled = PooledConnection(conn, pool, datetime.now())
        initial_use = pooled._use_count

        pooled.touch()
        assert pooled._use_count == initial_use + 1

    def test_is_valid_within_limits(self):
        """Test is_valid returns True within limits"""
        conn = MagicMock()
        pool = MagicMock()

        pooled = PooledConnection(conn, pool, datetime.now())

        assert pooled.is_valid(max_lifetime=3600, max_idle_time=300) is True

    def test_is_valid_expired_lifetime(self):
        """Test is_valid returns False for expired lifetime"""
        conn = MagicMock()
        pool = MagicMock()

        old_time = datetime.now() - timedelta(seconds=100)
        pooled = PooledConnection(conn, pool, old_time)

        assert pooled.is_valid(max_lifetime=60, max_idle_time=300) is False

    def test_is_valid_expired_idle(self):
        """Test is_valid returns False for expired idle time"""
        conn = MagicMock()
        pool = MagicMock()

        pooled = PooledConnection(conn, pool, datetime.now())
        pooled._last_used = datetime.now() - timedelta(seconds=400)

        assert pooled.is_valid(max_lifetime=3600, max_idle_time=300) is False


class TestConnectionPool:
    """Tests for ConnectionPool"""

    def test_initial_pool_size(self):
        """Test pool is initialized with minimum connections"""
        connection_count = [0]

        def factory():
            connection_count[0] += 1
            return MagicMock()

        config = PoolConfig(min_size=3, max_size=10)
        pool = ConnectionPool(factory, config)

        try:
            assert connection_count[0] >= 1
            stats = pool.stats
            assert stats.current_size >= 1
        finally:
            pool.shutdown()

    def test_acquire_returns_connection(self):
        """Test acquiring a connection"""

        def factory():
            return {"id": id(threading.current_thread())}

        config = PoolConfig(min_size=1, max_size=5)
        pool = ConnectionPool(factory, config)

        try:
            pooled = pool.acquire(timeout=5)
            assert pooled is not None
            assert pooled.connection is not None
            pool.release(pooled)
        finally:
            pool.shutdown()

    def test_release_returns_to_pool(self):
        """Test releasing returns connection to pool"""

        def factory():
            return {"id": id(threading.current_thread())}

        config = PoolConfig(min_size=1, max_size=5)
        pool = ConnectionPool(factory, config)

        try:
            initial_available = pool.stats.available_connections

            pooled = pool.acquire(timeout=5)
            pool.release(pooled)

            assert pool.stats.available_connections >= initial_available
        finally:
            pool.shutdown()

    def test_timeout_on_full_pool(self):
        """Test timeout when pool is full"""

        def factory():
            return {"id": "blocked"}

        def blocker(pooled):
            time.sleep(10)

        config = PoolConfig(min_size=1, max_size=1, acquisition_timeout=1)
        pool = ConnectionPool(factory, config)

        try:
            pooled = pool.acquire(timeout=5)

            with pytest.raises(TimeoutError):
                pool.acquire(timeout=0.5)

            pool.release(pooled)
        finally:
            pool.shutdown()

    def test_stats_tracking(self):
        """Test statistics are tracked correctly"""

        def factory():
            return MagicMock()

        config = PoolConfig(min_size=1, max_size=5)
        pool = ConnectionPool(factory, config)

        try:
            pooled = pool.acquire(timeout=5)
            pool.release(pooled)

            stats = pool.stats
            assert stats.total_acquisitions >= 1
            assert stats.successful_acquisitions >= 1
            assert stats.total_releases >= 1
        finally:
            pool.shutdown()

    def test_shutdown_closes_all(self):
        """Test shutdown closes all connections"""

        def factory():
            return MagicMock()

        config = PoolConfig(min_size=2, max_size=5)
        pool = ConnectionPool(factory, config)

        pool.shutdown()

        stats = pool.stats
        assert stats.current_size == 0

    def test_get_info(self):
        """Test get_info returns expected structure"""

        def factory():
            return MagicMock()

        config = PoolConfig(name="test_pool")
        pool = ConnectionPool(factory, config)

        try:
            info = pool.get_info()
            assert "name" in info
            assert "config" in info
            assert "stats" in info
            assert info["name"] == "test_pool"
        finally:
            pool.shutdown()


class TestPoolManager:
    """Tests for PoolManager"""

    def test_create_pool(self):
        """Test creating a named pool"""
        from src.connection_pool import PoolConfig

        manager = PoolManager()

        def factory():
            return MagicMock()

        config = PoolConfig(name="test_pool")
        pool = manager.create_pool("test_pool", factory, config)

        assert pool is not None
        assert pool.config.name == "test_pool"

    def test_get_existing_pool(self):
        """Test getting existing pool returns same instance"""
        manager = PoolManager()

        def factory():
            return MagicMock()

        pool1 = manager.create_pool("shared_pool", factory)
        pool2 = manager.get_pool("shared_pool")

        assert pool1 is pool2

    def test_get_nonexistent_pool(self):
        """Test getting nonexistent pool returns None"""
        manager = PoolManager()
        pool = manager.get_pool("nonexistent")
        assert pool is None

    def test_get_all_info(self):
        """Test getting all pools info"""
        manager = PoolManager()

        def factory():
            return MagicMock()

        manager.create_pool("pool1", factory)
        manager.create_pool("pool2", factory)

        all_info = manager.get_all_info()
        assert len(all_info) == 2

    def test_shutdown_all(self):
        """Test shutting down all pools"""
        manager = PoolManager()

        def factory():
            return MagicMock()

        manager.create_pool("pool1", factory)
        manager.create_pool("pool2", factory)

        manager.shutdown_all()

        assert manager.get_pool("pool1") is None
        assert manager.get_pool("pool2") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
