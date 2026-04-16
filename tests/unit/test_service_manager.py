#!/usr/bin/env python3
"""
Unit tests for ServiceManager module.
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime

from src.service_manager import (
    ServiceManager,
    ServiceConfig,
    Environment,
    CacheClient,
    MessageClient,
    DatabaseClient,
    APIClient,
    MockCacheClient,
    MockMessageClient,
    MockDatabaseClient,
    MockAPIClient,
    RealCacheClient,
)


class TestMockCacheClient:
    """Tests for MockCacheClient"""

    def setup_method(self):
        """Setup for each test"""
        self.config = ServiceConfig(host="localhost", port=6379)
        self.client = MockCacheClient(self.config, Environment.MOCK)

    def test_connect(self):
        """Test mock cache client connection"""
        assert self.client.connect() is True

    def test_disconnect(self):
        """Test mock cache client disconnection"""
        self.client.disconnect()

    def test_health_check(self):
        """Test mock cache health check"""
        assert self.client.health_check() is True

    def test_set_and_get(self):
        """Test basic set and get operations"""
        assert self.client.set("key1", "value1") is True
        assert self.client.get("key1") == "value1"

    def test_set_with_ttl(self):
        """Test set with TTL"""
        assert self.client.set("key2", "value2", ttl=3600) is True
        assert self.client.get("key2") == "value2"

    def test_get_nonexistent_key(self):
        """Test getting non-existent key"""
        assert self.client.get("nonexistent") is None

    def test_delete(self):
        """Test delete operation"""
        self.client.set("key3", "value3")
        assert self.client.delete("key3") is True
        assert self.client.get("key3") is None

    def test_delete_nonexistent(self):
        """Test deleting non-existent key"""
        assert self.client.delete("nonexistent") is False

    def test_exists(self):
        """Test exists check"""
        self.client.set("key4", "value4")
        assert self.client.exists("key4") is True
        assert self.client.exists("nonexistent") is False

    def test_flush_all(self):
        """Test flush all operation"""
        self.client.set("key1", "value1")
        self.client.set("key2", "value2")
        assert self.client.flush_all() is True
        assert self.client.get("key1") is None
        assert self.client.get("key2") is None

    def test_get_connection_info(self):
        """Test connection info"""
        info = self.client.get_connection_info()
        assert info["type"] == "mock"
        assert info["host"] == "localhost"
        assert info["port"] == 6379


class TestMockMessageClient:
    """Tests for MockMessageClient"""

    def setup_method(self):
        """Setup for each test"""
        self.config = ServiceConfig(host="localhost", port=9092)
        self.client = MockMessageClient(self.config, Environment.MOCK)

    def test_connect(self):
        """Test mock message client connection"""
        assert self.client.connect() is True

    def test_create_topic(self):
        """Test topic creation"""
        assert self.client.create_topic("test_topic") is True
        assert "test_topic" in self.client.list_topics()

    def test_publish(self):
        """Test message publishing"""
        self.client.create_topic("test_topic")
        message = {"event": "test", "data": "sample"}
        assert self.client.publish("test_topic", message) is True

    def test_consume(self):
        """Test message consumption"""
        self.client.create_topic("test_topic")
        self.client.publish("test_topic", {"event": "test"})
        messages = self.client.consume("test_topic")
        assert len(messages) == 1
        assert messages[0]["event"] == "test"

    def test_subscribe(self):
        """Test subscription"""
        callback_called = []

        def callback(msg):
            callback_called.append(msg)

        self.client.subscribe("test_topic", callback)
        self.client.publish("test_topic", {"event": "test"})

        assert len(callback_called) == 1
        assert callback_called[0]["event"] == "test"

    def test_subscribe_with_exception(self):
        """Test that subscriber exceptions don't crash"""

        def bad_callback(msg):
            raise Exception("Callback error")

        self.client.subscribe("test_topic", bad_callback)
        result = self.client.publish("test_topic", {"event": "test"})
        assert result is True

    def test_list_topics(self):
        """Test listing topics"""
        self.client.create_topic("topic1")
        self.client.create_topic("topic2")
        topics = self.client.list_topics()
        assert "topic1" in topics
        assert "topic2" in topics

    def test_get_connection_info(self):
        """Test connection info"""
        self.client.create_topic("test_topic")
        info = self.client.get_connection_info()
        assert info["type"] == "mock"
        assert "test_topic" in info["topics"]


class TestMockDatabaseClient:
    """Tests for MockDatabaseClient"""

    def setup_method(self):
        """Setup for each test"""
        self.config = ServiceConfig(host="localhost", port=27017, database="test_db")
        self.client = MockDatabaseClient(self.config, Environment.MOCK)

    def test_connect(self):
        """Test mock database connection"""
        assert self.client.connect() is True

    def test_insert_one(self):
        """Test single document insertion"""
        doc_id = self.client.insert_one("collection1", {"name": "test"})
        assert doc_id is not None
        assert doc_id.startswith("1")

    def test_insert_many(self):
        """Test multiple document insertion"""
        docs = [{"name": f"doc{i}"} for i in range(3)]
        ids = self.client.insert_many("collection1", docs)
        assert len(ids) == 3

    def test_find_one(self):
        """Test finding single document"""
        self.client.insert_one("collection1", {"name": "findme", "value": 42})
        doc = self.client.find_one("collection1", {"name": "findme"})
        assert doc is not None
        assert doc["name"] == "findme"
        assert doc["value"] == 42

    def test_find_one_not_found(self):
        """Test finding non-existent document"""
        doc = self.client.find_one("collection1", {"name": "nonexistent"})
        assert doc is None

    def test_find_many(self):
        """Test finding multiple documents"""
        for i in range(5):
            self.client.insert_one("collection1", {"index": i})
        docs = self.client.find_many("collection1", {})
        assert len(docs) == 5

    def test_find_many_with_filter(self):
        """Test finding with filter"""
        self.client.insert_one("collection1", {"type": "a"})
        self.client.insert_one("collection1", {"type": "b"})
        self.client.insert_one("collection1", {"type": "a"})
        docs = self.client.find_many("collection1", {"type": "a"})
        assert len(docs) == 2

    def test_update_one(self):
        """Test updating document"""
        doc_id = self.client.insert_one("collection1", {"name": "update", "old": True})
        result = self.client.update_one(
            "collection1", {"name": "update"}, {"new": True, "old": False}
        )
        assert result is True
        doc = self.client.find_one("collection1", {"_id": doc_id})
        assert doc["new"] is True
        assert doc["old"] is False

    def test_update_one_not_found(self):
        """Test updating non-existent document"""
        result = self.client.update_one(
            "collection1", {"name": "nonexistent"}, {"new": True}
        )
        assert result is False

    def test_delete_one(self):
        """Test deleting document"""
        doc_id = self.client.insert_one("collection1", {"name": "delete"})
        result = self.client.delete_one("collection1", {"name": "delete"})
        assert result is True
        assert self.client.find_one("collection1", {"name": "delete"}) is None

    def test_delete_one_not_found(self):
        """Test deleting non-existent document"""
        result = self.client.delete_one("collection1", {"name": "nonexistent"})
        assert result is False

    def test_count_documents(self):
        """Test counting documents"""
        for i in range(5):
            self.client.insert_one("collection1", {"index": i})
        count = self.client.count_documents("collection1")
        assert count == 5

    def test_count_documents_with_filter(self):
        """Test counting with filter"""
        self.client.insert_one("collection1", {"type": "a"})
        self.client.insert_one("collection1", {"type": "b"})
        self.client.insert_one("collection1", {"type": "a"})
        count = self.client.count_documents("collection1", {"type": "a"})
        assert count == 2


class TestMockAPIClient:
    """Tests for MockAPIClient"""

    def setup_method(self):
        """Setup for each test"""
        self.config = ServiceConfig(host="localhost", port=8080)
        self.client = MockAPIClient(self.config, Environment.MOCK)

    def test_connect(self):
        """Test mock API connection"""
        assert self.client.connect() is True

    def test_authenticate(self):
        """Test authentication"""
        result = self.client.authenticate({"api_key": "test-key"})
        assert result is True
        assert self.client._authenticated is True

    def test_get_events(self):
        """Test GET events endpoint"""
        response = self.client.get("/api/v2/events")
        assert response["status"] == "success"
        assert "data" in response
        assert "events" in response["data"]

    def test_get_policies(self):
        """Test GET policies endpoint"""
        response = self.client.get("/api/v2/policies")
        assert response["status"] == "success"
        assert "data" in response
        assert "policies" in response["data"]

    def test_get_users(self):
        """Test GET users endpoint"""
        response = self.client.get("/api/v2/users")
        assert response["status"] == "success"
        assert "data" in response
        assert "users" in response["data"]

    def test_post(self):
        """Test POST request"""
        response = self.client.post("/api/v2/events", {"event": "test"})
        assert response["status"] == "success"

    def test_put(self):
        """Test PUT request"""
        response = self.client.put("/api/v2/events/1", {"event": "updated"})
        assert response["status"] == "success"

    def test_delete(self):
        """Test DELETE request"""
        response = self.client.delete("/api/v2/events/1")
        assert response["status"] == "success"

    def test_request_count(self):
        """Test request counting"""
        initial_count = self.client._request_count
        self.client.get("/api/v2/events")
        assert self.client._request_count == initial_count + 1


class TestServiceManager:
    """Tests for ServiceManager"""

    def setup_method(self):
        """Setup for each test"""
        with patch("src.service_manager.get_environment_manager") as mock_env:
            mock_manager = MagicMock()
            mock_manager.get_current_environment.return_value = Environment.MOCK
            mock_manager.get_service_config.return_value = ServiceConfig(
                host="localhost", port=6379
            )
            mock_env.return_value = mock_manager
            self.manager = ServiceManager()

    def test_get_cache_client(self):
        """Test getting cache client"""
        with patch("src.service_manager.get_environment_manager") as mock_env:
            mock_manager = MagicMock()
            mock_manager.get_current_environment.return_value = Environment.MOCK
            mock_manager.get_service_config.return_value = ServiceConfig(
                host="localhost", port=6379
            )
            mock_env.return_value = mock_manager

            manager = ServiceManager()
            cache = manager.get_cache_client()
            assert isinstance(cache, MockCacheClient)

    def test_get_message_client(self):
        """Test getting message client"""
        with patch("src.service_manager.get_environment_manager") as mock_env:
            mock_manager = MagicMock()
            mock_manager.get_current_environment.return_value = Environment.MOCK
            mock_manager.get_service_config.return_value = ServiceConfig(
                host="localhost", port=9092
            )
            mock_env.return_value = mock_manager

            manager = ServiceManager()
            message = manager.get_message_client()
            assert isinstance(message, MockMessageClient)

    def test_get_database_client(self):
        """Test getting database client"""
        with patch("src.service_manager.get_environment_manager") as mock_env:
            mock_manager = MagicMock()
            mock_manager.get_current_environment.return_value = Environment.MOCK
            mock_manager.get_service_config.return_value = ServiceConfig(
                host="localhost", port=27017
            )
            mock_env.return_value = mock_manager

            manager = ServiceManager()
            db = manager.get_database_client()
            assert isinstance(db, MockDatabaseClient)

    def test_get_api_client(self):
        """Test getting API client"""
        with patch("src.service_manager.get_environment_manager") as mock_env:
            mock_manager = MagicMock()
            mock_manager.get_current_environment.return_value = Environment.MOCK
            mock_manager.get_service_config.return_value = ServiceConfig(
                host="localhost", port=8080
            )
            mock_env.return_value = mock_manager

            manager = ServiceManager()
            api = manager.get_api_client()
            assert isinstance(api, MockAPIClient)

    def test_health_check_all(self):
        """Test health check for all services"""
        with patch("src.service_manager.get_environment_manager") as mock_env:
            mock_manager = MagicMock()
            mock_manager.get_current_environment.return_value = Environment.MOCK
            mock_manager.get_service_config.return_value = ServiceConfig(
                host="localhost", port=6379
            )
            mock_env.return_value = mock_manager

            manager = ServiceManager()
            results = manager.health_check_all()

            assert "cache" in results
            assert "message" in results
            assert "database" in results
            assert "api" in results

    def test_disconnect_all(self):
        """Test disconnecting all clients"""
        with patch("src.service_manager.get_environment_manager") as mock_env:
            mock_manager = MagicMock()
            mock_manager.get_current_environment.return_value = Environment.MOCK
            mock_manager.get_service_config.return_value = ServiceConfig(
                host="localhost", port=6379
            )
            mock_env.return_value = mock_manager

            manager = ServiceManager()
            manager.get_cache_client()
            manager.get_message_client()
            manager.get_database_client()
            manager.get_api_client()

            manager.disconnect_all()
            assert len(manager._clients) == 0

    def test_client_caching(self):
        """Test that clients are cached"""
        with patch("src.service_manager.get_environment_manager") as mock_env:
            mock_manager = MagicMock()
            mock_manager.get_current_environment.return_value = Environment.MOCK
            mock_manager.get_service_config.return_value = ServiceConfig(
                host="localhost", port=6379
            )
            mock_env.return_value = mock_manager

            manager = ServiceManager()
            cache1 = manager.get_cache_client()
            cache2 = manager.get_cache_client()
            assert cache1 is cache2


class TestRealCacheClient:
    """Tests for RealCacheClient"""

    def test_connect_success(self):
        """Test successful Redis connection"""
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_instance.ping.return_value = True
            mock_redis.return_value = mock_instance

            config = ServiceConfig(host="localhost", port=6379)
            client = RealCacheClient(config, Environment.LOCAL)
            result = client.connect()

            assert result is True
            assert client._connection is not None

    def test_connect_failure(self):
        """Test failed Redis connection"""
        with patch("redis.Redis") as mock_redis:
            mock_redis.side_effect = Exception("Connection failed")

            config = ServiceConfig(host="localhost", port=6379)
            client = RealCacheClient(config, Environment.LOCAL)
            result = client.connect()

            assert result is False

    def test_health_check(self):
        """Test Redis health check"""
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_instance.ping.return_value = True
            mock_redis.return_value = mock_instance

            config = ServiceConfig(host="localhost", port=6379)
            client = RealCacheClient(config, Environment.LOCAL)
            client.connect()
            result = client.health_check()

            assert result is True

    def test_set_string_value(self):
        """Test setting string value"""
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_instance.set.return_value = True
            mock_redis.return_value = mock_instance

            config = ServiceConfig(host="localhost", port=6379)
            client = RealCacheClient(config, Environment.LOCAL)
            client.connect()
            result = client.set("key", "value")

            assert result is True

    def test_set_dict_value(self):
        """Test setting dict value (JSON serialization)"""
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_instance.set.return_value = True
            mock_redis.return_value = mock_instance

            config = ServiceConfig(host="localhost", port=6379)
            client = RealCacheClient(config, Environment.LOCAL)
            client.connect()
            result = client.set("key", {"nested": "value"})

            assert result is True

    def test_get_value(self):
        """Test getting value"""
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_instance.get.return_value = b"test_value"
            mock_redis.return_value = mock_instance

            config = ServiceConfig(host="localhost", port=6379)
            client = RealCacheClient(config, Environment.LOCAL)
            client.connect()
            result = client.get("key")

            assert result == "test_value"

    def test_get_json_value(self):
        """Test getting JSON value"""
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_instance.get.return_value = b'{"nested": "value"}'
            mock_redis.return_value = mock_instance

            config = ServiceConfig(host="localhost", port=6379)
            client = RealCacheClient(config, Environment.LOCAL)
            client.connect()
            result = client.get("key")

            assert result == {"nested": "value"}

    def test_delete(self):
        """Test delete operation"""
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_instance.delete.return_value = 1
            mock_redis.return_value = mock_instance

            config = ServiceConfig(host="localhost", port=6379)
            client = RealCacheClient(config, Environment.LOCAL)
            client.connect()
            result = client.delete("key")

            assert result is True

    def test_exists(self):
        """Test exists check"""
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_instance.exists.return_value = 1
            mock_redis.return_value = mock_instance

            config = ServiceConfig(host="localhost", port=6379)
            client = RealCacheClient(config, Environment.LOCAL)
            client.connect()
            result = client.exists("key")

            assert result is True


class TestMockDatabaseClientAdvanced:
    """Tests for advanced MockDatabaseClient methods"""

    def setup_method(self):
        """Setup for each test"""
        self.config = ServiceConfig(host="localhost", port=27017, database="test_db")
        self.client = MockDatabaseClient(self.config, Environment.MOCK)

    def test_create_index(self):
        """Test creating an index"""
        self.client.insert_one("collection1", {"name": "test", "value": 1})
        index_name = self.client.create_index("collection1", {"name": 1}, unique=True)
        assert index_name is not None
        indexes = self.client.list_indexes("collection1")
        assert any(idx["name"] == index_name for idx in indexes)

    def test_create_index_with_name(self):
        """Test creating an index with custom name"""
        self.client.insert_one("collection1", {"name": "test", "value": 1})
        index_name = self.client.create_index(
            "collection1", {"email": 1}, name="email_idx"
        )
        assert index_name == "email_idx"

    def test_drop_index(self):
        """Test dropping an index"""
        self.client.insert_one("collection1", {"name": "test", "value": 1})
        index_name = self.client.create_index("collection1", {"name": 1})
        result = self.client.drop_index("collection1", index_name)
        assert result is True

    def test_drop_index_not_found(self):
        """Test dropping non-existent index"""
        result = self.client.drop_index("collection1", "nonexistent")
        assert result is False

    def test_list_indexes(self):
        """Test listing indexes"""
        self.client.insert_one("collection1", {"name": "test", "value": 1})
        self.client.create_index("collection1", {"name": 1})
        self.client.create_index("collection1", {"email": 1})
        indexes = self.client.list_indexes("collection1")
        assert len(indexes) >= 2

    def test_aggregate_match(self):
        """Test aggregation with $match stage"""
        self.client.insert_one("collection1", {"type": "a", "value": 10})
        self.client.insert_one("collection1", {"type": "b", "value": 20})
        self.client.insert_one("collection1", {"type": "a", "value": 30})
        pipeline = [{"$match": {"type": "a"}}]
        results = self.client.aggregate("collection1", pipeline)
        assert len(results) == 2

    def test_aggregate_group(self):
        """Test aggregation with $group stage"""
        self.client.insert_one("collection1", {"type": "a", "value": 10})
        self.client.insert_one("collection1", {"type": "b", "value": 20})
        self.client.insert_one("collection1", {"type": "a", "value": 30})
        pipeline = [{"$group": {"_id": "$type", "total": {"$sum": "$value"}}}]
        results = self.client.aggregate("collection1", pipeline)
        assert len(results) == 2
        type_totals = {r["_id"]: r.get("total", 0) for r in results}
        assert type_totals.get("a", 0) == 40
        assert type_totals.get("b", 0) == 20


class TestMockMessageClientAdvanced:
    """Tests for advanced MockMessageClient methods"""

    def setup_method(self):
        """Setup for each test"""
        self.config = ServiceConfig(host="localhost", port=9092)
        self.client = MockMessageClient(self.config, Environment.MOCK)

    def test_unsubscribe(self):
        """Test unsubscribing from topic"""
        callback_called = []

        def callback(msg):
            callback_called.append(msg)

        self.client.subscribe("test_topic", callback)
        self.client.unsubscribe("test_topic")
        self.client.publish("test_topic", {"event": "test"})
        assert len(callback_called) == 0

    def test_unsubscribe_not_subscribed(self):
        """Test unsubscribing from non-subscribed topic"""
        result = self.client.unsubscribe("nonexistent_topic")
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
