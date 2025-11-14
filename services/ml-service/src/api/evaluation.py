"""
ML 모델 평가 API

엔드포인트:
- GET /v1/ml/models/compare - 두 모델 성능 비교
- GET /v1/ml/models - 모델 목록 조회
- GET /v1/ml/models/{model_id} - 모델 상세 조회
- GET /v1/ml/models/{model_id}/metrics - 모델 성능 지표 조회
"""

from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ml_model import MLModel, DeploymentStatus
from src.deployment.version_manager import ModelVersionManager

router = APIRouter(prefix="/v1/ml/models", tags=["ML Evaluation"])


# Pydantic 모델
class ModelMetrics(BaseModel):
    """모델 성능 지표"""

    accuracy: Optional[float] = Field(None, description="정확도 (0-1)")
    precision: Optional[float] = Field(None, description="정밀도 (0-1)")
    recall: Optional[float] = Field(None, description="재현율 (0-1)")
    f1_score: Optional[float] = Field(None, description="F1 스코어 (0-1)")


class ModelDetail(BaseModel):
    """모델 상세 정보"""

    id: str
    name: str
    version: str
    model_type: str
    deployment_status: str
    trained_at: str
    deployed_at: Optional[str]
    training_period: str
    metrics: ModelMetrics


class ModelComparison(BaseModel):
    """모델 비교 결과"""

    model_1: Dict[str, Any]
    model_2: Dict[str, Any]
    comparison: Dict[str, Optional[float]]
    recommendation: str


# 의존성: 데이터베이스 세션
async def get_db_session() -> AsyncSession:
    """데이터베이스 세션 의존성 (구현 필요)"""
    # TODO: 실제 DB 세션 반환
    raise NotImplementedError("DB 세션 의존성 구현 필요")


@router.get("/compare", response_model=ModelComparison)
async def compare_models(
    model_id_1: str = Query(..., description="첫 번째 모델 ID"),
    model_id_2: str = Query(..., description="두 번째 모델 ID"),
    db_session: AsyncSession = Depends(get_db_session),
) -> ModelComparison:
    """
    두 모델 성능 비교

    Args:
        model_id_1: 첫 번째 모델 ID
        model_id_2: 두 번째 모델 ID
        db_session: 데이터베이스 세션

    Returns:
        ModelComparison: 모델 비교 결과

    Raises:
        HTTPException: 모델을 찾을 수 없거나 비교 실패
    """
    try:
        id_1 = UUID(model_id_1)
        id_2 = UUID(model_id_2)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 모델 ID 형식")

    version_manager = ModelVersionManager(db_session)

    try:
        comparison_result = await version_manager.compare_models(id_1, id_2)
        return ModelComparison(**comparison_result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 비교 실패: {str(e)}")


@router.get("", response_model=List[ModelDetail])
async def list_models(
    deployment_status: Optional[str] = Query(
        None,
        description="배포 상태 필터 (development, staging, production, retired)",
    ),
    model_type: Optional[str] = Query(
        None,
        description="모델 유형 필터 (isolation_forest, lightgbm)",
    ),
    limit: int = Query(10, ge=1, le=100, description="조회 개수 제한"),
    db_session: AsyncSession = Depends(get_db_session),
) -> List[ModelDetail]:
    """
    모델 목록 조회

    Args:
        deployment_status: 배포 상태 필터 (선택)
        model_type: 모델 유형 필터 (선택)
        limit: 조회 개수 제한 (기본값: 10)
        db_session: 데이터베이스 세션

    Returns:
        List[ModelDetail]: 모델 목록

    Raises:
        HTTPException: 조회 실패
    """
    version_manager = ModelVersionManager(db_session)

    # 배포 상태 변환
    deployment_status_enum = None
    if deployment_status:
        try:
            deployment_status_enum = DeploymentStatus(deployment_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"잘못된 배포 상태: {deployment_status}",
            )

    try:
        models = await version_manager.list_models(
            deployment_status=deployment_status_enum,
            model_type=model_type,
            limit=limit,
        )

        result = []
        for model in models:
            training_period = f"{model.training_data_start} to {model.training_data_end}"

            result.append(
                ModelDetail(
                    id=str(model.id),
                    name=model.name,
                    version=model.version,
                    model_type=model.model_type,
                    deployment_status=model.deployment_status.value,
                    trained_at=model.trained_at.isoformat(),
                    deployed_at=(
                        model.deployed_at.isoformat() if model.deployed_at else None
                    ),
                    training_period=training_period,
                    metrics=ModelMetrics(
                        accuracy=float(model.accuracy) if model.accuracy else None,
                        precision=float(model.precision) if model.precision else None,
                        recall=float(model.recall) if model.recall else None,
                        f1_score=float(model.f1_score) if model.f1_score else None,
                    ),
                )
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 목록 조회 실패: {str(e)}")


@router.get("/{model_id}", response_model=ModelDetail)
async def get_model_detail(
    model_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> ModelDetail:
    """
    모델 상세 정보 조회

    Args:
        model_id: 모델 ID
        db_session: 데이터베이스 세션

    Returns:
        ModelDetail: 모델 상세 정보

    Raises:
        HTTPException: 모델을 찾을 수 없음
    """
    try:
        id_uuid = UUID(model_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 모델 ID 형식")

    version_manager = ModelVersionManager(db_session)

    try:
        _, model = await version_manager.load_model(model_id=id_uuid)

        training_period = f"{model.training_data_start} to {model.training_data_end}"

        return ModelDetail(
            id=str(model.id),
            name=model.name,
            version=model.version,
            model_type=model.model_type,
            deployment_status=model.deployment_status.value,
            trained_at=model.trained_at.isoformat(),
            deployed_at=model.deployed_at.isoformat() if model.deployed_at else None,
            training_period=training_period,
            metrics=ModelMetrics(
                accuracy=float(model.accuracy) if model.accuracy else None,
                precision=float(model.precision) if model.precision else None,
                recall=float(model.recall) if model.recall else None,
                f1_score=float(model.f1_score) if model.f1_score else None,
            ),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 조회 실패: {str(e)}")


@router.get("/{model_id}/metrics", response_model=ModelMetrics)
async def get_model_metrics(
    model_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> ModelMetrics:
    """
    모델 성능 지표 조회

    Args:
        model_id: 모델 ID
        db_session: 데이터베이스 세션

    Returns:
        ModelMetrics: 모델 성능 지표

    Raises:
        HTTPException: 모델을 찾을 수 없음
    """
    try:
        id_uuid = UUID(model_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 모델 ID 형식")

    version_manager = ModelVersionManager(db_session)

    try:
        _, model = await version_manager.load_model(model_id=id_uuid)

        return ModelMetrics(
            accuracy=float(model.accuracy) if model.accuracy else None,
            precision=float(model.precision) if model.precision else None,
            recall=float(model.recall) if model.recall else None,
            f1_score=float(model.f1_score) if model.f1_score else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 조회 실패: {str(e)}")


@router.get("/production/current", response_model=Optional[ModelDetail])
async def get_current_production_model(
    model_type: Optional[str] = Query(None, description="모델 유형 필터 (선택)"),
    db_session: AsyncSession = Depends(get_db_session),
) -> Optional[ModelDetail]:
    """
    현재 프로덕션 모델 조회

    Args:
        model_type: 모델 유형 (선택)
        db_session: 데이터베이스 세션

    Returns:
        Optional[ModelDetail]: 프로덕션 모델 (없으면 None)
    """
    version_manager = ModelVersionManager(db_session)

    try:
        model = await version_manager.get_production_model(model_type)

        if not model:
            return None

        training_period = f"{model.training_data_start} to {model.training_data_end}"

        return ModelDetail(
            id=str(model.id),
            name=model.name,
            version=model.version,
            model_type=model.model_type,
            deployment_status=model.deployment_status.value,
            trained_at=model.trained_at.isoformat(),
            deployed_at=model.deployed_at.isoformat() if model.deployed_at else None,
            training_period=training_period,
            metrics=ModelMetrics(
                accuracy=float(model.accuracy) if model.accuracy else None,
                precision=float(model.precision) if model.precision else None,
                recall=float(model.recall) if model.recall else None,
                f1_score=float(model.f1_score) if model.f1_score else None,
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"프로덕션 모델 조회 실패: {str(e)}",
        )
