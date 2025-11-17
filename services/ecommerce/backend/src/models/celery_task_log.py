"""
Celery Task Log Model

Celery 작업 로그를 추적하기 위한 데이터베이스 모델
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
import enum

from src.models.base import Base


class TaskStatus(str, enum.Enum):
    """Celery 작업 상태"""

    PENDING = "pending"  # 작업 대기 중
    STARTED = "started"  # 작업 시작
    SUCCESS = "success"  # 작업 성공
    FAILURE = "failure"  # 작업 실패
    RETRY = "retry"  # 작업 재시도


class CeleryTaskLog(Base):
    """Celery 작업 로그 모델"""

    __tablename__ = "celery_task_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), unique=True, nullable=False, index=True)
    task_name = Column(String(255), nullable=False, index=True)
    status = Column(
        SQLEnum(TaskStatus, name="task_status"),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
    )

    # 작업 실행 시간 추적
    queued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 작업 결과 및 에러
    result = Column(JSONB, nullable=True)  # 작업 성공 시 결과
    error = Column(Text, nullable=True)  # 작업 실패 시 에러 메시지
    traceback = Column(Text, nullable=True)  # 작업 실패 시 스택 트레이스

    # 재시도 정보
    retries = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # 작업 파라미터 (JSON)
    args = Column(JSONB, nullable=True)  # 위치 인자
    kwargs = Column(JSONB, nullable=True)  # 키워드 인자

    # 메타데이터
    queue_name = Column(String(100), nullable=True, index=True)  # 큐 이름
    worker_name = Column(String(255), nullable=True)  # 워커 이름

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return (
            f"<CeleryTaskLog(id={self.id}, task_name={self.task_name}, "
            f"status={self.status}, task_id={self.task_id})>"
        )

    def mark_as_started(self, worker_name: str = None):
        """작업 시작 마킹"""
        self.status = TaskStatus.STARTED
        self.started_at = datetime.utcnow()
        if worker_name:
            self.worker_name = worker_name

    def mark_as_success(self, result: dict = None):
        """작업 성공 마킹"""
        self.status = TaskStatus.SUCCESS
        self.completed_at = datetime.utcnow()
        if result:
            self.result = result

    def mark_as_failure(self, error: str, traceback: str = None):
        """작업 실패 마킹"""
        self.status = TaskStatus.FAILURE
        self.completed_at = datetime.utcnow()
        self.error = error
        if traceback:
            self.traceback = traceback

    def mark_as_retry(self):
        """작업 재시도 마킹"""
        self.status = TaskStatus.RETRY
        self.retries += 1

    @property
    def execution_time_seconds(self) -> float:
        """작업 실행 시간 (초 단위)"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
