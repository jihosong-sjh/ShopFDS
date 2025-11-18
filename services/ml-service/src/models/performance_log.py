"""
Performance Log Model

Stores model performance evaluation results for trend analysis
and retraining triggers.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Float,
    Integer,
    DateTime,
    Boolean,
    Index,
    Uuid,
)
import uuid

from .base import Base


class PerformanceLog(Base):
    """Model performance evaluation log"""

    __tablename__ = "performance_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    evaluated_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    sample_size = Column(Integer, nullable=False)

    # Performance metrics
    f1_score = Column(Float, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=False)
    false_positive_rate = Column(Float, nullable=False)
    false_negative_rate = Column(Float, nullable=False)

    # Confusion matrix
    true_positives = Column(Integer, nullable=False)
    false_positives = Column(Integer, nullable=False)
    true_negatives = Column(Integer, nullable=False)
    false_negatives = Column(Integer, nullable=False)

    # Performance status
    performance_degraded = Column(Boolean, nullable=False, default=False, index=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_performance_logs_evaluated_at", "evaluated_at"),
        Index("idx_performance_logs_performance_degraded", "performance_degraded"),
    )

    def __repr__(self):
        return (
            f"<PerformanceLog(id={self.id}, evaluated_at={self.evaluated_at}, "
            f"f1_score={self.f1_score}, degraded={self.performance_degraded})>"
        )
