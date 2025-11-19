"""
쿠폰(Coupon) 모델

목적: 할인 쿠폰 마스터 데이터
"""

from datetime import datetime
from enum import Enum
from decimal import Decimal
from sqlalchemy import (
    Column,
    String,
    Text,
    DECIMAL,
    Integer,
    DateTime,
    Boolean,
    Index,
    CheckConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class DiscountType(str, Enum):
    """할인 유형"""

    FIXED = "FIXED"  # 정액 할인 (예: 5,000원)
    PERCENT = "PERCENT"  # 정률 할인 (예: 10%)


class Coupon(Base):
    """쿠폰 모델"""

    __tablename__ = "coupons"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    coupon_code = Column(String(50), nullable=False, unique=True, index=True)
    coupon_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    discount_type = Column(String(20), nullable=False)
    discount_value = Column(DECIMAL(10, 2), nullable=False)
    max_discount_amount = Column(DECIMAL(10, 2), nullable=True)
    min_purchase_amount = Column(DECIMAL(10, 2), nullable=False, default=0)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    max_usage_count = Column(Integer, nullable=True)
    max_usage_per_user = Column(Integer, nullable=False, default=1)
    current_usage_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 제약 조건
    __table_args__ = (
        CheckConstraint("discount_value > 0", name="check_discount_value_positive"),
        CheckConstraint(
            "valid_until > valid_from", name="check_valid_date_range"
        ),
        CheckConstraint(
            "min_purchase_amount >= 0", name="check_min_purchase_non_negative"
        ),
        CheckConstraint(
            "current_usage_count >= 0", name="check_current_usage_non_negative"
        ),
        CheckConstraint(
            "discount_type IN ('FIXED', 'PERCENT')",
            name="check_discount_type",
        ),
        Index("idx_coupons_code", "coupon_code"),
        Index("idx_coupons_active", "is_active"),
        Index("idx_coupons_valid_dates", "valid_from", "valid_until"),
    )

    # Relationships
    user_coupons = relationship(
        "UserCoupon", back_populates="coupon", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Coupon(id={self.id}, code={self.coupon_code}, name={self.coupon_name})>"

    def is_valid(self) -> bool:
        """쿠폰이 현재 유효한지 확인"""
        now = datetime.utcnow()
        return (
            self.is_active
            and self.valid_from <= now <= self.valid_until
            and (
                self.max_usage_count is None
                or self.current_usage_count < self.max_usage_count
            )
        )

    def is_expired(self) -> bool:
        """쿠폰이 만료되었는지 확인"""
        return datetime.utcnow() > self.valid_until

    def is_usage_limit_reached(self) -> bool:
        """전체 사용 한도에 도달했는지 확인"""
        if self.max_usage_count is None:
            return False
        return self.current_usage_count >= self.max_usage_count

    def calculate_discount(self, order_amount: Decimal) -> Decimal:
        """
        주문 금액에 대한 할인 금액 계산

        Args:
            order_amount: 주문 금액

        Returns:
            할인 금액
        """
        if self.discount_type == DiscountType.FIXED.value:
            # 정액 할인
            return min(self.discount_value, order_amount)

        elif self.discount_type == DiscountType.PERCENT.value:
            # 정률 할인
            discount = order_amount * (self.discount_value / Decimal("100"))

            # 최대 할인 금액 제한
            if self.max_discount_amount is not None:
                discount = min(discount, self.max_discount_amount)

            return min(discount, order_amount)

        return Decimal("0")

    def can_apply_to_order(self, order_amount: Decimal) -> tuple[bool, str]:
        """
        주문에 쿠폰을 적용할 수 있는지 확인

        Args:
            order_amount: 주문 금액

        Returns:
            (적용 가능 여부, 불가능한 경우 사유)
        """
        if not self.is_active:
            return False, "비활성화된 쿠폰입니다"

        if self.is_expired():
            return False, "만료된 쿠폰입니다"

        if self.is_usage_limit_reached():
            return False, "쿠폰 사용 횟수가 초과되었습니다"

        now = datetime.utcnow()
        if now < self.valid_from:
            return False, "쿠폰 사용 기간이 아닙니다"

        if order_amount < self.min_purchase_amount:
            return (
                False,
                f"최소 구매 금액({self.min_purchase_amount}원)을 충족하지 않습니다",
            )

        return True, ""

    def increment_usage_count(self):
        """사용 횟수 증가"""
        self.current_usage_count += 1

    def decrement_usage_count(self):
        """사용 횟수 감소 (주문 취소 시)"""
        if self.current_usage_count > 0:
            self.current_usage_count -= 1
