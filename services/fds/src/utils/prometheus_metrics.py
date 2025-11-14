"""
Prometheus 메트릭 수집 유틸리티 - FDS 서비스

FDS(Fraud Detection System)의 주요 메트릭을 수집하고 Prometheus에 노출합니다.

주요 메트릭:
- FDS 평가 처리량 및 응답 시간 (목표: 100ms)
- 위험도별 거래 분포 (Counter)
- 탐지 엔진별 실행 시간 (Histogram)
- 룰 엔진, ML 엔진, CTI 엔진 성능
- 오탐/정탐률 (Gauge)
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    Summary,
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
    "fds_app",
    "FDS (Fraud Detection System) Application Info",
    registry=registry,
)
app_info.info(
    {
        "version": "1.0.0",
        "service": "fds",
        "environment": "production",
    }
)

# ===========================
# FDS 평가 메트릭 (핵심)
# ===========================
fds_evaluations_total = Counter(
    "fds_evaluations_total",
    "전체 FDS 평가 요청 수",
    ["risk_level", "decision"],  # low/medium/high/blocked, approve/auth/hold/block
    registry=registry,
)

fds_evaluation_duration_seconds = Histogram(
    "fds_evaluation_duration_seconds",
    "FDS 평가 처리 시간 (초) - 목표: P95 < 0.1초",
    ["risk_level"],
    buckets=(
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.15,
        0.2,
        0.3,
        0.5,
        1.0,
        2.0,
    ),  # 100ms 목표를 위한 세밀한 버킷
    registry=registry,
)

fds_evaluation_latency_summary = Summary(
    "fds_evaluation_latency_summary",
    "FDS 평가 지연 시간 요약 (P50, P90, P95, P99)",
    registry=registry,
)

fds_evaluations_in_progress = Gauge(
    "fds_evaluations_in_progress",
    "현재 평가 중인 거래 수",
    registry=registry,
)

# ===========================
# 위험 점수 메트릭
# ===========================
risk_score_distribution = Histogram(
    "fds_risk_score_distribution",
    "위험 점수 분포 (0-100)",
    buckets=(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100),
    registry=registry,
)

risk_factors_triggered = Counter(
    "fds_risk_factors_triggered_total",
    "위험 요인 발생 횟수",
    ["factor_name"],  # velocity_check, amount_threshold, geo_mismatch, etc.
    registry=registry,
)

risk_level_distribution = Counter(
    "fds_risk_level_distribution_total",
    "위험도별 거래 분포",
    ["risk_level"],  # low, medium, high, blocked
    registry=registry,
)

# ===========================
# 탐지 엔진별 메트릭
# ===========================
# 룰 엔진
rule_engine_duration_seconds = Histogram(
    "fds_rule_engine_duration_seconds",
    "룰 엔진 실행 시간 (초)",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1),
    registry=registry,
)

rule_engine_rules_evaluated = Counter(
    "fds_rule_engine_rules_evaluated_total",
    "평가된 룰 수",
    ["rule_id", "triggered"],  # rule-001, true/false
    registry=registry,
)

# ML 엔진
ml_engine_duration_seconds = Histogram(
    "fds_ml_engine_duration_seconds",
    "ML 엔진 실행 시간 (초)",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1),
    registry=registry,
)

ml_predictions_total = Counter(
    "fds_ml_predictions_total",
    "ML 예측 수",
    ["model_name", "prediction"],  # isolation_forest/lightgbm, normal/fraud
    registry=registry,
)

ml_model_info = Info(
    "fds_ml_model",
    "현재 사용 중인 ML 모델 정보",
    registry=registry,
)

# CTI 엔진
cti_engine_duration_seconds = Histogram(
    "fds_cti_engine_duration_seconds",
    "CTI 엔진 실행 시간 (초)",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1),
    registry=registry,
)

cti_lookups_total = Counter(
    "fds_cti_lookups_total",
    "CTI 조회 수",
    ["source", "result"],  # abuseipdb/internal, malicious/safe/cache_hit/timeout
    registry=registry,
)

cti_cache_hit_ratio = Gauge(
    "fds_cti_cache_hit_ratio",
    "CTI 캐시 히트율 (0.0 ~ 1.0)",
    registry=registry,
)

# ===========================
# 엔진별 세부 시간 분해
# ===========================
fds_engine_breakdown_seconds = Histogram(
    "fds_engine_breakdown_seconds",
    "엔진별 처리 시간 분해",
    ["engine"],  # rule, ml, cti, aggregation
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1),
    registry=registry,
)

# ===========================
# 정확도 메트릭
# ===========================
true_positives = Counter(
    "fds_true_positives_total",
    "정탐 (사기 거래를 올바르게 탐지)",
    registry=registry,
)

false_positives = Counter(
    "fds_false_positives_total",
    "오탐 (정상 거래를 사기로 오인)",
    registry=registry,
)

true_negatives = Counter(
    "fds_true_negatives_total",
    "정상 거래를 올바르게 승인",
    registry=registry,
)

false_negatives = Counter(
    "fds_false_negatives_total",
    "미탐 (사기 거래를 정상으로 오인)",
    registry=registry,
)

precision = Gauge(
    "fds_precision",
    "정밀도 (Precision) = TP / (TP + FP)",
    registry=registry,
)

recall = Gauge(
    "fds_recall",
    "재현율 (Recall) = TP / (TP + FN)",
    registry=registry,
)

f1_score = Gauge(
    "fds_f1_score",
    "F1 스코어 = 2 * (Precision * Recall) / (Precision + Recall)",
    registry=registry,
)

# ===========================
# 의사결정 메트릭
# ===========================
decisions_total = Counter(
    "fds_decisions_total",
    "FDS 의사결정 분포",
    ["decision"],  # approve, additional_auth_required, hold, block
    registry=registry,
)

blocked_transactions = Counter(
    "fds_blocked_transactions_total",
    "차단된 거래 수",
    ["reason"],  # high_risk, blacklisted_ip, velocity_violation
    registry=registry,
)

additional_auth_required = Counter(
    "fds_additional_auth_required_total",
    "추가 인증 요청 수",
    ["auth_type"],  # otp, biometric
    registry=registry,
)

# ===========================
# 에러 및 성능 메트릭
# ===========================
fds_errors_total = Counter(
    "fds_errors_total",
    "FDS 에러 수",
    ["error_type", "severity"],  # timeout, ml_failure, cti_timeout / warning, error, critical
    registry=registry,
)

fds_timeouts_total = Counter(
    "fds_timeouts_total",
    "타임아웃 발생 수",
    ["component"],  # cti, ml, database
    registry=registry,
)

fds_sla_violations_total = Counter(
    "fds_sla_violations_total",
    "SLA 위반 횟수 (100ms 초과)",
    registry=registry,
)

# ===========================
# 데이터베이스 메트릭
# ===========================
database_query_duration_seconds = Histogram(
    "fds_database_query_duration_seconds",
    "데이터베이스 쿼리 실행 시간 (초)",
    ["operation"],  # select, insert, update
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1),
    registry=registry,
)

# ===========================
# 데코레이터 유틸리티
# ===========================
def track_fds_evaluation():
    """FDS 평가 전체 프로세스를 추적하는 데코레이터"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            fds_evaluations_in_progress.inc()
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # 결과에서 위험도와 의사결정 추출
                risk_level = result.get("risk_level", "unknown")
                decision = result.get("decision", "unknown")

                # 메트릭 기록
                fds_evaluation_duration_seconds.labels(risk_level=risk_level).observe(
                    duration
                )
                fds_evaluation_latency_summary.observe(duration)
                fds_evaluations_total.labels(
                    risk_level=risk_level, decision=decision
                ).inc()

                # SLA 위반 체크 (100ms)
                if duration > 0.1:
                    fds_sla_violations_total.inc()

                return result
            except Exception as e:
                duration = time.time() - start_time
                fds_errors_total.labels(error_type="evaluation_error", severity="error").inc()
                raise
            finally:
                fds_evaluations_in_progress.dec()

        return wrapper

    return decorator


def track_engine_duration(engine_name: str):
    """개별 엔진 실행 시간을 추적하는 데코레이터"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # 엔진별 메트릭 기록
                if engine_name == "rule":
                    rule_engine_duration_seconds.observe(duration)
                elif engine_name == "ml":
                    ml_engine_duration_seconds.observe(duration)
                elif engine_name == "cti":
                    cti_engine_duration_seconds.observe(duration)

                fds_engine_breakdown_seconds.labels(engine=engine_name).observe(
                    duration
                )

                return result
            except Exception as e:
                fds_errors_total.labels(
                    error_type=f"{engine_name}_error", severity="error"
                ).inc()
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
def record_fds_evaluation_result(
    risk_score: float, risk_level: str, decision: str, duration: float
):
    """FDS 평가 결과 기록"""
    fds_evaluations_total.labels(risk_level=risk_level, decision=decision).inc()
    fds_evaluation_duration_seconds.labels(risk_level=risk_level).observe(duration)
    fds_evaluation_latency_summary.observe(duration)
    risk_score_distribution.observe(risk_score)
    risk_level_distribution.labels(risk_level=risk_level).inc()
    decisions_total.labels(decision=decision).inc()

    if duration > 0.1:
        fds_sla_violations_total.inc()


def record_risk_factor(factor_name: str):
    """위험 요인 발생 기록"""
    risk_factors_triggered.labels(factor_name=factor_name).inc()


def record_rule_evaluation(rule_id: str, triggered: bool):
    """룰 평가 결과 기록"""
    rule_engine_rules_evaluated.labels(
        rule_id=rule_id, triggered=str(triggered).lower()
    ).inc()


def record_ml_prediction(model_name: str, prediction: str):
    """ML 예측 결과 기록"""
    ml_predictions_total.labels(model_name=model_name, prediction=prediction).inc()


def record_cti_lookup(source: str, result: str):
    """CTI 조회 결과 기록"""
    cti_lookups_total.labels(source=source, result=result).inc()


def record_decision(decision: str, reason: str = None):
    """FDS 의사결정 기록"""
    decisions_total.labels(decision=decision).inc()
    if decision == "block" and reason:
        blocked_transactions.labels(reason=reason).inc()
    elif decision == "additional_auth_required":
        additional_auth_required.labels(auth_type="otp").inc()


def record_fraud_case(is_fraud: bool, detected: bool):
    """사기 탐지 정확도 기록 (사후 검증)"""
    if is_fraud and detected:
        true_positives.inc()
    elif is_fraud and not detected:
        false_negatives.inc()
    elif not is_fraud and detected:
        false_positives.inc()
    else:  # not is_fraud and not detected
        true_negatives.inc()

    # 정밀도, 재현율, F1 스코어 계산
    update_accuracy_metrics()


def update_accuracy_metrics():
    """정확도 메트릭 업데이트"""
    tp = true_positives._value.get()
    fp = false_positives._value.get()
    fn = false_negatives._value.get()

    if tp + fp > 0:
        prec = tp / (tp + fp)
        precision.set(prec)

    if tp + fn > 0:
        rec = tp / (tp + fn)
        recall.set(rec)

    if tp + fp > 0 and tp + fn > 0:
        prec = tp / (tp + fp)
        rec = tp / (tp + fn)
        if prec + rec > 0:
            f1 = 2 * (prec * rec) / (prec + rec)
            f1_score.set(f1)


def record_error(error_type: str, severity: str = "error"):
    """FDS 에러 기록"""
    fds_errors_total.labels(error_type=error_type, severity=severity).inc()


def record_timeout(component: str):
    """타임아웃 기록"""
    fds_timeouts_total.labels(component=component).inc()
    fds_errors_total.labels(error_type="timeout", severity="warning").inc()
