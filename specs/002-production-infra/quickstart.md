# Quick Start Guide: Production Infrastructure

**Feature**: 002-production-infra
**Created**: 2025-11-17
**Version**: 1.0

---

## Overview

This guide helps you set up the complete ShopFDS production infrastructure on your local machine using Docker Compose. You'll run:
- PostgreSQL Master + 2 Replicas (streaming replication)
- Redis Cluster (6 nodes: 3 masters + 3 replicas)
- RabbitMQ (message broker for Celery)
- Celery Workers + Beat (async task processing)
- Elasticsearch + Logstash + Kibana (centralized logging)
- Prometheus + Alertmanager + Grafana (monitoring and alerting)
- Flower (Celery task monitoring)

**Total containers**: ~20 containers
**Estimated setup time**: 30 minutes (first time)
**Disk space required**: ~10GB

---

## Prerequisites

### System Requirements

- **OS**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **RAM**: 16GB minimum (32GB recommended)
- **Disk**: 20GB free space
- **CPU**: 4 cores minimum (8 cores recommended)

### Software Requirements

| Software | Version | Installation |
|----------|---------|--------------|
| **Docker** | 20.10+ | [docker.com/get-started](https://www.docker.com/get-started) |
| **Docker Compose** | 2.0+ | Included with Docker Desktop |
| **Git** | 2.30+ | [git-scm.com/downloads](https://git-scm.com/downloads) |
| **Python** | 3.11+ | [python.org/downloads](https://www.python.org/downloads/) (for local dev only) |

### Verify Installation

```bash
# Check Docker
docker --version
# Expected: Docker version 20.10.0 or higher

# Check Docker Compose
docker-compose --version
# Expected: Docker Compose version 2.0.0 or higher

# Check Git
git --version
# Expected: git version 2.30.0 or higher
```

---

## Step 1: Clone Repository

```bash
# Clone the repository
git clone https://github.com/your-org/ShopFDS.git
cd ShopFDS

# Checkout production-infra branch (or main if merged)
git checkout 002-production-infra

# Verify you're in the correct directory
ls -la
# Expected: You should see: infrastructure/, services/, specs/, README.md
```

---

## Step 2: Environment Setup

### Create Environment Files

```bash
# Create .env file from template
cp infrastructure/docker/.env.example infrastructure/docker/.env

# Edit .env file with your credentials
nano infrastructure/docker/.env
```

### Required Environment Variables

```bash
# infrastructure/docker/.env

# PostgreSQL
POSTGRES_USER=shopfds
POSTGRES_PASSWORD=secure_password_here
POSTGRES_DB=shopfds
REPLICATOR_PASSWORD=replicator_password_here

# Redis Cluster
REDIS_PASSWORD=redis_password_here

# RabbitMQ
RABBITMQ_DEFAULT_USER=admin
RABBITMQ_DEFAULT_PASS=rabbitmq_password_here

# Elasticsearch
ELASTIC_PASSWORD=elastic_password_here

# Prometheus Alertmanager
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR_WEBHOOK_URL
SMTP_PASSWORD=your_gmail_app_password_here

# Flower (Celery Monitoring)
FLOWER_BASIC_AUTH=admin:flower_password_here

# JWT Secret (for API authentication)
JWT_SECRET_KEY=your_jwt_secret_key_here
```

**Security Note**: Never commit `.env` file to Git. It's already in `.gitignore`.

---

## Step 3: Build Docker Images

```bash
# Navigate to infrastructure directory
cd infrastructure/docker

# Build all service images (this may take 10-15 minutes first time)
docker-compose -f docker-compose.dev.yml build

# Expected output: Successfully built images for all services
```

---

## Step 4: Start Infrastructure Services

### Start Core Services First

```bash
# Start PostgreSQL Master + Replicas
docker-compose -f docker-compose.dev.yml up -d postgres-master postgres-replica-1 postgres-replica-2

# Wait 30 seconds for replication to initialize
sleep 30

# Verify replication status
docker exec -it shopfds-postgres-master psql -U shopfds -d shopfds -c "SELECT * FROM pg_stat_replication;"
# Expected: 2 rows showing replica-1 and replica-2 in "streaming" state

# Start Redis Cluster
docker-compose -f docker-compose.dev.yml up -d redis-node-1 redis-node-2 redis-node-3 redis-node-4 redis-node-5 redis-node-6

# Wait 10 seconds
sleep 10

# Create Redis Cluster (one-time setup)
docker exec -it shopfds-redis-node-1 redis-cli --cluster create \
  redis-node-1:7000 \
  redis-node-2:7001 \
  redis-node-3:7002 \
  redis-node-4:7003 \
  redis-node-5:7004 \
  redis-node-6:7005 \
  --cluster-replicas 1 \
  --cluster-yes

# Verify cluster status
docker exec -it shopfds-redis-node-1 redis-cli -p 7000 cluster info
# Expected: cluster_state:ok, cluster_slots_assigned:16384
```

### Start Message Queue and Workers

```bash
# Start RabbitMQ
docker-compose -f docker-compose.dev.yml up -d rabbitmq

# Start Celery Workers and Beat
docker-compose -f docker-compose.dev.yml up -d celery-worker celery-beat

# Start Flower (Celery monitoring)
docker-compose -f docker-compose.dev.yml up -d flower
```

### Start Logging Stack

```bash
# Start Elasticsearch
docker-compose -f docker-compose.dev.yml up -d elasticsearch

# Wait 60 seconds for Elasticsearch to start (first time can be slow)
sleep 60

# Verify Elasticsearch is running
curl -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/_cluster/health
# Expected: "status":"yellow" or "green"

# Start Logstash
docker-compose -f docker-compose.dev.yml up -d logstash

# Start Kibana
docker-compose -f docker-compose.dev.yml up -d kibana
```

### Start Monitoring Stack

```bash
# Start Prometheus
docker-compose -f docker-compose.dev.yml up -d prometheus

# Start Alertmanager
docker-compose -f docker-compose.dev.yml up -d alertmanager

# Start Grafana
docker-compose -f docker-compose.dev.yml up -d grafana
```

---

## Step 5: Start Application Services

```bash
# Start all backend services
docker-compose -f docker-compose.dev.yml up -d ecommerce-backend fds-service ml-service admin-dashboard-backend

# Start frontend services (optional, for local UI testing)
docker-compose -f docker-compose.dev.yml up -d ecommerce-frontend admin-dashboard-frontend
```

---

## Step 6: Load Seed Data

```bash
# Run database migrations
docker exec -it shopfds-ecommerce-backend alembic upgrade head

# Load seed data (sample products, users, etc.)
docker exec -it shopfds-ecommerce-backend python scripts/seed_data.py

# Verify data loaded
docker exec -it shopfds-postgres-master psql -U shopfds -d shopfds -c "SELECT COUNT(*) FROM products;"
# Expected: 50 products
```

---

## Step 7: Verify All Services

### Check Container Health

```bash
# Check all running containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Expected: All containers should show "Up" status
```

### Test Service Endpoints

```bash
# Test Ecommerce Backend Health Check
curl http://localhost:8000/health
# Expected: {"status":"healthy",...}

# Test FDS Service Health Check
curl http://localhost:8001/health
# Expected: {"status":"healthy",...}

# Test ML Service Health Check
curl http://localhost:8002/health
# Expected: {"status":"healthy",...}

# Test Admin Dashboard Backend Health Check
curl http://localhost:8003/health
# Expected: {"status":"healthy",...}
```

---

## Step 8: Access Monitoring Dashboards

### Flower (Celery Tasks)

- **URL**: http://localhost:5555
- **Auth**: `admin` / `flower_password_here` (from .env)
- **What to check**:
  - Active workers: 3-5 workers
  - Task success rate: >95%
  - No failed tasks on first startup

### Kibana (Logs)

- **URL**: http://localhost:5601
- **Auth**: `elastic` / `elastic_password_here` (from .env)
- **Setup**:
  1. Click "Discover" in left menu
  2. Create index pattern: `shopfds-*`
  3. Select `@timestamp` as time field
  4. Click "Create index pattern"
  5. Go back to "Discover" to view logs

### Prometheus (Metrics)

- **URL**: http://localhost:9090
- **No auth required** (local dev only)
- **What to check**:
  - Targets: http://localhost:9090/targets (all should be "UP")
  - Graph: Enter `up` query and click "Execute" (all values should be 1)

### Grafana (Dashboards)

- **URL**: http://localhost:3000
- **Auth**: `admin` / `admin` (change on first login)
- **Setup**:
  1. Add Prometheus data source: http://prometheus:9090
  2. Import dashboards: `/infrastructure/grafana/dashboards/*.json`

### Alertmanager (Alerts)

- **URL**: http://localhost:9093
- **No auth required** (local dev only)
- **What to check**:
  - Should have 0 firing alerts on fresh install

### RabbitMQ Management

- **URL**: http://localhost:15672
- **Auth**: `admin` / `rabbitmq_password_here` (from .env)
- **What to check**:
  - Queues: `default`, `email`, `fds` queues created
  - Connections: 3-5 Celery worker connections

---

## Step 9: Run Integration Tests

```bash
# Run health check tests
docker exec -it shopfds-ecommerce-backend pytest tests/integration/test_health_check.py -v

# Run PostgreSQL replication tests
docker exec -it shopfds-ecommerce-backend pytest tests/integration/test_replication.py -v

# Run Redis Cluster tests
docker exec -it shopfds-ecommerce-backend pytest tests/integration/test_redis_cluster.py -v

# Run Celery task tests
docker exec -it shopfds-ecommerce-backend pytest tests/integration/test_celery_tasks.py -v

# All tests should pass (green checkmarks)
```

---

## Common Commands

### Start All Services

```bash
cd infrastructure/docker
docker-compose -f docker-compose.dev.yml up -d
```

### Stop All Services

```bash
docker-compose -f docker-compose.dev.yml down
```

### Stop and Remove All Data (Clean Slate)

```bash
docker-compose -f docker-compose.dev.yml down -v
# WARNING: This deletes all databases, logs, and metrics
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.dev.yml logs -f

# Specific service
docker-compose -f docker-compose.dev.yml logs -f ecommerce-backend

# Last 100 lines
docker-compose -f docker-compose.dev.yml logs --tail=100 ecommerce-backend
```

### Restart Single Service

```bash
docker-compose -f docker-compose.dev.yml restart ecommerce-backend
```

### Execute Command in Container

```bash
# Open bash shell
docker exec -it shopfds-ecommerce-backend bash

# Run Python script
docker exec -it shopfds-ecommerce-backend python scripts/check_db.py

# Run database query
docker exec -it shopfds-postgres-master psql -U shopfds -d shopfds
```

---

## Troubleshooting

### Problem: PostgreSQL Replication Not Working

**Symptoms**: `pg_stat_replication` shows 0 rows or "catchup" state

**Solution**:
```bash
# Check master logs
docker logs shopfds-postgres-master | grep -i replication

# Check replica logs
docker logs shopfds-postgres-replica-1 | grep -i replication

# Recreate replica
docker-compose -f docker-compose.dev.yml down postgres-replica-1
docker volume rm shopfds_postgres-replica-1-data
docker-compose -f docker-compose.dev.yml up -d postgres-replica-1
```

### Problem: Redis Cluster Not Forming

**Symptoms**: `cluster info` shows `cluster_state:fail`

**Solution**:
```bash
# Delete all Redis data
docker-compose -f docker-compose.dev.yml down redis-node-1 redis-node-2 redis-node-3 redis-node-4 redis-node-5 redis-node-6
docker volume prune -f

# Restart and recreate cluster
docker-compose -f docker-compose.dev.yml up -d redis-node-1 redis-node-2 redis-node-3 redis-node-4 redis-node-5 redis-node-6
sleep 10

docker exec -it shopfds-redis-node-1 redis-cli --cluster create \
  redis-node-1:7000 redis-node-2:7001 redis-node-3:7002 \
  redis-node-4:7003 redis-node-5:7004 redis-node-6:7005 \
  --cluster-replicas 1 --cluster-yes
```

### Problem: Elasticsearch Fails to Start

**Symptoms**: Container keeps restarting, logs show "max virtual memory areas too low"

**Solution (Linux only)**:
```bash
# Increase vm.max_map_count
sudo sysctl -w vm.max_map_count=262144

# Make permanent
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf

# Restart Elasticsearch
docker-compose -f docker-compose.dev.yml restart elasticsearch
```

### Problem: Celery Workers Not Starting

**Symptoms**: `docker ps` shows celery-worker exited

**Solution**:
```bash
# Check logs for errors
docker logs shopfds-celery-worker

# Common issues:
# 1. RabbitMQ not ready -> wait 30s and restart
# 2. Import error in tasks -> fix code and rebuild
# 3. Database connection failed -> check POSTGRES_HOST in .env

# Restart worker
docker-compose -f docker-compose.dev.yml restart celery-worker
```

### Problem: Kibana Shows "Elasticsearch cluster is unavailable"

**Symptoms**: Kibana UI shows connection error

**Solution**:
```bash
# Wait longer (Elasticsearch takes 1-2 minutes to fully start)
sleep 120

# Check Elasticsearch health
curl -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/_cluster/health

# Restart Kibana
docker-compose -f docker-compose.dev.yml restart kibana
```

### Problem: Port Already in Use

**Symptoms**: Error: "bind: address already in use"

**Solution**:
```bash
# Find process using port (example: 5432)
lsof -i :5432

# Kill process
kill -9 <PID>

# Or change port in docker-compose.dev.yml
ports:
  - "15432:5432"  # Use 15432 instead of 5432
```

---

## Performance Tips

### Speed Up Docker Builds

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Use build cache
docker-compose -f docker-compose.dev.yml build --parallel
```

### Reduce Memory Usage

```bash
# Stop unused services
docker-compose -f docker-compose.dev.yml stop ecommerce-frontend admin-dashboard-frontend

# Limit container memory
# Add to docker-compose.dev.yml:
services:
  ecommerce-backend:
    mem_limit: 1g
    mem_reservation: 512m
```

### Speed Up Test Execution

```bash
# Run tests in parallel
docker exec -it shopfds-ecommerce-backend pytest -n 4 tests/

# Skip slow tests
docker exec -it shopfds-ecommerce-backend pytest -m "not slow" tests/
```

---

## Next Steps

1. **Configure Slack Notifications**: Update `SLACK_WEBHOOK_URL` in `.env`
2. **Configure Email Alerts**: Update `SMTP_PASSWORD` in `.env`
3. **Import Grafana Dashboards**: Navigate to Grafana and import pre-built dashboards
4. **Load Production Data Snapshot**: Import anonymized production data for realistic testing
5. **Run Load Tests**: Use Locust or JMeter to simulate production traffic
6. **Review Alert Rules**: Check Prometheus alert rules in `infrastructure/docker/prometheus/rules/`

---

## Useful Links

- **Documentation**: `docs/`
- **API Docs (Ecommerce)**: http://localhost:8000/docs
- **API Docs (FDS)**: http://localhost:8001/docs
- **API Docs (ML Service)**: http://localhost:8002/docs
- **API Docs (Admin Dashboard)**: http://localhost:8003/docs
- **Slack Support**: #shopfds-dev channel
- **Issue Tracker**: https://github.com/your-org/ShopFDS/issues

---

**Version**: 1.0
**Last Updated**: 2025-11-17
**Maintainer**: ShopFDS DevOps Team
