"""
Transaction Model (Reference)

This is a reference model for transactions. The actual transaction data
is stored in the ecommerce service. This model is used for ML training
and fraud detection purposes.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    DECIMAL,
    Integer,
    DateTime,
    ForeignKey,
    Boolean,
    Index,
    Uuid,
    JSON,
)
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class Transaction(Base):
    """Transaction model for ML training"""

    __tablename__ = "transactions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, nullable=False, index=True)
    order_id = Column(Uuid, nullable=True, index=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    payment_method = Column(String(50), nullable=False)
    ip_address = Column(String(45), nullable=True)
    device_fingerprint = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Fraud indicators
    is_chargeback = Column(Boolean, nullable=False, default=False, index=True)
    chargeback_date = Column(DateTime, nullable=True)
    fraud_reported = Column(Boolean, nullable=False, default=False, index=True)
    fraud_report_date = Column(DateTime, nullable=True)
    fraud_report_reason = Column(Text, nullable=True)

    # FDS evaluation result
    fds_risk_score = Column(Integer, nullable=True)
    fds_risk_level = Column(String(20), nullable=True)
    fds_decision = Column(String(50), nullable=True)
    fds_evaluation_data = Column(JSON, nullable=True)

    # Fraud label (for ML training)
    fraud_label_id = Column(
        Uuid, ForeignKey("fraud_labels.id", ondelete="SET NULL"), nullable=True
    )

    # Additional metadata
    metadata = Column(JSON, nullable=True)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    fraud_label = relationship("FraudLabel", back_populates="transaction")

    __table_args__ = (
        Index("idx_transactions_user_id", "user_id"),
        Index("idx_transactions_created_at", "created_at"),
        Index("idx_transactions_is_chargeback", "is_chargeback"),
        Index("idx_transactions_fraud_reported", "fraud_reported"),
        Index("idx_transactions_fraud_label_id", "fraud_label_id"),
    )

    def __repr__(self):
        return (
            f"<Transaction(id={self.id}, user_id={self.user_id}, "
            f"amount={self.amount}, is_chargeback={self.is_chargeback})>"
        )
