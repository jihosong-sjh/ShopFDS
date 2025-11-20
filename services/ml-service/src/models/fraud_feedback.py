"""
Fraud Feedback Model

Stores user feedback on fraudulent transactions.
Feedback can come from customers, merchants, or security team.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Index,
    Uuid,
    JSON,
)
import uuid

from .base import Base


class FraudFeedback(Base):
    """User feedback on fraud transactions"""

    __tablename__ = "fraud_feedback"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id = Column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Uuid, nullable=False, index=True)
    report_type = Column(
        String(50), nullable=False
    )  # customer, merchant, security_team
    reason = Column(Text, nullable=False)
    additional_info = Column(JSON, nullable=True)
    reported_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed = Column(Boolean, nullable=False, default=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_fraud_feedback_transaction_id", "transaction_id"),
        Index("idx_fraud_feedback_user_id", "user_id"),
        Index("idx_fraud_feedback_processed", "processed"),
        Index("idx_fraud_feedback_reported_at", "reported_at"),
    )

    def __repr__(self):
        return (
            f"<FraudFeedback(id={self.id}, transaction_id={self.transaction_id}, "
            f"type={self.report_type}, processed={self.processed})>"
        )
