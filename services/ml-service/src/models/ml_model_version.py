"""
MLModelVersion 모델

ML 모델 버전 관리를 위한 엔티티.
"""

from datetime import datetime
import enum
from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    DateTime,
    Index,
    UUID,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class ModelName(str, enum.Enum):
    """모델 이름"""

    RANDOM_FOREST = "random_forest"  # Random Forest
    XGBOOST = "xgboost"  # XGBoost
    AUTOENCODER = "autoencoder"  # Autoencoder
    LSTM = "lstm"  # LSTM


class MLModelVersion(Base):
    """ML 모델 버전 모델"""

    __tablename__ = "ml_model_versions"

    version_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="버전 ID"
    )
    model_name = Column(Enum(ModelName), nullable=False, comment="모델 이름")
    model_type = Column(String(50), nullable=True, comment='모델 타입 (예: "ensemble")')
    version_number = Column(String(20), nullable=False, comment='버전 번호 (예: "1.0.0")')
    trained_at = Column(DateTime, nullable=False, comment="학습 일시")
    accuracy = Column(Float, nullable=True, comment="정확도 (Accuracy)")
    precision = Column(Float, nullable=True, comment="정밀도 (Precision)")
    recall = Column(Float, nullable=True, comment="재현율 (Recall)")
    f1_score = Column(Float, nullable=True, comment="F1 Score")
    is_active = Column(Boolean, default=False, nullable=False, comment="활성화 여부")
    model_path = Column(String(255), nullable=False, comment="모델 파일 경로 (S3 또는 로컬)")
    hyperparameters = Column(JSONB, nullable=True, comment="학습에 사용된 하이퍼파라미터")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="생성 일시"
    )

    __table_args__ = (
        UniqueConstraint(
            "model_name", "version_number", name="uq_ml_model_name_version"
        ),
        Index("idx_ml_model_versions_is_active", "is_active"),
        Index("idx_ml_model_versions_trained_at", "trained_at"),
    )

    def __repr__(self):
        return f"<MLModelVersion(version_id={self.version_id}, model={self.model_name.value}, version={self.version_number})>"
