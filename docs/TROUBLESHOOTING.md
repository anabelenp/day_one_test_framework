# Day-1 Test Framework - Troubleshooting Guide

##  Common Issues and Solutions

### **Environment Detection Issues**

#### **Problem**: CLI shows "production" environment instead of "local"
```bash
python src/cli.py env info
# Shows: Environment: production (should be local)
```

**Solution**: Set the TESTING_MODE environment variable
```bash
export TESTING_MODE=local
python src/cli.py env info
# Now shows: Environment: local
```

**Root Cause**: Environment detection prioritizes configuration file existence. If multiple config files exist, it may default to production.

#### **Problem**: Environment validation fails with " Invalid"
```bash
python src/cli.py env validate
# Shows:  local environment validation failed
```

**Solution**: Check service connectivity
```bash
# Check if Docker services are running
docker-compose -f docker-compose.local.yml ps

# Start services if not running
docker-compose -f docker-compose.local.yml up -d

# Test connectivity manually
python -c "
import socket
def test_port(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

services = [('Redis', 'localhost', 6379), ('Kafka', 'localhost', 9092), ('MongoDB', 'localhost', 27017)]
for name, host, port in services:
    status = '' if test_port(host, port) else ''
    print(f'{name}: {status}')
"
```

### **Service Health Check Issues**

#### **Problem**: All services show " Unhealthy"
```bash
python src/cli.py services health
# Shows: cache:  Unhealthy, message:  Unhealthy, etc.
```

**Solution 1**: Check Docker Compose services
```bash
# Check service status
docker-compose -f docker-compose.local.yml ps

# Restart services if needed
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d

# Wait for services to be healthy
docker-compose -f docker-compose.local.yml ps
```

**Solution 2**: Check service credentials
```bash
# Verify MongoDB credentials match
grep -A 5 "mongodb:" config/local.yaml
grep -A 5 "MONGO_INITDB" docker-compose.local.yml

# Should match: admin/admin_2024
```

**Solution 3**: Check for missing services
```bash
# Ensure Mock API service is running
docker-compose -f docker-compose.local.yml up -d target-api-mock

# Test Mock API
curl http://localhost:8080/health
```

#### **Problem**: Kafka service fails with "kafka-python library not installed"
```bash
# Error: kafka-python library not installed. Run: pip install kafka-python
```

**Solution**: The framework uses mock Kafka for local development
```bash
# This is expected behavior for local environment
# Kafka will show as healthy using mock client
export TESTING_MODE=local
python src/cli.py services health
# Should show: message:  Healthy (using mock client)
```

### **Docker Compose Issues**

#### **Problem**: LocalStack keeps restarting
```bash
docker-compose -f docker-compose.local.yml ps
# Shows: day1-localstack ... Restarting (1) 55 seconds ago
```

**Solution**: Check LocalStack logs and fix volume issues
```bash
# Check logs
docker-compose -f docker-compose.local.yml logs localstack

# If volume issues, clean up and restart
docker-compose -f docker-compose.local.yml down --volumes
docker-compose -f docker-compose.local.yml up -d
```

#### **Problem**: Zookeeper still running after KRaft upgrade
```bash
docker ps | grep zookeeper
# Shows old Zookeeper container
```

**Solution**: Clean up old containers
```bash
# Stop and remove old Zookeeper
docker stop day1-zookeeper
docker rm day1-zookeeper

# Restart with clean KRaft setup
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d
```

### **Authentication Issues**

#### **Problem**: MongoDB authentication failed
```bash
# Error: Authentication failed., full error: {'ok': 0.0, 'errmsg': 'Authentication failed.'}
```

**Solution**: Update credentials in config/local.yaml
```yaml
mongodb:
  host: "localhost"
  port: 27017
  username: "admin"  # Must match Docker Compose
  password: "admin_2024"  # Must match Docker Compose
  database: "day1_local"
```

#### **Problem**: Redis connection refused
```bash
# Error: Redis not accessible at localhost:6379
```

**Solution**: Check Redis service and port mapping
```bash
# Check if Redis is running
docker-compose -f docker-compose.local.yml ps redis

# Check port mapping
docker port day1-redis
# Should show: 6379/tcp -> 0.0.0.0:6379

# Test Redis directly
docker-compose -f docker-compose.local.yml exec redis redis-cli ping
# Should return: PONG
```

### **Network Connectivity Issues**

#### **Problem**: Services not accessible from host
```bash
# Error: Connection refused to localhost:6379, localhost:9092, etc.
```

**Solution**: Check Docker network and port mappings
```bash
# Check Docker network
docker network ls | grep day1

# Check port mappings for all services
docker-compose -f docker-compose.local.yml ps --format "table {{.Name}}\t{{.Ports}}"

# Restart Docker if needed (macOS/Windows)
# Docker Desktop -> Restart Docker Desktop
```

### **Import and Dependency Issues**

#### **Problem**: Module import errors
```bash
# Error: ModuleNotFoundError: No module named 'src.environment_manager'
```

**Solution**: Check Python path and installation
```bash
# Install framework in development mode
pip install -e .

# Or add src to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Verify installation
python -c "from src.environment_manager import get_current_environment; print(' Import successful')"
```

#### **Problem**: Missing dependencies
```bash
# Error: No module named 'redis', 'pymongo', etc.
```

**Solution**: Install all dependencies
```bash
# Install from requirements.txt
pip install -r requirements.txt

# Or install specific packages
pip install redis pymongo requests pyyaml
```

### **Performance Issues**

#### **Problem**: Slow service startup or timeouts
```bash
# Services take too long to start or timeout during health checks
```

**Solution**: Increase timeouts and check system resources
```bash
# Check system resources
docker stats --no-stream

# Increase Docker memory/CPU limits (Docker Desktop)
# Docker Desktop -> Settings -> Resources

# Restart with increased timeouts
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d
```

##  Debugging Commands

### **Environment Debugging**
```bash
# Check current environment detection
export TESTING_MODE=local
python src/cli.py env detect

# Get detailed environment info
python src/cli.py env info

# Validate environment with verbose logging
python src/cli.py --verbose env validate
```

### **Service Debugging**
```bash
# Check individual service health
python src/cli.py services health

# Get service connection info
python src/cli.py services info

# Test individual services
python src/cli.py services test cache
python src/cli.py services test message
python src/cli.py services test database
```

### **Docker Debugging**
```bash
# Check all container status
docker-compose -f docker-compose.local.yml ps

# Check container logs
docker-compose -f docker-compose.local.yml logs redis
docker-compose -f docker-compose.local.yml logs kafka
docker-compose -f docker-compose.local.yml logs mongodb

# Check container health
docker inspect day1-redis | grep -A 10 "Health"
```

### **Network Debugging**
```bash
# Test port connectivity
nc -zv localhost 6379  # Redis
nc -zv localhost 9092  # Kafka
nc -zv localhost 27017 # MongoDB
nc -zv localhost 8080  # Mock API

# Check listening ports
lsof -i :6379
lsof -i :9092
lsof -i :27017
lsof -i :8080
```

##  Emergency Recovery

### **Complete Environment Reset**
```bash
# Nuclear option - reset everything
docker-compose -f docker-compose.local.yml down --volumes --remove-orphans
docker system prune -f
docker volume prune -f

# Remove any old containers
docker ps -a | grep day1 | awk '{print $1}' | xargs docker rm -f

# Start fresh
docker-compose -f docker-compose.local.yml up -d

# Wait for services to be healthy
sleep 30
export TESTING_MODE=local
python src/cli.py env validate
python src/cli.py services health
```

### **Service-Specific Recovery**

#### **Redis Recovery**
```bash
docker-compose -f docker-compose.local.yml stop redis
docker-compose -f docker-compose.local.yml rm -f redis
docker volume rm day1_test_framework_redis_data
docker volume rm day1_test_framework_kafka_data
docker volume rm day1_test_framework_mongodb_data
docker volume rm day1_test_framework_mongodb_config
docker-compose -f docker-compose.local.yml up -d mongodb
```

##  Getting Help

### **Check Framework Status**
```bash
# Quick health check
export TESTING_MODE=local
python src/cli.py env info
python src/cli.py services health

# Detailed status
docker-compose -f docker-compose.local.yml ps
docker stats --no-stream
```

### **Collect Debug Information**
```bash
# Create debug report
echo "=== Environment Info ===" > debug_report.txt
python src/cli.py env info >> debug_report.txt
echo -e "\n=== Service Health ===" >> debug_report.txt
python src/cli.py services health >> debug_report.txt
echo -e "\n=== Docker Status ===" >> debug_report.txt
docker-compose -f docker-compose.local.yml ps >> debug_report.txt
echo -e "\n=== System Resources ===" >> debug_report.txt
docker stats --no-stream >> debug_report.txt

cat debug_report.txt
```

### **Kubernetes Integration Deployment Issues**

#### **Problem**: Zookeeper fails with "serverid zookeeper-0 is not a number"
```bash
kubectl logs zookeeper-0 -n netskope-integration --previous
# Output shows: Invalid config, exiting abnormally
# Caused by: java.lang.IllegalArgumentException: serverid zookeeper-0 is not a number
```

**Solution**: Update `k8s/integration/kafka-cluster.yaml` - change `ZOOKEEPER_SERVER_ID` to use pod index:
```yaml
# Change from:
- name: ZOOKEEPER_SERVER_ID
  valueFrom:
    fieldRef:
      fieldPath: metadata.name

# To:
- name: ZOOKEEPER_SERVER_ID
  valueFrom:
    fieldRef:
      fieldPath: metadata.labels['apps.kubernetes.io/pod-index']
```

**Then redeploy**:
```bash
day1-sdet integration undeploy
day1-sdet integration deploy
```

#### **Problem**: Kafka pods stuck waiting for Zookeeper
```bash
kubectl get pods -n netskope-integration -l app=kafka
# Shows: Init:0/1 (waiting for init container)
```

**Solution**:
```bash
# Verify Zookeeper is running
kubectl get pods -n netskope-integration -l app=zookeeper

# Check Zookeeper is ready
kubectl exec -it zookeeper-0 -n netskope-integration -- sh -c 'echo ruok | nc localhost 2181'
# Should return: imok
```

#### **Problem**: "Cannot connect to Kubernetes cluster"
```bash
day1-sdet integration deploy
# Output: Cannot connect to Kubernetes cluster
```

**Solution**: Ensure a Kubernetes cluster is running:
```bash
# Check if kubectl is configured
kubectl cluster-info

# If using Docker Desktop, enable Kubernetes in Settings → Kubernetes

# If using Kind
kind create cluster --name day1-integration

# If using Minikube
minikube start
```

#### **Problem**: Zookeeper shows "My id 0 not in the peer list"
```bash
kubectl logs zookeeper-0 -n netskope-integration
# Output shows: java.lang.RuntimeException: My id 0 not in the peer list
```

**Solution**: For single-node Zookeeper, configure properly:
```yaml
# In k8s/integration/kafka-cluster.yaml, update Zookeeper env:
- name: ZOOKEEPER_CLIENT_PORT
  value: "2181"
- name: ZOOKEEPER_TICK_TIME
  value: "2000"
- name: ZOOKEEPER_INIT_LIMIT
  value: "5"
- name: ZOOKEEPER_SYNC_LIMIT
  value: "2"
- name: ZOOKEEPER_ADMIN_ENABLE_SERVER
  value: "false"
- name: ZOOKEEPER_4LW_COMMANDS_WHITELIST
  value: "ruok,conf,stat,mntr"
- name: ZOOKEEPER_SERVER_ID
  value: "0"

# Also update StatefulSet to use 1 replica (not 3):
spec:
  replicas: 1
```

**Then apply and recreate**:
```bash
kubectl apply -f k8s/integration/kafka-cluster.yaml
kubectl delete pvc -n netskope-integration zookeeper-data-zookeeper-0 zookeeper-logs-zookeeper-0
kubectl delete pod -n netskope-integration zookeeper-0 --force --grace-period=0
```

#### **Problem**: Zookeeper readiness probe fails with "Connection refused"
```bash
kubectl describe pod zookeeper-0 -n netskope-integration
# Shows: Readiness probe failed: Ncat: Connection refused.
```

**Solution**: The exec-based readiness probe is unreliable. Update to TCP socket probe:
```yaml
# In k8s/integration/kafka-cluster.yaml, change probes to TCP:
livenessProbe:
  tcpSocket:
    port: 2181
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  tcpSocket:
    port: 2181
  initialDelaySeconds: 5
  periodSeconds: 5
```

#### **Problem**: Kafka fails with "Invalid value for configuration broker.id: Not a number"
```bash
kubectl logs kafka-cluster-0 -n netskope-integration
# Output: Invalid value kafka-cluster-0 for configuration broker.id: Not a number of type INT
```

**Solution**: The broker ID is using the pod name instead of a number. Update in kafka-cluster.yaml:
```yaml
# Change from:
- name: KAFKA_BROKER_ID
  valueFrom:
    fieldRef:
      fieldPath: metadata.name

# To:
- name: KAFKA_BROKER_ID
  valueFrom:
    fieldRef:
      fieldPath: metadata.labels['apps.kubernetes.io/pod-index']
```

#### **Problem**: Kafka fails with "Unable to parse PLAINTEXT://$(POD_NAME).kafka-headless:9092"
```bash
kubectl logs kafka-cluster-0 -n netskope-integration
# Output: Unable to parse PLAINTEXT://$(POD_NAME).kafka-headless:9092 to a broker endpoint
```

**Solution**: The environment variable substitution doesn't work in Kubernetes env vars. Use a static FQDN:
```yaml
# Change from:
- name: KAFKA_ADVERTISED_LISTENERS
  value: "PLAINTEXT://$(POD_NAME).kafka-headless:9092"

# To (for single broker):
- name: KAFKA_ADVERTISED_LISTENERS
  value: "PLAINTEXT://kafka-cluster-0.kafka-headless.netskope-integration.svc.cluster.local:9092"

# Also ensure POD_NAME env var is defined:
- name: POD_NAME
  valueFrom:
    fieldRef:
      fieldPath: metadata.name
```

#### **Problem**: Kafka readiness probe times out
```bash
kubectl describe pod kafka-cluster-0 -n netskope-integration
# Shows: Readiness probe failed: command timed out: "sh -c kafka-broker-api-versions..."
```

**Solution**: The exec-based probe is slow. Change to TCP socket probe:
```yaml
# In k8s/integration/kafka-cluster.yaml:
livenessProbe:
  tcpSocket:
    port: 9092
  initialDelaySeconds: 60
  periodSeconds: 30
readinessProbe:
  tcpSocket:
    port: 9092
  initialDelaySeconds: 30
  periodSeconds: 10
```

**Also reduce Kafka replication for single-node**:
```yaml
- name: KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR
  value: "1"
- name: KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR
  value: "1"
- name: KAFKA_DEFAULT_REPLICATION_FACTOR
  value: "1"
- name: KAFKA_MIN_INSYNC_REPLICAS
  value: "1"
- name: KAFKA_NUM_PARTITIONS
  value: "1"
```

#### **Problem**: Service endpoints show no endpoints
```bash
kubectl get endpoints -n netskope-integration
# Shows: zookeeper-service   <empty>
```

**Solution**: This usually means the pod isn't ready. Check pod status:
```bash
# Check if pod is actually running and ready
kubectl get pods -n netskope-integration -l app=zookeeper

# If running but not ready, check the readiness probe issue above

# Check service selector matches pod labels
kubectl describe svc zookeeper-service -n netskope-integration | grep Selector
# Should show: app=zookeeper
```

### **Common Solutions Summary**

| Issue | Quick Fix |
|-------|-----------|
| Environment shows "production" | `export TESTING_MODE=local` |
| Services unhealthy | `docker-compose -f docker-compose.local.yml restart` |
| MongoDB auth failed | Update credentials in `config/local.yaml` |
| Kafka import error | Expected - uses mock client in local mode |
| LocalStack restarting | `docker-compose down --volumes && docker-compose up -d` |
| Port not accessible | Check Docker port mappings and restart Docker |
| Import errors | `pip install -e .` |
| Slow startup | Increase Docker resources and timeouts |

---

** Pro Tip**: Always start with `export TESTING_MODE=local` and `docker-compose -f docker-compose.local.yml ps` to check the basic setup before diving into specific issues.