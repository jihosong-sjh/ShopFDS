"""
ReviewQueue 모델: 수동 검토가 필요한 차단된 거래

이 모델은 고위험으로 분류되어 자동 차단된 거래를 보안팀이
수동으로 검토할 수 있도록 검토 큐에 등록합니다.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
import enum
from sqlalchemy import (
    ForeignKey,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


class ReviewStatus(str, enum.Enum):
    """검토 상태"""
    PENDING = "pending"        # 검토 대기 중
    IN_REVIEW = "in_review"    # 검토 진행 중
    COMPLETED = "completed"    # 검토 완료


class ReviewDecision(str, enum.Enum):
    """검토 결과"""
    APPROVE = "approve"    # 승인 (오탐으로 판단, 거래 허용)
    BLOCK = "block"        # 차단 유지 (정탐으로 판단, 거래 거부)
    ESCALATE = "escalate"  # 상위 에스컬레이션 (추가 조사 필요)


class ReviewQueue(Base):
    """
    ReviewQueue 모델

    고위험으로 분류되어 자동 차단된 거래를 보안팀이 수동으로 검토하기 위한 큐.
    각 차단된 거래는 ReviewQueue에 자동으로 추가되며,
    보안팀 담당자가 위험 요인을 분석하고 최종 결정을 내립니다.
    """

    __tablename__ = "review_queue"

    # 기본 식별자
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="고유 식별자",
    )

    # 관계 필드: Transaction과 1:1 관계
    transaction_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="거래 ID (1:1 관계)",
    )

    # 검토 담당자 (보안팀 사용자)
    assigned_to: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="검토 담당자 ID (보안팀 사용자)",
    )

    # 검토 상태 및 결과
    status: Mapped[ReviewStatus] = mapped_column(
        SQLEnum(ReviewStatus, name="review_status", create_constraint=True),
        nullable=False,
        default=ReviewStatus.PENDING,
        index=True,
        comment="검토 상태",
    )

    decision: Mapped[Optional[ReviewDecision]] = mapped_column(
        SQLEnum(ReviewDecision, name="review_decision", create_constraint=True),
        nullable=True,
        comment="검토 결과",
    )

    # 검토 메모
    review_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="검토 담당자 메모 (검토 사유, 추가 조사 내용 등)",
    )

    # 타임스탬프
    added_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="큐 추가 일시",
    )

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="검토 완료 일시",
    )

    # Relationship (Transaction 모델과 연결)
    # Note: Transaction 모델에도 역방향 relationship 추가 필요
    # transaction: Mapped["Transaction"] = relationship(
    #     "Transaction",
    #     back_populates="review_queue",
    #     uselist=False,
    # )

    def __repr__(self) -> str:
        return (
            f"<ReviewQueue(id={self.id}, "
            f"transaction_id={self.transaction_id}, "
            f"status={self.status}, "
            f"decision={self.decision})>"
        )

    @property
    def is_pending(self) -> bool:
        """검토 대기 중 여부"""
        return self.status == ReviewStatus.PENDING

    @property
    def is_in_review(self) -> bool:
        """검토 진행 중 여부"""
        return self.status == ReviewStatus.IN_REVIEW

    @property
    def is_completed(self) -> bool:
        """검토 완료 여부"""
        return self.status == ReviewStatus.COMPLETED

    @property
    def review_time_seconds(self) -> Optional[int]:
        """
        검토 소요 시간 (초)

        Returns:
            Optional[int]: 검토 소요 시간 (검토 완료되지 않은 경우 None)
        """
        if self.reviewed_at is None:
            return None
        return int((self.reviewed_at - self.added_at).total_seconds())

    def assign_to_reviewer(self, reviewer_id: UUID) -> None:
        """
        검토 담당자 할당 및 상태 변경

        Args:
            reviewer_id: 검토 담당자 사용자 ID
        """
        self.assigned_to = reviewer_id
        self.status = ReviewStatus.IN_REVIEW

    def complete_review(
        self, decision: ReviewDecision, notes: Optional[str] = None
    ) -> None:
        """
        검토 완료 처리

        Args:
            decision: 검토 결과 (approve/block/escalate)
            notes: 검토 메모
        """
        self.decision = decision
        self.status = ReviewStatus.COMPLETED
        self.reviewed_at = datetime.utcnow()
        if notes:
            self.review_notes = notes
