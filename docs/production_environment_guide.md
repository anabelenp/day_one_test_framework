# Production Environment (E5) Monitoring Guide

## Overview

The Production Environment (E5) provides **read-only monitoring and health checking** capabilities for production Netskope SDET Framework deployments. This environment is designed with strict safety measures to ensure no modifications can be made to production systems while providing comprehensive observability and incident response capabilities.

##  **CRITICAL SAFETY NOTICE**

**This environment is READ-ONLY by design. No write operations, deployments, or modifications are permitted in production.**

### Safety Features
- **Read-Only Mode**: All operations are strictly read-only
- **No Deployments**: Cannot deploy or modify production infrastructure
- **No Data Changes**: Cannot modify production data or configurations
- **External Secrets**: Uses external secret management (Vault, AWS Secrets Manager)
- **Audit Logging**: All access is logged and monitored
- **MFA Required**: Multi-factor authentication enforced
- **Time-Limited Access**: Sessions expire automatically

## Architecture

```

                Production Environment (E5)                       
                   READ-ONLY MONITORING ONLY                      

           
    Redis Prod        Kafka Prod       MongoDB Prod        
    (Read-Only)       (Read-Only)      (Read-Only)         
    Health Checks     Health Checks    Health Checks       
    Metrics Only      Metrics Only     Metrics Only        
           
                                                                  
           
   Netskope API      Prometheus          Grafana           
   (Read-Only)       (Read-Only)       (Read-Only)         
   Health & Stats    Metrics Query     Dashboards          
   No Mutations      No Config         View Only           
           
                                                                  
           
   Health Reports    Incident Mgmt     Alert Manager       
   Automated         Integration       (Read-Only)         
   Continuous        JIRA/PagerDuty    View Alerts         
           

```

## Prerequisites

### 1. Security Requirements

#### External Secret Management
Production credentials must be managed externally:

```bash
# Vault (recommended)
export VAULT_PROD_URL="https://vault.company.com"
export VAULT_PROD_TOKEN="hvs.production-token"

# AWS Secrets Manager
export AWS_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."

# Environment Variables (for testing only)
export REDIS_PROD_PASSWORD="..."
export KAFKA_PROD_USERNAME="..."
export KAFKA_PROD_PASSWORD="..."
export MONGODB_PROD_USERNAME="..."
export MONGODB_PROD_PASSWORD="..."
export NETSKOPE_PROD_API_KEY="..."
```

#### Network Access
- **VPN Connection**: Required for production network access
- **Firewall Rules**: Whitelist monitoring IPs
- **TLS Certificates**: Valid certificates for all services
- **DNS Resolution**: Access to production service FQDNs

#### Authentication & Authorization
- **MFA Enabled**: Multi-factor authentication required
- **RBAC**: Role-based access control configured
- **Audit Logging**: All access logged and monitored
- **Session Limits**: Time-limited access sessions

### 2. Required Tools

```bash
# Python 3.9+ with production monitoring dependencies
pip install -r requirements.txt

# Additional production monitoring tools
pip install redis kafka-python pymongo requests pyyaml

# Optional: Vault CLI for secret management
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install vault
```

### 3. Configuration Validation

```bash
# Validate production configuration
python -c "
import yaml
with open('config/production.yaml') as f:
    config = yaml.safe_load(f)
assert config['READ_ONLY_MODE'] is True
assert config['PRODUCTION_WRITE_OPERATIONS'] is False
print(' Production config is safe')
"
```

## Usage

### Quick Start

```bash
# Run production health check
python scripts/deploy_production.py --action health-check

# Or use CLI (when implemented)
netskope-sdet production health-check

# Generate health report
python scripts/deploy_production.py --action report --output reports/prod_health.json

# Start continuous monitoring
python scripts/deploy_production.py --action monitor --interval 300 --duration 3600
```

### Health Monitoring

#### Single Health Check

```bash
# Comprehensive health check
python scripts/deploy_production.py --action health-check

# Expected output:
#  Checking production monitoring prerequisites...
#  Production monitoring prerequisites met
#  Running comprehensive production health check...
#   This is read-only monitoring - no changes will be made
#   Checking redis...
#    redis: healthy
#   Checking kafka...
#    kafka: healthy
#   Checking mongodb...
#    mongodb: healthy
#   Checking api...
#    api: healthy
#    prometheus: healthy
#    grafana: healthy
# 
#  Overall Health: healthy
#  Health Score: 100.0%
#  Services: 6/6 healthy
```

#### Continuous Monitoring

```bash
# Monitor for 1 hour, check every 5 minutes
python scripts/deploy_production.py --action monitor --interval 300 --duration 3600

# Monitor indefinitely (until Ctrl+C)
python scripts/deploy_production.py --action monitor --interval 300 --duration 86400
```

### Metrics Collection

```bash
# Collect current metrics
python scripts/deploy_production.py --action metrics

# Example output:
{
  "timestamp": "2024-12-18T10:30:00Z",
  "environment": "production",
  "prometheus": {
    "cpu_usage": 65.2,
    "memory_usage": 72.8,
    "disk_usage": 45.1,
    "api_response_time": 0.245,
    "api_error_rate": 0.002,
    "service_uptime": 0.999
  },
  "custom": {
    "health_check_timestamp": "2024-12-18T10:30:00Z",
    "monitoring_mode": "read_only",
    "framework_version": "1.0.0"
  }
}
```

### Health Reports

```bash
# Generate comprehensive health report
python scripts/deploy_production.py --action report --output reports/production_health_$(date +%Y%m%d_%H%M%S).json

# View report
cat reports/production_health_20241218_103000.json | jq .
```

#### Sample Health Report

```json
{
  "report_metadata": {
    "generated_at": "2024-12-18T10:30:00Z",
    "environment": "production",
    "framework": "Netskope SDET Framework",
    "version": "1.0.0",
    "mode": "read_only_monitoring"
  },
  "health_check": {
    "environment": "production",
    "timestamp": "2024-12-18T10:30:00Z",
    "read_only_mode": true,
    "services": {
      "redis": {
        "status": "healthy",
        "ping": true,
        "version": "7.0.0",
        "uptime": 2592000,
        "connected_clients": 45,
        "used_memory": "2.1GB",
        "role": "master",
        "connected_slaves": 2
      },
      "kafka": {
        "status": "healthy",
        "cluster_id": "prod-kafka-cluster",
        "brokers": 5,
        "topics_count": 127,
        "controller": 1
      },
      "mongodb": {
        "status": "healthy",
        "version": "6.0.0",
        "uptime": 2592000,
        "replica_set": {
          "set_name": "prod-rs0",
          "members": 5,
          "primary": "mongo-prod-1:27017"
        },
        "database_size": 52428800000,
        "collections": 45,
        "indexes": 127
      },
      "api": {
        "status": "healthy",
        "response_time": 0.245,
        "api_version": "2.1.0"
      }
    },
    "monitoring": {
      "prometheus": {
        "status": "healthy",
        "status_code": 200,
        "response_time": 0.123
      },
      "grafana": {
        "status": "healthy",
        "status_code": 200,
        "response_time": 0.089
      }
    },
    "overall_health": {
      "status": "healthy",
      "healthy_services": 6,
      "total_services": 6,
      "health_percentage": 100.0
    }
  },
  "metrics": {
    "timestamp": "2024-12-18T10:30:00Z",
    "environment": "production",
    "prometheus": {
      "cpu_usage": 65.2,
      "memory_usage": 72.8,
      "api_response_time": 0.245,
      "api_error_rate": 0.002
    }
  },
  "recommendations": [
    " HEALTHY: All systems operating normally"
  ]
}
```

## Service-Specific Monitoring

### Redis Production Monitoring

```python
# Example: Custom Redis monitoring
from scripts.deploy_production import ProductionMonitoring

monitor = ProductionMonitoring()
redis_health = monitor.health_check_redis()

print(f"Redis Status: {redis_health['status']}")
print(f"Memory Usage: {redis_health['used_memory']}")
print(f"Connected Clients: {redis_health['connected_clients']}")
print(f"Replication Role: {redis_health['role']}")
```

**Monitored Metrics:**
- Connection status and ping response
- Memory usage and client connections
- Replication status (master/slave)
- Uptime and version information
- Sentinel status (if configured)

### Kafka Production Monitoring

```python
# Example: Custom Kafka monitoring
kafka_health = monitor.health_check_kafka()

print(f"Kafka Status: {kafka_health['status']}")
print(f"Cluster ID: {kafka_health['cluster_id']}")
print(f"Brokers: {kafka_health['brokers']}")
print(f"Topics: {kafka_health['topics_count']}")
```

**Monitored Metrics:**
- Cluster connectivity and broker count
- Topic count and partition health
- Controller status
- Consumer group lag (if accessible)
- SASL authentication status

### MongoDB Production Monitoring

```python
# Example: Custom MongoDB monitoring
mongo_health = monitor.health_check_mongodb()

print(f"MongoDB Status: {mongo_health['status']}")
print(f"Replica Set: {mongo_health['replica_set']['set_name']}")
print(f"Primary: {mongo_health['replica_set']['primary']}")
print(f"Collections: {mongo_health['collections']}")
```

**Monitored Metrics:**
- Connection status and ping response
- Replica set status and primary election
- Database size and collection count
- Index count and performance
- Version and uptime information

### Netskope API Monitoring

```python
# Example: Custom API monitoring
api_health = monitor.health_check_api()

print(f"API Status: {api_health['status']}")
print(f"Response Time: {api_health['response_time']}s")
print(f"API Version: {api_health.get('api_version', 'unknown')}")
```

**Monitored Metrics:**
- API endpoint availability
- Response time and latency
- Authentication status
- API version and health status
- Rate limiting status

## Alerting and Incident Response

### Alert Thresholds

Production monitoring includes predefined alert thresholds:

```yaml
# From config/production.yaml
ALERT_CPU_THRESHOLD: 80          # CPU usage > 80%
ALERT_MEMORY_THRESHOLD: 85       # Memory usage > 85%
ALERT_DISK_THRESHOLD: 90         # Disk usage > 90%
ALERT_ERROR_RATE_THRESHOLD: 1    # Error rate > 1%
ALERT_RESPONSE_TIME_THRESHOLD: 5000  # Response time > 5s
ALERT_AVAILABILITY_THRESHOLD: 99.9   # Availability < 99.9%
```

### Automated Incident Creation

```python
# Example: Automated incident response
health_data = monitor.run_comprehensive_health_check()

if health_data['overall_health']['health_percentage'] < 95:
    # Create incident in JIRA/ServiceNow
    incident_data = {
        'title': 'Production Health Degradation Detected',
        'severity': 'High' if health_data['overall_health']['health_percentage'] < 80 else 'Medium',
        'description': f"Overall health: {health_data['overall_health']['health_percentage']:.1f}%",
        'affected_services': [
            service for service, data in health_data['services'].items() 
            if data.get('status') != 'healthy'
        ]
    }
    # Integration with incident management system
```

### Notification Channels

```bash
# Slack notifications
export PROD_SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Email notifications
export PROD_SMTP_HOST="smtp.company.com"
export PROD_SMTP_USERNAME="alerts@company.com"
export PROD_SMTP_PASSWORD="..."

# PagerDuty integration
export PAGERDUTY_INTEGRATION_KEY="..."
```

## Security and Compliance

### Access Control

```bash
# Production access requires MFA
export MFA_TOKEN="123456"  # From authenticator app

# Session timeout (30 minutes)
export SECURITY_SESSION_TIMEOUT=1800

# Audit logging enabled
export SECURITY_AUDIT_LOGGING=true
```

### Compliance Monitoring

Production monitoring includes compliance checks:

- **SOC2**: Continuous monitoring and audit logging
- **GDPR**: Data access logging and retention policies
- **HIPAA**: Encryption and access controls (if applicable)
- **PCI DSS**: Security monitoring and incident response
- **ISO27001**: Risk management and continuous monitoring

### Data Protection

```yaml
# All production data is protected
DATA_ENCRYPTION_ENABLED: true
DATA_AUDIT_TRAIL: true
DATA_READ_ONLY: true
SECURITY_TLS_ENABLED: true
SECURITY_TLS_MIN_VERSION: "1.3"
SECURITY_MUTUAL_TLS: true
```

## Troubleshooting

### Common Issues

#### 1. Authentication Failures

```bash
# Check environment variables
echo $REDIS_PROD_PASSWORD | wc -c  # Should not be empty
echo $KAFKA_PROD_USERNAME          # Should not be empty

# Test Vault connectivity (if using Vault)
vault auth -method=userpass username=monitoring-user

# Check TLS certificates
openssl s_client -connect redis-prod.company.com:6379 -verify_return_error
```

#### 2. Network Connectivity

```bash
# Test DNS resolution
nslookup redis-prod.company.com
nslookup kafka-prod.company.com
nslookup mongodb-prod.company.com

# Test port connectivity
telnet redis-prod.company.com 6379
telnet kafka-prod.company.com 9093
telnet mongodb-prod.company.com 27017

# Check firewall rules
curl -v https://api-prod.company.com/health
```

#### 3. Permission Issues

```bash
# Check RBAC permissions
# This would be specific to your production setup

# Verify read-only access
python -c "
from scripts.deploy_production import ProductionMonitoring
monitor = ProductionMonitoring()
assert monitor.config['READ_ONLY_MODE'] is True
print(' Read-only mode confirmed')
"
```

#### 4. Service Health Issues

```bash
# Check individual service health
python scripts/deploy_production.py --action health-check 2>&1 | grep -E "(redis|kafka|mongodb|api)"

# Get detailed error information
python -c "
from scripts.deploy_production import ProductionMonitoring
monitor = ProductionMonitoring()
result = monitor.health_check_redis()
if result['status'] != 'healthy':
    print(f'Redis Error: {result.get(\"error\", \"Unknown\")}')
"
```

### Debugging

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG

# Run with detailed output
python scripts/deploy_production.py --action health-check --verbose

# Check configuration
python -c "
from scripts.deploy_production import ProductionMonitoring
monitor = ProductionMonitoring()
import json
print(json.dumps(monitor.config, indent=2))
"
```

## Best Practices

### 1. Security
- **Never store credentials in code** - Use external secret management
- **Use MFA** - Multi-factor authentication for all production access
- **Rotate credentials regularly** - Follow security policies
- **Monitor access** - All production access should be logged and monitored
- **Principle of least privilege** - Only grant necessary permissions

### 2. Monitoring
- **Continuous monitoring** - Run health checks regularly
- **Alert fatigue prevention** - Set appropriate thresholds
- **Incident response** - Have clear escalation procedures
- **Documentation** - Keep runbooks updated
- **Testing** - Regularly test monitoring and alerting

### 3. Compliance
- **Audit trails** - Maintain comprehensive logs
- **Data protection** - Ensure encryption and access controls
- **Regular reviews** - Conduct access and security reviews
- **Compliance reporting** - Generate regular compliance reports
- **Change management** - Follow change control procedures

### 4. Operational Excellence
- **Automation** - Automate routine monitoring tasks
- **Standardization** - Use consistent monitoring approaches
- **Documentation** - Maintain up-to-date procedures
- **Training** - Ensure team knows monitoring procedures
- **Continuous improvement** - Regularly review and improve monitoring

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Production Health Check
on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes
  workflow_dispatch:

jobs:
  production-health:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run production health check
        env:
          REDIS_PROD_PASSWORD: ${{ secrets.REDIS_PROD_PASSWORD }}
          KAFKA_PROD_USERNAME: ${{ secrets.KAFKA_PROD_USERNAME }}
          KAFKA_PROD_PASSWORD: ${{ secrets.KAFKA_PROD_PASSWORD }}
          MONGODB_PROD_USERNAME: ${{ secrets.MONGODB_PROD_USERNAME }}
          MONGODB_PROD_PASSWORD: ${{ secrets.MONGODB_PROD_PASSWORD }}
          NETSKOPE_PROD_API_KEY: ${{ secrets.NETSKOPE_PROD_API_KEY }}
        run: |
          python scripts/deploy_production.py --action health-check
      
      - name: Generate health report
        if: always()
        run: |
          python scripts/deploy_production.py --action report --output reports/production_health.json
      
      - name: Upload health report
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: production-health-report
          path: reports/production_health.json
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    
    triggers {
        cron('H/15 * * * *')  // Every 15 minutes
    }
    
    environment {
        REDIS_PROD_PASSWORD = credentials('redis-prod-password')
        KAFKA_PROD_USERNAME = credentials('kafka-prod-username')
        KAFKA_PROD_PASSWORD = credentials('kafka-prod-password')
        MONGODB_PROD_USERNAME = credentials('mongodb-prod-username')
        MONGODB_PROD_PASSWORD = credentials('mongodb-prod-password')
        NETSKOPE_PROD_API_KEY = credentials('netskope-prod-api-key')
    }
    
    stages {
        stage('Production Health Check') {
            steps {
                script {
                    def result = sh(
                        script: 'python scripts/deploy_production.py --action health-check',
                        returnStatus: true
                    )
                    
                    if (result != 0) {
                        currentBuild.result = 'UNSTABLE'
                        
                        // Send alert
                        slackSend(
                            channel: '#production-alerts',
                            color: 'danger',
                            message: " Production health check failed! Check Jenkins logs for details."
                        )
                    }
                }
            }
        }
        
        stage('Generate Report') {
            steps {
                sh 'python scripts/deploy_production.py --action report --output reports/production_health_${BUILD_NUMBER}.json'
                
                archiveArtifacts artifacts: 'reports/production_health_*.json'
            }
        }
    }
    
    post {
        always {
            // Clean up
            sh 'rm -f reports/production_health_${BUILD_NUMBER}.json'
        }
    }
}
```

## Support and Escalation

### Escalation Procedures

1. **Level 1**: Automated monitoring detects issue
2. **Level 2**: On-call engineer receives alert
3. **Level 3**: Senior engineer escalation (if not resolved in 30 minutes)
4. **Level 4**: Management escalation (if not resolved in 2 hours)

### Contact Information

- **On-Call Engineer**: PagerDuty rotation
- **Production Team**: production-team@company.com
- **Security Team**: security-team@company.com
- **Management**: engineering-management@company.com

### Emergency Procedures

```bash
# Emergency health check
python scripts/deploy_production.py --action health-check --emergency

# Emergency report generation
python scripts/deploy_production.py --action report --output /tmp/emergency_health_report.json --emergency

# Emergency continuous monitoring
python scripts/deploy_production.py --action monitor --interval 60 --duration 3600 --emergency
```

---

** REMEMBER: This is a READ-ONLY monitoring environment. No modifications to production systems are permitted through this framework.**

For production changes, follow your organization's change management procedures and use appropriate production deployment tools.