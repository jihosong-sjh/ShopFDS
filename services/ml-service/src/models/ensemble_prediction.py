"""
EnsemblePrediction 모델

앙상블 모델의 예측 결과를 저장한다.
"""

from datetime import datetime
import enum
from sqlalchemy import Column, Float, DateTime, Index, UUID, Enum
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class PredictionDecision(str, enum.Enum):
    """예측 결정"""

    ALLOW = "allow"  # 허용
    BLOCK = "block"  # 차단
    REVIEW = "review"  # 수동 검토


class EnsemblePrediction(Base):
    """앙상블 예측 모델"""

    __tablename__ = "ensemble_predictions"

    prediction_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="예측 ID"
    )
    transaction_id = Column(UUID(as_uuid=True), nullable=False, comment="거래 ID")
    rf_score = Column(Float, nullable=True, comment="Random Forest 예측 (0-1)")
    xgb_score = Column(Float, nullable=True, comment="XGBoost 예측 (0-1)")
    autoencoder_score = Column(Float, nullable=True, comment="Autoencoder 예측 (0-1)")
    lstm_score = Column(Float, nullable=True, comment="LSTM 예측 (0-1)")
    ensemble_score = Column(Float, nullable=False, comment="가중 평균 (0-1)")
    final_decision = Column(Enum(PredictionDecision), nullable=False, comment="최종 결정")
    predicted_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="예측 일시"
    )
    model_version_id = Column(UUID(as_uuid=True), nullable=True, comment="모델 버전 ID")

    __table_args__ = (
        Index("idx_ensemble_predictions_transaction_id", "transaction_id"),
        Index("idx_ensemble_predictions_predicted_at", "predicted_at"),
    )

    def __repr__(self):
        return f"<EnsemblePrediction(prediction_id={self.prediction_id}, transaction_id={self.transaction_id}, decision={self.final_decision.value})>"
