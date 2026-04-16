# Staging Environment (E4) Deployment Guide

## Overview

The Staging Environment (E4) provides a production-like Kubernetes-based environment with enhanced security, high availability, and comprehensive monitoring for pre-production testing of the Day-1 Framework. This environment mirrors production configurations while maintaining the safety of a testing environment.

## Key Features

### High Availability (HA)
- **Redis HA**: Master-replica setup with Sentinel for automatic failover
- **Kafka HA**: 5-broker cluster with 5-node Zookeeper ensemble
- **MongoDB HA**: 5-node replica set with arbiter for quorum
- **Prometheus HA**: 2-replica setup for metrics redundancy
- **Enhanced API**: 3-replica deployment with load balancing

### Enhanced Security
- **Authentication**: SASL for Kafka, authentication for all services
- **Encryption**: TLS support for API endpoints
- **Access Control**: RBAC policies and network policies
- **Audit Logging**: Comprehensive audit trails for all operations
- **Secret Management**: Kubernetes secrets with secure generation

### Production-Like Configuration
- **Resource Quotas**: Enforced limits on CPU, memory, and storage
- **Network Policies**: Restricted ingress/egress traffic
- **Storage Classes**: Fast SSD storage for performance
- **Monitoring**: Enhanced Prometheus with custom recording rules
- **Backup**: Automated daily backups with retention policies

## Architecture

```

                    Staging Environment (E4)                      
                  Production-Like Kubernetes Cluster              

           
     Redis HA          Kafka HA         MongoDB HA         
    Master + 2        5 Brokers +       5-Node             
    Replicas +        5 Zookeepers      Replica Set        
    3 Sentinels       with SASL         with Arbiter       
           
                                                                  
           
    Enhanced API     Prometheus HA       Grafana HA        
    3 Replicas        2 Replicas        with Enhanced      
    with TLS &        30d Retention     Dashboards         
    JWT Auth          & Alerting        & Alerting         
           
                                                                  
           
    Jaeger HA         AlertManager      Backup Jobs        
    Distributed       Notification      Daily @ 2 AM       
    Tracing           Management        30d Retention      
           

```

## Prerequisites

### 1. Kubernetes Cluster Requirements

- **Kubernetes version**: 1.22+
- **Nodes**: Minimum 5 nodes for HA (recommended: 7+ nodes)
- **Resources per node**: 
  - CPU: 4+ cores
  - Memory: 16GB+ RAM
  - Storage: 100GB+ SSD
- **Total cluster resources**:
  - CPU: 24+ cores
  - Memory: 48GB+ RAM
  - Storage: 500GB+ with fast SSD storage class
- **Networking**: CNI plugin with NetworkPolicy support
- **Storage**: Dynamic volume provisioning with `fast-ssd` storage class

### 2. Required Tools

```bash
# kubectl
kubectl version --client

# Helm (optional)
helm version

# Python 3.9+
python3 --version
```

### 3. Cluster Preparation

```bash
# Create fast-ssd storage class (if not exists)
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/gce-pd  # Adjust for your cloud provider
parameters:
  type: pd-ssd
  replication-type: regional-pd
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
EOF

# Verify storage class
kubectl get storageclass fast-ssd
```

## Deployment

### Quick Start

```bash
# Deploy staging environment
python scripts/deploy_staging.py --action deploy

# Or use CLI
netskope-sdet staging deploy

# Check deployment status
netskope-sdet staging status

# Run health checks
netskope-sdet staging health-check
```

### Detailed Deployment Steps

#### 1. Pre-Deployment Checks

```bash
# Check cluster connectivity
kubectl cluster-info

# Check available resources
kubectl top nodes

# Verify RBAC permissions
kubectl auth can-i create deployments --namespace=netskope-staging

# Check storage classes
kubectl get storageclass
```

#### 2. Deploy Staging Environment

```bash
# Deploy with default settings
python scripts/deploy_staging.py

# Deploy with custom namespace
python scripts/deploy_staging.py --namespace my-staging-env

# Deploy with custom kubeconfig
python scripts/deploy_staging.py --kubeconfig ~/.kube/staging-config

# Skip confirmation prompts
python scripts/deploy_staging.py --confirm
```

#### 3. Monitor Deployment

```bash
# Watch pod creation
kubectl get pods -n netskope-staging -w

# Check service status
kubectl get services -n netskope-staging

# View deployment logs
kubectl logs -n netskope-staging -l environment=staging --tail=100
```

#### 4. Verify Deployment

```bash
# Run comprehensive health checks
netskope-sdet staging health-check

# Check all pods are running
kubectl get pods -n netskope-staging

# Verify services are accessible
kubectl get svc -n netskope-staging
```

## Configuration

### Environment Configuration

The staging environment uses `config/staging.yaml` with production-like settings:

```yaml
ENVIRONMENT: staging
MOCK_MODE: false

# HA Service Endpoints
REDIS_HOST: redis-ha-service.netskope-staging.svc.cluster.local
REDIS_SENTINEL_HOSTS: redis-sentinel-service:26379
KAFKA_BOOTSTRAP_SERVERS: kafka-ha-service:9092
KAFKA_SECURITY_PROTOCOL: SASL_PLAINTEXT
MONGODB_HOST: mongodb-ha-service.netskope-staging.svc.cluster.local
MONGODB_REPLICA_SET: rs0

# Enhanced Security
SECURITY_TLS_ENABLED: true
SECURITY_AUDIT_LOGGING: true
SECURITY_ACCESS_CONTROL: rbac

# Enhanced Monitoring
METRICS_RETENTION: 30d
TRACING_ENABLED: true
LOG_RETENTION: 30d
```

### Resource Allocation

Default resource allocation for staging (per service):

| Service | Replicas | CPU Request | Memory Request | CPU Limit | Memory Limit | Storage |
|---------|----------|-------------|----------------|-----------|--------------|---------|
| Redis HA | 1+2 | 500m | 1Gi | 2 | 4Gi | 20Gi |
| Kafka HA | 5 | 1 | 3Gi | 4 | 6Gi | 50Gi |
| Zookeeper HA | 5 | 200m | 512Mi | 1 | 2Gi | 10Gi |
| MongoDB HA | 5 | 1 | 4Gi | 4 | 8Gi | 100Gi |
| Staging API | 3 | 200m | 512Mi | 1 | 2Gi | - |
| Prometheus HA | 2 | 1 | 4Gi | 4 | 8Gi | 100Gi |
| Grafana HA | 1 | 100m | 256Mi | 500m | 1Gi | - |

### Security Configuration

#### Secrets Management

Staging uses secure, auto-generated secrets:

```bash
# View secrets (without decoding)
kubectl get secrets -n netskope-staging

# Decode a secret (example)
kubectl get secret redis-ha-secret -n netskope-staging -o jsonpath='{.data.password}' | base64 --decode
```

#### Network Policies

Network policies restrict traffic between pods:

```bash
# View network policies
kubectl get networkpolicies -n netskope-staging

# Describe network policy
kubectl describe networkpolicy staging-network-policy -n netskope-staging
```

## Access and Usage

### Accessing Services

#### Port Forwarding

```bash
# Grafana HA Dashboard
kubectl port-forward -n netskope-staging svc/grafana-ha-service 3000:3000

# Prometheus HA
kubectl port-forward -n netskope-staging svc/prometheus-ha-service 9090:9090

# Staging API
kubectl port-forward -n netskope-staging svc/staging-api-service 8080:8080

# Redis HA Master
kubectl port-forward -n netskope-staging svc/redis-ha-service 6379:6379

# MongoDB HA Primary
kubectl port-forward -n netskope-staging svc/mongodb-ha-service 27017:27017
```

#### Service URLs (after port forwarding)

- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Staging API**: https://localhost:8080
- **Redis**: localhost:6379
- **MongoDB**: localhost:27017

### Running Tests

```bash
# Run integration tests
netskope-sdet staging test --test-type integration

# Run E2E tests
netskope-sdet staging test --test-type e2e

# Run security tests
netskope-sdet staging test --test-type security

# Run load tests
netskope-sdet staging test --test-type load

# Run all tests
netskope-sdet staging test
```

### Monitoring and Observability

#### Grafana Dashboards

Access Grafana at http://localhost:3000 (after port forwarding):
- **Credentials**: Check secrets in Kubernetes
- **Dashboards**: Pre-configured staging dashboards
- **Alerts**: Production-like alerting rules

#### Prometheus Metrics

Access Prometheus at http://localhost:9090:
- **Metrics**: 30-day retention
- **Recording Rules**: Pre-aggregated metrics
- **Alert Rules**: Production-like alerts

#### Logs

```bash
# View all staging logs
kubectl logs -n netskope-staging -l environment=staging --tail=100

# View specific service logs
netskope-sdet staging logs --service redis-ha --follow

# View logs for all pods
kubectl logs -n netskope-staging --all-containers=true --tail=100
```

## High Availability Features

### Redis HA

- **Master-Replica**: 1 master + 2 replicas
- **Sentinel**: 3 sentinels for automatic failover
- **Failover Time**: < 30 seconds
- **Data Persistence**: AOF + RDB snapshots

### Kafka HA

- **Brokers**: 5 brokers for high availability
- **Zookeeper**: 5-node ensemble for quorum
- **Replication Factor**: 3 (configurable)
- **Min In-Sync Replicas**: 2

### MongoDB HA

- **Replica Set**: 5 nodes (4 data + 1 arbiter)
- **Automatic Failover**: < 30 seconds
- **Read Preference**: Primary preferred
- **Write Concern**: Majority

## Backup and Recovery

### Automated Backups

```bash
# View backup CronJob
kubectl get cronjob mongodb-backup -n netskope-staging

# Manually trigger backup
kubectl create job --from=cronjob/mongodb-backup manual-backup-$(date +%Y%m%d) -n netskope-staging

# View backup logs
kubectl logs -n netskope-staging job/manual-backup-<date>
```

### Backup Schedule

- **MongoDB**: Daily at 2 AM
- **Retention**: 30 days
- **Storage**: Persistent volume (500Gi)
- **Compression**: Enabled
- **Encryption**: Enabled

### Recovery Procedures

```bash
# List available backups
kubectl exec -n netskope-staging mongodb-ha-cluster-0 -- ls -la /backup

# Restore from backup
kubectl exec -n netskope-staging mongodb-ha-cluster-0 -- mongorestore --uri="mongodb://..." /backup/mongodb_backup_<date>
```

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting

```bash
# Check pod status
kubectl get pods -n netskope-staging

# Describe problematic pod
kubectl describe pod <pod-name> -n netskope-staging

# Check events
kubectl get events -n netskope-staging --sort-by='.lastTimestamp'
```

#### 2. Service Connectivity Issues

```bash
# Test service DNS resolution
kubectl run test-dns --image=busybox -n netskope-staging --rm -it -- nslookup redis-ha-service

# Test service connectivity
kubectl run test-conn --image=curlimages/curl -n netskope-staging --rm -it -- curl -v redis-ha-service:6379
```

#### 3. Resource Constraints

```bash
# Check node resources
kubectl top nodes

# Check pod resources
kubectl top pods -n netskope-staging

# Check resource quotas
kubectl describe resourcequota -n netskope-staging
```

#### 4. Storage Issues

```bash
# Check PVCs
kubectl get pvc -n netskope-staging

# Describe PVC
kubectl describe pvc <pvc-name> -n netskope-staging

# Check storage class
kubectl get storageclass fast-ssd
```

### Health Checks

```bash
# Comprehensive health check
netskope-sdet staging health-check

# Check individual services
kubectl exec -n netskope-staging redis-ha-master-0 -- redis-cli -a <password> ping
kubectl exec -n netskope-staging mongodb-ha-cluster-0 -- mongosh --eval "rs.status()"
kubectl exec -n netskope-staging kafka-ha-cluster-0 -- kafka-broker-api-versions --bootstrap-server localhost:9093
```

## Scaling

### Horizontal Scaling

```bash
# Scale Redis replicas
kubectl scale statefulset redis-ha-replica --replicas=3 -n netskope-staging

# Scale Kafka brokers
kubectl scale statefulset kafka-ha-cluster --replicas=7 -n netskope-staging

# Scale MongoDB replica set
kubectl scale statefulset mongodb-ha-cluster --replicas=7 -n netskope-staging

# Scale API service
kubectl scale deployment staging-api-service --replicas=5 -n netskope-staging
```

### Vertical Scaling

Update resource limits in manifests and apply:

```bash
kubectl apply -f k8s/staging/<updated-manifest>.yaml
```

## Cleanup

### Remove Staging Environment

```bash
# Using CLI (with confirmation)
netskope-sdet staging undeploy

# Using script
python scripts/deploy_staging.py --action undeploy

# Using kubectl (immediate deletion)
kubectl delete namespace netskope-staging
```

### Backup Before Deletion

```bash
# Backup all configurations
kubectl get all,configmaps,secrets,pvc -n netskope-staging -o yaml > staging-backup.yaml

# Backup data
kubectl create job --from=cronjob/mongodb-backup final-backup -n netskope-staging
```

## Best Practices

### 1. Security
- Rotate secrets regularly
- Use RBAC for access control
- Enable audit logging
- Monitor security events

### 2. Monitoring
- Set up alerts for critical metrics
- Review dashboards regularly
- Monitor resource usage
- Track error rates

### 3. Performance
- Monitor service latency
- Optimize resource allocation
- Use connection pooling
- Enable caching where appropriate

### 4. Reliability
- Test failover scenarios
- Verify backup procedures
- Monitor replication lag
- Test disaster recovery

### 5. Maintenance
- Regular updates and patches
- Capacity planning
- Performance tuning
- Documentation updates

## Support

For issues or questions:
1. Check logs: `netskope-sdet staging logs`
2. Run health checks: `netskope-sdet staging health-check`
3. Check status: `netskope-sdet staging status`
4. Review documentation: `docs/staging_environment_guide.md`

---

**Note**: The Staging Environment (E4) is designed to mirror production configurations. Always test changes in staging before deploying to production.