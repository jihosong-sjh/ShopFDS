"""
로깅 설정 및 민감 데이터 자동 마스킹

PCI-DSS 및 개인정보보호법 준수를 위해 민감 데이터를 자동으로 마스킹합니다.
"""

import logging
import re
import json
from typing import Any
from datetime import datetime
import os


class SensitiveDataFilter(logging.Filter):
    """
    민감 데이터 자동 마스킹 필터

    로그에 출력되는 민감 정보를 자동으로 마스킹합니다.
    """

    # 마스킹할 필드 패턴
    SENSITIVE_PATTERNS = {
        # 카드 번호: 1234-5678-9012-3456 → 1234-****-****-3456
        "card_number": (
            r"\b(\d{4})[\s\-]?(\d{4})[\s\-]?(\d{4})[\s\-]?(\d{4})\b",
            r"\1-****-****-\4",
        ),
        # 비밀번호: "password": "MyPass123!" → "password": "***"
        "password": (
            r'"password"\s*:\s*"[^"]*"',
            '"password": "***"',
        ),
        # JWT 토큰: "token": "eyJ..." → "token": "***"
        "token": (
            r'"(token|access_token|refresh_token)"\s*:\s*"[^"]*"',
            r'"\1": "***"',
        ),
        # 이메일 일부 마스킹: user@example.com → u***@example.com
        "email": (
            r"\b([a-zA-Z0-9._%+-])[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b",
            r"\1***@\2",
        ),
        # 전화번호: 010-1234-5678 → 010-****-5678
        "phone": (
            r"\b(010|011|016|017|018|019)[\s\-]?(\d{4})[\s\-]?(\d{4})\b",
            r"\1-****-\3",
        ),
        # 주민등록번호: 123456-1234567 → 123456-*******
        "ssn": (
            r"\b(\d{6})[\s\-]?(\d{7})\b",
            r"\1-*******",
        ),
        # CVV: "cvv": "123" → "cvv": "***"
        "cvv": (
            r'"cvv"\s*:\s*"\d+"',
            '"cvv": "***"',
        ),
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """
        로그 레코드를 필터링하여 민감 데이터 마스킹

        Args:
            record: 로그 레코드

        Returns:
            bool: 항상 True (필터 통과)
        """
        # 로그 메시지 마스킹
        if isinstance(record.msg, str):
            record.msg = self.mask_sensitive_data(record.msg)

        # 로그 args 마스킹
        if record.args:
            record.args = tuple(
                self.mask_sensitive_data(str(arg)) for arg in record.args
            )

        return True

    def mask_sensitive_data(self, text: str) -> str:
        """
        민감 데이터 마스킹

        Args:
            text: 마스킹할 텍스트

        Returns:
            str: 마스킹된 텍스트
        """
        for pattern_name, (pattern, replacement) in self.SENSITIVE_PATTERNS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text


class JSONFormatter(logging.Formatter):
    """
    JSON 형식 로그 포맷터

    구조화된 로그를 위해 JSON 형식으로 출력합니다.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        로그 레코드를 JSON 형식으로 변환

        Args:
            record: 로그 레코드

        Returns:
            str: JSON 형식 로그
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 추가 컨텍스트 정보
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # 예외 정보
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    log_level: str = None,
    log_format: str = "json",
    log_file: str = None,
) -> None:
    """
    전역 로깅 설정

    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: 로그 포맷 ("json" 또는 "text")
        log_file: 로그 파일 경로 (None이면 콘솔만)
    """
    # 환경 변수에서 로그 설정 읽기
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    log_format = log_format or os.getenv("LOG_FORMAT", "json")
    log_file = log_file or os.getenv("LOG_FILE")

    # 로그 레벨 설정
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 포맷터 선택
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)

    # 파일 핸들러 (선택)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveDataFilter())
        root_logger.addHandler(file_handler)

    # 써드파티 라이브러리 로그 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    로거 인스턴스 생성

    Args:
        name: 로거 이름 (보통 __name__ 사용)

    Returns:
        logging.Logger: 로거 인스턴스

    Example:
        ```python
        logger = get_logger(__name__)
        logger.info("서버 시작")
        logger.error("오류 발생", extra={"user_id": "123"})
        ```
    """
    return logging.getLogger(name)


class RequestLogger:
    """
    API 요청/응답 로깅 미들웨어

    FastAPI 미들웨어로 사용하여 모든 요청/응답을 로깅합니다.
    """

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or get_logger("api.requests")

    async def log_request(self, request: Any, response_time: float, status_code: int):
        """
        API 요청 로깅

        Args:
            request: FastAPI Request 객체
            response_time: 응답 시간 (초)
            status_code: HTTP 상태 코드
        """
        self.logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "response_time_ms": round(response_time * 1000, 2),
                "status_code": status_code,
            },
        )


class AuditLogger:
    """
    감사 로그 (Audit Log)

    중요한 비즈니스 이벤트를 기록합니다 (회원가입, 결제, 주문 등).
    """

    def __init__(self):
        self.logger = get_logger("audit")

    def log_event(
        self,
        event_type: str,
        user_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        action: str = None,
        details: dict = None,
    ):
        """
        감사 이벤트 로깅

        Args:
            event_type: 이벤트 유형 (user.register, order.created 등)
            user_id: 사용자 ID
            resource_type: 리소스 유형 (order, product 등)
            resource_id: 리소스 ID
            action: 수행된 작업 (create, update, delete 등)
            details: 추가 상세 정보
        """
        self.logger.info(
            f"[AUDIT] {event_type}",
            extra={
                "event_type": event_type,
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "details": details or {},
            },
        )


# 전역 감사 로거 인스턴스
audit_logger = AuditLogger()
