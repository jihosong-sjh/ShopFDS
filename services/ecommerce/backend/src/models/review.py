"""
리뷰 모델

사용자가 구매한 상품에 대한 리뷰를 관리합니다.
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    Boolean,
    ForeignKey,
    CheckConstraint,
    Uuid,
)
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import relationship
import uuid

from src.models.base import Base, TimestampMixin


class Review(Base, TimestampMixin):
    """
    리뷰 모델

    사용자가 구매한 상품에 대한 리뷰를 저장합니다.
    별점, 제목, 내용, 사진을 포함할 수 있습니다.
    """

    __tablename__ = "reviews"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        Uuid,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id = Column(Uuid, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)

    # 리뷰 내용
    rating = Column(Integer, nullable=False)  # 1-5점
    title = Column(String(200), nullable=True)  # 리뷰 제목 (선택사항)
    content = Column(Text, nullable=False)  # 리뷰 내용 (최소 10자)
    images = Column(JSONB, default=list)  # 사진 URL 배열 (최대 3장)

    # 통계 및 상태
    helpful_count = Column(Integer, default=0)  # "도움돼요" 투표 수
    is_verified_purchase = Column(Boolean, default=False)  # 구매 확정 고객 여부
    is_flagged = Column(Boolean, default=False, index=True)  # 신고 처리 여부
    flagged_reason = Column(String(500), nullable=True)  # 신고 사유

    # Relationships
    user = relationship("User", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")
    order = relationship("Order", back_populates="reviews")
    votes = relationship(
        "ReviewVote", back_populates="review", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
        CheckConstraint("LENGTH(content) >= 10", name="check_content_length"),
        CheckConstraint("helpful_count >= 0", name="check_helpful_count_positive"),
        # UNIQUE constraint on (user_id, product_id) - 사용자당 상품당 하나의 리뷰만
        # SQLite에서는 UNIQUE index로 구현
    )

    def __repr__(self):
        return f"<Review(id={self.id}, user_id={self.user_id}, product_id={self.product_id}, rating={self.rating})>"

    def to_dict(self):
        """딕셔너리로 변환 (API 응답용)"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "product_id": str(self.product_id),
            "order_id": str(self.order_id) if self.order_id else None,
            "rating": self.rating,
            "title": self.title,
            "content": self.content,
            "images": self.images or [],
            "helpful_count": self.helpful_count,
            "is_verified_purchase": self.is_verified_purchase,
            "is_flagged": self.is_flagged,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict_with_user(self):
        """사용자 정보 포함 딕셔너리 변환"""
        data = self.to_dict()
        if self.user:
            data["user"] = {
                "id": str(self.user.id),
                "name": self.user.name,
                "masked_name": self._mask_name(self.user.name),
            }
        return data

    @staticmethod
    def _mask_name(name: str) -> str:
        """
        사용자 이름 마스킹

        예: "홍길동" -> "홍**"
        """
        if not name:
            return ""

        if len(name) <= 1:
            return name

        return name[0] + "*" * (len(name) - 1)
