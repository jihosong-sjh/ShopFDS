"""
사용자(User) 모델

목적: 플랫폼에 가입한 고객 및 관리자 계정
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, ENUM
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(
        ENUM(UserRole, name="user_role_enum", create_type=True),
        nullable=False,
        default=UserRole.CUSTOMER
    )
    status = Column(
        ENUM(UserStatus, name="user_status_enum", create_type=True),
        nullable=False,
        default=UserStatus.ACTIVE,
        index=True
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, default=0)

    # 관계
    orders = relationship("Order", back_populates="user", lazy="dynamic")
    cart = relationship("Cart", back_populates="user", uselist=False)

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
