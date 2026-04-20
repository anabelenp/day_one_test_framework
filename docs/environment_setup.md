# Day-1 Test Framework - Environment Setup Guide

##  Overview

This guide provides comprehensive instructions for setting up and configuring all testing environments in the Day-1 Test Framework, from local development to production validation.

##  Environment Architecture

```mermaid
graph TB
    subgraph "Development"
        A[Mock Environment ] --> B[Local Environment ]
    end
    
    subgraph "Testing"
        B --> C[Integration Environment ]
        C --> D[Staging Environment ]
    end
    
    subgraph "Production"
        D --> E[Production Environment ]
    end
    
    subgraph "Infrastructure"
        F[Docker Compose ] --> G[Kubernetes ]
        G --> H[Cloud Services ]
    end
```

### **Implementation Status**
-  **Completed**: Mock Environment, Local Environment, Docker Compose, LocalStack (AWS)
-  **In Progress**: Integration Environment (Kubernetes), Staging Environment, Production Environment
-  **Planned**: Advanced monitoring, security hardening, compliance automation

##  Environment 1: Mock Environment

### **Purpose**
- Fastest feedback loop for developers
- No external dependencies
- Synthetic data for predictable testing
- Perfect for unit tests and TDD

### **Setup Instructions**

#### **Prerequisites**
```bash
# Required software
- Python 3.9+
- Git
- IDE (VS Code, PyCharm, etc.)

# Optional but recommended
- Docker Desktop (for local environment)
```

#### **Framework Installation**
```bash
# Install the framework in development mode
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

#### **Quick Setup**
```bash
# 1. Clone repository
git clone <repository-url>
cd day_one_test_framework

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Install framework
pip install -e .

# 4. Verify mock environment
python -c "from src.environment_manager import get_current_environment; print(f'Environment: {get_current_environment().value}')"

# 5. Test service abstraction
python -c "from src.service_manager import get_cache_client; cache = get_cache_client(); cache.set('test', 'works'); print(f'Cache test: {cache.get(\"test\")}')"
```

#### **Configuration**
```yaml
# config/env.yaml
TESTING_MODE: "mock"
MOCK_MODE: true

# Mock Services
TARGET_API_BASE_URL: "http://localhost:8080/mock-netskope"
API_KEY: "mock-api-key-12345"

# Mock Data Sources
MOCK_RESPONSES_PATH: "./tests/mock_responses"
TEST_DATA_PATH: "./tests/data"
```

#### **Validation**
```bash
# Run mock environment tests
pytest tests/unit/ -v -m mock

# Expected output:
#  15 tests passed in 2.3 seconds
#  Mock services responding correctly
#  All synthetic data generated successfully
```

### **Mock Services Available**

| Service | Endpoint | Purpose |
|---------|----------|---------|
| Target API | `localhost:8080` | Security policy simulation |
| Redis Mock | In-memory | Caching simulation |
| Kafka Mock | In-memory | Event streaming simulation |
| MongoDB Mock | In-memory | Data persistence simulation |
| AWS Mock | In-memory | Cloud service simulation |

---

##  Environment 2: Local Environment

### **Purpose**
- Integration testing with real services
- Docker-based service orchestration
- Controlled test data management
- Development environment that mirrors production

### **Setup Instructions**

#### **Prerequisites**
```bash
# Required software
- Docker Desktop 4.0+
- Docker Compose 2.0+
- kubectl (for Kubernetes testing)
- LocalStack CLI (for AWS simulation)

# System requirements
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space
- Internet connection for image downloads
```

#### **Service Setup**
```bash
# 1. Start complete local environment (recommended)
python scripts/start_local_environment.py

# OR manually start services
docker-compose -f docker-compose.local.yml up -d

# 2. Verify services are running
docker-compose -f docker-compose.local.yml ps

# 3. Check service health
python scripts/start_local_environment.py --status

# 4. Run integration tests
pytest tests/integration/ -v
```

#### **Docker Compose Configuration**
```yaml
# docker-compose.local.yml
version: '3.8'

services:
  # Redis for caching and sessions
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Kafka for event streaming
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    healthcheck:
      test: ["CMD", "kafka-topics", "--bootstrap-server", "localhost:9092", "--list"]
      interval: 30s
      timeout: 10s
      retries: 3

  # MongoDB for data persistence
  mongodb:
    image: mongo:6
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: netskope_admin_2024
      MONGO_INITDB_DATABASE: netskope_local
    volumes:
      - mongodb_data:/data/db
      - ./scripts/mongo-init.js:/docker-entrypoint-initdb.d/mongo-init.js
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3

  # LocalStack for AWS services
  localstack:
    image: localstack/localstack:latest
    ports:
      - "4566:4566"
    environment:
      SERVICES: s3,iam,lambda,cloudwatch,dynamodb
      DEBUG: 1
      DATA_DIR: /tmp/localstack/data
      DOCKER_HOST: unix:///var/run/docker.sock
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock"
      - localstack_data:/tmp/localstack
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Prometheus for metrics
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  # Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./config/grafana/datasources:/etc/grafana/provisioning/datasources

volumes:
  redis_data:
  mongodb_data:
  localstack_data:
  prometheus_data:
  grafana_data:
```

#### **Environment Configuration**
```yaml
# config/env.yaml (Local mode)
TESTING_MODE: "local"
MOCK_MODE: false

# Service Endpoints
REDIS_URL: "redis://localhost:6379"
KAFKA_BROKERS: "localhost:9092"
MONGODB_URL: "mongodb://admin:netskope_admin_2024@localhost:27017/netskope_local?authSource=admin"
AWS_ENDPOINT_URL: "http://localhost:4566"

# AWS LocalStack Configuration
AWS_ACCESS_KEY_ID: "test"
AWS_SECRET_ACCESS_KEY: "test"
AWS_DEFAULT_REGION: "us-east-1"

# Monitoring
PROMETHEUS_URL: "http://localhost:9090"
GRAFANA_URL: "http://localhost:3000"
```

#### **Validation**
```bash
# Run integration tests
pytest tests/integration/ -v -m local

# Check service health
curl http://localhost:4566/health  # LocalStack
redis-cli ping                     # Redis
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list  # Kafka

# View monitoring dashboards
open http://localhost:3000  # Grafana (admin/admin)
open http://localhost:9090  # Prometheus
```

### Complete Monitoring Flow (Local Environment)

#### Step 1: Start the monitoring stack
```bash
docker-compose -f docker-compose.local.yml up -d
docker-compose -f docker-compose.local.yml ps
```

#### Step 2: Install dependencies
```bash
pip install prometheus-client
```

#### Step 3: Run tests (metrics auto-collected)
```bash
TESTING_MODE=local pytest tests/ -v
```

#### Step 4: View results in Grafana
```bash
open http://localhost:3000/d/framework-overview
```

> **Troubleshooting**: If Grafana login has issues, use alternative methods:
> - Prometheus: http://localhost:9090
> - Test results via CLI: `day1-sdet results --stats`

#### Step 5: Query test results via CLI (recommended)
```bash
day1-sdet results --stats
day1-sdet results --failed
```

#### Step 6: Review test results in MongoDB
```bash
mongosh "mongodb://admin:netskope_admin_2024@localhost:27017/netskope_local?authSource=admin"
db.test_results.find().sort({start_time: -1}).limit(10)
```

**For complete monitoring flow, see:** [TUTORIAL.md](./TUTORIAL.md)
```

---

##  Environment 3: Integration Environment

### **Purpose**
- End-to-end testing with production-like services
- Kubernetes-based orchestration
- Realistic data volumes and patterns
- Performance and security validation

### **IMPORTANT: Requires Kubernetes Cluster**

The Integration Environment (E3) **requires an existing Kubernetes cluster**. The framework does NOT create a cluster—it only deploys manifests to an existing one.

**Setup a local Kubernetes cluster first:**

```bash
# Option 1: Minikube (recommended)
minikube start --driver=virtualbox  # or --driver=hyperkit on macOS
minikube addons enable ingress

# Option 2: Kind (Kubernetes in Docker)
kind create cluster --name netskope-integration

# Option 3: K3s (lightweight)
curl -sfL https://get.k3s.io | sh -

# Option 4: Docker Desktop Kubernetes
# Enable in Docker Desktop → Settings → Kubernetes
```

**For local development without Kubernetes**, use E2 (Local with Docker Compose):
```bash
docker-compose -f docker-compose.local.yml up -d
TESTING_MODE=local pytest tests/integration/test_local_environment.py -v
```

### **Setup Instructions**

#### **Prerequisites**
```bash
# Required tools
- kubectl configured with cluster access
- Helm 3.0+ (optional, can use kubectl directly)
- Docker (for building custom images)

# Permissions required
- Kubernetes cluster access
- Container registry push/pull access (for custom images)
```

#### **Kubernetes Deployment**
```bash
# 1. Deploy using the framework CLI
day1-sdet integration deploy

# 2. Verify deployment
day1-sdet integration status
kubectl get pods -n netskope-integration

# 3. Run tests
TESTING_MODE=integration pytest tests/integration/test_integration_environment.py -v
```

#### **Kubernetes Manifests**
```yaml
# k8s/integration/test-runner-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: netskope-test-runner
  namespace: netskope-integration
spec:
  replicas: 3
  selector:
    matchLabels:
      app: netskope-test-runner
  template:
    metadata:
      labels:
        app: netskope-test-runner
    spec:
      containers:
      - name: test-runner
        image: netskope/sdet-framework:latest
        env:
        - name: TESTING_MODE
          value: "integration"
        - name: REDIS_URL
          value: "redis://redis-master:6379"
        - name: KAFKA_BROKERS
          value: "kafka:9092"
        - name: MONGODB_URL
          valueFrom:
            secretKeyRef:
              name: mongodb-secret
              key: connection-string
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### **Configuration Management**
```yaml
# k8s/integration/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: netskope-config
  namespace: netskope-integration
data:
  env.yaml: |
    TESTING_MODE: "integration"
    MOCK_MODE: false
    
    # Service Discovery
    REDIS_URL: "redis://redis-master:6379"
    KAFKA_BROKERS: "kafka:9092"
    MONGODB_URL: "mongodb://mongodb:27017/day1_integration"
    
    # External Services
    TARGET_API_BASE_URL: "https://demo.goskope.com"
    AWS_REGION: "us-east-1"
    
    # Performance Settings
    MAX_CONCURRENT_TESTS: 50
    TEST_TIMEOUT: 300
    RETRY_ATTEMPTS: 3
```

#### **Secrets Management**
```yaml
# k8s/integration/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: netskope-secrets
  namespace: netskope-integration
type: Opaque
data:
  api-key: <base64-encoded-api-key>
  mongodb-password: <base64-encoded-password>
  redis-password: <base64-encoded-password>
  aws-access-key: <base64-encoded-access-key>
  aws-secret-key: <base64-encoded-secret-key>
```

#### **Validation**
```bash
# Run E2E tests
kubectl exec -it deployment/netskope-test-runner -n netskope-integration -- \
  pytest tests/e2e/ -v --html=reports/e2e-report.html

# Check service health
kubectl get pods -n netskope-integration
kubectl logs -f deployment/netskope-test-runner -n netskope-integration

# Monitor resources
kubectl top pods -n netskope-integration
kubectl describe hpa netskope-test-runner -n netskope-integration
```

---

##  Environment 4: Staging Environment

### **Purpose**
- Production readiness validation
- Performance and load testing
- Security and compliance verification
- Final validation before production deployment

### **Setup Instructions**

#### **Infrastructure Requirements**
```yaml
# Minimum resource requirements
compute:
  nodes: 5
  cpu_per_node: 8 cores
  memory_per_node: 32GB
  storage_per_node: 500GB SSD

networking:
  load_balancer: true
  ssl_termination: true
  cdn: optional
  
monitoring:
  prometheus: true
  grafana: true
  alertmanager: true
  jaeger: true  # Distributed tracing
```

#### **Production-Like Configuration**
```yaml
# config/staging.yaml
TESTING_MODE: "staging"
ENVIRONMENT: "staging"

# High Availability Services
REDIS_CLUSTER_NODES:
  - "redis-1.staging.internal:6379"
  - "redis-2.staging.internal:6379"
  - "redis-3.staging.internal:6379"

KAFKA_CLUSTER_BROKERS:
  - "kafka-1.staging.internal:9092"
  - "kafka-2.staging.internal:9092"
  - "kafka-3.staging.internal:9092"

MONGODB_REPLICA_SET:
  primary: "mongo-primary.staging.internal:27017"
  secondaries:
    - "mongo-secondary-1.staging.internal:27017"
    - "mongo-secondary-2.staging.internal:27017"

# External Services
TARGET_API_BASE_URL: "https://staging.goskope.com"
AWS_REGION: "us-east-1"

# Performance Configuration
MAX_CONCURRENT_CONNECTIONS: 1000
CONNECTION_POOL_SIZE: 100
CACHE_TTL: 300
BATCH_SIZE: 1000

# Security Configuration
TLS_ENABLED: true
MUTUAL_TLS: true
ENCRYPTION_AT_REST: true
AUDIT_LOGGING: true
```

#### **Load Testing Setup**
```python
# scripts/load_test_staging.py
from locust import HttpUser, task, between
import random

class NetskopeAPIUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Authenticate user
        response = self.client.post("/auth/login", json={
            "username": f"test_user_{random.randint(1, 1000)}",
            "password": "test_password"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def get_events(self):
        self.client.get("/api/v2/events", headers=self.headers)
    
    @task(2)
    def get_policies(self):
        self.client.get("/api/v2/policies", headers=self.headers)
    
    @task(1)
    def create_user(self):
        self.client.post("/api/v2/users", 
                        headers=self.headers,
                        json={"username": f"user_{random.randint(1, 10000)}"})

# Load test configuration
LOAD_TEST_CONFIG = {
    "users": 500,
    "spawn_rate": 10,
    "duration": "30m",
    "host": "https://staging-api.netskope.com"
}
```

#### **Performance Monitoring**
```yaml
# config/monitoring/prometheus-staging.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'netskope-api'
    static_configs:
      - targets: ['api-1:8080', 'api-2:8080', 'api-3:8080']
    metrics_path: /metrics
    scrape_interval: 5s

  - job_name: 'redis-cluster'
    static_configs:
      - targets: ['redis-1:9121', 'redis-2:9121', 'redis-3:9121']

  - job_name: 'kafka-cluster'
    static_configs:
      - targets: ['kafka-1:9308', 'kafka-2:9308', 'kafka-3:9308']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

#### **Validation**
```bash
# Deploy to staging
helm upgrade --install netskope-staging ./helm/netskope \
  --namespace netskope-staging \
  --values config/staging-values.yaml

# Run performance tests
locust -f scripts/load_test_staging.py \
  --users 500 \
  --spawn-rate 10 \
  --run-time 30m \
  --host https://staging-api.netskope.com

# Security validation
pytest tests/security/ -v --environment=staging
pytest tests/compliance/ -v --environment=staging

# Monitor performance
open https://grafana.staging.netskope.com
```

---

##  Environment 5: Production Environment

### **Purpose**
- Live system monitoring and validation
- Production health checks
- Real-time performance monitoring
- Incident response and debugging

### **Setup Instructions**

#### **Production Monitoring**
```yaml
# Production monitoring configuration
monitoring:
  synthetic_tests:
    frequency: "5m"
    timeout: "30s"
    endpoints:
      - "/api/v2/health"
      - "/api/v2/events"
      - "/api/v2/policies"
  
  performance_tests:
    frequency: "1h"
    duration: "5m"
    max_users: 50
  
  security_scans:
    frequency: "daily"
    vulnerability_scan: true
    compliance_check: true
```

#### **Health Check Implementation**
```python
# scripts/production_health_check.py
import requests
import time
import logging
from datetime import datetime

class ProductionHealthChecker:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.logger = logging.getLogger(__name__)
    
    def check_api_health(self):
        """Check API endpoint health"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v2/health",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info("API health check passed")
                return True
            else:
                self.logger.error(f"API health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"API health check error: {str(e)}")
            return False
    
    def check_performance(self):
        """Check API performance"""
        start_time = time.time()
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v2/events?limit=10",
                headers=self.headers,
                timeout=5
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200 and response_time < 2.0:
                self.logger.info(f"Performance check passed: {response_time:.2f}s")
                return True
            else:
                self.logger.warning(f"Performance check failed: {response_time:.2f}s")
                return False
                
        except Exception as e:
            self.logger.error(f"Performance check error: {str(e)}")
            return False
    
    def run_continuous_monitoring(self):
        """Run continuous health monitoring"""
        while True:
            timestamp = datetime.now().isoformat()
            
            # Health checks
            api_healthy = self.check_api_health()
            performance_ok = self.check_performance()
            
            # Log results
            status = "HEALTHY" if api_healthy and performance_ok else "UNHEALTHY"
            self.logger.info(f"[{timestamp}] System status: {status}")
            
            # Alert if unhealthy
            if not (api_healthy and performance_ok):
                self.send_alert(f"Production system unhealthy at {timestamp}")
            
            # Wait before next check
            time.sleep(300)  # 5 minutes
    
    def send_alert(self, message):
        """Send alert to monitoring system"""
        # Implementation depends on alerting system (PagerDuty, Slack, etc.)
        self.logger.critical(f"ALERT: {message}")
```

#### **Production Configuration**
```yaml
# config/production.yaml
TESTING_MODE: "production"
ENVIRONMENT: "production"

# Read-only access for monitoring
DATABASE_READ_ONLY: true
API_READ_ONLY: true

# Monitoring configuration
HEALTH_CHECK_INTERVAL: 300  # 5 minutes
PERFORMANCE_CHECK_INTERVAL: 3600  # 1 hour
ALERT_THRESHOLD_RESPONSE_TIME: 2.0  # seconds
ALERT_THRESHOLD_ERROR_RATE: 0.01  # 1%

# Security configuration
AUDIT_ALL_REQUESTS: true
RATE_LIMITING_ENABLED: true
IP_WHITELIST_ENABLED: true

# Compliance
DATA_RETENTION_DAYS: 2555  # 7 years for compliance
ENCRYPTION_REQUIRED: true
ACCESS_LOGGING_REQUIRED: true
```

#### **Validation**
```bash
# Run production health checks
python scripts/production_health_check.py

# Monitor system metrics
kubectl get pods -n netskope-production
kubectl top nodes
kubectl top pods -n netskope-production

# Check alerts
curl -s http://alertmanager.netskope.com/api/v1/alerts | jq '.'

# View dashboards
open https://grafana.netskope.com/d/production-overview
```

---

##  Environment Management Scripts

### **Environment Switcher**
```python
# scripts/environment_manager.py
import os
import yaml
import subprocess
from typing import Dict, Any

class EnvironmentManager:
    def __init__(self):
        self.environments = {
            "mock": self._setup_mock,
            "local": self._setup_local,
            "integration": self._setup_integration,
            "staging": self._setup_staging,
            "production": self._setup_production
        }
    
    def switch_environment(self, env_name: str):
        """Switch to specified environment"""
        if env_name not in self.environments:
            raise ValueError(f"Unknown environment: {env_name}")
        
        print(f"Switching to {env_name} environment...")
        self.environments[env_name]()
        print(f" Successfully switched to {env_name} environment")
    
    def _setup_mock(self):
        """Setup mock environment"""
        self._update_config("mock")
        subprocess.run(["python", "start_mock_mode.py"], check=True)
    
    def _setup_local(self):
        """Setup local environment"""
        self._update_config("local")
        subprocess.run(["docker-compose", "-f", "docker-compose.local.yml", "up", "-d"], check=True)
        self._wait_for_services()
    
    def _setup_integration(self):
        """Setup integration environment"""
        self._update_config("integration")
        subprocess.run(["kubectl", "apply", "-f", "k8s/integration/"], check=True)
    
    def _setup_staging(self):
        """Setup staging environment"""
        self._update_config("staging")
        # Staging setup handled by CI/CD pipeline
    
    def _setup_production(self):
        """Setup production monitoring"""
        self._update_config("production")
        # Production is read-only monitoring
    
    def _update_config(self, env_name: str):
        """Update configuration for environment"""
        config_file = f"config/{env_name}.yaml"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            with open("config/env.yaml", 'w') as f:
                yaml.dump(config, f)
    
    def _wait_for_services(self):
        """Wait for services to be ready"""
        import time
        import requests
        
        services = [
            ("Redis", "http://localhost:6379"),
            ("Kafka", "http://localhost:9092"),
            ("MongoDB", "http://localhost:27017"),
            ("LocalStack", "http://localhost:4566/health")
        ]
        
        for service_name, url in services:
            print(f"Waiting for {service_name}...")
            for _ in range(30):  # 30 attempts
                try:
                    if "health" in url:
                        response = requests.get(url, timeout=5)
                        if response.status_code == 200:
                            break
                    else:
                        # For other services, just check if port is open
                        import socket
                        host, port = url.replace("http://", "").split(":")
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        result = sock.connect_ex((host, int(port)))
                        sock.close()
                        if result == 0:
                            break
                except:
                    pass
                time.sleep(2)
            else:
                print(f"  Warning: {service_name} may not be ready")
            
            print(f" {service_name} is ready")

# Usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python environment_manager.py <environment>")
        print("Environments: mock, local, integration, staging, production")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    env_manager.switch_environment(sys.argv[1])
```

### **Test Runner Script**
```bash
#!/bin/bash
# scripts/run_tests.sh

set -e

ENVIRONMENT=${1:-mock}
TEST_SUITE=${2:-all}

echo " Running tests in $ENVIRONMENT environment"

case $ENVIRONMENT in
    "mock")
        echo "Starting mock services..."
        python start_mock_mode.py &
        MOCK_PID=$!
        sleep 5
        
        echo "Running unit tests..."
        pytest tests/unit/ -v -m mock --html=reports/unit-report.html
        
        kill $MOCK_PID
        ;;
        
    "local")
        echo "Starting local services..."
        docker-compose -f docker-compose.local.yml up -d
        
        echo "Waiting for services to be ready..."
        python scripts/wait_for_services.py
        
        echo "Running integration tests..."
        pytest tests/integration/ -v -m local --html=reports/integration-report.html
        
        echo "Cleaning up..."
        docker-compose -f docker-compose.local.yml down
        ;;
        
    "integration")
        echo "Running E2E tests in integration environment..."
        pytest tests/e2e/ -v -m integration --html=reports/e2e-report.html
        ;;
        
    "staging")
        echo "Running performance tests in staging environment..."
        pytest tests/performance/ -v -m staging --html=reports/performance-report.html
        ;;
        
    "production")
        echo "Running production health checks..."
        python scripts/production_health_check.py
        ;;
        
    *)
        echo "Unknown environment: $ENVIRONMENT"
        echo "Available environments: mock, local, integration, staging, production"
        exit 1
        ;;
esac

echo " Tests completed successfully!"
```

---

##  Environment Comparison

| Feature | Mock | Local | Integration | Staging | Production |
|---------|------|-------|-------------|---------|------------|
| **Setup Time** | <1 min | <5 min | <15 min | <30 min | N/A |
| **Resource Usage** | Minimal | Medium | High | Very High | Read-only |
| **Data Realism** | Synthetic | Controlled | Realistic | Production-like | Real |
| **Test Speed** | Very Fast | Fast | Medium | Slow | Monitoring |
| **Cost** | Free | Low | Medium | High | Monitoring only |
| **Isolation** | Complete | High | Medium | Low | None |
| **Debugging** | Easy | Easy | Medium | Hard | Limited |

##  Environment Selection Guide

### **When to Use Each Environment**

- **Mock**: Daily development, unit tests, TDD, CI/CD pipelines
- **Local**: Integration testing, debugging, feature development
- **Integration**: E2E testing, release validation, security testing
- **Staging**: Performance testing, load testing, pre-production validation
- **Production**: Health monitoring, incident investigation, compliance auditing

This comprehensive environment setup ensures robust testing capabilities across the entire development lifecycle while maintaining security, performance, and compliance standards.