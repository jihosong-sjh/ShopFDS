"""
XAI API - 설명 가능한 AI 분석 엔드포인트

SHAP/LIME 기반 ML 모델 예측 설명을 제공합니다.

엔드포인트:
- GET /v1/fds/xai/{transaction_id}: 거래에 대한 XAI 분석 결과 조회
- POST /v1/fds/xai/explain: 실시간 XAI 분석 수행

목표:
- 3클릭 이내로 거래 차단 사유 확인 가능
- SHAP 분석 95%가 5초 이내 완료
- 워터폴 차트 데이터 제공
- 상위 5개 위험 요인 제공
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
import uuid
import pandas as pd

from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.services.xai_service import XAIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/fds/xai", tags=["XAI"])

# XAI 서비스 인스턴스 (싱글톤)
_xai_service: Optional[XAIService] = None


def get_xai_service() -> XAIService:
    """XAI 서비스 인스턴스 반환 (의존성 주입)"""
    global _xai_service
    if _xai_service is None:
        _xai_service = XAIService(
            timeout_seconds=5,
            enable_shap=True,
            enable_lime=True,
            max_display_features=5,
        )
    return _xai_service


# ================== Request/Response Models ==================


class ExplainRequest(BaseModel):
    """실시간 XAI 분석 요청"""

    transaction_id: str = Field(..., description="거래 ID")
    features: Dict[str, float] = Field(..., description="Feature 데이터 (dict 형식)")
    model_type: str = Field(
        "tree", description="모델 타입 (tree, deep)", pattern="^(tree|deep)$"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
                "features": {
                    "amount": 15000.0,
                    "velocity_1h": 3,
                    "ip_country_mismatch": 1,
                    "bot_score": 0.85,
                    "device_fingerprint_changes": 2,
                },
                "model_type": "tree",
            }
        }


class SHAPValue(BaseModel):
    """SHAP 값"""

    feature: str = Field(..., description="Feature 이름")
    value: float = Field(..., description="Feature 값")
    shap_value: float = Field(..., description="SHAP 값")
    contribution: float = Field(..., description="기여도 (양수: 위험 증가, 음수: 위험 감소)")
    rank: int = Field(..., description="순위 (1부터 시작)")


class RiskFactor(BaseModel):
    """위험 요인"""

    factor: str = Field(..., description="위험 요인 이름")
    value: float = Field(..., description="Feature 값")
    contribution: float = Field(..., description="기여도")
    rank: int = Field(..., description="순위")
    impact: str = Field(..., description="영향 (위험 증가/감소)")


class XAIResponse(BaseModel):
    """XAI 분석 응답"""

    transaction_id: str = Field(..., description="거래 ID")
    shap_values: Optional[list] = Field(None, description="SHAP 값 목록")
    lime_explanation: Optional[Dict[str, Any]] = Field(None, description="LIME 설명")
    top_risk_factors: list = Field([], description="상위 5개 위험 요인")
    explanation_time_ms: int = Field(..., description="분석 소요 시간 (밀리초)")
    generated_at: str = Field(..., description="생성 일시 (ISO 8601)")
    validation: Optional[Dict[str, Any]] = Field(None, description="SHAP 검증 결과")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
                "shap_values": [
                    {
                        "feature": "base_value",
                        "value": 0.15,
                        "shap_value": 0.0,
                        "contribution": 0.0,
                        "rank": 0,
                    },
                    {
                        "feature": "bot_score",
                        "value": 0.85,
                        "shap_value": 0.42,
                        "contribution": 0.42,
                        "rank": 1,
                    },
                    {
                        "feature": "velocity_1h",
                        "value": 3.0,
                        "shap_value": 0.28,
                        "contribution": 0.28,
                        "rank": 2,
                    },
                ],
                "lime_explanation": {
                    "prediction": 0.87,
                    "local_prediction": 0.85,
                    "score": 0.92,
                    "intercept": 0.15,
                    "explanations": [
                        {"feature": "bot_score", "weight": 0.45},
                        {"feature": "velocity_1h", "weight": 0.30},
                    ],
                },
                "top_risk_factors": [
                    {
                        "factor": "bot_score",
                        "value": 0.85,
                        "contribution": 0.42,
                        "rank": 1,
                        "impact": "위험 증가",
                    },
                    {
                        "factor": "velocity_1h",
                        "value": 3.0,
                        "contribution": 0.28,
                        "rank": 2,
                        "impact": "위험 증가",
                    },
                ],
                "explanation_time_ms": 1850,
                "generated_at": "2025-11-18T12:00:00Z",
                "validation": {"valid": True, "mismatches": [], "total_features": 10},
            }
        }


# ================== API Endpoints ==================


@router.get("/{transaction_id}", response_model=XAIResponse)
async def get_explanation(
    transaction_id: str,
    db_session: AsyncSession = Depends(get_db),
    xai_service: XAIService = Depends(get_xai_service),
):
    """
    T083: 거래 ID로 저장된 XAI 분석 결과 조회

    거래에 대한 SHAP/LIME 분석 결과를 데이터베이스에서 조회합니다.

    Args:
        transaction_id: 거래 ID (UUID)

    Returns:
        XAI 분석 결과 (SHAP 값, LIME 설명, 상위 위험 요인)

    Raises:
        404: 분석 결과를 찾을 수 없음
    """
    try:
        # UUID 검증
        try:
            txn_uuid = uuid.UUID(transaction_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transaction_id format: {transaction_id}",
            )

        # 데이터베이스에서 조회
        result = await xai_service.get_explanation_by_transaction(txn_uuid, db_session)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"XAI explanation not found for transaction {transaction_id}",
            )

        logger.info(f"[XAI API] Explanation retrieved for transaction {transaction_id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[XAI API] Failed to retrieve explanation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve XAI explanation: {str(e)}",
        )


@router.post("/explain", response_model=XAIResponse)
async def explain_prediction(
    request: ExplainRequest,
    save_to_db: bool = Query(True, description="분석 결과를 데이터베이스에 저장할지 여부"),
    db_session: AsyncSession = Depends(get_db),
    xai_service: XAIService = Depends(get_xai_service),
):
    """
    실시간 XAI 분석 수행

    주어진 거래 데이터에 대해 SHAP/LIME 분석을 수행하고 설명을 반환합니다.

    Args:
        request: 분석 요청 (transaction_id, features, model_type)
        save_to_db: 결과를 DB에 저장할지 여부

    Returns:
        XAI 분석 결과

    Raises:
        400: 잘못된 요청
        500: 분석 실패
    """
    try:
        # UUID 검증
        try:
            txn_uuid = uuid.UUID(request.transaction_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transaction_id format: {request.transaction_id}",
            )

        # Features를 DataFrame으로 변환
        features_df = pd.DataFrame([request.features])

        # 모델 로드 (실제 구현에서는 모델 레지스트리에서 로드)
        # 여기서는 더미 모델 사용 (실제로는 ML 서비스에서 모델 로드)
        model = None  # TODO: 실제 모델 로드
        if model is None:
            logger.warning(
                "[XAI API] Model not loaded, using mock model for demonstration"
            )

            # Mock 모델 (실제로는 ML 서비스에서 로드)
            class MockModel:
                def predict_proba(self, X):
                    import numpy as np

                    # 간단한 규칙 기반 예측
                    return np.array([[0.3, 0.7]] * len(X))

            model = MockModel()

        # XAI 분석 수행
        result = await xai_service.explain_prediction(
            transaction_id=txn_uuid,
            features=features_df,
            model=model,
            model_type=request.model_type,
            db_session=db_session if save_to_db else None,
        )

        logger.info(
            f"[XAI API] Explanation generated for transaction {request.transaction_id} "
            f"in {result['explanation_time_ms']}ms"
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[XAI API] Failed to explain prediction: {e}")
        import traceback

        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to explain prediction: {str(e)}",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(xai_service: XAIService = Depends(get_xai_service)):
    """
    XAI 서비스 헬스 체크

    SHAP/LIME 라이브러리 설치 여부 및 서비스 상태 확인

    Returns:
        서비스 상태
    """
    return {
        "status": "healthy",
        "shap_enabled": xai_service.enable_shap,
        "lime_enabled": xai_service.enable_lime,
        "timeout_seconds": xai_service.timeout_seconds,
        "max_display_features": xai_service.max_display_features,
    }
