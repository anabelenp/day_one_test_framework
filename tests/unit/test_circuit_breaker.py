#!/usr/bin/env python3
"""
Unit tests for Circuit Breaker module.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from src.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerStats,
    CircuitState,
    CircuitBreakerRegistry,
    create_service_circuit_breaker,
)


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig"""

    def test_default_config(self):
        """Test default configuration"""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout == 60
        assert config.name == "default"

    def test_custom_config(self):
        """Test custom configuration"""
        config = CircuitBreakerConfig(
            failure_threshold=10, success_threshold=3, timeout=120, name="test_breaker"
        )
        assert config.failure_threshold == 10
        assert config.success_threshold == 3
        assert config.timeout == 120
        assert config.name == "test_breaker"


class TestCircuitBreaker:
    """Tests for CircuitBreaker"""

    def test_initial_state_closed(self):
        """Test that circuit starts in closed state"""
        breaker = CircuitBreaker()
        assert breaker.state == CircuitState.CLOSED

    def test_record_success_increments_count(self):
        """Test that success is recorded"""
        breaker = CircuitBreaker()
        breaker.record_success()
        stats = breaker.stats
        assert stats.successful_calls == 1
        assert stats.consecutive_successes == 1

    def test_record_failure_increments_count(self):
        """Test that failure is recorded"""
        breaker = CircuitBreaker()
        breaker.record_failure()
        stats = breaker.stats
        assert stats.failed_calls == 1
        assert stats.consecutive_failures == 1

    def test_trip_after_failure_threshold(self):
        """Test circuit trips after failure threshold"""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)

        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN

    def test_reset_after_success_threshold_in_half_open(self):
        """Test circuit resets after success threshold in half-open"""
        config = CircuitBreakerConfig(
            failure_threshold=2, success_threshold=2, timeout=0.5
        )
        breaker = CircuitBreaker(config)

        for _ in range(2):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN

        time.sleep(0.6)

        breaker.state
        breaker.record_success()
        breaker.record_success()

        assert breaker.state == CircuitState.CLOSED

    def test_retry_after_timeout(self):
        """Test circuit allows retry after timeout"""
        config = CircuitBreakerConfig(failure_threshold=1, timeout=1)
        breaker = CircuitBreaker(config)

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        time.sleep(1.1)

        assert breaker.state == CircuitState.HALF_OPEN

    def test_reject_request_when_open(self):
        """Test request is rejected when circuit is open"""
        config = CircuitBreakerConfig(failure_threshold=1, timeout=60)
        breaker = CircuitBreaker(config)

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert breaker.allow_request() is False

    def test_allow_request_in_half_open(self):
        """Test request is allowed in half-open state"""
        config = CircuitBreakerConfig(failure_threshold=1, timeout=1)
        breaker = CircuitBreaker(config)

        breaker.record_failure()
        time.sleep(1.1)

        breaker.state
        assert breaker.allow_request() is True

    def test_call_success(self):
        """Test successful call through circuit breaker"""
        breaker = CircuitBreaker()

        def success_func():
            return "success"

        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.stats.successful_calls == 1

    def test_call_failure(self):
        """Test failure call through circuit breaker"""
        breaker = CircuitBreaker()

        def fail_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            breaker.call(fail_func)

        assert breaker.stats.failed_calls == 1

    def test_reject_call_when_open(self):
        """Test call is rejected when circuit is open"""
        from src.exceptions import CircuitBreakerError

        config = CircuitBreakerConfig(failure_threshold=1, timeout=60)
        breaker = CircuitBreaker(config)

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        def some_func():
            return "should not reach"

        with pytest.raises(CircuitBreakerError):
            breaker.call(some_func)

    def test_reset(self):
        """Test reset returns circuit to closed state"""
        config = CircuitBreakerConfig(failure_threshold=1, timeout=60)
        breaker = CircuitBreaker(config)

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.stats.total_calls == 0

    def test_get_info(self):
        """Test get_info returns expected structure"""
        breaker = CircuitBreaker(CircuitBreakerConfig(name="test"))
        breaker.record_success()

        info = breaker.get_info()
        assert "name" in info
        assert "state" in info
        assert "config" in info
        assert "stats" in info
        assert info["name"] == "test"
        assert info["state"] == "closed"


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry"""

    def test_get_or_create_new(self):
        """Test creating new circuit breaker"""
        registry = CircuitBreakerRegistry()
        breaker = registry.get_or_create("test1")
        assert breaker is not None
        assert breaker.config.name == "test1"

    def test_get_or_create_existing(self):
        """Test getting existing circuit breaker"""
        registry = CircuitBreakerRegistry()
        breaker1 = registry.get_or_create("test2")
        breaker2 = registry.get_or_create("test2")
        assert breaker1 is breaker2

    def test_get_all_info(self):
        """Test getting all circuit breakers info"""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("breaker1")
        registry.get_or_create("breaker2")

        all_info = registry.get_all_info()
        assert len(all_info) == 2

    def test_reset_all(self):
        """Test resetting all circuit breakers"""
        registry = CircuitBreakerRegistry()
        breaker = registry.get_or_create("test3")
        breaker.record_failure()

        registry.reset_all()
        assert breaker.state == CircuitState.CLOSED


class TestCreateServiceCircuitBreaker:
    """Tests for create_service_circuit_breaker helper"""

    def test_creates_with_custom_config(self):
        """Test creating with custom config"""
        breaker = create_service_circuit_breaker(
            "test_service", failure_threshold=10, timeout=120
        )
        assert breaker.config.name == "test_service"
        assert breaker.config.failure_threshold == 10
        assert breaker.config.timeout == 120


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
