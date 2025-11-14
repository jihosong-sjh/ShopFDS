"""
Prometheus 메트릭 수집 유틸리티

이커머스 백엔드의 주요 메트릭을 수집하고 Prometheus에 노출합니다.

주요 메트릭:
- 거래 처리량 (Counter)
- 거래 처리 시간 (Histogram)
- 활성 요청 수 (Gauge)
- HTTP 요청 수 및 응답 시간 (Counter, Histogram)
- 데이터베이스 연결 풀 상태 (Gauge)
- 캐시 히트/미스 비율 (Counter)
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
)
from functools import wraps
from typing import Callable
import time


# 커스텀 레지스트리 (기본 메트릭 제외)
registry = CollectorRegistry()

# ===========================
# 애플리케이션 정보
# ===========================
app_info = Info(
    "ecommerce_app",
    "Ecommerce Backend Application Info",
    registry=registry,
)
app_info.info(
    {
        "version": "1.0.0",
        "service": "ecommerce-backend",
        "environment": "production",
    }
)

# ===========================
# HTTP 요청 메트릭
# ===========================
http_requests_total = Counter(
    "ecommerce_http_requests_total",
    "전체 HTTP 요청 수",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "ecommerce_http_request_duration_seconds",
    "HTTP 요청 처리 시간 (초)",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    registry=registry,
)

http_requests_in_progress = Gauge(
    "ecommerce_http_requests_in_progress",
    "현재 처리 중인 HTTP 요청 수",
    ["method", "endpoint"],
    registry=registry,
)

# ===========================
# 거래 처리 메트릭
# ===========================
transactions_total = Counter(
    "ecommerce_transactions_total",
    "전체 거래 수",
    ["status"],  # pending, completed, failed, cancelled
    registry=registry,
)

transaction_amount_total = Counter(
    "ecommerce_transaction_amount_total",
    "총 거래 금액 (원)",
    ["status"],
    registry=registry,
)

transaction_processing_duration_seconds = Histogram(
    "ecommerce_transaction_processing_duration_seconds",
    "거래 처리 시간 (초)",
    ["type"],  # cart_to_order, payment, fulfillment
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    registry=registry,
)

# ===========================
# 주문 메트릭
# ===========================
orders_total = Counter(
    "ecommerce_orders_total",
    "전체 주문 수",
    ["status"],  # pending, processing, shipped, delivered, cancelled
    registry=registry,
)

order_items_total = Counter(
    "ecommerce_order_items_total",
    "전체 주문 항목 수",
    registry=registry,
)

# ===========================
# 결제 메트릭
# ===========================
payments_total = Counter(
    "ecommerce_payments_total",
    "전체 결제 시도 수",
    ["status", "payment_method"],  # completed, failed, pending
    registry=registry,
)

payment_amount_total = Counter(
    "ecommerce_payment_amount_total",
    "총 결제 금액 (원)",
    ["status", "payment_method"],
    registry=registry,
)

# ===========================
# 사용자 메트릭
# ===========================
user_registrations_total = Counter(
    "ecommerce_user_registrations_total",
    "전체 회원가입 수",
    registry=registry,
)

user_logins_total = Counter(
    "ecommerce_user_logins_total",
    "전체 로그인 시도 수",
    ["status"],  # success, failed
    registry=registry,
)

active_users = Gauge(
    "ecommerce_active_users",
    "현재 활성 사용자 수 (세션 기반)",
    registry=registry,
)

# ===========================
# 장바구니 메트릭
# ===========================
cart_operations_total = Counter(
    "ecommerce_cart_operations_total",
    "장바구니 작업 수",
    ["operation"],  # add, update, remove, clear
    registry=registry,
)

abandoned_carts_total = Counter(
    "ecommerce_abandoned_carts_total",
    "방치된 장바구니 수 (24시간 이상 미결제)",
    registry=registry,
)

# ===========================
# 데이터베이스 메트릭
# ===========================
database_connections = Gauge(
    "ecommerce_database_connections",
    "데이터베이스 연결 수",
    ["state"],  # active, idle, waiting
    registry=registry,
)

database_query_duration_seconds = Histogram(
    "ecommerce_database_query_duration_seconds",
    "데이터베이스 쿼리 실행 시간 (초)",
    ["operation"],  # select, insert, update, delete
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 1.0),
    registry=registry,
)

database_errors_total = Counter(
    "ecommerce_database_errors_total",
    "데이터베이스 에러 수",
    ["error_type"],  # connection, query, transaction
    registry=registry,
)

# ===========================
# Redis 캐시 메트릭
# ===========================
cache_operations_total = Counter(
    "ecommerce_cache_operations_total",
    "캐시 작업 수",
    ["operation", "result"],  # get/set/delete, hit/miss/success/error
    registry=registry,
)

cache_hit_ratio = Gauge(
    "ecommerce_cache_hit_ratio",
    "캐시 히트율 (0.0 ~ 1.0)",
    registry=registry,
)

# ===========================
# 에러 메트릭
# ===========================
errors_total = Counter(
    "ecommerce_errors_total",
    "애플리케이션 에러 수",
    ["error_type", "severity"],  # 4xx, 5xx, exception / info, warning, error, critical
    registry=registry,
)

# ===========================
# FDS 연동 메트릭
# ===========================
fds_evaluations_total = Counter(
    "ecommerce_fds_evaluations_total",
    "FDS 평가 요청 수",
    ["result"],  # low_risk, medium_risk, high_risk, blocked, error
    registry=registry,
)

fds_evaluation_duration_seconds = Histogram(
    "ecommerce_fds_evaluation_duration_seconds",
    "FDS 평가 소요 시간 (초)",
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0),
    registry=registry,
)


# ===========================
# 데코레이터 유틸리티
# ===========================
def track_request_duration(method: str, endpoint: str):
    """HTTP 요청 처리 시간을 추적하는 데코레이터"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                http_request_duration_seconds.labels(
                    method=method, endpoint=endpoint
                ).observe(duration)
                return result
            finally:
                http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()

        return wrapper

    return decorator


def track_transaction_duration(transaction_type: str):
    """거래 처리 시간을 추적하는 데코레이터"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                transaction_processing_duration_seconds.labels(
                    type=transaction_type
                ).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                transaction_processing_duration_seconds.labels(
                    type=transaction_type
                ).observe(duration)
                errors_total.labels(
                    error_type="transaction_error", severity="error"
                ).inc()
                raise

        return wrapper

    return decorator


def track_database_query(operation: str):
    """데이터베이스 쿼리 실행 시간을 추적하는 데코레이터"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                database_query_duration_seconds.labels(operation=operation).observe(
                    duration
                )
                return result
            except Exception as e:
                database_errors_total.labels(error_type="query").inc()
                raise

        return wrapper

    return decorator


# ===========================
# 메트릭 노출 함수
# ===========================
def get_metrics() -> bytes:
    """Prometheus가 수집할 수 있는 형식으로 메트릭 반환"""
    return generate_latest(registry)


def get_content_type() -> str:
    """Prometheus 메트릭 Content-Type 반환"""
    return CONTENT_TYPE_LATEST


# ===========================
# 편의 함수
# ===========================
def record_http_request(method: str, endpoint: str, status_code: int):
    """HTTP 요청 기록"""
    http_requests_total.labels(
        method=method, endpoint=endpoint, status_code=status_code
    ).inc()


def record_transaction(status: str, amount: float = 0.0):
    """거래 기록"""
    transactions_total.labels(status=status).inc()
    if amount > 0:
        transaction_amount_total.labels(status=status).inc(amount)


def record_order(status: str, item_count: int = 1):
    """주문 기록"""
    orders_total.labels(status=status).inc()
    order_items_total.inc(item_count)


def record_payment(status: str, payment_method: str, amount: float = 0.0):
    """결제 기록"""
    payments_total.labels(status=status, payment_method=payment_method).inc()
    if amount > 0:
        payment_amount_total.labels(status=status, payment_method=payment_method).inc(
            amount
        )


def record_user_registration():
    """회원가입 기록"""
    user_registrations_total.inc()


def record_login(success: bool):
    """로그인 기록"""
    status = "success" if success else "failed"
    user_logins_total.labels(status=status).inc()


def record_cart_operation(operation: str):
    """장바구니 작업 기록"""
    cart_operations_total.labels(operation=operation).inc()


def record_cache_operation(operation: str, hit: bool = None, success: bool = True):
    """캐시 작업 기록"""
    if operation == "get":
        result = "hit" if hit else "miss"
    else:
        result = "success" if success else "error"
    cache_operations_total.labels(operation=operation, result=result).inc()


def record_fds_evaluation(result: str, duration: float):
    """FDS 평가 기록"""
    fds_evaluations_total.labels(result=result).inc()
    fds_evaluation_duration_seconds.observe(duration)


def record_error(error_type: str, severity: str = "error"):
    """에러 기록"""
    errors_total.labels(error_type=error_type, severity=severity).inc()
