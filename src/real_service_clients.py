#!/usr/bin/env python3
"""
Real Service Client Implementations for Day-1 Framework

This module contains the production-ready implementations of service clients
that connect to real services (Redis, Kafka, MongoDB, Netskope API).
"""

import json
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

from .service_manager import (
    ServiceConfig,
    Environment,
    MessageClient,
    DatabaseClient,
    APIClient,
)

# Configuration constants
MAX_CONSUMER_MESSAGES = 100
DEFAULT_TIMEOUT_MS = 5000
DEFAULT_PARTITIONS = 1
MAX_BATCH_SIZE = 16384


class RealMessageClient(MessageClient):
    """Real Kafka client implementation using kafka-python"""

    def __init__(self, config: ServiceConfig, environment: Environment):
        super().__init__(config, environment)
        self._producer = None
        self._consumers = {}
        self._admin_client = None
        self._consumer_threads: Dict[str, threading.Thread] = {}
        self._running: Dict[str, bool] = {}

    def connect(self) -> bool:
        """Establish connection to Kafka cluster"""
        try:
            from kafka import KafkaProducer, KafkaAdminClient
            from kafka.errors import KafkaError

            # Create producer with proper configuration
            self._producer = KafkaProducer(
                bootstrap_servers=[f"{self.config.host}:{self.config.port}"],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,
                request_timeout_ms=self.config.timeout * 1000,
                compression_type="gzip",
                batch_size=16384,
                linger_ms=10,
            )

            # Create admin client for topic management
            self._admin_client = KafkaAdminClient(
                bootstrap_servers=[f"{self.config.host}:{self.config.port}"],
                request_timeout_ms=self.config.timeout * 1000,
            )

            # Test connection by getting cluster metadata
            metadata = self._producer.bootstrap_connected()
            if metadata:
                self.logger.info(
                    f"Connected to Kafka at {self.config.host}:{self.config.port}"
                )
                return True
            else:
                self.logger.error("Failed to connect to Kafka bootstrap servers")
                return False

        except ImportError:
            self.logger.error(
                "kafka-python library not installed. Run: pip install kafka-python"
            )
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to Kafka: {e}")
            return False

    def disconnect(self) -> None:
        """Close connections to Kafka"""
        try:
            if self._producer:
                self._producer.flush()
                self._producer.close()
                self._producer = None

            for consumer in self._consumers.values():
                consumer.close()
            self._consumers.clear()

            if self._admin_client:
                self._admin_client.close()
                self._admin_client = None

            self.logger.info("Disconnected from Kafka")
        except Exception as e:
            self.logger.error(f"Error disconnecting from Kafka: {e}")

    def health_check(self) -> bool:
        """Check Kafka cluster health"""
        try:
            if not self._producer:
                return False

            # Try to get cluster metadata
            metadata = self._producer.bootstrap_connected()
            return metadata is not None
        except Exception:
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information"""
        return {
            "type": "real",
            "host": self.config.host,
            "port": self.config.port,
            "ssl_enabled": self.config.ssl_enabled,
            "connected": self._producer is not None,
            "topics": self.list_topics() if self._admin_client else [],
        }

    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """Publish message to Kafka topic"""
        try:
            if not self._producer:
                self.logger.error("Producer not connected")
                return False

            # Add metadata to message
            enriched_message = {
                **message,
                "_timestamp": datetime.now().isoformat(),
                "_topic": topic,
                "_producer": "netskope-sdet-framework",
            }

            # Send message
            future = self._producer.send(topic, enriched_message)

            # Wait for confirmation (with timeout)
            record_metadata = future.get(timeout=10)

            self.logger.debug(
                f"Message sent to {topic} partition {record_metadata.partition} offset {record_metadata.offset}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to publish message to {topic}: {e}")
            return False

    def subscribe(self, topic: str, callback: callable) -> bool:
        """Subscribe to topic with callback running in background thread"""
        try:
            from kafka import KafkaConsumer

            if (
                topic in self._consumer_threads
                and self._consumer_threads[topic].is_alive()
            ):
                self.logger.warning(f"Already subscribed to topic {topic}")
                return True

            self._running[topic] = True
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[f"{self.config.host}:{self.config.port}"],
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                group_id=f"netskope-sdet-{topic}",
                consumer_timeout_ms=1000,
            )

            self._consumers[topic] = consumer

            thread = threading.Thread(
                target=self._consumer_loop,
                args=(topic, callback),
                daemon=True,
                name=f"kafka-consumer-{topic}",
            )
            thread.start()
            self._consumer_threads[topic] = thread

            self.logger.info(f"Subscribed to topic {topic} (background thread started)")
            return True

        except Exception as e:
            self.logger.error(f"Failed to subscribe to {topic}: {e}")
            return False

    def _consumer_loop(self, topic: str, callback: callable) -> None:
        """Background thread loop for consuming messages"""
        consumer = self._consumers.get(topic)
        if not consumer:
            return

        self.logger.debug(f"Consumer loop started for topic {topic}")
        try:
            while self._running.get(topic, False):
                try:
                    messages = consumer.poll(timeout_ms=1000)
                    for tp, records in messages.items():
                        for record in records:
                            try:
                                callback(record.value)
                            except Exception as e:
                                self.logger.error(f"Callback error for {topic}: {e}")
                except Exception as e:
                    if self._running.get(topic, False):
                        self.logger.warning(f"Poll error for {topic}: {e}")
        finally:
            consumer.close()
            self.logger.debug(f"Consumer loop stopped for topic {topic}")

    def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from topic and stop background thread"""
        if topic not in self._running:
            return False

        self._running[topic] = False
        if topic in self._consumer_threads:
            self._consumer_threads[topic].join(timeout=5)
            del self._consumer_threads[topic]
        if topic in self._consumers:
            del self._consumers[topic]
        if topic in self._running:
            del self._running[topic]

        self.logger.info(f"Unsubscribed from topic {topic}")
        return True

    def consume(self, topic: str, timeout: int = 1000) -> List[Dict[str, Any]]:
        """Consume messages from topic"""
        try:
            from kafka import KafkaConsumer

            # Create temporary consumer for this operation
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[f"{self.config.host}:{self.config.port}"],
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                consumer_timeout_ms=timeout,
            )

            messages = []
            try:
                for message in consumer:
                    messages.append(message.value)
                    if len(messages) >= MAX_CONSUMER_MESSAGES:
                        break
            except StopIteration:
                # Timeout reached
                pass
            finally:
                consumer.close()

            self.logger.debug(f"Consumed {len(messages)} messages from {topic}")
            return messages

        except Exception as e:
            self.logger.error(f"Failed to consume from {topic}: {e}")
            return []

def create_topic(self, topic: str, partitions: int = 1) -> bool:
        """Create a new Kafka topic"""
        try:
            from kafka.admin import NewTopic

            if not self._admin_client:
                self.logger.error("Admin client not connected")
                return False

            topic_config = NewTopic(
                name=topic,
                num_partitions=partitions,
                replication_factor=1,
            )

            result = self._admin_client.create_topics([topic_config])

            # Handle different response types from kafka-python versions
            if hasattr(result, 'items'):
                topics_dict = dict(result.items())
            elif hasattr(result, 'topic_result_dict'):
                topics_dict = result.topic_result_dict()
            else:
                topics_dict = {topic: result}

            for topic_name, future in topics_dict.items():
                try:
                    if hasattr(future, 'result'):
                        future.result()
                    self.logger.info(f"Created topic {topic_name}")
                    return True
                except Exception as e:
                    if "already exists" in str(e).lower():
                        self.logger.info(f"Topic {topic_name} already exists")
                        return True
                    else:
                        self.logger.error(f"Failed to create topic {topic_name}: {e}")
                        return False

            return False

        except Exception as e:
            self.logger.error(f"Failed to create topic: {e}")
            return False

            topic_config = NewTopic(
                name=topic,
                num_partitions=partitions,
                replication_factor=1,  # Adjust based on cluster size
            )

            result = self._admin_client.create_topics([topic_config])

            # Wait for topic creation
            for topic_name, future in result.items():
                try:
                    future.result()  # Will raise exception if creation failed
                    self.logger.info(f"Created topic {topic_name}")
                    return True
                except Exception as e:
                    if "already exists" in str(e).lower():
                        self.logger.info(f"Topic {topic_name} already exists")
                        return True
                    else:
                        self.logger.error(f"Failed to create topic {topic_name}: {e}")
                        return False

            return False

        except Exception as e:
            self.logger.error(f"Failed to create topic {topic}: {e}")
            return False

    def list_topics(self) -> List[str]:
        """List all available topics"""
        try:
            if not self._admin_client:
                return []

            metadata = self._admin_client.list_topics()
            return list(metadata)

        except Exception as e:
            self.logger.error(f"Failed to list topics: {e}")
            return []


class RealDatabaseClient(DatabaseClient):
    """Real MongoDB client implementation using pymongo"""

    def __init__(self, config: ServiceConfig, environment: Environment):
        super().__init__(config, environment)
        self._client = None
        self._database = None

    def connect(self) -> bool:
        """Establish connection to MongoDB"""
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure
            from urllib.parse import quote_plus

            # Build connection string with proper URL encoding
            if self.config.username and self.config.password:
                escaped_username = quote_plus(self.config.username)
                escaped_password = quote_plus(self.config.password)
                # Use database as auth source if specified, otherwise default to admin
                auth_source = getattr(self.config, "auth_source", "admin")
                connection_string = f"mongodb://{escaped_username}:{escaped_password}@{self.config.host}:{self.config.port}/{self.config.database}?authSource={auth_source}"
            else:
                connection_string = f"mongodb://{self.config.host}:{self.config.port}/{self.config.database}"

            # Create client
            self._client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=self.config.timeout * 1000,
                connectTimeoutMS=self.config.timeout * 1000,
                maxPoolSize=self.config.connection_pool_size,
                ssl=self.config.ssl_enabled,
            )

            # Test connection
            self._client.admin.command("ping")

            # Get database
            self._database = self._client[self.config.database]

            self.logger.info(
                f"Connected to MongoDB at {self.config.host}:{self.config.port}"
            )
            return True

        except ImportError:
            self.logger.error("pymongo library not installed. Run: pip install pymongo")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            return False

    def disconnect(self) -> None:
        """Close connection to MongoDB"""
        try:
            if self._client:
                self._client.close()
                self._client = None
                self._database = None
            self.logger.info("Disconnected from MongoDB")
        except Exception as e:
            self.logger.error(f"Error disconnecting from MongoDB: {e}")

    def health_check(self) -> bool:
        """Check MongoDB health"""
        try:
            if not self._client:
                return False

            # Ping the database
            self._client.admin.command("ping")
            return True
        except Exception:
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information"""
        return {
            "type": "real",
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
            "ssl_enabled": self.config.ssl_enabled,
            "connected": self._client is not None,
        }

    def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        """Insert single document"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            # Add metadata
            doc_with_metadata = {
                **document,
                "_created_at": datetime.now(),
                "_framework": "netskope-sdet",
            }

            result = self._database[collection].insert_one(doc_with_metadata)
            self.logger.debug(
                f"Inserted document into {collection}: {result.inserted_id}"
            )
            return str(result.inserted_id)

        except Exception as e:
            self.logger.error(f"Failed to insert document into {collection}: {e}")
            raise

    def insert_many(
        self, collection: str, documents: List[Dict[str, Any]]
    ) -> List[str]:
        """Insert multiple documents"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            # Add metadata to all documents
            docs_with_metadata = []
            for doc in documents:
                docs_with_metadata.append(
                    {
                        **doc,
                        "_created_at": datetime.now(),
                        "_framework": "netskope-sdet",
                    }
                )

            result = self._database[collection].insert_many(docs_with_metadata)
            ids = [str(id) for id in result.inserted_ids]
            self.logger.debug(f"Inserted {len(ids)} documents into {collection}")
            return ids

        except Exception as e:
            self.logger.error(f"Failed to insert documents into {collection}: {e}")
            raise

    def find_one(
        self, collection: str, filter_dict: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find single document"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            result = self._database[collection].find_one(filter_dict)
            if result:
                # Convert ObjectId to string
                result["_id"] = str(result["_id"])

            return result

        except Exception as e:
            self.logger.error(f"Failed to find document in {collection}: {e}")
            return None

    def find_many(
        self, collection: str, filter_dict: Dict[str, Any], limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find multiple documents"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            cursor = self._database[collection].find(filter_dict).limit(limit)
            results = []

            for doc in cursor:
                # Convert ObjectId to string
                doc["_id"] = str(doc["_id"])
                results.append(doc)

            return results

        except Exception as e:
            self.logger.error(f"Failed to find documents in {collection}: {e}")
            return []

    def update_one(
        self, collection: str, filter_dict: Dict[str, Any], update_dict: Dict[str, Any]
    ) -> bool:
        """Update single document"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            # Check if update_dict already has MongoDB operators
            has_operator = any(key.startswith("$") for key in update_dict.keys())

            if has_operator:
                # Update dict already contains operators, just add metadata
                if "$set" in update_dict:
                    update_dict["$set"]["_updated_at"] = datetime.now()
                update_with_metadata = update_dict
            else:
                # Wrap in $set operator and add metadata
                update_with_metadata = {
                    "$set": {**update_dict, "_updated_at": datetime.now()}
                }

            result = self._database[collection].update_one(
                filter_dict, update_with_metadata
            )
            return result.modified_count > 0

        except Exception as e:
            self.logger.error(f"Failed to update document in {collection}: {e}")
            return False

    def delete_one(self, collection: str, filter_dict: Dict[str, Any]) -> bool:
        """Delete single document"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            result = self._database[collection].delete_one(filter_dict)
            return result.deleted_count > 0

        except Exception as e:
            self.logger.error(f"Failed to delete document from {collection}: {e}")
            return False

    def count_documents(
        self, collection: str, filter_dict: Dict[str, Any] = None
    ) -> int:
        """Count documents in collection"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            if filter_dict is None:
                filter_dict = {}

            return self._database[collection].count_documents(filter_dict)

        except Exception as e:
            self.logger.error(f"Failed to count documents in {collection}: {e}")
            return 0

    def create_index(
        self,
        collection: str,
        keys: Dict[str, int],
        unique: bool = False,
        name: str = None,
    ) -> str:
        """Create an index on the collection"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            index_name = self._database[collection].create_index(
                list(keys.items()), unique=unique, name=name
            )
            self.logger.info(f"Created index {index_name} on {collection}")
            return index_name

        except Exception as e:
            self.logger.error(f"Failed to create index on {collection}: {e}")
            raise

    def drop_index(self, collection: str, index_name: str) -> bool:
        """Drop an index from the collection"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            self._database[collection].drop_index(index_name)
            self.logger.info(f"Dropped index {index_name} from {collection}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to drop index from {collection}: {e}")
            return False

    def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """List all indexes on the collection"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            indexes = list(self._database[collection].list_indexes())
            return [
                {
                    "name": idx.get("name"),
                    "keys": idx.get("key"),
                    "unique": idx.get("unique", False),
                }
                for idx in indexes
            ]

        except Exception as e:
            self.logger.error(f"Failed to list indexes for {collection}: {e}")
            return []

    def aggregate(
        self, collection: str, pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute an aggregation pipeline"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            cursor = self._database[collection].aggregate(pipeline)
            results = []
            for doc in cursor:
                if "_id" in doc and hasattr(doc["_id"], "__str__"):
                    doc["_id"] = str(doc["_id"])
                results.append(doc)

            self.logger.debug(
                f"Aggregation on {collection} returned {len(results)} results"
            )
            return results

        except Exception as e:
            self.logger.error(f"Failed to aggregate on {collection}: {e}")
            return []

    def bulk_write(
        self, collection: str, operations: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Execute bulk write operations"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            from pymongo import UpdateOne, InsertOne, DeleteOne

            pymongo_ops = []
            for op in operations:
                op_type = op.get("type")
                if op_type == "insert":
                    pymongo_ops.append(InsertOne(op.get("document")))
                elif op_type == "update":
                    pymongo_ops.append(
                        UpdateOne(
                            op.get("filter"),
                            op.get("update"),
                            upsert=op.get("upsert", False),
                        )
                    )
                elif op_type == "delete":
                    pymongo_ops.append(DeleteOne(op.get("filter")))

            result = self._database[collection].bulk_write(pymongo_ops)
            return {
                "inserted": result.inserted_count,
                "modified": result.modified_count,
                "deleted": result.deleted_count,
                "upserted": result.upserted_count,
            }

        except Exception as e:
            self.logger.error(f"Failed to execute bulk write on {collection}: {e}")
            raise

    def distinct(
        self, collection: str, field: str, filter_dict: Dict[str, Any] = None
    ) -> List[Any]:
        """Get distinct values for a field"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            if filter_dict is None:
                filter_dict = {}

            return self._database[collection].distinct(field, filter_dict)

        except Exception as e:
            self.logger.error(f"Failed to get distinct values from {collection}: {e}")
            return []

    def find_one_and_update(
        self,
        collection: str,
        filter_dict: Dict[str, Any],
        update_dict: Dict[str, Any],
        return_new: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Find and update a single document, returning it"""
        try:
            if self._database is None:
                raise Exception("Database not connected")

            from pymongo import ReturnDocument

            result = self._database[collection].find_one_and_update(
                filter_dict,
                {"$set": {**update_dict, "_updated_at": datetime.now()}},
                return_document=ReturnDocument.AFTER
                if return_new
                else ReturnDocument.BEFORE,
            )

            if result and "_id" in result:
                result["_id"] = str(result["_id"])
            return result

        except Exception as e:
            self.logger.error(f"Failed to find and update in {collection}: {e}")
            return None


class RealAPIClient(APIClient):
    """Real Netskope API client implementation using requests with connection pooling and circuit breaker"""

    def __init__(self, config: ServiceConfig, environment: Environment):
        super().__init__(config, environment)
        self._session = None
        self._authenticated = False
        self._base_url = (
            f"{'https' if config.ssl_enabled else 'http'}://{config.host}:{config.port}"
        )
        self._circuit_breaker = None
        self._connection_pool = None

    def connect(self) -> bool:
        """Establish HTTP session with connection pooling and circuit breaker"""
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            self._session = requests.Session()

            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )

            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=10,
                pool_maxsize=20,
            )
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)

            self._session.headers.update(
                {
                    "User-Agent": "Netskope-SDET-Framework/1.0",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
            )

            self._session.timeout = self.config.timeout

            try:
                from .circuit_breaker import create_service_circuit_breaker

                self._circuit_breaker = create_service_circuit_breaker(
                    f"api_{self.config.host}", failure_threshold=5, timeout=60
                )
                self.logger.info("Circuit breaker enabled for API client")
            except ImportError:
                self.logger.warning("Circuit breaker not available")

            try:
                from .connection_pool import HTTPConnectionPool, PoolConfig

                pool_config = PoolConfig(
                    name=f"api_{self.config.host}",
                    min_size=5,
                    max_size=20,
                    max_idle_time=300,
                    max_lifetime=3600,
                )
                self._connection_pool = HTTPConnectionPool(pool_config)
                self.logger.info("Connection pool enabled for API client")
            except ImportError:
                self.logger.warning("Connection pool not available")

            self.logger.info(f"HTTP session established for {self._base_url}")
            return True

        except ImportError:
            self.logger.error(
                "requests library not installed. Run: pip install requests"
            )
            return False
        except Exception as e:
            self.logger.error(f"Failed to create HTTP session: {e}")
            return False

    def disconnect(self) -> None:
        """Close HTTP session and connection pool"""
        try:
            if self._connection_pool:
                self._connection_pool.shutdown()
                self._connection_pool = None
            if self._session:
                self._session.close()
                self._session = None
            self._authenticated = False
            self.logger.info("HTTP session closed")
        except Exception as e:
            self.logger.error(f"Error closing HTTP session: {e}")

    def health_check(self) -> bool:
        """Check API health"""
        try:
            if not self._session:
                return False

            # Try to access health endpoint
            response = self._session.get(f"{self._base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information"""
        return {
            "type": "real",
            "base_url": self._base_url,
            "ssl_enabled": self.config.ssl_enabled,
            "authenticated": self._authenticated,
            "connected": self._session is not None,
        }

    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Authenticate with the API"""
        try:
            if not self._session:
                self.logger.error("Session not established")
                return False

            # Handle different authentication methods
            if "api_key" in credentials:
                # API Key authentication
                self._session.headers.update(
                    {"Authorization": f"Bearer {credentials['api_key']}"}
                )
                self._authenticated = True
                self.logger.info("Authenticated with API key")
                return True

            elif "username" in credentials and "password" in credentials:
                # Username/password authentication
                auth_data = {
                    "username": credentials["username"],
                    "password": credentials["password"],
                }

                response = self._session.post(
                    f"{self._base_url}/auth/login", json=auth_data
                )

                if response.status_code == 200:
                    auth_response = response.json()
                    if "access_token" in auth_response:
                        self._session.headers.update(
                            {"Authorization": f"Bearer {auth_response['access_token']}"}
                        )
                        self._authenticated = True
                        self.logger.info("Authenticated with username/password")
                        return True

            self.logger.error("Authentication failed - invalid credentials")
            return False

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    def _record_success(self) -> None:
        if self._circuit_breaker:
            self._circuit_breaker.record_success()

    def _record_failure(self) -> None:
        if self._circuit_breaker:
            self._circuit_breaker.record_failure()

    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make GET request"""
        try:
            if not self._session:
                raise Exception("Session not established")

            url = f"{self._base_url}{endpoint}"
            response = self._session.get(url, params=params)

            response.raise_for_status()
            result = response.json()
            self._record_success()
            return result

        except Exception as e:
            self._record_failure()
            self.logger.error(f"GET request failed for {endpoint}: {e}")
            raise

    def post(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make POST request"""
        try:
            if not self._session:
                raise Exception("Session not established")

            url = f"{self._base_url}{endpoint}"
            response = self._session.post(url, json=data)

            response.raise_for_status()
            result = response.json()
            self._record_success()
            return result

        except Exception as e:
            self._record_failure()
            self.logger.error(f"POST request failed for {endpoint}: {e}")
            raise

    def put(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make PUT request"""
        try:
            if not self._session:
                raise Exception("Session not established")

            url = f"{self._base_url}{endpoint}"
            response = self._session.put(url, json=data)

            response.raise_for_status()
            result = response.json()
            self._record_success()
            return result

        except Exception as e:
            self._record_failure()
            self.logger.error(f"PUT request failed for {endpoint}: {e}")
            raise

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request"""
        try:
            if not self._session:
                raise Exception("Session not established")

            url = f"{self._base_url}{endpoint}"
            response = self._session.delete(url)

            response.raise_for_status()

            # DELETE responses are often empty; handle non-JSON body gracefully
            try:
                result = response.json()
            except ValueError:
                result = {"status": "success", "message": "Resource deleted"}

            self._record_success()
            return result

        except Exception as e:
            self._record_failure()
            self.logger.error(f"DELETE request failed for {endpoint}: {e}")
            raise


# Factory functions to integrate with existing service manager


def create_real_message_client(
    config: ServiceConfig, environment: Environment
) -> MessageClient:
    """Create real Kafka message client"""
    return RealMessageClient(config, environment)


def create_real_database_client(
    config: ServiceConfig, environment: Environment
) -> DatabaseClient:
    """Create real MongoDB database client"""
    return RealDatabaseClient(config, environment)


def create_real_api_client(
    config: ServiceConfig, environment: Environment
) -> APIClient:
    """Create real Netskope API client"""
    return RealAPIClient(config, environment)
