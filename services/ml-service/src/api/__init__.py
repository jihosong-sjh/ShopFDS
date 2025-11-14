"""
ML 서비스 API

이 패키지는 ML 서비스의 REST API 엔드포인트를 포함합니다:
- 모델 학습 API
- 모델 배포 API
- 모델 평가 API
"""

from .training import router as training_router
from .deployment import router as deployment_router
from .evaluation import router as evaluation_router

__all__ = [
    "training_router",
    "deployment_router",
    "evaluation_router",
]
