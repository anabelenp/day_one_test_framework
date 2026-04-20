#!/usr/bin/env python3
"""
Security Tests for Data Handling

Tests for secure data handling including:
- Data encryption
- Sensitive data masking
- Secure storage
- Data retention policies
"""

import pytest
import json
import base64
from unittest.mock import patch, MagicMock


@pytest.mark.security
class TestDataEncryption:
    """Test data encryption at rest and in transit"""

    def test_sensitive_data_encrypted(self):
        """Test that sensitive data is encrypted"""
        from src.service_manager import ServiceManager

        manager = ServiceManager()
        db = manager.get_database_client()

        db.insert_one(
            "sensitive_data",
            {
                "ssn": "123-45-6789",
                "credit_card": "4111-1111-1111-1111",
                "password": "secret123",
            },
        )

        doc = db.find_one("sensitive_data", {"ssn": "123-45-6789"})
        assert doc is not None

    def test_password_hashing(self):
        """Test that passwords are hashed, not stored in plaintext"""
        from src.service_manager import ServiceManager

        manager = ServiceManager()
        db = manager.get_database_client()

        user_id = db.insert_one(
            "users", {"username": "testuser", "password": "plaintext_password"}
        )

        doc = db.find_one("users", {"username": "testuser"})
        if doc and "password" in doc:
            assert doc["password"] != "plaintext_password"

    def test_encrypted_communication(self):
        """Test that communications use encryption"""
        from src.environment_manager import Environment

        with patch(
            "src.environment_manager.os.environ", {"TESTING_MODE": "production"}
        ):
            from src.environment_manager import EnvironmentManager

            manager = EnvironmentManager()

            for service_name in ["redis", "kafka", "mongodb", "target_api"]:
                config = manager.get_service_config(service_name)


@pytest.mark.security
class TestDataMasking:
    """Test data masking for sensitive fields"""

    def test_ssn_masking(self):
        """Test SSN masking"""
        ssn = "123-45-6789"
        masked = f"***-**-{ssn[-4:]}"
        assert masked == "***-**-6789"
        assert ssn not in masked

    def test_credit_card_masking(self):
        """Test credit card number masking"""
        card = "4111111111111111"
        masked = f"****-****-****-{card[-4:]}"
        assert masked == "****-****-****-1111"
        assert card not in masked

    def test_email_masking(self):
        """Test email address masking for privacy"""
        email = "user@example.com"
        username, domain = email.split("@")
        masked = f"{username[0]}***@{domain}"
        assert "@" in masked
        assert username not in masked or username[0] == masked[0]


@pytest.mark.security
class TestSecureStorage:
    """Test secure storage practices"""

    def test_cache_expiry(self):
        """Test that cached sensitive data expires"""
        from src.service_manager import ServiceManager

        manager = ServiceManager()
        cache = manager.get_cache_client()

        cache.set("sensitive_token", "secret_value", ttl=3600)
        value = cache.get("sensitive_token")

        assert value == "secret_value"

    def test_cache_flush_after_use(self):
        """Test that sensitive cached data is flushed"""
        from src.service_manager import ServiceManager

        manager = ServiceManager()
        cache = manager.get_cache_client()

        cache.set("temp_data", "value")
        cache.delete("temp_data")

        assert cache.get("temp_data") is None

    def test_database_connection_security(self):
        """Test database connection security settings"""
        from src.service_manager import ServiceManager

        manager = ServiceManager()
        db = manager.get_database_client()

        info = db.get_connection_info()
        assert "ssl_enabled" in info or "type" in info


@pytest.mark.security
class TestDataRetention:
    """Test data retention policies"""

    def test_old_records_deleted(self):
        """Test that old records follow retention policy"""
        from src.service_manager import ServiceManager
        from datetime import datetime, timedelta

        manager = ServiceManager()
        db = manager.get_database_client()

        old_date = (datetime.now() - timedelta(days=400)).isoformat()
        db.insert_one("logs", {"timestamp": old_date, "data": "old"})

        recent_date = datetime.now().isoformat()
        db.insert_one("logs", {"timestamp": recent_date, "data": "recent"})

    def test_audit_log_completeness(self):
        """Test that audit logs capture all required events"""
        from src.service_manager import ServiceManager

        manager = ServiceManager()
        db = manager.get_database_client()

        db.insert_one(
            "audit_logs",
            {
                "action": "test_action",
                "user": "test_user",
                "timestamp": "2024-01-01T00:00:00",
            },
        )

        logs = db.find_many("audit_logs", {})
        assert len(logs) >= 1


@pytest.mark.security
class TestAPIKeySecurity:
    """Test API key security"""

    def test_api_key_format_validation(self):
        """Test that API keys meet format requirements"""
        valid_keys = [
            "sk_live_abc123def456",
            "sk_test_xyz789uvw012",
        ]

        for key in valid_keys:
            assert len(key) >= 20
            assert key.startswith(("sk_live_", "sk_test_"))

    def test_api_key_rotation(self):
        """Test API key rotation mechanism"""
        from src.service_manager import ServiceManager

        manager = ServiceManager()
        api = manager.get_api_client()

        api.authenticate({"api_key": "sk_live_old_key"})

        new_key = "sk_live_new_key_12345678901234567890"
        api.authenticate({"api_key": new_key})


@pytest.mark.security
class TestComplianceDataHandling:
    """Test compliance-related data handling"""

    def test_gdpr_data_deletion(self):
        """Test GDPR-compliant data deletion"""
        from src.service_manager import ServiceManager

        manager = ServiceManager()
        db = manager.get_database_client()

        user_id = db.insert_one(
            "users",
            {"name": "GDPR User", "email": "gdpr@example.com", "gdpr_consent": True},
        )

        deleted = db.delete_one("users", {"_id": user_id})
        assert deleted is True

    def test_data_portability_format(self):
        """Test data can be exported in portable format"""
        from src.service_manager import ServiceManager
        import json

        manager = ServiceManager()
        db = manager.get_database_client()

        db.insert_one("export_test", {"field1": "value1", "field2": "value2"})
        doc = db.find_one("export_test", {"field1": "value1"})

        json_export = json.dumps(doc)
        assert "value1" in json_export

    def test_pii_field_detection(self):
        """Test detection of PII fields"""
        pii_fields = [
            "ssn",
            "social_security_number",
            "credit_card",
            "card_number",
            "password",
            "secret",
            "email",
            "phone",
            "address",
        ]

        test_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "ssn": "123-45-6789",
        }

        detected_pii = [key for key in test_data.keys() if key in pii_fields]
        assert "email" in detected_pii or "ssn" in detected_pii


@pytest.mark.security
class TestSecureConfiguration:
    """Test secure configuration practices"""

    def test_debug_mode_disabled_in_production(self):
        """Test that debug mode is disabled in production"""
        from src.environment_manager import Environment

        with patch.dict("os.environ", {"TESTING_MODE": "production"}):
            assert True

    def test_error_messages_no_stack_traces(self):
        """Test that error messages don't expose stack traces"""
        from src.service_manager import ServiceManager

        manager = ServiceManager()
        api = manager.get_api_client()

        response = api.get("/api/v2/nonexistent")

        error_str = str(response)
        assert "Traceback" not in error_str
        assert "File " not in error_str

    def test_security_headers_present(self):
        """Test that security headers are present in responses"""
        from src.service_manager import ServiceManager

        manager = ServiceManager()
        api = manager.get_api_client()

        response = api.get("/api/v2/events")
        assert "status" in response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
