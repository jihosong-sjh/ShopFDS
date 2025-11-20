"""
ML Service Configuration

Environment-based configuration for ML Service.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """ML Service settings"""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/shopfds",
    )
    DATABASE_URL_ASYNC: str = os.getenv(
        "DATABASE_URL_ASYNC",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/shopfds",
    )

    # Celery
    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL",
        "redis://localhost:6379/0",
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/0",
    )

    # Slack
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")

    # Model paths
    MODEL_STORAGE_PATH: str = os.getenv("MODEL_STORAGE_PATH", "./models")
    MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

    # Performance thresholds
    F1_THRESHOLD: float = float(os.getenv("F1_THRESHOLD", "0.85"))
    PRECISION_THRESHOLD: float = float(os.getenv("PRECISION_THRESHOLD", "0.90"))
    RECALL_THRESHOLD: float = float(os.getenv("RECALL_THRESHOLD", "0.80"))

    # Drift detection
    KS_THRESHOLD: float = float(os.getenv("KS_THRESHOLD", "0.05"))
    PSI_THRESHOLD: float = float(os.getenv("PSI_THRESHOLD", "0.1"))

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
