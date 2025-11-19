"""
푸시 알림 구독 모델

PWA 푸시 알림 구독 정보를 저장합니다.
Firebase Cloud Messaging (FCM) 기반 푸시 알림을 위한 구독 관리.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class PushSubscription(Base):
    """푸시 알림 구독 모델"""

    __tablename__ = "push_subscriptions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    endpoint = Column(Text, nullable=False, unique=True)  # FCM endpoint URL
    p256dh_key = Column(Text, nullable=False)  # Public key for encryption
    auth_key = Column(Text, nullable=False)  # Authentication secret
    device_type = Column(String(50), nullable=True)  # android, ios, web
    user_agent = Column(Text, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    last_used_at = Column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="push_subscriptions")

    __table_args__ = (
        Index("idx_push_subscriptions_user", "user_id"),
        Index("idx_push_subscriptions_endpoint", "endpoint"),
    )

    def __repr__(self):
        return f"<PushSubscription(id={self.id}, user_id={self.user_id}, device_type={self.device_type})>"
