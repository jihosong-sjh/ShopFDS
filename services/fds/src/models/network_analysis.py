"""
NetworkAnalysis 모델

거래별 네트워크 분석 결과를 저장한다.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Index,
    UUID,
)
from sqlalchemy.dialects.postgresql import INET
from src.models.base import Base


class NetworkAnalysis(Base):
    """네트워크 분석 모델"""

    __tablename__ = "network_analysis"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, comment="거래 ID")
    ip_address = Column(INET, nullable=False, comment="IP 주소")
    geoip_country = Column(String(2), nullable=True, comment="GeoIP 국가 코드 (ISO)")
    geoip_city = Column(String(50), nullable=True, comment="GeoIP 도시")
    asn = Column(Integer, nullable=True, comment="AS 번호")
    asn_organization = Column(String(255), nullable=True, comment="AS 조직명")
    is_tor = Column(Boolean, default=False, nullable=False, comment="TOR 사용 여부")
    is_vpn = Column(Boolean, default=False, nullable=False, comment="VPN 사용 여부")
    is_proxy = Column(Boolean, default=False, nullable=False, comment="프록시 사용 여부")
    dns_ptr_record = Column(String(255), nullable=True, comment="DNS PTR 레코드")
    country_mismatch = Column(
        Boolean, default=False, nullable=False, comment="국가 불일치 여부"
    )
    risk_score = Column(Integer, default=0, nullable=False, comment="위험 점수 (0-100)")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="생성 일시"
    )

    __table_args__ = (
        Index("idx_network_analysis_ip_address", "ip_address"),
        Index("idx_network_analysis_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<NetworkAnalysis(transaction_id={self.transaction_id}, ip={self.ip_address}, risk_score={self.risk_score})>"
