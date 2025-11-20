"""
Enhanced Logging Utility
구조화된 로그, 민감 정보 마스킹, JSON 포맷 지원
"""

import logging
import json
import re
from typing import Any, Dict, Optional
from datetime import datetime
from functools import wraps


class SensitiveDataMasker:
    """민감한 정보 자동 마스킹"""

    # 민감 정보 패턴
    PATTERNS = {
        "card_number": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
        "cvv": re.compile(r"\b\d{3,4}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "email": re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b"),
        "phone": re.compile(r"\b\d{3}[-.]?\d{3,4}[-.]?\d{4}\b"),
        "password": re.compile(r"(password|pwd|passwd)[\s:=]+\S+", re.IGNORECASE),
        "token": re.compile(r"(token|api[_-]?key|secret)[\s:=]+\S+", re.IGNORECASE),
    }

    # 민감 필드명
    SENSITIVE_KEYS = {
        "password",
        "card_number",
        "card_cvv",
        "cvv",
        "ssn",
        "social_security_number",
        "api_key",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "private_key",
    }

    @classmethod
    def mask_card_number(cls, card_number: str) -> str:
        """카드 번호 마스킹 (마지막 4자리만 표시)"""
        cleaned = re.sub(r"[\s-]", "", card_number)
        if len(cleaned) == 16:
            return f"****-****-****-{cleaned[-4:]}"
        return "****"

    @classmethod
    def mask_email(cls, email: str) -> str:
        """이메일 마스킹 (앞 3자리 + @domain)"""
        if "@" in email:
            local, domain = email.split("@", 1)
            masked_local = local[:3] + "***" if len(local) > 3 else "***"
            return f"{masked_local}@{domain}"
        return "***"

    @classmethod
    def mask_phone(cls, phone: str) -> str:
        """전화번호 마스킹 (마지막 4자리만 표시)"""
        cleaned = re.sub(r"[\s\-\.]", "", phone)
        if len(cleaned) >= 10:
            return f"***-****-{cleaned[-4:]}"
        return "***"

    @classmethod
    def mask_text(cls, text: str) -> str:
        """텍스트에서 민감 정보 자동 마스킹"""
        masked = text

        # 카드 번호
        masked = cls.PATTERNS["card_number"].sub(
            lambda m: cls.mask_card_number(m.group(0)), masked
        )

        # 이메일
        masked = cls.PATTERNS["email"].sub(lambda m: cls.mask_email(m.group(0)), masked)

        # 전화번호
        masked = cls.PATTERNS["phone"].sub(lambda m: cls.mask_phone(m.group(0)), masked)

        # 비밀번호, 토큰
        masked = cls.PATTERNS["password"].sub("[REDACTED]", masked)
        masked = cls.PATTERNS["token"].sub("[REDACTED]", masked)

        return masked

    @classmethod
    def mask_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """딕셔너리에서 민감 정보 마스킹"""
        if not isinstance(data, dict):
            return data

        masked = {}
        for key, value in data.items():
            # 민감 필드명 체크
            if key.lower() in cls.SENSITIVE_KEYS:
                if isinstance(value, str):
                    if "card" in key.lower():
                        masked[key] = cls.mask_card_number(value)
                    elif "email" in key.lower():
                        masked[key] = cls.mask_email(value)
                    elif "phone" in key.lower():
                        masked[key] = cls.mask_phone(value)
                    else:
                        masked[key] = "***"
                else:
                    masked[key] = "***"
            elif isinstance(value, dict):
                masked[key] = cls.mask_dict(value)
            elif isinstance(value, list):
                masked[key] = [
                    cls.mask_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str):
                masked[key] = cls.mask_text(value)
            else:
                masked[key] = value

        return masked


class StructuredLogger:
    """구조화된 JSON 로거"""

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # JSON 핸들러 추가
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JSONFormatter())
            self.logger.addHandler(handler)

    def _log(
        self,
        level: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        mask_sensitive: bool = True,
    ):
        """구조화된 로그 출력"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": logging.getLevelName(level),
            "message": message,
        }

        if extra:
            if mask_sensitive:
                extra = SensitiveDataMasker.mask_dict(extra)
            log_data.update(extra)

        self.logger.log(level, json.dumps(log_data, ensure_ascii=False))

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, kwargs)

    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, kwargs)


class JSONFormatter(logging.Formatter):
    """JSON 포맷 로그 포맷터"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 예외 정보 추가
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 추가 필드 병합
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data, ensure_ascii=False)


# 전역 로거 인스턴스
logger = StructuredLogger("ecommerce")


# 로깅 데코레이터
def log_function_call(mask_args: bool = True):
    """함수 호출 로깅 데코레이터"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.info(
                f"Function called: {func_name}",
                args=str(args) if not mask_args else "***",
                kwargs=str(kwargs) if not mask_args else "***",
            )

            try:
                result = await func(*args, **kwargs)
                logger.info(f"Function completed: {func_name}")
                return result
            except Exception as e:
                logger.error(
                    f"Function failed: {func_name}",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.info(
                f"Function called: {func_name}",
                args=str(args) if not mask_args else "***",
                kwargs=str(kwargs) if not mask_args else "***",
            )

            try:
                result = func(*args, **kwargs)
                logger.info(f"Function completed: {func_name}")
                return result
            except Exception as e:
                logger.error(
                    f"Function failed: {func_name}",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

        # async 함수 감지
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:
            return async_wrapper
        return sync_wrapper

    return decorator


# 사용 예시
if __name__ == "__main__":
    # 기본 로깅
    logger.info("Application started")

    # 구조화된 로깅
    logger.info(
        "User login attempt",
        user_id="user123",
        email="test@example.com",
        ip_address="192.168.1.1",
    )

    # 민감 정보 마스킹
    logger.info(
        "Payment processed",
        card_number="1234567890123456",
        cvv="123",
        amount=10000,
    )

    # 에러 로깅
    try:
        raise ValueError("Something went wrong")
    except Exception as e:
        logger.error("Error occurred", error=str(e), traceback=True)
