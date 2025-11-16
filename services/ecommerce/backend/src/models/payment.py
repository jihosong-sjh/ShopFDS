"""
결제(Payment) 모델

목적: 주문에 대한 결제 정보 (PCI-DSS 준수)
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    String,
    Text,
    DECIMAL,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class PaymentMethod(str, Enum):
    """결제 수단"""

    CREDIT_CARD = "credit_card"
    # 향후 확장: debit_card, bank_transfer, paypal 등


class PaymentStatus(str, Enum):
    """결제 상태"""

    PENDING = "pending"  # 결제 대기
    COMPLETED = "completed"  # 결제 완료
    FAILED = "failed"  # 결제 실패
    REFUNDED = "refunded"  # 환불 완료


class Payment(Base):
    """결제 모델"""

    __tablename__ = "payments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    order_id = Column(
        Uuid,
        ForeignKey("orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    payment_method = Column(
        String(50),
        nullable=False,
        default=PaymentMethod.CREDIT_CARD.value,
    )
    amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(
        String(50),
        nullable=False,
        default=PaymentStatus.PENDING.value,
    )

    # 카드 정보 (토큰화된 정보만 저장)
    card_token = Column(String(255), nullable=False)  # 실제 카드 번호는 저장 금지
    card_last_four = Column(String(4), nullable=False)  # 표시용 마지막 4자리

    # 결제 게이트웨이 정보
    transaction_id = Column(String(100), nullable=True)  # 외부 결제 게이트웨이의 거래 ID

    # 타임스탬프
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # 실패 사유
    failed_reason = Column(Text, nullable=True)

    # 관계
    order = relationship("Order", back_populates="payment")

    # 제약 조건
    __table_args__ = (
        CheckConstraint("amount >= 0", name="check_payment_amount_non_negative"),
        CheckConstraint("payment_method IN ('credit_card')", name="check_payment_method"),
        CheckConstraint("status IN ('pending', 'completed', 'failed', 'refunded')", name="check_payment_status"),
    )

    def __repr__(self):
        return f"<Payment(id={self.id}, order_id={self.order_id}, status={self.status}, amount={self.amount})>"

    def mark_as_completed(self, transaction_id: str):
        """결제 완료 처리"""
        if self.status != PaymentStatus.PENDING.value:
            raise ValueError(f"결제 완료 처리 불가: 현재 상태 {self.status}")

        self.status = PaymentStatus.COMPLETED.value
        self.transaction_id = transaction_id
        self.completed_at = datetime.utcnow()

    def mark_as_failed(self, reason: str):
        """결제 실패 처리"""
        if self.status not in [PaymentStatus.PENDING.value, PaymentStatus.COMPLETED.value]:
            raise ValueError(f"결제 실패 처리 불가: 현재 상태 {self.status}")

        self.status = PaymentStatus.FAILED.value
        self.failed_reason = reason

    def mark_as_refunded(self):
        """환불 처리"""
        if self.status != PaymentStatus.COMPLETED.value:
            raise ValueError(f"환불 처리 불가: 현재 상태 {self.status}")

        self.status = PaymentStatus.REFUNDED.value

    @staticmethod
    def tokenize_card(card_number: str) -> str:
        """
        카드 번호를 토큰화

        실제 구현에서는 PCI-DSS 준수 결제 게이트웨이의 토큰화 API를 사용해야 함
        (예: Stripe, Toss Payments 등)
        """
        # 임시 구현: 실제로는 외부 서비스 호출
        import hashlib

        return hashlib.sha256(card_number.encode()).hexdigest()

    @staticmethod
    def get_last_four_digits(card_number: str) -> str:
        """카드 마지막 4자리 추출"""
        card_digits = "".join(filter(str.isdigit, card_number))
        if len(card_digits) < 4:
            raise ValueError("유효하지 않은 카드 번호")
        return card_digits[-4:]
