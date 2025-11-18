"""
RetrainingJob 모델

모델 재학습 작업을 추적한다.
"""

from datetime import datetime
import enum
from sqlalchemy import Column, String, Text, DateTime, Index, UUID, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class RetrainTriggerType(str, enum.Enum):
    """재학습 트리거 타입"""

    AUTO = "auto"  # 자동
    MANUAL = "manual"  # 수동


class RetrainStatus(str, enum.Enum):
    """재학습 상태"""

    PENDING = "pending"  # 대기 중
    RUNNING = "running"  # 실행 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"  # 실패


class RetrainingJob(Base):
    """재학습 작업 모델"""

    __tablename__ = "retraining_jobs"

    job_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="작업 ID"
    )
    triggered_by = Column(Enum(RetrainTriggerType), nullable=False, comment="트리거 타입")
    trigger_reason = Column(String(255), nullable=True, comment="트리거 사유")
    started_at = Column(DateTime, nullable=True, comment="시작 일시")
    completed_at = Column(DateTime, nullable=True, comment="완료 일시")
    status = Column(
        Enum(RetrainStatus), default=RetrainStatus.PENDING, nullable=False, comment="상태"
    )
    new_model_version_id = Column(
        UUID(as_uuid=True), nullable=True, comment="신규 모델 버전 ID"
    )
    metrics = Column(
        JSONB, nullable=True, comment="성능 지표 {accuracy, precision, recall, f1_score}"
    )
    logs = Column(Text, nullable=True, comment="로그")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="생성 일시"
    )

    __table_args__ = (
        Index("idx_retraining_jobs_status", "status"),
        Index("idx_retraining_jobs_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<RetrainingJob(job_id={self.job_id}, status={self.status.value}, triggered_by={self.triggered_by.value})>"
