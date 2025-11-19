"""
푸시 알림 서비스

Firebase Cloud Messaging (FCM)을 사용하여 푸시 알림을 전송합니다.
PWA 및 모바일 앱에서 사용자에게 실시간 알림을 제공합니다.
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pywebpush import webpush, WebPushException

from src.models.push_subscription import PushSubscription


logger = logging.getLogger(__name__)


class PushNotificationService:
    """푸시 알림 서비스 클래스"""

    def __init__(
        self,
        db_session: AsyncSession,
        vapid_private_key: Optional[str] = None,
        vapid_claims: Optional[Dict[str, str]] = None,
    ):
        """
        Args:
            db_session: 데이터베이스 세션
            vapid_private_key: VAPID 개인 키 (PEM 형식)
            vapid_claims: VAPID claims (subject 필수, 예: {"sub": "mailto:admin@example.com"})
        """
        self.db_session = db_session
        self.vapid_private_key = vapid_private_key
        self.vapid_claims = vapid_claims or {}

    async def subscribe(
        self,
        user_id: UUID,
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
        device_type: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PushSubscription:
        """
        푸시 알림 구독 등록

        Args:
            user_id: 사용자 ID
            endpoint: FCM endpoint URL
            p256dh_key: Public key for encryption
            auth_key: Authentication secret
            device_type: 기기 유형 (android, ios, web)
            user_agent: 브라우저 User Agent

        Returns:
            생성된 PushSubscription 객체

        Raises:
            ValueError: 중복된 endpoint 또는 유효하지 않은 입력
        """
        # 기존 구독 확인 (동일 endpoint)
        existing_subscription = await self.db_session.execute(
            select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        )
        existing = existing_subscription.scalar_one_or_none()

        if existing:
            # 이미 존재하는 경우 업데이트
            existing.p256dh_key = p256dh_key
            existing.auth_key = auth_key
            existing.device_type = device_type
            existing.user_agent = user_agent
            await self.db_session.commit()
            await self.db_session.refresh(existing)
            logger.info(f"[OK] Updated push subscription for user {user_id}")
            return existing

        # 새 구독 생성
        subscription = PushSubscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh_key=p256dh_key,
            auth_key=auth_key,
            device_type=device_type,
            user_agent=user_agent,
        )

        self.db_session.add(subscription)
        await self.db_session.commit()
        await self.db_session.refresh(subscription)

        logger.info(f"[OK] Created push subscription for user {user_id}")
        return subscription

    async def unsubscribe(self, user_id: UUID) -> int:
        """
        사용자의 모든 푸시 알림 구독 해지

        Args:
            user_id: 사용자 ID

        Returns:
            삭제된 구독 수
        """
        result = await self.db_session.execute(
            delete(PushSubscription).where(PushSubscription.user_id == user_id)
        )
        deleted_count = result.rowcount
        await self.db_session.commit()

        logger.info(
            f"[OK] Unsubscribed {deleted_count} push subscriptions for user {user_id}"
        )
        return deleted_count

    async def unsubscribe_by_endpoint(self, endpoint: str) -> bool:
        """
        특정 endpoint의 구독 해지

        Args:
            endpoint: FCM endpoint URL

        Returns:
            삭제 성공 여부
        """
        result = await self.db_session.execute(
            delete(PushSubscription).where(PushSubscription.endpoint == endpoint)
        )
        deleted_count = result.rowcount
        await self.db_session.commit()

        logger.info(f"[OK] Unsubscribed endpoint {endpoint[:50]}...")
        return deleted_count > 0

    async def get_user_subscriptions(self, user_id: UUID) -> List[PushSubscription]:
        """
        사용자의 모든 구독 조회

        Args:
            user_id: 사용자 ID

        Returns:
            PushSubscription 리스트
        """
        result = await self.db_session.execute(
            select(PushSubscription).where(PushSubscription.user_id == user_id)
        )
        return list(result.scalars().all())

    async def send_notification(
        self,
        user_id: UUID,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        icon: Optional[str] = None,
        badge: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        사용자에게 푸시 알림 전송

        Args:
            user_id: 사용자 ID
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터 (JSON serializable)
            icon: 아이콘 URL
            badge: 뱃지 URL
            tag: 알림 태그 (같은 태그는 덮어씀)

        Returns:
            {"success": 성공 수, "failed": 실패 수}
        """
        subscriptions = await self.get_user_subscriptions(user_id)

        if not subscriptions:
            logger.warning(f"[WARN] No push subscriptions found for user {user_id}")
            return {"success": 0, "failed": 0}

        # 푸시 알림 페이로드 구성
        notification_payload = {
            "notification": {
                "title": title,
                "body": body,
                "icon": icon or "/icon-192x192.png",
                "badge": badge or "/badge-72x72.png",
                "tag": tag,
            },
            "data": data or {},
        }

        success_count = 0
        failed_count = 0
        failed_endpoints = []

        for subscription in subscriptions:
            try:
                # Web Push 전송
                subscription_info = {
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh_key,
                        "auth": subscription.auth_key,
                    },
                }

                webpush(
                    subscription_info=subscription_info,
                    data=json.dumps(notification_payload),
                    vapid_private_key=self.vapid_private_key,
                    vapid_claims=self.vapid_claims,
                )

                success_count += 1
                logger.info(
                    f"[OK] Push notification sent to subscription {subscription.id}"
                )

            except WebPushException as e:
                failed_count += 1
                failed_endpoints.append(subscription.endpoint)
                logger.error(
                    f"[FAIL] Failed to send push notification to subscription {subscription.id}: {e}"
                )

                # 410 Gone (구독 만료) 또는 404 Not Found (구독 삭제됨)인 경우 구독 제거
                if e.response and e.response.status_code in [410, 404]:
                    logger.info(f"[OK] Removing expired subscription {subscription.id}")
                    await self.db_session.delete(subscription)

            except Exception as e:
                failed_count += 1
                logger.error(
                    f"[FAIL] Unexpected error sending push notification to subscription {subscription.id}: {e}"
                )

        # 실패한 구독 정리
        if failed_endpoints:
            await self.db_session.commit()

        return {"success": success_count, "failed": failed_count}

    async def send_order_status_notification(
        self, user_id: UUID, order_id: UUID, status: str, order_number: str
    ) -> Dict[str, int]:
        """
        주문 상태 변경 알림 전송

        Args:
            user_id: 사용자 ID
            order_id: 주문 ID
            status: 주문 상태
            order_number: 주문 번호

        Returns:
            {"success": 성공 수, "failed": 실패 수}
        """
        status_messages = {
            "pending": "[ORDER] 주문이 접수되었습니다",
            "confirmed": "[ORDER] 주문이 확인되었습니다",
            "preparing": "[ORDER] 상품을 준비 중입니다",
            "shipped": "[ORDER] 상품이 발송되었습니다",
            "delivered": "[ORDER] 상품이 배송 완료되었습니다",
            "cancelled": "[ORDER] 주문이 취소되었습니다",
        }

        title = status_messages.get(status, "[ORDER] 주문 상태가 변경되었습니다")
        body = f"주문 번호: {order_number}"

        return await self.send_notification(
            user_id=user_id,
            title=title,
            body=body,
            data={
                "type": "order_status",
                "order_id": str(order_id),
                "status": status,
                "url": f"/orders/{order_id}",
            },
            tag=f"order-{order_id}",
        )

    async def send_promotion_notification(
        self, user_id: UUID, title: str, message: str, url: Optional[str] = None
    ) -> Dict[str, int]:
        """
        프로모션 알림 전송

        Args:
            user_id: 사용자 ID
            title: 알림 제목
            message: 알림 메시지
            url: 링크 URL

        Returns:
            {"success": 성공 수, "failed": 실패 수}
        """
        return await self.send_notification(
            user_id=user_id,
            title=f"[PROMO] {title}",
            body=message,
            data={"type": "promotion", "url": url} if url else {"type": "promotion"},
        )


async def get_push_notification_service(
    db_session: AsyncSession,
    vapid_private_key: Optional[str] = None,
    vapid_claims: Optional[Dict[str, str]] = None,
) -> PushNotificationService:
    """푸시 알림 서비스 인스턴스 생성 (의존성 주입용)"""
    return PushNotificationService(db_session, vapid_private_key, vapid_claims)
