# Monitoring Quick Start Guide

## Prerequisites

```bash
# Install dependencies
pip install prometheus-client

# Start monitoring stack
docker-compose -f docker-compose.local.yml up -d

# Verify services are running
docker-compose -f docker-compose.local.yml ps
```

---

## Complete Monitoring Flow

### Step 1: Start the monitoring stack

```bash
docker-compose -f docker-compose.local.yml up -d

# Wait for services to be healthy
docker-compose -f docker-compose.local.yml ps
```

### Step 2: Install dependencies

```bash
pip install prometheus-client
```

### Step 3: Run tests (metrics auto-collected)

```bash
TESTING_MODE=local pytest tests/unit/ -v
```

### Step 4: View results in Grafana

```bash
# Framework Overview Dashboard
open http://localhost:3000/d/framework-overview

# Service Performance Dashboard
open http://localhost:3000/d/service-performance

# Test Execution Dashboard
open http://localhost:3000/d/test-execution
```

### Step 5: Query Prometheus directly

```bash
# Get all metrics
curl http://localhost:9091/metrics

# Open Prometheus UI
open http://localhost:9090

# Query examples in Prometheus UI:
# - pytest_tests_total
# - pytest_success_rate
# - pytest_session_tests
```

### Step 6: Review test results in MongoDB

```bash
# Connect to MongoDB
mongosh "mongodb://admin:admin_2024@localhost:27017/day1_local"

# Query recent test results
db.test_results.find().sort({start_time: -1}).limit(10)

# Query test sessions
db.test_sessions.find().sort({timestamp: -1}).limit(5)

# Exit
exit()
```

---

## Service URLs

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| **Grafana** | http://localhost:3000 | admin/integration-grafana-2024 | Dashboards |
| **Prometheus** | http://localhost:9090 | - | Metrics |
| **Prometheus Metrics** | http://localhost:9091 | - | App metrics |
| **MongoDB** | localhost:27017 | admin/admin_2024 | Test data |
| **Redis** | localhost:6379 | - | Cache |
| **Kafka** | localhost:9092 | - | Messages |
| **Jaeger** | http://localhost:16686 | - | Tracing |

---

## Dashboard Access

### Grafana Dashboards (Auto-Provisioned)

| Dashboard | URL |
|-----------|-----|
| Framework Overview | http://localhost:3000/d/framework-overview |
| Service Performance | http://localhost:3000/d/service-performance |
| Test Execution | http://localhost:3000/d/test-execution |

### Login

```bash
# Username: admin
# Password: grafana_2024
```

---

## Prometheus Metrics

### Available Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `pytest_tests_total` | Counter | Total tests by status, test_file, test_name |
| `pytest_test_duration_seconds` | Histogram | Test duration in seconds |
| `pytest_session_tests` | Gauge | Current session test counts |
| `pytest_success_rate` | Gauge | Success rate percentage |
| `up` | Gauge | Service health status |

### Query Examples

```promql
# Test pass/fail counts by status
sum(pytest_tests_total{environment="local"}) by (status)

# Success rate percentage
sum(pytest_tests_total{status="passed"}) / sum(pytest_tests_total) * 100

# Average test duration
rate(pytest_test_duration_seconds_sum[5m]) / rate(pytest_test_duration_seconds_count[5m])

# Session test counts by status
pytest_session_tests{environment="local", status="passed"}

# Service health
up{job="redis"}
up{job="kafka"}
up{job="mongodb"}
```

---

## Health Checks

```bash
# Grafana health
curl -s http://localhost:3000/api/health

# Prometheus health
curl -s http://localhost:9090/-/healthy

# Prometheus metrics endpoint health
curl -s http://localhost:9091/health

# MongoDB health
curl -s http://localhost:27017/

# Redis health
redis-cli ping

# Kafka health
kafka-broker-api-versions --bootstrap-server localhost:9092
```

---

## Troubleshooting

### No metrics appearing in Grafana

```bash
# 1. Check prometheus_client is installed
pip list | grep prometheus

# 2. Check metrics endpoint is responding
curl http://localhost:9091/metrics

# 3. Check Prometheus is scraping the metrics
# In Prometheus UI: http://localhost:9090/targets

# 4. Check Grafana datasource is configured
# Grafana → Configuration → Data Sources → Prometheus
```

### Grafana dashboards not found

```bash
# 1. Restart Grafana to load dashboards
docker-compose restart grafana

# 2. Check dashboard files exist
ls -la config/grafana/dashboards/

# 3. Import dashboards manually
# Grafana → Dashboards → Import → Upload JSON file
```

### Metrics endpoint not responding

```bash
# 1. Check port is not in use
lsof -i :9091

# 2. Check prometheus_client is installed
pip install prometheus-client

# 3. Run tests to initialize metrics
TESTING_MODE=local pytest tests/unit/ -v
```

---

## Environment-Specific Commands

### Local Environment

```bash
TESTING_MODE=local pytest tests/ -v
```

### Integration Environment

```bash
# Requires Kubernetes
TESTING_MODE=integration kubectl port-forward svc/grafana 3000:3000 -n netskope-integration
TESTING_MODE=integration kubectl port-forward svc/prometheus 9090:9090 -n netskope-integration
```

### Staging Environment

```bash
TESTING_MODE=staging kubectl port-forward svc/grafana 3000:3000 -n day1-staging
```

---

## Quick Reference Card

```bash
# One-liner to start everything and run tests
docker-compose -f docker-compose.local.yml up -d && \
pip install prometheus-client && \
TESTING_MODE=local pytest tests/unit/ -v && \
open http://localhost:3000/d/framework-overview
```

---

## For Complete Documentation

See the full tutorial: [TUTORIAL.md](./TUTORIAL.md)