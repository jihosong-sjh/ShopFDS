"""
푸시 알림 API 엔드포인트

PWA 푸시 알림 구독/해지 및 알림 전송 API를 제공합니다.
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.middleware.auth import get_current_user
from src.models.user import User
from src.services.push_notification_service import (
    get_push_notification_service,
)
from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/push", tags=["push"])


# Pydantic 모델
class PushSubscriptionRequest(BaseModel):
    """푸시 구독 요청"""

    endpoint: str = Field(..., description="FCM endpoint URL")
    keys: dict = Field(..., description="Encryption keys (p256dh, auth)")

    class Config:
        json_schema_extra = {
            "example": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/...",
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls...",
                    "auth": "tBHItJI5svbpez7KI4CCXg==",
                },
            }
        }


class PushSubscriptionResponse(BaseModel):
    """푸시 구독 응답"""

    id: str
    subscribed_at: datetime

    class Config:
        from_attributes = True


class PushNotificationRequest(BaseModel):
    """푸시 알림 전송 요청 (테스트용)"""

    title: str = Field(..., description="알림 제목")
    body: str = Field(..., description="알림 내용")
    data: Optional[dict] = Field(None, description="추가 데이터")
    icon: Optional[str] = Field(None, description="아이콘 URL")
    tag: Optional[str] = Field(None, description="알림 태그")


class PushNotificationResponse(BaseModel):
    """푸시 알림 전송 응답"""

    success: int
    failed: int
    message: str


@router.post(
    "/subscribe",
    response_model=PushSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="푸시 알림 구독 등록",
    description="PWA 푸시 알림 구독 정보를 등록합니다. Web Push API의 subscription 객체를 전달합니다.",
)
async def subscribe_push_notification(
    request: PushSubscriptionRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    푸시 알림 구독 등록

    - endpoint: FCM endpoint URL
    - keys.p256dh: Public key for encryption
    - keys.auth: Authentication secret
    """
    try:
        # User-Agent 추출
        user_agent = http_request.headers.get("User-Agent", "")

        # 기기 타입 추론 (간단한 로직)
        device_type = "web"
        if "Android" in user_agent:
            device_type = "android"
        elif "iPhone" or "iPad" in user_agent:
            device_type = "ios"

        # 서비스 인스턴스 생성
        push_service = await get_push_notification_service(db_session)

        # 구독 등록
        subscription = await push_service.subscribe(
            user_id=current_user.id,
            endpoint=request.endpoint,
            p256dh_key=request.keys.get("p256dh", ""),
            auth_key=request.keys.get("auth", ""),
            device_type=device_type,
            user_agent=user_agent,
        )

        logger.info(f"[OK] User {current_user.id} subscribed to push notifications")

        return PushSubscriptionResponse(
            id=str(subscription.id), subscribed_at=subscription.created_at
        )

    except Exception as e:
        logger.error(f"[FAIL] Failed to subscribe push notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to subscribe push notification",
        )


@router.delete(
    "/unsubscribe",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="푸시 알림 구독 해지",
    description="현재 사용자의 모든 푸시 알림 구독을 해지합니다.",
)
async def unsubscribe_push_notification(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    푸시 알림 구독 해지

    현재 사용자의 모든 푸시 구독을 삭제합니다.
    """
    try:
        push_service = await get_push_notification_service(db_session)
        deleted_count = await push_service.unsubscribe(user_id=current_user.id)

        logger.info(
            f"[OK] User {current_user.id} unsubscribed from push notifications (deleted {deleted_count} subscriptions)"
        )

        return None  # 204 No Content

    except Exception as e:
        logger.error(f"[FAIL] Failed to unsubscribe push notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe push notification",
        )


@router.post(
    "/test",
    response_model=PushNotificationResponse,
    summary="테스트 푸시 알림 전송 (개발용)",
    description="현재 사용자에게 테스트 푸시 알림을 전송합니다. 개발/디버깅 용도입니다.",
)
async def send_test_push_notification(
    request: PushNotificationRequest,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    테스트 푸시 알림 전송

    - 개발/디버깅 용도
    - 프로덕션 환경에서는 비활성화 권장
    """
    try:
        push_service = await get_push_notification_service(db_session)

        result = await push_service.send_notification(
            user_id=current_user.id,
            title=request.title,
            body=request.body,
            data=request.data,
            icon=request.icon,
            tag=request.tag,
        )

        message = f"Sent {result['success']} notifications, {result['failed']} failed"
        logger.info(
            f"[OK] Test push notification sent to user {current_user.id}: {message}"
        )

        return PushNotificationResponse(
            success=result["success"], failed=result["failed"], message=message
        )

    except Exception as e:
        logger.error(f"[FAIL] Failed to send test push notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test push notification",
        )
