"""
커스텀 예외 클래스 정의

애플리케이션 전역에서 사용하는 예외 클래스를 정의합니다.
"""

from typing import Optional, Any
from fastapi import status


class AppException(Exception):
    """
    애플리케이션 기본 예외 클래스

    모든 커스텀 예외는 이 클래스를 상속받습니다.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "app_error",
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AppException):
    """
    입력 검증 실패 예외

    사용자 입력이 유효하지 않을 때 발생합니다.
    """

    def __init__(
        self,
        message: str = "입력 데이터가 유효하지 않습니다.",
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        if field:
            details = details or {}
            details["field"] = field

        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="validation_error",
            details=details,
        )


class NotFoundException(AppException):
    """
    리소스를 찾을 수 없을 때 발생하는 예외
    """

    def __init__(
        self,
        resource: str = "리소스",
        resource_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        if message is None:
            if resource_id:
                message = f"{resource}를 찾을 수 없습니다 (ID: {resource_id})"
            else:
                message = f"{resource}를 찾을 수 없습니다."

        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="not_found",
            details={"resource": resource, "resource_id": resource_id},
        )


class UnauthorizedException(AppException):
    """
    인증 실패 예외 (401 Unauthorized)
    """

    def __init__(self, message: str = "인증에 실패했습니다."):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="unauthorized",
        )


class ForbiddenException(AppException):
    """
    권한 부족 예외 (403 Forbidden)
    """

    def __init__(self, message: str = "접근 권한이 없습니다."):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="forbidden",
        )


class ConflictException(AppException):
    """
    리소스 충돌 예외 (409 Conflict)

    예: 이미 존재하는 이메일로 회원가입 시도
    """

    def __init__(
        self,
        message: str = "요청이 현재 서버 상태와 충돌합니다.",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="conflict",
            details=details,
        )


class BusinessRuleException(AppException):
    """
    비즈니스 규칙 위반 예외

    예: 재고 부족, 결제 한도 초과 등
    """

    def __init__(
        self,
        message: str,
        rule: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        if rule:
            details = details or {}
            details["rule"] = rule

        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="business_rule_violation",
            details=details,
        )


class ExternalServiceException(AppException):
    """
    외부 서비스 통신 실패 예외

    예: FDS 서비스 연결 실패, 결제 게이트웨이 오류 등
    """

    def __init__(
        self,
        service: str,
        message: str = "외부 서비스 요청에 실패했습니다.",
        details: Optional[dict[str, Any]] = None,
    ):
        details = details or {}
        details["service"] = service

        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="external_service_error",
            details=details,
        )


class RateLimitException(AppException):
    """
    요청 속도 제한 초과 예외 (429 Too Many Requests)
    """

    def __init__(
        self,
        message: str = "너무 많은 요청을 보냈습니다. 잠시 후 다시 시도해주세요.",
        retry_after: Optional[int] = None,
    ):
        details = {}
        if retry_after:
            details["retry_after_seconds"] = retry_after

        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="rate_limit_exceeded",
            details=details,
        )


class DatabaseException(AppException):
    """
    데이터베이스 오류 예외
    """

    def __init__(
        self,
        message: str = "데이터베이스 오류가 발생했습니다.",
        operation: Optional[str] = None,
    ):
        details = {}
        if operation:
            details["operation"] = operation

        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="database_error",
            details=details,
        )


# 이커머스 전용 예외 클래스


class ProductNotFoundException(NotFoundException):
    """상품을 찾을 수 없을 때"""

    def __init__(self, product_id: str):
        super().__init__(resource="상품", resource_id=product_id)


class OutOfStockException(BusinessRuleException):
    """재고 부족 예외"""

    def __init__(self, product_name: str, available: int = 0):
        super().__init__(
            message=f"'{product_name}' 상품의 재고가 부족합니다.",
            rule="stock_available",
            details={"product": product_name, "available_stock": available},
        )


class InvalidCartException(ValidationException):
    """장바구니 오류"""

    def __init__(self, message: str = "장바구니가 유효하지 않습니다."):
        super().__init__(message=message, field="cart")


class OrderNotFoundException(NotFoundException):
    """주문을 찾을 수 없을 때"""

    def __init__(self, order_id: str):
        super().__init__(resource="주문", resource_id=order_id)


class PaymentFailedException(ExternalServiceException):
    """결제 실패 예외"""

    def __init__(self, reason: Optional[str] = None):
        message = "결제 처리에 실패했습니다."
        if reason:
            message += f" (사유: {reason})"

        super().__init__(
            service="payment_gateway",
            message=message,
            details={"reason": reason} if reason else None,
        )


class FDSBlockedException(BusinessRuleException):
    """FDS에 의해 거래가 차단된 예외"""

    def __init__(self, risk_score: int, reason: str):
        super().__init__(
            message="거래가 보안 시스템에 의해 차단되었습니다.",
            rule="fds_risk_threshold",
            details={"risk_score": risk_score, "reason": reason},
        )


# Alias for backward compatibility
AuthenticationError = UnauthorizedException
ResourceNotFoundError = NotFoundException
ValidationError = ValidationException
BusinessLogicError = BusinessRuleException
