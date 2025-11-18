"""
DataDriftLog 모델

데이터 분포 변화를 추적한다.
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, Text, DateTime, Index, UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class DataDriftLog(Base):
    """데이터 드리프트 로그 모델"""

    __tablename__ = "data_drift_logs"

    log_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="로그 ID"
    )
    detected_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="감지 일시"
    )
    metric_name = Column(
        String(255),
        nullable=False,
        comment='메트릭 이름 (예: "avg_order_amount", "transaction_frequency")',
    )
    baseline_value = Column(Float, nullable=False, comment="기준값")
    current_value = Column(Float, nullable=False, comment="현재값")
    drift_percentage = Column(Float, nullable=False, comment="변화율 (%)")
    alert_triggered = Column(
        Boolean, default=False, nullable=False, comment="알림 트리거 여부"
    )
    alert_message = Column(Text, nullable=True, comment="알림 메시지")

    __table_args__ = (
        Index("idx_data_drift_logs_detected_at", "detected_at"),
        Index("idx_data_drift_logs_alert_triggered", "alert_triggered"),
    )

    def __repr__(self):
        return f"<DataDriftLog(log_id={self.log_id}, metric={self.metric_name}, drift={self.drift_percentage}%)>"
