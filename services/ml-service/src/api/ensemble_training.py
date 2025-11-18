"""
Ensemble Model Training API (T067-T068)

앙상블 모델 학습 및 모니터링 엔드포인트:
- POST /v1/ml/ensemble/train - 앙상블 모델 학습 트리거
- GET /v1/ml/ensemble/status/{job_id} - 학습 진행 상황 모니터링
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field


router = APIRouter(prefix="/v1/ml", tags=["Ensemble Training"])


# ===== Pydantic Models =====


class EnsembleTrainingRequest(BaseModel):
    """앙상블 모델 학습 요청"""

    training_period_days: int = Field(
        default=180,
        ge=30,
        le=365,
        description="학습 데이터 기간 (일)",
    )
    smote_target_ratio: float = Field(
        default=0.4,
        ge=0.1,
        le=0.5,
        description="SMOTE 목표 사기 비율 (0.4 = 40%%)",
    )
    optimize_threshold: bool = Field(
        default=True,
        description="임계값 최적화 여부",
    )
    save_models: bool = Field(
        default=True,
        description="모델 저장 여부",
    )
    track_with_mlflow: bool = Field(
        default=True,
        description="MLflow로 실험 추적 여부",
    )


class EnsembleTrainingResponse(BaseModel):
    """앙상블 모델 학습 응답"""

    message: str
    job_id: str
    status: str
    training_started_at: str
    estimated_completion_minutes: int


class EnsembleStatusResponse(BaseModel):
    """앙상블 학습 상태 응답"""

    job_id: str
    status: str
    progress_percentage: int
    current_step: str
    elapsed_minutes: float
    estimated_remaining_minutes: Optional[float]
    models_completed: int
    total_models: int
    results: Optional[Dict[str, Any]]
    error_message: Optional[str]


# ===== Status Tracking =====


ensemble_training_status: Dict[str, Dict[str, Any]] = {}


def update_ensemble_status(
    job_id: str,
    status: str,
    progress: int,
    current_step: str,
    models_completed: int = 0,
    results: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """앙상블 학습 상태 업데이트"""
    if job_id not in ensemble_training_status:
        ensemble_training_status[job_id] = {
            "start_time": datetime.utcnow(),
            "total_models": 4,  # RF, XGB, AE, LSTM
        }

    ensemble_training_status[job_id].update(
        {
            "status": status,
            "progress": progress,
            "current_step": current_step,
            "models_completed": models_completed,
            "results": results,
            "error": error,
            "updated_at": datetime.utcnow(),
        }
    )


# ===== Background Training Task =====


async def train_ensemble_background(
    job_id: str,
    training_period_days: int,
    smote_target_ratio: float,
    optimize_threshold: bool,
    save_models: bool,
    track_with_mlflow: bool,
) -> None:
    """
    백그라운드 앙상블 모델 학습 작업

    Args:
        job_id: 작업 ID
        training_period_days: 학습 데이터 기간
        smote_target_ratio: SMOTE 목표 비율
        optimize_threshold: 임계값 최적화 여부
        save_models: 모델 저장 여부
        track_with_mlflow: MLflow 추적 여부
    """
    try:
        # 1. 데이터 로드
        update_ensemble_status(
            job_id,
            status="loading_data",
            progress=10,
            current_step="학습 데이터 로드 중",
        )

        # TODO: 실제 데이터 로드 구현
        # from src.data.data_loader import load_fraud_data
        # X_train, y_train, X_test, y_test = await load_fraud_data(training_period_days)

        # Dummy data for demonstration
        import pandas as pd
        import numpy as np

        n_samples = 10000
        n_features = 50

        X_train = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"feature_{i}" for i in range(n_features)],
        )
        y_train = pd.Series(np.random.choice([0, 1], size=n_samples, p=[0.95, 0.05]))

        X_test = pd.DataFrame(
            np.random.randn(2000, n_features),
            columns=[f"feature_{i}" for i in range(n_features)],
        )
        y_test = pd.Series(np.random.choice([0, 1], size=2000, p=[0.95, 0.05]))

        # 2. SMOTE 데이터 리샘플링
        update_ensemble_status(
            job_id,
            status="resampling",
            progress=20,
            current_step="SMOTE 데이터 리샘플링 중",
        )

        from src.training.data_resampler import resample_fraud_data

        X_train_resampled, y_train_resampled, resample_stats = await asyncio.to_thread(
            resample_fraud_data,
            X_train,
            y_train,
            strategy="smote",
            target_ratio=smote_target_ratio,
        )

        # 3. 앙상블 모델 학습
        update_ensemble_status(
            job_id,
            status="training_models",
            progress=30,
            current_step="앙상블 모델 학습 중 (Random Forest, XGBoost, Autoencoder, LSTM)",
        )

        from src.models.ensemble_model import train_ensemble

        ensemble_model, ensemble_results = await asyncio.to_thread(
            train_ensemble,
            X_train_resampled,
            y_train_resampled,
            X_test,
            y_test,
            optimize_threshold=optimize_threshold,
        )

        # 4. MLflow 추적
        if track_with_mlflow:
            update_ensemble_status(
                job_id,
                status="tracking_mlflow",
                progress=85,
                current_step="MLflow에 실험 추적 중",
            )

            from src.training.mlflow_tracker import MLflowTracker

            tracker = MLflowTracker(experiment_name="ensemble-fraud-detection")

            params = {
                "training_period_days": training_period_days,
                "smote_target_ratio": smote_target_ratio,
                "rf_weight": 0.30,
                "xgb_weight": 0.35,
                "ae_weight": 0.25,
                "lstm_weight": 0.10,
            }

            tracker.log_ensemble_training(
                params=params,
                train_metrics=ensemble_results["train_metrics"],
                eval_metrics=ensemble_results["eval_metrics"],
            )

        # 5. 모델 저장
        if save_models:
            update_ensemble_status(
                job_id,
                status="saving_models",
                progress=90,
                current_step="모델 저장 중",
            )

            import os

            model_dir = f"./models/ensemble_{job_id}"
            os.makedirs(model_dir, exist_ok=True)

            await asyncio.to_thread(ensemble_model.save, model_dir)

        # 6. 완료
        update_ensemble_status(
            job_id,
            status="completed",
            progress=100,
            current_step="학습 완료",
            models_completed=4,
            results=ensemble_results,
        )

    except Exception as e:
        import traceback

        update_ensemble_status(
            job_id,
            status="failed",
            progress=0,
            current_step="학습 실패",
            error=str(e) + "\n" + traceback.format_exc(),
        )
        raise


# ===== API Endpoints =====


@router.post(
    "/ensemble/train", response_model=EnsembleTrainingResponse, status_code=202
)
async def trigger_ensemble_training(
    request: EnsembleTrainingRequest,
    background_tasks: BackgroundTasks,
) -> EnsembleTrainingResponse:
    """
    앙상블 모델 학습 트리거 (T067)

    4개 ML 모델(Random Forest, XGBoost, Autoencoder, LSTM)을 학습하고
    가중 투표 방식으로 결합합니다.

    목표 성능:
    - F1 Score: 0.95 이상
    - 오탐률(FPR): 6%% 이하
    - 미탐률(FNR): 12.6%% 이하

    Args:
        request: 앙상블 학습 요청
        background_tasks: 백그라운드 작업

    Returns:
        EnsembleTrainingResponse: 학습 시작 응답

    Example:
        ```bash
        curl -X POST "http://localhost:8002/v1/ml/ensemble/train" \\
          -H "Content-Type: application/json" \\
          -d '{
            "training_period_days": 180,
            "smote_target_ratio": 0.4,
            "optimize_threshold": true,
            "save_models": true,
            "track_with_mlflow": true
          }'
        ```
    """
    job_id = str(uuid.uuid4())
    training_started_at = datetime.utcnow()

    # 예상 완료 시간 (앙상블 학습은 30-60분 소요)
    estimated_completion_minutes = 45

    # 백그라운드 작업 추가
    background_tasks.add_task(
        train_ensemble_background,
        job_id=job_id,
        training_period_days=request.training_period_days,
        smote_target_ratio=request.smote_target_ratio,
        optimize_threshold=request.optimize_threshold,
        save_models=request.save_models,
        track_with_mlflow=request.track_with_mlflow,
    )

    # 초기 상태 설정
    update_ensemble_status(
        job_id, status="started", progress=0, current_step="앙상블 학습 시작"
    )

    return EnsembleTrainingResponse(
        message="앙상블 모델 학습이 시작되었습니다 (Random Forest + XGBoost + Autoencoder + LSTM)",
        job_id=job_id,
        status="started",
        training_started_at=training_started_at.isoformat(),
        estimated_completion_minutes=estimated_completion_minutes,
    )


@router.get("/ensemble/status/{job_id}", response_model=EnsembleStatusResponse)
async def get_ensemble_training_status(
    job_id: str,
) -> EnsembleStatusResponse:
    """
    앙상블 모델 학습 진행 상황 조회 (T068)

    Args:
        job_id: 작업 ID

    Returns:
        EnsembleStatusResponse: 학습 상태
          - status: started, loading_data, resampling, training_models, tracking_mlflow, saving_models, completed, failed
          - progress_percentage: 0-100
          - models_completed: 완료된 개별 모델 수 (0-4)
          - results: 학습 완료 시 평가 메트릭

    Raises:
        HTTPException: 작업을 찾을 수 없음

    Example:
        ```bash
        curl "http://localhost:8002/v1/ml/ensemble/status/550e8400-e29b-41d4-a716-446655440000"
        ```
    """
    if job_id not in ensemble_training_status:
        raise HTTPException(
            status_code=404,
            detail=f"학습 작업을 찾을 수 없습니다: {job_id}",
        )

    status_data = ensemble_training_status[job_id]
    start_time = status_data["start_time"]
    elapsed_minutes = (datetime.utcnow() - start_time).total_seconds() / 60.0

    # 예상 남은 시간 계산
    progress = status_data["progress"]
    if 0 < progress < 100:
        total_estimated_minutes = elapsed_minutes * 100 / progress
        estimated_remaining_minutes = total_estimated_minutes - elapsed_minutes
    else:
        estimated_remaining_minutes = None

    return EnsembleStatusResponse(
        job_id=job_id,
        status=status_data["status"],
        progress_percentage=status_data["progress"],
        current_step=status_data["current_step"],
        elapsed_minutes=round(elapsed_minutes, 2),
        estimated_remaining_minutes=(
            round(estimated_remaining_minutes, 2)
            if estimated_remaining_minutes
            else None
        ),
        models_completed=status_data.get("models_completed", 0),
        total_models=status_data.get("total_models", 4),
        results=status_data.get("results"),
        error_message=status_data.get("error"),
    )
