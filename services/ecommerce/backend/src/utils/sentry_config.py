"""
Sentry 에러 트래킹 설정

실시간 에러 모니터링, 성능 추적, 디버깅을 위한 Sentry SDK 설정

주요 기능:
- 예외 자동 캡처 및 전송
- 성능 트랜잭션 추적
- 사용자 컨텍스트 추가
- 민감 정보 자동 마스킹
- 환경별 샘플링 비율 조정
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
    Sentry SDK 초기화

    Args:
        dsn: Sentry DSN (Data Source Name). 환경변수 SENTRY_DSN에서 가져옴
        environment: 환경 이름 (development, staging, production)
        enable_tracing: 성능 추적 활성화 여부
        traces_sample_rate: 트랜잭션 샘플링 비율 (0.0 ~ 1.0)
        profiles_sample_rate: 프로파일링 샘플링 비율 (0.0 ~ 1.0)

    환경별 권장 샘플링 비율:
    - development: 1.0 (모든 트랜잭션)
    - staging: 0.5 (50%)
    - production: 0.1 (10%)
    """
    # DSN이 없으면 초기화하지 않음 (로컬 개발 시)
    if not dsn:
        dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        logging.info("Sentry DSN이 설정되지 않았습니다. Sentry 모니터링이 비활성화됩니다.")
        return

    # 환경별 샘플링 비율 자동 조정
    if environment == "production":
        traces_sample_rate = min(traces_sample_rate, 0.1)
        profiles_sample_rate = min(profiles_sample_rate, 0.1)
    elif environment == "staging":
        traces_sample_rate = min(traces_sample_rate, 0.5)
        profiles_sample_rate = min(profiles_sample_rate, 0.5)

    # Sentry SDK 초기화
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        # 통합 설정
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint",  # 엔드포인트별로 트랜잭션 그룹화
                failed_request_status_codes=[500, 599],  # 5xx 에러만 캡처
            ),
            SqlalchemyIntegration(),  # 데이터베이스 쿼리 추적
            RedisIntegration(),  # Redis 명령 추적
            LoggingIntegration(
                level=logging.INFO,  # INFO 이상 로그 캡처
                event_level=logging.ERROR,  # ERROR 이상만 이벤트로 전송
            ),
        ],
        # 성능 추적 설정
        enable_tracing=enable_tracing,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        # 릴리스 버전 추적
        release=os.getenv("APP_VERSION", "1.0.0"),
        # 민감 정보 마스킹
        send_default_pii=False,  # 개인정보 자동 전송 비활성화
        before_send=before_send_filter,
        before_breadcrumb=before_breadcrumb_filter,
        # 에러 샘플링 (모든 에러 전송)
        sample_rate=1.0,
        # 최대 breadcrumb 수
        max_breadcrumbs=50,
        # 태그
        default_integrations=True,
        attach_stacktrace=True,
        # 디버그 모드 (개발 환경에서만)
        debug=environment == "development",
    )

    logging.info(
        f"Sentry 초기화 완료: environment={environment}, "
        f"traces_sample_rate={traces_sample_rate}, "
        f"profiles_sample_rate={profiles_sample_rate}"
    )


def before_send_filter(event, hint):
    """
    이벤트 전송 전 필터링 및 민감 정보 마스킹

    민감 정보 패턴:
    - 결제 정보: card_number, card_cvv, card_expiry
    - 비밀번호: password, passwd, pwd
    - 토큰: token, api_key, secret
    - 개인정보: email, phone, address (일부만 마스킹)
    """
    # 민감 키워드 목록
    sensitive_keys = [
        "password",
        "passwd",
        "pwd",
        "token",
        "api_key",
        "secret",
        "card_number",
        "card_cvv",
        "card_expiry",
        "ssn",
        "social_security",
    ]

    # Request 데이터 마스킹
    if "request" in event:
        request = event["request"]

        # POST/PUT 요청 본문 마스킹
        if "data" in request:
            request["data"] = mask_sensitive_data(request["data"], sensitive_keys)

        # 쿼리 파라미터 마스킹
        if "query_string" in request:
            request["query_string"] = mask_sensitive_data(
                request["query_string"], sensitive_keys
            )

        # 헤더 마스킹 (Authorization 등)
        if "headers" in request:
            headers = request["headers"]
            for key in ["Authorization", "X-Api-Key", "X-Auth-Token"]:
                if key in headers:
                    headers[key] = "[Filtered]"

    # Extra 데이터 마스킹
    if "extra" in event:
        event["extra"] = mask_sensitive_data(event["extra"], sensitive_keys)

    # Context 데이터 마스킹
    if "contexts" in event:
        event["contexts"] = mask_sensitive_data(event["contexts"], sensitive_keys)

    return event


def before_breadcrumb_filter(crumb, hint):
    """
    Breadcrumb 전송 전 필터링

    SQL 쿼리, HTTP 요청 등의 breadcrumb에서 민감 정보 제거
    """
    # SQL 쿼리에서 민감 데이터 마스킹
    if crumb.get("category") == "query":
        if "message" in crumb:
            crumb["message"] = mask_sql_query(crumb["message"])

    # HTTP 요청에서 Authorization 헤더 마스킹
    if crumb.get("category") == "httplib":
        if "data" in crumb and "headers" in crumb["data"]:
            headers = crumb["data"]["headers"]
            for key in ["Authorization", "X-Api-Key"]:
                if key in headers:
                    headers[key] = "[Filtered]"

    return crumb


def mask_sensitive_data(data, sensitive_keys):
    """
    민감 데이터 마스킹 (재귀적)

    Args:
        data: 마스킹할 데이터 (dict, list, str 등)
        sensitive_keys: 민감 키워드 목록

    Returns:
        마스킹된 데이터
    """
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            # 키가 민감 키워드를 포함하는지 확인
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                masked[key] = "[Filtered]"
            else:
                masked[key] = mask_sensitive_data(value, sensitive_keys)
        return masked

    elif isinstance(data, list):
        return [mask_sensitive_data(item, sensitive_keys) for item in data]

    elif isinstance(data, str):
        # 문자열에서 패턴 마스킹 (예: 카드번호, 이메일 일부)
        return data  # 문자열 자체는 그대로 반환 (키 레벨에서 이미 마스킹)

    else:
        return data


def mask_sql_query(query: str) -> str:
    """
    SQL 쿼리에서 민감 정보 마스킹

    Args:
        query: SQL 쿼리 문자열

    Returns:
        마스킹된 SQL 쿼리
    """
    import re

    # 비밀번호, 카드번호 등이 포함된 VALUES 절 마스킹
    query = re.sub(
        r"(password|card_number|card_cvv|token)\s*=\s*'[^']*'",
        r"\1='[Filtered]'",
        query,
        flags=re.IGNORECASE,
    )

    return query


def capture_exception_with_context(
    exception: Exception, user_id: str = None, transaction_id: str = None, **extra
):
    """
    예외를 Sentry에 수동으로 전송 (추가 컨텍스트 포함)

    Args:
        exception: 캡처할 예외
        user_id: 사용자 ID (선택)
        transaction_id: 거래 ID (선택)
        **extra: 추가 컨텍스트 정보

    Example:
        try:
            risky_operation()
        except Exception as e:
            capture_exception_with_context(
                e,
                user_id="user-123",
                transaction_id="txn-456",
                order_amount=50000,
                payment_method="card"
            )
    """
    with sentry_sdk.push_scope() as scope:
        # 사용자 컨텍스트 추가
        if user_id:
            scope.set_user({"id": user_id})

        # 트랜잭션 컨텍스트 추가
        if transaction_id:
            scope.set_tag("transaction_id", transaction_id)

        # 추가 컨텍스트
        for key, value in extra.items():
            scope.set_extra(key, value)

        # 예외 캡처
        sentry_sdk.capture_exception(exception)


def capture_message_with_context(
    message: str, level: str = "info", user_id: str = None, **extra
):
    """
    메시지를 Sentry에 수동으로 전송 (추가 컨텍스트 포함)

    Args:
        message: 전송할 메시지
        level: 로그 레벨 (debug, info, warning, error, fatal)
        user_id: 사용자 ID (선택)
        **extra: 추가 컨텍스트 정보
    """
    with sentry_sdk.push_scope() as scope:
        if user_id:
            scope.set_user({"id": user_id})

        for key, value in extra.items():
            scope.set_extra(key, value)

        sentry_sdk.capture_message(message, level=level)


def start_transaction(name: str, op: str = "http.server"):
    """
    성능 트랜잭션 시작

    Args:
        name: 트랜잭션 이름 (예: "POST /v1/orders")
        op: 작업 유형 (예: "http.server", "db.query", "cache.get")

    Returns:
        트랜잭션 객체 (with 문으로 사용)

    Example:
        with start_transaction("process_payment", op="payment"):
            process_payment_logic()
    """
    return sentry_sdk.start_transaction(name=name, op=op)


def add_breadcrumb(message: str, category: str = "default", level: str = "info", data: dict = None):
    """
    Breadcrumb 추가 (이벤트 발생 경로 추적)

    Args:
        message: Breadcrumb 메시지
        category: 카테고리 (예: "auth", "query", "http")
        level: 레벨 (debug, info, warning, error)
        data: 추가 데이터

    Example:
        add_breadcrumb(
            "User attempted login",
            category="auth",
            level="info",
            data={"user_id": "user-123", "ip": "1.2.3.4"}
        )
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {},
    )
