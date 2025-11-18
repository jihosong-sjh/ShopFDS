"""
DeviceFingerprint 모델

브라우저 기반 디바이스 고유 식별 정보를 저장한다.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, Index
from src.models.base import Base


class DeviceFingerprint(Base):
    """디바이스 핑거프린트 모델"""

    __tablename__ = "device_fingerprints"

    device_id = Column(String(64), primary_key=True, comment="SHA-256 해시")
    canvas_hash = Column(String(64), nullable=False, comment="Canvas API 해시")
    webgl_hash = Column(String(64), nullable=False, comment="WebGL API 해시")
    audio_hash = Column(String(64), nullable=False, comment="Audio API 해시")
    cpu_cores = Column(Integer, nullable=False, comment="CPU 코어 수")
    memory_size = Column(Integer, nullable=False, comment="메모리 크기 (MB)")
    screen_resolution = Column(
        String(20), nullable=False, comment='화면 해상도 (예: "1920x1080")'
    )
    timezone = Column(String(50), nullable=False, comment='타임존 (예: "Asia/Seoul")')
    language = Column(String(10), nullable=False, comment='언어 (예: "ko-KR")')
    user_agent = Column(Text, nullable=False, comment="User-Agent 문자열")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="생성 일시"
    )
    last_seen_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="마지막 활동 일시"
    )
    blacklisted = Column(Boolean, default=False, nullable=False, comment="블랙리스트 여부")
    blacklist_reason = Column(Text, nullable=True, comment="블랙리스트 사유")
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="수정 일시",
    )

    __table_args__ = (
        Index("idx_device_fingerprints_created_at", "created_at"),
        Index("idx_device_fingerprints_blacklisted", "blacklisted"),
    )

    def __repr__(self):
        return f"<DeviceFingerprint(device_id={self.device_id}, blacklisted={self.blacklisted})>"
