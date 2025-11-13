"""
애플리케이션 환경 설정 관리

Pydantic Settings를 사용하여 타입 안전한 환경 변수 관리를 제공합니다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """
    애플리케이션 전역 설정

    환경 변수에서 자동으로 값을 로드하며, 타입 검증을 수행합니다.
    """

    # 애플리케이션 기본 설정
    APP_NAME: str = "이커머스 플랫폼"
    APP_VERSION: str = "1.0.0"
    ENV: str = "development"  # development, staging, production
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 데이터베이스 설정
    DATABASE_URL: str = (
        "postgresql+asyncpg://shopfds:dev_password@localhost:5432/shopfds_dev"
    )
    SQL_ECHO: bool = False  # SQL 쿼리 로깅
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600  # 1시간

    # Redis 설정
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5

    # JWT 인증 설정
    SECRET_KEY: str = "your-secret-key-change-in-production-INSECURE"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS 설정
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True

    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json, text
    LOG_FILE: str | None = None

    # FDS 서비스 연동
    FDS_SERVICE_URL: str = "http://localhost:8001"
    FDS_TIMEOUT_MS: int = 150  # FDS 호출 타임아웃 (목표: 100ms, 여유: 150ms)

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100  # 분당 요청 수
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # 파일 업로드 설정
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]

    # 이메일 설정 (추후 구현)
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None

    # Sentry 설정 (에러 트래킹)
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str | None = None

    # 모니터링 설정
    PROMETHEUS_ENABLED: bool = False
    PROMETHEUS_PORT: int = 9090

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # 알 수 없는 환경 변수 무시
    )

    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.ENV == "development"

    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.ENV == "production"

    @property
    def is_testing(self) -> bool:
        """테스트 환경 여부"""
        return self.ENV == "testing"

    def get_cors_origins(self) -> List[str]:
        """
        CORS Origins 목록 반환

        환경 변수에서 쉼표로 구분된 문자열을 리스트로 변환합니다.
        """
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS


class TestSettings(Settings):
    """
    테스트 환경 설정

    테스트 시 사용하는 별도의 설정입니다.
    """

    ENV: str = "testing"
    DATABASE_URL: str = (
        "postgresql+asyncpg://shopfds:dev_password@localhost:5432/shopfds_test"
    )
    REDIS_URL: str = "redis://localhost:6379/15"  # 테스트 전용 DB
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


@lru_cache
def get_settings() -> Settings:
    """
    설정 객체 싱글톤 반환

    @lru_cache를 사용하여 한 번만 로드됩니다.

    Returns:
        Settings: 설정 객체

    Example:
        ```python
        from src.config import get_settings

        settings = get_settings()
        print(settings.DATABASE_URL)
        ```
    """
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()
