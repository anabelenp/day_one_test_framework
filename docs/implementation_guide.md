# Day-1 Framework - Implementation Guide

##  Overview

This guide provides detailed information about the current implementation status, usage examples, and next steps for the Day-1 Framework.

##  **Completed Components**

### **1. Environment Manager** (`src/environment_manager.py`)

#### **Features Implemented**
-  Automatic environment detection (Kubernetes, Docker, env vars, config files)
-  YAML-based configuration management with environment-specific overrides
-  Service discovery and configuration
-  Health checks and connectivity validation
-  CLI interface for environment management

#### **Usage Examples**

```python
# Basic usage
from src.environment_manager import get_environment_manager, Environment

env_manager = get_environment_manager()

# Detect current environment
current_env = env_manager.detect_environment()
print(f"Running in: {current_env.value}")  # mock, local, integration, etc.

# Load configuration
config = env_manager.load_configuration()
print(f"Redis host: {config.redis.host}")
print(f"Kafka port: {config.kafka.port}")

# Get service-specific configuration
redis_config = env_manager.get_service_config("redis")
connection_string = redis_config.connection_string

# Validate environment
is_valid = env_manager.validate_environment()
if is_valid:
    print(" Environment is properly configured")

# Get complete environment information
info = env_manager.get_environment_info()
print(f"Services: {info['services']}")
```

#### **CLI Commands**

```bash
# Detect current environment
python src/environment_manager.py detect

# Show environment information
python src/environment_manager.py info
python src/environment_manager.py info local

# Validate environment
python src/environment_manager.py validate
python src/environment_manager.py validate integration

# Set environment
python src/environment_manager.py set local

# List all environments
python src/environment_manager.py list
```

#### **Configuration Files**

```yaml
# config/local.yaml
name: "Local Development Environment"
environment: "local"

redis:
  host: "redis"
  port: 6379
  ssl_enabled: false

kafka:
  host: "kafka"
  port: 29092

mongodb:
  host: "mongodb"
  port: 27017
  database: "netskope_local"

# ... more configuration
```

---

### **2. Service Abstraction Layer** (`src/service_manager.py`)

#### **Features Implemented**
-  Abstract base classes for all service types
-  Mock implementations for fast testing (Redis, Kafka, MongoDB, API)
-  Real Redis client implementation
-  Environment-aware client selection
-  Health monitoring and connection management
-  CLI interface for service testing

#### **Service Clients**

##### **Cache Client (Redis)**

```python
from src.service_manager import get_cache_client

cache = get_cache_client()

# Basic operations
cache.set("user:123", {"name": "John", "role": "admin"})
user = cache.get("user:123")

# With TTL
cache.set("session:abc", "active", ttl=3600)  # 1 hour

# Check existence
if cache.exists("user:123"):
    print("User found in cache")

# Delete
cache.delete("user:123")

# Clear all
cache.flush_all()
```

##### **Message Client (Kafka)**

```python
from src.service_manager import get_message_client

message_client = get_message_client()

# Create topic
message_client.create_topic("security_events")

# Publish message
message_client.publish("security_events", {
    "event_type": "login",
    "user_id": "user123",
    "timestamp": "2024-01-01T10:00:00Z",
    "source_ip": "192.168.1.100"
})

# Subscribe to topic
def handle_event(message):
    print(f"Received: {message}")

message_client.subscribe("security_events", handle_event)

# Consume messages
messages = message_client.consume("security_events", timeout=5000)
for msg in messages:
    print(f"Event: {msg}")

# List topics
topics = message_client.list_topics()
```

##### **Database Client (MongoDB)**

```python
from src.service_manager import get_database_client

db = get_database_client()

# Insert document
user_id = db.insert_one("users", {
    "username": "john_doe",
    "email": "john@example.com",
    "role": "admin"
})

# Insert multiple
ids = db.insert_many("users", [
    {"username": "jane", "role": "user"},
    {"username": "bob", "role": "manager"}
])

# Find one
user = db.find_one("users", {"username": "john_doe"})

# Find many
admins = db.find_many("users", {"role": "admin"}, limit=10)

# Update
db.update_one("users", 
    {"username": "john_doe"}, 
    {"last_login": "2024-01-01T10:00:00Z"}
)

# Delete
db.delete_one("users", {"username": "john_doe"})

# Count
user_count = db.count_documents("users", {"role": "admin"})
```

##### **API Client (Netskope)**

```python
from src.service_manager import get_api_client

api = get_api_client()

# Authenticate
api.authenticate({"api_key": "your-api-key"})

# GET request
events = api.get("/api/v2/events", params={"limit": 10})

# POST request
response = api.post("/api/v2/users", data={
    "username": "new_user",
    "email": "user@example.com"
})

# PUT request
api.put("/api/v2/users/123", data={"role": "admin"})

# DELETE request
api.delete("/api/v2/users/123")
```

#### **Health Monitoring**

```python
from src.service_manager import get_service_manager

service_manager = get_service_manager()

# Check all services
health_results = service_manager.health_check_all()

for service, is_healthy in health_results.items():
    status = "" if is_healthy else ""
    print(f"{service}: {status}")

# Disconnect all services
service_manager.disconnect_all()
```

#### **CLI Commands**

```bash
# Check service health
python src/service_manager.py health

# Show connection information
python src/service_manager.py info

# Test cache operations
python src/service_manager.py test-cache

# Test message operations
python src/service_manager.py test-message

# Test database operations
python src/service_manager.py test-database

# Test API operations
python src/service_manager.py test-api
```

---

### **3. Docker Compose Local Environment** (`docker-compose.local.yml`)

#### **Services Included**
-  **Redis 7**: Caching and session management
-  **Kafka + Zookeeper**: Event streaming
-  **MongoDB 6**: Document storage with validation schemas
-  **LocalStack**: AWS services (S3, IAM, Lambda, DynamoDB, etc.)
-  **Prometheus**: Metrics collection
-  **Grafana**: Metrics visualization
-  **Jaeger**: Distributed tracing
-  **Exporters**: Redis, Kafka, MongoDB metrics

#### **Quick Start**

```bash
# Start all services
docker-compose -f docker-compose.local.yml up -d

# Check service status
docker-compose -f docker-compose.local.yml ps

# View logs
docker-compose -f docker-compose.local.yml logs -f redis
docker-compose -f docker-compose.local.yml logs -f kafka

# Stop all services
docker-compose -f docker-compose.local.yml down

# Stop and remove volumes (clean slate)
docker-compose -f docker-compose.local.yml down -v
```

#### **Automated Startup Script**

```bash
# Start complete environment with validation
python scripts/start_local_environment.py

# Check status
python scripts/start_local_environment.py --status

# Stop environment
python scripts/start_local_environment.py --stop

# Restart environment
python scripts/start_local_environment.py --restart
```

#### **Service Access**

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / integration-grafana-2024 |
| **Prometheus** | http://localhost:9090 | - |
| **Jaeger** | http://localhost:16686 | - |
| **LocalStack** | http://localhost:4566 | - |
| **Redis** | localhost:6379 | - |
| **Kafka** | localhost:9092 | - |
| **MongoDB** | localhost:27017 | netskope_app / netskope_app_2024 |

#### **Initialization Scripts**

##### **MongoDB Initialization** (`scripts/mongo-init.js`)
- Creates collections with validation schemas
- Sets up indexes for performance
- Inserts sample test data
- Configures TTL indexes for data retention

##### **LocalStack Initialization** (`scripts/localstack-init.sh`)
- Creates S3 buckets for testing
- Sets up IAM roles and policies
- Creates Secrets Manager secrets
- Initializes DynamoDB tables
- Creates SNS topics and SQS queues
- Sets up CloudWatch log groups
- Deploys sample Lambda function

---

### **4. Updated Helper Functions**

#### **Redis Helper** (`tests/utils/redis_helper.py`)

```python
from tests.utils.redis_helper import set_key, get_key, delete_key

# Now uses service abstraction layer
set_key("test", "value")
value = get_key("test")
delete_key("test")
```

#### **Kafka Helper** (`tests/utils/kafka_helper.py`)

```python
from tests.utils.kafka_helper import publish_event, consume_event

# Now uses service abstraction layer
publish_event("events", {"type": "test"})
messages = consume_event("events")
```

#### **NoSQL Helper** (`tests/utils/nosql_helper.py`)

```python
from tests.utils.nosql_helper import insert_log, get_logs

# Now uses service abstraction layer
insert_log({"action": "login", "user": "john"})
logs = get_logs({"user": "john"})
```

---

##  **Components In Progress**

### **1. Real Service Client Implementations**

#### **Kafka Client** (Planned)
```python
class RealMessageClient(MessageClient):
    """Real Kafka client using kafka-python"""
    # TODO: Implement using kafka-python library
    # - Producer with proper serialization
    # - Consumer with offset management
    # - Topic management
    # - Error handling and retries
```

#### **MongoDB Client** (Planned)
```python
class RealDatabaseClient(DatabaseClient):
    """Real MongoDB client using pymongo"""
    # TODO: Implement using pymongo library
    # - Connection pooling
    # - Query optimization
    # - Index management
    # - Transaction support
```

#### **Netskope API Client** (Planned)
```python
class RealAPIClient(APIClient):
    """Real Netskope API client"""
    # TODO: Implement using requests library
    # - Authentication (JWT, API keys)
    # - Rate limiting
    # - Retry logic
    # - Response parsing
```

---

### **2. Kubernetes Integration Environment**

#### **Planned Components**
- Kubernetes manifests for all services
- Helm charts for deployment
- Service mesh integration (Istio/Linkerd)
- Ingress configuration
- Secrets management (Vault/Sealed Secrets)
- Auto-scaling configuration

#### **Directory Structure**
```
k8s/
 integration/
    namespace.yaml
    redis-cluster.yaml
    kafka-cluster.yaml
    mongodb-replica.yaml
    monitoring-stack.yaml
    test-runner-job.yaml
 staging/
    ...
 production/
     ...
```

---

### **3. CI/CD Pipeline Integration**

#### **GitHub Actions** (Planned)
```yaml
name: Day-1 Pipeline

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Unit Tests (Mock)
        run: |
          python start_mock_mode.py &
          pytest tests/unit/ -v
          
  integration-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    steps:
      - name: Start Local Services
        run: python scripts/start_local_environment.py
      - name: Run Integration Tests
        run: pytest tests/integration/ -v
```

#### **Jenkins Pipeline** (Planned)
- Multi-stage pipeline
- Environment-specific testing
- Artifact management
- Test result publishing

---

### **4. Security Testing Framework**

#### **Planned Components**
- SAST integration (Bandit, Semgrep)
- DAST integration (OWASP ZAP)
- Dependency scanning (Safety, Snyk)
- Secret scanning (TruffleHog)
- Compliance validation (SOC2, GDPR, PCI)

---

##  **Usage Patterns**

### **Pattern 1: Environment-Aware Testing**

```python
import pytest
from src.environment_manager import get_current_environment, Environment
from src.service_manager import get_cache_client, get_database_client

class TestUserManagement:
    def setup_method(self):
        """Setup runs before each test"""
        self.env = get_current_environment()
        self.cache = get_cache_client()
        self.db = get_database_client()
    
    def test_user_creation(self):
        """Test works in any environment"""
        # Create user
        user_id = self.db.insert_one("users", {
            "username": "test_user",
            "email": "test@example.com"
        })
        
        # Cache user
        self.cache.set(f"user:{user_id}", {"username": "test_user"})
        
        # Verify
        cached_user = self.cache.get(f"user:{user_id}")
        assert cached_user["username"] == "test_user"
        
        # Cleanup
        self.db.delete_one("users", {"_id": user_id})
        self.cache.delete(f"user:{user_id}")
```

### **Pattern 2: Progressive Testing**

```python
# tests/conftest.py
import pytest
from src.environment_manager import get_current_environment, Environment

def pytest_configure(config):
    """Configure pytest based on environment"""
    env = get_current_environment()
    
    # Add markers
    config.addinivalue_line("markers", "mock: tests that run in mock mode")
    config.addinivalue_line("markers", "local: tests that require local services")
    config.addinivalue_line("markers", "integration: tests that require integration environment")

def pytest_collection_modifyitems(config, items):
    """Skip tests based on environment"""
    env = get_current_environment()
    
    for item in items:
        # Skip integration tests in mock mode
        if env == Environment.MOCK and "integration" in item.keywords:
            item.add_marker(pytest.mark.skip(reason="Integration tests require local/integration environment"))
        
        # Skip local tests in mock mode
        if env == Environment.MOCK and "local" in item.keywords:
            item.add_marker(pytest.mark.skip(reason="Local tests require Docker services"))
```

### **Pattern 3: Service Health Monitoring**

```python
from src.service_manager import get_service_manager
import time

def monitor_services(interval=60):
    """Monitor service health continuously"""
    service_manager = get_service_manager()
    
    while True:
        health_results = service_manager.health_check_all()
        
        unhealthy = [s for s, h in health_results.items() if not h]
        
        if unhealthy:
            print(f"  Unhealthy services: {unhealthy}")
            # Send alert
        else:
            print(" All services healthy")
        
        time.sleep(interval)
```

---

##  **Next Steps**

### **Immediate (Week 1-2)**
1.  Complete real Redis client implementation
2.  Implement real Kafka client
3.  Implement real MongoDB client
4.  Implement real Netskope API client
5.  Add comprehensive error handling

### **Short-term (Week 3-4)**
1.  Create Kubernetes manifests for integration environment
2.  Set up Helm charts for deployment
3.  Implement CI/CD pipeline (GitHub Actions)
4.  Add security scanning integration
5.  Create comprehensive test suite

### **Medium-term (Month 2)**
1.  Implement staging environment
2.  Add performance testing framework
3.  Implement compliance testing automation
4.  Create monitoring dashboards
5.  Add incident response testing

### **Long-term (Month 3+)**
1.  Production monitoring implementation
2.  Advanced security testing
3.  Chaos engineering integration
4.  Multi-region support
5.  Advanced analytics and reporting

---

##  **Contributing**

### **Adding New Service Clients**

1. Create abstract base class in `src/service_manager.py`
2. Implement mock version for testing
3. Implement real version with proper error handling
4. Add health check implementation
5. Update service manager factory methods
6. Add CLI commands for testing
7. Update documentation

### **Adding New Environments**

1. Add environment to `Environment` enum
2. Create configuration file (`config/{environment}.yaml`)
3. Update environment detection logic
4. Add validation rules
5. Create deployment manifests
6. Update documentation

---

##  **Additional Resources**

- **Architecture Documentation**: `docs/architecture.md`
- **Testing Strategy**: `docs/testing_strategy.md`
- **Security Testing Guide**: `docs/security_testing_guide.md`
- **Environment Setup**: `docs/environment_setup.md`
- **API Documentation**: Generated with Sphinx (coming soon)

---

##  **Known Issues**

1. **Real Kafka client not implemented**: Currently using mock client in all environments except mock
2. **Real MongoDB client not implemented**: Currently using mock client in all environments except mock
3. **Real Netskope API client not implemented**: Currently using mock client in all environments
4. **LocalStack initialization**: May take 60+ seconds on first startup
5. **Docker resource usage**: Local environment requires ~8GB RAM

---

##  **Tips and Best Practices**

### **Development Workflow**
1. Start with mock environment for rapid development
2. Move to local environment for integration testing
3. Use integration environment for E2E testing
4. Validate in staging before production

### **Testing Strategy**
1. Write unit tests in mock environment (fast feedback)
2. Write integration tests in local environment (realistic)
3. Write E2E tests in integration environment (complete workflows)
4. Monitor in production environment (real-world validation)

### **Performance Optimization**
1. Use connection pooling for all services
2. Implement caching strategies
3. Batch operations when possible
4. Monitor resource usage with Prometheus/Grafana

### **Security Best Practices**
1. Never commit real credentials
2. Use environment variables for sensitive data
3. Rotate secrets regularly
4. Implement least privilege access
5. Enable audit logging

---

This implementation guide will be updated as new components are completed and best practices are discovered.