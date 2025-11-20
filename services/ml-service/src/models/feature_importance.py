"""
FeatureImportance 모델

ML 모델의 Feature 중요도 분석 결과를 저장한다.
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Index, UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class FeatureImportance(Base):
    """Feature 중요도 모델"""

    __tablename__ = "feature_importances"

    analysis_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="분석 ID"
    )
    model_version_id = Column(UUID(as_uuid=True), nullable=False, comment="모델 버전 ID")
    feature_name = Column(String(255), nullable=False, comment="Feature 이름")
    importance_score = Column(Float, nullable=False, comment="중요도 점수 (0-1)")
    rank = Column(Integer, nullable=False, comment="순위 (1부터 시작)")
    analyzed_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="분석 일시"
    )

    __table_args__ = (
        Index("idx_feature_importances_model_version_id", "model_version_id"),
        Index("idx_feature_importances_rank", "rank"),
    )

    def __repr__(self):
        return f"<FeatureImportance(analysis_id={self.analysis_id}, feature={self.feature_name}, rank={self.rank})>"
