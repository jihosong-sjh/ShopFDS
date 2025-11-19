"""
사용자(User) 모델

목적: 플랫폼에 가입한 고객 및 관리자 계정
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Integer, Uuid, CheckConstraint
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class UserRole(str, Enum):
    """사용자 역할"""

    CUSTOMER = "customer"
    ADMIN = "admin"
    SECURITY_TEAM = "security_team"


class UserStatus(str, Enum):
    """계정 상태"""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(Base):
    """사용자 모델"""

    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(
        String(50),
        nullable=False,
        default=UserRole.CUSTOMER.value,
    )
    status = Column(
        String(50),
        nullable=False,
        default=UserStatus.ACTIVE.value,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint(
            "role IN ('customer', 'admin', 'security_team')", name="check_user_role"
        ),
        CheckConstraint(
            "status IN ('active', 'suspended', 'deleted')", name="check_user_status"
        ),
    )

    # 관계
    orders = relationship("Order", back_populates="user", lazy="dynamic")
    cart = relationship("Cart", back_populates="user", uselist=False)
    reviews = relationship("Review", back_populates="user", lazy="dynamic")
    review_votes = relationship("ReviewVote", back_populates="user", lazy="dynamic")
    user_coupons = relationship("UserCoupon", back_populates="user", lazy="dynamic")
    oauth_accounts = relationship("OAuthAccount", back_populates="user", lazy="dynamic")
    wishlist_items = relationship("WishlistItem", back_populates="user", lazy="dynamic")
    addresses = relationship("Address", back_populates="user", lazy="dynamic")
    push_subscriptions = relationship(
        "PushSubscription", back_populates="user", lazy="dynamic"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    def is_locked(self) -> bool:
        """계정이 잠겼는지 확인 (3회 초과 로그인 실패)"""
        return self.failed_login_attempts >= 3

    def reset_failed_attempts(self):
        """로그인 실패 횟수 초기화"""
        self.failed_login_attempts = 0

    def increment_failed_attempts(self):
        """로그인 실패 횟수 증가"""
        self.failed_login_attempts += 1
