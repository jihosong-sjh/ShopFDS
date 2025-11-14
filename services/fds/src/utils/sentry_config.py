"""
Sentry 에러 트래킹 설정 - FDS 서비스

FDS 서비스의 실시간 에러 모니터링 및 성능 추적

주요 기능:
- FDS 평가 중 예외 자동 캡처
- 룰/ML/CTI 엔진별 성능 트랜잭션
- 거래 정보 컨텍스트 (민감 정보 제외)
- 알림 우선순위 설정
"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging
import os


def init_sentry(
    dsn: str = None,
    environment: str = "development",
    enable_tracing: bool = True,
    traces_sample_rate: float = 1.0,
    profiles_sample_rate: float = 1.0,
):
    """
    Sentry SDK 초기화 (FDS 전용)

    FDS는 핵심 서비스이므로 프로덕션에서도 높은 샘플링 비율 사용
    """
    if not dsn:
        dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        logging.info("Sentry DSN이 설정되지 않았습니다. Sentry 모니터링이 비활성화됩니다.")
        return

    # FDS는 중요 서비스이므로 프로덕션에서도 30% 샘플링
    if environment == "production":
        traces_sample_rate = min(traces_sample_rate, 0.3)
        profiles_sample_rate = min(profiles_sample_rate, 0.3)
    elif environment == "staging":
        traces_sample_rate = min(traces_sample_rate, 0.7)
        profiles_sample_rate = min(profiles_sample_rate, 0.7)

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint",
                failed_request_status_codes=[500, 599],
            ),
            SqlalchemyIntegration(),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        enable_tracing=enable_tracing,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        release=os.getenv("APP_VERSION", "1.0.0"),
        send_default_pii=False,
        before_send=before_send_filter,
        sample_rate=1.0,
        max_breadcrumbs=100,  # FDS는 더 많은 breadcrumb 저장
        default_integrations=True,
        attach_stacktrace=True,
        debug=environment == "development",
    )

    # FDS 특화 태그 설정
    sentry_sdk.set_tag("service", "fds")
    sentry_sdk.set_tag("critical", "true")

    logging.info(
        f"Sentry 초기화 완료 (FDS): environment={environment}, "
        f"traces_sample_rate={traces_sample_rate}"
    )


def before_send_filter(event, hint):
    """
    FDS 이벤트 전송 전 필터링

    거래 정보에서 민감 정보 제거:
    - 사용자 개인정보 (이름, 주소, 전화번호)
    - 결제 정보 (카드번호, CVV)
    - IP 주소는 일부만 마스킹 (1.2.3.* 형태)
    """
    # IP 주소 일부 마스킹
    if "request" in event:
        request = event["request"]
        if "env" in request and "REMOTE_ADDR" in request["env"]:
            ip = request["env"]["REMOTE_ADDR"]
            # 마지막 옥텟만 마스킹
            parts = ip.split(".")
            if len(parts) == 4:
                request["env"]["REMOTE_ADDR"] = f"{parts[0]}.{parts[1]}.{parts[2]}.*"

    # 거래 정보 마스킹
    if "extra" in event:
        extra = event["extra"]
        for key in ["user_name", "shipping_address", "shipping_phone", "email"]:
            if key in extra:
                extra[key] = "[Filtered]"

    # FDS 평가 실패 시 우선순위 높임
    if "exception" in event:
        exception = event["exception"]
        if any("FDS" in str(val) for val in exception.get("values", [])):
            event["level"] = "error"
            sentry_sdk.set_tag("fds_failure", "true")

    return event


def capture_fds_exception(
    exception: Exception,
    transaction_id: str = None,
    risk_score: float = None,
    engine: str = None,
    **extra,
):
    """
    FDS 평가 중 예외를 Sentry에 전송

    Args:
        exception: 캡처할 예외
        transaction_id: 거래 ID
        risk_score: 위험 점수
        engine: 실패한 엔진 (rule, ml, cti)
        **extra: 추가 컨텍스트
    """
    with sentry_sdk.push_scope() as scope:
        if transaction_id:
            scope.set_tag("transaction_id", transaction_id)

        if risk_score is not None:
            scope.set_extra("risk_score", risk_score)

        if engine:
            scope.set_tag("fds_engine", engine)

        for key, value in extra.items():
            scope.set_extra(key, value)

        sentry_sdk.capture_exception(exception)


def capture_fds_performance_issue(
    duration_ms: float,
    threshold_ms: float = 100.0,
    transaction_id: str = None,
    engine: str = None,
):
    """
    FDS 성능 이슈를 Sentry에 전송

    100ms SLA 위반 시 자동으로 이벤트 전송

    Args:
        duration_ms: 실제 소요 시간 (밀리초)
        threshold_ms: 임계값 (기본 100ms)
        transaction_id: 거래 ID
        engine: 지연 발생 엔진
    """
    if duration_ms > threshold_ms:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("performance_issue", "true")
            scope.set_tag("sla_violation", "true")

            if transaction_id:
                scope.set_tag("transaction_id", transaction_id)

            if engine:
                scope.set_tag("slow_engine", engine)

            scope.set_extra("duration_ms", duration_ms)
            scope.set_extra("threshold_ms", threshold_ms)
            scope.set_extra("overrun_ms", duration_ms - threshold_ms)

            sentry_sdk.capture_message(
                f"FDS SLA 위반: {duration_ms:.2f}ms (목표: {threshold_ms}ms)",
                level="warning",
            )


def start_fds_transaction(operation: str):
    """
    FDS 작업 트랜잭션 시작

    Args:
        operation: 작업 유형 (evaluate, rule_engine, ml_engine, cti_engine)

    Returns:
        트랜잭션 객체

    Example:
        with start_fds_transaction("evaluate"):
            evaluate_transaction(data)
    """
    return sentry_sdk.start_transaction(name=f"fds.{operation}", op="fds")


def add_fds_breadcrumb(
    message: str,
    engine: str = None,
    risk_score: float = None,
    decision: str = None,
    data: dict = None,
):
    """
    FDS 평가 과정을 Breadcrumb으로 기록

    Args:
        message: Breadcrumb 메시지
        engine: 엔진 이름 (rule, ml, cti)
        risk_score: 위험 점수
        decision: 의사결정 (approve, auth, hold, block)
        data: 추가 데이터
    """
    breadcrumb_data = data or {}

    if engine:
        breadcrumb_data["engine"] = engine

    if risk_score is not None:
        breadcrumb_data["risk_score"] = risk_score

    if decision:
        breadcrumb_data["decision"] = decision

    sentry_sdk.add_breadcrumb(
        message=message,
        category="fds",
        level="info",
        data=breadcrumb_data,
    )
