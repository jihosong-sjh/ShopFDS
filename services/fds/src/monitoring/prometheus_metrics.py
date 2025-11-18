"""
Prometheus 메트릭 수집

FDS 평가 성능, 사기 탐지율, 시스템 메트릭을 Prometheus 형식으로 제공합니다.

**메트릭 카테고리**:
- FDS 평가 시간 (히스토그램)
- ML 모델 추론 시간 (히스토그램)
- 위험 수준별 거래 분포 (카운터)
- 의사결정별 분포 (카운터)
- 캐시 히트율 (게이지)
- API 요청 수 (카운터)
- 에러 발생 수 (카운터)

**Prometheus 엔드포인트**:
- GET /metrics - Prometheus scrape 엔드포인트
"""

import logging
from typing import Dict
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from prometheus_client import CollectorRegistry
from fastapi import Response

logger = logging.getLogger(__name__)

# Prometheus Registry (전역)
registry = CollectorRegistry()


# === FDS 평가 메트릭 ===

# FDS 평가 시간 (히스토그램)
fds_evaluation_duration = Histogram(
    name="fds_evaluation_duration_seconds",
    documentation="FDS 평가 소요 시간 (초)",
    buckets=(
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ),  # 10ms ~ 10초
    labelnames=["engine_type"],  # fingerprint, behavior, network, rule, ml
    registry=registry,
)

# FDS 평가 카운터 (위험 수준별)
fds_evaluations_total = Counter(
    name="fds_evaluations_total",
    documentation="FDS 평가 총 횟수 (위험 수준별)",
    labelnames=[
        "risk_level",
        "decision",
    ],  # low/medium/high, approve/block/additional_auth
    registry=registry,
)

# FDS 위험 점수 (요약 통계)
fds_risk_score = Summary(
    name="fds_risk_score",
    documentation="FDS 위험 점수 통계",
    registry=registry,
)


# === ML 모델 메트릭 ===

# ML 모델 추론 시간 (히스토그램)
ml_inference_duration = Histogram(
    name="ml_inference_duration_seconds",
    documentation="ML 모델 추론 시간 (초)",
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    labelnames=["model_type"],  # random_forest, xgboost, autoencoder, lstm, ensemble
    registry=registry,
)

# ML 예측 결과 카운터
ml_predictions_total = Counter(
    name="ml_predictions_total",
    documentation="ML 예측 총 횟수 (예측 결과별)",
    labelnames=["model_type", "prediction"],  # normal, anomaly
    registry=registry,
)


# === 룰 엔진 메트릭 ===

# 룰 실행 카운터
rule_executions_total = Counter(
    name="rule_executions_total",
    documentation="룰 실행 총 횟수 (룰 카테고리별)",
    labelnames=["rule_category", "matched"],  # payment/account/shipping, true/false
    registry=registry,
)

# 룰 매칭 카운터 (액션별)
rule_matches_total = Counter(
    name="rule_matches_total",
    documentation="룰 매칭 총 횟수 (액션별)",
    labelnames=["rule_category", "action"],  # block/manual_review/warning
    registry=registry,
)


# === 캐시 메트릭 ===

# 캐시 히트율 (게이지)
cache_hit_rate = Gauge(
    name="cache_hit_rate",
    documentation="Redis 캐시 히트율 (0~1)",
    labelnames=["cache_type"],  # device, ip, rule, ml, geo
    registry=registry,
)

# 캐시 조회 카운터
cache_lookups_total = Counter(
    name="cache_lookups_total",
    documentation="캐시 조회 총 횟수",
    labelnames=["cache_type", "result"],  # hit/miss
    registry=registry,
)


# === API 메트릭 ===

# API 요청 카운터
api_requests_total = Counter(
    name="api_requests_total",
    documentation="API 요청 총 횟수",
    labelnames=["method", "endpoint", "status_code"],
    registry=registry,
)

# API 응답 시간 (히스토그램)
api_response_duration = Histogram(
    name="api_response_duration_seconds",
    documentation="API 응답 시간 (초)",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    labelnames=["method", "endpoint"],
    registry=registry,
)


# === 시스템 메트릭 ===

# 시스템 정보 (Info)
system_info = Info(
    name="fds_system_info",
    documentation="FDS 시스템 정보",
    registry=registry,
)

# 활성 엔진 수 (게이지)
active_engines = Gauge(
    name="fds_active_engines",
    documentation="활성화된 FDS 엔진 수",
    registry=registry,
)

# 데이터베이스 연결 풀 (게이지)
db_connections_active = Gauge(
    name="db_connections_active",
    documentation="활성 데이터베이스 연결 수",
    registry=registry,
)

db_connections_idle = Gauge(
    name="db_connections_idle",
    documentation="유휴 데이터베이스 연결 수",
    registry=registry,
)


# === 에러 메트릭 ===

# 에러 발생 카운터
errors_total = Counter(
    name="fds_errors_total",
    documentation="FDS 에러 발생 총 횟수",
    labelnames=[
        "error_type",
        "engine",
    ],  # timeout/exception/validation, fingerprint/ml/rule
    registry=registry,
)


# === 사기 탐지 메트릭 ===

# 사기 탐지 카운터
fraud_detections_total = Counter(
    name="fraud_detections_total",
    documentation="사기 탐지 총 횟수",
    labelnames=["detection_source"],  # rule, ml, network, behavior, fingerprint
    registry=registry,
)

# 거래 차단 카운터
transactions_blocked_total = Counter(
    name="transactions_blocked_total",
    documentation="차단된 거래 총 횟수",
    labelnames=["block_reason"],  # high_risk, blacklist, rule_block, ml_anomaly
    registry=registry,
)


# === 헬퍼 함수 ===


def record_evaluation_metrics(
    duration_seconds: float,
    risk_level: str,
    decision: str,
    risk_score: int,
    engine_timings: Dict[str, float] = None,
):
    """
    FDS 평가 메트릭 기록

    Args:
        duration_seconds: 전체 평가 시간 (초)
        risk_level: 위험 수준 (low/medium/high)
        decision: 의사결정 (approve/block/additional_auth)
        risk_score: 위험 점수 (0-100)
        engine_timings: 엔진별 실행 시간 (초)
    """
    # 전체 평가 시간
    fds_evaluation_duration.labels(engine_type="total").observe(duration_seconds)

    # 엔진별 평가 시간
    if engine_timings:
        for engine_name, duration in engine_timings.items():
            fds_evaluation_duration.labels(engine_type=engine_name).observe(duration)

    # 평가 카운터
    fds_evaluations_total.labels(risk_level=risk_level, decision=decision).inc()

    # 위험 점수 통계
    fds_risk_score.observe(risk_score)


def record_ml_inference(model_type: str, duration_seconds: float, prediction: str):
    """
    ML 추론 메트릭 기록

    Args:
        model_type: 모델 타입 (random_forest/xgboost/ensemble)
        duration_seconds: 추론 시간 (초)
        prediction: 예측 결과 (normal/anomaly)
    """
    ml_inference_duration.labels(model_type=model_type).observe(duration_seconds)
    ml_predictions_total.labels(model_type=model_type, prediction=prediction).inc()


def record_rule_execution(rule_category: str, matched: bool, action: str = None):
    """
    룰 실행 메트릭 기록

    Args:
        rule_category: 룰 카테고리 (payment/account/shipping)
        matched: 룰 매칭 여부
        action: 액션 (block/manual_review/warning)
    """
    rule_executions_total.labels(
        rule_category=rule_category, matched=str(matched).lower()
    ).inc()

    if matched and action:
        rule_matches_total.labels(rule_category=rule_category, action=action).inc()


def record_cache_lookup(cache_type: str, hit: bool):
    """
    캐시 조회 메트릭 기록

    Args:
        cache_type: 캐시 타입 (device/ip/rule/ml/geo)
        hit: 캐시 히트 여부
    """
    result = "hit" if hit else "miss"
    cache_lookups_total.labels(cache_type=cache_type, result=result).inc()


def update_cache_hit_rate(cache_type: str, hit_rate: float):
    """
    캐시 히트율 업데이트

    Args:
        cache_type: 캐시 타입
        hit_rate: 히트율 (0.0 ~ 1.0)
    """
    cache_hit_rate.labels(cache_type=cache_type).set(hit_rate)


def record_api_request(
    method: str, endpoint: str, status_code: int, duration_seconds: float
):
    """
    API 요청 메트릭 기록

    Args:
        method: HTTP 메서드
        endpoint: 엔드포인트 경로
        status_code: HTTP 상태 코드
        duration_seconds: 응답 시간 (초)
    """
    api_requests_total.labels(
        method=method, endpoint=endpoint, status_code=str(status_code)
    ).inc()
    api_response_duration.labels(method=method, endpoint=endpoint).observe(
        duration_seconds
    )


def record_error(error_type: str, engine: str = "unknown"):
    """
    에러 발생 메트릭 기록

    Args:
        error_type: 에러 타입 (timeout/exception/validation)
        engine: 발생한 엔진 (fingerprint/ml/rule)
    """
    errors_total.labels(error_type=error_type, engine=engine).inc()


def record_fraud_detection(detection_source: str):
    """
    사기 탐지 메트릭 기록

    Args:
        detection_source: 탐지 소스 (rule/ml/network/behavior/fingerprint)
    """
    fraud_detections_total.labels(detection_source=detection_source).inc()


def record_transaction_blocked(block_reason: str):
    """
    거래 차단 메트릭 기록

    Args:
        block_reason: 차단 사유 (high_risk/blacklist/rule_block/ml_anomaly)
    """
    transactions_blocked_total.labels(block_reason=block_reason).inc()


def init_system_info():
    """시스템 정보 초기화"""
    system_info.info(
        {
            "version": "2.0.0",
            "service": "shopfds-fds-service",
            "environment": "production",
        }
    )


def get_metrics_response() -> Response:
    """
    Prometheus 메트릭 응답 생성

    Returns:
        Response: Prometheus 형식의 메트릭 응답
    """
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )


# 시스템 정보 초기화
init_system_info()
