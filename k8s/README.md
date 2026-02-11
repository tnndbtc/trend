# Kubernetes Deployment for Trend Intelligence Platform

This directory contains Kubernetes manifests and Helm charts for deploying the Trend Intelligence Platform.

## Directory Structure

```
k8s/
├── base/                       # Base Kubernetes manifests
│   ├── namespace.yaml          # Namespace definition
│   ├── configmap.yaml          # Configuration
│   ├── secrets.yaml            # Secrets (use external secrets in production)
│   ├── api-deployment.yaml     # FastAPI application
│   ├── celery-worker-deployment.yaml  # Celery workers
│   ├── postgres-statefulset.yaml     # PostgreSQL database
│   ├── redis-deployment.yaml   # Redis cache
│   ├── qdrant-statefulset.yaml # Qdrant vector database
│   ├── ingress.yaml            # Ingress configuration
│   └── kustomization.yaml      # Kustomize base
├── overlays/                   # Environment-specific overlays
│   ├── dev/                    # Development environment
│   ├── staging/                # Staging environment
│   └── production/             # Production environment
└── helm/                       # Helm charts (optional)

```

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- kustomize (or kubectl with kustomize support)
- Helm 3.x (optional)
- Ingress controller (nginx recommended)
- cert-manager for TLS certificates

## Quick Start

### Deploy with Kustomize

```bash
# Deploy base configuration
kubectl apply -k k8s/base

# Deploy production configuration
kubectl apply -k k8s/overlays/production

# Verify deployment
kubectl get all -n trend-intelligence
```

### Deploy with kubectl

```bash
# Apply manifests individually
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/secrets.yaml
kubectl apply -f k8s/base/postgres-statefulset.yaml
kubectl apply -f k8s/base/redis-deployment.yaml
kubectl apply -f k8s/base/qdrant-statefulset.yaml
kubectl apply -f k8s/base/api-deployment.yaml
kubectl apply -f k8s/base/celery-worker-deployment.yaml
kubectl apply -f k8s/base/ingress.yaml
```

## Configuration

### Environment Variables

Configure the platform via ConfigMap (`k8s/base/configmap.yaml`):

- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `POSTGRES_DB`: PostgreSQL database name
- `REDIS_PORT`: Redis port
- `ENABLE_RATE_LIMITING`: Enable API rate limiting

### Secrets

**IMPORTANT**: The secrets in `k8s/base/secrets.yaml` are base64-encoded placeholders for development only.

For production:
1. Use [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
2. Or [External Secrets Operator](https://external-secrets.io/)
3. Or cloud provider secret managers (AWS Secrets Manager, Google Secret Manager, etc.)

## Scaling

### Horizontal Pod Autoscaling

```bash
# API autoscaling
kubectl autoscale deployment trend-api \
  --cpu-percent=70 \
  --min=3 \
  --max=20 \
  -n trend-intelligence

# Celery worker autoscaling
kubectl autoscale deployment celery-worker \
  --cpu-percent=80 \
  --min=5 \
  --max=50 \
  -n trend-intelligence
```

### Manual Scaling

```bash
# Scale API replicas
kubectl scale deployment trend-api --replicas=10 -n trend-intelligence

# Scale Celery workers
kubectl scale deployment celery-worker --replicas=20 -n trend-intelligence
```

## Monitoring

Deployments are configured with Prometheus annotations for automatic scraping:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

Access metrics:
```bash
kubectl port-forward -n trend-intelligence svc/trend-api 8000:8000
curl http://localhost:8000/metrics
```

## Troubleshooting

### Check pod status
```bash
kubectl get pods -n trend-intelligence
kubectl describe pod <pod-name> -n trend-intelligence
kubectl logs <pod-name> -n trend-intelligence
```

### Check services
```bash
kubectl get svc -n trend-intelligence
kubectl describe svc trend-api -n trend-intelligence
```

### Database connection issues
```bash
# Check PostgreSQL
kubectl exec -it postgres-0 -n trend-intelligence -- psql -U trend_user -d trends

# Check Redis
kubectl exec -it <redis-pod> -n trend-intelligence -- redis-cli ping
```

## Resource Requirements

### Minimum Requirements
- **API**: 500m CPU, 512Mi RAM (3 replicas)
- **Celery Workers**: 1000m CPU, 1Gi RAM (5 replicas)
- **PostgreSQL**: 500m CPU, 1Gi RAM, 50Gi storage
- **Redis**: 250m CPU, 512Mi RAM
- **Qdrant**: 500m CPU, 1Gi RAM, 20Gi storage

### Production Requirements
- **Total**: ~15 CPU cores, ~30Gi RAM, ~100Gi storage (minimum)
- **Recommended**: 30+ CPU cores, 60Gi+ RAM for high throughput

## Security

1. **Network Policies**: Implement network policies to restrict traffic between pods
2. **Pod Security Standards**: Apply restricted PSS/PSA
3. **RBAC**: Use service accounts with minimal permissions
4. **Secrets**: Use external secret management
5. **TLS**: Enable TLS for all external traffic (via Ingress + cert-manager)

## Updates and Rollbacks

### Rolling Update
```bash
# Update image
kubectl set image deployment/trend-api \
  api=trend-intelligence/api:v1.1.0 \
  -n trend-intelligence

# Check rollout status
kubectl rollout status deployment/trend-api -n trend-intelligence
```

### Rollback
```bash
# Rollback to previous version
kubectl rollout undo deployment/trend-api -n trend-intelligence

# Rollback to specific revision
kubectl rollout undo deployment/trend-api --to-revision=2 -n trend-intelligence
```

## Cleanup

```bash
# Delete all resources in namespace
kubectl delete namespace trend-intelligence

# Or with kustomize
kubectl delete -k k8s/base
```
