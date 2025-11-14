"""
MLModel: ML 모델 메타데이터

FDS에서 사용하는 기계학습 모델의 버전, 성능 지표, 배포 상태를 관리
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Date,
    Numeric,
    Enum as SQLEnum,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import validates


class DeploymentStatus(str, Enum):
    """모델 배포 상태"""

    DEVELOPMENT = "development"  # 개발 중
    STAGING = "staging"  # 스테이징 환경 배포
    PRODUCTION = "production"  # 프로덕션 배포
    RETIRED = "retired"  # 은퇴 (사용 중단)


class ModelType(str, Enum):
    """ML 모델 유형"""

    ISOLATION_FOREST = "isolation_forest"  # 이상 탐지 (비지도 학습)
    RANDOM_FOREST = "random_forest"  # 랜덤 포레스트 (지도 학습)
    LIGHTGBM = "lightgbm"  # LightGBM (그래디언트 부스팅)
    XGBOOST = "xgboost"  # XGBoost
    NEURAL_NETWORK = "neural_network"  # 딥러닝 모델


# Base는 ml-service 자체 데이터베이스 설정에서 가져옴 (나중에 구현)
# 현재는 구조만 정의
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class MLModel(Base):
    """
    ML 모델 메타데이터

    모델의 학습 정보, 성능 지표, 배포 이력을 관리하여
    모델 버전 관리 및 A/B 테스트, 롤백을 지원
    """

    __tablename__ = "ml_models"

    # 기본 정보
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, comment="모델 이름 (예: IsolationForest-v1.2)")
    version = Column(String(50), nullable=False, comment="Semantic Versioning (1.2.0)")
    model_type = Column(
        SQLEnum(ModelType, name="model_type_enum"),
        nullable=False,
        comment="모델 유형 (isolation_forest, lightgbm 등)",
    )

    # 학습 정보
    training_data_start = Column(
        Date, nullable=False, comment="학습 데이터 시작일 (예: 2025-01-01)"
    )
    training_data_end = Column(
        Date, nullable=False, comment="학습 데이터 종료일 (예: 2025-11-13)"
    )
    trained_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="학습 완료 일시"
    )

    # 성능 지표 (0-1 범위)
    accuracy = Column(
        Numeric(5, 4),
        nullable=True,
        comment="정확도 (Accuracy): (TP+TN)/(TP+TN+FP+FN)",
    )
    precision = Column(
        Numeric(5, 4),
        nullable=True,
        comment="정밀도 (Precision): TP/(TP+FP) - 양성 예측 중 실제 양성 비율",
    )
    recall = Column(
        Numeric(5, 4),
        nullable=True,
        comment="재현율 (Recall): TP/(TP+FN) - 실제 양성 중 탐지 비율",
    )
    f1_score = Column(
        Numeric(5, 4),
        nullable=True,
        comment="F1 스코어: 2*(Precision*Recall)/(Precision+Recall)",
    )

    # 배포 정보
    deployment_status = Column(
        SQLEnum(DeploymentStatus, name="deployment_status_enum"),
        nullable=False,
        default=DeploymentStatus.DEVELOPMENT,
        comment="배포 상태",
    )
    deployed_at = Column(DateTime, nullable=True, comment="프로덕션 배포 일시")
    model_path = Column(
        String(500),
        nullable=False,
        comment="모델 파일 경로 (S3, 로컬, MLflow 등)",
    )

    # 제약 조건
    __table_args__ = (
        CheckConstraint(
            "training_data_end >= training_data_start",
            name="check_training_dates",
        ),
        CheckConstraint("accuracy >= 0 AND accuracy <= 1", name="check_accuracy_range"),
        CheckConstraint(
            "precision >= 0 AND precision <= 1", name="check_precision_range"
        ),
        CheckConstraint("recall >= 0 AND recall <= 1", name="check_recall_range"),
        CheckConstraint(
            "f1_score >= 0 AND f1_score <= 1", name="check_f1_score_range"
        ),
    )

    @validates("version")
    def validate_version(self, key, version: str) -> str:
        """
        버전 형식 검증: Semantic Versioning (MAJOR.MINOR.PATCH)

        예: "1.2.0", "2.0.1"
        """
        parts = version.split(".")
        if len(parts) != 3:
            raise ValueError(
                f"버전은 Semantic Versioning 형식(MAJOR.MINOR.PATCH)이어야 합니다: {version}"
            )

        for part in parts:
            if not part.isdigit():
                raise ValueError(f"버전의 각 부분은 숫자여야 합니다: {version}")

        return version

    @validates("model_path")
    def validate_model_path(self, key, model_path: str) -> str:
        """모델 경로 검증"""
        if not model_path or not model_path.strip():
            raise ValueError("모델 경로는 필수입니다")

        return model_path.strip()

    def to_dict(self) -> dict:
        """모델 정보를 딕셔너리로 변환"""
        return {
            "id": str(self.id),
            "name": self.name,
            "version": self.version,
            "model_type": self.model_type.value,
            "training_data_start": self.training_data_start.isoformat(),
            "training_data_end": self.training_data_end.isoformat(),
            "trained_at": self.trained_at.isoformat(),
            "accuracy": float(self.accuracy) if self.accuracy else None,
            "precision": float(self.precision) if self.precision else None,
            "recall": float(self.recall) if self.recall else None,
            "f1_score": float(self.f1_score) if self.f1_score else None,
            "deployment_status": self.deployment_status.value,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "model_path": self.model_path,
        }

    def __repr__(self) -> str:
        return (
            f"<MLModel(name='{self.name}', version='{self.version}', "
            f"status='{self.deployment_status.value}', f1={self.f1_score})>"
        )


# 유틸리티 함수
def get_production_model(db_session) -> Optional[MLModel]:
    """
    현재 프로덕션 배포 중인 모델 조회

    주의: deployment_status='production'인 모델은 1개만 존재해야 함
    """
    return (
        db_session.query(MLModel)
        .filter(MLModel.deployment_status == DeploymentStatus.PRODUCTION)
        .order_by(MLModel.deployed_at.desc())
        .first()
    )


def compare_models(model_a: MLModel, model_b: MLModel) -> dict:
    """
    두 모델의 성능 지표 비교

    Args:
        model_a: 첫 번째 모델
        model_b: 두 번째 모델

    Returns:
        비교 결과 딕셔너리 (향상도 포함)
    """
    metrics = ["accuracy", "precision", "recall", "f1_score"]
    comparison = {
        "model_a": {"name": model_a.name, "version": model_a.version},
        "model_b": {"name": model_b.name, "version": model_b.version},
        "metrics": {},
    }

    for metric in metrics:
        val_a = getattr(model_a, metric)
        val_b = getattr(model_b, metric)

        if val_a is not None and val_b is not None:
            val_a_float = float(val_a)
            val_b_float = float(val_b)
            improvement = ((val_b_float - val_a_float) / val_a_float) * 100

            comparison["metrics"][metric] = {
                "model_a": val_a_float,
                "model_b": val_b_float,
                "improvement_percent": round(improvement, 2),
                "better_model": (
                    "model_b" if val_b_float > val_a_float else "model_a"
                ),
            }
        else:
            comparison["metrics"][metric] = {
                "model_a": val_a_float if val_a else None,
                "model_b": val_b_float if val_b else None,
                "improvement_percent": None,
                "better_model": None,
            }

    return comparison
