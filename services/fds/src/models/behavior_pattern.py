"""
BehaviorPattern 모델

사용자의 마우스, 키보드, 클릭스트림 패턴을 저장한다.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Index, UUID
from sqlalchemy.dialects.postgresql import JSONB
from src.models.base import Base
import uuid


class BehaviorPattern(Base):
    """행동 패턴 모델"""

    __tablename__ = "behavior_patterns"

    session_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="세션 ID"
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, comment="사용자 ID")
    mouse_movements = Column(
        JSONB,
        nullable=True,
        comment="마우스 움직임 데이터 [{timestamp, x, y, speed, acceleration, curvature}]",
    )
    keyboard_events = Column(
        JSONB, nullable=True, comment="키보드 이벤트 [{timestamp, key, duration}]"
    )
    clickstream = Column(
        JSONB, nullable=True, comment="클릭스트림 [{page, timestamp, duration}]"
    )
    bot_score = Column(Integer, default=0, nullable=False, comment="봇 확률 (0-100)")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="생성 일시"
    )

    __table_args__ = (
        Index("idx_behavior_patterns_user_id", "user_id"),
        Index("idx_behavior_patterns_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<BehaviorPattern(session_id={self.session_id}, user_id={self.user_id}, bot_score={self.bot_score})>"
