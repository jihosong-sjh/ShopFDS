# 모니터링 및 로깅 가이드

**작성일**: 2025-11-14
**Phase**: 9 - 마무리 및 교차 기능
**구현 완료**: T134-T136

---

## 목차

1. [개요](#개요)
2. [Prometheus 메트릭 수집](#prometheus-메트릭-수집)
3. [Grafana 대시보드](#grafana-대시보드)
4. [Sentry 에러 트래킹](#sentry-에러-트래킹)
5. [사용 방법](#사용-방법)
6. [모범 사례](#모범-사례)
7. [문제 해결](#문제-해결)

---

## 개요

ShopFDS 프로젝트는 3가지 핵심 모니터링 도구를 사용합니다:

| 도구 | 목적 | 포트 | URL |
|------|------|------|-----|
| **Prometheus** | 메트릭 수집 및 저장 | 9090 | http://localhost:9090 |
| **Grafana** | 메트릭 시각화 및 대시보드 | 3002 | http://localhost:3002 |
| **Sentry** | 에러 트래킹 및 성능 모니터링 | - | https://sentry.io |

### 핵심 목표

- **FDS 평가 시간**: P95 < 100ms
- **API 응답 시간**: P95 < 200ms
- **거래 처리량**: 1000 TPS (초당 거래)
- **에러율**: < 0.1% (99.9% 성공률)

---

## Prometheus 메트릭 수집

### 1. 메트릭 엔드포인트

각 서비스는 `/metrics` 엔드포인트를 통해 메트릭을 노출합니다:

```bash
# 이커머스 백엔드
curl http://localhost:8000/metrics

# FDS 서비스
curl http://localhost:8001/metrics

# ML 서비스
curl http://localhost:8002/metrics

# 관리자 대시보드
curl http://localhost:8003/metrics
```

### 2. 주요 메트릭

#### 이커머스 백엔드 (services/ecommerce/backend)

**HTTP 메트릭:**
- `ecommerce_http_requests_total`: 전체 HTTP 요청 수 (method, endpoint, status_code별)
- `ecommerce_http_request_duration_seconds`: 요청 처리 시간 (Histogram)
- `ecommerce_http_requests_in_progress`: 현재 처리 중인 요청 수 (Gauge)

**거래 메트릭:**
- `ecommerce_transactions_total`: 전체 거래 수 (status별)
- `ecommerce_transaction_amount_total`: 총 거래 금액 (원)
- `ecommerce_transaction_processing_duration_seconds`: 거래 처리 시간

**주문 메트릭:**
- `ecommerce_orders_total`: 전체 주문 수 (status별)
- `ecommerce_order_items_total`: 전체 주문 항목 수

**결제 메트릭:**
- `ecommerce_payments_total`: 전체 결제 시도 수 (status, payment_method별)
- `ecommerce_payment_amount_total`: 총 결제 금액 (원)

**사용자 메트릭:**
- `ecommerce_user_registrations_total`: 전체 회원가입 수
- `ecommerce_user_logins_total`: 전체 로그인 시도 수 (success/failed)
- `ecommerce_active_users`: 현재 활성 사용자 수

**캐시 메트릭:**
- `ecommerce_cache_operations_total`: 캐시 작업 수 (operation, result별)
- `ecommerce_cache_hit_ratio`: 캐시 히트율 (0.0 ~ 1.0)

**FDS 연동 메트릭:**
- `ecommerce_fds_evaluations_total`: FDS 평가 요청 수 (result별)
- `ecommerce_fds_evaluation_duration_seconds`: FDS 평가 소요 시간

#### FDS 서비스 (services/fds)

**FDS 평가 메트릭 (핵심):**
- `fds_evaluations_total`: 전체 FDS 평가 요청 수 (risk_level, decision별)
- `fds_evaluation_duration_seconds`: FDS 평가 처리 시간 (목표: P95 < 100ms)
- `fds_evaluation_latency_summary`: 지연 시간 요약 (P50, P90, P95, P99)
- `fds_evaluations_in_progress`: 현재 평가 중인 거래 수
- `fds_sla_violations_total`: SLA 위반 횟수 (100ms 초과)

**위험 점수 메트릭:**
- `fds_risk_score_distribution`: 위험 점수 분포 (0-100)
- `fds_risk_factors_triggered_total`: 위험 요인 발생 횟수
- `fds_risk_level_distribution_total`: 위험도별 거래 분포

**엔진별 메트릭:**
- `fds_rule_engine_duration_seconds`: 룰 엔진 실행 시간
- `fds_ml_engine_duration_seconds`: ML 엔진 실행 시간
- `fds_cti_engine_duration_seconds`: CTI 엔진 실행 시간
- `fds_engine_breakdown_seconds`: 엔진별 처리 시간 분해

**정확도 메트릭:**
- `fds_true_positives_total`: 정탐 (사기 거래를 올바르게 탐지)
- `fds_false_positives_total`: 오탐 (정상 거래를 사기로 오인)
- `fds_true_negatives_total`: 정상 거래를 올바르게 승인
- `fds_false_negatives_total`: 미탐 (사기 거래를 정상으로 오인)
- `fds_precision`: 정밀도 = TP / (TP + FP)
- `fds_recall`: 재현율 = TP / (TP + FN)
- `fds_f1_score`: F1 스코어

**의사결정 메트릭:**
- `fds_decisions_total`: FDS 의사결정 분포 (approve, auth, hold, block)
- `fds_blocked_transactions_total`: 차단된 거래 수 (reason별)
- `fds_additional_auth_required_total`: 추가 인증 요청 수

### 3. 코드 예시

#### 메트릭 기록 (Python)

```python
from src.utils.prometheus_metrics import (
    record_http_request,
    record_transaction,
    record_fds_evaluation,
    track_transaction_duration,
)

# HTTP 요청 기록
record_http_request(method="GET", endpoint="/v1/products", status_code=200)

# 거래 기록
record_transaction(status="completed", amount=50000)

# FDS 평가 기록
record_fds_evaluation(result="low_risk", duration=0.075)

# 데코레이터를 사용한 자동 추적
@track_transaction_duration("payment")
async def process_payment(order_id: str):
    # 결제 처리 로직
    pass
```

#### 메트릭 조회 (PromQL)

```promql
# FDS 평가 시간 P95 (5분 평균)
histogram_quantile(0.95, rate(fds_evaluation_duration_seconds_bucket[5m]))

# 분당 거래 처리량
rate(ecommerce_transactions_total[5m]) * 60

# 캐시 히트율
ecommerce_cache_hit_ratio

# 위험도별 거래 분포
sum by(risk_level) (rate(fds_evaluations_total[5m]))

# 엔진별 평균 실행 시간
rate(fds_rule_engine_duration_seconds_sum[5m]) / rate(fds_rule_engine_duration_seconds_count[5m])

# SLA 위반률 (100ms 초과 비율)
rate(fds_sla_violations_total[5m]) / rate(fds_evaluations_total[5m])
```

---

## Grafana 대시보드

### 1. 접속 및 로그인

```bash
# URL
http://localhost:3002

# 기본 계정
ID: admin
PW: admin (초기 설정 시 변경 가능)
```

### 2. 제공되는 대시보드

#### FDS Performance Dashboard (fds-performance)

**패널 구성:**
1. **FDS 평가 시간 P95** (Gauge): 목표 100ms 대비 현재 성능
2. **FDS 평가 지연 시간 추이** (Time Series): P50, P95, P99 추이
3. **거래 처리량** (Stat): 분당 거래 수
4. **SLA 위반** (Stat): 100ms 초과 횟수
5. **에러율** (Stat): 분당 에러 발생 수
6. **위험도별 거래 분포** (Pie Chart): low/medium/high/blocked
7. **엔진별 평균 실행 시간** (Time Series): Rule/ML/CTI 엔진
8. **FDS 탐지 정확도** (Time Series): Precision, Recall, F1 Score

**사용 사례:**
- FDS 성능 목표(100ms) 달성 여부 실시간 모니터링
- 엔진별 병목 구간 식별 (어떤 엔진이 느린지)
- 위험도 분포 트렌드 분석 (사기 거래 증가/감소)
- 탐지 정확도 추적 (오탐/미탐 개선)

#### Ecommerce Overview Dashboard (ecommerce-overview)

**패널 구성:**
1. **거래 처리량** (Stat): 분당 거래 수
2. **시간당 매출** (Stat): 완료된 거래 금액
3. **활성 사용자** (Stat): 현재 세션 수
4. **API 응답 시간 P95** (Stat): 목표 200ms 대비
5. **주문 상태별 추이** (Time Series): pending, processing, shipped, delivered
6. **HTTP 상태 코드별 요청 수** (Time Series): 2xx, 4xx, 5xx
7. **결제 상태 분포** (Pie Chart): completed, failed, pending
8. **캐시 히트율** (Time Series): 목표 80% 이상
9. **FDS 평가 결과 분포** (Time Series): low/medium/high risk

**사용 사례:**
- 비즈니스 지표 실시간 추적 (매출, 거래량)
- API 성능 모니터링 (응답 시간, 에러율)
- 캐시 효율성 분석
- FDS 연동 상태 확인

### 3. 알림 설정 (Alert Rules)

Grafana에서 알림 조건 설정:

```yaml
# FDS SLA 위반 알림
- name: FDS SLA Violation
  condition: fds_sla_violations_total > 100
  for: 5m
  annotations:
    summary: "FDS SLA 위반 (100ms 초과) 발생"
    description: "지난 5분간 {{ $value }}건의 SLA 위반"

# 에러율 급증 알림
- name: High Error Rate
  condition: rate(ecommerce_errors_total[5m]) > 10
  for: 5m
  annotations:
    summary: "에러율 급증"
    description: "분당 {{ $value }}개 에러 발생"

# FDS 탐지 정확도 저하 알림
- name: FDS Precision Drop
  condition: fds_precision < 0.8
  for: 10m
  annotations:
    summary: "FDS 정밀도 저하"
    description: "정밀도가 {{ $value }}로 떨어짐 (목표: 0.9)"
```

### 4. 커스텀 대시보드 생성

1. Grafana UI에서 **"Create" → "Dashboard"**
2. **"Add new panel"** 클릭
3. PromQL 쿼리 입력:

```promql
# 예시: 시간대별 거래량
sum by(hour) (
  rate(ecommerce_transactions_total[1h])
)
```

4. 시각화 타입 선택 (Time Series, Stat, Gauge, Pie Chart 등)
5. 패널 제목 및 설정 저장

---

## Sentry 에러 트래킹

### 1. Sentry 설정

#### 환경 변수 (.env)

```bash
# Sentry DSN (프로젝트별 고유 값)
SENTRY_DSN=https://your-key@o123456.ingest.sentry.io/789012

# 환경 구분
ENVIRONMENT=development  # development, staging, production

# 앱 버전 (릴리스 추적)
APP_VERSION=1.0.0
```

#### 초기화 (main.py)

```python
from src.utils.sentry_config import init_sentry

# FastAPI 앱 시작 시
@app.on_event("startup")
async def startup_event():
    init_sentry(
        dsn=os.getenv("SENTRY_DSN"),
        environment=os.getenv("ENVIRONMENT", "development"),
        enable_tracing=True,
        traces_sample_rate=1.0,  # 개발: 100%, 프로덕션: 10%
    )
```

### 2. 자동 에러 캡처

Sentry는 FastAPI 예외를 자동으로 캡처합니다:

```python
@app.get("/v1/products/{product_id}")
async def get_product(product_id: str):
    # 예외 발생 시 자동으로 Sentry에 전송됨
    product = await product_service.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
```

### 3. 수동 에러 캡처 (컨텍스트 추가)

```python
from src.utils.sentry_config import capture_exception_with_context

try:
    result = await process_payment(order_id)
except PaymentError as e:
    # 추가 컨텍스트와 함께 Sentry에 전송
    capture_exception_with_context(
        e,
        user_id=current_user.id,
        transaction_id=order_id,
        order_amount=order.total_amount,
        payment_method="card",
    )
    raise
```

### 4. FDS 전용 에러 캡처

```python
from src.utils.sentry_config import capture_fds_exception, capture_fds_performance_issue

# FDS 평가 중 예외
try:
    result = await evaluate_transaction(transaction)
except Exception as e:
    capture_fds_exception(
        e,
        transaction_id=transaction.id,
        risk_score=transaction.risk_score,
        engine="ml",  # 실패한 엔진
    )

# FDS 성능 이슈 (100ms 초과)
evaluation_time_ms = 125.5
capture_fds_performance_issue(
    duration_ms=evaluation_time_ms,
    threshold_ms=100.0,
    transaction_id=transaction.id,
    engine="cti",  # 지연 발생 엔진
)
```

### 5. Breadcrumbs (이벤트 경로 추적)

```python
from src.utils.sentry_config import add_breadcrumb, add_fds_breadcrumb

# 일반 Breadcrumb
add_breadcrumb(
    "User attempted payment",
    category="payment",
    level="info",
    data={"user_id": user.id, "amount": 50000}
)

# FDS Breadcrumb
add_fds_breadcrumb(
    "Rule engine evaluation completed",
    engine="rule",
    risk_score=45.0,
    decision="additional_auth_required",
)
```

### 6. 성능 트랜잭션 추적

```python
from src.utils.sentry_config import start_transaction

with start_transaction("process_order", op="order"):
    # 주문 처리 로직
    order = create_order(cart)
    payment = process_payment(order)
    send_confirmation(order)
```

### 7. Sentry 대시보드

Sentry 웹 UI (https://sentry.io)에서 확인 가능:

- **Issues**: 발생한 에러 목록 (빈도, 영향도별 정렬)
- **Performance**: 트랜잭션별 성능 분석
- **Releases**: 버전별 에러 추적
- **Alerts**: 에러 급증 시 알림

---

## 사용 방법

### 1. 개발 환경 실행

```bash
# Docker Compose로 모든 서비스 시작
cd infrastructure/docker
docker-compose -f docker-compose.dev.yml up -d

# Prometheus, Grafana, Sentry 포함
```

### 2. 메트릭 확인

**Prometheus:**
```bash
# 브라우저에서
http://localhost:9090

# Graph 탭에서 PromQL 쿼리 실행
histogram_quantile(0.95, rate(fds_evaluation_duration_seconds_bucket[5m]))
```

**Grafana:**
```bash
# 브라우저에서
http://localhost:3002

# Dashboards → ShopFDS → FDS Performance Dashboard
```

**Sentry:**
```bash
# 브라우저에서
https://sentry.io/organizations/your-org/issues/

# Issues, Performance 탭 확인
```

### 3. 운영 환경 모니터링 워크플로우

#### 일일 점검 (Daily Check)

1. **Grafana 대시보드 확인**
   - FDS Performance Dashboard: SLA 위반 횟수 확인
   - Ecommerce Overview: 매출, 거래량 트렌드 확인

2. **Sentry 이슈 확인**
   - 신규 에러 발생 여부
   - 재발 에러 패턴 분석

3. **Prometheus 알림 확인**
   - 임계값 초과 알림
   - 성능 저하 알림

#### 장애 대응 (Incident Response)

1. **알림 수신** (Grafana/Prometheus)
   - 예: "FDS SLA 위반 100건 초과"

2. **Grafana 대시보드로 이동**
   - FDS Performance Dashboard에서 원인 파악
   - 어떤 엔진이 느린지 확인 (Rule/ML/CTI)

3. **Sentry에서 에러 로그 확인**
   - 동일 시간대 에러 발생 여부
   - Stack trace 및 컨텍스트 분석

4. **Prometheus 쿼리로 상세 분석**
   ```promql
   # 엔진별 평균 실행 시간
   rate(fds_cti_engine_duration_seconds_sum[5m]) / rate(fds_cti_engine_duration_seconds_count[5m])

   # 예: CTI 엔진이 느린 경우 → 외부 API 타임아웃 의심
   ```

5. **조치 및 모니터링**
   - 캐시 설정 조정
   - 타임아웃 증가
   - 리소스 스케일링

---

## 모범 사례

### 1. 메트릭 수집

**DO:**
- 비즈니스 중요 메트릭 우선 (거래량, 매출, FDS 성능)
- Histogram 사용 시 적절한 버킷 설정 (0.01, 0.05, 0.1, ...)
- Label 카디널리티 낮게 유지 (high cardinality 주의)

**DON'T:**
- 불필요한 메트릭 과다 수집 (스토리지 낭비)
- Label에 UUID, 타임스탬프 등 포함 (카디널리티 폭발)
- 메트릭 이름 변경 (히스토리 단절)

### 2. 대시보드 설계

**DO:**
- 핵심 지표를 상단에 배치 (Stat 패널)
- 추세는 Time Series로 시각화
- 분포는 Histogram/Pie Chart 사용
- 알림 임계값을 대시보드에 표시 (Threshold Lines)

**DON'T:**
- 한 대시보드에 너무 많은 패널 (10개 이하 권장)
- 복잡한 PromQL 쿼리 남발 (성능 저하)
- 의미 없는 메트릭 시각화

### 3. 에러 트래킹

**DO:**
- 민감 정보 자동 마스킹 (before_send 필터)
- 에러에 충분한 컨텍스트 추가 (user_id, transaction_id)
- Breadcrumb로 이벤트 경로 추적
- 프로덕션에서 샘플링 비율 조정 (비용 절감)

**DON'T:**
- 개인정보를 Sentry에 전송 (GDPR 위반)
- 모든 로그를 Sentry로 전송 (Info 레벨 제외)
- 재귀 에러 무한 전송

### 4. 알림 설정

**DO:**
- 실행 가능한 알림만 설정 (Actionable Alerts)
- 알림 임계값을 점진적으로 조정
- 알림 채널 분리 (Critical → SMS, Warning → Slack)

**DON'T:**
- 너무 민감한 임계값 (알림 피로)
- 중복 알림 (같은 이슈에 여러 알림)
- 조치 불가능한 알림

---

## 문제 해결

### 1. Prometheus 메트릭이 수집되지 않음

**증상:**
- Prometheus Target Status가 "DOWN"
- Grafana에서 "No Data" 표시

**원인 및 해결:**
```bash
# 1. 서비스가 실행 중인지 확인
docker ps | grep ecommerce-backend

# 2. /metrics 엔드포인트 접근 가능한지 확인
curl http://localhost:8000/metrics

# 3. Prometheus 설정 확인
cat infrastructure/docker/prometheus.yml

# 4. 네트워크 연결 확인
docker network inspect shopfds-network

# 5. Prometheus 로그 확인
docker logs shopfds-prometheus
```

### 2. Grafana 대시보드가 비어있음

**원인 및 해결:**
```bash
# 1. Prometheus 데이터소스 연결 확인
# Grafana UI → Configuration → Data Sources → Prometheus
# URL: http://prometheus:9090

# 2. PromQL 쿼리 수동 실행
# Prometheus UI (http://localhost:9090) → Graph 탭
histogram_quantile(0.95, rate(fds_evaluation_duration_seconds_bucket[5m]))

# 3. 데이터 수집 시작 시간 확인 (최소 1분 대기)
# 4. Time Range 조정 (Last 1 hour → Last 5 minutes)
```

### 3. Sentry 이벤트가 전송되지 않음

**원인 및 해결:**
```python
# 1. DSN 확인
import os
print(os.getenv("SENTRY_DSN"))  # None이면 .env 파일 확인

# 2. Sentry 초기화 확인
from src.utils.sentry_config import init_sentry
init_sentry(dsn="your-dsn", environment="development")

# 3. 수동 이벤트 전송 테스트
import sentry_sdk
sentry_sdk.capture_message("Test message", level="info")

# 4. 네트워크 방화벽 확인
# Sentry로 아웃바운드 연결 가능한지 확인
curl https://o123456.ingest.sentry.io/api/789012/envelope/

# 5. 샘플링 비율 확인 (프로덕션에서 0.1이면 90% 이벤트 무시)
```

### 4. FDS SLA 목표(100ms) 미달성

**진단 프로세스:**

1. **Grafana에서 엔진별 시간 확인**
   ```promql
   rate(fds_rule_engine_duration_seconds_sum[5m]) / rate(fds_rule_engine_duration_seconds_count[5m])
   rate(fds_ml_engine_duration_seconds_sum[5m]) / rate(fds_ml_engine_duration_seconds_count[5m])
   rate(fds_cti_engine_duration_seconds_sum[5m]) / rate(fds_cti_engine_duration_seconds_count[5m])
   ```

2. **병목 엔진 식별**
   - Rule Engine > 30ms → 룰 수 감소 또는 최적화
   - ML Engine > 40ms → 모델 경량화 또는 Feature 수 감소
   - CTI Engine > 50ms → 캐시 히트율 증가, 타임아웃 단축

3. **조치 방안**
   ```python
   # CTI 캐시 TTL 증가
   CACHE_TTL = 3600  # 1시간

   # 룰 엔진 병렬화
   async def evaluate_rules(transaction):
       results = await asyncio.gather(
           *[rule.evaluate(transaction) for rule in active_rules]
       )

   # ML 모델 Feature 수 감소 (100개 → 50개)
   ```

---

## 부록

### A. 메트릭 명명 규칙

- **Counter**: `_total` 접미사 (예: `requests_total`)
- **Gauge**: 접미사 없음 (예: `active_users`)
- **Histogram**: `_seconds` 또는 `_bytes` (예: `duration_seconds`)
- **Summary**: `_summary` 접미사 (예: `latency_summary`)

### B. PromQL 치트시트

```promql
# Rate (초당 증가율)
rate(metric_total[5m])

# Increase (기간 내 증가량)
increase(metric_total[1h])

# Histogram Quantile (백분위수)
histogram_quantile(0.95, rate(metric_seconds_bucket[5m]))

# Sum by Label
sum by(label) (metric_total)

# Average
avg(metric_gauge)

# Division (비율 계산)
sum(metric_a) / sum(metric_b)
```

### C. Grafana 패널 타입 선택 가이드

| 데이터 유형 | 권장 패널 타입 |
|------------|---------------|
| 단일 최신 값 | Stat |
| 목표 달성 여부 | Gauge |
| 시간 추이 | Time Series |
| 분포/비율 | Pie Chart |
| 상위 N개 | Bar Chart |
| 맵 시각화 | Geomap |

---

## 결론

ShopFDS 프로젝트는 Prometheus, Grafana, Sentry를 통해:

1. **실시간 성능 모니터링**: FDS 100ms 목표 달성 여부 추적
2. **비즈니스 인사이트**: 거래량, 매출, 위험도 분포 시각화
3. **신속한 장애 대응**: 에러 발생 시 즉시 알림 및 컨텍스트 제공

모니터링과 로깅은 시스템 안정성과 성능 개선의 핵심입니다. 지속적으로 메트릭을 분석하고 임계값을 조정하여 최적의 상태를 유지하세요.
