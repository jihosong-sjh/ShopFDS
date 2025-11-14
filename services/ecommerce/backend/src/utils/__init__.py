"""
유틸리티 패키지

보안, 로깅, Redis, 예외 처리 등의 공통 유틸리티를 제공합니다.
"""

from src.utils.security import (
    PasswordHasher,
    JWTManager,
    SecurityUtils,
)

from src.utils.logging import (
    setup_logging,
    get_logger,
    RequestLogger,
    AuditLogger,
    audit_logger,
)

from src.utils.redis_client import (
    init_redis,
    close_redis,
    get_redis,
    get_redis_cache,
    get_rate_limiter,
    RedisCache,
    RateLimiter,
)

from src.utils.exceptions import (
    AppException,
    ValidationException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ConflictException,
    BusinessRuleException,
    ExternalServiceException,
    RateLimitException,
    DatabaseException,
    # 이커머스 전용
    ProductNotFoundException,
    OutOfStockException,
    InvalidCartException,
    OrderNotFoundException,
    PaymentFailedException,
    FDSBlockedException,
)

__all__ = [
    # 보안
    "PasswordHasher",
    "JWTManager",
    "SecurityUtils",
    # 로깅
    "setup_logging",
    "get_logger",
    "RequestLogger",
    "AuditLogger",
    "audit_logger",
    # Redis
    "init_redis",
    "close_redis",
    "get_redis",
    "get_redis_cache",
    "get_rate_limiter",
    "RedisCache",
    "RateLimiter",
    # 예외
    "AppException",
    "ValidationException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "ConflictException",
    "BusinessRuleException",
    "ExternalServiceException",
    "RateLimitException",
    "DatabaseException",
    "ProductNotFoundException",
    "OutOfStockException",
    "InvalidCartException",
    "OrderNotFoundException",
    "PaymentFailedException",
    "FDSBlockedException",
]
