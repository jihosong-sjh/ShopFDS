"""
RuleExecution 모델

거래별 룰 실행 결과를 저장한다.
"""

from datetime import datetime
from sqlalchemy import Column, Boolean, DateTime, Index, UUID
from sqlalchemy.dialects.postgresql import JSON  # JSON -> JSON for SQLite compatibility
from src.models.base import Base
import uuid


class RuleExecution(Base):
    """룰 실행 결과 모델"""

    __tablename__ = "rule_executions"

    execution_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="실행 ID"
    )
    transaction_id = Column(UUID(as_uuid=True), nullable=False, comment="거래 ID")
    rule_id = Column(UUID(as_uuid=True), nullable=False, comment="룰 ID")
    matched = Column(Boolean, nullable=False, comment="매칭 여부")
    triggered_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="트리거 일시"
    )
    match_metadata = Column(JSON, nullable=True, comment="매칭 상세 정보")

    __table_args__ = (
        Index("idx_rule_executions_transaction_id", "transaction_id"),
        Index("idx_rule_executions_rule_id", "rule_id"),
        Index("idx_rule_executions_triggered_at", "triggered_at"),
    )

    def __repr__(self):
        return f"<RuleExecution(execution_id={self.execution_id}, transaction_id={self.transaction_id}, matched={self.matched})>"
