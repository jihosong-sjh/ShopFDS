"""
BlacklistEntry 모델

차단할 디바이스, IP, 이메일, 카드 BIN, 배송지를 저장한다.
"""

from datetime import datetime
import enum
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Index,
    UUID,
    Enum,
    Boolean,
    UniqueConstraint,
)
from src.models.base import Base
import uuid


class BlacklistEntryType(str, enum.Enum):
    """블랙리스트 항목 타입"""

    DEVICE_ID = "device_id"  # 디바이스 ID
    IP_ADDRESS = "ip_address"  # IP 주소
    EMAIL = "email"  # 이메일
    CARD_BIN = "card_bin"  # 카드 BIN
    SHIPPING_ADDRESS = "shipping_address"  # 배송지


class BlacklistEntry(Base):
    """블랙리스트 항목 모델"""

    __tablename__ = "blacklist_entries"

    entry_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="항목 ID"
    )
    entry_type = Column(Enum(BlacklistEntryType), nullable=False, comment="항목 타입")
    entry_value = Column(String(255), nullable=False, comment="항목 값")
    reason = Column(Text, nullable=False, comment="차단 사유")
    added_by = Column(UUID(as_uuid=True), nullable=True, comment="추가한 사용자 ID")
    added_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="추가 일시"
    )
    expires_at = Column(DateTime, nullable=True, comment="만료 일시 (선택)")
    is_active = Column(Boolean, default=True, nullable=False, comment="활성화 여부")

    __table_args__ = (
        UniqueConstraint(
            "entry_type", "entry_value", name="uq_blacklist_entry_type_value"
        ),
        Index("idx_blacklist_entries_entry_type", "entry_type"),
        Index("idx_blacklist_entries_is_active", "is_active"),
        Index("idx_blacklist_entries_expires_at", "expires_at"),
    )

    def __repr__(self):
        return f"<BlacklistEntry(entry_id={self.entry_id}, type={self.entry_type.value}, value={self.entry_value})>"
