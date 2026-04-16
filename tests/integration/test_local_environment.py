#!/usr/bin/env python3
"""
Local Environment Integration Tests

Tests for Docker Compose local environment (E2).
Run with: TESTING_MODE=local pytest tests/integration/test_local_environment.py -v
"""

import pytest
import time
from typing import Dict, Any

from src.environment_manager import EnvironmentManager, Environment
from src.service_manager import ServiceManager


class TestLocalEnvironment:
    """Test suite for Local Environment (E2) validation"""

    @pytest.fixture(autouse=True)
    def setup_local_environment(self):
        """Ensure we're running in local environment"""
        env_manager = EnvironmentManager()
        current_env = env_manager.get_current_environment()

        if current_env != Environment.LOCAL:
            pytest.skip(
                f"Local environment tests require local environment, got {current_env.value}"
            )

        self.env_manager = env_manager
        self.service_manager = ServiceManager()

    def test_environment_detection(self):
        """Test that local environment is properly detected"""
        detected_env = self.env_manager.detect_environment()
        assert detected_env == Environment.LOCAL

        current_env = self.env_manager.get_current_environment()
        assert current_env == Environment.LOCAL

    def test_environment_configuration(self):
        """Test that local environment configuration is loaded correctly"""
        config = self.env_manager.load_configuration(Environment.LOCAL)

        assert config.environment == Environment.LOCAL
        assert config.name is not None

        assert config.redis.host is not None
        assert config.redis.port > 0
        assert config.kafka.host is not None
        assert config.kafka.port > 0
        assert config.mongodb.host is not None
        assert config.mongodb.port > 0
        assert config.target_api.host is not None
        assert config.target_api.port > 0

    def test_redis_connectivity(self):
        """Test Redis connectivity and operations"""
        cache_client = self.service_manager.get_cache_client()

        assert cache_client.connect(), "Should be able to connect to Redis"

        test_key = "local_test_key"
        test_value = "local_test_value"

        assert cache_client.set(test_key, test_value), "Should be able to set value"
        retrieved_value = cache_client.get(test_key)
        assert retrieved_value == test_value, "Retrieved value should match set value"

        assert cache_client.exists(test_key), "Key should exist"

        assert cache_client.delete(test_key), "Should be able to delete key"
        assert not cache_client.exists(test_key), "Key should not exist after deletion"

    def test_redis_ttl(self):
        """Test Redis TTL functionality"""
        cache_client = self.service_manager.get_cache_client()

        test_key = "local_ttl_test"
        test_value = "ttl_value"

        assert cache_client.set(test_key, test_value, ttl=2), "Should set with TTL"
        assert cache_client.get(test_key) == test_value, "Value should be retrievable"

        cache_client.delete(test_key)

    def test_mongodb_connectivity(self):
        """Test MongoDB connectivity and operations"""
        db_client = self.service_manager.get_database_client()

        assert db_client.connect(), "Should be able to connect to MongoDB"

        test_collection = "local_test_collection"
        test_document = {
            "name": "local_test",
            "environment": "local",
            "timestamp": time.time(),
        }

        doc_id = db_client.insert_one(test_collection, test_document)
        assert doc_id is not None, "Should return document ID"

        found_doc = db_client.find_one(test_collection, {"name": "local_test"})
        assert found_doc is not None, "Should find inserted document"
        assert found_doc["name"] == test_document["name"], (
            "Document content should match"
        )

        count = db_client.count_documents(test_collection)
        assert count > 0, "Should have at least one document"

        update_result = db_client.update_one(
            test_collection, {"name": "local_test"}, {"$set": {"updated": True}}
        )
        assert update_result, "Should be able to update document"

        delete_result = db_client.delete_one(test_collection, {"name": "local_test"})
        assert delete_result, "Should be able to delete document"

    def test_mongodb_aggregation(self):
        """Test MongoDB aggregation pipeline"""
        db_client = self.service_manager.get_database_client()

        test_collection = "local_agg_test"

        db_client.insert_one(test_collection, {"type": "a", "value": 10})
        db_client.insert_one(test_collection, {"type": "a", "value": 20})
        db_client.insert_one(test_collection, {"type": "b", "value": 30})

        pipeline = [
            {"$match": {"type": "a"}},
            {"$group": {"_id": "$type", "total": {"$sum": "$value"}}},
        ]

        results = db_client.aggregate(test_collection, pipeline)
        assert len(results) > 0, "Should return aggregation results"

        for doc in db_client.find_many(test_collection, {}):
            db_client.delete_one(test_collection, {"_id": doc["_id"]})

    def test_mongodb_indexes(self):
        """Test MongoDB index operations"""
        db_client = self.service_manager.get_database_client()

        test_collection = "local_index_test"

        index_name = db_client.create_index(test_collection, {"email": 1}, unique=True)
        assert index_name is not None, "Should create index"

        indexes = db_client.list_indexes(test_collection)
        assert len(indexes) >= 1, "Should list indexes"

        assert db_client.drop_index(test_collection, index_name), "Should drop index"

        for doc in db_client.find_many(test_collection, {}):
            db_client.delete_one(test_collection, {"_id": doc["_id"]})

    def test_cache_and_database_integration(self):
        """Test integration between Redis cache and MongoDB"""
        cache_client = self.service_manager.get_cache_client()
        db_client = self.service_manager.get_database_client()

        test_collection = "local_integration_test"
        test_id = "test_doc_123"
        test_data = {"_id": test_id, "name": "integration_test", "value": 42}

        db_client.insert_one(test_collection, test_data)
        cache_client.set(f"doc:{test_id}", test_data)

        cached_data = cache_client.get(f"doc:{test_id}")
        assert cached_data is not None, "Should retrieve from cache"

        db_doc = db_client.find_one(test_collection, {"_id": test_id})
        assert db_doc is not None, "Should retrieve from database"

        cache_client.delete(f"doc:{test_id}")
        db_client.delete_one(test_collection, {"_id": test_id})

    def test_service_health_checks(self):
        """Test that all services report healthy"""
        health_results = self.service_manager.health_check_all()

        for service, is_healthy in health_results.items():
            assert is_healthy, f"Service {service} should be healthy"

    def test_environment_validation(self):
        """Test that local environment passes validation"""
        is_valid = self.env_manager.validate_environment(Environment.LOCAL)
        assert is_valid, "Local environment should be valid"

    def test_service_configs(self):
        """Test that service configurations are correct for local"""
        redis_config = self.env_manager.get_service_config("redis")
        kafka_config = self.env_manager.get_service_config("kafka")
        mongodb_config = self.env_manager.get_service_config("mongodb")
        api_config = self.env_manager.get_service_config("target_api")

        assert redis_config.host == "localhost", "Redis should be localhost"
        assert redis_config.port == 6379, "Redis port should be 6379"

        assert kafka_config.host == "localhost", "Kafka should be localhost"
        assert kafka_config.port == 9092, "Kafka port should be 9092"

        assert mongodb_config.host == "localhost", "MongoDB should be localhost"
        assert mongodb_config.port == 27017, "MongoDB port should be 27017"

        assert api_config.host == "localhost", "API should be localhost"
        assert api_config.port == 8080, "API port should be 8080"


class TestLocalEnvironmentMonitoring:
    """Test monitoring stack accessibility in local environment"""

    @pytest.fixture(autouse=True)
    def setup_local_environment(self):
        """Ensure we're running in local environment"""
        env_manager = EnvironmentManager()
        current_env = env_manager.get_current_environment()

        if current_env != Environment.LOCAL:
            pytest.skip(
                f"Local environment tests require local environment, got {current_env.value}"
            )

        self.env_manager = env_manager

    def test_monitoring_config(self):
        """Test that monitoring is configured for local environment"""
        config = self.env_manager.load_configuration(Environment.LOCAL)

        assert config.monitoring is not None
        assert "prometheus_url" in config.monitoring
        assert "grafana_url" in config.monitoring

    def test_prometheus_accessible(self):
        """Test that Prometheus is accessible in local environment"""
        import requests

        config = self.env_manager.load_configuration(Environment.LOCAL)
        prometheus_url = config.monitoring.get("prometheus_url")

        if prometheus_url:
            try:
                response = requests.get(f"{prometheus_url}/-/healthy", timeout=5)
                assert response.status_code == 200, "Prometheus should be healthy"
            except requests.RequestException:
                pytest.skip("Prometheus not accessible")

    def test_grafana_accessible(self):
        """Test that Grafana is accessible in local environment"""
        import requests

        config = self.env_manager.load_configuration(Environment.LOCAL)
        grafana_url = config.monitoring.get("grafana_url")

        if grafana_url:
            try:
                response = requests.get(f"{grafana_url}/api/health", timeout=5)
                assert response.status_code == 200, "Grafana should be healthy"
            except requests.RequestException:
                pytest.skip("Grafana not accessible")
