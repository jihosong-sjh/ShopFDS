"""
Device Fingerprint API

디바이스 핑거프린팅 수집 및 조회 API
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.device_fingerprint import DeviceFingerprint
from src.utils.cache_utils import (
    get_cached_device_fingerprint,
    cache_device_fingerprint,
)
from sqlalchemy import select


router = APIRouter(prefix="/v1/fds/device-fingerprint", tags=["Device Fingerprint"])


class DeviceFingerprintRequest(BaseModel):
    """디바이스 핑거프린트 수집 요청"""

    canvas_hash: str = Field(..., max_length=64, description="Canvas API 해시")
    webgl_hash: str = Field(..., max_length=64, description="WebGL API 해시")
    audio_hash: str = Field(..., max_length=64, description="Audio API 해시")
    cpu_cores: int = Field(..., ge=0, description="CPU 코어 수")
    memory_size: int = Field(..., ge=0, description="메모리 크기 (MB)")
    screen_resolution: str = Field(
        ..., max_length=20, description='화면 해상도 (예: "1920x1080")'
    )
    timezone: str = Field(..., max_length=50, description='타임존 (예: "Asia/Seoul")')
    language: str = Field(..., max_length=10, description='언어 (예: "ko-KR")')
    user_agent: str = Field(..., description="User-Agent 문자열")


class DeviceFingerprintResponse(BaseModel):
    """디바이스 핑거프린트 응답"""

    device_id: str = Field(..., description="디바이스 ID (SHA-256)")
    is_new: bool = Field(..., description="신규 디바이스 여부")
    blacklisted: bool = Field(..., description="블랙리스트 등록 여부")
    blacklist_reason: Optional[str] = Field(None, description="블랙리스트 사유")
    created_at: datetime = Field(..., description="생성 일시")
    last_seen_at: datetime = Field(..., description="마지막 활동 일시")


class DeviceInfoResponse(BaseModel):
    """디바이스 상세 정보 응답"""

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
    created_at: datetime
    last_seen_at: datetime
    blacklisted: bool
    blacklist_reason: Optional[str]
    updated_at: datetime


@router.post(
    "/collect",
    response_model=DeviceFingerprintResponse,
    status_code=status.HTTP_200_OK,
    summary="디바이스 핑거프린트 수집",
    description="클라이언트에서 수집한 디바이스 핑거프린트를 저장하고 디바이스 ID를 생성합니다.",
)
async def collect_device_fingerprint(
    request: DeviceFingerprintRequest, db: AsyncSession = Depends(get_db)
):
    """
    디바이스 핑거프린트 수집

    1. 디바이스 ID 생성 (SHA-256 해시)
    2. 기존 디바이스 조회
    3. 신규 디바이스면 생성, 기존 디바이스면 last_seen_at 업데이트
    4. 블랙리스트 여부 반환
    """
    import hashlib

    # 디바이스 ID 생성 (클라이언트와 동일한 알고리즘)
    components = [
        request.canvas_hash,
        request.webgl_hash,
        request.audio_hash,
        str(request.cpu_cores),
        request.screen_resolution,
        request.timezone,
        request.language,
    ]
    combined = "|".join(components)
    device_id = hashlib.sha256(combined.encode()).hexdigest()

    # 기존 디바이스 조회
    result = await db.execute(
        select(DeviceFingerprint).where(DeviceFingerprint.device_id == device_id)
    )
    existing_device = result.scalar_one_or_none()

    is_new = existing_device is None
    now = datetime.utcnow()

    if is_new:
        # 신규 디바이스 생성
        device = DeviceFingerprint(
            device_id=device_id,
            canvas_hash=request.canvas_hash,
            webgl_hash=request.webgl_hash,
            audio_hash=request.audio_hash,
            cpu_cores=request.cpu_cores,
            memory_size=request.memory_size,
            screen_resolution=request.screen_resolution,
            timezone=request.timezone,
            language=request.language,
            user_agent=request.user_agent,
            created_at=now,
            last_seen_at=now,
            blacklisted=False,
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
    else:
        # 기존 디바이스 업데이트 (last_seen_at)
        existing_device.last_seen_at = now
        existing_device.user_agent = request.user_agent  # User-Agent 업데이트
        await db.commit()
        await db.refresh(existing_device)
        device = existing_device

    # 디바이스 정보 Redis 캐싱 (TTL 24시간)
    device_data = {
        "device_id": device.device_id,
        "canvas_hash": device.canvas_hash,
        "webgl_hash": device.webgl_hash,
        "audio_hash": device.audio_hash,
        "cpu_cores": device.cpu_cores,
        "memory_size": device.memory_size,
        "screen_resolution": device.screen_resolution,
        "timezone": device.timezone,
        "language": device.language,
        "user_agent": device.user_agent,
        "blacklisted": device.blacklisted,
        "blacklist_reason": device.blacklist_reason,
        "created_at": device.created_at.isoformat(),
        "last_seen_at": device.last_seen_at.isoformat(),
    }
    await cache_device_fingerprint(device_id, device_data)

    return DeviceFingerprintResponse(
        device_id=device.device_id,
        is_new=is_new,
        blacklisted=device.blacklisted,
        blacklist_reason=device.blacklist_reason,
        created_at=device.created_at,
        last_seen_at=device.last_seen_at,
    )


@router.get(
    "/{device_id}",
    response_model=DeviceInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="디바이스 정보 조회",
    description="디바이스 ID로 디바이스 핑거프린트 상세 정보를 조회합니다.",
)
async def get_device_fingerprint(device_id: str, db: AsyncSession = Depends(get_db)):
    """
    디바이스 정보 조회

    디바이스 ID로 핑거프린트 상세 정보를 조회합니다.
    캐시를 우선 확인하고, 없으면 DB에서 조회합니다 (TTL 24시간).
    """
    # Redis 캐시 조회 시도
    cached_data = await get_cached_device_fingerprint(device_id)
    if cached_data:
        # 캐시 히트: 캐시 데이터를 파싱하여 반환
        return DeviceInfoResponse(
            device_id=cached_data["device_id"],
            canvas_hash=cached_data["canvas_hash"],
            webgl_hash=cached_data["webgl_hash"],
            audio_hash=cached_data["audio_hash"],
            cpu_cores=cached_data["cpu_cores"],
            memory_size=cached_data["memory_size"],
            screen_resolution=cached_data["screen_resolution"],
            timezone=cached_data["timezone"],
            language=cached_data["language"],
            user_agent=cached_data["user_agent"],
            created_at=datetime.fromisoformat(cached_data["created_at"]),
            last_seen_at=datetime.fromisoformat(cached_data["last_seen_at"]),
            blacklisted=cached_data["blacklisted"],
            blacklist_reason=cached_data.get("blacklist_reason"),
            updated_at=datetime.fromisoformat(
                cached_data.get("updated_at", cached_data["last_seen_at"])
            ),
        )

    # 캐시 미스: DB에서 조회
    result = await db.execute(
        select(DeviceFingerprint).where(DeviceFingerprint.device_id == device_id)
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device not found: {device_id}",
        )

    # DB 조회 결과를 캐시에 저장
    device_data = {
        "device_id": device.device_id,
        "canvas_hash": device.canvas_hash,
        "webgl_hash": device.webgl_hash,
        "audio_hash": device.audio_hash,
        "cpu_cores": device.cpu_cores,
        "memory_size": device.memory_size,
        "screen_resolution": device.screen_resolution,
        "timezone": device.timezone,
        "language": device.language,
        "user_agent": device.user_agent,
        "blacklisted": device.blacklisted,
        "blacklist_reason": device.blacklist_reason,
        "created_at": device.created_at.isoformat(),
        "last_seen_at": device.last_seen_at.isoformat(),
        "updated_at": device.updated_at.isoformat(),
    }
    await cache_device_fingerprint(device_id, device_data)

    return DeviceInfoResponse(
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
        created_at=device.created_at,
        last_seen_at=device.last_seen_at,
        blacklisted=device.blacklisted,
        blacklist_reason=device.blacklist_reason,
        updated_at=device.updated_at,
    )
