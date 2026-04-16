#!/usr/bin/env python3
"""
Circuit Breaker Pattern Implementation for Day-1 Framework

Provides fault tolerance and resilience for service clients by implementing
the circuit breaker pattern to prevent cascading failures.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional, TypeVar
import logging

from .exceptions import CircuitBreakerError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: int = 60
    expected_exceptions: tuple = (Exception,)
    name: str = "default"


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring"""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreaker:
    """
    Circuit Breaker implementation for fault tolerance.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is tripped, requests are rejected
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._lock = threading.RLock()
        self._last_state_change = datetime.now()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
            return self._state

    @property
    def stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics"""
        with self._lock:
            return CircuitBreakerStats(
                total_calls=self._stats.total_calls,
                successful_calls=self._stats.successful_calls,
                failed_calls=self._stats.failed_calls,
                rejected_calls=self._stats.rejected_calls,
                state_changes=self._stats.state_changes,
                last_failure_time=self._stats.last_failure_time,
                last_success_time=self._stats.last_success_time,
                consecutive_failures=self._stats.consecutive_failures,
                consecutive_successes=self._stats.consecutive_successes,
            )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        elapsed = (datetime.now() - self._last_state_change).total_seconds()
        return elapsed >= self.config.timeout

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state"""
        if self._state != new_state:
            logger.info(
                f"Circuit breaker '{self.config.name}': "
                f"{self._state.value} -> {new_state.value}"
            )
            self._state = new_state
            self._last_state_change = datetime.now()
            self._stats.state_changes += 1

            if new_state == CircuitState.HALF_OPEN:
                self._stats.consecutive_successes = 0
                self._stats.consecutive_failures = 0

    def _transition_to_half_open(self) -> None:
        """Transition to half-open state"""
        self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to_open(self) -> None:
        """Transition to open state"""
        self._transition_to(CircuitState.OPEN)

    def _transition_to_closed(self) -> None:
        """Transition to closed state"""
        self._transition_to(CircuitState.CLOSED)
        self._stats.consecutive_failures = 0

    def record_success(self) -> None:
        """Record a successful call"""
        with self._lock:
            self._stats.successful_calls += 1
            self._stats.last_success_time = datetime.now()
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0

            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self.config.success_threshold:
                    self._transition_to_closed()

    def record_failure(self) -> None:
        """Record a failed call"""
        with self._lock:
            self._stats.failed_calls += 1
            self._stats.last_failure_time = datetime.now()
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0

            if self._state == CircuitState.HALF_OPEN:
                self._transition_to_open()
            elif self._state == CircuitState.CLOSED:
                if self._stats.consecutive_failures >= self.config.failure_threshold:
                    self._transition_to_open()

    def allow_request(self) -> bool:
        """Check if a request should be allowed"""
        with self._lock:
            state = self.state
            if state == CircuitState.CLOSED:
                return True
            elif state == CircuitState.HALF_OPEN:
                return True
            else:
                self._stats.rejected_calls += 1
                return False

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with circuit breaker protection.

        Raises:
            CircuitBreakerError: If circuit is open
        """
        if not self.allow_request():
            raise CircuitBreakerError(
                self.config.name,
                {"state": self._state.value, "timeout": self.config.timeout},
            )

        with self._lock:
            self._stats.total_calls += 1

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except self.config.expected_exceptions as e:
            self.record_failure()
            raise
        except Exception as e:
            self.record_failure()
            raise

    def reset(self) -> None:
        """Reset the circuit breaker to closed state"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._stats = CircuitBreakerStats()
            self._last_state_change = datetime.now()

    def get_info(self) -> dict[str, Any]:
        """Get circuit breaker information"""
        stats = self.stats
        return {
            "name": self.config.name,
            "state": self.state.value,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
            },
            "stats": {
                "total_calls": stats.total_calls,
                "successful_calls": stats.successful_calls,
                "failed_calls": stats.failed_calls,
                "rejected_calls": stats.rejected_calls,
                "success_rate": (
                    stats.successful_calls / stats.total_calls * 100
                    if stats.total_calls > 0
                    else 0
                ),
                "consecutive_failures": stats.consecutive_failures,
                "consecutive_successes": stats.consecutive_successes,
            },
            "last_failure_time": (
                stats.last_failure_time.isoformat() if stats.last_failure_time else None
            ),
            "last_success_time": (
                stats.last_success_time.isoformat() if stats.last_success_time else None
            ),
        }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def get_or_create(
        self, name: str, config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get an existing circuit breaker or create a new one"""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    config or CircuitBreakerConfig(name=name)
                )
            return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name"""
        return self._breakers.get(name)

    def get_all_info(self) -> list[dict[str, Any]]:
        """Get information for all circuit breakers"""
        return [breaker.get_info() for breaker in self._breakers.values()]

    def reset_all(self) -> None:
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            breaker.reset()


_registry = None
_registry_lock = threading.Lock()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry"""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = CircuitBreakerRegistry()
    return _registry


def circuit_breaker(
    name: str, config: Optional[CircuitBreakerConfig] = None
) -> Callable:
    """
    Decorator to add circuit breaker protection to a function.

    Usage:
        @circuit_breaker("my_service")
        def my_function():
            ...
    """
    breaker = get_circuit_breaker_registry().get_or_create(name, config)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            return breaker.call(func, *args, **kwargs)

        wrapper._circuit_breaker = breaker
        return wrapper

    return decorator


def create_service_circuit_breaker(
    service_name: str, failure_threshold: int = 5, timeout: int = 60
) -> CircuitBreaker:
    """Create a circuit breaker for a service"""
    config = CircuitBreakerConfig(
        name=service_name,
        failure_threshold=failure_threshold,
        timeout=timeout,
    )
    return get_circuit_breaker_registry().get_or_create(service_name, config)
