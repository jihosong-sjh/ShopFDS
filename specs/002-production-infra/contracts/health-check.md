# Health Check API Contract

**Feature**: 002-production-infra
**Component**: All Backend Services
**Created**: 2025-11-17
**Version**: 1.0

---

## Overview

Unified health check endpoint for all ShopFDS backend services. Used by:
- Kubernetes liveness/readiness probes
- Load balancers (Nginx, AWS ALB)
- Monitoring systems (Prometheus, Grafana)
- CI/CD pipelines (deployment validation)

---

## Endpoint

### GET /health

Returns the overall health status of the service and its dependencies.

**URL**: `/health`
**Method**: `GET`
**Authentication**: None (public endpoint)
**Rate Limit**: None (health checks should not be rate-limited)

---

## Response Format

### Success (200 OK)

All systems operational.

```json
{
  "status": "healthy",
  "timestamp": "2025-11-17T12:00:00.123456Z",
  "service": "ecommerce-backend",
  "version": "1.2.3",
  "uptime_seconds": 86400,
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 5.2,
      "details": {
        "connection_pool": {
          "active": 5,
          "idle": 15,
          "max": 20
        },
        "replica_lag_seconds": 0.8
      }
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1.3,
      "details": {
        "cluster_nodes": 6,
        "cluster_state": "ok",
        "used_memory_mb": 512,
        "max_memory_mb": 2048
      }
    },
    "disk": {
      "status": "healthy",
      "details": {
        "total_gb": 100,
        "available_gb": 60,
        "usage_percent": 40
      }
    }
  }
}
```

### Degraded (200 OK)

Service is operational but some non-critical dependencies are unhealthy.

```json
{
  "status": "degraded",
  "timestamp": "2025-11-17T12:00:00.123456Z",
  "service": "fds",
  "version": "1.0.5",
  "uptime_seconds": 3600,
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 8.1
    },
    "redis": {
      "status": "unhealthy",
      "error": "Connection timeout after 5s",
      "last_success": "2025-11-17T11:55:00Z"
    },
    "disk": {
      "status": "healthy",
      "details": {
        "total_gb": 50,
        "available_gb": 10,
        "usage_percent": 80
      }
    }
  },
  "warnings": [
    "Redis connection failed - using fallback to database",
    "Disk usage at 80% - cleanup recommended"
  ]
}
```

### Unhealthy (503 Service Unavailable)

Critical dependency is down. Service cannot handle requests.

```json
{
  "status": "unhealthy",
  "timestamp": "2025-11-17T12:00:00.123456Z",
  "service": "ml-service",
  "version": "2.1.0",
  "uptime_seconds": 120,
  "checks": {
    "database": {
      "status": "unhealthy",
      "error": "FATAL: database \"shopfds\" does not exist",
      "last_success": null
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 2.1
    },
    "disk": {
      "status": "healthy",
      "details": {
        "total_gb": 200,
        "available_gb": 150,
        "usage_percent": 25
      }
    }
  },
  "errors": [
    "Database connection failed - service cannot start",
    "Missing required tables: users, transactions"
  ]
}
```

---

## Response Fields

### Root Level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | String | Yes | Overall health: `healthy`, `degraded`, `unhealthy` |
| `timestamp` | String (ISO8601) | Yes | UTC timestamp of health check |
| `service` | String | Yes | Service identifier (e.g., "ecommerce-backend") |
| `version` | String | Yes | Semantic version (e.g., "1.2.3") |
| `uptime_seconds` | Integer | Yes | Seconds since service started |
| `checks` | Object | Yes | Individual dependency health checks |
| `warnings` | Array[String] | No | Non-critical issues (only for `degraded` status) |
| `errors` | Array[String] | No | Critical issues (only for `unhealthy` status) |

### checks.{dependency}

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | String | Yes | Health status: `healthy`, `unhealthy` |
| `latency_ms` | Float | No | Response time for health check (milliseconds) |
| `error` | String | No | Error message (only for `unhealthy`) |
| `last_success` | String (ISO8601) | No | Last successful check timestamp |
| `details` | Object | No | Dependency-specific metadata |

---

## Health Check Logic

### Database Check

```python
async def check_database() -> dict:
    """Check PostgreSQL connection and query performance."""
    try:
        start = time.time()
        # Execute simple query
        await db.execute(text("SELECT 1"))
        latency_ms = (time.time() - start) * 1000

        # Check connection pool
        pool_stats = db.get_pool_stats()

        # Check replica lag (if applicable)
        replica_lag = await get_replica_lag()

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "details": {
                "connection_pool": {
                    "active": pool_stats.active,
                    "idle": pool_stats.idle,
                    "max": pool_stats.max
                },
                "replica_lag_seconds": replica_lag
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_success": None
        }
```

### Redis Check

```python
async def check_redis() -> dict:
    """Check Redis Cluster connection and memory usage."""
    try:
        start = time.time()
        # PING command
        await redis.ping()
        latency_ms = (time.time() - start) * 1000

        # Get cluster info
        cluster_info = await redis.cluster_info()
        memory_info = await redis.info("memory")

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "details": {
                "cluster_nodes": cluster_info.get("cluster_known_nodes"),
                "cluster_state": cluster_info.get("cluster_state"),
                "used_memory_mb": memory_info.get("used_memory") / 1024 / 1024,
                "max_memory_mb": memory_info.get("maxmemory") / 1024 / 1024
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_success": get_last_redis_success()
        }
```

### Disk Check

```python
import shutil

async def check_disk() -> dict:
    """Check disk space availability."""
    try:
        total, used, free = shutil.disk_usage("/")
        usage_percent = (used / total) * 100

        status = "healthy" if usage_percent < 85 else "unhealthy"

        return {
            "status": status,
            "details": {
                "total_gb": round(total / 1024 / 1024 / 1024, 2),
                "available_gb": round(free / 1024 / 1024 / 1024, 2),
                "usage_percent": round(usage_percent, 2)
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

---

## Overall Status Determination

```python
def determine_overall_status(checks: dict) -> str:
    """
    Determine overall health status based on dependency checks.

    Rules:
    - All checks healthy -> "healthy"
    - Any critical check unhealthy -> "unhealthy"
    - Only non-critical checks unhealthy -> "degraded"
    """
    critical_deps = ["database"]  # Critical dependencies
    optional_deps = ["redis", "disk"]  # Optional dependencies

    # Check critical dependencies
    for dep in critical_deps:
        if checks.get(dep, {}).get("status") == "unhealthy":
            return "unhealthy"

    # Check optional dependencies
    for dep in optional_deps:
        if checks.get(dep, {}).get("status") == "unhealthy":
            return "degraded"

    return "healthy"
```

---

## HTTP Status Codes

| Status Code | Condition | Description |
|-------------|-----------|-------------|
| **200 OK** | `healthy` or `degraded` | Service is operational (may have warnings) |
| **503 Service Unavailable** | `unhealthy` | Critical dependency is down, service cannot handle requests |
| **500 Internal Server Error** | Exception | Health check itself failed (bug in health check code) |

---

## Kubernetes Integration

### Liveness Probe

Determines if the container should be restarted.

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
    scheme: HTTP
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  successThreshold: 1
  failureThreshold: 3
```

**Logic**:
- If `/health` returns 503 or times out 3 times in a row, restart container
- Allow 30s for service to start before first check

### Readiness Probe

Determines if the container should receive traffic.

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
    scheme: HTTP
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  successThreshold: 1
  failureThreshold: 2
```

**Logic**:
- If `/health` returns 503 or times out 2 times in a row, remove from load balancer
- Check every 5s (more frequent than liveness)

---

## Prometheus Integration

### Custom Metrics

Health check endpoint should also expose metrics for Prometheus scraping.

```python
from prometheus_client import Gauge

# Health status metrics (1=healthy, 0=unhealthy)
health_status = Gauge('health_check_status', 'Service health status', ['service', 'dependency'])
health_latency = Gauge('health_check_latency_ms', 'Health check latency', ['dependency'])

@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "disk": await check_disk()
    }

    # Update Prometheus metrics
    for dep, result in checks.items():
        status_value = 1 if result["status"] == "healthy" else 0
        health_status.labels(service="ecommerce-backend", dependency=dep).set(status_value)

        if "latency_ms" in result:
            health_latency.labels(dependency=dep).set(result["latency_ms"])

    overall_status = determine_overall_status(checks)
    # ... return response
```

---

## Service-Specific Checks

### Ecommerce Backend

Additional checks:
- Payment gateway connectivity (optional, degraded if fails)
- S3/blob storage access (optional)

### FDS Service

Additional checks:
- ML model loaded in memory
- CTI API connectivity (optional)

### ML Service

Additional checks:
- Model artifact storage (S3/MinIO)
- GPU availability (if applicable)

### Admin Dashboard Backend

Additional checks:
- Same as Ecommerce Backend (shared dependencies)

---

## Examples

### cURL

```bash
# Check health
curl http://localhost:8000/health

# With timeout
curl --max-time 5 http://localhost:8000/health

# Pretty print JSON
curl -s http://localhost:8000/health | jq
```

### Python

```python
import requests

response = requests.get("http://localhost:8000/health", timeout=5)
health = response.json()

if health["status"] == "healthy":
    print("[OK] Service is healthy")
elif health["status"] == "degraded":
    print(f"[WARNING] Service degraded: {health.get('warnings')}")
else:
    print(f"[FAIL] Service unhealthy: {health.get('errors')}")
    exit(1)
```

### Docker Compose Healthcheck

```yaml
services:
  ecommerce-backend:
    image: shopfds/ecommerce-backend:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## Performance Requirements

- **Response Time**: < 100ms (P95)
- **Success Rate**: > 99.9%
- **No Database Load**: Health check should not impact production traffic
- **Caching**: Cache dependency status for 5s to reduce overhead

---

## Security Considerations

- **No Authentication**: Health check must be publicly accessible (load balancers need it)
- **No Sensitive Data**: Do not expose database passwords, API keys, or PII
- **Rate Limiting**: Do not rate-limit health checks (breaks Kubernetes probes)
- **Error Messages**: Generic errors only (do not leak internal details)

---

## Testing

### Unit Test

```python
@pytest.mark.asyncio
async def test_health_check_healthy():
    response = await client.get("/health")
    assert response.status_code == 200

    health = response.json()
    assert health["status"] == "healthy"
    assert "database" in health["checks"]
    assert health["checks"]["database"]["status"] == "healthy"
```

### Integration Test

```python
@pytest.mark.asyncio
async def test_health_check_database_down(mock_db):
    # Simulate database failure
    mock_db.side_effect = Exception("Connection refused")

    response = await client.get("/health")
    assert response.status_code == 503

    health = response.json()
    assert health["status"] == "unhealthy"
    assert "database" in health["errors"][0]
```

---

## Troubleshooting

### Health Check Always Returns 503

**Possible Causes**:
1. Database not initialized (missing tables)
2. Database credentials incorrect
3. Network connectivity issues
4. Firewall blocking PostgreSQL port (5432)

**Debug Steps**:
```bash
# Check database connection manually
docker exec -it shopfds-ecommerce-backend psql -h postgres -U shopfds -d shopfds -c "SELECT 1"

# Check service logs
docker logs shopfds-ecommerce-backend | grep -i "health"

# Check network connectivity
docker exec -it shopfds-ecommerce-backend ping postgres
```

### Health Check Times Out

**Possible Causes**:
1. Slow database query (> 5s)
2. Redis connection hanging
3. Disk I/O bottleneck

**Debug Steps**:
```bash
# Increase health check timeout in Kubernetes
timeoutSeconds: 10  # Increase from 5 to 10

# Check database performance
docker exec -it postgres psql -U shopfds -c "SELECT * FROM pg_stat_activity WHERE wait_event IS NOT NULL;"

# Check Redis latency
docker exec -it redis redis-cli --latency
```

---

**Version**: 1.0
**Last Updated**: 2025-11-17
**Status**: Ready for Implementation
