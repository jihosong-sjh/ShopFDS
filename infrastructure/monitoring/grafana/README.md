# Grafana Dashboards for ShopFDS

## Overview

ShopFDS Grafana 대시보드는 FDS(Fraud Detection System) 성능 지표 및 사기 탐지율을 실시간으로 모니터링하기 위한 종합 대시보드입니다.

## Dashboards

### 1. FDS Performance & Fraud Detection Dashboard

**파일**: `dashboards/fds-performance-dashboard.json`

#### 주요 메트릭

##### 성능 지표
- **FDS Evaluation Time (P50/P95/P99)**: FDS 평가 시간 백분위수
  - Target: P95 < 50ms
  - 시간대별 추이 확인
  - 성능 저하 시점 식별

- **FDS Evaluation Throughput**: 초당 FDS 평가 처리량
  - 실시간 TPS 모니터링
  - 부하 패턴 분석

- **FDS P95 Latency**: P95 지연 시간 게이지
  - 목표: 50ms 이내
  - 50ms 이상: 노란색
  - 100ms 이상: 빨간색

- **Cache Hit Rate**: 캐시 히트율 게이지
  - 목표: 85% 이상
  - 80% 이상: 노란색
  - 85% 이상: 초록색

- **Total Evaluations (24h)**: 24시간 총 평가 건수
  - 일일 처리량 확인
  - 트래픽 패턴 분석

- **Total Errors (1h)**: 1시간 총 에러 건수
  - 100건 이상: 노란색
  - 500건 이상: 빨간색

##### 사기 탐지 지표
- **Fraud Detection by Risk Level (1h)**: 위험 수준별 사기 탐지 분포
  - Low/Medium/High 비율 확인
  - Donut Chart로 시각화

- **FDS Decisions Distribution (1h)**: 의사결정 분포
  - Approve/Block/Additional Auth 비율
  - 추가 인증 비율로 사용자 경험 측정

- **Fraud Detections by Source (1h)**: 탐지 소스별 사기 건수
  - Rule/ML/Network/Behavior/Fingerprint
  - 어느 탐지 방법이 가장 효과적인지 확인

- **Blocked Transactions by Reason (1h)**: 차단 사유별 거래 건수
  - High Risk/Blacklist/Rule Block/ML Anomaly
  - 차단 이유 분석

##### 엔진별 성능
- **Engine Evaluation Time P95 (by Engine Type)**: 엔진별 P95 평가 시간
  - Fingerprint/Behavior/Network/Rule/ML 각각 모니터링
  - 병목 엔진 식별

- **ML Inference Time P95 (by Model Type)**: ML 모델별 P95 추론 시간
  - Random Forest/XGBoost/Autoencoder/LSTM/Ensemble
  - 모델 최적화 필요성 판단

##### 운영 지표
- **Cache Hit Rate by Type**: 캐시 타입별 히트율
  - Device/IP/Rule/ML/Geo 각각 추적
  - 캐시 전략 최적화

- **Errors by Type (1h)**: 에러 타입별 발생 건수
  - Timeout/Exception/Validation
  - 에러 원인 분석

- **Database Connection Pool**: 데이터베이스 연결 풀 상태
  - Active/Idle 연결 수 모니터링
  - 연결 부족 또는 누수 감지

- **API Request Rate by Endpoint**: 엔드포인트별 API 요청률
  - 가장 많이 사용되는 API 확인
  - 부하 분산 필요성 판단

## Installation

### 1. Docker Compose로 Grafana 실행

```bash
cd infrastructure/monitoring

# Grafana 컨테이너 시작
docker-compose up -d grafana
```

### 2. Grafana 접속

- URL: `http://localhost:3000`
- 기본 계정:
  - Username: `admin`
  - Password: `admin`

### 3. 대시보드 확인

자동 프로비저닝된 대시보드는 **FDS** 폴더에서 확인 가능:

1. 왼쪽 메뉴 > **Dashboards** 클릭
2. **FDS** 폴더 선택
3. **FDS Performance & Fraud Detection Dashboard** 클릭

## Configuration

### Prometheus Data Source

Grafana는 Prometheus를 데이터 소스로 사용합니다.

**설정 파일**: `provisioning/datasources/prometheus.yml`

```yaml
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
```

### Dashboard Provisioning

대시보드는 자동으로 프로비저닝됩니다.

**설정 파일**: `provisioning/dashboards/dashboard.yml`

```yaml
providers:
  - name: 'FDS Dashboards'
    folder: 'FDS'
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
```

## Metrics Reference

### FDS Evaluation Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `fds_evaluation_duration_seconds` | Histogram | `engine_type` | FDS 평가 시간 (초) |
| `fds_evaluations_total` | Counter | `risk_level`, `decision` | FDS 평가 총 횟수 |
| `fds_risk_score` | Summary | - | FDS 위험 점수 통계 |

### ML Model Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ml_inference_duration_seconds` | Histogram | `model_type` | ML 모델 추론 시간 (초) |
| `ml_predictions_total` | Counter | `model_type`, `prediction` | ML 예측 총 횟수 |

### Rule Engine Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `rule_executions_total` | Counter | `rule_category`, `matched` | 룰 실행 총 횟수 |
| `rule_matches_total` | Counter | `rule_category`, `action` | 룰 매칭 총 횟수 |

### Cache Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `cache_hit_rate` | Gauge | `cache_type` | Redis 캐시 히트율 (0~1) |
| `cache_lookups_total` | Counter | `cache_type`, `result` | 캐시 조회 총 횟수 |

### API Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `api_requests_total` | Counter | `method`, `endpoint`, `status_code` | API 요청 총 횟수 |
| `api_response_duration_seconds` | Histogram | `method`, `endpoint` | API 응답 시간 (초) |

### Fraud Detection Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `fraud_detections_total` | Counter | `detection_source` | 사기 탐지 총 횟수 |
| `transactions_blocked_total` | Counter | `block_reason` | 차단된 거래 총 횟수 |

### System Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `db_connections_active` | Gauge | - | 활성 데이터베이스 연결 수 |
| `db_connections_idle` | Gauge | - | 유휴 데이터베이스 연결 수 |
| `fds_errors_total` | Counter | `error_type`, `engine` | FDS 에러 발생 총 횟수 |

## Alert Rules (예정)

향후 AlertManager 통합 시 다음 알림 규칙 적용 예정:

1. **High P95 Latency**: FDS P95 > 100ms (5분 이상)
2. **Low Cache Hit Rate**: Cache Hit Rate < 70% (10분 이상)
3. **High Error Rate**: Error Count > 1000/hour
4. **High Fraud Detection Rate**: Fraud Rate > 20% (1시간 이상)
5. **DB Connection Pool Exhaustion**: Active Connections > 90% of Max Pool

## Customization

### Adding New Panels

1. Grafana UI에서 대시보드 편집
2. **Add Panel** 클릭
3. Prometheus 쿼리 작성
4. 시각화 타입 선택 (Graph/Gauge/Stat/Pie Chart)
5. **Save** 클릭

### Exporting Dashboard

```bash
# Grafana UI에서 대시보드 설정 > JSON Model > Copy to Clipboard
# JSON을 파일로 저장
cat > custom-dashboard.json <<EOF
{...}
EOF
```

## Troubleshooting

### Dashboard가 보이지 않음

1. Grafana 로그 확인:
   ```bash
   docker-compose logs -f grafana
   ```

2. 프로비저닝 경로 확인:
   ```bash
   docker exec -it grafana ls /etc/grafana/provisioning/dashboards
   ```

### Prometheus 데이터가 없음

1. Prometheus 연결 확인:
   ```bash
   curl http://localhost:9090/api/v1/query?query=up
   ```

2. FDS 서비스 메트릭 확인:
   ```bash
   curl http://localhost:8001/metrics
   ```

### 메트릭이 갱신되지 않음

1. Grafana에서 **Refresh Interval** 확인 (기본: 10s)
2. Prometheus Scrape Interval 확인 (기본: 15s)
3. 시간 범위 확인 (기본: Last 1 hour)

## Best Practices

1. **적절한 시간 범위 선택**: 실시간 모니터링은 Last 1h, 트렌드 분석은 Last 24h
2. **Panel별 Refresh Interval 조정**: 중요한 메트릭은 5s, 덜 중요한 메트릭은 30s
3. **Threshold 설정**: 게이지/그래프에 임계값 표시로 이상 징후 쉽게 파악
4. **Alerting 활성화**: 중요한 메트릭에 Alert Rule 설정
5. **Dashboard 최적화**: 너무 많은 Panel은 성능 저하 유발 (최대 20개 권장)

## Resources

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)

## Support

문제 발생 시 다음 정보 제공:
1. Grafana 버전
2. 에러 로그 (`docker-compose logs grafana`)
3. Prometheus 쿼리 결과
4. 스크린샷
