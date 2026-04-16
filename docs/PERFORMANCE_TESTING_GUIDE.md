# Performance Testing Guide - Day-1 Framework

##  Overview

The Day-1 Framework includes comprehensive performance testing capabilities using both **JMeter** and **Locust** to validate system performance, scalability, and reliability under various load conditions.

##  Performance Testing Stack

### **Testing Tools**
- **JMeter 5.5+**: GUI-based load testing with comprehensive reporting
- **Locust 2.0+**: Python-based distributed load testing
- **Python Load Tests**: Custom performance validation scripts

### **Monitoring Integration**
- **Prometheus**: Real-time metrics collection during load tests
- **Grafana**: Performance dashboards and visualization
- **Jaeger**: Distributed tracing for performance bottlenecks
- **MongoDB**: Test result storage and analytics

##  Installation & Setup

### **Prerequisites**
```bash
# Install JMeter (macOS)
brew install jmeter

# Install Locust
pip install locust

# Verify installations
jmeter --version
locust --version

# Install additional dependencies
pip install faker requests matplotlib seaborn
```

### **Framework Setup**
```bash
# Ensure framework is installed
pip install -e .

# Start local environment for testing
docker-compose -f docker-compose.local.yml up -d

# Verify services are running
python src/cli.py services health
```

##  Performance Testing Scenarios

### **Test Categories**

#### **1. Smoke Tests** (5 users, 1 minute)
- **Purpose**: Quick validation that system handles basic load
- **Scope**: All major API endpoints
- **Success Criteria**: 0% error rate, <500ms response time

#### **2. Load Tests** (50-100 users, 5-10 minutes)
- **Purpose**: Normal business hours simulation
- **Scope**: Realistic user behavior patterns
- **Success Criteria**: <2% error rate, <1000ms response time

#### **3. Stress Tests** (200-500 users, 15-30 minutes)
- **Purpose**: Find system breaking points
- **Scope**: High concurrent user load
- **Success Criteria**: Graceful degradation, no crashes

#### **4. Endurance Tests** (100 users, 1+ hours)
- **Purpose**: Long-running stability validation
- **Scope**: Memory leaks, resource exhaustion
- **Success Criteria**: Stable performance over time

#### **5. Spike Tests** (Variable load, 10-20 minutes)
- **Purpose**: Sudden load increase handling
- **Scope**: Auto-scaling and recovery
- **Success Criteria**: Quick recovery to baseline

##  JMeter Performance Testing

### **JMeter Test Plan Structure**
```
netskope_api_load_test.jmx
 Test Plan Configuration
    User Variables (BASE_URL, API_KEY, USERS, DURATION)
    Thread Group (Load simulation)
    HTTP Request Defaults
 Security Service Tests
    SWG - URL Check (40% of requests)
    DLP - File Scan (30% of requests)
    ZTNA - Access Check (20% of requests)
    Firewall - Rule Check (10% of requests)
 Assertions & Validations
    Response Code Assertions (200 OK)
    Response Time Assertions (<1000ms)
    Content Validation
 Reporting & Listeners
     Summary Report
     Results Tree (disabled in load tests)
     CSV Results Export
```

Additional plans:
- `dlp_scan_load_test.jmx` - DLP-focused plan that targets `/api/v2/dlp/scan-file` with configurable `base_url`, `users`, `ramp_time` and `duration`.


### **Running JMeter Tests**

#### **GUI Mode (Development)**
```bash
# Open JMeter GUI
jmeter

# Load test plan
# File → Open → tests/performance/jmeter/netskope_api_load_test.jmx

# Configure test parameters:
# - BASE_URL: http://localhost:8080
# - USERS: 50
# - RAMP_TIME: 60 (seconds)
# - DURATION: 300 (seconds)

# Run test and monitor results in real-time
```

#### **Command Line Mode (CI/CD)**
```bash
# Basic load test
jmeter -n -t tests/performance/jmeter/netskope_api_load_test.jmx \
       -l reports/jmeter_results.jtl \
       -e -o reports/jmeter_html_report

# Custom parameters
jmeter -n -t tests/performance/jmeter/netskope_api_load_test.jmx \
       -Jbase_url=http://localhost:8080 \
       -Jusers=100 \
       -Jramp_time=120 \
       -Jduration=600 \
       -l reports/jmeter_results.jtl \
       -e -o reports/jmeter_html_report

# Stress test configuration
jmeter -n -t tests/performance/jmeter/netskope_api_load_test.jmx \
       -Jusers=500 \
       -Jramp_time=300 \
       -Jduration=1800 \
       -l reports/jmeter_stress_results.jtl \
       -e -o reports/jmeter_stress_report
```

#### **JMeter Test Scenarios**
```bash
# Smoke test (quick validation)
jmeter -n -t tests/performance/jmeter/netskope_api_load_test.jmx \
       -Jusers=5 -Jramp_time=30 -Jduration=60 \
       -l reports/jmeter_smoke.jtl

# Normal load test
jmeter -n -t tests/performance/jmeter/netskope_api_load_test.jmx \
       -Jusers=50 -Jramp_time=60 -Jduration=300 \
       -l reports/jmeter_load.jtl

# Peak load test
jmeter -n -t tests/performance/jmeter/netskope_api_load_test.jmx \
       -Jusers=200 -Jramp_time=120 -Jduration=600 \
       -l reports/jmeter_peak.jtl
```

### DLP-specific JMeter example
```
# Run the DLP scan load test
jmeter -n -t tests/performance/jmeter/dlp_scan_load_test.jmx \
       -Jbase_url=http://localhost:8080 \
       -Jusers=50 -Jramp_time=60 -Jduration=300 \
       -l reports/dlp_jmeter_results.jtl \
       -e -o reports/dlp_jmeter_html_report
```

### **JMeter Results Analysis**
```bash
# Generate HTML report from results
jmeter -g reports/jmeter_results.jtl -o reports/jmeter_html_report

# View detailed HTML report
open reports/jmeter_html_report/index.html

# Key metrics to analyze:
# - Response Time Percentiles (90th, 95th, 99th)
# - Throughput (requests/second)
# - Error Rate (should be <2%)
# - Resource Utilization
```

##  Locust Performance Testing

### **Locust Test Structure**
```python
# tests/performance/locust/netskope_load_test.py
 NetskopeSecurityUser (Main user simulation)
    check_url_swg() - 40% of requests
    scan_file_dlp() - 30% of requests  
    check_access_ztna() - 20% of requests
    check_firewall_rules() - 10% of requests
 AdminUser (Administrative operations)
    get_security_events()
    get_security_reports()
    get_system_health()
 LoadTestScenarios (Predefined configurations)
     SMOKE_TEST (5 users, 60s)
     NORMAL_LOAD (50 users, 300s)
     PEAK_LOAD (200 users, 600s)
     STRESS_TEST (500 users, 900s)
     ENDURANCE_TEST (100 users, 3600s)
```

### **Running Locust Tests**

#### **Web UI Mode (Interactive)**
```bash
# Start Locust web interface
locust -f tests/performance/locust/netskope_load_test.py \
       --host=http://localhost:8080 \
       --web-host=0.0.0.0 \
       --web-port=8089

# Open web interface
open http://localhost:8089

# Configure test parameters in web UI:
# - Number of users: 50
# - Spawn rate: 5 users/second
# - Host: http://localhost:8080
# - Run time: 300 seconds
```

#### **Headless Mode (CI/CD)**
```bash
# Basic load test
locust -f tests/performance/locust/netskope_load_test.py \
       --host=http://localhost:8080 \
       --users=50 \
       --spawn-rate=5 \
       --run-time=300s \
       --headless \
       --csv=reports/locust_results

# Stress test
locust -f tests/performance/locust/netskope_load_test.py \
       --host=http://localhost:8080 \
       --users=500 \
       --spawn-rate=20 \
       --run-time=900s \
       --headless \
       --csv=reports/locust_stress_results

# Endurance test
locust -f tests/performance/locust/netskope_load_test.py \
       --host=http://localhost:8080 \
       --users=100 \
       --spawn-rate=5 \
       --run-time=3600s \
       --headless \
       --csv=reports/locust_endurance_results
```

#### **Predefined Scenarios**
```bash
# Use built-in scenario configurations
python tests/performance/locust/netskope_load_test.py smoke
python tests/performance/locust/netskope_load_test.py normal
python tests/performance/locust/netskope_load_test.py peak
python tests/performance/locust/netskope_load_test.py stress
python tests/performance/locust/netskope_load_test.py endurance
```

#### **Distributed Load Testing**
```bash
# Master node
locust -f tests/performance/locust/netskope_load_test.py \
       --host=http://localhost:8080 \
       --master \
       --web-host=0.0.0.0

# Worker nodes (run on multiple machines)
locust -f tests/performance/locust/netskope_load_test.py \
       --worker \
       --master-host=<master-ip>
```

### **Locust Results Analysis**
```bash
# Results are automatically saved as CSV files:
# - reports/locust_results_stats.csv (Request statistics)
# - reports/locust_results_stats_history.csv (Time series data)
# - reports/locust_results_failures.csv (Failure details)

# Generate custom reports
python scripts/analyze_locust_results.py reports/locust_results_stats.csv
```

##  Python Load Testing

### **Custom Performance Tests**
```bash
# Run existing Python load test
pytest tests/performance/test_load.py -v

# Run with custom parameters
NUM_USERS=200 pytest tests/performance/test_load.py -v

# Run with performance profiling
pytest tests/performance/test_load.py -v --profile
```

### **Performance Test Structure**
```python
# tests/performance/test_load.py
def test_load_simulation():
    """Simulates concurrent users across all security services"""
    # ThreadPoolExecutor for concurrent execution
    # Realistic user behavior simulation
    # Service interaction validation
    # Performance metrics collection
```

##  Performance Monitoring During Tests

### **Real-Time Monitoring**
```bash
# Start monitoring stack
docker-compose -f docker-compose.local.yml up -d

# Access monitoring dashboards during tests
open http://localhost:3000    # Grafana (admin/grafana_2024)
open http://localhost:9090    # Prometheus
open http://localhost:16686   # Jaeger
```

### **Key Performance Metrics**

#### **Response Time Metrics**
- **Average Response Time**: <500ms (normal load)
- **95th Percentile**: <1000ms (acceptable)
- **99th Percentile**: <2000ms (maximum)
- **Maximum Response Time**: <5000ms (timeout threshold)

#### **Throughput Metrics**
- **Requests per Second (RPS)**: Target based on expected load
- **Concurrent Users**: Maximum sustainable concurrent connections
- **Data Transfer Rate**: MB/s for file operations

#### **Error Rate Metrics**
- **HTTP Error Rate**: <2% (acceptable)
- **Timeout Rate**: <1% (network issues)
- **Application Error Rate**: <0.5% (critical)

#### **Resource Utilization**
- **CPU Usage**: <80% sustained
- **Memory Usage**: <85% with no leaks
- **Network I/O**: Monitor bandwidth utilization
- **Disk I/O**: Database and logging performance

### **Grafana Performance Dashboards**
```bash
# Pre-configured dashboards available:
# - API Performance Overview
# - Service Response Times
# - Error Rate Monitoring
# - Resource Utilization
# - Load Test Progress

# Import custom dashboards
# Grafana → Import → Upload JSON dashboard files
```

##  Performance Test Execution Workflows

### **Development Workflow**
```bash
# 1. Start local environment
docker-compose -f docker-compose.local.yml up -d

# 2. Run smoke test (quick validation)
python tests/performance/locust/netskope_load_test.py smoke

# 3. Run normal load test
locust -f tests/performance/locust/netskope_load_test.py \
       --host=http://localhost:8080 --users=50 --spawn-rate=5 \
       --run-time=300s --headless --csv=reports/dev_load_test

# 4. Analyze results
python scripts/analyze_performance_results.py reports/dev_load_test_stats.csv
```

### **CI/CD Integration Workflow**
```bash
# Automated performance testing in CI/CD pipeline
# .github/workflows/performance-tests.yml

name: Performance Tests
on: [push, pull_request]

jobs:
  performance-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install locust jmeter
          
      - name: Start services
        run: docker-compose -f docker-compose.local.yml up -d
        
      - name: Wait for services
        run: sleep 30
        
      - name: Run smoke test
        run: |
          locust -f tests/performance/locust/netskope_load_test.py \
                 --host=http://localhost:8080 \
                 --users=10 --spawn-rate=2 --run-time=60s \
                 --headless --csv=reports/ci_smoke_test
                 
      - name: Run load test
        run: |
          locust -f tests/performance/locust/netskope_load_test.py \
                 --host=http://localhost:8080 \
                 --users=50 --spawn-rate=5 --run-time=180s \
                 --headless --csv=reports/ci_load_test
                 
      - name: Analyze results
        run: python scripts/analyze_performance_results.py reports/ci_load_test_stats.csv
        
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-test-results
          path: reports/
```

### **Staging Environment Workflow**
```bash
# 1. Deploy to staging environment
kubectl apply -f k8s/staging/

# 2. Wait for deployment
kubectl rollout status deployment/target-api -n day1-staging

# 3. Run comprehensive load tests
locust -f tests/performance/locust/netskope_load_test.py \
       --host=https://staging-api.day1.internal \
       --users=200 --spawn-rate=10 --run-time=1800s \
       --headless --csv=reports/staging_load_test

# 4. Run stress tests
python tests/performance/locust/netskope_load_test.py stress

# 5. Generate performance report
python scripts/generate_performance_report.py \
       --results reports/staging_load_test_stats.csv \
       --output reports/staging_performance_report.html
```

##  Performance Test Scripts

### **Automated Test Execution**
```bash
# Create performance test runner script
cat > scripts/run_performance_tests.sh << 'EOF'
#!/bin/bash

# Performance Test Runner for Day-1 Framework

set -e

# Configuration
HOST=${HOST:-"http://localhost:8080"}
RESULTS_DIR=${RESULTS_DIR:-"reports/performance"}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create results directory
mkdir -p $RESULTS_DIR

echo " Starting Performance Test Suite - $TIMESTAMP"

# 1. Smoke Test (Quick validation)
echo " Running Smoke Test..."
locust -f tests/performance/locust/netskope_load_test.py \
       --host=$HOST --users=5 --spawn-rate=1 --run-time=60s \
       --headless --csv=$RESULTS_DIR/smoke_test_$TIMESTAMP

# 2. Load Test (Normal usage)
echo " Running Load Test..."
locust -f tests/performance/locust/netskope_load_test.py \
       --host=$HOST --users=50 --spawn-rate=5 --run-time=300s \
       --headless --csv=$RESULTS_DIR/load_test_$TIMESTAMP

# 3. Stress Test (High load)
echo " Running Stress Test..."
locust -f tests/performance/locust/netskope_load_test.py \
       --host=$HOST --users=200 --spawn-rate=10 --run-time=600s \
       --headless --csv=$RESULTS_DIR/stress_test_$TIMESTAMP

# 4. JMeter Test (Alternative tool validation)
echo " Running JMeter Test..."
jmeter -n -t tests/performance/jmeter/netskope_api_load_test.jmx \
       -Jbase_url=$HOST -Jusers=50 -Jramp_time=60 -Jduration=300 \
       -l $RESULTS_DIR/jmeter_test_$TIMESTAMP.jtl \
       -e -o $RESULTS_DIR/jmeter_report_$TIMESTAMP

# 5. Generate Summary Report
echo " Generating Performance Report..."
python scripts/generate_performance_summary.py \
       --results-dir $RESULTS_DIR \
       --timestamp $TIMESTAMP \
       --output $RESULTS_DIR/performance_summary_$TIMESTAMP.html

echo " Performance Test Suite Completed!"
echo " Results available in: $RESULTS_DIR"
echo " Open report: $RESULTS_DIR/performance_summary_$TIMESTAMP.html"
EOF

chmod +x scripts/run_performance_tests.sh
```

### **Performance Analysis Script**
```bash
# Create performance analysis script
cat > scripts/analyze_performance_results.py << 'EOF'
#!/usr/bin/env python3
"""
Performance Results Analyzer for Day-1 Framework

Analyzes Locust and JMeter test results and generates comprehensive reports.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import json
from pathlib import Path

def analyze_locust_results(stats_file):
    """Analyze Locust CSV results"""
    df = pd.read_csv(stats_file)
    
    analysis = {
        "total_requests": df["Request Count"].sum(),
        "total_failures": df["Failure Count"].sum(),
        "failure_rate": (df["Failure Count"].sum() / df["Request Count"].sum()) * 100,
        "avg_response_time": df["Average Response Time"].mean(),
        "max_response_time": df["Max Response Time"].max(),
        "requests_per_second": df["Requests/s"].sum(),
        "endpoints": df["Name"].tolist()
    }
    
    return analysis

def generate_performance_charts(stats_file, output_dir):
    """Generate performance visualization charts"""
    df = pd.read_csv(stats_file)
    
    # Response time distribution
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 2, 1)
    plt.bar(df["Name"], df["Average Response Time"])
    plt.title("Average Response Time by Endpoint")
    plt.xticks(rotation=45)
    plt.ylabel("Response Time (ms)")
    
    plt.subplot(2, 2, 2)
    plt.bar(df["Name"], df["Requests/s"])
    plt.title("Requests per Second by Endpoint")
    plt.xticks(rotation=45)
    plt.ylabel("Requests/s")
    
    plt.subplot(2, 2, 3)
    failure_rates = (df["Failure Count"] / df["Request Count"]) * 100
    plt.bar(df["Name"], failure_rates)
    plt.title("Failure Rate by Endpoint")
    plt.xticks(rotation=45)
    plt.ylabel("Failure Rate (%)")
    
    plt.subplot(2, 2, 4)
    plt.bar(df["Name"], df["Request Count"])
    plt.title("Total Requests by Endpoint")
    plt.xticks(rotation=45)
    plt.ylabel("Request Count")
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/performance_charts.png", dpi=300, bbox_inches='tight')
    plt.close()

def main():
    parser = argparse.ArgumentParser(description="Analyze performance test results")
    parser.add_argument("stats_file", help="Path to Locust stats CSV file")
    parser.add_argument("--output-dir", default="reports", help="Output directory")
    
    args = parser.parse_args()
    
    # Analyze results
    analysis = analyze_locust_results(args.stats_file)
    
    # Generate charts
    generate_performance_charts(args.stats_file, args.output_dir)
    
    # Print summary
    print(" Performance Test Analysis Summary")
    print("=" * 50)
    print(f"Total Requests: {analysis['total_requests']:,}")
    print(f"Total Failures: {analysis['total_failures']:,}")
    print(f"Failure Rate: {analysis['failure_rate']:.2f}%")
    print(f"Average Response Time: {analysis['avg_response_time']:.2f}ms")
    print(f"Max Response Time: {analysis['max_response_time']:.2f}ms")
    print(f"Requests per Second: {analysis['requests_per_second']:.2f}")
    print(f"Endpoints Tested: {len(analysis['endpoints'])}")
    
    # Performance assessment
    if analysis['failure_rate'] < 2.0:
        print(" PASS: Failure rate within acceptable limits")
    else:
        print(" FAIL: High failure rate detected")
        
    if analysis['avg_response_time'] < 1000:
        print(" PASS: Response times within acceptable limits")
    else:
        print("  WARNING: High response times detected")
    
    # Save detailed analysis
    with open(f"{args.output_dir}/performance_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\n Detailed analysis saved to: {args.output_dir}/performance_analysis.json")
    print(f" Charts saved to: {args.output_dir}/performance_charts.png")

if __name__ == "__main__":
    main()
EOF

chmod +x scripts/analyze_performance_results.py
```

##  Performance Benchmarks & SLAs

### **Service Level Agreements (SLAs)**

#### **Response Time SLAs**
| Service | 95th Percentile | 99th Percentile | Maximum |
|---------|----------------|----------------|---------|
| **SWG URL Check** | <800ms | <1500ms | <3000ms |
| **DLP File Scan** | <1200ms | <2000ms | <5000ms |
| **ZTNA Access Check** | <600ms | <1000ms | <2000ms |
| **Firewall Rules** | <400ms | <800ms | <1500ms |
| **Admin Operations** | <2000ms | <5000ms | <10000ms |

#### **Throughput SLAs**
| Service | Target RPS | Peak RPS | Concurrent Users |
|---------|------------|----------|------------------|
| **SWG URL Check** | 100 RPS | 200 RPS | 500 users |
| **DLP File Scan** | 50 RPS | 100 RPS | 200 users |
| **ZTNA Access Check** | 80 RPS | 150 RPS | 300 users |
| **Firewall Rules** | 120 RPS | 250 RPS | 600 users |

#### **Reliability SLAs**
- **Availability**: 99.9% uptime
- **Error Rate**: <2% under normal load
- **Recovery Time**: <30 seconds after load reduction

### **Performance Baselines**
```bash
# Establish performance baselines
python scripts/establish_performance_baseline.py \
       --environment local \
       --duration 300 \
       --users 50 \
       --output reports/performance_baseline.json

# Compare against baseline
python scripts/compare_performance.py \
       --baseline reports/performance_baseline.json \
       --current reports/locust_results_stats.csv \
       --threshold 10  # 10% degradation threshold
```

##  Troubleshooting Performance Issues

### **Common Performance Problems**

#### **High Response Times**
```bash
# Check system resources
docker stats

# Monitor database performance
mongosh "mongodb://admin:netskope_admin_2024@localhost:27017/netskope_local?authSource=admin"
db.runCommand({serverStatus: 1})

# Check Redis performance
docker exec -it redis redis-cli info stats

# Monitor Kafka performance
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --list
```

#### **High Error Rates**
```bash
# Check application logs
docker-compose -f docker-compose.local.yml logs netskope-api-mock

# Monitor service health
python src/cli.py services health

# Check network connectivity
curl -v http://localhost:8080/api/v2/health
```

#### **Memory Leaks**
```bash
# Monitor memory usage over time
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Check for memory leaks in Python
pip install memory-profiler
python -m memory_profiler tests/performance/test_load.py
```

### **Performance Optimization Tips**

#### **Application Level**
- Implement response caching
- Optimize database queries
- Use connection pooling
- Enable compression

#### **Infrastructure Level**
- Scale horizontally with load balancers
- Use CDN for static content
- Optimize container resources
- Implement auto-scaling

#### **Test Level**
- Use realistic test data
- Implement proper think times
- Monitor resource utilization
- Validate test environment

##  Additional Resources

### **Documentation**
- **[JMeter User Manual](https://jmeter.apache.org/usermanual/index.html)**: Official JMeter documentation
- **[Locust Documentation](https://docs.locust.io/)**: Comprehensive Locust guide
- **[Performance Testing Best Practices](https://martinfowler.com/articles/practical-test-pyramid.html)**: Industry best practices

### **Framework Integration**
- **[Monitoring Guide](MONITORING_AND_REPORTS_GUIDE.md)**: Complete monitoring setup
- **[CI/CD Integration](CI_CD_INTEGRATION_GUIDE.md)**: Automated performance testing
- **[Architecture Guide](architecture.md)**: System architecture and scaling

### **Performance Testing Checklist**
```bash
# Pre-test checklist
 Environment is stable and healthy
 Baseline performance metrics established
 Test data is prepared and realistic
 Monitoring systems are active
 Test duration and load levels defined

# During test checklist
 Monitor system resources (CPU, memory, network)
 Watch for error rates and response times
 Check application logs for issues
 Validate test is running as expected
 Document any anomalies or issues

# Post-test checklist
 Analyze test results and metrics
 Compare against baselines and SLAs
 Generate performance report
 Document findings and recommendations
 Clean up test data and resources
```

---

##  Performance Testing Success

The Day-1 Framework now includes **comprehensive performance testing capabilities** with:

 **JMeter Integration**: GUI and command-line load testing  
 **Locust Implementation**: Python-based distributed testing  
 **Monitoring Integration**: Real-time performance monitoring  
 **CI/CD Integration**: Automated performance validation  
 **Comprehensive Reporting**: Detailed analysis and visualization  
 **Multiple Test Scenarios**: Smoke, load, stress, and endurance testing  

**Start performance testing immediately with zero configuration!** 