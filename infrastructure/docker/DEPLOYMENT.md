# ShopFDS Deployment Guide

Complete guide for deploying the ShopFDS platform to production using Docker and Kubernetes.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Configuration](#configuration)
- [Build & Push Images](#build--push-images)
- [Deployment Verification](#deployment-verification)
- [Monitoring & Logs](#monitoring--logs)
- [Troubleshooting](#troubleshooting)
- [Security Checklist](#security-checklist)

---

## Prerequisites

### Required Software

- **Docker**: 20.10+ (with Docker Compose v2)
- **Kubernetes**: 1.24+ (for K8s deployment)
- **kubectl**: Latest version
- **Git**: For source code management

### Infrastructure Requirements

**Minimum Hardware (Docker Compose)**:
- CPU: 8 cores
- RAM: 16 GB
- Disk: 100 GB SSD

**Recommended Hardware (Kubernetes)**:
- Control Plane: 4 cores, 8 GB RAM
- Worker Nodes: 3+ nodes with 8 cores, 16 GB RAM each
- Storage: 500 GB+ distributed storage (Ceph, NFS, etc.)

### Network Requirements

- Open ports: 80, 443 (HTTP/HTTPS), 8000-8003 (Backend services)
- Outbound internet access for:
  - Docker image pulling
  - External API calls (EmailRep, Numverify, etc.)
  - Package installations

---

## Docker Deployment

### 1. Prepare Environment

```bash
# Clone the repository
git clone https://github.com/your-org/ShopFDS.git
cd ShopFDS/infrastructure/docker

# Copy environment template
cp .env.production.template .env.production

# Edit with production values (IMPORTANT!)
vi .env.production
```

**Critical**: Update all passwords, API keys, and secrets in `.env.production`. See [Configuration](#configuration) section.

### 2. Build Docker Images

**Linux/Mac**:
```bash
# Make script executable
chmod +x build-images.sh

# Build all images (with version tag)
./build-images.sh v1.0.0

# Or build with latest tag
./build-images.sh
```

**Windows**:
```cmd
REM Build all images
build-images.bat v1.0.0
```

Build process takes approximately 15-30 minutes depending on hardware.

### 3. Start Services

```bash
# Start all services in production mode
docker-compose -f docker-compose.prod.yml up -d

# Verify all containers are running
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 4. Initialize Database

```bash
# Run database migrations
docker-compose -f docker-compose.prod.yml exec ecommerce-backend \
    alembic upgrade head

# Seed initial data (optional)
docker-compose -f docker-compose.prod.yml exec postgres \
    psql -U shopfds_user -d shopfds_prod -f /docker-entrypoint-initdb.d/seed_products.sql
```

### 5. Verify Deployment

```bash
# Check health endpoints
curl http://localhost:8000/health  # Ecommerce Backend
curl http://localhost:8001/health  # FDS Service
curl http://localhost:8002/health  # ML Service
curl http://localhost:8003/health  # Admin Dashboard Backend

# Check frontend
curl http://localhost:3000  # Ecommerce Frontend
curl http://localhost:3001  # Admin Dashboard Frontend
```

---

## Kubernetes Deployment

### 1. Prepare Kubernetes Cluster

```bash
# Verify kubectl is configured
kubectl cluster-info

# Verify cluster version
kubectl version --short

# Check node status
kubectl get nodes
```

### 2. Build and Push Images

```bash
# Build images
./build-images.sh v1.0.0

# Login to your registry (Docker Hub, ECR, GCR, etc.)
docker login

# Push images to registry
./push-images.sh v1.0.0
```

**For private registries**:
```bash
# AWS ECR example
export REGISTRY=123456789012.dkr.ecr.us-east-1.amazonaws.com
./build-images.sh v1.0.0
./push-images.sh v1.0.0

# Create Kubernetes secret for registry access
kubectl create secret docker-registry regcred \
    --docker-server=$REGISTRY \
    --docker-username=AWS \
    --docker-password=$(aws ecr get-login-password) \
    -n shopfds
```

### 3. Configure Kubernetes Manifests

```bash
cd ../k8s

# Edit secrets.yaml with production values
vi secrets.yaml

# IMPORTANT: Encode secrets in base64
echo -n 'your-password' | base64

# Edit configmap.yaml with production settings
vi configmap.yaml

# Update image tags in deployment files
sed -i 's/latest/v1.0.0/g' *.yaml
```

### 4. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Deploy ConfigMap and Secrets
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml

# Deploy persistent volumes
kubectl apply -f persistent-volumes.yaml

# Deploy database and cache
kubectl apply -f postgres.yaml
kubectl apply -f redis.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n shopfds --timeout=300s

# Deploy backend services
kubectl apply -f ecommerce-backend.yaml
kubectl apply -f fds-service.yaml
kubectl apply -f ml-service.yaml
kubectl apply -f admin-dashboard-backend.yaml

# Deploy frontend services
kubectl apply -f ecommerce-frontend.yaml
kubectl apply -f admin-dashboard-frontend.yaml

# Deploy Ingress
kubectl apply -f ingress.yaml

# Or deploy everything at once with Kustomize
kubectl apply -k .
```

### 5. Run Database Migrations

```bash
# Create a one-time job for migrations
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  namespace: shopfds
spec:
  template:
    spec:
      containers:
      - name: migration
        image: shopfds/ecommerce-backend:v1.0.0
        command: ["alembic", "upgrade", "head"]
        envFrom:
        - configMapRef:
            name: shopfds-config
        - secretRef:
            name: shopfds-secrets
      restartPolicy: Never
  backoffLimit: 3
EOF

# Check migration job status
kubectl logs -n shopfds job/db-migration
```

---

## Configuration

### Environment Variables

See `.env.production.template` for all available environment variables.

**Critical Variables**:

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Database password | Generate with `openssl rand -hex 16` |
| `REDIS_PASSWORD` | Redis password | Generate with `openssl rand -hex 16` |
| `JWT_SECRET` | JWT signing secret | Generate with `openssl rand -hex 32` |
| `SENTRY_DSN` | Error tracking URL | `https://...@sentry.io/...` |
| `EMAILREP_API_KEY` | EmailRep API key | From https://emailrep.io/ |
| `NUMVERIFY_API_KEY` | Phone validation API | From https://numverify.com/ |
| `HIBP_API_KEY` | Pwned password check | From https://haveibeenpwned.com/ |
| `MAXMIND_LICENSE_KEY` | GeoIP database | From https://www.maxmind.com/ |

### Generate Secrets

```bash
# JWT Secret (32 bytes)
openssl rand -hex 32

# Database Password (16 bytes)
openssl rand -hex 16

# Base64 encoding for Kubernetes secrets
echo -n 'my-secret' | base64
```

### Update Kubernetes Secrets

```bash
# Edit secrets directly
kubectl edit secret shopfds-secrets -n shopfds

# Or delete and recreate
kubectl delete secret shopfds-secrets -n shopfds
kubectl create secret generic shopfds-secrets \
    --from-literal=POSTGRES_PASSWORD=$(openssl rand -hex 16) \
    --from-literal=REDIS_PASSWORD=$(openssl rand -hex 16) \
    --from-literal=JWT_SECRET=$(openssl rand -hex 32) \
    -n shopfds
```

---

## Build & Push Images

### Automated Build Script

The `build-images.sh` (Linux/Mac) or `build-images.bat` (Windows) script builds all Docker images with proper tags and metadata.

**Features**:
- Multi-stage builds for smaller images
- Version tagging
- Build metadata (date, git commit)
- Automated error handling

**Usage**:
```bash
# Build with specific version
./build-images.sh v1.2.0

# Build with no cache
NO_CACHE=1 ./build-images.sh v1.2.0

# Build for different registry
REGISTRY=myregistry.azurecr.io ./build-images.sh v1.2.0
```

### Manual Build (if needed)

```bash
# Build single service
docker build \
    --tag shopfds/fds-service:v1.0.0 \
    --file services/fds/Dockerfile \
    services/fds

# Push to registry
docker push shopfds/fds-service:v1.0.0
```

---

## Deployment Verification

### Health Checks

All services expose `/health` endpoints:

```bash
# Docker Compose
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health

# Kubernetes (via port-forward)
kubectl port-forward -n shopfds svc/ecommerce-backend 8000:8000
curl http://localhost:8000/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-18T12:34:56Z",
  "version": "v1.0.0",
  "database": "connected",
  "redis": "connected"
}
```

### Service Status

**Docker Compose**:
```bash
docker-compose -f docker-compose.prod.yml ps
```

**Kubernetes**:
```bash
# Check all pods
kubectl get pods -n shopfds

# Check services
kubectl get svc -n shopfds

# Check ingress
kubectl get ingress -n shopfds

# Check HPA (autoscaling)
kubectl get hpa -n shopfds
```

### Test End-to-End Flow

```bash
# 1. Register a new user
curl -X POST http://localhost:8000/v1/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"Test123!"}'

# 2. Login
curl -X POST http://localhost:8000/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"Test123!"}'

# 3. Create an order (triggers FDS evaluation)
# (Use JWT token from login response)

# 4. Check FDS evaluation result
curl http://localhost:8001/v1/fds/evaluate/<transaction_id>
```

---

## Monitoring & Logs

### Docker Compose Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f fds-service

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 fds-service
```

### Kubernetes Logs

```bash
# Get logs from all pods of a service
kubectl logs -n shopfds -l app=fds-service --tail=100 -f

# Get logs from specific pod
kubectl logs -n shopfds fds-service-abc123 -f

# Get logs from previous crashed container
kubectl logs -n shopfds fds-service-abc123 --previous
```

### Metrics & Monitoring

If Prometheus/Grafana is deployed:

```bash
# Port-forward Grafana
kubectl port-forward -n shopfds svc/prometheus-grafana 3000:80

# Access Grafana at http://localhost:3000
# Default credentials: admin / prom-operator

# Import dashboards from infrastructure/docker/grafana/dashboards/
```

**Key Metrics to Monitor**:
- FDS evaluation latency (P95 < 50ms)
- API request rate (1,000 TPS target)
- Database connection pool usage
- Redis cache hit rate (> 85%)
- Model inference time
- Error rate (< 1%)

---

## Troubleshooting

### Common Issues

#### 1. Container Won't Start

**Symptoms**: Container keeps restarting

**Diagnosis**:
```bash
# Check container logs
docker logs <container_name>

# Check container exit code
docker inspect <container_name> | grep ExitCode

# Kubernetes
kubectl describe pod <pod_name> -n shopfds
kubectl logs <pod_name> -n shopfds
```

**Common Causes**:
- Missing environment variables
- Database connection failure
- Port already in use
- Insufficient resources

#### 2. Database Connection Failed

**Symptoms**: Backend services can't connect to PostgreSQL

**Solutions**:
```bash
# Verify PostgreSQL is running
docker-compose -f docker-compose.prod.yml ps postgres

# Check PostgreSQL logs
docker-compose -f docker-compose.prod.yml logs postgres

# Test connection manually
docker-compose -f docker-compose.prod.yml exec postgres \
    psql -U shopfds_user -d shopfds_prod -c "SELECT 1;"

# Kubernetes
kubectl exec -it -n shopfds postgres-0 -- \
    psql -U shopfds_user -d shopfds_prod -c "SELECT 1;"
```

#### 3. High Memory Usage

**Symptoms**: OOMKilled errors, slow performance

**Solutions**:
```bash
# Check container resource usage
docker stats

# Kubernetes
kubectl top pods -n shopfds

# Adjust resource limits in docker-compose.prod.yml or k8s manifests
# Increase ML Service memory to 8GB if needed
```

#### 4. FDS Evaluation Slow (> 100ms)

**Diagnosis**:
- Check Redis cache hit rate
- Review database query performance
- Check ML model inference time

**Solutions**:
```bash
# Check Redis stats
docker-compose -f docker-compose.prod.yml exec redis \
    redis-cli INFO stats

# Enable query logging in PostgreSQL
# Optimize slow queries
# Warm up model cache on startup
```

#### 5. Ingress Not Working (Kubernetes)

**Symptoms**: Can't access services via domain

**Solutions**:
```bash
# Check Ingress Controller
kubectl get pods -n ingress-nginx

# Check Ingress resource
kubectl describe ingress shopfds-ingress -n shopfds

# Check service endpoints
kubectl get endpoints -n shopfds

# Test service directly
kubectl port-forward -n shopfds svc/ecommerce-backend 8000:8000
```

---

## Security Checklist

Before going to production, verify:

### Secrets & Credentials

- [ ] Changed all default passwords
- [ ] Generated strong JWT_SECRET (32+ bytes)
- [ ] Configured all external API keys
- [ ] Enabled HTTPS/TLS for all public endpoints
- [ ] Stored secrets in Kubernetes Secrets (not ConfigMap)
- [ ] Used Sealed Secrets or Vault for sensitive data
- [ ] `.env.production` is NOT committed to Git
- [ ] Rotated secrets regularly (90-day cycle)

### Network Security

- [ ] Configured firewall rules (only ports 80, 443 open)
- [ ] Enabled Network Policies in Kubernetes
- [ ] Configured CORS with specific origins
- [ ] Enabled rate limiting (100 req/min)
- [ ] Disabled unused services/ports
- [ ] Internal services only accessible within cluster

### Application Security

- [ ] Reviewed OWASP Top 10 vulnerabilities
- [ ] Enabled PCI-DSS compliance checks
- [ ] Configured Sentry for error tracking
- [ ] Enabled API authentication (JWT)
- [ ] Implemented input validation
- [ ] Sanitized logs (no sensitive data)
- [ ] Enabled CSRF protection

### Database Security

- [ ] Strong database password (16+ bytes)
- [ ] Database only accessible from backend services
- [ ] Enabled SSL/TLS for database connections
- [ ] Regular backups configured (daily)
- [ ] Point-in-time recovery enabled
- [ ] Reviewed user permissions (least privilege)

### Monitoring & Logging

- [ ] Prometheus metrics enabled
- [ ] Grafana dashboards configured
- [ ] Alerts for critical errors
- [ ] Centralized logging (ELK, Loki, etc.)
- [ ] Log retention policy (30 days minimum)
- [ ] Audit logs for admin actions

### Compliance

- [ ] GDPR compliance verified
- [ ] CCPA compliance verified
- [ ] PCI-DSS compliance verified (if handling cards)
- [ ] Data retention policies documented
- [ ] Privacy policy updated
- [ ] Terms of service reviewed

---

## Rollback Procedure

If deployment fails or issues are detected:

### Docker Compose Rollback

```bash
# Stop current deployment
docker-compose -f docker-compose.prod.yml down

# Pull previous version images
docker pull shopfds/ecommerce-backend:v0.9.0
docker pull shopfds/fds-service:v0.9.0
# ... (all services)

# Update VERSION in .env.production
VERSION=v0.9.0

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes Rollback

```bash
# Rollback to previous revision
kubectl rollout undo deployment/ecommerce-backend -n shopfds
kubectl rollout undo deployment/fds-service -n shopfds

# Rollback to specific revision
kubectl rollout undo deployment/ecommerce-backend \
    --to-revision=2 -n shopfds

# Check rollout history
kubectl rollout history deployment/ecommerce-backend -n shopfds

# Verify rollback
kubectl get pods -n shopfds
kubectl rollout status deployment/ecommerce-backend -n shopfds
```

---

## Support & Contact

For deployment issues or questions:

- **Documentation**: https://docs.shopfds.example.com
- **Issues**: https://github.com/your-org/ShopFDS/issues
- **Email**: devops@shopfds.example.com
- **Slack**: #shopfds-deployment

---

**Last Updated**: 2025-11-18
**Version**: 1.0.0
