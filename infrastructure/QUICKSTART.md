# ShopFDS Development Environment - Quick Start Guide

This guide will help you set up the complete ShopFDS development environment in under 10 minutes.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (5 minutes)](#quick-start-5-minutes)
3. [Makefile Commands Reference](#makefile-commands-reference)
4. [Service URLs](#service-urls)
5. [Troubleshooting](#troubleshooting)
6. [Advanced Usage](#advanced-usage)

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker Desktop**: Version 20.10+ (includes Docker Compose)
  - Windows: [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
  - Mac: [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
  - Linux: Install Docker Engine + Docker Compose

- **Python 3.11+**: For running backend services locally
  - Windows: [Download Python](https://www.python.org/downloads/)
  - Mac: `brew install python@3.11`
  - Linux: `apt-get install python3.11`

- **Make**: For running automation scripts
  - Windows: `choco install make` or use Git Bash
  - Mac: Pre-installed with Xcode Command Line Tools
  - Linux: `apt-get install make`

- **Git**: For cloning the repository
  - All platforms: [Download Git](https://git-scm.com/downloads)

---

## Quick Start (5 minutes)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/ShopFDS.git
cd ShopFDS
```

### Step 2: Full Environment Setup

```bash
cd infrastructure
make setup
```

This command will:
- Pull all Docker images (PostgreSQL, Redis, RabbitMQ, ELK, Prometheus, Grafana)
- Start infrastructure services
- Initialize Redis Cluster (6 nodes)
- Run database migrations
- Verify all services are healthy

**Expected output:**
```
[SUCCESS] Setup Complete!

Next steps:
  1. Start all services:     cd infrastructure && make dev
  2. Generate seed data:     cd infrastructure && make seed
  3. Run tests:              cd infrastructure && make test
```

**Duration:** 3-5 minutes (depends on internet speed)

### Step 3: Start Development Services

```bash
make dev
```

This starts:
- Backend services (Ecommerce, FDS, ML Service, Admin Dashboard)
- Celery workers for async tasks
- Monitoring tools (Flower, Prometheus, Grafana, Kibana)

**Duration:** 1-2 minutes

### Step 4: Generate Seed Data (Optional)

```bash
make seed
```

This generates:
- **1000 users** (1 admin + 999 customers)
- **500 products** (across 8 categories)
- **10000 orders** (85% normal, 10% suspicious, 5% fraudulent)

**Duration:** 5-10 minutes

---

## Makefile Commands Reference

### Environment Management

| Command | Description | Duration |
|---------|-------------|----------|
| `make help` | Show all available commands | Instant |
| `make setup` | Initial setup (run once) | 3-5 min |
| `make dev` | Start all development services | 1-2 min |
| `make clean` | Stop all services and remove containers | 30 sec |

### Database Management

| Command | Description | Duration |
|---------|-------------|----------|
| `make migrate` | Run database migrations for all services | 10-30 sec |
| `make seed` | Generate seed data (users, products, orders) | 5-10 min |
| `make reset-db` | **DESTRUCTIVE**: Drop all tables and recreate | 30 sec |

### Testing

| Command | Description | Duration |
|---------|-------------|----------|
| `make test` | Run all infrastructure integration tests | 2-3 min |

### Monitoring & Debugging

| Command | Description | Duration |
|---------|-------------|----------|
| `make logs` | View real-time logs from all services | Continuous |
| `make health` | Check health status of all services | 10 sec |

### Docker Management

| Command | Description | Duration |
|---------|-------------|----------|
| `make docker-build` | Build Docker images from scratch | 10-15 min |
| `make docker-pull` | Pull pre-built images from registry | 3-5 min |

---

## Service URLs

Once all services are running, you can access them at:

### API Documentation (Swagger/OpenAPI)

- **Ecommerce Backend**: http://localhost:8000/docs
- **FDS Service**: http://localhost:8001/docs
- **ML Service**: http://localhost:8002/docs
- **Admin Dashboard**: http://localhost:8003/docs

### Monitoring & Management Tools

- **Flower (Celery)**: http://localhost:5555
  - Monitor async tasks (email, batch processing)
  - Default credentials: `admin` / `admin123`

- **Kibana (Logs)**: http://localhost:5601
  - View centralized logs from all services
  - Search and analyze application logs

- **Grafana (Metrics)**: http://localhost:3001
  - Visualize performance metrics
  - Default credentials: `admin` / `admin`

- **Prometheus**: http://localhost:9090
  - Raw metrics collection
  - Query and alert on system metrics

### Database Access

- **PostgreSQL Master**: `localhost:5432`
  - Database: `shopfds_db`
  - User: `shopfds_user`
  - Password: `shopfds_password`

- **PostgreSQL Replica**: `localhost:5433`
  - Read-only access

- **Redis Cluster**: `localhost:7000-7005`
  - 6 nodes (3 masters + 3 replicas)

- **RabbitMQ Management**: http://localhost:15672
  - Default credentials: `guest` / `guest`

---

## Troubleshooting

### Issue: Docker Daemon Not Running

**Error:**
```
ERROR: Cannot connect to the Docker daemon
```

**Solution:**
```bash
# Start Docker Desktop (Windows/Mac)
# Or start Docker service (Linux)
sudo systemctl start docker
```

### Issue: Port Already in Use

**Error:**
```
Error: Bind for 0.0.0.0:8000 failed: port is already allocated
```

**Solution:**
```bash
# Find the process using the port
netstat -an | grep 8000  # Unix/Mac
netstat -an | findstr 8000  # Windows

# Kill the process or change the port in docker-compose.yml
```

### Issue: PostgreSQL Migration Failed

**Error:**
```
alembic.util.exc.CommandError: Can't locate revision identified by 'xxx'
```

**Solution:**
```bash
# Reset database and re-run migrations
cd infrastructure
make reset-db
make migrate
```

### Issue: Redis Cluster Initialization Failed

**Error:**
```
[FAIL] Redis Cluster initialization failed
```

**Solution:**
```bash
# Manually initialize Redis Cluster
docker exec -it shopfds-redis-node-1 redis-cli --cluster create \
  redis-node-1:6379 redis-node-2:6379 redis-node-3:6379 \
  redis-node-4:6379 redis-node-5:6379 redis-node-6:6379 \
  --cluster-replicas 1
```

### Issue: Services Not Starting

**Solution:**
```bash
# Check Docker resources
docker system df

# Clean up unused resources
docker system prune -f

# Restart Docker Desktop
```

### Issue: Seed Data Generation Slow

**Solution:**
```bash
# Generate fewer records
python infrastructure/scripts/seed-data.py --users 100 --orders 1000 --products 50

# Or run in background
nohup python infrastructure/scripts/seed-data.py &
```

---

## Advanced Usage

### Custom Seed Data

```bash
# Generate specific amounts
python infrastructure/scripts/seed-data.py \
  --users 500 \
  --products 200 \
  --orders 5000 \
  --reviews 2000

# Append data (idempotent mode)
python infrastructure/scripts/seed-data.py --append
```

### Manual Database Migration

```bash
# Ecommerce service
cd services/ecommerce/backend
alembic revision --autogenerate -m "Add new table"
alembic upgrade head
alembic downgrade -1

# FDS service
cd services/fds
alembic upgrade head
```

### Monitoring Specific Services

```bash
# View logs for a single service
docker-compose logs -f ecommerce-backend

# View logs for multiple services
docker-compose logs -f ecommerce-backend fds

# View last 100 lines
docker-compose logs --tail=100 ecommerce-backend
```

### Running Individual Tests

```bash
# Redis Cluster tests
cd ..  # Back to project root
pytest tests/infrastructure/test_redis_cluster.py -v

# PostgreSQL replication tests
pytest tests/infrastructure/test_postgres_replication.py -v

# Celery task tests
pytest tests/infrastructure/test_celery_tasks.py -v

# ELK logging tests
pytest tests/infrastructure/test_elk_logging.py -v
```

### Performance Testing

```bash
# FDS performance benchmark
cd services/fds
pytest tests/performance -v --benchmark

# Load testing with locust
locust -f tests/load/locustfile.py --host=http://localhost:8001
```

---

## Next Steps

Once your environment is set up:

1. **Explore API Documentation**: Visit http://localhost:8000/docs
2. **Create a Test Order**: Use Swagger UI to test the order flow
3. **Monitor FDS Evaluation**: Check http://localhost:5601 for logs
4. **View Metrics**: Open Grafana at http://localhost:3001

For more detailed documentation, see:
- **API Documentation**: `/docs/api/`
- **Architecture Diagrams**: `/docs/architecture/`
- **Development Guidelines**: `/CLAUDE.md`

---

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section above
2. View service logs: `make logs`
3. Check service health: `make health`
4. Report issues: [GitHub Issues](https://github.com/yourusername/ShopFDS/issues)

---

**Last Updated:** 2025-11-18
**Version:** 1.0
