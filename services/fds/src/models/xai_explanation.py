"""
XAIExplanation 모델

SHAP/LIME 기반 XAI 분석 결과를 저장한다.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Index, UUID
from sqlalchemy.dialects.postgresql import JSON  # JSON -> JSON for SQLite compatibility
from src.models.base import Base
import uuid


class XAIExplanation(Base):
    """XAI 설명 모델"""

    __tablename__ = "xai_explanations"

    explanation_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="설명 ID"
    )
    transaction_id = Column(UUID(as_uuid=True), nullable=False, comment="거래 ID")
    shap_values = Column(
        JSON, nullable=True, comment="SHAP 값 [{feature, shap_value, base_value}]"
    )
    lime_explanation = Column(JSON, nullable=True, comment="LIME 로컬 모델 근사 결과")
    top_risk_factors = Column(
        JSON, nullable=True, comment="상위 위험 요인 [{factor, contribution, rank}]"
    )
    explanation_time_ms = Column(Integer, nullable=True, comment="SHAP 계산 시간 (밀리초)")
    generated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="생성 일시"
    )

    __table_args__ = (
        Index("idx_xai_explanations_transaction_id", "transaction_id"),
        Index("idx_xai_explanations_generated_at", "generated_at"),
    )

    def __repr__(self):
        return f"<XAIExplanation(explanation_id={self.explanation_id}, transaction_id={self.transaction_id})>"
