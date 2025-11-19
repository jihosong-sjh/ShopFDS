"""
WishlistItem Model

사용자의 찜한 상품(위시리스트) 정보를 저장하는 모델
"""

from sqlalchemy import Column, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.models.base import Base


class WishlistItem(Base):
    """
    WishlistItem 모델

    사용자가 찜한 상품 목록을 저장합니다.
    - 로그인 사용자만 위시리스트 사용 가능
    - 동일 상품 중복 추가 불가 (UNIQUE 제약)
    - 상품 삭제 시 위시리스트에서도 자동 삭제 (CASCADE)
    """

    __tablename__ = "wishlist_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, comment="찜한 날짜"
    )

    # Relationships
    user = relationship("User", back_populates="wishlist_items")
    product = relationship("Product")

    # Unique constraint: 사용자당 상품당 하나의 위시리스트 항목만 허용
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_user_product_wishlist"),
        {"comment": "사용자 위시리스트 (찜한 상품)"},
    )

    def __repr__(self):
        return f"<WishlistItem(id={self.id}, user_id={self.user_id}, product_id={self.product_id})>"
