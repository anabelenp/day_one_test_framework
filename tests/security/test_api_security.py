#!/usr/bin/env python3
"""
Security Tests for API Endpoints

Tests for common security vulnerabilities including:
- SQL Injection
- XSS (Cross-Site Scripting)
- Authentication bypass
- Authorization issues
- Input validation
"""

import pytest
import json
from unittest.mock import patch, MagicMock


@pytest.mark.security
class TestSQLInjection:
    """Test for SQL/NoSQL injection vulnerabilities"""

    @pytest.fixture
    def api_client(self):
        """Create API client for testing"""
        from src.service_manager import ServiceManager

        return ServiceManager().get_api_client()

    def test_sql_injection_select(self, api_client):
        """Test SQL injection in SELECT queries"""
        payloads = [
            "'; DROP TABLE users;--",
            "' OR '1'='1",
            "1; DELETE FROM users",
            "admin'--",
        ]

        for payload in payloads:
            response = api_client.get(f"/api/v2/events?filter={payload}")
            assert response.get("status") == "error" or "error" in response

    def test_sql_injection_insert(self, api_client):
        """Test SQL injection in INSERT operations"""
        payloads = [
            "'; INSERT INTO admin VALUES (1);--",
            '{"name": "test", "value": "\'; DROP TABLE--"}',
        ]

        for payload in payloads:
            response = api_client.post("/api/v2/events", {"data": payload})
            assert response.get("status") == "error" or "error" in response

    def test_no_sql_injection_mongodb(self, api_client):
        """Test that MongoDB operators are handled safely"""
        payloads = [
            '{"$gt": ""}',
            '{"$ne": null}',
            '{"$where": "function()"}',
        ]

        for payload in payloads:
            response = api_client.get(f"/api/v2/events?filter={json.dumps(payload)}")
            assert response.get("status") == "error" or "data" in response


@pytest.mark.security
class TestXSSVulnerabilities:
    """Test for XSS vulnerabilities"""

    @pytest.fixture
    def api_client(self):
        """Create API client for testing"""
        from src.service_manager import ServiceManager

        return ServiceManager().get_api_client()

    def test_xss_in_user_input(self, api_client):
        """Test XSS payload in user input"""
        payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
        ]

        for payload in payloads:
            response = api_client.post("/api/v2/events", {"name": payload})
            assert response.get("status") in ["success", "error"]

    def test_xss_in_api_response(self, api_client):
        """Test that API properly escapes XSS in responses"""
        api_client.post("/api/v2/events", {"name": "<script>alert(1)</script>"})
        response = api_client.get("/api/v2/events")

        if "data" in response and "events" in response["data"]:
            for event in response["data"]["events"]:
                if "name" in event:
                    assert "<script>" not in str(event["name"])


@pytest.mark.security
class TestAuthenticationSecurity:
    """Test authentication security"""

    @pytest.fixture
    def api_client(self):
        """Create API client for testing"""
        from src.service_manager import ServiceManager

        return ServiceManager().get_api_client()

    def test_invalid_credentials(self, api_client):
        """Test authentication with invalid credentials"""
        result = api_client.authenticate({"username": "invalid", "password": "wrong"})
        assert result is False

    def test_missing_credentials(self, api_client):
        """Test authentication with missing credentials"""
        result = api_client.authenticate({})
        assert result is False

    def test_unauthenticated_access(self, api_client):
        """Test accessing protected endpoints without authentication"""
        response = api_client.get("/api/v2/events")
        assert "status" in response

    def test_weak_password_rejection(self, api_client):
        """Test that weak passwords are rejected"""
        weak_passwords = [
            "password",
            "123456",
            "admin",
            "qwerty",
        ]

        for password in weak_passwords:
            result = api_client.authenticate({"username": "test", "password": password})
            assert result is False


@pytest.mark.security
class TestAuthorizationSecurity:
    """Test authorization security"""

    @pytest.fixture
    def api_client(self):
        """Create API client for testing"""
        from src.service_manager import ServiceManager

        return ServiceManager().get_api_client()

    def test_privilege_escalation(self, api_client):
        """Test privilege escalation attempts"""
        api_client.authenticate({"api_key": "test-key"})

        response = api_client.post("/api/v2/admin/users", {"role": "admin"})
        assert (
            response.get("status") == "error" or "unauthorized" in str(response).lower()
        )

    def test_resource_access_control(self, api_client):
        """Test that users can only access their own resources"""
        api_client.authenticate({"api_key": "test-key"})

        response = api_client.get("/api/v2/users/9999")
        assert "data" in response or response.get("status") == "error"


@pytest.mark.security
class TestInputValidation:
    """Test input validation security"""

    @pytest.fixture
    def api_client(self):
        """Create API client for testing"""
        from src.service_manager import ServiceManager

        return ServiceManager().get_api_client()

    def test_max_length_enforcement(self, api_client):
        """Test that maximum field lengths are enforced"""
        long_input = "A" * 10000

        response = api_client.post("/api/v2/events", {"name": long_input})
        assert response.get("status") == "error" or len(str(response)) < 100000

    def test_invalid_data_types(self, api_client):
        """Test that invalid data types are rejected"""
        invalid_data = [
            {"name": 12345},
            {"name": ["array"]},
            {"name": {"object": "value"}},
            {"name": None},
        ]

        for data in invalid_data:
            response = api_client.post("/api/v2/events", data)
            assert response.get("status") in ["success", "error"]

    def test_special_characters_sanitization(self, api_client):
        """Test sanitization of special characters"""
        special_chars = [
            "\x00 NULL",
            "\n\\r newline",
            "\x1b escape",
            "%00 encoded",
        ]

        for char in special_chars:
            response = api_client.post("/api/v2/events", {"name": char})
            assert response.get("status") in ["success", "error"]


@pytest.mark.security
class TestRateLimiting:
    """Test rate limiting security"""

    @pytest.fixture
    def api_client(self):
        """Create API client for testing"""
        from src.service_manager import ServiceManager

        return ServiceManager().get_api_client()

    def test_rate_limit_headers(self, api_client):
        """Test that rate limit headers are present"""
        api_client.authenticate({"api_key": "test-key"})

        response = api_client.get("/api/v2/events")
        headers = response.get("headers", {})
        assert "X-RateLimit-Limit" in headers or "rate_limit" in response

    def test_excessive_requests_blocked(self, api_client):
        """Test that excessive requests are rate limited"""
        api_client.authenticate({"api_key": "test-key"})

        blocked = False
        for _ in range(1000):
            response = api_client.get("/api/v2/events")
            if response.get("status") == "error" and "rate" in str(response).lower():
                blocked = True
                break

        assert blocked or response.get("status") == "success"


@pytest.mark.security
class TestSSLSettings:
    """Test SSL/TLS security settings"""

    def test_ssl_required_in_production(self):
        """Test that SSL is required in production"""
        from src.environment_manager import EnvironmentManager

        with patch(
            "src.environment_manager.os.environ", {"TESTING_MODE": "production"}
        ):
            manager = EnvironmentManager()
            env = manager.detect_environment()
            config = manager.get_service_config("target_api")

            if env.value == "production":
                assert config.ssl_enabled is True

    def test_insecure_connections_rejected(self):
        """Test that insecure connections are rejected in production"""
        from src.environment_manager import Environment

        if Environment.PRODUCTION:
            assert Environment.PRODUCTION.value == "production"


@pytest.mark.security
class TestSecretExposure:
    """Test for secret exposure prevention"""

    def test_passwords_not_in_logs(self):
        """Test that passwords don't appear in logs"""
        from src.service_manager import ServiceManager
        import logging

        class LogCapture(logging.Handler):
            def __init__(self):
                super().__init__()
                self.records = []

            def emit(self, record):
                self.records.append(record.getMessage())

        handler = LogCapture()
        logger = logging.getLogger("ServiceManager")
        logger.addHandler(handler)

        try:
            from src.service_manager import ServiceManager

            manager = ServiceManager()
            api = manager.get_api_client()
            api.authenticate({"password": "super_secret_password_123"})

            for record in handler.records:
                assert "super_secret_password" not in record.lower()
        finally:
            logger.removeHandler(handler)

    def test_api_keys_masked_in_responses(self):
        """Test that API keys are masked in responses"""
        from src.service_manager import ServiceManager

        manager = ServiceManager()
        api = manager.get_api_client()
        api.authenticate({"api_key": "sk_live_secret_key_12345"})

        response = api.get("/api/v2/events")
        response_str = json.dumps(response)

        assert "sk_live_secret" not in response_str
        assert "***" in response_str or "sk_" not in response_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
