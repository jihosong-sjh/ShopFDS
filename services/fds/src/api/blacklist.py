"""
Blacklist API

디바이스 블랙리스트 조회 및 관리 API
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.database import get_db
from src.models.device_fingerprint import DeviceFingerprint
from src.utils.cache_utils import get_cache, CacheKeys


router = APIRouter(prefix="/v1/fds/blacklist", tags=["Blacklist"])


class BlacklistDeviceRequest(BaseModel):
    """디바이스 블랙리스트 등록 요청"""

    device_id: str = Field(..., max_length=64, description="디바이스 ID (SHA-256)")
    reason: str = Field(..., min_length=1, max_length=500, description="블랙리스트 사유")


class BlacklistDeviceResponse(BaseModel):
    """디바이스 블랙리스트 응답"""

    device_id: str
    blacklisted: bool
    blacklist_reason: Optional[str]
    updated_at: datetime


class BlacklistCheckResponse(BaseModel):
    """블랙리스트 확인 응답"""

    device_id: str
    is_blacklisted: bool
    blacklist_reason: Optional[str]
    created_at: Optional[datetime]
    last_seen_at: Optional[datetime]


class BlacklistEntryResponse(BaseModel):
    """블랙리스트 항목 응답"""

    device_id: str
    canvas_hash: str
    webgl_hash: str
    audio_hash: str
    cpu_cores: int
    memory_size: int
    screen_resolution: str
    timezone: str
    language: str
    user_agent: str
    blacklist_reason: str
    created_at: datetime
    last_seen_at: datetime
    updated_at: datetime


class BlacklistStatsResponse(BaseModel):
    """블랙리스트 통계 응답"""

    total_blacklisted: int
    blacklisted_today: int
    blacklisted_this_week: int
    blacklisted_this_month: int


@router.get(
    "/device/{device_id}",
    response_model=BlacklistCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="블랙리스트 조회",
    description="디바이스 ID가 블랙리스트에 등록되어 있는지 확인합니다.",
)
async def check_blacklist(device_id: str, db: AsyncSession = Depends(get_db)):
    """
    블랙리스트 조회

    디바이스 ID로 블랙리스트 등록 여부를 조회합니다.
    """
    result = await db.execute(
        select(DeviceFingerprint).where(DeviceFingerprint.device_id == device_id)
    )
    device = result.scalar_one_or_none()

    if not device:
        # 디바이스가 없으면 블랙리스트에 없음
        return BlacklistCheckResponse(
            device_id=device_id,
            is_blacklisted=False,
            blacklist_reason=None,
            created_at=None,
            last_seen_at=None,
        )

    return BlacklistCheckResponse(
        device_id=device.device_id,
        is_blacklisted=device.blacklisted,
        blacklist_reason=device.blacklist_reason,
        created_at=device.created_at,
        last_seen_at=device.last_seen_at,
    )


@router.post(
    "/device",
    response_model=BlacklistDeviceResponse,
    status_code=status.HTTP_200_OK,
    summary="블랙리스트 등록",
    description="디바이스를 블랙리스트에 등록합니다.",
)
async def add_to_blacklist(
    request: BlacklistDeviceRequest, db: AsyncSession = Depends(get_db)
):
    """
    블랙리스트 등록

    디바이스를 블랙리스트에 등록하고 사유를 기록합니다.
    """
    result = await db.execute(
        select(DeviceFingerprint).where(
            DeviceFingerprint.device_id == request.device_id
        )
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device not found: {request.device_id}",
        )

    if device.blacklisted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device already blacklisted: {request.device_id}",
        )

    # 블랙리스트 등록
    device.blacklisted = True
    device.blacklist_reason = request.reason
    device.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(device)

    # Redis 캐시 무효화 (블랙리스트 상태 변경)
    cache = get_cache()
    cache_key = CacheKeys.device_fingerprint(request.device_id)
    await cache.delete(cache_key)

    return BlacklistDeviceResponse(
        device_id=device.device_id,
        blacklisted=device.blacklisted,
        blacklist_reason=device.blacklist_reason,
        updated_at=device.updated_at,
    )


@router.delete(
    "/device/{device_id}",
    response_model=BlacklistDeviceResponse,
    status_code=status.HTTP_200_OK,
    summary="블랙리스트 해제",
    description="디바이스를 블랙리스트에서 해제합니다.",
)
async def remove_from_blacklist(device_id: str, db: AsyncSession = Depends(get_db)):
    """
    블랙리스트 해제

    디바이스를 블랙리스트에서 제거합니다.
    """
    result = await db.execute(
        select(DeviceFingerprint).where(DeviceFingerprint.device_id == device_id)
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device not found: {device_id}",
        )

    if not device.blacklisted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device is not blacklisted: {device_id}",
        )

    # 블랙리스트 해제
    device.blacklisted = False
    device.blacklist_reason = None
    device.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(device)

    # Redis 캐시 무효화 (블랙리스트 상태 변경)
    cache = get_cache()
    cache_key = CacheKeys.device_fingerprint(device_id)
    await cache.delete(cache_key)

    return BlacklistDeviceResponse(
        device_id=device.device_id,
        blacklisted=device.blacklisted,
        blacklist_reason=device.blacklist_reason,
        updated_at=device.updated_at,
    )


@router.get(
    "/entries",
    response_model=List[BlacklistEntryResponse],
    status_code=status.HTTP_200_OK,
    summary="블랙리스트 목록 조회",
    description="블랙리스트에 등록된 모든 디바이스 목록을 조회합니다.",
)
async def get_blacklist_entries(
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(100, ge=1, le=1000, description="조회할 항목 수"),
    db: AsyncSession = Depends(get_db),
):
    """
    블랙리스트 목록 조회

    블랙리스트에 등록된 모든 디바이스를 페이징하여 조회합니다.
    """
    result = await db.execute(
        select(DeviceFingerprint)
        .where(DeviceFingerprint.blacklisted)
        .order_by(DeviceFingerprint.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    devices = result.scalars().all()

    return [
        BlacklistEntryResponse(
            device_id=device.device_id,
            canvas_hash=device.canvas_hash,
            webgl_hash=device.webgl_hash,
            audio_hash=device.audio_hash,
            cpu_cores=device.cpu_cores,
            memory_size=device.memory_size,
            screen_resolution=device.screen_resolution,
            timezone=device.timezone,
            language=device.language,
            user_agent=device.user_agent,
            blacklist_reason=device.blacklist_reason or "",
            created_at=device.created_at,
            last_seen_at=device.last_seen_at,
            updated_at=device.updated_at,
        )
        for device in devices
    ]


@router.get(
    "/stats",
    response_model=BlacklistStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="블랙리스트 통계",
    description="블랙리스트 등록 통계를 조회합니다.",
)
async def get_blacklist_stats(db: AsyncSession = Depends(get_db)):
    """
    블랙리스트 통계

    블랙리스트 등록 통계를 조회합니다 (총 개수, 오늘, 이번주, 이번달).
    """
    from datetime import timedelta

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 총 블랙리스트 개수
    total_result = await db.execute(
        select(func.count()).where(DeviceFingerprint.blacklisted)
    )
    total_blacklisted = total_result.scalar_one()

    # 오늘 등록된 개수
    today_result = await db.execute(
        select(func.count()).where(
            DeviceFingerprint.blacklisted,
            DeviceFingerprint.updated_at >= today_start,
        )
    )
    blacklisted_today = today_result.scalar_one()

    # 이번주 등록된 개수
    week_result = await db.execute(
        select(func.count()).where(
            DeviceFingerprint.blacklisted,
            DeviceFingerprint.updated_at >= week_start,
        )
    )
    blacklisted_this_week = week_result.scalar_one()

    # 이번달 등록된 개수
    month_result = await db.execute(
        select(func.count()).where(
            DeviceFingerprint.blacklisted,
            DeviceFingerprint.updated_at >= month_start,
        )
    )
    blacklisted_this_month = month_result.scalar_one()

    return BlacklistStatsResponse(
        total_blacklisted=total_blacklisted,
        blacklisted_today=blacklisted_today,
        blacklisted_this_week=blacklisted_this_week,
        blacklisted_this_month=blacklisted_this_month,
    )
