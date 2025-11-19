"""
리뷰 투표 모델

사용자가 리뷰에 "도움돼요" 투표한 이력을 관리합니다.
"""

from sqlalchemy import Column, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base, TimestampMixin


class ReviewVote(Base, TimestampMixin):
    """
    리뷰 투표 모델

    사용자가 리뷰에 "도움돼요" 투표한 이력을 저장합니다.
    중복 투표를 방지하기 위해 (review_id, user_id) 복합 기본 키를 사용합니다.
    """

    __tablename__ = "review_votes"

    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    review = relationship("Review", back_populates="votes")
    user = relationship("User", back_populates="review_votes")

    # Composite primary key: (review_id, user_id)
    __table_args__ = (
        PrimaryKeyConstraint("review_id", "user_id", name="pk_review_votes"),
    )

    def __repr__(self):
        return f"<ReviewVote(review_id={self.review_id}, user_id={self.user_id})>"

    def to_dict(self):
        """딕셔너리로 변환 (API 응답용)"""
        return {
            "review_id": str(self.review_id),
            "user_id": str(self.user_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
