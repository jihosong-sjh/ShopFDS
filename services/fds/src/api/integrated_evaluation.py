"""
통합 FDS 평가 API 엔드포인트

모든 고급 FDS 엔진을 조합한 종합적인 사기 탐지 평가 API

**통합 엔진**:
- Fingerprint Engine: 디바이스 핑거프린팅 및 블랙리스트 체크
- Behavior Analysis Engine: 마우스/키보드/클릭스트림 봇 탐지
- Network Analysis Engine: TOR/VPN/Proxy 탐지, GeoIP 분석
- Fraud Rule Engine: 30개 실전 사기 탐지 룰
- ML Engine: 앙상블 ML 모델 기반 정밀 예측

**성능 목표**:
- P95 평가 시간: 50ms 이내
- 처리량: 1,000 TPS
"""

import logging
import os
from fastapi import APIRouter, HTTPException, Header, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    get_db,
    get_redis,
    Transaction,
    DeviceType,
    RiskLevel,
    EvaluationStatus,
)
from ..models.schemas import (
    FDSEvaluationRequest,
    FDSEvaluationResponse,
    FDSErrorResponse,
)
from ..engines.integrated_evaluation_engine import IntegratedEvaluationEngine
from ..services.review_queue_service import ReviewQueueService

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/v1/fds", tags=["FDS Integrated Evaluation"])


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
    # TODO: 실제 JWT 검증 구현 (T111에서 처리)
    # 현재는 임시로 하드코딩된 토큰 사용 (개발용)
    VALID_TOKEN = os.getenv("FDS_SERVICE_TOKEN", "dev-service-token-12345")

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
    summary="[통합] 거래 위험도 평가",
    description="""
    통합 FDS 엔진으로 거래를 평가하고 종합 위험 점수를 산정합니다.

    **통합 평가 엔진**:
    1. 디바이스 핑거프린팅 (블랙리스트 체크, 타임존/언어 불일치)
    2. 행동 패턴 분석 (봇 탐지: 마우스, 키보드, 클릭스트림)
    3. 네트워크 분석 (TOR/VPN/Proxy 탐지, GeoIP 불일치)
    4. 룰 기반 평가 (30개 실전 사기 탐지 룰)
    5. ML 모델 평가 (앙상블: Random Forest, XGBoost, Autoencoder, LSTM)

    **인증**: X-Service-Token 헤더 필요

    **응답 시간 SLA**: P95 < 50ms

    **의사결정**:
    - `approve` (위험 점수 0-30): 자동 승인
    - `additional_auth_required` (위험 점수 31-70): 추가 인증 필요
    - `blocked` (위험 점수 71-100): 자동 차단

    **성능 지표**:
    - 처리량: 1,000 TPS
    - 정확도: 95% 이상
    - 오탐률: 6% 이하
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
            "description": "서버 에러 (Fail-Open 정책 적용)",
            "model": FDSErrorResponse,
        },
    },
)
async def evaluate_transaction_integrated(
    request: FDSEvaluationRequest,
    db: AsyncSession = Depends(get_db),
    token_valid: bool = Depends(verify_service_token),
) -> FDSEvaluationResponse:
    """
    통합 FDS 평가 엔진으로 거래를 종합 평가합니다.

    Args:
        request: FDS 평가 요청
        db: 데이터베이스 세션
        token_valid: 서비스 토큰 검증 결과

    Returns:
        FDSEvaluationResponse: 종합 평가 결과

    Raises:
        HTTPException: 평가 중 에러 발생 시 (Fail-Open 정책)
    """
    try:
        logger.info(
            f"[INTEGRATED] FDS 평가 시작: transaction_id={request.transaction_id}, "
            f"user_id={request.user_id}, amount={request.amount}"
        )

        # 1. Redis 클라이언트 가져오기
        redis = await get_redis()

        # 2. 통합 평가 엔진 초기화
        ml_model_path = os.getenv("FDS_ML_MODEL_PATH")
        geoip_db_path = os.getenv(
            "GEOIP_DB_PATH", "/usr/share/GeoIP/GeoLite2-City.mmdb"
        )
        asn_db_path = os.getenv("ASN_DB_PATH", "/usr/share/GeoIP/GeoLite2-ASN.mmdb")

        # 파일 존재 확인 (없으면 None 전달)
        geoip_path = geoip_db_path if os.path.exists(geoip_db_path) else None
        asn_path = asn_db_path if os.path.exists(asn_db_path) else None

        if not geoip_path:
            logger.warning(
                f"GeoIP database not found at {geoip_db_path}. Network analysis will be limited."
            )
        if not asn_path:
            logger.warning(
                f"ASN database not found at {asn_db_path}. ASN reputation check will be skipped."
            )

        engine = IntegratedEvaluationEngine(
            db=db,
            redis=redis,
            ml_model_path=ml_model_path,
            geoip_db_path=geoip_path,
            asn_db_path=asn_path,
        )

        # 3. 통합 평가 수행
        evaluation_result = await engine.evaluate(request)

        # 4. 평가 결과를 데이터베이스에 저장
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
                # GeoIP 정보는 Network Analysis Engine에서 수집
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

        # 5. 고위험 거래(BLOCKED)는 자동으로 검토 큐에 추가
        if evaluation_result.decision.value == "blocked":
            try:
                review_queue_service = ReviewQueueService(db)
                review_queue = await review_queue_service.add_to_review_queue(
                    transaction.id
                )

                if review_queue:
                    # 검토 큐 ID를 응답에 포함
                    evaluation_result.recommended_action.review_queue_id = str(
                        review_queue.id
                    )

                    logger.info(
                        f"[INTEGRATED] 고위험 거래를 검토 큐에 추가: "
                        f"transaction_id={transaction.id}, "
                        f"queue_id={review_queue.id}, "
                        f"risk_score={evaluation_result.risk_score}"
                    )
            except Exception as e:
                # 검토 큐 추가 실패 시 로그만 남기고 계속 진행 (fail-safe)
                logger.error(
                    f"[INTEGRATED] 검토 큐 추가 실패: "
                    f"transaction_id={transaction.id}, error={str(e)}",
                    exc_info=True,
                )

        # 6. 성능 로그 (P95 50ms 목표)
        evaluation_time = evaluation_result.evaluation_metadata.evaluation_time_ms
        if evaluation_time > 50:
            logger.warning(
                f"[PERFORMANCE] FDS 평가 시간이 목표(50ms)를 초과: "
                f"{evaluation_time}ms - transaction_id={request.transaction_id}"
            )

        logger.info(
            f"[INTEGRATED] FDS 평가 완료: "
            f"transaction_id={request.transaction_id}, "
            f"risk_score={evaluation_result.risk_score}, "
            f"decision={evaluation_result.decision}, "
            f"evaluation_time={evaluation_time}ms, "
            f"risk_factors_count={len(evaluation_result.risk_factors)}"
        )

        return evaluation_result

    except HTTPException:
        # HTTPException은 그대로 전달 (인증 실패 등)
        raise

    except Exception as e:
        logger.error(
            f"[INTEGRATED] FDS 평가 에러: "
            f"transaction_id={request.transaction_id}, error={str(e)}",
            exc_info=True,
        )

        # Fail-Open 정책: 에러 발생 시 거래 승인 (사후 검토)
        # 실시간 거래 중단을 방지하고 고객 경험 보호
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "FDS_EVALUATION_ERROR",
                "message": "FDS 평가 중 에러가 발생했습니다",
                "details": {
                    "fallback_strategy": "fail_open",
                    "action": "approve_with_review",
                    "reason": "FDS 장애 시 거래 중단 방지, 사후 검토 큐에 추가",
                    "transaction_id": str(request.transaction_id),
                },
            },
        )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="[통합] 헬스 체크",
    description="통합 FDS 서비스의 헬스 상태를 확인합니다.",
)
async def health_check_integrated() -> dict:
    """
    통합 FDS 서비스 헬스 체크

    Returns:
        dict: 헬스 상태 및 통합 엔진 정보
    """
    return {
        "status": "healthy",
        "service": "fds-integrated",
        "version": "2.0.0",
        "engines": {
            "fingerprint": "enabled",
            "behavior_analysis": "enabled",
            "network_analysis": "enabled (if GeoIP DB available)",
            "fraud_rules": "enabled (30 rules)",
            "ml_ensemble": "enabled (if model available)",
        },
        "performance_target": {
            "p95_latency_ms": 50,
            "throughput_tps": 1000,
        },
    }


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="[통합] 평가 메트릭",
    description="FDS 평가 성능 및 통계 메트릭을 조회합니다.",
)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    FDS 평가 메트릭 조회

    Args:
        db: 데이터베이스 세션

    Returns:
        dict: 평가 메트릭 (평균 평가 시간, 위험 수준별 분포 등)
    """
    try:
        from sqlalchemy import func, select

        # 최근 1시간 거래 통계
        one_hour_ago = func.now() - func.text("INTERVAL '1 hour'")

        # 평균 평가 시간
        avg_time_query = select(func.avg(Transaction.evaluation_time_ms)).where(
            Transaction.evaluated_at >= one_hour_ago
        )
        avg_time_result = await db.execute(avg_time_query)
        avg_evaluation_time_ms = avg_time_result.scalar() or 0

        # 위험 수준별 분포
        risk_distribution_query = (
            select(
                Transaction.risk_level,
                func.count(Transaction.id),
            )
            .where(Transaction.evaluated_at >= one_hour_ago)
            .group_by(Transaction.risk_level)
        )

        risk_distribution_result = await db.execute(risk_distribution_query)
        risk_distribution = {
            str(level): count for level, count in risk_distribution_result.all()
        }

        # 의사결정별 분포
        decision_distribution_query = (
            select(
                Transaction.evaluation_status,
                func.count(Transaction.id),
            )
            .where(Transaction.evaluated_at >= one_hour_ago)
            .group_by(Transaction.evaluation_status)
        )

        decision_distribution_result = await db.execute(decision_distribution_query)
        decision_distribution = {
            str(status): count for status, count in decision_distribution_result.all()
        }

        return {
            "time_window": "last_1_hour",
            "performance": {
                "avg_evaluation_time_ms": round(avg_evaluation_time_ms, 2),
                "target_p95_ms": 50,
            },
            "risk_distribution": risk_distribution,
            "decision_distribution": decision_distribution,
        }

    except Exception as e:
        logger.error(f"메트릭 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메트릭 조회 중 에러가 발생했습니다",
        )
