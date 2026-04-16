# Netskope SDET Framework - Troubleshooting Guide

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

# Should match: admin/netskope_admin_2024
```

**Solution 3**: Check for missing services
```bash
# Ensure Mock API service is running
docker-compose -f docker-compose.local.yml up -d netskope-api-mock

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
# Shows: netskope-localstack ... Restarting (1) 55 seconds ago
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
docker stop netskope-zookeeper
docker rm netskope-zookeeper

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
  password: "netskope_admin_2024"  # Must match Docker Compose
  database: "netskope_local"
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
docker port netskope-redis
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
docker network ls | grep netskope

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
docker inspect netskope-redis | grep -A 10 "Health"
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
docker ps -a | grep netskope | awk '{print $1}' | xargs docker rm -f

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
docker volume rm netskope_day_one_test_framework_redis_data
docker-compose -f docker-compose.local.yml up -d redis
```

#### **Kafka Recovery**
```bash
docker-compose -f docker-compose.local.yml stop kafka
docker-compose -f docker-compose.local.yml rm -f kafka
docker volume rm netskope_day_one_test_framework_kafka_data
docker-compose -f docker-compose.local.yml up -d kafka
```

#### **MongoDB Recovery**
```bash
docker-compose -f docker-compose.local.yml stop mongodb
docker-compose -f docker-compose.local.yml rm -f mongodb
docker volume rm netskope_day_one_test_framework_mongodb_data
docker volume rm netskope_day_one_test_framework_mongodb_config
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