# Integration Environment (E3) Deployment Guide

## Overview

The Integration Environment (E3) provides a production-like Kubernetes-based environment for comprehensive end-to-end testing of the Netskope SDET Framework. This environment includes all services running in a distributed, scalable configuration with full monitoring and observability.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Integration Environment (E3)                 │
│                         Kubernetes Cluster                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    Redis    │  │    Kafka    │  │  MongoDB    │             │
│  │   Cluster   │  │   Cluster   │  │  Replica    │             │
│  │  (3 nodes)  │  │  (3 nodes)  │  │    Set      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Mock API  │  │ Prometheus  │  │   Grafana   │             │
│  │   Service   │  │  Metrics    │  │ Dashboard   │             │
│  │ (2 replicas)│  │ Collection  │  │   & Alerts  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Jaeger    │  │ Test Runner │  │   Ingress   │             │
│  │  Tracing    │  │    Jobs     │  │ Controller  │             │
│  │   Service   │  │ (Scheduled) │  │   (nginx)   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. Kubernetes Cluster

You need access to a Kubernetes cluster with:
- **Kubernetes version**: 1.20+
- **Nodes**: At least 3 nodes (for high availability)
- **Resources**: Minimum 16 CPU cores, 32GB RAM total
- **Storage**: Dynamic volume provisioning enabled
- **Networking**: CNI plugin installed (Calico, Flannel, etc.)

### 2. Required Tools

```bash
# kubectl (Kubernetes CLI)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Helm (optional, for advanced deployments)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Docker (for building custom images)
# Install Docker Desktop or Docker Engine
```

### 3. Cluster Access

Ensure you have proper access to your Kubernetes cluster:

```bash
# Test cluster connectivity
kubectl cluster-info

# Check available resources
kubectl top nodes

# Verify permissions
kubectl auth can-i create deployments --namespace=netskope-integration
```

## Quick Start Deployment

### 1. Deploy Integration Environment

```bash
# Clone the repository
git clone <repo_url>
cd netskope_sdet_framework

# Deploy the complete integration environment
python scripts/deploy_integration.py --action deploy

# Or use the CLI
netskope-sdet integration deploy
```

### 2. Verify Deployment

```bash
# Check deployment status
netskope-sdet integration status

# Run health checks
netskope-sdet integration health-check

# View service logs
netskope-sdet integration logs --service redis
```

### 3. Access Services

```bash
# Port forward to access services locally
kubectl port-forward -n netskope-integration svc/grafana-service 3000:3000 &
kubectl port-forward -n netskope-integration svc/prometheus-service 9090:9090 &
kubectl port-forward -n netskope-integration svc/jaeger-service 16686:16686 &
kubectl port-forward -n netskope-integration svc/mock-api-service 8080:8080 &

# Access URLs
# Grafana: http://localhost:3000 (admin/integration-grafana-2024)
# Prometheus: http://localhost:9090
# Jaeger: http://localhost:16686
# Mock API: http://localhost:8080
```

### 4. Run Tests

```bash
# Run integration tests
netskope-sdet integration test --test-type integration

# Run E2E tests
netskope-sdet integration test --test-type e2e

# Run all tests
netskope-sdet integration test
```

## Detailed Deployment Options

### Option 1: Using Python Script

```bash
# Basic deployment
python scripts/deploy_integration.py

# Custom namespace
python scripts/deploy_integration.py --namespace my-integration-env

# Custom kubeconfig
python scripts/deploy_integration.py --kubeconfig ~/.kube/my-config

# Check status
python scripts/deploy_integration.py --action status

# Remove environment
python scripts/deploy_integration.py --action undeploy
```

### Option 2: Using CLI

```bash
# Deploy with default settings
netskope-sdet integration deploy

# Deploy with custom namespace
netskope-sdet integration deploy --namespace my-integration-env

# Check status
netskope-sdet integration status

# View logs
netskope-sdet integration logs --follow

# Remove environment
netskope-sdet integration undeploy
```

### Option 3: Using Helm Charts

```bash
# Install using Helm
helm install netskope-integration ./helm/netskope-sdet \
  --namespace netskope-integration \
  --create-namespace \
  --values ./helm/netskope-sdet/values-integration.yaml

# Upgrade deployment
helm upgrade netskope-integration ./helm/netskope-sdet \
  --namespace netskope-integration \
  --values ./helm/netskope-sdet/values-integration.yaml

# Uninstall
helm uninstall netskope-integration --namespace netskope-integration
```

### Option 4: Manual kubectl Deployment

```bash
# Deploy manifests in order
kubectl apply -f k8s/integration/namespace.yaml
kubectl apply -f k8s/integration/redis-cluster.yaml
kubectl apply -f k8s/integration/kafka-cluster.yaml
kubectl apply -f k8s/integration/mongodb-replica.yaml
kubectl apply -f k8s/integration/mock-api-service.yaml
kubectl apply -f k8s/integration/monitoring-stack.yaml
kubectl apply -f k8s/integration/test-runner-job.yaml

# Check deployment
kubectl get all -n netskope-integration
```

## Configuration

### Environment Variables

The integration environment uses the following configuration:

```yaml
# config/integration.yaml
ENVIRONMENT: integration
MOCK_MODE: false

# Service endpoints (Kubernetes DNS)
REDIS_HOST: redis-service.netskope-integration.svc.cluster.local
KAFKA_BOOTSTRAP_SERVERS: kafka-service.netskope-integration.svc.cluster.local:9092
MONGODB_HOST: mongodb-service.netskope-integration.svc.cluster.local
NETSKOPE_BASE_URL: http://mock-api-service.netskope-integration.svc.cluster.local:8080

# Monitoring
PROMETHEUS_URL: http://prometheus-service.netskope-integration.svc.cluster.local:9090
GRAFANA_URL: http://grafana-service.netskope-integration.svc.cluster.local:3000
JAEGER_URL: http://jaeger-service.netskope-integration.svc.cluster.local:16686
```

### Resource Allocation

Default resource allocation per service:

| Service | CPU Request | Memory Request | CPU Limit | Memory Limit |
|---------|-------------|----------------|-----------|--------------|
| Redis | 100m | 256Mi | 500m | 1Gi |
| Kafka | 200m | 512Mi | 1 | 2Gi |
| MongoDB | 200m | 512Mi | 1 | 2Gi |
| Mock API | 100m | 128Mi | 500m | 512Mi |
| Prometheus | 200m | 512Mi | 1 | 2Gi |
| Grafana | 100m | 256Mi | 500m | 1Gi |
| Jaeger | 100m | 256Mi | 500m | 1Gi |
| Test Runner | 500m | 1Gi | 2 | 4Gi |

### Storage Requirements

| Service | Volume Size | Storage Class |
|---------|-------------|---------------|
| Redis | 5Gi per replica | Default |
| Kafka | 10Gi per broker | Default |
| Zookeeper | 5Gi data + 2Gi logs | Default |
| MongoDB | 10Gi per replica | Default |

## Monitoring and Observability

### Grafana Dashboards

Access Grafana at `http://localhost:3000` (after port forwarding):
- **Username**: admin
- **Password**: integration-grafana-2024

Available dashboards:
- **Netskope SDET Overview**: System health and test metrics
- **Redis Metrics**: Cache performance and usage
- **Kafka Metrics**: Message throughput and lag
- **MongoDB Metrics**: Database performance
- **Test Execution**: Test results and trends

### Prometheus Metrics

Access Prometheus at `http://localhost:9090`:
- Service health metrics
- Application performance metrics
- Test execution metrics
- Resource utilization metrics

### Jaeger Tracing

Access Jaeger at `http://localhost:16686`:
- Distributed tracing across services
- Request flow visualization
- Performance bottleneck identification

## Testing

### Test Types

1. **Integration Tests**: Service integration validation
2. **E2E Tests**: Complete workflow testing
3. **Security Tests**: Security policy validation
4. **Performance Tests**: Load and performance testing
5. **Smoke Tests**: Basic functionality validation

### Running Tests

```bash
# Run specific test type
netskope-sdet integration test --test-type integration

# Run with custom parameters
kubectl create job test-custom --from=cronjob/scheduled-integration-tests \
  -n netskope-integration

# Monitor test execution
kubectl logs -n netskope-integration job/test-custom -f

# Get test results
kubectl cp netskope-integration/test-custom-pod:/app/reports ./test-reports
```

### Scheduled Tests

Tests run automatically on schedule:
- **Daily**: Full integration test suite at 2 AM
- **Twice daily**: Smoke tests at 1 AM and 1 PM

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting

```bash
# Check pod status
kubectl get pods -n netskope-integration

# Describe problematic pod
kubectl describe pod <pod-name> -n netskope-integration

# Check logs
kubectl logs <pod-name> -n netskope-integration
```

#### 2. Service Connectivity Issues

```bash
# Test service connectivity
kubectl run test-pod --image=curlimages/curl -n netskope-integration --rm -it -- sh

# Inside the pod, test services:
curl redis-service:6379
curl kafka-service:9092
curl mongodb-service:27017
curl mock-api-service:8080/health
```

#### 3. Resource Constraints

```bash
# Check node resources
kubectl top nodes

# Check pod resources
kubectl top pods -n netskope-integration

# Describe resource quotas
kubectl describe resourcequota -n netskope-integration
```

#### 4. Storage Issues

```bash
# Check persistent volumes
kubectl get pv

# Check persistent volume claims
kubectl get pvc -n netskope-integration

# Describe storage issues
kubectl describe pvc <pvc-name> -n netskope-integration
```

### Health Checks

```bash
# Run comprehensive health check
netskope-sdet integration health-check

# Check individual services
kubectl exec -n netskope-integration deployment/redis-cluster -- redis-cli ping
kubectl exec -n netskope-integration deployment/mongodb-replica -- mongosh --eval "db.adminCommand('ping')"
```

### Log Analysis

```bash
# View all logs
kubectl logs -n netskope-integration -l environment=integration --tail=100

# Follow specific service logs
netskope-sdet integration logs --service redis --follow

# Export logs for analysis
kubectl logs -n netskope-integration -l app=kafka > kafka-logs.txt
```

## Scaling and Performance

### Horizontal Scaling

```bash
# Scale Redis cluster
kubectl scale statefulset redis-cluster --replicas=5 -n netskope-integration

# Scale Kafka cluster
kubectl scale statefulset kafka-cluster --replicas=5 -n netskope-integration

# Scale Mock API
kubectl scale deployment mock-api-service --replicas=4 -n netskope-integration
```

### Vertical Scaling

Update resource limits in the deployment manifests:

```yaml
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2
    memory: 4Gi
```

### Performance Tuning

1. **Redis**: Adjust memory policies and persistence settings
2. **Kafka**: Tune partition counts and replication factors
3. **MongoDB**: Configure appropriate indexes and connection pools
4. **Test Runner**: Adjust parallel worker counts

## Security

### Network Policies

```bash
# Apply network policies (if enabled)
kubectl apply -f k8s/integration/network-policies.yaml
```

### RBAC

The deployment creates minimal RBAC permissions:
- Service account for test runner
- Role for accessing pods and services
- RoleBinding to associate account with role

### Secrets Management

Sensitive data is stored in Kubernetes secrets:
- Database passwords
- API keys
- Service credentials

## Backup and Recovery

### Data Backup

```bash
# Backup MongoDB data
kubectl exec -n netskope-integration mongodb-replica-0 -- mongodump --out /tmp/backup

# Backup Redis data
kubectl exec -n netskope-integration redis-cluster-0 -- redis-cli BGSAVE
```

### Configuration Backup

```bash
# Export all configurations
kubectl get all,configmaps,secrets -n netskope-integration -o yaml > integration-backup.yaml
```

## Cleanup

### Remove Integration Environment

```bash
# Using CLI
netskope-sdet integration undeploy

# Using script
python scripts/deploy_integration.py --action undeploy

# Using kubectl
kubectl delete namespace netskope-integration

# Using Helm
helm uninstall netskope-integration --namespace netskope-integration
```

## Advanced Configuration

### Custom Images

Build and use custom images:

```bash
# Build integration test runner image
docker build -f Dockerfile.integration -t netskope-sdet:integration .

# Push to registry
docker tag netskope-sdet:integration your-registry/netskope-sdet:integration
docker push your-registry/netskope-sdet:integration

# Update deployment to use custom image
kubectl set image deployment/test-runner-deployment test-runner=your-registry/netskope-sdet:integration -n netskope-integration
```

### Environment Customization

Create custom configuration files:

```bash
# Copy and modify configuration
cp config/integration.yaml config/my-integration.yaml

# Update deployment to use custom config
kubectl create configmap my-integration-config --from-file=config/my-integration.yaml -n netskope-integration
```

### Multi-Environment Setup

Deploy multiple integration environments:

```bash
# Deploy to different namespaces
netskope-sdet integration deploy --namespace integration-dev
netskope-sdet integration deploy --namespace integration-staging
netskope-sdet integration deploy --namespace integration-prod
```

## Support and Troubleshooting

### Getting Help

1. **Check logs**: Always start with service and pod logs
2. **Verify resources**: Ensure adequate CPU, memory, and storage
3. **Test connectivity**: Verify network connectivity between services
4. **Review configuration**: Check environment variables and config maps
5. **Monitor metrics**: Use Grafana dashboards to identify issues

### Common Solutions

- **Pod crashes**: Check resource limits and increase if necessary
- **Service timeouts**: Verify network policies and service discovery
- **Storage issues**: Ensure dynamic provisioning is working
- **Test failures**: Check service health and connectivity

For additional support, refer to the main documentation or create an issue in the project repository.