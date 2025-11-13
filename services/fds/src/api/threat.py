"""
위협 정보 관리 API (Threat Intelligence API)

자체 블랙리스트 관리 및 CTI 조회 API
"""

import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ..models import get_db
from ..models.threat_intelligence import (
    ThreatIntelligence,
    ThreatType,
    ThreatLevel,
    ThreatSource,
)
from ..engines.cti_connector import CTIConnector
from ..utils.redis_client import get_redis

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/internal/fds", tags=["Threat Intelligence"])


# === Pydantic 스키마 ===


class ThreatIntelligenceCreate(BaseModel):
    """위협 정보 생성 요청"""

    threat_type: ThreatType = Field(..., description="위협 유형 (IP, 이메일 도메인, 카드 BIN)")
    value: str = Field(..., description="위협 값 (예: 192.168.1.1)")
    threat_level: ThreatLevel = Field(..., description="위협 수준 (low, medium, high)")
    source: ThreatSource = Field(
        default=ThreatSource.INTERNAL, description="출처 (기본값: internal)"
    )
    description: Optional[str] = Field(None, description="위협 설명")
    expires_at: Optional[datetime] = Field(None, description="만료 일시 (NULL이면 영구)")
    metadata: Optional[dict] = Field(None, description="추가 메타데이터")


class ThreatIntelligenceUpdate(BaseModel):
    """위협 정보 수정 요청"""

    threat_level: Optional[ThreatLevel] = Field(None, description="위협 수준")
    description: Optional[str] = Field(None, description="위협 설명")
    expires_at: Optional[datetime] = Field(None, description="만료 일시")
    is_active: Optional[bool] = Field(None, description="활성화 여부")
    metadata: Optional[dict] = Field(None, description="추가 메타데이터")


class ThreatIntelligenceResponse(BaseModel):
    """위협 정보 응답"""

    id: UUID
    threat_type: ThreatType
    value: str
    threat_level: ThreatLevel
    source: ThreatSource
    description: Optional[str]
    registered_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    is_expired: bool
    metadata: Optional[dict]
    times_blocked: int
    last_blocked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ThreatCheckRequest(BaseModel):
    """위협 확인 요청"""

    threat_type: ThreatType = Field(..., description="위협 유형")
    value: str = Field(..., description="확인할 값 (예: IP 주소)")


class ThreatCheckResponse(BaseModel):
    """위협 확인 응답"""

    threat_type: str
    value: str
    is_threat: bool
    threat_level: Optional[str]
    source: Optional[str]
    confidence_score: int
    description: Optional[str]
    metadata: dict


# === API 엔드포인트 ===


@router.post(
    "/blacklist",
    response_model=ThreatIntelligenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="블랙리스트 항목 추가",
    description="""
    자체 블랙리스트에 위협 정보를 추가합니다.

    **사용 예시**:
    - 악성 IP 수동 등록
    - 사기 이메일 도메인 등록
    - 도난 카드 BIN 등록

    **중복 방지**: (threat_type, value) 조합이 고유해야 합니다.
    """,
)
async def create_blacklist_entry(
    entry: ThreatIntelligenceCreate,
    db: AsyncSession = Depends(get_db),
) -> ThreatIntelligenceResponse:
    """
    블랙리스트 항목 추가

    Args:
        entry: 위협 정보 생성 요청
        db: 데이터베이스 세션

    Returns:
        ThreatIntelligenceResponse: 생성된 위협 정보

    Raises:
        HTTPException: 중복 항목 또는 에러 발생 시
    """
    try:
        # 중복 확인
        stmt = select(ThreatIntelligence).where(
            ThreatIntelligence.threat_type == entry.threat_type,
            ThreatIntelligence.value == entry.value,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"이미 등록된 위협 정보입니다: {entry.threat_type.value} - {entry.value}",
            )

        # 새 항목 생성
        threat = ThreatIntelligence(
            threat_type=entry.threat_type,
            value=entry.value,
            threat_level=entry.threat_level,
            source=entry.source,
            description=entry.description,
            expires_at=entry.expires_at,
            metadata=entry.metadata,
        )

        db.add(threat)
        await db.commit()
        await db.refresh(threat)

        logger.info(
            f"블랙리스트 항목 추가: {entry.threat_type.value} - {entry.value} "
            f"(위협 수준: {entry.threat_level.value})"
        )

        return ThreatIntelligenceResponse(
            id=threat.id,
            threat_type=threat.threat_type,
            value=threat.value,
            threat_level=threat.threat_level,
            source=threat.source,
            description=threat.description,
            registered_at=threat.registered_at,
            expires_at=threat.expires_at,
            is_active=threat.is_active,
            is_expired=threat.is_expired,
            metadata=threat.metadata,
            times_blocked=threat.times_blocked,
            last_blocked_at=threat.last_blocked_at,
            created_at=threat.created_at,
            updated_at=threat.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"블랙리스트 항목 추가 에러: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"블랙리스트 항목 추가 중 에러가 발생했습니다: {str(e)}",
        )


@router.get(
    "/blacklist",
    response_model=List[ThreatIntelligenceResponse],
    status_code=status.HTTP_200_OK,
    summary="블랙리스트 목록 조회",
    description="자체 블랙리스트 목록을 조회합니다.",
)
async def get_blacklist(
    threat_type: Optional[ThreatType] = Query(None, description="위협 유형 필터"),
    threat_level: Optional[ThreatLevel] = Query(None, description="위협 수준 필터"),
    is_active: Optional[bool] = Query(None, description="활성화 상태 필터"),
    limit: int = Query(100, ge=1, le=1000, description="최대 조회 개수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    db: AsyncSession = Depends(get_db),
) -> List[ThreatIntelligenceResponse]:
    """
    블랙리스트 목록 조회

    Args:
        threat_type: 위협 유형 필터
        threat_level: 위협 수준 필터
        is_active: 활성화 상태 필터
        limit: 최대 조회 개수
        offset: 오프셋
        db: 데이터베이스 세션

    Returns:
        List[ThreatIntelligenceResponse]: 위협 정보 목록
    """
    try:
        # 쿼리 빌드
        stmt = select(ThreatIntelligence)

        # 필터 적용
        if threat_type:
            stmt = stmt.where(ThreatIntelligence.threat_type == threat_type)
        if threat_level:
            stmt = stmt.where(ThreatIntelligence.threat_level == threat_level)
        if is_active is not None:
            stmt = stmt.where(ThreatIntelligence.is_active == is_active)

        # 정렬 및 페이징
        stmt = (
            stmt.order_by(ThreatIntelligence.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        # 실행
        result = await db.execute(stmt)
        threats = result.scalars().all()

        return [
            ThreatIntelligenceResponse(
                id=threat.id,
                threat_type=threat.threat_type,
                value=threat.value,
                threat_level=threat.threat_level,
                source=threat.source,
                description=threat.description,
                registered_at=threat.registered_at,
                expires_at=threat.expires_at,
                is_active=threat.is_active,
                is_expired=threat.is_expired,
                metadata=threat.metadata,
                times_blocked=threat.times_blocked,
                last_blocked_at=threat.last_blocked_at,
                created_at=threat.created_at,
                updated_at=threat.updated_at,
            )
            for threat in threats
        ]

    except Exception as e:
        logger.error(f"블랙리스트 목록 조회 에러: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"블랙리스트 목록 조회 중 에러가 발생했습니다: {str(e)}",
        )


@router.get(
    "/blacklist/{threat_id}",
    response_model=ThreatIntelligenceResponse,
    status_code=status.HTTP_200_OK,
    summary="블랙리스트 항목 상세 조회",
    description="특정 블랙리스트 항목의 상세 정보를 조회합니다.",
)
async def get_blacklist_entry(
    threat_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ThreatIntelligenceResponse:
    """
    블랙리스트 항목 상세 조회

    Args:
        threat_id: 위협 정보 ID
        db: 데이터베이스 세션

    Returns:
        ThreatIntelligenceResponse: 위협 정보

    Raises:
        HTTPException: 항목을 찾을 수 없는 경우
    """
    try:
        stmt = select(ThreatIntelligence).where(ThreatIntelligence.id == threat_id)
        result = await db.execute(stmt)
        threat = result.scalar_one_or_none()

        if not threat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"블랙리스트 항목을 찾을 수 없습니다: {threat_id}",
            )

        return ThreatIntelligenceResponse(
            id=threat.id,
            threat_type=threat.threat_type,
            value=threat.value,
            threat_level=threat.threat_level,
            source=threat.source,
            description=threat.description,
            registered_at=threat.registered_at,
            expires_at=threat.expires_at,
            is_active=threat.is_active,
            is_expired=threat.is_expired,
            metadata=threat.metadata,
            times_blocked=threat.times_blocked,
            last_blocked_at=threat.last_blocked_at,
            created_at=threat.created_at,
            updated_at=threat.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"블랙리스트 항목 조회 에러: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"블랙리스트 항목 조회 중 에러가 발생했습니다: {str(e)}",
        )


@router.patch(
    "/blacklist/{threat_id}",
    response_model=ThreatIntelligenceResponse,
    status_code=status.HTTP_200_OK,
    summary="블랙리스트 항목 수정",
    description="블랙리스트 항목의 정보를 수정합니다.",
)
async def update_blacklist_entry(
    threat_id: UUID,
    update: ThreatIntelligenceUpdate,
    db: AsyncSession = Depends(get_db),
) -> ThreatIntelligenceResponse:
    """
    블랙리스트 항목 수정

    Args:
        threat_id: 위협 정보 ID
        update: 수정할 정보
        db: 데이터베이스 세션

    Returns:
        ThreatIntelligenceResponse: 수정된 위협 정보

    Raises:
        HTTPException: 항목을 찾을 수 없는 경우
    """
    try:
        stmt = select(ThreatIntelligence).where(ThreatIntelligence.id == threat_id)
        result = await db.execute(stmt)
        threat = result.scalar_one_or_none()

        if not threat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"블랙리스트 항목을 찾을 수 없습니다: {threat_id}",
            )

        # 필드 업데이트
        if update.threat_level is not None:
            threat.threat_level = update.threat_level
        if update.description is not None:
            threat.description = update.description
        if update.expires_at is not None:
            threat.expires_at = update.expires_at
        if update.is_active is not None:
            threat.is_active = update.is_active
        if update.metadata is not None:
            threat.metadata = update.metadata

        await db.commit()
        await db.refresh(threat)

        logger.info(f"블랙리스트 항목 수정: {threat_id}")

        return ThreatIntelligenceResponse(
            id=threat.id,
            threat_type=threat.threat_type,
            value=threat.value,
            threat_level=threat.threat_level,
            source=threat.source,
            description=threat.description,
            registered_at=threat.registered_at,
            expires_at=threat.expires_at,
            is_active=threat.is_active,
            is_expired=threat.is_expired,
            metadata=threat.metadata,
            times_blocked=threat.times_blocked,
            last_blocked_at=threat.last_blocked_at,
            created_at=threat.created_at,
            updated_at=threat.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"블랙리스트 항목 수정 에러: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"블랙리스트 항목 수정 중 에러가 발생했습니다: {str(e)}",
        )


@router.delete(
    "/blacklist/{threat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="블랙리스트 항목 삭제",
    description="블랙리스트 항목을 삭제합니다. (또는 비활성화)",
)
async def delete_blacklist_entry(
    threat_id: UUID,
    hard_delete: bool = Query(False, description="완전 삭제 여부 (기본값: 비활성화)"),
    db: AsyncSession = Depends(get_db),
):
    """
    블랙리스트 항목 삭제

    Args:
        threat_id: 위협 정보 ID
        hard_delete: 완전 삭제 여부 (False: 비활성화만)
        db: 데이터베이스 세션

    Raises:
        HTTPException: 항목을 찾을 수 없는 경우
    """
    try:
        stmt = select(ThreatIntelligence).where(ThreatIntelligence.id == threat_id)
        result = await db.execute(stmt)
        threat = result.scalar_one_or_none()

        if not threat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"블랙리스트 항목을 찾을 수 없습니다: {threat_id}",
            )

        if hard_delete:
            # 완전 삭제
            await db.delete(threat)
            logger.info(f"블랙리스트 항목 삭제 (hard delete): {threat_id}")
        else:
            # 비활성화만
            threat.is_active = False
            logger.info(f"블랙리스트 항목 비활성화: {threat_id}")

        await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"블랙리스트 항목 삭제 에러: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"블랙리스트 항목 삭제 중 에러가 발생했습니다: {str(e)}",
        )


@router.post(
    "/check-threat",
    response_model=ThreatCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="위협 정보 확인",
    description="""
    특정 값(IP, 이메일 도메인 등)의 위협 여부를 확인합니다.

    **조회 순서**:
    1. Redis 캐시 확인
    2. 자체 블랙리스트 확인
    3. 외부 CTI 소스 조회 (IP의 경우 AbuseIPDB)

    **성능**: 타임아웃 50ms, Redis 캐싱
    """,
)
async def check_threat(
    request: ThreatCheckRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> ThreatCheckResponse:
    """
    위협 정보 확인 (CTI 통합)

    Args:
        request: 위협 확인 요청
        db: 데이터베이스 세션
        redis: Redis 클라이언트

    Returns:
        ThreatCheckResponse: 위협 확인 결과
    """
    try:
        # CTI 커넥터 생성
        cti_connector = CTIConnector(db, redis)

        # 위협 유형에 따라 적절한 메서드 호출
        if request.threat_type == ThreatType.IP:
            result = await cti_connector.check_ip_threat(request.value)
        elif request.threat_type == ThreatType.EMAIL_DOMAIN:
            result = await cti_connector.check_email_domain_threat(request.value)
        elif request.threat_type == ThreatType.CARD_BIN:
            result = await cti_connector.check_card_bin_threat(request.value)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"지원하지 않는 위협 유형입니다: {request.threat_type}",
            )

        # CTI 커넥터 종료
        await cti_connector.close()

        return ThreatCheckResponse(**result.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"위협 정보 확인 에러: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"위협 정보 확인 중 에러가 발생했습니다: {str(e)}",
        )
