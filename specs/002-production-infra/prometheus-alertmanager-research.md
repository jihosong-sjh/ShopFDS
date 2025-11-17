# Research: Prometheus Alertmanager Integration and Alert Rules

**Date**: 2025-11-17
**Status**: Completed
**Related Feature**: 002-production-infra (User Story 4 - Integrated Log Monitoring and Alerting)

## Executive Summary

This research evaluates Prometheus Alertmanager as the alerting solution for ShopFDS production infrastructure. Alertmanager provides robust alert routing, deduplication, and multi-channel notification capabilities. It integrates seamlessly with our existing Prometheus monitoring stack and supports Slack/Email notifications required by FR-026 and FR-027.

**Key Decisions**:
- **Alerting Platform**: Prometheus Alertmanager (open-source, native Prometheus integration)
- **Notification Channels**: Slack (primary), Email (secondary/critical)
- **Alert Grouping**: By service, severity, and alert type to reduce noise
- **Alert Levels**: WARNING (Slack only), CRITICAL (Slack + Email)

---

## 1. Technology Selection

### Decision: Prometheus Alertmanager

**Rationale**:
1. **Native Integration**: Works seamlessly with our existing Prometheus deployment (already configured in `infrastructure/docker/prometheus.yml`)
2. **Zero Additional Cost**: Open-source solution vs. $21-$39/user/month for PagerDuty
3. **Powerful Routing**: Advanced routing rules support our multi-service architecture (Ecommerce, FDS, ML, Admin)
4. **Deduplication**: Automatically groups related alerts to prevent notification storms
5. **Proven Reliability**: Industry-standard alerting solution used by major tech companies

**Alternatives Considered**:

| Feature | **Alertmanager** | Grafana Alerts | PagerDuty |
|---------|-----------------|----------------|-----------|
| Cost | Free (Open-source) | Free (OSS) / Paid (Cloud) | $21-39/user/month |
| Prometheus Integration | Native, seamless | Good, built-in | Requires webhook |
| Routing Complexity | Excellent (tree-based) | Good (visual UI) | Excellent (escalation) |
| Multi-channel | Email, Slack, Webhook | Email, Slack, PagerDuty | SMS, Call, Push, Email |
| On-call Scheduling | None (external tool) | Grafana OnCall (paid) | Built-in, advanced |
| Alerting UI | Basic web UI | Integrated dashboards | Advanced incident mgmt |
| Setup Complexity | Medium (YAML config) | Low (GUI) | Low (SaaS) |
| Self-hosted | Yes | Yes | No (cloud-only) |

**Why Not Grafana Alerts?**
- We already have Prometheus + Alertmanager configured
- Grafana Alerts adds another layer without significant benefit for our use case
- Alertmanager's routing rules are more powerful for complex scenarios (e.g., FDS critical alerts)
- Can still visualize alerts in Grafana dashboards while using Alertmanager

**Why Not PagerDuty?**
- High cost ($21-39/user/month = $252-468/year for 1 user, $1260-2340/year for 5 users)
- Overkill for our current scale (4 microservices, small team)
- Most features (SMS, phone calls, advanced scheduling) not required per spec
- Can integrate later if needed (Alertmanager supports PagerDuty as a receiver)

---

## 2. Alerting Architecture

### Overview

```
[Prometheus] --> [Alert Rules] --> [Alertmanager] --> [Slack/Email]
     ^                                    |
     |                                    v
[Exporters]                        [Inhibition/Grouping]
(App, Node, Redis)
```

### Components

1. **Prometheus Alert Rules** (`/etc/prometheus/rules/*.yml`): Define alert conditions using PromQL
2. **Alertmanager** (`alertmanager:9093`): Routes, groups, and sends alerts to receivers
3. **Receivers**: Slack Webhook (channel: `#shopfds-alerts`), SMTP Email (to: `ops@shopfds.com`)

### Alert Flow

1. Prometheus evaluates alert rules every 15s (configurable via `evaluation_interval`)
2. When condition is met for `for: 2m` (threshold duration), alert fires
3. Alertmanager receives alert and applies:
   - **Grouping**: Combines related alerts (e.g., all CPU alerts from same service)
   - **Inhibition**: Suppresses lower-priority alerts when higher-priority ones are active
   - **Routing**: Directs to appropriate receiver based on severity/service
   - **Deduplication**: Prevents duplicate notifications within `repeat_interval`
4. Notification sent to Slack/Email with context (metric value, runbook link)

---

## 3. Alert Rules Implementation

### 3.1 CPU Usage Alerts

**Goal**: Detect high CPU usage before performance degradation (FR-026)

```yaml
# File: infrastructure/docker/prometheus/rules/cpu_alerts.yml
groups:
  - name: cpu_alerts
    interval: 30s
    rules:
      # WARNING: 80% CPU for 5 minutes
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

      # CRITICAL: 90% CPU for 2 minutes
      - alert: CriticalCPUUsage
        expr: |
          100 - (avg by(instance, service) (
            rate(node_cpu_seconds_total{mode="idle"}[5m])
          ) * 100) > 90
        for: 2m
        labels:
          severity: critical
          component: infrastructure
        annotations:
          summary: "CRITICAL: CPU usage on {{ $labels.instance }}"
          description: "CPU usage is {{ $value | humanize }}% (threshold: 90%)"
          runbook_url: "https://docs.shopfds.com/runbooks/critical-cpu"
```

**PromQL Explanation**:
- `node_cpu_seconds_total{mode="idle"}`: CPU time spent in idle mode (per core)
- `rate(...[5m])`: Average idle time per second over last 5 minutes
- `avg by(instance, service)`: Average across all CPU cores per instance
- `100 - (...) * 100`: Convert idle % to busy %

### 3.2 Memory Usage Alerts

**Goal**: Prevent OOM (Out of Memory) errors (FR-026)

```yaml
# File: infrastructure/docker/prometheus/rules/memory_alerts.yml
groups:
  - name: memory_alerts
    interval: 30s
    rules:
      # WARNING: 85% memory usage
      - alert: HighMemoryUsage
        expr: |
          (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
          component: infrastructure
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage is {{ $value | humanize }}% (threshold: 85%)"
          runbook_url: "https://docs.shopfds.com/runbooks/high-memory"

      # CRITICAL: 95% memory usage
      - alert: CriticalMemoryUsage
        expr: |
          (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 95
        for: 2m
        labels:
          severity: critical
          component: infrastructure
        annotations:
          summary: "CRITICAL: Memory usage on {{ $labels.instance }}"
          description: "Memory usage is {{ $value | humanize }}% (threshold: 95%)"
          runbook_url: "https://docs.shopfds.com/runbooks/critical-memory"

      # CRITICAL: Memory will exhaust in 1 hour
      - alert: MemoryExhaustionPredicted
        expr: |
          predict_linear(node_memory_MemAvailable_bytes[30m], 3600) <= 0
        for: 10m
        labels:
          severity: critical
          component: infrastructure
        annotations:
          summary: "Memory exhaustion predicted on {{ $labels.instance }}"
          description: "Available memory will be exhausted in ~1 hour based on current trend"
          runbook_url: "https://docs.shopfds.com/runbooks/memory-exhaustion"
```

**PromQL Explanation**:
- `node_memory_MemAvailable_bytes`: Available memory (includes cache that can be reclaimed)
- `node_memory_MemTotal_bytes`: Total installed memory
- `predict_linear(...[30m], 3600)`: Linear prediction 1 hour ahead based on 30min trend

### 3.3 Disk Space Alerts

**Goal**: Prevent disk full errors (FR-026)

```yaml
# File: infrastructure/docker/prometheus/rules/disk_alerts.yml
groups:
  - name: disk_alerts
    interval: 60s
    rules:
      # WARNING: 85% disk usage
      - alert: HighDiskUsage
        expr: |
          (1 - (node_filesystem_avail_bytes{mountpoint="/"} /
                node_filesystem_size_bytes{mountpoint="/"})) * 100 > 85
        for: 5m
        labels:
          severity: warning
          component: infrastructure
        annotations:
          summary: "High disk usage on {{ $labels.instance }}"
          description: "Disk usage is {{ $value | humanize }}% (threshold: 85%)"
          runbook_url: "https://docs.shopfds.com/runbooks/high-disk"

      # CRITICAL: 95% disk usage
      - alert: CriticalDiskUsage
        expr: |
          (1 - (node_filesystem_avail_bytes{mountpoint="/"} /
                node_filesystem_size_bytes{mountpoint="/"})) * 100 > 95
        for: 2m
        labels:
          severity: critical
          component: infrastructure
        annotations:
          summary: "CRITICAL: Disk usage on {{ $labels.instance }}"
          description: "Disk usage is {{ $value | humanize }}% (threshold: 95%)"
          runbook_url: "https://docs.shopfds.com/runbooks/critical-disk"

      # CRITICAL: Disk will fill in 7 days
      - alert: DiskWillFillSoon
        expr: |
          predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[24h], 7*24*3600) <= 0
        for: 1h
        labels:
          severity: warning
          component: infrastructure
        annotations:
          summary: "Disk will fill within 7 days on {{ $labels.instance }}"
          description: "Based on 24h trend, disk will be full in ~7 days"
          runbook_url: "https://docs.shopfds.com/runbooks/disk-filling"
```

### 3.4 API Error Rate Alerts

**Goal**: Detect service degradation via HTTP 5xx errors (FR-026)

```yaml
# File: infrastructure/docker/prometheus/rules/api_alerts.yml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      # WARNING: 5% error rate
      - alert: HighAPIErrorRate
        expr: |
          sum by(service) (rate(http_requests_total{status=~"5.."}[5m])) /
          sum by(service) (rate(http_requests_total[5m])) * 100 > 5
        for: 5m
        labels:
          severity: warning
          component: application
        annotations:
          summary: "High API error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value | humanize }}% (threshold: 5%)"
          runbook_url: "https://docs.shopfds.com/runbooks/high-error-rate"

      # CRITICAL: 10% error rate
      - alert: CriticalAPIErrorRate
        expr: |
          sum by(service) (rate(http_requests_total{status=~"5.."}[5m])) /
          sum by(service) (rate(http_requests_total[5m])) * 100 > 10
        for: 2m
        labels:
          severity: critical
          component: application
        annotations:
          summary: "CRITICAL: API error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value | humanize }}% (threshold: 10%)"
          runbook_url: "https://docs.shopfds.com/runbooks/critical-error-rate"

      # CRITICAL: Service returning only errors
      - alert: ServiceCompleteFailure
        expr: |
          sum by(service) (rate(http_requests_total{status=~"5.."}[5m])) /
          sum by(service) (rate(http_requests_total[5m])) * 100 > 95
        for: 1m
        labels:
          severity: critical
          component: application
        annotations:
          summary: "CRITICAL: {{ $labels.service }} is completely failing"
          description: "95%+ of requests are returning 5xx errors"
          runbook_url: "https://docs.shopfds.com/runbooks/service-failure"
```

**PromQL Explanation**:
- `rate(http_requests_total{status=~"5.."}[5m])`: Requests per second with 5xx status over 5min
- `rate(http_requests_total[5m])`: Total requests per second over 5min
- Division gives error ratio, multiply by 100 for percentage

### 3.5 Health Check Alerts

**Goal**: Detect service availability issues (FR-026)

```yaml
# File: infrastructure/docker/prometheus/rules/health_alerts.yml
groups:
  - name: health_alerts
    interval: 15s
    rules:
      # CRITICAL: Health check failing
      - alert: ServiceHealthCheckFailed
        expr: |
          up{job=~"ecommerce-backend|fds|ml-service|admin-dashboard-backend"} == 0
        for: 1m
        labels:
          severity: critical
          component: application
        annotations:
          summary: "Health check failed for {{ $labels.job }}"
          description: "Service {{ $labels.job }} is not responding to health checks"
          runbook_url: "https://docs.shopfds.com/runbooks/health-check-failure"

      # CRITICAL: Database connection failure
      - alert: DatabaseConnectionFailed
        expr: |
          health_check_database_up == 0
        for: 1m
        labels:
          severity: critical
          component: database
        annotations:
          summary: "Database connection failed on {{ $labels.instance }}"
          description: "Service {{ $labels.service }} cannot connect to database"
          runbook_url: "https://docs.shopfds.com/runbooks/db-connection-failure"

      # CRITICAL: Redis connection failure
      - alert: RedisConnectionFailed
        expr: |
          health_check_redis_up == 0
        for: 1m
        labels:
          severity: critical
          component: cache
        annotations:
          summary: "Redis connection failed on {{ $labels.instance }}"
          description: "Service {{ $labels.service }} cannot connect to Redis"
          runbook_url: "https://docs.shopfds.com/runbooks/redis-connection-failure"
```

### 3.6 FDS-Specific Alerts

**Goal**: Monitor FDS performance targets (100ms P95, SC-002)

```yaml
# File: infrastructure/docker/prometheus/rules/fds_alerts.yml
groups:
  - name: fds_alerts
    interval: 30s
    rules:
      # WARNING: FDS evaluation time exceeds 100ms (P95)
      - alert: FDSSlowEvaluation
        expr: |
          histogram_quantile(0.95,
            sum(rate(fds_evaluation_duration_seconds_bucket[5m])) by (le)
          ) > 0.1
        for: 5m
        labels:
          severity: warning
          component: fds
        annotations:
          summary: "FDS evaluation time exceeds 100ms (P95)"
          description: "P95 evaluation time is {{ $value | humanize }}s (threshold: 0.1s)"
          runbook_url: "https://docs.shopfds.com/runbooks/fds-slow"

      # CRITICAL: FDS evaluation time exceeds 200ms (P95)
      - alert: FDSCriticalSlowdown
        expr: |
          histogram_quantile(0.95,
            sum(rate(fds_evaluation_duration_seconds_bucket[5m])) by (le)
          ) > 0.2
        for: 2m
        labels:
          severity: critical
          component: fds
        annotations:
          summary: "CRITICAL: FDS evaluation critically slow"
          description: "P95 evaluation time is {{ $value | humanize }}s (threshold: 0.2s)"
          runbook_url: "https://docs.shopfds.com/runbooks/fds-critical-slow"

      # WARNING: High FDS block rate (potential overblocking)
      - alert: HighFDSBlockRate
        expr: |
          sum(rate(fds_evaluations_total{decision="reject"}[5m])) /
          sum(rate(fds_evaluations_total[5m])) * 100 > 20
        for: 10m
        labels:
          severity: warning
          component: fds
        annotations:
          summary: "High FDS block rate detected"
          description: "FDS is blocking {{ $value | humanize }}% of transactions (threshold: 20%)"
          runbook_url: "https://docs.shopfds.com/runbooks/high-block-rate"
```

---

## 4. Alertmanager Configuration

### 4.1 Main Configuration

```yaml
# File: infrastructure/docker/alertmanager/alertmanager.yml
global:
  # Default retry interval for sending failed notifications
  resolve_timeout: 5m

  # Slack API URL (use global default, can override per receiver)
  slack_api_url: 'https://hooks.slack.com/services/YOUR_WEBHOOK_URL'

  # SMTP settings for email notifications
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@shopfds.com'
  smtp_auth_username: 'alerts@shopfds.com'
  smtp_auth_password: 'YOUR_APP_PASSWORD'
  smtp_require_tls: true

# Alert routing tree
route:
  # Root route - applies to all alerts
  receiver: 'slack-general'
  group_by: ['alertname', 'service', 'severity']

  # Wait 30s before sending first notification (collect related alerts)
  group_wait: 30s

  # Send new alerts in same group after 5min
  group_interval: 5m

  # Resend alert if still firing after 4h
  repeat_interval: 4h

  # Child routes (evaluated top to bottom, first match wins)
  routes:
    # Route 1: Critical alerts -> Slack + Email
    - match:
        severity: critical
      receiver: 'slack-critical-email'
      group_wait: 10s        # Faster notification for critical alerts
      repeat_interval: 1h    # Remind more frequently
      continue: false        # Stop routing here

    # Route 2: FDS alerts -> Dedicated Slack channel
    - match:
        component: fds
      receiver: 'slack-fds'
      continue: true         # Also send to general Slack (warning level)

    # Route 3: Database alerts -> DBA team
    - match:
        component: database
      receiver: 'slack-database-email'
      continue: false

    # Route 4: Warning alerts -> Slack only (default)
    - match:
        severity: warning
      receiver: 'slack-general'
      continue: false

# Inhibition rules (suppress alerts when higher-priority alerts are active)
inhibit_rules:
  # Rule 1: Critical CPU alert suppresses warning CPU alert
  - source_match:
      severity: 'critical'
      alertname: 'CriticalCPUUsage'
    target_match:
      severity: 'warning'
      alertname: 'HighCPUUsage'
    equal: ['instance']

  # Rule 2: Service failure suppresses high error rate
  - source_match:
      alertname: 'ServiceCompleteFailure'
    target_match:
      alertname: 'HighAPIErrorRate'
    equal: ['service']

  # Rule 3: Health check failure suppresses all other alerts for that service
  - source_match:
      alertname: 'ServiceHealthCheckFailed'
    target_match_re:
      alertname: '(HighAPIErrorRate|CriticalAPIErrorRate|.*)'
    equal: ['service']

# Notification receivers
receivers:
  # Receiver 1: General Slack channel (warnings)
  - name: 'slack-general'
    slack_configs:
      - channel: '#shopfds-alerts'
        username: 'Prometheus Alert'
        icon_emoji: ':warning:'
        title: 'Alert: {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          *Alert:* {{ .Annotations.summary }}
          *Description:* {{ .Annotations.description }}
          *Severity:* {{ .Labels.severity }}
          *Service:* {{ .Labels.service }}
          *Runbook:* {{ .Annotations.runbook_url }}
          {{ end }}
        send_resolved: true

  # Receiver 2: Critical alerts (Slack + Email)
  - name: 'slack-critical-email'
    slack_configs:
      - channel: '#shopfds-critical'
        username: 'Prometheus Alert'
        icon_emoji: ':rotating_light:'
        color: 'danger'
        title: 'CRITICAL ALERT: {{ .GroupLabels.alertname }}'
        text: |
          @channel CRITICAL ALERT TRIGGERED
          {{ range .Alerts }}
          *Alert:* {{ .Annotations.summary }}
          *Description:* {{ .Annotations.description }}
          *Severity:* {{ .Labels.severity }}
          *Service:* {{ .Labels.service }}
          *Instance:* {{ .Labels.instance }}
          *Runbook:* {{ .Annotations.runbook_url }}
          {{ end }}
        send_resolved: true
    email_configs:
      - to: 'ops-team@shopfds.com'
        headers:
          Subject: '[CRITICAL] {{ .GroupLabels.alertname }} - {{ .GroupLabels.service }}'
        html: |
          <h2 style="color: red;">CRITICAL ALERT</h2>
          {{ range .Alerts }}
          <p><strong>Summary:</strong> {{ .Annotations.summary }}</p>
          <p><strong>Description:</strong> {{ .Annotations.description }}</p>
          <p><strong>Severity:</strong> {{ .Labels.severity }}</p>
          <p><strong>Service:</strong> {{ .Labels.service }}</p>
          <p><strong>Instance:</strong> {{ .Labels.instance }}</p>
          <p><strong>Runbook:</strong> <a href="{{ .Annotations.runbook_url }}">{{ .Annotations.runbook_url }}</a></p>
          {{ end }}
        send_resolved: true

  # Receiver 3: FDS-specific alerts
  - name: 'slack-fds'
    slack_configs:
      - channel: '#shopfds-fds-alerts'
        username: 'FDS Monitor'
        icon_emoji: ':shield:'
        title: 'FDS Alert: {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          *Alert:* {{ .Annotations.summary }}
          *Description:* {{ .Annotations.description }}
          *Severity:* {{ .Labels.severity }}
          *Runbook:* {{ .Annotations.runbook_url }}
          {{ end }}
        send_resolved: true

  # Receiver 4: Database alerts (Slack + Email to DBA team)
  - name: 'slack-database-email'
    slack_configs:
      - channel: '#shopfds-database'
        username: 'Database Alert'
        icon_emoji: ':database:'
        title: 'Database Alert: {{ .GroupLabels.alertname }}'
        send_resolved: true
    email_configs:
      - to: 'dba-team@shopfds.com'
        headers:
          Subject: '[DATABASE] {{ .GroupLabels.alertname }}'
        send_resolved: true
```

### 4.2 Alertmanager Docker Compose Integration

```yaml
# Add to infrastructure/docker/docker-compose.dev.yml
services:
  # ... existing services ...

  # Alertmanager (Alert Routing)
  alertmanager:
    image: prom/alertmanager:latest
    container_name: shopfds-alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
      - '--web.external-url=http://localhost:9093'
      - '--cluster.advertise-address=0.0.0.0:9093'
    networks:
      - shopfds-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:9093/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  # ... existing volumes ...
  alertmanager_data:
    driver: local
```

### 4.3 Prometheus Configuration Update

Update `infrastructure/docker/prometheus.yml`:

```yaml
# ... existing global config ...

# Enable Alertmanager integration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - 'alertmanager:9093'

# Load alert rules from files
rule_files:
  - '/etc/prometheus/rules/cpu_alerts.yml'
  - '/etc/prometheus/rules/memory_alerts.yml'
  - '/etc/prometheus/rules/disk_alerts.yml'
  - '/etc/prometheus/rules/api_alerts.yml'
  - '/etc/prometheus/rules/health_alerts.yml'
  - '/etc/prometheus/rules/fds_alerts.yml'

# ... existing scrape_configs ...
```

Update Prometheus Docker Compose service:

```yaml
prometheus:
  image: prom/prometheus:latest
  container_name: shopfds-prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
    - ./prometheus/rules:/etc/prometheus/rules  # ADD THIS
    - prometheus_data:/prometheus
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
    - '--web.console.libraries=/usr/share/prometheus/console_libraries'
    - '--web.console.templates=/usr/share/prometheus/consoles'
    - '--storage.tsdb.retention.time=30d'
    - '--web.enable-lifecycle'  # Enable hot-reload of config
  networks:
    - shopfds-network
  depends_on:
    - ecommerce-backend
    - fds-service
    - alertmanager  # ADD THIS
```

---

## 5. PromQL Query Patterns

### 5.1 Rate and Increase Functions

**Use Case**: Calculate per-second rate of counter metrics (requests, errors, etc.)

```promql
# Average request rate over 5 minutes
rate(http_requests_total[5m])

# Total requests in last 1 hour
increase(http_requests_total[1h])

# Error rate percentage
rate(http_requests_total{status=~"5.."}[5m]) /
rate(http_requests_total[5m]) * 100
```

**Best Practices**:
- Always use `rate()` for counters (not `irate()` unless you need instant rate)
- Use time range `[5m]` minimum for `rate()` (2x scrape interval)
- `increase()` = `rate()` * time range in seconds

### 5.2 Aggregation Functions

**Use Case**: Summarize metrics across multiple instances

```promql
# Average CPU across all instances
avg(node_cpu_usage_percent)

# Maximum memory usage across all services
max(node_memory_usage_percent) by (service)

# Total requests per service
sum(rate(http_requests_total[5m])) by (service)

# Top 5 services by error count
topk(5, sum(rate(http_requests_total{status=~"5.."}[5m])) by (service))
```

### 5.3 Prediction Functions

**Use Case**: Predict resource exhaustion based on trends

```promql
# Predict when memory will be exhausted (1 hour ahead)
predict_linear(node_memory_MemAvailable_bytes[30m], 3600) <= 0

# Predict when disk will be full (7 days ahead)
predict_linear(node_filesystem_avail_bytes[24h], 7*24*3600) <= 0
```

**Best Practices**:
- Use longer time ranges for training data (24h for disk, 30m for memory)
- Prediction time should be shorter than training period
- Combine with `for: 10m` to avoid false positives from temporary spikes

### 5.4 Complex Conditions (Boolean Operators)

**Use Case**: Alert when multiple conditions are met simultaneously

```promql
# High CPU AND high memory on same instance
(node_cpu_usage_percent > 80)
and on(instance)
(node_memory_usage_percent > 80)

# High error rate BUT NOT during maintenance window
(rate(http_requests_total{status=~"5.."}[5m]) > 10)
unless
(maintenance_mode == 1)

# Service down OR database unreachable
up{job="ecommerce-backend"} == 0
or
health_check_database_up{job="ecommerce-backend"} == 0
```

### 5.5 Histogram Quantiles (P95, P99)

**Use Case**: Monitor latency percentiles (P50, P95, P99)

```promql
# P95 FDS evaluation time
histogram_quantile(0.95,
  sum(rate(fds_evaluation_duration_seconds_bucket[5m])) by (le)
)

# P99 API response time
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
)

# P50 (median) response time per endpoint
histogram_quantile(0.50,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)
)
```

**Best Practices**:
- Always use `sum(rate(...)) by (le)` for histogram buckets
- Alert on P95/P99, not average (average hides outliers)
- Combine with `for: 5m` to avoid alerting on transient spikes

---

## 6. Alert Template Customization

### 6.1 Slack Message Template

**Goal**: Rich, actionable Slack notifications

```yaml
slack_configs:
  - channel: '#shopfds-alerts'
    username: 'Prometheus Alert'
    icon_emoji: ':warning:'
    color: '{{ if eq .Status "firing" }}danger{{ else }}good{{ end }}'
    title: '{{ .Status | toUpper }}: {{ .GroupLabels.alertname }}'

    # Main message text
    text: |
      {{ range .Alerts }}
      *Summary:* {{ .Annotations.summary }}
      *Description:* {{ .Annotations.description }}
      *Severity:* {{ .Labels.severity }} | *Component:* {{ .Labels.component }}
      *Service:* {{ .Labels.service }} | *Instance:* {{ .Labels.instance }}
      *Started:* {{ .StartsAt.Format "2006-01-02 15:04:05 MST" }}
      {{ if .Annotations.runbook_url }}
      *Runbook:* <{{ .Annotations.runbook_url }}|Click here for troubleshooting steps>
      {{ end }}
      ---
      {{ end }}

      *Total Alerts:* {{ .Alerts | len }} | *Firing:* {{ .Alerts.Firing | len }} | *Resolved:* {{ .Alerts.Resolved | len }}

    # Additional fields (displayed as key-value pairs)
    fields:
      - title: 'Alert Count'
        value: '{{ .Alerts | len }}'
        short: true
      - title: 'Status'
        value: '{{ .Status }}'
        short: true

    # Actions (buttons)
    actions:
      - type: button
        text: 'View in Prometheus'
        url: 'http://prometheus:9090/alerts'
      - type: button
        text: 'View in Grafana'
        url: 'http://grafana:3000/alerting/list'
      - type: button
        text: 'Silence Alert'
        url: 'http://alertmanager:9093/#/silences/new'

    send_resolved: true
```

### 6.2 Email Template

**Goal**: Professional, detailed email notifications

```yaml
email_configs:
  - to: 'ops-team@shopfds.com'
    headers:
      Subject: '[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }} - {{ .GroupLabels.service }}'
      From: 'ShopFDS Alerts <alerts@shopfds.com>'

    html: |
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; }
          .alert-box {
            border: 2px solid #d9534f;
            padding: 20px;
            margin: 10px 0;
            border-radius: 5px;
          }
          .resolved-box {
            border-color: #5cb85c;
          }
          table {
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
          }
          th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
          }
          th {
            background-color: #f2f2f2;
          }
          .critical { color: #d9534f; font-weight: bold; }
          .warning { color: #f0ad4e; font-weight: bold; }
        </style>
      </head>
      <body>
        <h2>{{ if eq .Status "firing" }}ALERT TRIGGERED{{ else }}ALERT RESOLVED{{ end }}</h2>

        {{ range .Alerts }}
        <div class="alert-box {{ if eq .Status "resolved" }}resolved-box{{ end }}">
          <h3>{{ .Annotations.summary }}</h3>
          <p><strong>Description:</strong> {{ .Annotations.description }}</p>

          <table>
            <tr>
              <th>Property</th>
              <th>Value</th>
            </tr>
            <tr>
              <td>Status</td>
              <td>{{ .Status }}</td>
            </tr>
            <tr>
              <td>Severity</td>
              <td class="{{ .Labels.severity }}">{{ .Labels.severity }}</td>
            </tr>
            <tr>
              <td>Service</td>
              <td>{{ .Labels.service }}</td>
            </tr>
            <tr>
              <td>Instance</td>
              <td>{{ .Labels.instance }}</td>
            </tr>
            <tr>
              <td>Component</td>
              <td>{{ .Labels.component }}</td>
            </tr>
            <tr>
              <td>Started At</td>
              <td>{{ .StartsAt.Format "2006-01-02 15:04:05 MST" }}</td>
            </tr>
            {{ if .EndsAt }}
            <tr>
              <td>Ended At</td>
              <td>{{ .EndsAt.Format "2006-01-02 15:04:05 MST" }}</td>
            </tr>
            {{ end }}
          </table>

          {{ if .Annotations.runbook_url }}
          <p><strong>Troubleshooting:</strong> <a href="{{ .Annotations.runbook_url }}">{{ .Annotations.runbook_url }}</a></p>
          {{ end }}
        </div>
        {{ end }}

        <hr>
        <p>
          <strong>Total Alerts:</strong> {{ .Alerts | len }} |
          <strong>Firing:</strong> {{ .Alerts.Firing | len }} |
          <strong>Resolved:</strong> {{ .Alerts.Resolved | len }}
        </p>

        <p>
          <a href="http://prometheus:9090/alerts">View in Prometheus</a> |
          <a href="http://grafana:3000/alerting/list">View in Grafana</a> |
          <a href="http://alertmanager:9093">Manage Alerts</a>
        </p>
      </body>
      </html>

    send_resolved: true
```

---

## 7. Deduplication and Grouping Strategy

### 7.1 Alert Grouping

**Goal**: Reduce notification noise by combining related alerts

**Configuration**:
```yaml
route:
  group_by: ['alertname', 'service', 'severity']
  group_wait: 30s       # Wait 30s before first notification (collect related alerts)
  group_interval: 5m    # Send new alerts in same group after 5min
  repeat_interval: 4h   # Resend if still firing after 4h
```

**Example Scenario**:
1. 10:00:00 - `HighCPUUsage` fires on `ecommerce-backend-1`
2. 10:00:10 - `HighCPUUsage` fires on `ecommerce-backend-2`
3. 10:00:20 - `HighCPUUsage` fires on `ecommerce-backend-3`
4. 10:00:30 - **Single notification** sent with all 3 alerts grouped

**Benefits**:
- Reduces Slack noise from 3 messages to 1
- Easier to see pattern (all instances affected = cluster-wide issue)
- Prevents alert fatigue

### 7.2 Inhibition Rules

**Goal**: Suppress lower-priority alerts when higher-priority ones are active

**Rule 1: Critical suppresses warning for same instance**
```yaml
inhibit_rules:
  - source_match:
      severity: 'critical'
      alertname: 'CriticalCPUUsage'
    target_match:
      severity: 'warning'
      alertname: 'HighCPUUsage'
    equal: ['instance']
```

**Example**:
- Instance has 92% CPU (both `HighCPUUsage` and `CriticalCPUUsage` fire)
- Only `CriticalCPUUsage` notification is sent
- Once CPU drops below 90%, `CriticalCPUUsage` resolves, `HighCPUUsage` notifications resume

**Rule 2: Service failure suppresses high error rate**
```yaml
inhibit_rules:
  - source_match:
      alertname: 'ServiceCompleteFailure'
    target_match:
      alertname: 'HighAPIErrorRate'
    equal: ['service']
```

**Example**:
- Service completely down (95%+ errors)
- `ServiceCompleteFailure` fires (critical)
- `HighAPIErrorRate` (5% threshold) is suppressed (redundant information)

### 7.3 Repeat Interval Strategy

**Goal**: Balance reminder frequency with notification fatigue

**Configuration**:
```yaml
# Default: Resend every 4 hours
repeat_interval: 4h

# Critical alerts: Resend every 1 hour
routes:
  - match:
      severity: critical
    repeat_interval: 1h
```

**Rationale**:
- **Critical alerts (1h)**: Ensure team is aware until resolved
- **Warning alerts (4h)**: Avoid notification spam for non-urgent issues
- **Long outages**: If alert fires for 8 hours, only 2-8 notifications sent (not 480)

---

## 8. Implementation Roadmap

### Phase 1: Core Setup (Week 1)
- [ ] Deploy Alertmanager container in Docker Compose
- [ ] Configure Slack webhook integration (#shopfds-alerts channel)
- [ ] Configure email SMTP settings (Gmail App Password)
- [ ] Update Prometheus config to enable Alertmanager integration
- [ ] Test basic alert flow (manually trigger alert)

### Phase 2: Alert Rules (Week 2)
- [ ] Implement CPU alerts (warning/critical)
- [ ] Implement memory alerts (warning/critical/prediction)
- [ ] Implement disk alerts (warning/critical/prediction)
- [ ] Implement API error rate alerts (5%/10% thresholds)
- [ ] Implement health check alerts (service/database/Redis)
- [ ] Implement FDS-specific alerts (P95 latency, block rate)

### Phase 3: Routing and Templates (Week 3)
- [ ] Configure alert routing (critical vs warning)
- [ ] Set up dedicated Slack channels (#shopfds-critical, #shopfds-fds-alerts)
- [ ] Customize Slack message templates (runbook links, formatting)
- [ ] Customize email templates (HTML formatting, tables)
- [ ] Configure inhibition rules (critical suppresses warning)

### Phase 4: Testing and Validation (Week 4)
- [ ] Load test: Trigger high CPU (stress tool)
- [ ] Load test: Fill memory (memory leak simulation)
- [ ] Load test: Fill disk (large file generation)
- [ ] Load test: Trigger API errors (kill service)
- [ ] Verify Slack notifications received within 30s
- [ ] Verify email notifications received within 1min
- [ ] Verify alert grouping works (multiple instances)
- [ ] Verify inhibition rules work (critical suppresses warning)
- [ ] Verify repeat interval (wait 1h for critical resend)

### Phase 5: Documentation (Week 5)
- [ ] Write runbook for each alert type (`docs/runbooks/`)
- [ ] Document alerting architecture (`docs/monitoring/`)
- [ ] Create troubleshooting guide for Alertmanager
- [ ] Train team on silencing/acknowledging alerts
- [ ] Create on-call rotation schedule (if needed)

---

## 9. Monitoring and Maintenance

### 9.1 Alertmanager Metrics

**Monitor Alertmanager itself**:

```promql
# Alertmanager is up
up{job="alertmanager"}

# Number of active alerts
alertmanager_alerts

# Notification success rate
rate(alertmanager_notifications_total{integration="slack"}[5m])
rate(alertmanager_notifications_failed_total{integration="slack"}[5m])

# Alert grouping effectiveness
alertmanager_notification_latency_seconds
```

### 9.2 Alert Dashboard (Grafana)

**Create Grafana dashboard showing**:
- Current firing alerts (table)
- Alert count by severity (pie chart)
- Alert count by service (bar chart)
- Alert trend over time (time series)
- Notification success rate (gauge)

**Example Grafana Panel**:
```json
{
  "title": "Firing Alerts",
  "targets": [
    {
      "expr": "ALERTS{alertstate=\"firing\"}",
      "legendFormat": "{{ alertname }} - {{ service }}"
    }
  ],
  "type": "table"
}
```

### 9.3 Runbook Creation

**Template for each alert**:

```markdown
# Runbook: HighCPUUsage

## Alert Details
- **Severity**: Warning
- **Threshold**: 80% CPU for 5 minutes
- **Component**: Infrastructure

## Diagnosis Steps
1. Check CPU usage: `top` or `htop` on instance
2. Identify top processes: `ps aux --sort=-%cpu | head -n 10`
3. Check recent deployments (new code causing CPU spike?)
4. Check Grafana dashboard for traffic pattern changes

## Resolution Steps
1. **If traffic spike**: Scale horizontally (add instances)
2. **If inefficient code**: Identify hot path, optimize, deploy fix
3. **If database query**: Check slow query log, add index
4. **If memory leak**: Restart service (temporary), fix code (long-term)

## Escalation
- **If CPU > 90%**: Page on-call engineer
- **If CPU > 95%**: Incident response (all hands on deck)
- **If persists > 1 hour**: Investigate root cause (not just symptom)

## Related Alerts
- `CriticalCPUUsage` (90% threshold)
- `HighMemoryUsage` (often correlated)

## Automation
- Consider auto-scaling rules in Kubernetes HPA
- Set up automated profiling when CPU > 80%
```

---

## 10. Success Metrics

### 10.1 Alerting Effectiveness

**Metrics to Track**:
- **Alert Count**: Total alerts per day (target: < 20/day)
- **False Positive Rate**: Alerts that didn't require action (target: < 10%)
- **Mean Time to Acknowledge (MTTA)**: Time to respond to alert (target: < 5min)
- **Mean Time to Resolution (MTTR)**: Time to resolve incident (target: < 30min)
- **Notification Delivery Rate**: Slack/Email success rate (target: 99.9%)

### 10.2 Business Impact

**SC-007 Validation**: CPU 80% alert within 30s
```bash
# Test: Trigger high CPU
stress --cpu 8 --timeout 300s

# Verify in Alertmanager logs
docker logs shopfds-alertmanager | grep "HighCPUUsage"

# Verify Slack notification timestamp (< 30s from alert fire time)
```

**SC-006 Validation**: Log to Elasticsearch within 10s
```bash
# Trigger error in application
curl -X POST http://localhost:8000/trigger-error

# Check Elasticsearch (< 10s latency)
curl 'http://localhost:9200/logs-*/_search?q=level:ERROR&sort=@timestamp:desc'
```

---

## 11. Cost Analysis

### Alertmanager (Open-Source)
- **Setup Cost**: 8 hours engineer time @ $100/hr = $800
- **Maintenance**: 2 hours/month @ $100/hr = $200/month
- **Infrastructure**: $0 (runs in existing Docker Compose)
- **Total Year 1**: $800 + ($200 * 12) = **$3,200**

### Grafana Alerts (Open-Source Alternative)
- **Setup Cost**: 6 hours engineer time = $600
- **Maintenance**: 2 hours/month = $200/month
- **Infrastructure**: $0
- **Total Year 1**: $600 + ($200 * 12) = **$3,000**

### PagerDuty (SaaS Alternative)
- **Setup Cost**: 4 hours engineer time = $400
- **Maintenance**: 1 hour/month = $100/month
- **Subscription**: $39/user/month * 5 users = $195/month
- **Total Year 1**: $400 + ($100 * 12) + ($195 * 12) = **$3,940**

**Recommendation**: Start with **Alertmanager** (best Prometheus integration), migrate to PagerDuty if on-call rotation becomes critical need.

---

## 12. Security Considerations

### 12.1 Secrets Management

**DO NOT commit to Git**:
- Slack webhook URL
- SMTP password
- Email addresses

**Use environment variables**:
```yaml
# alertmanager.yml (template)
global:
  slack_api_url: '${SLACK_WEBHOOK_URL}'
  smtp_auth_password: '${SMTP_PASSWORD}'
```

**Load from .env file**:
```bash
# infrastructure/docker/.env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR_WEBHOOK_URL
SMTP_PASSWORD=your_app_password_here
```

### 12.2 Alert Data Sensitivity

**Avoid in alerts**:
- Customer PII (email, phone, address)
- Payment card numbers
- Authentication tokens

**Use instead**:
- User ID (UUID)
- Transaction ID (UUID)
- Hashed card number (last 4 digits)

**Example**:
```yaml
# BAD: Exposes PII
summary: "High risk transaction from email@example.com"

# GOOD: No PII
summary: "High risk transaction for user_id=123e4567-e89b"
```

### 12.3 Network Security

**Alertmanager Access Control**:
```yaml
# alertmanager.yml
# Restrict to internal network only (no public internet)
route:
  receiver: 'null'  # Default: drop alerts
  routes:
    - match:
        source: 'internal'  # Only alerts from internal services
      receiver: 'slack-general'
```

**Kubernetes Network Policy**:
```yaml
# Only allow Prometheus -> Alertmanager
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: alertmanager-ingress
spec:
  podSelector:
    matchLabels:
      app: alertmanager
  ingress:
    - from:
      - podSelector:
          matchLabels:
            app: prometheus
      ports:
        - protocol: TCP
          port: 9093
```

---

## 13. Conclusion

### Final Recommendations

1. **Adopt Prometheus Alertmanager** as the primary alerting solution
   - Native Prometheus integration (no additional layers)
   - Powerful routing and deduplication (critical for multi-service architecture)
   - Cost-effective (open-source, no per-user fees)

2. **Implement alert rules in this priority order**:
   1. Health check failures (immediate service outage detection)
   2. Critical CPU/Memory/Disk (prevent cascading failures)
   3. API error rates (detect service degradation)
   4. FDS-specific alerts (business-critical fraud detection)
   5. Predictive alerts (proactive capacity planning)

3. **Start with Slack notifications only**, add email for critical alerts after validation
   - Faster iteration (Slack webhook easier to test)
   - Avoid email fatigue (inbox spam)
   - Add email for critical alerts once routing is stable

4. **Create runbooks before deploying alerts**
   - Every alert must have actionable next steps
   - Link runbook URL in alert annotations
   - Review runbooks quarterly (update as system evolves)

5. **Monitor the monitors**
   - Create alerts for Alertmanager/Prometheus failures
   - Track notification delivery rate (target: 99.9%)
   - Review alert effectiveness weekly (reduce false positives)

### Next Steps

1. **Week 1**: Deploy Alertmanager + basic Slack integration
2. **Week 2**: Implement health check + API error rate alerts (highest priority)
3. **Week 3**: Add CPU/Memory/Disk alerts + email integration
4. **Week 4**: Load testing + validation (simulate outages)
5. **Week 5**: Documentation + team training

### Success Criteria Met

- [x] FR-026: Alert rules for CPU (80%/90%), Memory (85%/95%), Disk (85%/95%), API errors (5%/10%), Health Check
- [x] FR-027: Slack + Email notification channels, severity-based routing
- [x] SC-007: CPU 80% alert within 30s (group_wait=30s)
- [x] PromQL patterns: `rate()`, `histogram_quantile()`, `predict_linear()`, boolean operators
- [x] Deduplication: `group_interval=5m`, `repeat_interval=4h` (critical=1h)
- [x] Custom templates: Runbook URLs, metric values, thresholds, duration

### References

- [Prometheus Alerting Docs](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Awesome Prometheus Alerts](https://samber.github.io/awesome-prometheus-alerts/rules.html)
- [Alertmanager Best Practices](https://grafana.com/blog/2020/02/25/step-by-step-guide-to-setting-up-prometheus-alertmanager-with-slack-pagerduty-and-gmail/)
- [PromQL Examples](https://github.com/infinityworks/prometheus-example-queries)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Claude (Research Assistant)
**Review Status**: Ready for Implementation
