"""
FraudCase: 확정된 사기 케이스

ML 학습 데이터로 활용되는 사기 거래 사례 관리
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Numeric,
    Text,
    ForeignKey,
    Enum as SQLEnum,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, validates

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class FraudType(str, Enum):
    """사기 유형"""

    CARD_THEFT = "card_theft"  # 카드 도용
    ACCOUNT_TAKEOVER = "account_takeover"  # 계정 탈취
    REFUND_FRAUD = "refund_fraud"  # 환불 사기
    IDENTITY_THEFT = "identity_theft"  # 신원 도용
    PROMO_ABUSE = "promo_abuse"  # 프로모션 악용
    CHARGEBACK_FRAUD = "chargeback_fraud"  # 지불 거부 사기
    SYNTHETIC_IDENTITY = "synthetic_identity"  # 합성 신원 사기


class CaseStatus(str, Enum):
    """케이스 상태"""

    SUSPECTED = "suspected"  # 의심 (자동 탐지)
    CONFIRMED = "confirmed"  # 확정 (보안팀 검토 완료)
    FALSE_POSITIVE = "false_positive"  # 오탐 (정상 거래로 판정)


class FraudCase(Base):
    """
    확정된 사기 케이스

    FDS가 탐지하거나 보안팀이 검토한 사기 거래 사례를 저장하여
    ML 모델 학습 데이터로 활용
    """

    __tablename__ = "fraud_cases"

    # 기본 정보
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id = Column(
        PGUUID(as_uuid=True),
        # ForeignKey("transactions.id"),  # FDS 서비스의 transactions 테이블 참조
        unique=True,
        nullable=False,
        comment="거래 ID (transactions.id)",
    )
    user_id = Column(
        PGUUID(as_uuid=True),
        # ForeignKey("users.id"),  # 이커머스 서비스의 users 테이블 참조
        nullable=False,
        comment="사용자 ID (users.id)",
    )

    # 사기 유형 및 상태
    fraud_type = Column(
        SQLEnum(FraudType, name="fraud_type_enum"),
        nullable=False,
        comment="사기 유형",
    )
    status = Column(
        SQLEnum(CaseStatus, name="case_status_enum"),
        nullable=False,
        default=CaseStatus.SUSPECTED,
        comment="케이스 상태",
    )

    # 일시 정보
    detected_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="탐지 일시 (FDS 자동 탐지 또는 보안팀 발견)",
    )
    confirmed_at = Column(
        DateTime,
        nullable=True,
        comment="확정 일시 (보안팀 검토 완료 후)",
    )

    # 손실 정보
    loss_amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment="손실 금액 (원)",
    )

    # 보안팀 메모
    notes = Column(
        Text,
        nullable=True,
        comment="보안팀 메모 (사기 수법, 대응 내역 등)",
    )

    # 제약 조건
    __table_args__ = (
        CheckConstraint("loss_amount >= 0", name="check_loss_amount_positive"),
        CheckConstraint(
            "(status = 'confirmed' AND confirmed_at IS NOT NULL) OR "
            "(status != 'confirmed' AND confirmed_at IS NULL)",
            name="check_confirmed_at_consistency",
        ),
    )

    @validates("status")
    def validate_status_transition(self, key, new_status: CaseStatus) -> CaseStatus:
        """
        상태 전이 검증

        suspected → confirmed (보안팀 검토 후 확정)
        suspected → false_positive (오탐으로 판단)
        """
        if hasattr(self, "status") and self.status:
            old_status = self.status

            # confirmed나 false_positive에서는 더 이상 상태 변경 불가
            if old_status in [CaseStatus.CONFIRMED, CaseStatus.FALSE_POSITIVE]:
                if new_status != old_status:
                    raise ValueError(
                        f"상태 '{old_status.value}'에서는 더 이상 변경할 수 없습니다"
                    )

        return new_status

    def confirm(self, notes: Optional[str] = None) -> None:
        """
        사기 케이스 확정

        보안팀이 검토를 완료하고 실제 사기로 확정할 때 사용
        """
        self.status = CaseStatus.CONFIRMED
        self.confirmed_at = datetime.utcnow()

        if notes:
            self.notes = notes if not self.notes else f"{self.notes}\n\n{notes}"

    def mark_false_positive(self, notes: Optional[str] = None) -> None:
        """
        오탐으로 표시

        보안팀이 검토 후 정상 거래로 판단할 때 사용
        """
        self.status = CaseStatus.FALSE_POSITIVE

        if notes:
            self.notes = notes if not self.notes else f"{self.notes}\n\n오탐: {notes}"

    def to_dict(self) -> dict:
        """케이스 정보를 딕셔너리로 변환"""
        return {
            "id": str(self.id),
            "transaction_id": str(self.transaction_id),
            "user_id": str(self.user_id),
            "fraud_type": self.fraud_type.value,
            "status": self.status.value,
            "detected_at": self.detected_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "loss_amount": float(self.loss_amount),
            "notes": self.notes,
        }

    def to_training_sample(self) -> dict:
        """
        ML 학습 샘플 형식으로 변환

        Returns:
            학습용 레이블 및 메타데이터
        """
        return {
            "transaction_id": str(self.transaction_id),
            "user_id": str(self.user_id),
            "is_fraud": self.status == CaseStatus.CONFIRMED,  # 레이블
            "fraud_type": self.fraud_type.value if self.status == CaseStatus.CONFIRMED else None,
            "loss_amount": float(self.loss_amount),
            "detected_at": self.detected_at.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"<FraudCase(transaction_id='{self.transaction_id}', "
            f"fraud_type='{self.fraud_type.value}', "
            f"status='{self.status.value}', loss_amount={self.loss_amount})>"
        )


# 유틸리티 함수
def get_confirmed_fraud_cases(db_session, limit: Optional[int] = None):
    """
    확정된 사기 케이스 조회 (ML 학습용)

    Args:
        db_session: 데이터베이스 세션
        limit: 조회 개수 제한 (None이면 전체)

    Returns:
        확정된 FraudCase 리스트
    """
    query = db_session.query(FraudCase).filter(
        FraudCase.status == CaseStatus.CONFIRMED
    ).order_by(FraudCase.confirmed_at.desc())

    if limit:
        query = query.limit(limit)

    return query.all()


def get_fraud_statistics(db_session) -> dict:
    """
    사기 케이스 통계 조회

    Returns:
        사기 유형별, 상태별 통계
    """
    from sqlalchemy import func

    # 전체 케이스 수
    total_cases = db_session.query(func.count(FraudCase.id)).scalar()

    # 상태별 케이스 수
    status_counts = (
        db_session.query(FraudCase.status, func.count(FraudCase.id))
        .group_by(FraudCase.status)
        .all()
    )

    # 사기 유형별 케이스 수 (확정된 케이스만)
    fraud_type_counts = (
        db_session.query(FraudCase.fraud_type, func.count(FraudCase.id))
        .filter(FraudCase.status == CaseStatus.CONFIRMED)
        .group_by(FraudCase.fraud_type)
        .all()
    )

    # 총 손실 금액 (확정된 케이스만)
    total_loss = (
        db_session.query(func.sum(FraudCase.loss_amount))
        .filter(FraudCase.status == CaseStatus.CONFIRMED)
        .scalar()
    ) or Decimal("0")

    return {
        "total_cases": total_cases,
        "status_distribution": {status.value: count for status, count in status_counts},
        "fraud_type_distribution": {
            fraud_type.value: count for fraud_type, count in fraud_type_counts
        },
        "total_confirmed_loss": float(total_loss),
    }
