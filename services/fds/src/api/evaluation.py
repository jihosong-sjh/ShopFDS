"""
FDS 평가 API 엔드포인트

이커머스 서비스에서 거래 평가를 요청하는 내부 API
"""

import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from ..models import get_db, Transaction, DeviceType, RiskLevel, EvaluationStatus
from ..models.schemas import (
    FDSEvaluationRequest,
    FDSEvaluationResponse,
    FDSErrorResponse,
)
from ..engines.evaluation_engine import evaluation_engine

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/internal/fds", tags=["FDS Evaluation"])


def verify_service_token(x_service_token: str = Header(...)) -> bool:
    """
    서비스 간 인증 토큰 검증

    Args:
        x_service_token: 서비스 간 인증 토큰

    Returns:
        bool: 토큰이 유효하면 True

    Raises:
        HTTPException: 토큰이 유효하지 않은 경우
    """
    # TODO: Phase 2에서 실제 JWT 검증 구현
    # 현재는 임시로 하드코딩된 토큰 사용 (개발용)
    VALID_TOKEN = "dev-service-token-12345"

    if x_service_token != VALID_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 서비스 토큰입니다",
        )
    return True


@router.post(
    "/evaluate",
    response_model=FDSEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="거래 위험도 평가",
    description="""
    이커머스 서비스에서 전송한 거래를 평가하고 위험 점수를 산정합니다.

    **인증**: X-Service-Token 헤더 필요

    **응답 시간 SLA**: P95 < 100ms

    **의사결정**:
    - `approve` (위험 점수 0-30): 자동 승인
    - `additional_auth_required` (위험 점수 40-70): 추가 인증 필요
    - `blocked` (위험 점수 80-100): 자동 차단
    """,
    responses={
        200: {
            "description": "평가 성공",
            "model": FDSEvaluationResponse,
        },
        401: {
            "description": "인증 실패",
            "model": FDSErrorResponse,
        },
        500: {
            "description": "서버 에러",
            "model": FDSErrorResponse,
        },
    },
)
async def evaluate_transaction(
    request: FDSEvaluationRequest,
    db: AsyncSession = Depends(get_db),
    token_valid: bool = Depends(verify_service_token),
) -> FDSEvaluationResponse:
    """
    거래를 평가하고 위험 점수를 산정합니다.

    Args:
        request: FDS 평가 요청
        db: 데이터베이스 세션
        token_valid: 서비스 토큰 검증 결과

    Returns:
        FDSEvaluationResponse: 평가 결과

    Raises:
        HTTPException: 평가 중 에러 발생 시
    """
    try:
        logger.info(
            f"FDS 평가 시작: transaction_id={request.transaction_id}, "
            f"user_id={request.user_id}, amount={request.amount}"
        )

        # 1. 평가 엔진으로 거래 평가
        evaluation_result = await evaluation_engine.evaluate(request)

        # 2. 평가 결과를 데이터베이스에 저장
        transaction = Transaction(
            id=request.transaction_id,
            user_id=request.user_id,
            order_id=request.order_id,
            amount=request.amount,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            device_type=DeviceType(request.device_fingerprint.device_type.value),
            geolocation={
                "ip": request.ip_address,
                # TODO: Phase 5에서 실제 IP 지오로케이션 추가
            },
            risk_score=evaluation_result.risk_score,
            risk_level=RiskLevel(evaluation_result.risk_level.value),
            evaluation_status=EvaluationStatus.APPROVED
            if evaluation_result.decision.value == "approve"
            else EvaluationStatus.BLOCKED
            if evaluation_result.decision.value == "blocked"
            else EvaluationStatus.EVALUATING,
            evaluation_time_ms=evaluation_result.evaluation_metadata.evaluation_time_ms,
            evaluated_at=evaluation_result.evaluation_metadata.timestamp,
        )

        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        logger.info(
            f"FDS 평가 완료: transaction_id={request.transaction_id}, "
            f"risk_score={evaluation_result.risk_score}, "
            f"decision={evaluation_result.decision}, "
            f"evaluation_time={evaluation_result.evaluation_metadata.evaluation_time_ms}ms"
        )

        return evaluation_result

    except Exception as e:
        logger.error(
            f"FDS 평가 에러: transaction_id={request.transaction_id}, error={str(e)}",
            exc_info=True,
        )

        # Fail-Open 정책: 에러 발생 시 거래 승인 (사후 검토)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "FDS_EVALUATION_ERROR",
                "message": "FDS 평가 중 에러가 발생했습니다",
                "details": {
                    "fallback_strategy": "fail_open",
                    "action": "approve_with_review",
                    "reason": "FDS 장애 시 거래 중단 방지, 사후 검토 큐에 추가",
                },
            },
        )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="헬스 체크",
    description="FDS 서비스의 헬스 상태를 확인합니다.",
)
async def health_check() -> dict:
    """
    FDS 서비스 헬스 체크

    Returns:
        dict: 헬스 상태
    """
    return {
        "status": "healthy",
        "service": "fds",
        "version": "1.0.0",
    }
