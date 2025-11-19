"""
배송지(Address) 모델

목적: 사용자의 여러 배송지 주소 저장 및 관리
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Uuid, ForeignKey, Index
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class Address(Base):
    """배송지 모델"""

    __tablename__ = "addresses"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    address_name = Column(String(100), nullable=False)  # 예: "집", "회사"
    recipient_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    zipcode = Column(String(10), nullable=False)
    address = Column(String(500), nullable=False)
    address_detail = Column(String(500), nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="addresses")

    __table_args__ = (
        # Composite index: 사용자별 배송지 조회 (기본 배송지 우선)
        Index("idx_addresses_user", "user_id", "is_default", "created_at"),
        # Note: Partial unique index for is_default is handled at application level
        # PostgreSQL: CREATE UNIQUE INDEX idx_addresses_user_default ON addresses(user_id) WHERE is_default = true;
    )

    def __repr__(self):
        return f"<Address(id={self.id}, user_id={self.user_id}, name={self.address_name}, is_default={self.is_default})>"
