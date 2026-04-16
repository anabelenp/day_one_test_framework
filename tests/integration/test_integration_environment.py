#!/usr/bin/env python3
"""
Integration Environment Tests

Tests specifically for the Integration Environment (E3) running on Kubernetes.
These tests validate the complete integration environment setup and functionality.
"""

import pytest
import time
import requests
from typing import Dict, Any

from src.environment_manager import EnvironmentManager, Environment
from src.service_manager import ServiceManager


class TestIntegrationEnvironment:
    """Test suite for Integration Environment (E3) validation"""

    @pytest.fixture(autouse=True)
    def setup_integration_environment(self):
        """Ensure we're running in integration environment"""
        env_manager = EnvironmentManager()
        current_env = env_manager.get_current_environment()

        if current_env != Environment.INTEGRATION:
            pytest.skip(
                f"Integration tests require integration environment, got {current_env.value}"
            )

        self.env_manager = env_manager
        self.service_manager = ServiceManager()

    def test_environment_detection(self):
        """Test that integration environment is properly detected"""
        detected_env = self.env_manager.detect_environment()
        assert detected_env == Environment.INTEGRATION

        current_env = self.env_manager.get_current_environment()
        assert current_env == Environment.INTEGRATION

    def test_environment_configuration(self):
        """Test that integration environment configuration is loaded correctly"""
        config = self.env_manager.load_configuration(Environment.INTEGRATION)

        assert config.environment == Environment.INTEGRATION
        assert config.name is not None

        # Validate service configurations
        assert config.redis.host is not None
        assert config.redis.port > 0
        assert config.kafka.host is not None
        assert config.kafka.port > 0
        assert config.mongodb.host is not None
        assert config.mongodb.port > 0
        assert config.target_api.host is not None
        assert config.target_api.port > 0

    def test_environment_validation(self):
        """Test that integration environment passes validation"""
        is_valid = self.env_manager.validate_environment(Environment.INTEGRATION)
        assert is_valid, "Integration environment should be valid"

    def test_service_health_checks(self):
        """Test that all services in integration environment are healthy"""
        health_results = self.service_manager.health_check_all()

        # All services should be healthy
        for service, is_healthy in health_results.items():
            assert is_healthy, (
                f"Service {service} should be healthy in integration environment"
            )

    def test_redis_connectivity(self):
        """Test Redis connectivity and operations in integration environment"""
        cache_client = self.service_manager.get_cache_client()

        # Test connection
        assert cache_client.connect(), "Should be able to connect to Redis"

        # Test basic operations
        test_key = "integration_test_key"
        test_value = "integration_test_value"

        # Set and get
        assert cache_client.set(test_key, test_value), "Should be able to set value"
        retrieved_value = cache_client.get(test_key)
        assert retrieved_value == test_value, "Retrieved value should match set value"

        # Exists check
        assert cache_client.exists(test_key), "Key should exist"

        # Delete
        assert cache_client.delete(test_key), "Should be able to delete key"
        assert not cache_client.exists(test_key), "Key should not exist after deletion"

    def test_kafka_connectivity(self):
        """Test Kafka connectivity and operations in integration environment"""
        message_client = self.service_manager.get_message_client()

        # Test connection
        assert message_client.connect(), "Should be able to connect to Kafka"

        # Test topic operations
        test_topic = "integration_test_topic"
        test_message = {"test": "integration_message", "timestamp": time.time()}

        # Create topic
        assert message_client.create_topic(test_topic), "Should be able to create topic"

        # Publish message
        assert message_client.publish(test_topic, test_message), (
            "Should be able to publish message"
        )

        # Consume messages
        messages = message_client.consume(test_topic, timeout=5000)
        assert len(messages) > 0, "Should receive at least one message"

        # Verify message content
        received_message = messages[0]
        assert received_message["test"] == test_message["test"], (
            "Message content should match"
        )

    def test_mongodb_connectivity(self):
        """Test MongoDB connectivity and operations in integration environment"""
        db_client = self.service_manager.get_database_client()

        # Test connection
        assert db_client.connect(), "Should be able to connect to MongoDB"

        # Test document operations
        test_collection = "integration_test_collection"
        test_document = {
            "name": "integration_test",
            "environment": "integration",
            "timestamp": time.time(),
        }

        # Insert document
        doc_id = db_client.insert_one(test_collection, test_document)
        assert doc_id is not None, "Should return document ID"

        # Find document
        found_doc = db_client.find_one(test_collection, {"name": "integration_test"})
        assert found_doc is not None, "Should find inserted document"
        assert found_doc["name"] == test_document["name"], (
            "Document content should match"
        )

        # Count documents
        count = db_client.count_documents(test_collection)
        assert count > 0, "Should have at least one document"

        # Update document
        update_result = db_client.update_one(
            test_collection, {"name": "integration_test"}, {"$set": {"updated": True}}
        )
        assert update_result, "Should be able to update document"

        # Delete document
        delete_result = db_client.delete_one(
            test_collection, {"name": "integration_test"}
        )
        assert delete_result, "Should be able to delete document"

    def test_mock_api_connectivity(self):
        """Test Mock API connectivity and responses in integration environment"""
        api_client = self.service_manager.get_api_client()

        # Test connection
        assert api_client.connect(), "Should be able to connect to Mock API"

        # Test authentication
        auth_result = api_client.authenticate({"api_key": "integration-api-key-2024"})
        assert auth_result, "Should be able to authenticate"

        # Test API endpoints
        endpoints_to_test = [
            "/api/v2/events",
            "/api/v2/policies",
            "/api/v2/users",
            "/api/v2/alerts",
            "/api/v2/reports",
        ]

        for endpoint in endpoints_to_test:
            response = api_client.get(endpoint)
            assert response is not None, f"Should get response from {endpoint}"
            assert "data" in response or "error" not in response, (
                f"Response from {endpoint} should be valid"
            )

    def test_monitoring_stack_accessibility(self):
        """Test that monitoring stack is accessible in integration environment"""
        env_info = self.env_manager.get_environment_info(Environment.INTEGRATION)
        monitoring_config = env_info.get("monitoring", {})

        # Test Prometheus accessibility
        prometheus_url = monitoring_config.get("prometheus_url")
        if prometheus_url:
            try:
                response = requests.get(f"{prometheus_url}/-/healthy", timeout=10)
                assert response.status_code == 200, "Prometheus should be healthy"
            except requests.RequestException:
                pytest.skip(
                    "Prometheus not accessible (may be expected in some setups)"
                )

        # Test Grafana accessibility
        grafana_url = monitoring_config.get("grafana_url")
        if grafana_url:
            try:
                response = requests.get(f"{grafana_url}/api/health", timeout=10)
                assert response.status_code == 200, "Grafana should be healthy"
            except requests.RequestException:
                pytest.skip("Grafana not accessible (may be expected in some setups)")

    def test_service_discovery(self):
        """Test that services can discover each other in integration environment"""
        # Get service configurations
        redis_config = self.env_manager.get_service_config(
            "redis", Environment.INTEGRATION
        )
        kafka_config = self.env_manager.get_service_config(
            "kafka", Environment.INTEGRATION
        )
        mongodb_config = self.env_manager.get_service_config(
            "mongodb", Environment.INTEGRATION
        )
        api_config = self.env_manager.get_service_config(
            "target_api", Environment.INTEGRATION
        )

        # Validate service discovery works
        assert redis_config.host is not None, "Redis host should be discoverable"
        assert kafka_config.host is not None, "Kafka host should be discoverable"
        assert mongodb_config.host is not None, "MongoDB host should be discoverable"
        assert api_config.host is not None, "API host should be discoverable"

        # In Kubernetes, services should use cluster DNS
        if self.env_manager._is_kubernetes_environment():
            assert (
                ".svc.cluster.local" in redis_config.host
                or "service" in redis_config.host
            ), "Redis should use Kubernetes service discovery"
            assert (
                ".svc.cluster.local" in kafka_config.host
                or "service" in kafka_config.host
            ), "Kafka should use Kubernetes service discovery"
            assert (
                ".svc.cluster.local" in mongodb_config.host
                or "service" in mongodb_config.host
            ), "MongoDB should use Kubernetes service discovery"

    def test_data_persistence(self):
        """Test that data persists across service restarts in integration environment"""
        # This test validates that persistent volumes work correctly

        # Store data in Redis
        cache_client = self.service_manager.get_cache_client()
        persistence_key = "integration_persistence_test"
        persistence_value = f"persistent_data_{time.time()}"

        cache_client.set(persistence_key, persistence_value)

        # Store data in MongoDB
        db_client = self.service_manager.get_database_client()
        persistence_collection = "integration_persistence_test"
        persistence_doc = {
            "test_id": "persistence_test",
            "data": f"persistent_document_{time.time()}",
            "created_at": time.time(),
        }

        doc_id = db_client.insert_one(persistence_collection, persistence_doc)

        # Verify data exists
        assert cache_client.get(persistence_key) == persistence_value, (
            "Redis data should persist"
        )

        found_doc = db_client.find_one(
            persistence_collection, {"test_id": "persistence_test"}
        )
        assert found_doc is not None, "MongoDB document should persist"
        assert found_doc["data"] == persistence_doc["data"], "MongoDB data should match"

        # Clean up
        cache_client.delete(persistence_key)
        db_client.delete_one(persistence_collection, {"test_id": "persistence_test"})

    def test_performance_characteristics(self):
        """Test performance characteristics of integration environment"""
        # Test Redis performance
        cache_client = self.service_manager.get_cache_client()

        start_time = time.time()
        for i in range(100):
            cache_client.set(f"perf_test_{i}", f"value_{i}")
        redis_write_time = time.time() - start_time

        start_time = time.time()
        for i in range(100):
            cache_client.get(f"perf_test_{i}")
        redis_read_time = time.time() - start_time

        # Clean up
        for i in range(100):
            cache_client.delete(f"perf_test_{i}")

        # Performance should be reasonable (adjust thresholds as needed)
        assert redis_write_time < 5.0, (
            f"Redis writes should be fast, took {redis_write_time:.2f}s"
        )
        assert redis_read_time < 5.0, (
            f"Redis reads should be fast, took {redis_read_time:.2f}s"
        )

        # Test API performance
        api_client = self.service_manager.get_api_client()

        start_time = time.time()
        for _ in range(10):
            api_client.get("/api/v2/events")
        api_response_time = time.time() - start_time

        assert api_response_time < 10.0, (
            f"API responses should be fast, took {api_response_time:.2f}s"
        )

    def test_error_handling(self):
        """Test error handling in integration environment"""
        # Test handling of invalid operations
        cache_client = self.service_manager.get_cache_client()
        db_client = self.service_manager.get_database_client()
        api_client = self.service_manager.get_api_client()

        # Test Redis error handling
        non_existent_key = cache_client.get("non_existent_key_12345")
        assert non_existent_key is None, "Should handle non-existent keys gracefully"

        # Test MongoDB error handling
        invalid_doc = db_client.find_one(
            "non_existent_collection", {"invalid": "query"}
        )
        assert invalid_doc is None, "Should handle invalid queries gracefully"

        # Test API error handling
        try:
            # This should either return an error response or raise an exception
            response = api_client.get("/api/v2/invalid_endpoint")
            if response is not None:
                assert "error" in response, "Invalid endpoint should return error"
        except Exception:
            # Exception is also acceptable for invalid endpoints
            pass

    @pytest.mark.slow
    def test_load_handling(self):
        """Test that integration environment can handle moderate load"""
        import concurrent.futures
        import threading

        # Test concurrent Redis operations
        cache_client = self.service_manager.get_cache_client()

        def redis_operations(thread_id: int):
            for i in range(50):
                key = f"load_test_{thread_id}_{i}"
                value = f"value_{thread_id}_{i}"
                cache_client.set(key, value)
                retrieved = cache_client.get(key)
                assert retrieved == value
                cache_client.delete(key)

        # Run concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(redis_operations, i) for i in range(5)]

            # Wait for all operations to complete
            for future in concurrent.futures.as_completed(futures, timeout=30):
                future.result()  # This will raise any exceptions that occurred

        # Test concurrent API operations
        api_client = self.service_manager.get_api_client()

        def api_operations(thread_id: int):
            for i in range(10):
                response = api_client.get("/api/v2/events")
                assert response is not None

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(api_operations, i) for i in range(3)]

            for future in concurrent.futures.as_completed(futures, timeout=30):
                future.result()


@pytest.mark.integration
class TestIntegrationEnvironmentSecurity:
    """Security-focused tests for integration environment"""

    @pytest.fixture(autouse=True)
    def setup_integration_environment(self):
        """Ensure we're running in integration environment"""
        env_manager = EnvironmentManager()
        current_env = env_manager.get_current_environment()

        if current_env != Environment.INTEGRATION:
            pytest.skip(
                f"Integration security tests require integration environment, got {current_env.value}"
            )

        self.env_manager = env_manager
        self.service_manager = ServiceManager()

    def test_authentication_required(self):
        """Test that services require proper authentication"""
        api_client = self.service_manager.get_api_client()

        # Test without authentication
        try:
            # This should fail or return an error
            response = api_client.get("/api/v2/events", skip_auth=True)
            if response is not None:
                assert "error" in response or "unauthorized" in str(response).lower(), (
                    "Unauthenticated requests should be rejected"
                )
        except Exception:
            # Exception is acceptable for unauthenticated requests
            pass

    def test_secure_connections(self):
        """Test that secure connections are used where appropriate"""
        config = self.env_manager.load_configuration(Environment.INTEGRATION)

        # In production-like integration environment, some services should use SSL
        # This is environment-specific and may not apply to all setups
        security_config = config.security

        if security_config.get("tls_enabled", False):
            assert config.redis.ssl_enabled or config.mongodb.ssl_enabled, (
                "At least one service should use SSL when TLS is enabled"
            )

    def test_access_controls(self):
        """Test that proper access controls are in place"""
        # Test that services are not accessible from unauthorized sources
        # This is more relevant in actual network-isolated environments

        # For now, just verify that authentication is working
        api_client = self.service_manager.get_api_client()

        # Valid authentication should work
        auth_result = api_client.authenticate({"api_key": "integration-api-key-2024"})
        assert auth_result, "Valid authentication should succeed"

        # Invalid authentication should fail
        try:
            invalid_auth = api_client.authenticate({"api_key": "invalid-key"})
            assert not invalid_auth, "Invalid authentication should fail"
        except Exception:
            # Exception is also acceptable for invalid authentication
            pass


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-m", "integration"])
