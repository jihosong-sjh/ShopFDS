# Troubleshooting Guide: Production Infrastructure

**Feature**: 002-production-infra
**Created**: 2025-11-18
**Version**: 1.0

---

## Table of Contents

1. [Windows-Specific Issues](#windows-specific-issues)
2. [PostgreSQL Issues](#postgresql-issues)
3. [Redis Cluster Issues](#redis-cluster-issues)
4. [Celery/RabbitMQ Issues](#celery-rabbitmq-issues)
5. [ELK Stack Issues](#elk-stack-issues)
6. [Docker Issues](#docker-issues)
7. [Network Issues](#network-issues)
8. [Performance Issues](#performance-issues)

---

## Windows-Specific Issues

### Problem: Docker Desktop Not Starting

**Symptoms**: Docker Desktop shows "Starting..." forever or fails to start

**Solution**:
```powershell
# Step 1: Enable WSL 2 (Windows Subsystem for Linux)
wsl --install
wsl --set-default-version 2

# Step 2: Restart your computer

# Step 3: Open Docker Desktop settings
# Ensure "Use WSL 2 based engine" is enabled

# Step 4: If still not working, reset Docker Desktop
# Settings -> Troubleshoot -> Reset to factory defaults
# WARNING: This deletes all containers and images
```

### Problem: Port Conflicts on Windows

**Symptoms**: Error: "Ports are not available: exposing port TCP 0.0.0.0:5432"

**Root Cause**: Windows services or other applications already using the port

**Solution**:
```powershell
# Step 1: Find process using port (Windows)
netstat -ano | findstr :5432
# Output example: TCP 0.0.0.0:5432 0.0.0.0:0 LISTENING 1234

# Step 2: Kill process by PID
taskkill /PID 1234 /F

# Alternative: Change port in docker-compose.yml
# services:
#   postgres-master:
#     ports:
#       - "15432:5432"  # Use 15432 instead of 5432
```

**Common Port Conflicts**:
- 5432 (PostgreSQL) - Often used by local PostgreSQL installation
- 6379 (Redis) - Often used by local Redis installation
- 3000 (Grafana) - Often used by local development servers
- 9200 (Elasticsearch) - May conflict with other search services

### Problem: File Permissions Issues

**Symptoms**: "Permission denied" errors when mounting volumes

**Solution**:
```bash
# Step 1: Ensure Docker Desktop has access to your drive
# Docker Desktop -> Settings -> Resources -> File Sharing
# Add D:\ (or whatever drive your project is on)

# Step 2: Verify Docker can access the directory
docker run --rm -v D:/side-project/ShopFDS:/test alpine ls /test

# Step 3: If still failing, reset Docker Desktop file sharing
# Settings -> Reset -> Reset to factory defaults
# WARNING: Deletes all containers and volumes
```

### Problem: Line Ending Issues (CRLF vs LF)

**Symptoms**:
- Shell scripts fail with "No such file or directory"
- Error: "$'\r': command not found"
- Scripts run on Linux but fail on Windows

**Root Cause**: Windows uses CRLF (`\r\n`) line endings, Linux uses LF (`\n`)

**Solution**:
```bash
# Step 1: Configure Git to use LF for shell scripts
git config --global core.autocrlf input

# Step 2: Convert existing files to LF (using Git Bash)
find infrastructure/scripts -name "*.sh" -exec dos2unix {} \;

# Or using sed (if dos2unix not available)
find infrastructure/scripts -name "*.sh" -exec sed -i 's/\r$//' {} \;

# Step 3: Add .gitattributes to enforce LF
cat >> .gitattributes << EOF
*.sh text eol=lf
*.py text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
EOF

# Step 4: Re-clone repository or refresh files
git rm --cached -r .
git reset --hard
```

### Problem: Slow Docker Performance on Windows

**Symptoms**: Containers take very long to start, builds are slow

**Solution**:
```powershell
# Step 1: Use WSL 2 backend (not Hyper-V)
# Docker Desktop -> Settings -> General -> "Use WSL 2 based engine"

# Step 2: Move project to WSL 2 filesystem for better performance
# Open WSL terminal
wsl
cd ~
git clone https://github.com/your-org/ShopFDS.git
cd ShopFDS

# Step 3: Increase Docker Desktop resources
# Settings -> Resources -> Advanced
# RAM: 8GB minimum (16GB recommended)
# CPUs: 4 minimum (8 recommended)
# Swap: 2GB
# Disk image size: 64GB

# Step 4: Enable file sharing caching
# Add to docker-compose.yml volumes:
volumes:
  - ./services:/app/services:cached
```

---

## PostgreSQL Issues

### Problem: PostgreSQL Replication Not Working

**Symptoms**: `pg_stat_replication` shows 0 rows or "catchup" state

**Root Cause**: Replica cannot connect to master or replication slot not created

**Solution**:
```bash
# Step 1: Check master logs
docker logs shopfds-postgres-master | grep -i replication

# Step 2: Check replica logs
docker logs shopfds-postgres-replica-1 | grep -i replication

# Step 3: Verify replicator user exists
docker exec -it shopfds-postgres-master psql -U shopfds -d shopfds -c "SELECT * FROM pg_user WHERE usename='replicator';"

# Step 4: Recreate replica
docker-compose -f docker-compose.yml down postgres-replica-1
docker volume rm shopfds_postgres-replica-1-data
docker-compose -f docker-compose.yml up -d postgres-replica-1

# Step 5: Verify replication status
docker exec -it shopfds-postgres-master psql -U shopfds -d shopfds -c "SELECT client_addr, state, sync_state, replay_lag FROM pg_stat_replication;"
```

### Problem: PostgreSQL High Replication Lag

**Symptoms**: Replica is 30+ seconds behind master

**Root Cause**: Network latency, heavy write load, or replica hardware issues

**Solution**:
```bash
# Step 1: Check replication lag
docker exec -it shopfds-postgres-master psql -U shopfds -d shopfds -c "SELECT client_addr, replay_lag, write_lag, flush_lag FROM pg_stat_replication;"

# Step 2: Check disk I/O
docker stats --no-stream | grep postgres

# Step 3: Increase WAL sender processes (master only)
# Edit infrastructure/docker/postgres/master.conf
max_wal_senders = 10  # Increase from 5
wal_keep_size = 1GB   # Keep more WAL files

# Step 4: Restart master (WARNING: causes brief downtime)
docker-compose -f docker-compose.yml restart postgres-master

# Step 5: Monitor improvement
watch -n 5 'docker exec -it shopfds-postgres-master psql -U shopfds -d shopfds -c "SELECT replay_lag FROM pg_stat_replication;"'
```

---

## Redis Cluster Issues

### Problem: Redis Cluster Not Forming

**Symptoms**: `cluster info` shows `cluster_state:fail`

**Root Cause**: Nodes cannot communicate or cluster not initialized

**Solution**:
```bash
# Step 1: Check node status
for i in {0..5}; do
  echo "Node $i:"
  docker exec -it shopfds-redis-node-$((i+1)) redis-cli -p $((7000+i)) cluster info | grep cluster_state
done

# Step 2: Delete all Redis data
docker-compose -f docker-compose.yml down redis-node-1 redis-node-2 redis-node-3 redis-node-4 redis-node-5 redis-node-6
docker volume prune -f

# Step 3: Restart all nodes
docker-compose -f docker-compose.yml up -d redis-node-1 redis-node-2 redis-node-3 redis-node-4 redis-node-5 redis-node-6
sleep 10

# Step 4: Recreate cluster
docker exec -it shopfds-redis-node-1 redis-cli --cluster create \
  redis-node-1:7000 redis-node-2:7001 redis-node-3:7002 \
  redis-node-4:7003 redis-node-5:7004 redis-node-6:7005 \
  --cluster-replicas 1 --cluster-yes

# Step 5: Verify cluster health
docker exec -it shopfds-redis-node-1 redis-cli -p 7000 cluster info
# Expected: cluster_state:ok, cluster_slots_assigned:16384
```

### Problem: Redis Cluster Connection from Host Machine (Windows/macOS)

**Symptoms**:
- Python/Node.js Redis Cluster client cannot connect from host machine
- Error: "Redis Cluster cannot be connected. Please provide at least one reachable node: Timeout connecting to server"
- Port is reachable but cluster communication fails

**Root Cause**: Docker containers use internal hostnames (`redis-node-1`, `redis-node-2`, etc.) which are not resolvable from the host machine. When Redis Cluster returns cluster topology, it provides internal Docker hostnames that the host cannot resolve.

**Solution Options**:

**Option A: Run Tests Inside Docker Network** (Recommended)
```bash
# Create a test container in the same network
docker run --rm -it --network docker_redis-cluster \
  -v D:/side-project/ShopFDS:/app \
  python:3.11 bash

# Inside container, install dependencies and run tests
cd /app
pip install redis pytest
pytest tests/infrastructure/test_redis_cluster.py -v
```

**Option B: Add Host Entries** (Windows)
```powershell
# Edit C:\Windows\System32\drivers\etc\hosts as Administrator
# Add these lines:
127.0.0.1 redis-node-1
127.0.0.1 redis-node-2
127.0.0.1 redis-node-3
127.0.0.1 redis-node-4
127.0.0.1 redis-node-5
127.0.0.1 redis-node-6

# Note: This allows host to resolve redis-node-X to localhost
# Restart Docker containers after adding entries
```

**Option C: Use Single Redis Node for Development**
```yaml
# docker-compose.yml - Add single Redis for local development
services:
  redis:
    image: redis:7-alpine
    container_name: shopfds-redis
    ports:
      - "6379:6379"
    command: redis-server --save 60 1 --loglevel notice

# Update application to use single Redis for dev, cluster for prod
# services/*/src/db/redis_connection.py:
import os
if os.getenv("ENVIRONMENT") == "production":
    client = RedisCluster(...)  # Use cluster in prod
else:
    client = Redis(host="localhost", port=6379)  # Use single node in dev
```

**Why cluster-announce-ip Doesn't Work**:
Setting `--cluster-announce-ip 127.0.0.1` in docker-compose.yml causes nodes inside Docker network to try connecting to 127.0.0.1 (themselves) instead of other nodes, preventing cluster formation.

**Production Deployment**: In Kubernetes or cloud environments, use proper DNS/service discovery (e.g., `redis-node-1.default.svc.cluster.local`) which works for both internal and external access.

### Problem: Redis Cluster Connection Timeouts

**Symptoms**: Applications cannot connect to Redis Cluster, timeouts in logs

**Root Cause**: Network issues, firewall, or cluster not fully initialized

**Solution**:
```bash
# Step 1: Test connectivity to each node
for i in {0..5}; do
  echo "Testing node $((i+1)) (port $((7000+i))):"
  nc -zv localhost $((7000+i))
done

# Step 2: Test Redis PING
for i in {0..5}; do
  echo "Node $((i+1)):"
  docker exec -it shopfds-redis-node-$((i+1)) redis-cli -p $((7000+i)) ping
done

# Step 3: Check cluster node communication
docker exec -it shopfds-redis-node-1 redis-cli -p 7000 cluster nodes

# Step 4: Increase socket timeout in application
# Update services/*/src/db/connection.py:
# RedisCluster(
#     startup_nodes=[...],
#     socket_timeout=10,  # Increase from 5
#     socket_connect_timeout=10
# )
```

---

## Celery/RabbitMQ Issues

### Problem: Celery Workers Not Starting

**Symptoms**: `docker ps` shows celery-worker exited

**Root Cause**: RabbitMQ not ready, import errors, or database connection failed

**Solution**:
```bash
# Step 1: Check Celery logs
docker logs shopfds-celery-worker --tail=100

# Step 2: Verify RabbitMQ is running
docker exec -it shopfds-rabbitmq rabbitmqctl status

# Step 3: Check queue status
docker exec -it shopfds-rabbitmq rabbitmqctl list_queues

# Step 4: Test RabbitMQ connection
curl -u admin:${RABBITMQ_DEFAULT_PASS} http://localhost:15672/api/overview

# Step 5: Restart worker
docker-compose -f docker-compose.yml restart celery-worker

# Step 6: If still failing, rebuild image
docker-compose -f docker-compose.yml build celery-worker
docker-compose -f docker-compose.yml up -d celery-worker
```

### Problem: Celery Tasks Stuck in Queue

**Symptoms**: Tasks not being processed, Flower shows tasks pending

**Root Cause**: Workers crashed, deadlock, or insufficient workers

**Solution**:
```bash
# Step 1: Check Flower dashboard
# http://localhost:5555/tasks

# Step 2: Check worker logs for errors
docker logs shopfds-celery-worker | grep -i error

# Step 3: Check active workers
docker exec -it shopfds-celery-worker celery -A celeryconfig inspect active

# Step 4: Check reserved tasks
docker exec -it shopfds-celery-worker celery -A celeryconfig inspect reserved

# Step 5: Purge stuck tasks (WARNING: deletes all pending tasks)
docker exec -it shopfds-celery-worker celery -A celeryconfig purge

# Step 6: Restart workers
docker-compose -f docker-compose.yml restart celery-worker
```

---

## ELK Stack Issues

### Problem: Elasticsearch 7.x "unknown setting xpack.security.enrollment.enabled"

**Symptoms**: Elasticsearch container fails to start with error:
```
java.lang.IllegalArgumentException: unknown setting [xpack.security.enrollment.enabled]
```

**Root Cause**: `xpack.security.enrollment.enabled` is only available in Elasticsearch 8.x, not 7.x

**Solution**:
```bash
# Step 1: Edit elasticsearch.yml
# Remove or comment out the following line:
# xpack.security.enrollment.enabled: false

# Step 2: Restart Elasticsearch
cd infrastructure/docker
docker-compose restart elasticsearch

# Step 3: Verify cluster health
curl http://localhost:9200/_cluster/health?pretty
# Expected: "status":"green"
```

**File to Fix**: `infrastructure/docker/elasticsearch/elasticsearch.yml`

Remove this line:
```yaml
xpack.security.enrollment.enabled: false  # Only for ES 8.x
```

### Problem: Elasticsearch Fails to Start

**Symptoms**: Container keeps restarting, logs show "max virtual memory areas too low"

**Root Cause**: Linux kernel parameter `vm.max_map_count` too low

**Solution**:

**Linux**:
```bash
# Increase vm.max_map_count
sudo sysctl -w vm.max_map_count=262144

# Make permanent
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf

# Restart Elasticsearch
docker-compose -f docker-compose.yml restart elasticsearch
```

**Windows (WSL 2)**:
```powershell
# Open WSL terminal
wsl

# Set vm.max_map_count in WSL
sudo sysctl -w vm.max_map_count=262144

# Make permanent in WSL
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf

# Restart Docker Desktop
# Right-click Docker Desktop tray icon -> Restart
```

**macOS**:
```bash
# macOS uses Docker Desktop's embedded Linux VM
# Screen -> Preferences -> Docker Engine
# Add to JSON config:
{
  "max-virtual-memory": {
    "vm": {
      "max_map_count": 262144
    }
  }
}

# Restart Docker Desktop
```

### Problem: Kibana Shows "Elasticsearch cluster is unavailable"

**Symptoms**: Kibana UI shows connection error

**Root Cause**: Elasticsearch not fully started (can take 1-2 minutes)

**Solution**:
```bash
# Step 1: Wait longer (Elasticsearch takes time to start)
sleep 120

# Step 2: Check Elasticsearch health
curl -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/_cluster/health
# Expected: "status":"yellow" or "green"

# Step 3: Check Elasticsearch logs
docker logs shopfds-elasticsearch --tail=100

# Step 4: Restart Kibana
docker-compose -f docker-compose.yml restart kibana

# Step 5: Verify Kibana logs
docker logs shopfds-kibana --tail=50
```

---

## Docker Issues

### Problem: Docker Daemon Not Responding

**Symptoms**: `docker ps` hangs or shows "Cannot connect to the Docker daemon"

**Solution**:
```bash
# Linux
sudo systemctl restart docker

# Windows/macOS
# Restart Docker Desktop from system tray
```

### Problem: Docker Out of Disk Space

**Symptoms**: Error: "no space left on device"

**Solution**:
```bash
# Check Docker disk usage
docker system df

# Clean up unused images
docker image prune -a

# Clean up unused volumes
docker volume prune

# Clean up everything (WARNING: deletes all stopped containers)
docker system prune -a --volumes

# Increase Docker Desktop disk size
# Settings -> Resources -> Advanced -> Disk image size
```

---

## Network Issues

### Problem: Containers Cannot Communicate

**Symptoms**: Services cannot reach each other (e.g., app cannot connect to database)

**Solution**:
```bash
# Check network
docker network ls

# Inspect network
docker network inspect shopfds-internal

# Test connectivity between containers
docker exec -it shopfds-ecommerce-backend ping shopfds-postgres-master

# Recreate network
docker-compose -f docker-compose.yml down
docker network prune
docker-compose -f docker-compose.yml up -d
```

---

## Performance Issues

### Problem: Slow Query Performance

**Symptoms**: API responses take 5+ seconds

**Solution**:
```bash
# Check slow queries in PostgreSQL
docker exec -it shopfds-postgres-master psql -U shopfds -d shopfds -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Enable query logging
# Edit postgresql.conf:
log_min_duration_statement = 1000  # Log queries > 1 second

# Check Redis cache hit rate
docker exec -it shopfds-redis-node-1 redis-cli -p 7000 info stats | grep keyspace_hits
```

### Problem: High Memory Usage

**Symptoms**: System slows down, OOM errors

**Solution**:
```bash
# Check container memory usage
docker stats --no-stream

# Limit container memory in docker-compose.yml:
services:
  ecommerce-backend:
    mem_limit: 1g
    mem_reservation: 512m

# Restart services
docker-compose -f docker-compose.yml restart
```

---

## Getting Help

If you encounter issues not covered in this guide:

1. **Check Logs**: Always start by checking container logs
   ```bash
   docker logs <container-name> --tail=100
   ```

2. **Search GitHub Issues**: https://github.com/your-org/ShopFDS/issues

3. **Ask in Slack**: #shopfds-dev channel

4. **Create GitHub Issue**: Include:
   - Error message (full stack trace)
   - Docker version: `docker --version`
   - OS and version
   - Steps to reproduce
   - Relevant logs

---

**Version**: 1.0
**Last Updated**: 2025-11-18
**Maintainer**: ShopFDS DevOps Team
