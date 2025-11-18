"""
Fraud Label Model

Stores fraud labels for transactions used in ML model training.
Labels can come from chargebacks, user reports, or manual review.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    Index,
    Uuid,
)
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class LabelSource(str, Enum):
    """Source of the fraud label"""

    CHARGEBACK = "chargeback"  # Automatic from chargeback data
    USER_REPORT = "user_report"  # User fraud report
    MANUAL_REVIEW = "manual_review"  # Security team manual review
    AUTO_SAFE_PERIOD = "auto_safe_period"  # Auto-labeled as safe after period
    ML_PREDICTION = "ml_prediction"  # ML model prediction (for validation)


class FraudLabel(Base):
    """Fraud label for transaction"""

    __tablename__ = "fraud_labels"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id = Column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    is_fraud = Column(Boolean, nullable=False)
    label_source = Column(String(50), nullable=False)  # LabelSource enum
    confidence_score = Column(Float, nullable=False)  # 0.0-1.0
    labeled_by = Column(String(100), nullable=False)  # User ID or 'system'
    labeled_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    transaction = relationship("Transaction", back_populates="fraud_label")

    __table_args__ = (
        Index("idx_fraud_labels_transaction_id", "transaction_id"),
        Index("idx_fraud_labels_label_source", "label_source"),
        Index("idx_fraud_labels_is_fraud", "is_fraud"),
        Index("idx_fraud_labels_labeled_at", "labeled_at"),
    )

    def __repr__(self):
        return (
            f"<FraudLabel(id={self.id}, transaction_id={self.transaction_id}, "
            f"is_fraud={self.is_fraud}, source={self.label_source})>"
        )
