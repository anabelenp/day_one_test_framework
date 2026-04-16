#!/usr/bin/env python3
"""
Custom Exceptions for Day-1 SDET Framework

This module defines all custom exceptions used across the framework
for consistent error handling and better debugging.
"""


class SDETFrameworkError(Exception):
    """Base exception for all SDET Framework errors"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class ConfigurationError(SDETFrameworkError):
    """Raised when configuration is invalid or missing"""

    pass


class EnvironmentError(SDETFrameworkError):
    """Raised when environment detection or switching fails"""

    pass


class ServiceConnectionError(SDETFrameworkError):
    """Raised when connection to a service fails"""

    def __init__(self, service: str, message: str, details: dict = None):
        super().__init__(message, details)
        self.service = service


class ServiceTimeoutError(ServiceConnectionError):
    """Raised when a service operation times out"""

    def __init__(
        self, service: str, operation: str, timeout: int, details: dict = None
    ):
        super().__init__(
            service, f"Operation '{operation}' timed out after {timeout}s", details
        )
        self.operation = operation
        self.timeout = timeout


class AuthenticationError(SDETFrameworkError):
    """Raised when authentication fails"""

    def __init__(self, service: str, message: str = None, details: dict = None):
        msg = message or f"Authentication failed for {service}"
        super().__init__(msg, details)
        self.service = service


class ValidationError(SDETFrameworkError):
    """Raised when data validation fails"""

    pass


class TestDataError(SDETFrameworkError):
    """Raised when test data is invalid or missing"""

    pass


class DeploymentError(SDETFrameworkError):
    """Raised when deployment operations fail"""

    pass


class KubernetesError(DeploymentError):
    """Raised when Kubernetes operations fail"""

    def __init__(self, operation: str, message: str, details: dict = None):
        super().__init__(message, details)
        self.operation = operation


class HealthCheckError(SDETFrameworkError):
    """Raised when health check fails"""

    def __init__(self, service: str, message: str = None, details: dict = None):
        msg = message or f"Health check failed for {service}"
        super().__init__(msg, details)
        self.service = service


class ResourceNotFoundError(SDETFrameworkError):
    """Raised when a requested resource is not found"""

    def __init__(self, resource_type: str, resource_id: str, details: dict = None):
        super().__init__(f"{resource_type} '{resource_id}' not found", details)
        self.resource_type = resource_type
        self.resource_id = resource_id


class CircuitBreakerError(SDETFrameworkError):
    """Raised when circuit breaker is open"""

    def __init__(self, service: str, details: dict = None):
        super().__init__(f"Circuit breaker is open for {service}", details)
        self.service = service


class RateLimitError(SDETFrameworkError):
    """Raised when rate limit is exceeded"""

    def __init__(self, service: str, limit: int, window: int, details: dict = None):
        super().__init__(
            f"Rate limit exceeded for {service}: {limit} requests per {window}s",
            details,
        )
        self.service = service
        self.limit = limit
        self.window = window
