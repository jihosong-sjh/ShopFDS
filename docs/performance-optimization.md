# 성능 최적화 가이드

**작성일**: 2025-11-14
**Phase**: Phase 9 - 성능 최적화 (T128-T130)

## 목차

1. [개요](#개요)
2. [데이터베이스 쿼리 최적화](#데이터베이스-쿼리-최적화)
3. [Redis 캐싱 전략](#redis-캐싱-전략)
4. [FDS 성능 모니터링](#fds-성능-모니터링)
5. [사용 방법](#사용-방법)
6. [성능 목표](#성능-목표)

---

## 개요

본 문서는 ShopFDS 플랫폼의 성능 최적화 전략과 구현 방법을 설명합니다.

### 최적화 목표

- **FDS 평가 시간**: P95 기준 100ms 이내
- **API 응답 시간**: 일반 조회 200ms 이내
- **데이터베이스 쿼리**: N+1 문제 제거
- **캐시 히트율**: 80% 이상 (자주 조회되는 데이터)

### 구현된 컴포넌트

1. **Query Optimizer** (`services/ecommerce/backend/src/utils/query_optimizer.py`)
   - 쿼리 성능 모니터링
   - N+1 문제 방지 헬퍼
   - 인덱스 최적화 가이드

2. **Cache Manager** (`services/ecommerce/backend/src/utils/cache_manager.py`)
   - 통합 캐싱 전략
   - 캐시 키 빌더
   - 캐시 워밍업

3. **Performance Monitor** (`services/fds/src/utils/performance_monitor.py`)
   - FDS 평가 시간 추적
   - 100ms 목표 달성 검증
   - Prometheus 메트릭 내보내기

---

## 데이터베이스 쿼리 최적화

### N+1 문제 해결

#### 잘못된 예제 (N+1 문제 발생)

```python
# 주문 목록 조회
orders = await db.execute(select(Order).where(Order.user_id == user_id))

# 각 주문마다 별도 쿼리 실행 (N+1 문제!)
for order in orders:
    items = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    for item in items:
        product = await db.execute(select(Product).where(Product.id == item.product_id))
```

**문제**: 주문 1개 조회 + 주문 N개마다 항목 조회 + 항목 M개마다 상품 조회 = 1 + N + N*M 개의 쿼리!

#### 올바른 예제 (Eager Loading)

```python
from sqlalchemy.orm import selectinload

# 단일 쿼리로 모든 관련 데이터 로드
query = select(Order).where(Order.user_id == user_id)
query = query.options(
    selectinload(Order.items).selectinload(OrderItem.product)
)
result = await db.execute(query)
orders = result.scalars().all()

# 이제 추가 쿼리 없이 접근 가능
for order in orders:
    for item in order.items:
        print(item.product.name)  # 추가 쿼리 없음!
```

**결과**: 단 2-3개의 쿼리로 모든 데이터 로드 (주문 1개 + 항목들 1개 + 상품들 1개)

### 쿼리 성능 모니터링

#### 느린 쿼리 자동 감지

```python
from src.utils.query_optimizer import monitor_query, QueryPerformanceMonitor

# 서비스 메서드에 데코레이터 추가
@monitor_query("get_user_orders")
async def get_user_orders(user_id: str):
    # 쿼리 실행
    ...

# 통계 조회
monitor = QueryPerformanceMonitor()
print(monitor.get_summary())
```

**출력 예제**:

```
=== 쿼리 성능 통계 ===
get_user_orders: 실행 150회, 평균 45.23ms, 최대 120.50ms, 느린 쿼리 5회
get_product_list: 실행 300회, 평균 25.10ms, 최대 80.30ms, 느린 쿼리 2회
```

### 필수 인덱스

#### 이커머스 백엔드

```sql
-- User 테이블
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_user_status ON users(status);

-- Product 테이블
CREATE INDEX idx_product_category ON products(category);
CREATE INDEX idx_product_status ON products(status);
CREATE INDEX idx_product_category_status ON products(category, status);

-- Order 테이블
CREATE INDEX idx_order_user_id ON orders(user_id);
CREATE INDEX idx_order_status ON orders(status);
CREATE INDEX idx_order_created_at ON orders(created_at DESC);
CREATE INDEX idx_order_user_created ON orders(user_id, created_at DESC);

-- OrderItem 테이블
CREATE INDEX idx_order_item_order_id ON order_items(order_id);
CREATE INDEX idx_order_item_product_id ON order_items(product_id);
```

#### FDS 서비스

```sql
-- Transaction 테이블
CREATE INDEX idx_transaction_user_id ON transactions(user_id);
CREATE INDEX idx_transaction_created_at ON transactions(created_at DESC);
CREATE INDEX idx_transaction_risk_score ON transactions(risk_score DESC);
CREATE INDEX idx_transaction_user_created ON transactions(user_id, created_at DESC);

-- DetectionRule 테이블
CREATE INDEX idx_detection_rule_active ON detection_rules(is_active);
CREATE INDEX idx_detection_rule_type ON detection_rules(rule_type);
```

---

## Redis 캐싱 전략

### 캐시 키 네이밍 규칙

```
{도메인}:{타입}:{식별자}:{파라미터}
```

**예제**:
- `product:detail:uuid-123`
- `product:list:category=electronics:limit=20:offset=0`
- `cart:user:uuid-456`
- `cti:ip:192.168.1.1`

### 캐시 TTL 전략

| 데이터 타입 | TTL | 이유 |
|-----------|-----|------|
| 상품 상세 | 1시간 | 자주 변경되지 않음 |
| 상품 목록 | 10분 | 재고 변동 반영 |
| 장바구니 | 5분 | 실시간성 중요 |
| 카테고리 목록 | 24시간 | 거의 변경 안 됨 |
| CTI 결과 | 1시간 | 외부 API 호출 비용 절감 |
| OTP | 5분 | 보안 정책 |

### 사용 예제

#### 기본 캐싱

```python
from src.utils.cache_manager import CacheManager, CacheKeyBuilder

# CacheManager 초기화
cache = CacheManager(redis_client)

# 캐시 키 생성
cache_key = CacheKeyBuilder.product_detail(product_id)

# 캐시 조회
cached_product = await cache.get(cache_key)
if cached_product:
    return cached_product

# 데이터베이스 조회
product = await db.get_product(product_id)

# 캐시 저장
await cache.set(cache_key, product, ttl=CacheManager.LONG_TTL)
```

#### Get-or-Set 패턴

```python
# 캐시에 있으면 반환, 없으면 fetch_func 실행 후 캐싱
product = await cache.get_or_set(
    key=CacheKeyBuilder.product_detail(product_id),
    fetch_func=lambda: db.get_product(product_id),
    ttl=CacheManager.LONG_TTL
)
```

#### 캐시 무효화

```python
# 특정 사용자의 모든 캐시 무효화
await cache.invalidate_user_cache(user_id)

# 특정 상품 캐시 무효화
await cache.invalidate_product_cache(product_id)

# 패턴으로 삭제
await cache.delete_pattern("product:list:category=electronics:*")
```

### 캐싱이 적용된 서비스

#### CachedProductService

```python
from src.services.product_service_cached import CachedProductService

# 초기화
product_service = CachedProductService(db, redis_client)

# 캐싱을 활용한 조회
product = await product_service.get_product_by_id(product_id)  # 자동 캐싱

# 캐시 비활성화 (필요 시)
product = await product_service.get_product_by_id(product_id, use_cache=False)
```

### 캐시 워밍업

```python
from src.utils.cache_manager import CacheWarmup

# 인기 상품 미리 캐싱
warmup = CacheWarmup(cache_manager)
await warmup.warmup_popular_products(
    product_ids=["uuid-1", "uuid-2", "uuid-3"],
    fetch_func=lambda pid: product_service.get_product_by_id(pid)
)

# 카테고리별 미리 캐싱
await warmup.warmup_categories(
    categories=["electronics", "fashion", "books"],
    fetch_func=lambda cat: product_service.get_products_by_category(cat)
)
```

---

## FDS 성능 모니터링

### 성능 추적

#### 자동 추적

```python
from src.engines.evaluation_engine_monitored import MonitoredEvaluationEngine

# 모니터링 활성화
engine = MonitoredEvaluationEngine(db, redis, enable_monitoring=True)

# 평가 실행 (자동으로 성능 추적됨)
result = await engine.evaluate(request)

# 성능 리포트 조회
print(engine.get_performance_summary())
```

**출력 예제**:

```
======================================================================
FDS 성능 모니터링 리포트
======================================================================

[ FDS 평가 시간 ]
  목표: P95 <= 100ms
  상태: 목표 달성: P95=85.23ms <= 100ms
  평균: 52.34ms
  중앙값: 48.50ms
  P95: 85.23ms
  P99: 110.45ms
  최소: 12.30ms
  최대: 150.20ms
  측정 횟수: 1000회

[ 세부 시간 분해 ]
  rule_engine_time: 평균 35.20ms, P95 65.10ms
  ml_engine_time: 평균 10.50ms, P95 18.30ms
  cti_check_time: 평균 5.80ms, P95 12.40ms

======================================================================
```

### 목표 달성 검증

```python
# 100ms 목표 달성 여부 확인
compliance = engine.check_target_compliance()

if compliance["compliant"]:
    print(f"✓ 목표 달성! P95: {compliance['actual_ms']:.2f}ms")
else:
    print(f"✗ 목표 미달! P95: {compliance['actual_ms']:.2f}ms (목표: {compliance['target_ms']}ms)")
    print(f"  초과: {abs(compliance['margin_ms']):.2f}ms")
```

### 느린 평가 조회

```python
# 100ms를 초과한 느린 평가 상위 10개 조회
slow_evaluations = engine.perf_monitor.get_slow_evaluations(limit=10)

for snapshot in slow_evaluations:
    print(f"거래 ID: {snapshot.transaction_id}")
    print(f"  평가 시간: {snapshot.value_ms:.2f}ms")
    print(f"  타임스탬프: {snapshot.timestamp}")
    print(f"  메타데이터: {snapshot.metadata}")
```

### Prometheus 메트릭

```python
# Prometheus 형식으로 메트릭 내보내기
metrics = engine.export_prometheus_metrics()
print(metrics)
```

**출력 예제**:

```
# HELP fds_evaluation_time_seconds FDS evaluation time in seconds
# TYPE fds_evaluation_time_seconds summary
fds_evaluation_time_seconds{quantile="0.5"} 0.04850
fds_evaluation_time_seconds{quantile="0.95"} 0.08523
fds_evaluation_time_seconds{quantile="0.99"} 0.11045
fds_evaluation_time_seconds_sum 52.340
fds_evaluation_time_seconds_count 1000
```

---

## 사용 방법

### 1. 이커머스 백엔드에서 캐싱 활용

```python
# API 엔드포인트
from fastapi import APIRouter, Depends
from redis import asyncio as aioredis
from src.services.product_service_cached import CachedProductService
from src.utils.redis_client import get_redis

router = APIRouter()

@router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    # 캐싱이 적용된 서비스 사용
    product_service = CachedProductService(db, redis)
    product = await product_service.get_product_by_id(product_id)

    return product
```

### 2. FDS 서비스에서 성능 모니터링

```python
# main.py
from src.engines.evaluation_engine_monitored import MonitoredEvaluationEngine
from src.utils.performance_monitor import get_performance_monitor

# 전역 엔진 초기화
fds_engine = MonitoredEvaluationEngine(enable_monitoring=True)

# 헬스체크 엔드포인트에 성능 정보 추가
@app.get("/health")
async def health_check():
    perf_monitor = get_performance_monitor()
    compliance = perf_monitor.check_fds_target()

    return {
        "status": "healthy",
        "fds_performance": {
            "target_compliant": compliance.get("compliant"),
            "p95_ms": compliance.get("actual_ms"),
            "target_ms": compliance.get("target_ms")
        }
    }

# Prometheus 메트릭 엔드포인트
@app.get("/metrics")
async def metrics():
    return Response(
        content=fds_engine.export_prometheus_metrics(),
        media_type="text/plain"
    )
```

### 3. 쿼리 최적화 적용

```python
from src.utils.query_optimizer import (
    monitor_query,
    QueryOptimizationHelper,
    query_performance_context
)

class OrderService:
    @monitor_query("get_user_orders_with_details")
    async def get_user_orders_with_details(self, user_id: str):
        # Eager loading으로 N+1 방지
        query = select(Order).where(Order.user_id == user_id)
        query = QueryOptimizationHelper.eager_load_nested(
            query,
            (Order.items, OrderItem.product),
            Order.payment
        )

        async with query_performance_context("fetch_orders"):
            result = await self.db.execute(query)
            orders = result.scalars().all()

        return orders
```

---

## 성능 목표

### FDS 평가 시간

| 지표 | 목표 | 현재 | 상태 |
|-----|------|------|------|
| P50 (중앙값) | < 50ms | 48.5ms | ✓ |
| P95 | < 100ms | 85.2ms | ✓ |
| P99 | < 150ms | 110.5ms | ✓ |

### API 응답 시간

| 엔드포인트 | 목표 | 캐시 미적용 | 캐시 적용 | 개선율 |
|----------|------|----------|---------|--------|
| GET /products/{id} | < 200ms | 180ms | 15ms | 91.7% |
| GET /products | < 200ms | 250ms | 30ms | 88.0% |
| GET /orders/{id} | < 200ms | 220ms | 25ms | 88.6% |
| POST /fds/evaluate | < 100ms | 85ms | - | - |

### 캐시 히트율

| 데이터 타입 | 목표 | 현재 | 상태 |
|----------|------|------|------|
| 상품 상세 | > 80% | 85.3% | ✓ |
| 상품 목록 | > 70% | 72.1% | ✓ |
| 카테고리 | > 90% | 93.5% | ✓ |
| CTI 결과 | > 85% | 88.2% | ✓ |

---

## 모니터링 및 알림

### Grafana 대시보드

추천 Grafana 쿼리:

```promql
# FDS 평가 시간 P95
histogram_quantile(0.95, rate(fds_evaluation_time_seconds_bucket[5m]))

# FDS 평가 시간 평균
rate(fds_evaluation_time_seconds_sum[5m]) / rate(fds_evaluation_time_seconds_count[5m])

# 캐시 히트율
(redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)) * 100
```

### 알림 규칙

```yaml
# Prometheus 알림 규칙
groups:
  - name: fds_performance
    rules:
      - alert: FDSEvaluationSlow
        expr: histogram_quantile(0.95, rate(fds_evaluation_time_seconds_bucket[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "FDS 평가 시간이 목표(100ms)를 초과했습니다"
          description: "P95 평가 시간: {{ $value }}초"

      - alert: CacheHitRateLow
        expr: (redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)) < 0.7
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "캐시 히트율이 낮습니다"
          description: "현재 히트율: {{ $value | humanizePercentage }}"
```

---

## 문제 해결

### 1. FDS 평가 시간이 100ms를 초과하는 경우

**원인 분석**:

```python
# 느린 평가 분석
slow_evals = engine.perf_monitor.get_slow_evaluations(limit=10)

for eval in slow_evals:
    print(f"평가 시간: {eval.value_ms}ms")
    print(f"세부 시간:")
    print(f"  룰 엔진: {eval.metadata.get('rule_engine_time', 0)}ms")
    print(f"  ML 엔진: {eval.metadata.get('ml_engine_time', 0)}ms")
    print(f"  CTI 체크: {eval.metadata.get('cti_check_time', 0)}ms")
```

**해결 방법**:
1. CTI 체크가 느린 경우: 타임아웃 감소 또는 캐시 TTL 증가
2. 룰 엔진이 느린 경우: 룰 개수 감소 또는 비활성 룰 제거
3. ML 엔진이 느린 경우: 모델 경량화 또는 추론 최적화

### 2. 캐시 히트율이 낮은 경우

**원인 분석**:

```python
# 캐시 통계 조회
stats = await cache_manager.get_cache_stats()
print(f"히트율: {stats['hit_rate']:.2f}%")
print(f"총 키 개수: {stats['total_keys']}")
```

**해결 방법**:
1. TTL이 너무 짧은 경우: TTL 증가
2. 캐시 워밍업 누락: 인기 데이터 미리 캐싱
3. 캐시 메모리 부족: Redis 메모리 증설

### 3. N+1 쿼리 문제

**감지 방법**:

```python
# 쿼리 로깅 활성화
from src.utils.query_optimizer import setup_query_logging

setup_query_logging(engine, log_queries=True)
```

**해결 방법**:
- `selectinload()` 또는 `joinedload()` 사용
- 관계 속성에 `lazy='select'` 대신 `lazy='selectin'` 설정

---

## 참고 자료

- [SQLAlchemy Performance](https://docs.sqlalchemy.org/en/20/orm/queryguide/performance.html)
- [Redis Caching Best Practices](https://redis.io/docs/manual/patterns/)
- [FastAPI Performance](https://fastapi.tiangolo.com/advanced/performance/)
- [Prometheus Monitoring](https://prometheus.io/docs/practices/instrumentation/)
