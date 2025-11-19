"""
사용자 쿠폰(UserCoupon) 모델

목적: 사용자가 보유한 쿠폰 및 사용 이력
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    ForeignKey,
    DateTime,
    Index,
    CheckConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class UserCoupon(Base):
    """사용자 쿠폰 모델"""

    __tablename__ = "user_coupons"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    coupon_id = Column(
        Uuid, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False
    )
    order_id = Column(
        Uuid, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    issued_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)

    # 제약 조건
    __table_args__ = (
        CheckConstraint(
            "used_at IS NULL OR used_at >= issued_at",
            name="check_used_after_issued",
        ),
        Index("idx_user_coupons_user", "user_id", "used_at"),
        Index("idx_user_coupons_coupon", "coupon_id"),
        Index("idx_user_coupons_order", "order_id"),
    )

    # Relationships
    user = relationship("User", back_populates="user_coupons")
    coupon = relationship("Coupon", back_populates="user_coupons")
    order = relationship("Order", back_populates="user_coupon", uselist=False)

    def __repr__(self):
        return f"<UserCoupon(id={self.id}, user_id={self.user_id}, coupon_id={self.coupon_id})>"

    def is_used(self) -> bool:
        """쿠폰 사용 여부 확인"""
        return self.used_at is not None

    def is_available(self) -> bool:
        """쿠폰 사용 가능 여부 확인 (미사용 상태)"""
        return self.used_at is None

    def mark_as_used(self, order_id: uuid.UUID):
        """
        쿠폰을 사용 상태로 표시

        Args:
            order_id: 주문 ID
        """
        self.used_at = datetime.utcnow()
        self.order_id = order_id

    def restore(self):
        """
        쿠폰 복구 (주문 취소 시)
        """
        self.used_at = None
        self.order_id = None
