#!/usr/bin/env python3
"""
Service Manager for Day-1 Framework

Provides abstract service clients that work across all environments:
- Mock services for fast testing
- Local services for integration testing
- Production services for real validation

Supports: Redis, Kafka, MongoDB, AWS, Netskope API
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import json

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .environment_manager import get_environment_manager, Environment, ServiceConfig

# Abstract Base Classes for Service Clients


class ServiceClient(ABC):
    """Abstract base class for all service clients"""

    def __init__(self, config: ServiceConfig, environment: Environment):
        self.config = config
        self.environment = environment
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._connection = None

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the service"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the service"""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if service is healthy and accessible"""
        pass

    @abstractmethod
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for debugging"""
        pass


class CacheClient(ServiceClient):
    """Abstract cache client (Redis)"""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a key-value pair with optional TTL"""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass

    @abstractmethod
    def flush_all(self) -> bool:
        """Clear all cached data"""
        pass


class MessageClient(ServiceClient):
    """Abstract message queue client (Kafka)"""

    @abstractmethod
    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """Publish message to topic"""
        pass

    @abstractmethod
    def subscribe(self, topic: str, callback: callable) -> bool:
        """Subscribe to topic with callback"""
        pass

    @abstractmethod
    def consume(self, topic: str, timeout: int = 1000) -> List[Dict[str, Any]]:
        """Consume messages from topic"""
        pass

    @abstractmethod
    def create_topic(self, topic: str, partitions: int = 1) -> bool:
        """Create a new topic"""
        pass

    @abstractmethod
    def list_topics(self) -> List[str]:
        """List all available topics"""
        pass

    def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from topic"""
        pass


class DatabaseClient(ServiceClient):
    """Abstract database client (MongoDB)"""

    @abstractmethod
    def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        """Insert single document"""
        pass

    @abstractmethod
    def insert_many(
        self, collection: str, documents: List[Dict[str, Any]]
    ) -> List[str]:
        """Insert multiple documents"""
        pass

    @abstractmethod
    def find_one(
        self, collection: str, filter_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find single document"""
        pass

    @abstractmethod
    def find_many(
        self, collection: str, filter_dict: Dict[str, Any], limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find multiple documents"""
        pass

    @abstractmethod
    def update_one(
        self, collection: str, filter_dict: Dict[str, Any], update_dict: Dict[str, Any]
    ) -> bool:
        """Update single document"""
        pass

    @abstractmethod
    def delete_one(self, collection: str, filter_dict: Dict[str, Any]) -> bool:
        """Delete single document"""
        pass

    @abstractmethod
    def count_documents(
        self, collection: str, filter_dict: Dict[str, Any] = None
    ) -> int:
        """Count documents in collection"""
        pass

    @abstractmethod
    def create_index(
        self,
        collection: str,
        keys: Dict[str, int],
        unique: bool = False,
        name: str = None,
    ) -> str:
        """Create an index on the collection"""
        pass

    @abstractmethod
    def drop_index(self, collection: str, index_name: str) -> bool:
        """Drop an index from the collection"""
        pass

    @abstractmethod
    def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """List all indexes on the collection"""
        pass

    @abstractmethod
    def aggregate(
        self, collection: str, pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute an aggregation pipeline"""
        pass


class APIClient(ServiceClient):
    """Abstract API client (Netskope API)"""

    @abstractmethod
    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make GET request"""
        pass

    @abstractmethod
    def post(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make POST request"""
        pass

    @abstractmethod
    def put(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make PUT request"""
        pass

    @abstractmethod
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request"""
        pass

    @abstractmethod
    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Authenticate with the API"""
        pass


# Mock Service Implementations


class MockCacheClient(CacheClient):
    """Mock Redis client for testing"""

    def __init__(self, config: ServiceConfig, environment: Environment):
        super().__init__(config, environment)
        self._cache: Dict[str, Any] = {}
        self._ttl: Dict[str, datetime] = {}

    def connect(self) -> bool:
        self.logger.info("Connected to mock Redis")
        return True

    def disconnect(self) -> None:
        self.logger.info("Disconnected from mock Redis")

    def health_check(self) -> bool:
        return True

    def get_connection_info(self) -> Dict[str, Any]:
        return {
            "type": "mock",
            "host": self.config.host,
            "port": self.config.port,
            "cache_size": len(self._cache),
        }

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        self._cache[key] = value
        if ttl:
            self._ttl[key] = datetime.now().timestamp() + ttl
        self.logger.debug(f"Mock Redis SET {key}: {value}")
        return True

    def get(self, key: str) -> Optional[Any]:
        # Check TTL
        if key in self._ttl and datetime.now().timestamp() > self._ttl[key]:
            del self._cache[key]
            del self._ttl[key]
            return None

        value = self._cache.get(key)
        self.logger.debug(f"Mock Redis GET {key}: {value}")
        return value

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            if key in self._ttl:
                del self._ttl[key]
            self.logger.debug(f"Mock Redis DELETE {key}")
            return True
        return False

    def exists(self, key: str) -> bool:
        return key in self._cache

    def flush_all(self) -> bool:
        self._cache.clear()
        self._ttl.clear()
        self.logger.debug("Mock Redis FLUSHALL")
        return True


class MockMessageClient(MessageClient):
    """Mock Kafka client for testing"""

    def __init__(self, config: ServiceConfig, environment: Environment):
        super().__init__(config, environment)
        self._topics: Dict[str, List[Dict[str, Any]]] = {}
        self._subscribers: Dict[str, List[callable]] = {}

    def connect(self) -> bool:
        self.logger.info("Connected to mock Kafka")
        return True

    def disconnect(self) -> None:
        self.logger.info("Disconnected from mock Kafka")

    def health_check(self) -> bool:
        return True

    def get_connection_info(self) -> Dict[str, Any]:
        return {
            "type": "mock",
            "host": self.config.host,
            "port": self.config.port,
            "topics": list(self._topics.keys()),
        }

    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        if topic not in self._topics:
            self._topics[topic] = []

        # Add metadata
        enriched_message = {
            **message,
            "_timestamp": datetime.now().isoformat(),
            "_topic": topic,
        }

        self._topics[topic].append(enriched_message)
        self.logger.debug(f"Mock Kafka PUBLISH to {topic}: {message}")

        # Notify subscribers
        if topic in self._subscribers:
            for callback in self._subscribers[topic]:
                try:
                    callback(enriched_message)
                except Exception as e:
                    self.logger.error(f"Subscriber callback error: {e}")

        return True

    def subscribe(self, topic: str, callback: callable) -> bool:
        if topic not in self._subscribers:
            self._subscribers[topic] = []

        self._subscribers[topic].append(callback)
        self.logger.debug(f"Mock Kafka SUBSCRIBE to {topic}")
        return True

    def consume(self, topic: str, timeout: int = 1000) -> List[Dict[str, Any]]:
        messages = self._topics.get(topic, [])
        self.logger.debug(f"Mock Kafka CONSUME from {topic}: {len(messages)} messages")
        return messages

    def create_topic(self, topic: str, partitions: int = 1) -> bool:
        if topic not in self._topics:
            self._topics[topic] = []
            self.logger.debug(f"Mock Kafka CREATE TOPIC {topic}")
        return True

    def list_topics(self) -> List[str]:
        return list(self._topics.keys())

    def unsubscribe(self, topic: str) -> bool:
        if topic in self._subscribers:
            del self._subscribers[topic]
            self.logger.debug(f"Mock Kafka UNSUBSCRIBE from {topic}")
            return True
        return False


class MockDatabaseClient(DatabaseClient):
    """Mock MongoDB client for testing"""

    def __init__(self, config: ServiceConfig, environment: Environment):
        super().__init__(config, environment)
        self._collections: Dict[str, List[Dict[str, Any]]] = {}
        self._next_id = 1

    def connect(self) -> bool:
        self.logger.info("Connected to mock MongoDB")
        return True

    def disconnect(self) -> None:
        self.logger.info("Disconnected from mock MongoDB")

    def health_check(self) -> bool:
        return True

    def get_connection_info(self) -> Dict[str, Any]:
        return {
            "type": "mock",
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
            "collections": list(self._collections.keys()),
        }

    def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        if collection not in self._collections:
            self._collections[collection] = []

        # Add ID and metadata
        doc_with_id = {
            "_id": str(self._next_id),
            "_created_at": datetime.now().isoformat(),
            **document,
        }
        self._next_id += 1

        self._collections[collection].append(doc_with_id)
        self.logger.debug(
            f"Mock MongoDB INSERT ONE to {collection}: {doc_with_id['_id']}"
        )
        return doc_with_id["_id"]

    def insert_many(
        self, collection: str, documents: List[Dict[str, Any]]
    ) -> List[str]:
        ids = []
        for doc in documents:
            doc_id = self.insert_one(collection, doc)
            ids.append(doc_id)
        return ids

    def find_one(
        self, collection: str, filter_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if collection not in self._collections:
            return None

        for doc in self._collections[collection]:
            if self._matches_filter(doc, filter_dict):
                self.logger.debug(
                    f"Mock MongoDB FIND ONE in {collection}: {doc['_id']}"
                )
                return doc

        return None

    def find_many(
        self, collection: str, filter_dict: Dict[str, Any], limit: int = 100
    ) -> List[Dict[str, Any]]:
        if collection not in self._collections:
            return []

        matches = []
        for doc in self._collections[collection]:
            if self._matches_filter(doc, filter_dict):
                matches.append(doc)
                if len(matches) >= limit:
                    break

        self.logger.debug(
            f"Mock MongoDB FIND MANY in {collection}: {len(matches)} documents"
        )
        return matches

    def update_one(
        self, collection: str, filter_dict: Dict[str, Any], update_dict: Dict[str, Any]
    ) -> bool:
        if collection not in self._collections:
            return False

        for doc in self._collections[collection]:
            if self._matches_filter(doc, filter_dict):
                doc.update(update_dict)
                doc["_updated_at"] = datetime.now().isoformat()
                self.logger.debug(
                    f"Mock MongoDB UPDATE ONE in {collection}: {doc['_id']}"
                )
                return True

        return False

    def delete_one(self, collection: str, filter_dict: Dict[str, Any]) -> bool:
        if collection not in self._collections:
            return False

        for i, doc in enumerate(self._collections[collection]):
            if self._matches_filter(doc, filter_dict):
                del self._collections[collection][i]
                self.logger.debug(
                    f"Mock MongoDB DELETE ONE in {collection}: {doc['_id']}"
                )
                return True

        return False

    def count_documents(
        self, collection: str, filter_dict: Dict[str, Any] = None
    ) -> int:
        if collection not in self._collections:
            return 0

        if filter_dict is None:
            return len(self._collections[collection])

        count = 0
        for doc in self._collections[collection]:
            if self._matches_filter(doc, filter_dict):
                count += 1

        return count

    def create_index(
        self,
        collection: str,
        keys: Dict[str, int],
        unique: bool = False,
        name: str = None,
    ) -> str:
        if not hasattr(self, "_indexes"):
            self._indexes: Dict[str, List[Dict[str, Any]]] = {}
        if collection not in self._indexes:
            self._indexes[collection] = []
        index_name = name or f"idx_{len(self._indexes[collection])}"
        self._indexes[collection].append(
            {"name": index_name, "keys": keys, "unique": unique}
        )
        self.logger.debug(f"Mock MongoDB CREATE INDEX {index_name} on {collection}")
        return index_name

    def drop_index(self, collection: str, index_name: str) -> bool:
        if not hasattr(self, "_indexes") or collection not in self._indexes:
            return False
        self._indexes[collection] = [
            idx for idx in self._indexes[collection] if idx["name"] != index_name
        ]
        self.logger.debug(f"Mock MongoDB DROP INDEX {index_name} from {collection}")
        return True

    def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        if not hasattr(self, "_indexes") or collection not in self._indexes:
            return [{"name": "_id_", "keys": {"_id": 1}, "unique": False}]
        return self._indexes[collection]

    def aggregate(
        self, collection: str, pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if collection not in self._collections:
            return []
        results = list(self._collections[collection])
        for stage in pipeline:
            if "$match" in stage:
                results = [
                    doc for doc in results if self._matches_filter(doc, stage["$match"])
                ]
            elif "$group" in stage:
                group_field = stage["$group"].get("_id")
                if group_field:
                    grouped = {}
                    for doc in results:
                        key = doc.get(group_field.replace("$", ""), "unknown")
                        if key not in grouped:
                            grouped[key] = {"_id": key}
                            for agg_field, agg_op in stage["$group"].items():
                                if agg_field != "_id" and isinstance(agg_op, dict):
                                    grouped[key][agg_field] = 0
                    for doc in results:
                        key = doc.get(group_field.replace("$", ""), "unknown")
                        for agg_field, agg_op in stage["$group"].items():
                            if agg_field != "_id" and isinstance(agg_op, dict):
                                if "$sum" in agg_op:
                                    field_name = agg_op["$sum"].replace("$", "")
                                    grouped[key][agg_field] = grouped[key].get(
                                        agg_field, 0
                                    ) + doc.get(field_name, 0)
                                elif "$avg" in agg_op:
                                    field_name = agg_op["$avg"].replace("$", "")
                                    grouped[key][agg_field] = grouped[key].get(
                                        agg_field, 0
                                    ) + doc.get(field_name, 0)
                    results = list(grouped.values())
        self.logger.debug(
            f"Mock MongoDB AGGREGATE on {collection}: {len(results)} results"
        )
        return results

    def _matches_filter(
        self, document: Dict[str, Any], filter_dict: Dict[str, Any]
    ) -> bool:
        """Simple filter matching for mock implementation"""
        if not filter_dict:
            return True

        for key, value in filter_dict.items():
            if key not in document or document[key] != value:
                return False

        return True


class MockAPIClient(APIClient):
    """Mock Netskope API client for testing"""

    def __init__(self, config: ServiceConfig, environment: Environment):
        super().__init__(config, environment)
        self._authenticated = False
        self._request_count = 0

    def connect(self) -> bool:
        self.logger.info("Connected to mock Netskope API")
        return True

    def disconnect(self) -> None:
        self.logger.info("Disconnected from mock Netskope API")

    def health_check(self) -> bool:
        return True

    def get_connection_info(self) -> Dict[str, Any]:
        return {
            "type": "mock",
            "host": self.config.host,
            "port": self.config.port,
            "authenticated": self._authenticated,
            "request_count": self._request_count,
        }

    def authenticate(self, credentials: Dict[str, str]) -> bool:
        # Mock authentication always succeeds
        self._authenticated = True
        self.logger.debug("Mock API authentication successful")
        return True

    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        self._request_count += 1
        self.logger.debug(f"Mock API GET {endpoint}")

        # Return mock responses based on endpoint
        return self._generate_mock_response("GET", endpoint, params)

    def post(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        self._request_count += 1
        self.logger.debug(f"Mock API POST {endpoint}")

        return self._generate_mock_response("POST", endpoint, data)

    def put(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        self._request_count += 1
        self.logger.debug(f"Mock API PUT {endpoint}")

        return self._generate_mock_response("PUT", endpoint, data)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        self._request_count += 1
        self.logger.debug(f"Mock API DELETE {endpoint}")

        return self._generate_mock_response("DELETE", endpoint)

    def _generate_mock_response(
        self, method: str, endpoint: str, data: Any = None
    ) -> Dict[str, Any]:
        """Generate realistic mock responses"""

        # Common response structure
        base_response = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "endpoint": endpoint,
        }

        # Endpoint-specific responses
        if "/events" in endpoint:
            base_response["data"] = {
                "events": [
                    {
                        "id": f"evt_{i}",
                        "type": "security_event",
                        "severity": "medium",
                        "timestamp": datetime.now().isoformat(),
                    }
                    for i in range(5)
                ],
                "total": 5,
            }
        elif "/policies" in endpoint:
            base_response["data"] = {
                "policies": [
                    {
                        "id": "pol_1",
                        "name": "DLP Policy",
                        "type": "dlp",
                        "enabled": True,
                    }
                ]
            }
        elif "/users" in endpoint:
            base_response["data"] = {
                "users": [
                    {
                        "id": "usr_1",
                        "username": "test_user",
                        "role": "user",
                        "active": True,
                    }
                ]
            }
        else:
            base_response["data"] = {"message": "Mock response"}

        return base_response


# Real Service Implementations (stubs for now)


class RealCacheClient(CacheClient):
    """Real Redis client implementation"""

    def connect(self) -> bool:
        try:
            import redis

            self._connection = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                ssl=self.config.ssl_enabled,
                socket_timeout=self.config.timeout,
            )
            self._connection.ping()
            self.logger.info(
                f"Connected to Redis at {self.config.host}:{self.config.port}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            return False

    def disconnect(self) -> None:
        if self._connection:
            self._connection.close()
            self.logger.info("Disconnected from Redis")

    def health_check(self) -> bool:
        if not REDIS_AVAILABLE:
            return True
        try:
            return self._connection.ping() if self._connection else False
        except (redis.ConnectionError, redis.TimeoutError) as e:
            self.logger.debug(f"Redis health check failed: {e}")
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        return {
            "type": "real",
            "host": self.config.host,
            "port": self.config.port,
            "ssl_enabled": self.config.ssl_enabled,
            "connected": self._connection is not None,
        }

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return self._connection.set(key, value, ex=ttl)
        except Exception as e:
            self.logger.error(f"Redis SET error: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        try:
            value = self._connection.get(key)
            if value:
                try:
                    return json.loads(value.decode("utf-8"))
                except json.JSONDecodeError:
                    return value.decode("utf-8")
            return None
        except Exception as e:
            self.logger.error(f"Redis GET error: {e}")
            return None

    def delete(self, key: str) -> bool:
        try:
            return bool(self._connection.delete(key))
        except Exception as e:
            self.logger.error(f"Redis DELETE error: {e}")
            return False

    def exists(self, key: str) -> bool:
        try:
            return bool(self._connection.exists(key))
        except Exception as e:
            self.logger.error(f"Redis EXISTS error: {e}")
            return False

    def flush_all(self) -> bool:
        try:
            return self._connection.flushall()
        except Exception as e:
            self.logger.error(f"Redis FLUSHALL error: {e}")
            return False


# Service Manager Class


class ServiceManager:
    """Manages service clients across different environments"""

    def __init__(self):
        self.env_manager = get_environment_manager()
        self.logger = logging.getLogger(__name__)
        self._clients: Dict[str, ServiceClient] = {}

    def get_cache_client(self) -> CacheClient:
        """Get Redis cache client for current environment"""
        return self._get_or_create_client("cache", self._create_cache_client)

    def get_message_client(self) -> MessageClient:
        """Get Kafka message client for current environment"""
        return self._get_or_create_client("message", self._create_message_client)

    def get_database_client(self) -> DatabaseClient:
        """Get MongoDB database client for current environment"""
        return self._get_or_create_client("database", self._create_database_client)

    def get_api_client(self) -> APIClient:
        """Get Netskope API client for current environment"""
        return self._get_or_create_client("api", self._create_api_client)

    def health_check_all(self) -> Dict[str, bool]:
        """Check health of all services"""
        results = {}

        # Service types and their factory methods
        service_factories = {
            "cache": self.get_cache_client,
            "message": self.get_message_client,
            "database": self.get_database_client,
            "api": self.get_api_client,
        }

        for service_name, factory_func in service_factories.items():
            try:
                # Get or create the client (this will also connect)
                client = factory_func()
                results[service_name] = client.health_check()
            except Exception as e:
                self.logger.error(f"Health check failed for {service_name}: {e}")
                results[service_name] = False

        return results

    def disconnect_all(self) -> None:
        """Disconnect all service clients"""
        for client in self._clients.values():
            try:
                client.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting client: {e}")

        self._clients.clear()

    def _get_or_create_client(
        self, service_type: str, factory_func: callable
    ) -> ServiceClient:
        """Get existing client or create new one"""
        if service_type not in self._clients:
            self._clients[service_type] = factory_func()

            # Connect to service
            if not self._clients[service_type].connect():
                self.logger.warning(f"Failed to connect to {service_type} service")

        return self._clients[service_type]

    def _create_cache_client(self) -> CacheClient:
        """Create appropriate cache client based on environment"""
        environment = self.env_manager.get_current_environment()
        config = self.env_manager.get_service_config("redis")

        if environment == Environment.MOCK:
            return MockCacheClient(config, environment)
        else:
            return RealCacheClient(config, environment)

    def _create_message_client(self) -> MessageClient:
        """Create appropriate message client based on environment"""
        environment = self.env_manager.get_current_environment()
        config = self.env_manager.get_service_config("kafka")

        # For local development, use mock client to avoid kafka-python issues
        if environment in [Environment.MOCK, Environment.LOCAL]:
            return MockMessageClient(config, environment)
        else:
            try:
                from src.real_service_clients import create_real_message_client

                return create_real_message_client(config, environment)
            except ImportError:
                self.logger.warning("Real Kafka client not available, using mock")
                return MockMessageClient(config, environment)

    def _create_database_client(self) -> DatabaseClient:
        """Create appropriate database client based on environment"""
        environment = self.env_manager.get_current_environment()
        config = self.env_manager.get_service_config("mongodb")

        if environment == Environment.MOCK:
            return MockDatabaseClient(config, environment)
        else:
            try:
                from src.real_service_clients import create_real_database_client

                return create_real_database_client(config, environment)
            except ImportError:
                self.logger.warning("Real MongoDB client not available, using mock")
                return MockDatabaseClient(config, environment)

    def _create_api_client(self) -> APIClient:
        """Create appropriate API client based on environment"""
        environment = self.env_manager.get_current_environment()
        config = self.env_manager.get_service_config("netskope_api")

        if environment == Environment.MOCK:
            return MockAPIClient(config, environment)
        else:
            try:
                from src.real_service_clients import create_real_api_client

                return create_real_api_client(config, environment)
            except ImportError:
                self.logger.warning(
                    "Real Netskope API client not available, using mock"
                )
                return MockAPIClient(config, environment)


# Global service manager instance with thread safety
import threading

_service_manager = None
_service_manager_lock = threading.Lock()


def get_service_manager() -> ServiceManager:
    """Get global service manager instance (thread-safe)"""
    global _service_manager
    if _service_manager is None:
        with _service_manager_lock:
            if _service_manager is None:
                _service_manager = ServiceManager()
    return _service_manager


def reset_service_manager() -> None:
    """Reset the global service manager (useful for testing)"""
    global _service_manager
    with _service_manager_lock:
        if _service_manager is not None:
            _service_manager.disconnect_all()
            _service_manager = None


# Convenience functions
def get_cache_client() -> CacheClient:
    """Get cache client (convenience function)"""
    return get_service_manager().get_cache_client()


def get_message_client() -> MessageClient:
    """Get message client (convenience function)"""
    return get_service_manager().get_message_client()


def get_database_client() -> DatabaseClient:
    """Get database client (convenience function)"""
    return get_service_manager().get_database_client()


def get_api_client() -> APIClient:
    """Get API client (convenience function)"""
    return get_service_manager().get_api_client()


# CLI interface for service management
if __name__ == "__main__":
    import sys

    def print_usage():
        print("Usage: python service_manager.py <command>")
        print("Commands:")
        print("  health                    - Check health of all services")
        print("  info                      - Show service connection information")
        print("  test-cache               - Test cache operations")
        print("  test-message             - Test message operations")
        print("  test-database            - Test database operations")
        print("  test-api                 - Test API operations")

    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()
    service_manager = ServiceManager()

    if command == "health":
        print("Checking service health...")
        health_results = service_manager.health_check_all()

        for service, is_healthy in health_results.items():
            status = " Healthy" if is_healthy else " Unhealthy"
            print(f"  {service}: {status}")

    elif command == "info":
        print("Service connection information:")

        clients = {
            "cache": service_manager.get_cache_client(),
            "message": service_manager.get_message_client(),
            "database": service_manager.get_database_client(),
            "api": service_manager.get_api_client(),
        }

        for service_name, client in clients.items():
            info = client.get_connection_info()
            print(f"  {service_name}: {info}")

    elif command == "test-cache":
        print("Testing cache operations...")
        cache = service_manager.get_cache_client()

        # Test basic operations
        cache.set("test_key", "test_value")
        value = cache.get("test_key")
        print(f"  SET/GET: {value}")

        exists = cache.exists("test_key")
        print(f"  EXISTS: {exists}")

        deleted = cache.delete("test_key")
        print(f"  DELETE: {deleted}")

    elif command == "test-message":
        print("Testing message operations...")
        message_client = service_manager.get_message_client()

        # Test basic operations
        message_client.create_topic("test_topic")
        message_client.publish("test_topic", {"message": "Hello, World!"})

        messages = message_client.consume("test_topic")
        print(f"  Published and consumed {len(messages)} messages")

    elif command == "test-database":
        print("Testing database operations...")
        db = service_manager.get_database_client()

        # Test basic operations
        doc_id = db.insert_one("test_collection", {"name": "test", "value": 123})
        print(f"  INSERT: {doc_id}")

        doc = db.find_one("test_collection", {"name": "test"})
        print(f"  FIND: {doc}")

        count = db.count_documents("test_collection")
        print(f"  COUNT: {count}")

    elif command == "test-api":
        print("Testing API operations...")
        api = service_manager.get_api_client()

        # Test basic operations
        api.authenticate({"username": "test", "password": "test"})

        events = api.get("/api/v2/events")
        print(f"  GET events: {len(events.get('data', {}).get('events', []))} events")

        policies = api.get("/api/v2/policies")
        print(
            f"  GET policies: {len(policies.get('data', {}).get('policies', []))} policies"
        )

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)

    # Cleanup
    service_manager.disconnect_all()
