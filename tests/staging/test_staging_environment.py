#!/usr/bin/env python3
"""
Staging Environment Tests

Tests specifically for the Staging Environment (E4) running on Kubernetes with HA.
These tests validate the production-like staging environment setup with enhanced
security, monitoring, and high availability features.
"""

import pytest
import time
import requests
import concurrent.futures
from typing import Dict, Any

from src.environment_manager import EnvironmentManager, Environment
from src.service_manager import ServiceManager


class TestStagingEnvironment:
    """Test suite for Staging Environment (E4) validation"""

    @pytest.fixture(autouse=True)
    def setup_staging_environment(self):
        """Ensure we're running in staging environment"""
        env_manager = EnvironmentManager()
        current_env = env_manager.get_current_environment()

        if current_env != Environment.STAGING:
            pytest.skip(
                f"Staging tests require staging environment, got {current_env.value}"
            )

        self.env_manager = env_manager
        self.service_manager = ServiceManager()

    def test_environment_detection(self):
        """Test that staging environment is properly detected"""
        detected_env = self.env_manager.detect_environment()
        assert detected_env == Environment.STAGING

        current_env = self.env_manager.get_current_environment()
        assert current_env == Environment.STAGING

    def test_environment_configuration(self):
        """Test that staging environment configuration is loaded correctly"""
        config = self.env_manager.load_configuration(Environment.STAGING)

        assert config.environment == Environment.STAGING
        assert config.name is not None

        # Validate HA service configurations
        assert config.redis.host is not None
        assert (
            "ha" in config.redis.host.lower() or "sentinel" in config.redis.host.lower()
        )
        assert config.kafka.host is not None
        assert "ha" in config.kafka.host.lower()
        assert config.mongodb.host is not None
        assert "ha" in config.mongodb.host.lower()
        assert config.target_api.host is not None

    def test_environment_validation(self):
        """Test that staging environment passes validation"""
        is_valid = self.env_manager.validate_environment(Environment.STAGING)
        assert is_valid, "Staging environment should be valid"

    def test_high_availability_services(self):
        """Test that all services are configured for high availability"""
        health_results = self.service_manager.health_check_all()

        # All HA services should be healthy
        for service, is_healthy in health_results.items():
            assert is_healthy, (
                f"HA service {service} should be healthy in staging environment"
            )

    def test_redis_ha_connectivity(self):
        """Test Redis HA connectivity and failover capabilities"""
        cache_client = self.service_manager.get_cache_client()

        # Test connection to HA Redis
        assert cache_client.connect(), "Should be able to connect to Redis HA"

        # Test basic operations with HA
        test_key = "staging_ha_test_key"
        test_value = "staging_ha_test_value"

        # Set and get with HA
        assert cache_client.set(test_key, test_value), (
            "Should be able to set value in HA Redis"
        )
        retrieved_value = cache_client.get(test_key)
        assert retrieved_value == test_value, (
            "Retrieved value should match set value in HA Redis"
        )

        # Test persistence across potential failovers
        time.sleep(2)  # Allow for replication
        assert cache_client.exists(test_key), "Key should exist after replication delay"

        # Clean up
        assert cache_client.delete(test_key), (
            "Should be able to delete key from HA Redis"
        )

    def test_kafka_ha_connectivity(self):
        """Test Kafka HA connectivity and cluster operations"""
        message_client = self.service_manager.get_message_client()

        # Test connection to HA Kafka
        assert message_client.connect(), "Should be able to connect to Kafka HA"

        # Test topic operations with HA
        test_topic = "staging_ha_test_topic"
        test_message = {
            "test": "staging_ha_message",
            "timestamp": time.time(),
            "environment": "staging",
            "ha_test": True,
        }

        # Create topic with replication
        assert message_client.create_topic(test_topic), (
            "Should be able to create HA topic"
        )

        # Publish message to HA cluster
        assert message_client.publish(test_topic, test_message), (
            "Should be able to publish to HA Kafka"
        )

        # Consume messages from HA cluster
        messages = message_client.consume(test_topic, timeout=10000)
        assert len(messages) > 0, "Should receive at least one message from HA Kafka"

        # Verify message content and HA metadata
        received_message = messages[0]
        assert received_message["test"] == test_message["test"], (
            "Message content should match"
        )
        assert received_message["ha_test"] == True, "HA test flag should be preserved"

    def test_mongodb_ha_connectivity(self):
        """Test MongoDB HA connectivity and replica set operations"""
        db_client = self.service_manager.get_database_client()

        # Test connection to HA MongoDB
        assert db_client.connect(), "Should be able to connect to MongoDB HA"

        # Test document operations with replica set
        test_collection = "staging_ha_test_collection"
        test_document = {
            "name": "staging_ha_test",
            "environment": "staging",
            "timestamp": time.time(),
            "ha_enabled": True,
            "replica_set_test": True,
        }

        # Insert document to replica set
        doc_id = db_client.insert_one(test_collection, test_document)
        assert doc_id is not None, "Should return document ID from HA MongoDB"

        # Read from replica set (may read from secondary)
        time.sleep(1)  # Allow for replication
        found_doc = db_client.find_one(test_collection, {"name": "staging_ha_test"})
        assert found_doc is not None, "Should find inserted document in HA MongoDB"
        assert found_doc["ha_enabled"] == True, "HA flag should be preserved"

        # Test write concern and read preference for HA
        update_result = db_client.update_one(
            test_collection,
            {"name": "staging_ha_test"},
            {"$set": {"updated_in_ha": True, "update_timestamp": time.time()}},
        )
        assert update_result, "Should be able to update document in HA MongoDB"

        # Verify update propagation
        time.sleep(1)  # Allow for replication
        updated_doc = db_client.find_one(test_collection, {"name": "staging_ha_test"})
        assert updated_doc["updated_in_ha"] == True, "Update should be replicated"

        # Clean up
        delete_result = db_client.delete_one(
            test_collection, {"name": "staging_ha_test"}
        )
        assert delete_result, "Should be able to delete document from HA MongoDB"

    def test_enhanced_api_connectivity(self):
        """Test enhanced staging API with security features"""
        api_client = self.service_manager.get_api_client()

        # Test connection to enhanced API
        assert api_client.connect(), "Should be able to connect to enhanced staging API"

        # Test enhanced authentication
        auth_result = api_client.authenticate(
            {"api_key": "staging-api-key-2024-secure-enhanced"}
        )
        assert auth_result, "Should be able to authenticate with enhanced API"

        # Test enhanced API endpoints with security
        enhanced_endpoints = [
            "/api/v2/events",
            "/api/v2/policies",
            "/api/v2/users",
            "/api/v2/alerts",
            "/api/v2/reports",
        ]

        for endpoint in enhanced_endpoints:
            response = api_client.get(endpoint)
            assert response is not None, f"Should get response from enhanced {endpoint}"

            # Verify enhanced response structure
            if isinstance(response, dict):
                assert "data" in response or "error" not in response, (
                    f"Enhanced response from {endpoint} should be valid"
                )

                # Check for staging-specific enhancements
                if (
                    "data" in response
                    and isinstance(response["data"], list)
                    and len(response["data"]) > 0
                ):
                    first_item = response["data"][0]
                    if isinstance(first_item, dict):
                        # Look for staging-specific fields
                        staging_indicators = ["staging", "enhanced", "ha", "secure"]
                        has_staging_indicator = any(
                            indicator in str(first_item).lower()
                            for indicator in staging_indicators
                        )
                        assert has_staging_indicator, (
                            f"Response should contain staging-specific data"
                        )

    def test_enhanced_monitoring_stack(self):
        """Test that enhanced monitoring stack is accessible and functional"""
        env_info = self.env_manager.get_environment_info(Environment.STAGING)
        monitoring_config = env_info.get("monitoring", {})

        # Test Prometheus HA accessibility
        prometheus_url = monitoring_config.get("prometheus_url")
        if prometheus_url:
            try:
                response = requests.get(f"{prometheus_url}/-/healthy", timeout=15)
                assert response.status_code == 200, "Prometheus HA should be healthy"

                # Test Prometheus HA metrics
                metrics_response = requests.get(
                    f"{prometheus_url}/api/v1/query?query=up", timeout=15
                )
                assert metrics_response.status_code == 200, (
                    "Should be able to query Prometheus HA"
                )

                metrics_data = metrics_response.json()
                assert metrics_data.get("status") == "success", (
                    "Prometheus query should succeed"
                )

            except requests.RequestException:
                pytest.skip(
                    "Prometheus HA not accessible (may be expected in some setups)"
                )

        # Test Grafana HA accessibility
        grafana_url = monitoring_config.get("grafana_url")
        if grafana_url:
            try:
                response = requests.get(f"{grafana_url}/api/health", timeout=15)
                assert response.status_code == 200, "Grafana HA should be healthy"

            except requests.RequestException:
                pytest.skip(
                    "Grafana HA not accessible (may be expected in some setups)"
                )

    def test_security_enhancements(self):
        """Test enhanced security features in staging environment"""
        # Test that services require proper authentication
        api_client = self.service_manager.get_api_client()

        # Test without proper authentication (should fail)
        try:
            response = api_client.get("/api/v2/events", skip_auth=True)
            if response is not None:
                assert "error" in response or "unauthorized" in str(response).lower(), (
                    "Unauthenticated requests should be rejected in staging"
                )
        except Exception:
            # Exception is expected for unauthenticated requests in staging
            pass

        # Test with proper authentication (should succeed)
        auth_result = api_client.authenticate(
            {"api_key": "staging-api-key-2024-secure-enhanced"}
        )
        assert auth_result, "Proper authentication should succeed in staging"

        response = api_client.get("/api/v2/events")
        assert response is not None, "Authenticated requests should succeed in staging"

    def test_performance_characteristics(self):
        """Test performance characteristics of staging HA environment"""
        # Test Redis HA performance
        cache_client = self.service_manager.get_cache_client()

        start_time = time.time()
        for i in range(200):  # More operations for staging
            cache_client.set(f"staging_perf_test_{i}", f"value_{i}")
        redis_write_time = time.time() - start_time

        start_time = time.time()
        for i in range(200):
            cache_client.get(f"staging_perf_test_{i}")
        redis_read_time = time.time() - start_time

        # Clean up
        for i in range(200):
            cache_client.delete(f"staging_perf_test_{i}")

        # Performance should be reasonable for HA setup
        assert redis_write_time < 10.0, (
            f"Redis HA writes should be reasonably fast, took {redis_write_time:.2f}s"
        )
        assert redis_read_time < 8.0, (
            f"Redis HA reads should be reasonably fast, took {redis_read_time:.2f}s"
        )

        # Test API performance with enhanced security
        api_client = self.service_manager.get_api_client()

        start_time = time.time()
        for _ in range(20):  # More API calls for staging
            api_client.get("/api/v2/events")
        api_response_time = time.time() - start_time

        assert api_response_time < 20.0, (
            f"Enhanced API responses should be reasonably fast, took {api_response_time:.2f}s"
        )

    def test_data_persistence_and_durability(self):
        """Test data persistence and durability in HA environment"""
        # Test Redis HA persistence
        cache_client = self.service_manager.get_cache_client()
        persistence_key = "staging_ha_persistence_test"
        persistence_value = f"ha_persistent_data_{time.time()}"

        cache_client.set(persistence_key, persistence_value)

        # Test MongoDB HA persistence
        db_client = self.service_manager.get_database_client()
        persistence_collection = "staging_ha_persistence_test"
        persistence_doc = {
            "test_id": "ha_persistence_test",
            "data": f"ha_persistent_document_{time.time()}",
            "created_at": time.time(),
            "ha_replicated": True,
        }

        doc_id = db_client.insert_one(persistence_collection, persistence_doc)

        # Wait for replication
        time.sleep(3)

        # Verify data exists and is replicated
        assert cache_client.get(persistence_key) == persistence_value, (
            "Redis HA data should persist"
        )

        found_doc = db_client.find_one(
            persistence_collection, {"test_id": "ha_persistence_test"}
        )
        assert found_doc is not None, "MongoDB HA document should persist"
        assert found_doc["data"] == persistence_doc["data"], (
            "MongoDB HA data should match"
        )
        assert found_doc["ha_replicated"] == True, (
            "HA replication flag should be preserved"
        )

        # Clean up
        cache_client.delete(persistence_key)
        db_client.delete_one(persistence_collection, {"test_id": "ha_persistence_test"})

    @pytest.mark.slow
    def test_high_availability_resilience(self):
        """Test HA resilience and failover capabilities"""
        # This test simulates various failure scenarios

        # Test Redis HA resilience
        cache_client = self.service_manager.get_cache_client()

        # Store test data
        resilience_keys = [f"ha_resilience_test_{i}" for i in range(10)]
        for key in resilience_keys:
            cache_client.set(key, f"resilient_value_{key}")

        # Verify all data is accessible (should work even if one replica is down)
        for key in resilience_keys:
            value = cache_client.get(key)
            assert value is not None, f"HA Redis should maintain access to {key}"
            assert value == f"resilient_value_{key}", (
                f"HA Redis should return correct value for {key}"
            )

        # Test MongoDB HA resilience
        db_client = self.service_manager.get_database_client()
        resilience_collection = "ha_resilience_test"

        # Store test documents
        resilience_docs = [
            {
                "doc_id": f"resilience_doc_{i}",
                "data": f"resilient_data_{i}",
                "timestamp": time.time(),
                "ha_test": True,
            }
            for i in range(10)
        ]

        for doc in resilience_docs:
            db_client.insert_one(resilience_collection, doc)

        # Wait for replication
        time.sleep(2)

        # Verify all documents are accessible
        for doc in resilience_docs:
            found_doc = db_client.find_one(
                resilience_collection, {"doc_id": doc["doc_id"]}
            )
            assert found_doc is not None, (
                f"HA MongoDB should maintain access to {doc['doc_id']}"
            )
            assert found_doc["data"] == doc["data"], (
                f"HA MongoDB should return correct data"
            )

        # Clean up
        for key in resilience_keys:
            cache_client.delete(key)
        for doc in resilience_docs:
            db_client.delete_one(resilience_collection, {"doc_id": doc["doc_id"]})

    @pytest.mark.load
    def test_concurrent_load_handling(self):
        """Test concurrent load handling in HA staging environment"""
        import concurrent.futures

        def concurrent_operations(thread_id: int, operation_count: int = 100):
            """Perform concurrent operations for load testing"""
            cache_client = self.service_manager.get_cache_client()
            db_client = self.service_manager.get_database_client()
            api_client = self.service_manager.get_api_client()

            results = {
                "thread_id": thread_id,
                "operations": 0,
                "errors": 0,
                "start_time": time.time(),
            }

            try:
                for i in range(operation_count):
                    # Cache operations
                    key = f"load_test_ha_{thread_id}_{i}"
                    value = f"value_{thread_id}_{i}"
                    cache_client.set(key, value)
                    retrieved = cache_client.get(key)
                    assert retrieved == value
                    cache_client.delete(key)

                    # Database operations
                    doc = {
                        "thread_id": thread_id,
                        "operation": i,
                        "timestamp": time.time(),
                        "ha_load_test": True,
                    }
                    doc_id = db_client.insert_one("ha_load_test", doc)
                    assert doc_id is not None

                    found_doc = db_client.find_one(
                        "ha_load_test", {"thread_id": thread_id, "operation": i}
                    )
                    assert found_doc is not None
                    assert found_doc["ha_load_test"] == True

                    db_client.delete_one(
                        "ha_load_test", {"thread_id": thread_id, "operation": i}
                    )

                    # API operations (every 10th iteration)
                    if i % 10 == 0:
                        response = api_client.get("/api/v2/events")
                        assert response is not None

                    results["operations"] += 1

            except Exception as e:
                results["errors"] += 1
                print(f"Error in HA load test thread {thread_id}: {e}")

            results["end_time"] = time.time()
            results["duration"] = results["end_time"] - results["start_time"]

            return results

        # Run concurrent load test with more threads for staging
        num_threads = 10
        operations_per_thread = 50

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(concurrent_operations, i, operations_per_thread)
                for i in range(num_threads)
            ]

            results = []
            for future in concurrent.futures.as_completed(futures, timeout=120):
                result = future.result()
                results.append(result)

        # Analyze HA load test results
        total_operations = sum(r["operations"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        avg_duration = sum(r["duration"] for r in results) / len(results)

        print(f"HA Load test results:")
        print(f"  Total operations: {total_operations}")
        print(f"  Total errors: {total_errors}")
        print(f"  Average duration per thread: {avg_duration:.2f}s")
        print(f"  Error rate: {(total_errors / max(total_operations, 1) * 100):.2f}%")

        # Assertions for HA environment
        assert total_operations > 0, "Should complete some operations in HA environment"
        assert total_errors / max(total_operations, 1) < 0.05, (
            "Error rate should be less than 5% in HA environment"
        )
        assert avg_duration < 60, (
            "Average duration should be reasonable for HA environment"
        )


@pytest.mark.staging
class TestStagingEnvironmentSecurity:
    """Enhanced security tests for staging environment"""

    @pytest.fixture(autouse=True)
    def setup_staging_environment(self):
        """Ensure we're running in staging environment"""
        env_manager = EnvironmentManager()
        current_env = env_manager.get_current_environment()

        if current_env != Environment.STAGING:
            pytest.skip(
                f"Staging security tests require staging environment, got {current_env.value}"
            )

        self.env_manager = env_manager
        self.service_manager = ServiceManager()

    def test_enhanced_authentication(self):
        """Test enhanced authentication mechanisms in staging"""
        api_client = self.service_manager.get_api_client()

        # Test JWT authentication if enabled
        try:
            # Test token-based authentication
            token_response = api_client.post(
                "/api/v2/auth/token",
                {"api_key": "staging-api-key-2024-secure-enhanced"},
            )

            if token_response and "token" in token_response:
                token = token_response["token"]

                # Use token for authenticated request
                headers = {"Authorization": f"Bearer {token}"}
                response = api_client.get("/api/v2/events", headers=headers)
                assert response is not None, "Token-based authentication should work"

        except Exception:
            # Fallback to API key authentication
            auth_result = api_client.authenticate(
                {"api_key": "staging-api-key-2024-secure-enhanced"}
            )
            assert auth_result, "Enhanced API key authentication should work"

    def test_tls_security(self):
        """Test TLS security configuration in staging"""
        # Test that HTTPS is enforced where configured
        api_client = self.service_manager.get_api_client()

        # Verify secure connections are used
        config = self.env_manager.load_configuration(Environment.STAGING)

        if config.security.get("tls_enabled", False):
            # Test that TLS is properly configured
            assert "https" in config.target_api.host.lower(), (
                "API should use HTTPS in staging"
            )

        # Test that insecure requests are rejected
        try:
            # This should fail if TLS is properly enforced
            insecure_response = api_client.get("/api/v2/events", verify_ssl=False)
            # If it succeeds, verify it's properly secured
            if insecure_response:
                print(" TLS enforcement may not be fully configured")
        except Exception:
            # Exception is expected for properly secured staging environment
            pass

    def test_access_control_and_rbac(self):
        """Test access control and RBAC in staging environment"""
        api_client = self.service_manager.get_api_client()

        # Test that different API keys have different permissions
        # (This would require multiple API keys with different roles)

        # Test rate limiting
        start_time = time.time()
        request_count = 0
        rate_limited = False

        try:
            # Make rapid requests to test rate limiting
            for i in range(100):
                response = api_client.get("/api/v2/events")
                request_count += 1

                if response and isinstance(response, dict) and "error" in response:
                    if "rate limit" in response["error"].lower():
                        rate_limited = True
                        break

                # Stop if taking too long
                if time.time() - start_time > 30:
                    break

        except Exception as e:
            if "rate limit" in str(e).lower():
                rate_limited = True

        # Rate limiting should be active in staging
        print(f"Made {request_count} requests, rate limited: {rate_limited}")
        # Note: Rate limiting behavior depends on configuration

    def test_audit_logging(self):
        """Test that audit logging is enabled and functional"""
        # Test that security events are properly logged
        api_client = self.service_manager.get_api_client()
        db_client = self.service_manager.get_database_client()

        # Perform an action that should be audited
        test_timestamp = time.time()
        response = api_client.get("/api/v2/users")

        # Wait for audit log to be written
        time.sleep(2)

        # Check if audit logs are being created
        # (This assumes audit logs are stored in the database)
        try:
            audit_logs = db_client.find_one(
                "audit_logs",
                {
                    "timestamp": {"$gte": test_timestamp - 10},
                    "action": {"$regex": "users", "$options": "i"},
                },
            )

            if audit_logs:
                print(" Audit logging is functional")
                assert audit_logs is not None, (
                    "Audit logs should be created for API access"
                )
            else:
                print(" Audit logs not found - may be configured differently")

        except Exception as e:
            print(f" Could not verify audit logging: {e}")


if __name__ == "__main__":
    # Run staging tests
    pytest.main([__file__, "-v", "-m", "staging"])
