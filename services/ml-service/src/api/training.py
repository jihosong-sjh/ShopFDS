"""
ML 모델 학습 API

엔드포인트:
- POST /v1/ml/train - 모델 학습 트리거
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.models.ml_model import MLModel, DeploymentStatus
from src.models.fraud_case import FraudCase
from src.training.train_isolation_forest import train_isolation_forest
from src.training.train_lightgbm import train_lightgbm
from src.evaluation.evaluate import evaluate_model
from src.deployment.version_manager import ModelVersionManager

router = APIRouter(prefix="/v1/ml", tags=["ML Training"])


# Pydantic 모델
class TrainingRequest(BaseModel):
    """모델 학습 요청"""

    model_type: str = Field(
        ...,
        description="모델 유형 (isolation_forest, lightgbm)",
        example="isolation_forest",
    )
    training_period_days: int = Field(
        default=30,
        ge=7,
        le=365,
        description="학습 데이터 기간 (일)",
    )
    hyperparameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="하이퍼파라미터 (선택)",
        example={
            "n_estimators": 100,
            "contamination": 0.1,
            "max_samples": "auto",
        },
    )
    auto_deploy_to_staging: bool = Field(
        default=False,
        description="학습 완료 후 자동으로 스테이징 환경에 배포",
    )


class TrainingResponse(BaseModel):
    """모델 학습 응답"""

    message: str
    model_id: str
    model_name: str
    version: str
    training_started_at: str
    estimated_completion_time: str
    status: str


class TrainingStatusResponse(BaseModel):
    """모델 학습 상태 응답"""

    model_id: str
    status: str
    progress_percentage: int
    current_step: str
    elapsed_time_seconds: int
    estimated_remaining_seconds: Optional[int]
    error_message: Optional[str]


# 의존성: 데이터베이스 세션 (실제 구현 시 추가 필요)
async def get_db_session() -> AsyncSession:
    """데이터베이스 세션 의존성 (구현 필요)"""
    # TODO: 실제 DB 세션 반환
    raise NotImplementedError("DB 세션 의존성 구현 필요")


# 학습 상태 추적 (메모리 캐시)
training_status_cache: Dict[str, Dict[str, Any]] = {}


def update_training_status(
    model_id: str,
    status: str,
    progress: int,
    current_step: str,
    error: Optional[str] = None,
) -> None:
    """학습 상태 업데이트"""
    if model_id not in training_status_cache:
        training_status_cache[model_id] = {
            "start_time": datetime.utcnow(),
        }

    training_status_cache[model_id].update(
        {
            "status": status,
            "progress": progress,
            "current_step": current_step,
            "error": error,
            "updated_at": datetime.utcnow(),
        }
    )


async def train_model_background(
    model_type: str,
    training_period_days: int,
    hyperparameters: Optional[Dict[str, Any]],
    auto_deploy_to_staging: bool,
    db_session: AsyncSession,
) -> None:
    """
    백그라운드 모델 학습 작업

    Args:
        model_type: 모델 유형
        training_period_days: 학습 데이터 기간
        hyperparameters: 하이퍼파라미터
        auto_deploy_to_staging: 자동 스테이징 배포 여부
        db_session: 데이터베이스 세션
    """
    model_id = None

    try:
        # 1. 학습 데이터 준비
        update_training_status(
            model_id or "temp",
            status="preparing_data",
            progress=10,
            current_step="학습 데이터 로드 중",
        )

        # 학습 데이터 기간 계산
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=training_period_days)

        # FraudCase 데이터 조회 (레이블)
        # TODO: 실제 학습 데이터 로드 로직 구현
        # fraud_cases = await load_fraud_cases(db_session, start_date, end_date)
        # transaction_data = await load_transaction_data(db_session, start_date, end_date)

        # 2. 모델 학습
        update_training_status(
            model_id or "temp",
            status="training",
            progress=30,
            current_step=f"{model_type} 모델 학습 중",
        )

        if model_type == "isolation_forest":
            # Isolation Forest 학습
            model, metrics = await asyncio.to_thread(
                train_isolation_forest,
                training_data=None,  # TODO: 실제 데이터 전달
                hyperparameters=hyperparameters,
            )
        elif model_type == "lightgbm":
            # LightGBM 학습
            model, metrics = await asyncio.to_thread(
                train_lightgbm,
                training_data=None,  # TODO: 실제 데이터 전달
                hyperparameters=hyperparameters,
            )
        else:
            raise ValueError(f"지원하지 않는 모델 유형: {model_type}")

        # 3. 모델 평가
        update_training_status(
            model_id or "temp",
            status="evaluating",
            progress=70,
            current_step="모델 성능 평가 중",
        )

        # TODO: 실제 평가 데이터로 평가
        # evaluation_results = await asyncio.to_thread(
        #     evaluate_model,
        #     model=model,
        #     test_data=test_data,
        # )

        # 4. MLflow에 모델 등록
        update_training_status(
            model_id or "temp",
            status="registering",
            progress=90,
            current_step="MLflow에 모델 등록 중",
        )

        version_manager = ModelVersionManager(db_session)

        # 버전 자동 생성 (YYYY.MM.DD 형식)
        version = datetime.utcnow().strftime("%Y.%m.%d")

        ml_model = await version_manager.register_model(
            model=model,
            model_name=f"{model_type}-fraud-detection",
            model_type=model_type,
            version=version,
            training_data_start=start_date.strftime("%Y-%m-%d"),
            training_data_end=end_date.strftime("%Y-%m-%d"),
            metrics=metrics,
            params=hyperparameters,
            tags={
                "training_period_days": str(training_period_days),
                "auto_trained": "true",
            },
        )

        model_id = str(ml_model.id)

        # 5. 자동 스테이징 배포
        if auto_deploy_to_staging:
            update_training_status(
                model_id,
                status="deploying_to_staging",
                progress=95,
                current_step="스테이징 환경에 배포 중",
            )

            await version_manager.promote_to_staging(ml_model.id)

        # 6. 완료
        update_training_status(
            model_id,
            status="completed",
            progress=100,
            current_step="학습 완료",
        )

    except Exception as e:
        update_training_status(
            model_id or "temp",
            status="failed",
            progress=0,
            current_step="학습 실패",
            error=str(e),
        )
        raise


@router.post("/train", response_model=TrainingResponse, status_code=202)
async def trigger_model_training(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_db_session),
) -> TrainingResponse:
    """
    모델 학습 트리거

    비동기로 모델 학습을 시작하고 즉시 응답을 반환합니다.
    학습 상태는 GET /v1/ml/train/status/{model_id}로 확인할 수 있습니다.

    Args:
        request: 학습 요청 데이터
        background_tasks: FastAPI 백그라운드 작업
        db_session: 데이터베이스 세션

    Returns:
        TrainingResponse: 학습 시작 응답

    Raises:
        HTTPException: 잘못된 요청 또는 학습 시작 실패
    """
    # 모델 유형 검증
    if request.model_type not in ["isolation_forest", "lightgbm"]:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 모델 유형: {request.model_type}",
        )

    # 학습 시작 시간
    training_started_at = datetime.utcnow()

    # 예상 완료 시간 (모델 유형별)
    estimated_duration_minutes = {
        "isolation_forest": 10,
        "lightgbm": 30,
    }
    estimated_completion_time = training_started_at + timedelta(
        minutes=estimated_duration_minutes.get(request.model_type, 15)
    )

    # 버전 생성
    version = training_started_at.strftime("%Y.%m.%d")
    model_name = f"{request.model_type}-fraud-detection-{version}"

    # 임시 모델 ID (실제 모델 ID는 학습 완료 후 생성)
    temp_model_id = f"temp-{training_started_at.timestamp()}"

    # 백그라운드 작업 추가
    background_tasks.add_task(
        train_model_background,
        model_type=request.model_type,
        training_period_days=request.training_period_days,
        hyperparameters=request.hyperparameters,
        auto_deploy_to_staging=request.auto_deploy_to_staging,
        db_session=db_session,
    )

    # 초기 상태 설정
    update_training_status(
        temp_model_id,
        status="started",
        progress=0,
        current_step="학습 시작",
    )

    return TrainingResponse(
        message=f"{request.model_type} 모델 학습이 시작되었습니다",
        model_id=temp_model_id,
        model_name=model_name,
        version=version,
        training_started_at=training_started_at.isoformat(),
        estimated_completion_time=estimated_completion_time.isoformat(),
        status="started",
    )


@router.get("/train/status/{model_id}", response_model=TrainingStatusResponse)
async def get_training_status(
    model_id: str,
) -> TrainingStatusResponse:
    """
    모델 학습 상태 조회

    Args:
        model_id: 모델 ID

    Returns:
        TrainingStatusResponse: 학습 상태

    Raises:
        HTTPException: 모델을 찾을 수 없음
    """
    if model_id not in training_status_cache:
        raise HTTPException(
            status_code=404,
            detail=f"학습 상태를 찾을 수 없습니다: {model_id}",
        )

    status_data = training_status_cache[model_id]
    start_time = status_data["start_time"]
    elapsed_seconds = int((datetime.utcnow() - start_time).total_seconds())

    # 예상 남은 시간 계산
    progress = status_data["progress"]
    if progress > 0 and progress < 100:
        total_estimated_seconds = int(elapsed_seconds * 100 / progress)
        estimated_remaining_seconds = total_estimated_seconds - elapsed_seconds
    else:
        estimated_remaining_seconds = None

    return TrainingStatusResponse(
        model_id=model_id,
        status=status_data["status"],
        progress_percentage=status_data["progress"],
        current_step=status_data["current_step"],
        elapsed_time_seconds=elapsed_seconds,
        estimated_remaining_seconds=estimated_remaining_seconds,
        error_message=status_data.get("error"),
    )


@router.get("/train/history", response_model=list[Dict[str, Any]])
async def get_training_history(
    limit: int = 10,
    db_session: AsyncSession = Depends(get_db_session),
) -> list[Dict[str, Any]]:
    """
    모델 학습 히스토리 조회

    Args:
        limit: 조회 개수 제한 (기본값: 10)
        db_session: 데이터베이스 세션

    Returns:
        list[Dict[str, Any]]: 학습 히스토리
    """
    # 최근 학습된 모델 조회 (trained_at 기준 내림차순)
    result = await db_session.execute(
        select(MLModel)
        .order_by(MLModel.trained_at.desc())
        .limit(limit)
    )
    models = result.scalars().all()

    history = []
    for model in models:
        history.append(
            {
                "model_id": str(model.id),
                "name": model.name,
                "version": model.version,
                "model_type": model.model_type,
                "trained_at": model.trained_at.isoformat(),
                "deployment_status": model.deployment_status.value,
                "metrics": {
                    "accuracy": float(model.accuracy) if model.accuracy else None,
                    "precision": float(model.precision) if model.precision else None,
                    "recall": float(model.recall) if model.recall else None,
                    "f1_score": float(model.f1_score) if model.f1_score else None,
                },
            }
        )

    return history
