# Day-1 Framework - Monitoring and Reports Guide

##  Overview

The Day-1 Framework includes a comprehensive monitoring stack with multiple platforms for observability, metrics, and reporting. This guide covers how to access, configure, and use each monitoring platform.

##  Quick Access

### **Service URLs (Local Environment)**
| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| **Grafana** | http://localhost:3000 | admin/netskope_grafana_2024 | Dashboards & Visualization |
| **Prometheus** | http://localhost:9090 | None | Metrics Collection |
| **Jaeger** | http://localhost:16686 | None | Distributed Tracing |
| **MongoDB** | mongodb://localhost:27017 | admin/netskope_admin_2024 | Database Queries |
| **Redis** | localhost:6379 | None | Cache Monitoring |
| **Kafka** | localhost:9092 | None | Message Streaming |

### **Start Monitoring Stack**
```bash
# Start all services
docker-compose -f docker-compose.local.yml up -d

# Verify services are healthy
docker-compose -f docker-compose.local.yml ps

# Check monitoring services specifically
curl -s http://localhost:9090/-/healthy  # Prometheus
curl -s http://localhost:3000/api/health # Grafana
curl -s http://localhost:16686/         # Jaeger
```

---

##  Grafana - Dashboards & Visualization

### **Access Grafana**
```bash
# Open Grafana dashboard
open http://localhost:3000

# Login credentials
Username: admin
Password: netskope_grafana_2024
```

### **Default Dashboards**

#### **1. Framework Overview Dashboard**
- **URL**: http://localhost:3000/d/framework-overview
- **Metrics**: Service health, request rates, error rates
- **Panels**: 
  - Service Status (Redis, Kafka, MongoDB, API)
  - Request Volume Over Time
  - Error Rate Trends
  - Response Time Distribution

#### **2. Service Performance Dashboard**
- **URL**: http://localhost:3000/d/service-performance
- **Metrics**: Individual service performance
- **Panels**:
  - Redis Operations/sec
  - Kafka Message Throughput
  - MongoDB Query Performance
  - API Response Times

#### **3. Test Execution Dashboard**
- **URL**: http://localhost:3000/d/test-execution
- **Metrics**: Test run statistics
- **Panels**:
  - Test Pass/Fail Rates
  - Test Execution Time
  - Coverage Metrics
  - Environment Health During Tests

### **Creating Custom Dashboards**

#### **Add New Dashboard**
```bash
# Navigate to Grafana
1. Go to http://localhost:3000
2. Click "+" → "Dashboard"
3. Click "Add new panel"
4. Configure data source: Prometheus
5. Enter PromQL query (see examples below)
```

#### **Useful PromQL Queries**
```promql
# Service health status
up{job="netskope-services"}

# Request rate per service
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Response time percentiles
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Redis operations
redis_commands_processed_total

# MongoDB operations
mongodb_op_counters_total

# Kafka message rate
kafka_server_brokertopicmetrics_messagesinpersec
```

### **Grafana Configuration**

#### **Data Sources Configuration**
```yaml
# Located in: config/grafana/provisioning/datasources/prometheus.yml
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
  
  - name: Jaeger
    type: jaeger
    url: http://jaeger:16686
```

#### **Dashboard Provisioning**
```yaml
# Located in: config/grafana/provisioning/dashboards/dashboard.yml
providers:
  - name: 'Day-1 Dashboards'
    folder: 'Day-1'
    type: file
    path: /var/lib/grafana/dashboards
```

### **Grafana Alerts**
```bash
# Set up alerts for service health
1. Go to Alerting → Alert Rules
2. Create new rule
3. Query: up{job="netskope-services"} == 0
4. Condition: IS BELOW 1
5. Evaluation: Every 1m for 2m
6. Add notification channels (email, Slack, etc.)
```

---

##  Prometheus - Metrics Collection

### **Access Prometheus**
```bash
# Open Prometheus UI
open http://localhost:9090

# Check targets status
open http://localhost:9090/targets

# Check service discovery
open http://localhost:9090/service-discovery
```

### **Key Metrics Available**

#### **Framework Metrics**
```promql
# Service availability
up{job="netskope-services"}

# HTTP request metrics
http_requests_total
http_request_duration_seconds
http_request_size_bytes

# Test execution metrics
test_runs_total
test_failures_total
test_duration_seconds
```

#### **Infrastructure Metrics**
```promql
# Redis metrics
redis_connected_clients
redis_used_memory_bytes
redis_commands_processed_total

# MongoDB metrics (via exporter)
mongodb_up
mongodb_connections
mongodb_op_counters_total

# Kafka metrics (via exporter)
kafka_server_brokertopicmetrics_messagesinpersec
kafka_server_brokertopicmetrics_bytesinpersec
```

### **Prometheus Configuration**
```yaml
# Located in: config/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'netskope-services'
    static_configs:
      - targets: ['localhost:8080']  # Framework API
  
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']
  
  - job_name: 'mongodb-exporter'
    static_configs:
      - targets: ['mongodb-exporter:9216']
  
  - job_name: 'kafka-exporter'
    static_configs:
      - targets: ['kafka-exporter:9308']
```

### **Custom Metrics Collection**
```python
# Add custom metrics to your tests
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
test_counter = Counter('netskope_tests_total', 'Total tests executed', ['test_type', 'status'])
test_duration = Histogram('netskope_test_duration_seconds', 'Test execution time')
active_connections = Gauge('netskope_active_connections', 'Active service connections')

# Use in tests
@test_duration.time()
def test_api_endpoint():
    # Your test code
    test_counter.labels(test_type='api', status='pass').inc()
```

### **Querying Prometheus**
```bash
# Using PromQL in Prometheus UI
1. Go to http://localhost:9090/graph
2. Enter PromQL query
3. Click "Execute"
4. View graph or table results

# Example queries:
# - Service uptime: up{job="netskope-services"}
# - Request rate: rate(http_requests_total[5m])
# - Error percentage: (rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])) * 100
```

---

##  Jaeger - Distributed Tracing

### **Access Jaeger**
```bash
# Open Jaeger UI
open http://localhost:16686

# No authentication required
```

### **Viewing Traces**

#### **Search for Traces**
```bash
1. Go to http://localhost:16686/search
2. Select service: "netskope-sdet-framework"
3. Select operation: "test_execution" or "api_call"
4. Set time range (last 1 hour)
5. Click "Find Traces"
```

#### **Trace Analysis**
- **Service Map**: Visualize service dependencies
- **Trace Timeline**: See request flow through services
- **Span Details**: Individual operation timing and metadata
- **Error Analysis**: Identify failed operations and bottlenecks

### **Trace Integration in Tests**
```python
# Add tracing to your test code
from jaeger_client import Config
import opentracing

# Configure Jaeger
config = Config(
    config={
        'sampler': {'type': 'const', 'param': 1},
        'logging': True,
        'local_agent': {'reporting_host': 'localhost', 'reporting_port': 6831}
    },
    service_name='netskope-sdet-tests'
)
tracer = config.initialize_tracer()

# Use in tests
def test_with_tracing():
    with tracer.start_span('test_api_call') as span:
        span.set_tag('test.type', 'integration')
        span.set_tag('service.name', 'netskope-api')
        
        # Your test code here
        response = api_client.get('/api/v2/events')
        
        span.set_tag('http.status_code', response.status_code)
        if response.status_code >= 400:
            span.set_tag('error', True)
```

### **Jaeger Features**

#### **Service Dependencies**
- **URL**: http://localhost:16686/dependencies
- **View**: Service interaction graph
- **Metrics**: Request volume, error rates between services

#### **Performance Analysis**
- **Latency Distribution**: P50, P75, P95, P99 percentiles
- **Operation Comparison**: Compare performance across operations
- **Error Rate Tracking**: Identify problematic services/operations

---

##  MongoDB - Database Monitoring

### **Access MongoDB**

#### **Command Line Access**
```bash
# Connect using mongosh
mongosh "mongodb://admin:netskope_admin_2024@localhost:27017/netskope_local?authSource=admin"

# Or connect to admin database first
mongosh mongodb://localhost:27017
use admin
db.auth("admin", "netskope_admin_2024")
use netskope_local
```

#### **GUI Tools**
```bash
# MongoDB Compass (Official GUI)
# Connection string: mongodb://admin:netskope_admin_2024@localhost:27017/netskope_local?authSource=admin

# Other options:
# - Studio 3T
# - Robo 3T
# - NoSQLBooster
```

### **Database Monitoring Queries**

#### **Collection Statistics**
```javascript
// Show all collections
show collections

// Collection stats
db.test_results.stats()
db.test_results.count()

// Index usage
db.test_results.getIndexes()
db.test_results.aggregate([{$indexStats: {}}])
```

#### **Performance Monitoring**
```javascript
// Current operations
db.currentOp()

// Server status
db.serverStatus()

// Database stats
db.stats()

// Profiling (enable first)
db.setProfilingLevel(2)  // Profile all operations
db.system.profile.find().limit(5).sort({ts: -1})
```

#### **Test Data Analysis**
```javascript
// Test results analysis
db.test_results.aggregate([
  {$group: {
    _id: "$status",
    count: {$sum: 1},
    avg_duration: {$avg: "$duration"}
  }}
])

// Error analysis
db.test_results.find({status: "failed"}).sort({timestamp: -1})

// Performance trends
db.test_results.aggregate([
  {$match: {timestamp: {$gte: new Date(Date.now() - 24*60*60*1000)}}},
  {$group: {
    _id: {$dateToString: {format: "%Y-%m-%d %H", date: "$timestamp"}},
    avg_duration: {$avg: "$duration"},
    test_count: {$sum: 1}
  }},
  {$sort: {_id: 1}}
])
```

### **MongoDB Exporter Metrics**
```bash
# Access MongoDB metrics via Prometheus
open http://localhost:9090/graph

# Key MongoDB metrics:
# - mongodb_up: Database availability
# - mongodb_connections: Active connections
# - mongodb_op_counters_total: Operation counters
# - mongodb_memory: Memory usage
# - mongodb_network_bytes_total: Network I/O
```

---

##  Redis - Cache Monitoring

### **Access Redis**

#### **Command Line Access**
```bash
# Connect using redis-cli (via Docker)
docker-compose -f docker-compose.local.yml exec redis redis-cli

# Or if redis-cli is installed locally
redis-cli -h localhost -p 6379
```

#### **Redis Monitoring Commands**
```bash
# Server info
INFO

# Memory usage
INFO memory

# Client connections
INFO clients

# Statistics
INFO stats

# Key space info
INFO keyspace

# Monitor commands in real-time
MONITOR

# Slow log
SLOWLOG GET 10
```

### **Redis Performance Analysis**
```bash
# Key analysis
SCAN 0 MATCH "test:*" COUNT 100
KEYS "test:*"  # Use carefully in production

# Memory analysis per key
MEMORY USAGE test_key

# TTL analysis
TTL test_key

# Database size
DBSIZE

# Configuration
CONFIG GET "*"
```

### **Redis Exporter Metrics**
```bash
# Access Redis metrics via Prometheus
open http://localhost:9090/graph

# Key Redis metrics:
# - redis_up: Redis availability
# - redis_connected_clients: Active connections
# - redis_used_memory_bytes: Memory usage
# - redis_commands_processed_total: Command statistics
# - redis_keyspace_hits_total: Cache hit rate
```

---

##  Test Reports and Analytics

### **HTML Test Reports**
```bash
# Generate comprehensive HTML report
pytest tests/ --html=reports/test_report.html --self-contained-html -v

# Open report
open reports/test_report.html

# Report includes:
# - Test summary (pass/fail/skip)
# - Detailed test results
# - Error messages and stack traces
# - Test duration analysis
# - Environment information
```

### **Coverage Reports**
```bash
# Generate coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term

# Open coverage report
open htmlcov/index.html

# Coverage includes:
# - Line coverage percentage
# - Branch coverage
# - Missing lines highlighted
# - File-by-file analysis
```

### **JUnit XML Reports**
```bash
# Generate JUnit XML for CI/CD
pytest tests/ --junitxml=reports/junit.xml

# XML includes:
# - Test case results
# - Execution times
# - Error details
# - System properties
```

### **Custom Analytics Dashboard**
```python
# Create custom analytics
import pandas as pd
import matplotlib.pyplot as plt
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://admin:netskope_admin_2024@localhost:27017/")
db = client.netskope_local

# Analyze test results
results = list(db.test_results.find())
df = pd.DataFrame(results)

# Create visualizations
plt.figure(figsize=(12, 8))

# Test pass rate over time
df['date'] = pd.to_datetime(df['timestamp'])
daily_stats = df.groupby(df['date'].dt.date).agg({
    'status': lambda x: (x == 'passed').sum() / len(x) * 100
}).reset_index()

plt.subplot(2, 2, 1)
plt.plot(daily_stats['date'], daily_stats['status'])
plt.title('Test Pass Rate Over Time')
plt.ylabel('Pass Rate (%)')

# Test duration distribution
plt.subplot(2, 2, 2)
plt.hist(df['duration'], bins=30)
plt.title('Test Duration Distribution')
plt.xlabel('Duration (seconds)')

# Error analysis
plt.subplot(2, 2, 3)
error_counts = df[df['status'] == 'failed']['error_type'].value_counts()
plt.pie(error_counts.values, labels=error_counts.index, autopct='%1.1f%%')
plt.title('Error Type Distribution')

# Service performance
plt.subplot(2, 2, 4)
service_perf = df.groupby('service')['duration'].mean()
plt.bar(service_perf.index, service_perf.values)
plt.title('Average Response Time by Service')
plt.ylabel('Duration (seconds)')

plt.tight_layout()
plt.savefig('reports/analytics_dashboard.png')
plt.show()
```

---

##  Configuration and Customization

### **Monitoring Configuration Files**
```bash
# Prometheus configuration
config/prometheus.yml

# Grafana provisioning
config/grafana/provisioning/datasources/prometheus.yml
config/grafana/provisioning/dashboards/dashboard.yml

# Docker Compose monitoring stack
docker-compose.local.yml  # Services: prometheus, grafana, jaeger, exporters
```

### **Custom Metrics Integration**
```python
# Add custom metrics to your framework
from prometheus_client import start_http_server, Counter, Histogram, Gauge

# Define metrics
REQUEST_COUNT = Counter('netskope_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('netskope_request_duration_seconds', 'Request latency')
ACTIVE_USERS = Gauge('netskope_active_users', 'Active users')

# Start metrics server
start_http_server(8000)

# Use in your code
@REQUEST_LATENCY.time()
def api_call(endpoint):
    REQUEST_COUNT.labels(method='GET', endpoint=endpoint).inc()
    # Your API call code
```

### **Alert Configuration**
```yaml
# Grafana alerts configuration
# Create alerts for:
# - Service downtime
# - High error rates
# - Performance degradation
# - Resource exhaustion

# Example alert rule
groups:
  - name: netskope_alerts
    rules:
      - alert: ServiceDown
        expr: up{job="netskope-services"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.instance }} is down"
```

---

##  Quick Start Monitoring

### **1. Start Everything**
```bash
# Start all services
docker-compose -f docker-compose.local.yml up -d

# Wait for services to be ready
sleep 30
```

### **2. Open All Dashboards**
```bash
# Open all monitoring interfaces
open http://localhost:3000    # Grafana
open http://localhost:9090    # Prometheus  
open http://localhost:16686   # Jaeger

# Login to Grafana: admin/netskope_grafana_2024
```

### **3. Run Tests and Generate Data**
```bash
# Run tests to generate monitoring data
export TESTING_MODE=local
pytest tests/ -v

# Check service health
python src/cli.py services health
```

### **4. View Reports**
```bash
# Generate and view test reports
pytest tests/ --html=reports/test_report.html --self-contained-html
open reports/test_report.html

# View coverage
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

---

##  Support and Troubleshooting

### **Common Issues**
- **Grafana login fails**: Check credentials (admin/netskope_grafana_2024)
- **No metrics in Prometheus**: Check if exporters are running
- **Empty Jaeger traces**: Ensure tracing is enabled in tests
- **MongoDB connection fails**: Verify credentials and authentication database

### **Debug Commands**
```bash
# Check service status
docker-compose -f docker-compose.local.yml ps

# Check logs
docker-compose -f docker-compose.local.yml logs grafana
docker-compose -f docker-compose.local.yml logs prometheus
docker-compose -f docker-compose.local.yml logs jaeger

# Test connectivity
curl http://localhost:3000/api/health  # Grafana
curl http://localhost:9090/-/healthy   # Prometheus
curl http://localhost:16686/           # Jaeger
```

### **Getting Help**
-  **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions
-  **[Architecture Guide](architecture.md)** - System design and components
-  **[Main Documentation](../README.md)** - Framework overview

---

** This guide provides complete coverage of all monitoring and reporting capabilities in the Day-1 Framework. Use it to gain full observability into your testing infrastructure and results!**