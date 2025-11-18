"""
ExternalServiceLog 모델

EmailRep, Numverify, BIN DB, HaveIBeenPwned 등 외부 API 호출을 기록한다.
"""

from datetime import datetime
import enum
from sqlalchemy import Column, Text, Integer, DateTime, Index, UUID, Enum
from sqlalchemy.dialects.postgresql import JSON  # JSON -> JSON for SQLite compatibility
from src.models.base import Base
import uuid


class ServiceName(str, enum.Enum):
    """외부 서비스 이름"""

    EMAILREP = "emailrep"  # 이메일 평판 조회
    NUMVERIFY = "numverify"  # 전화번호 검증
    BIN_DATABASE = "bin_database"  # 카드 BIN 조회
    HAVEIBEENPWNED = "haveibeenpwned"  # 유출 이메일 확인


class ExternalServiceLog(Base):
    """외부 서비스 호출 로그 모델"""

    __tablename__ = "external_service_logs"

    log_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="로그 ID"
    )
    service_name = Column(Enum(ServiceName), nullable=False, comment="서비스 이름")
    request_data = Column(JSON, nullable=True, comment="요청 데이터")
    response_data = Column(JSON, nullable=True, comment="응답 데이터")
    response_time_ms = Column(Integer, nullable=False, comment="응답 시간 (밀리초)")
    status_code = Column(Integer, nullable=True, comment="HTTP 상태 코드")
    error_message = Column(Text, nullable=True, comment="에러 메시지")
    called_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="호출 일시"
    )
    transaction_id = Column(UUID(as_uuid=True), nullable=True, comment="거래 ID (선택)")

    __table_args__ = (
        Index("idx_external_service_logs_service_name", "service_name"),
        Index("idx_external_service_logs_called_at", "called_at"),
        Index("idx_external_service_logs_transaction_id", "transaction_id"),
    )

    def __repr__(self):
        return f"<ExternalServiceLog(log_id={self.log_id}, service={self.service_name.value}, status={self.status_code})>"
