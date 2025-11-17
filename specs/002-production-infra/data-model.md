# Data Model: Production Infrastructure

**Feature**: 002-production-infra
**Phase**: Phase 1 - Design & Contracts
**Created**: 2025-11-17
**Status**: Draft

---

## Overview

This document defines the data models required for production infrastructure components:
- PostgreSQL replication monitoring
- Redis Cluster blacklist management
- Celery task logging
- Elasticsearch log indexing
- Prometheus alert configuration

---

## 1. ReplicationStatus (PostgreSQL)

Tracks PostgreSQL streaming replication health between Master and Replica nodes.

### Entity Definition

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | UUID | No | `uuid4()` | Primary key |
| `replica_name` | String(100) | No | - | Application name from pg_stat_replication |
| `client_addr` | String(50) | No | - | Replica IP address |
| `state` | Enum | No | `'unknown'` | Replication state: streaming, catchup, unknown |
| `write_lag_seconds` | Float | Yes | `NULL` | Master write to replica write lag |
| `flush_lag_seconds` | Float | Yes | `NULL` | Master write to replica flush lag |
| `replay_lag_seconds` | Float | Yes | `NULL` | Master write to replica replay lag (most important) |
| `lag_bytes` | BigInteger | Yes | `NULL` | Bytes behind master (LSN diff) |
| `sync_state` | Enum | No | `'async'` | Synchronization state: async, sync, quorum |
| `is_healthy` | Boolean | No | `False` | True if state=streaming and replay_lag < 5s |
| `checked_at` | DateTime | No | `utcnow()` | Timestamp of last health check |
| `created_at` | DateTime | No | `utcnow()` | Record creation timestamp |

### Indexes

```sql
CREATE INDEX idx_replication_status_replica_name ON replication_status(replica_name);
CREATE INDEX idx_replication_status_checked_at ON replication_status(checked_at DESC);
CREATE INDEX idx_replication_status_healthy ON replication_status(is_healthy);
```

### Constraints

- `replica_name` must be unique
- `replay_lag_seconds >= 0` (cannot be negative)
- `lag_bytes >= 0`

### Sample Data

```python
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "replica_name": "replica-node-1",
    "client_addr": "10.0.1.10",
    "state": "streaming",
    "write_lag_seconds": 0.05,
    "flush_lag_seconds": 0.08,
    "replay_lag_seconds": 0.12,
    "lag_bytes": 1024,
    "sync_state": "async",
    "is_healthy": True,
    "checked_at": "2025-11-17T12:00:00Z",
    "created_at": "2025-11-17T10:00:00Z"
}
```

---

## 2. BlacklistEntry (Redis Cluster)

Stores blacklisted IPs, card BINs, and email domains in Redis Cluster with TTL.

### Entity Definition (Redis Hash)

| Field | Type | TTL | Description |
|-------|------|-----|-------------|
| `key` | String | Varies | Redis key: `blacklist:{type}:{value}` |
| `type` | String | - | Blacklist type: ip, card_bin, email_domain |
| `value` | String | - | Actual value (e.g., "192.168.1.1") |
| `threat_level` | Enum | - | temporary, fraud, permanent, stolen_card, suspicious_email |
| `reason` | String | - | Human-readable reason for blocking |
| `added_at` | ISO8601 | - | UTC timestamp when added |
| `added_by` | String | - | User ID or system that added entry |
| `ttl` | Integer | Varies | Seconds until expiration (NULL for permanent) |

### TTL Strategy

| Threat Level | TTL (seconds) | Duration | Use Case |
|--------------|---------------|----------|----------|
| `temporary` | 3,600 | 1 hour | Suspicious IP (VPN, public WiFi) |
| `fraud` | 604,800 | 7 days | Past fraud transaction IP |
| `permanent` | None | Infinite | APT attack, repeat offender |
| `stolen_card` | 2,592,000 | 30 days | Card BIN reported stolen |
| `suspicious_email` | 7,776,000 | 90 days | Temporary email domain |

### Redis Key Pattern

```
blacklist:ip:192.168.1.1
blacklist:card_bin:123456
blacklist:email_domain:guerrillamail.com
```

### Sample Data

```json
{
    "type": "ip",
    "value": "192.168.1.1",
    "threat_level": "fraud",
    "reason": "Multiple failed payment attempts",
    "added_at": "2025-11-17T12:00:00Z",
    "added_by": "fds-engine",
    "ttl": 604800
}
```

---

## 3. CeleryTaskLog (PostgreSQL)

Logs all Celery async task executions for debugging and auditing.

### Entity Definition

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | UUID | No | `uuid4()` | Primary key |
| `task_id` | String(255) | No | - | Celery task UUID |
| `task_name` | String(255) | No | - | Task function name (e.g., "send_email") |
| `task_args` | JSON | Yes | `{}` | Task positional arguments (serialized) |
| `task_kwargs` | JSON | Yes | `{}` | Task keyword arguments (serialized) |
| `status` | Enum | No | `'pending'` | Task status: pending, started, success, failure, retry |
| `result` | JSON | Yes | `NULL` | Task return value (for success) |
| `error` | Text | Yes | `NULL` | Exception message (for failure) |
| `traceback` | Text | Yes | `NULL` | Full stack trace (for failure) |
| `retries` | Integer | No | `0` | Number of retry attempts |
| `max_retries` | Integer | No | `3` | Maximum allowed retries |
| `queue` | String(100) | No | `'default'` | Celery queue name |
| `worker` | String(255) | Yes | `NULL` | Worker hostname that executed task |
| `started_at` | DateTime | Yes | `NULL` | Task execution start time |
| `completed_at` | DateTime | Yes | `NULL` | Task execution end time |
| `duration_ms` | Integer | Yes | `NULL` | Execution duration in milliseconds |
| `created_at` | DateTime | No | `utcnow()` | Record creation timestamp |

### Indexes

```sql
CREATE INDEX idx_celery_task_log_task_id ON celery_task_log(task_id);
CREATE INDEX idx_celery_task_log_task_name ON celery_task_log(task_name);
CREATE INDEX idx_celery_task_log_status ON celery_task_log(status);
CREATE INDEX idx_celery_task_log_created_at ON celery_task_log(created_at DESC);
CREATE INDEX idx_celery_task_log_queue ON celery_task_log(queue);
```

### Constraints

- `task_id` must be unique
- `retries <= max_retries`
- `duration_ms >= 0`
- `status = 'success'` requires `result IS NOT NULL`
- `status = 'failure'` requires `error IS NOT NULL`

### Sample Data

```python
{
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "task_id": "a1b2c3d4-e5f6-4789-a012-3456789abcde",
    "task_name": "send_order_confirmation_email",
    "task_args": [],
    "task_kwargs": {"order_id": "123e4567-e89b-12d3-a456-426614174000"},
    "status": "success",
    "result": {"status": "sent", "message_id": "msg_123"},
    "error": None,
    "traceback": None,
    "retries": 0,
    "max_retries": 3,
    "queue": "email",
    "worker": "celery-worker-1@hostname",
    "started_at": "2025-11-17T12:00:00Z",
    "completed_at": "2025-11-17T12:00:02Z",
    "duration_ms": 2000,
    "created_at": "2025-11-17T11:59:58Z"
}
```

---

## 4. LogIndex (Elasticsearch)

Elasticsearch index template for centralized logging.

### Index Pattern

`shopfds-{service}-{YYYY.MM.dd}`

Examples:
- `shopfds-ecommerce-2025.11.17`
- `shopfds-fds-2025.11.17`
- `shopfds-ml-service-2025.11.17`

### Mapping Definition

```json
{
  "mappings": {
    "properties": {
      "@timestamp": {
        "type": "date"
      },
      "service": {
        "type": "keyword"
      },
      "environment": {
        "type": "keyword"
      },
      "log_level": {
        "type": "keyword"
      },
      "logger_name": {
        "type": "keyword"
      },
      "message": {
        "type": "text",
        "fields": {
          "keyword": {
            "type": "keyword",
            "ignore_above": 256
          }
        }
      },
      "endpoint": {
        "type": "keyword"
      },
      "method": {
        "type": "keyword"
      },
      "status_code": {
        "type": "integer"
      },
      "response_time": {
        "type": "float"
      },
      "user_id": {
        "type": "keyword"
      },
      "request_id": {
        "type": "keyword"
      },
      "client_ip": {
        "type": "ip"
      },
      "exception_type": {
        "type": "keyword"
      },
      "stack_trace": {
        "type": "text"
      },
      "fds_evaluation": {
        "properties": {
          "risk_score": {
            "type": "integer"
          },
          "risk_level": {
            "type": "keyword"
          },
          "decision": {
            "type": "keyword"
          },
          "evaluation_time_ms": {
            "type": "float"
          }
        }
      },
      "geo": {
        "properties": {
          "country_name": {
            "type": "keyword"
          },
          "city_name": {
            "type": "keyword"
          },
          "location": {
            "type": "geo_point"
          }
        }
      }
    }
  },
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "index.lifecycle.name": "shopfds-logs-policy",
    "index.lifecycle.rollover_alias": "shopfds-logs",
    "index.refresh_interval": "30s"
  }
}
```

### Sample Document

```json
{
  "@timestamp": "2025-11-17T12:00:00.123Z",
  "service": "ecommerce",
  "environment": "production",
  "log_level": "INFO",
  "logger_name": "src.api.orders",
  "message": "Order created successfully",
  "endpoint": "/v1/orders",
  "method": "POST",
  "status_code": 201,
  "response_time": 85.3,
  "user_id": "user_123",
  "request_id": "req_a1b2c3d4",
  "client_ip": "192.168.1.100",
  "fds_evaluation": {
    "risk_score": 25,
    "risk_level": "low",
    "decision": "approve",
    "evaluation_time_ms": 45.2
  },
  "geo": {
    "country_name": "South Korea",
    "city_name": "Seoul",
    "location": {
      "lat": 37.5665,
      "lon": 126.9780
    }
  }
}
```

---

## 5. AlertRule (Prometheus)

Stores Prometheus alert rule configurations (managed via YAML files, not database).

### YAML Structure

```yaml
groups:
  - name: cpu_alerts
    interval: 30s
    rules:
      - alert: HighCPUUsage
        expr: |
          100 - (avg by(instance, service) (
            rate(node_cpu_seconds_total{mode="idle"}[5m])
          ) * 100) > 80
        for: 5m
        labels:
          severity: warning
          component: infrastructure
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is {{ $value | humanize }}% (threshold: 80%)"
          runbook_url: "https://docs.shopfds.com/runbooks/high-cpu"
```

### Alert Metadata (in-memory, not persisted)

| Field | Type | Description |
|-------|------|-------------|
| `alert_name` | String | Alert identifier (e.g., "HighCPUUsage") |
| `expr` | String | PromQL expression |
| `for` | Duration | Alert must be active for this duration before firing |
| `severity` | Enum | warning, critical |
| `component` | Enum | infrastructure, application, database, cache, fds |
| `summary` | String | Template for alert summary |
| `description` | String | Template for alert description |
| `runbook_url` | String | Link to troubleshooting guide |

---

## Data Flow

### 1. Replication Monitoring Flow

```
[PostgreSQL Master] -> pg_stat_replication
                    -> [Monitoring Service] (check_replication_lag)
                    -> [ReplicationStatus Table]
                    -> [Prometheus Exporter]
                    -> [Alertmanager] (if lag > 10s)
                    -> [Slack Notification]
```

### 2. Blacklist Enforcement Flow

```
[FDS Engine] -> Check Redis Cluster
             -> Key: blacklist:ip:192.168.1.1
             -> If EXISTS: Block Transaction
             -> If NOT EXISTS: Continue Evaluation
             -> If High Risk: Add to Blacklist (SETEX)
```

### 3. Celery Task Logging Flow

```
[FastAPI Endpoint] -> Trigger Async Task
                   -> Celery Worker
                   -> Create CeleryTaskLog (status=pending)
                   -> Execute Task
                   -> Update CeleryTaskLog (status=success/failure)
                   -> Prometheus Metrics (task_duration_seconds)
```

### 4. Log Indexing Flow

```
[FastAPI App] -> JSON Log (stdout)
              -> Filebeat
              -> Logstash (parse, filter, enrich)
              -> Elasticsearch (index: shopfds-ecommerce-2025.11.17)
              -> Kibana (visualize)
```

### 5. Alert Firing Flow

```
[Prometheus] -> Evaluate Alert Rules (every 15s)
             -> Alert Fires (condition met for 5m)
             -> Alertmanager
             -> Route by Severity
             -> Slack (warning) + Email (critical)
```

---

## Migration Strategy

### Phase 1: PostgreSQL Schema (Week 1)

```bash
# Create migration
cd services/ecommerce/backend
alembic revision --autogenerate -m "Add ReplicationStatus and CeleryTaskLog"

# Apply migration
alembic upgrade head
```

### Phase 2: Redis Cluster Initialization (Week 2)

```bash
# No schema migration needed (key-value store)
# Initialize cluster
redis-cli --cluster create \
  redis-node-1:7000 \
  redis-node-2:7001 \
  redis-node-3:7002 \
  redis-node-4:7003 \
  redis-node-5:7004 \
  redis-node-6:7005 \
  --cluster-replicas 1
```

### Phase 3: Elasticsearch Index Template (Week 3)

```bash
# Apply index template
curl -X PUT "http://localhost:9200/_index_template/shopfds-logs" \
  -H 'Content-Type: application/json' \
  -d @infrastructure/elasticsearch/index-template.json

# Create initial index
curl -X PUT "http://localhost:9200/shopfds-logs-000001" \
  -H 'Content-Type: application/json' \
  -d '{"aliases": {"shopfds-logs": {"is_write_index": true}}}'
```

### Phase 4: Prometheus Alert Rules (Week 4)

```bash
# Reload Prometheus config
docker exec shopfds-prometheus kill -HUP 1

# Or use API
curl -X POST http://localhost:9090/-/reload
```

---

## Retention Policies

| Data Store | Data Type | Retention | Cleanup Method |
|------------|-----------|-----------|----------------|
| PostgreSQL | ReplicationStatus | 7 days | Celery Beat task (daily delete) |
| PostgreSQL | CeleryTaskLog | 30 days | Celery Beat task (weekly delete) |
| Redis Cluster | BlacklistEntry | Variable (TTL) | Automatic (SETEX TTL) |
| Elasticsearch | Logs (default) | 30 days | Curator (daily delete) |
| Elasticsearch | Logs (high-risk) | 90 days | Curator (weekly delete) |
| Prometheus | Metrics | 30 days | TSDB retention (automatic) |
| Alertmanager | Alert History | 5 days | Automatic (resolve_timeout) |

---

## Performance Considerations

### PostgreSQL

- **Partitioning**: Not needed initially (< 10M rows expected)
- **Vacuum**: Auto-vacuum enabled for CeleryTaskLog (high churn)
- **Index Bloat**: Monitor weekly, REINDEX if > 20% bloat

### Redis Cluster

- **Memory Limit**: 2GB per node (maxmemory-policy=volatile-lru)
- **Eviction**: Evict TTL keys first, then LRU if memory full
- **Persistence**: AOF enabled (appendfsync=everysec)

### Elasticsearch

- **Shard Size**: 30GB optimal (10-50GB range)
- **Refresh Interval**: 30s (not real-time, optimized for indexing)
- **Force Merge**: Daily for indices > 7 days old (reduce segments)

### Prometheus

- **TSDB Retention**: 30 days (storage.tsdb.retention.time)
- **Compression**: Automatic (Gorilla compression algorithm)
- **Scrape Interval**: 15s (balance between granularity and overhead)

---

## Security

### PostgreSQL

- **Replication User**: `replicator` with `REPLICATION` role only
- **SSL/TLS**: Required for replication connections
- **Row-Level Security**: Not needed (monitoring data only)

### Redis Cluster

- **Authentication**: `requirepass` + `masterauth` (same password)
- **Network**: Internal network only (no public internet)
- **Encryption**: TLS for cluster bus (Redis 6.0+)

### Elasticsearch

- **Authentication**: Basic Auth (username/password)
- **Encryption**: HTTPS for all API calls
- **Field-Level Security**: Mask PII in logs (Logstash filter)

### Prometheus/Alertmanager

- **Authentication**: Basic Auth (Nginx reverse proxy)
- **Secrets**: Slack webhook URL, SMTP password in environment variables
- **Network**: Internal network only

---

## Testing

### Unit Tests

```python
# Test ReplicationStatus model
def test_replication_status_healthy():
    status = ReplicationStatus(
        replica_name="test-replica",
        state="streaming",
        replay_lag_seconds=3.0
    )
    assert status.is_healthy == True

# Test BlacklistEntry TTL
async def test_blacklist_expiration():
    await redis.setex("blacklist:ip:192.168.1.1", 3600, json.dumps({...}))
    ttl = await redis.ttl("blacklist:ip:192.168.1.1")
    assert 3595 <= ttl <= 3600  # Allow 5s margin
```

### Integration Tests

```python
# Test Celery task logging
@pytest.mark.asyncio
async def test_celery_task_logging():
    task = send_email.delay(to="test@example.com")
    await asyncio.sleep(5)  # Wait for completion

    log = await db.execute(
        select(CeleryTaskLog).where(CeleryTaskLog.task_id == task.id)
    )
    assert log.status == "success"
    assert log.duration_ms > 0
```

---

## Monitoring

### Metrics to Track

- **PostgreSQL Replication Lag**: `replay_lag_seconds` (alert if > 10s)
- **Redis Memory Usage**: `used_memory_rss` (alert if > 1.6GB)
- **Elasticsearch Disk Usage**: `fs.total.available_in_bytes` (alert if < 15%)
- **Celery Task Failure Rate**: `celery_tasks_failed_total / celery_tasks_total` (alert if > 5%)
- **Prometheus Scrape Failures**: `up{job="..."} == 0` (alert immediately)

---

## Glossary

| Term | Definition |
|------|------------|
| **LSN** | Log Sequence Number (PostgreSQL WAL position) |
| **TTL** | Time To Live (automatic expiration in Redis) |
| **ILM** | Index Lifecycle Management (Elasticsearch) |
| **Rollover** | Creating new index when size/age threshold is reached |
| **PromQL** | Prometheus Query Language |
| **Scrape Interval** | How often Prometheus collects metrics |
| **Replication Lag** | Time delay between Master and Replica |
| **Async Replication** | Replica commit does not block Master commit |

---

**Version**: 1.0
**Last Updated**: 2025-11-17
**Status**: Ready for Review
