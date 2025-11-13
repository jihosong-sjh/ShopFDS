"""
ThreatIntelligence 모델: 외부 CTI 및 자체 블랙리스트

이 모델은 악성 IP, 이메일 도메인, 카드 BIN 등의 위협 정보를 저장합니다.
외부 CTI 소스(AbuseIPDB 등)와 내부 블랙리스트를 통합 관리합니다.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
import enum
from sqlalchemy import (
    Boolean,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base, TimestampMixin


class ThreatType(str, enum.Enum):
    """위협 유형"""
    IP = "ip"                    # IP 주소
    EMAIL_DOMAIN = "email_domain"  # 이메일 도메인
    CARD_BIN = "card_bin"        # 카드 BIN (처음 6자리)


class ThreatLevel(str, enum.Enum):
    """위협 수준"""
    LOW = "low"        # 낮음 (의심 수준)
    MEDIUM = "medium"  # 중간 (주의 필요)
    HIGH = "high"      # 높음 (자동 차단 대상)


class ThreatSource(str, enum.Enum):
    """위협 정보 출처"""
    ABUSEIPDB = "abuseipdb"      # AbuseIPDB API
    INTERNAL = "internal"         # 내부 보안팀 등록
    VIRUSTOTAL = "virustotal"    # VirusTotal (향후 확장)
    MANUAL = "manual"            # 수동 등록


class ThreatIntelligence(Base, TimestampMixin):
    """
    ThreatIntelligence 모델

    외부 CTI 소스 및 자체 블랙리스트를 통합 관리합니다.
    Redis 캐싱을 통해 O(1) 조회 성능을 보장합니다.
    """

    __tablename__ = "threat_intelligence"

    # 기본 식별자
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="고유 식별자",
    )

    # 위협 정보
    threat_type: Mapped[ThreatType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="위협 유형 (IP, 이메일 도메인, 카드 BIN)",
    )

    value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="위협 값 (IP 주소, 이메일 도메인, 카드 BIN)",
    )

    threat_level: Mapped[ThreatLevel] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="위협 수준 (low, medium, high)",
    )

    source: Mapped[ThreatSource] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="출처 (AbuseIPDB, internal 등)",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="위협 설명 및 근거",
    )

    # 만료 및 활성화
    registered_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        comment="등록 일시",
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="만료 일시 (NULL이면 영구)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="활성화 여부",
    )

    # CTI 추가 메타데이터 (JSON)
    metadata: Mapped[Optional[dict]] = mapped_column(
        nullable=True,
        comment="추가 메타데이터 (신뢰도 점수, 카테고리 등)",
    )

    # 적용 통계
    times_blocked: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="이 위협으로 인해 차단된 거래 횟수",
    )

    last_blocked_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="마지막 차단 일시",
    )

    # 테이블 제약 조건 및 인덱스
    __table_args__ = (
        # UNIQUE 제약: (threat_type, value) 조합은 고유해야 함
        UniqueConstraint(
            "threat_type",
            "value",
            name="uq_threat_intelligence_type_value",
        ),
        # 복합 인덱스: 활성화된 위협 조회 최적화
        Index(
            "ix_threat_intelligence_active_type",
            "is_active",
            "threat_type",
        ),
        # 만료 일시 인덱스: 만료된 항목 자동 삭제용
        Index(
            "ix_threat_intelligence_expires_at",
            "expires_at",
        ),
        # 위협 수준별 조회 최적화
        Index(
            "ix_threat_intelligence_level_active",
            "threat_level",
            "is_active",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ThreatIntelligence(id={self.id}, "
            f"type={self.threat_type}, "
            f"value='{self.value}', "
            f"level={self.threat_level}, "
            f"source={self.source})>"
        )

    @property
    def is_expired(self) -> bool:
        """만료 여부 확인"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_high_threat(self) -> bool:
        """높은 위협 수준 여부"""
        return self.threat_level == ThreatLevel.HIGH

    @property
    def redis_key(self) -> str:
        """
        Redis 캐싱용 키 생성

        Returns:
            str: Redis 키 (예: "threat:ip:192.168.1.1")
        """
        return f"threat:{self.threat_type.value}:{self.value}"

    def increment_block_count(self) -> None:
        """
        차단 횟수 증가 및 마지막 차단 시간 갱신
        """
        self.times_blocked += 1
        self.last_blocked_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """
        API 응답용 딕셔너리 변환

        Returns:
            dict: ThreatIntelligence 정보
        """
        return {
            "id": str(self.id),
            "threat_type": self.threat_type.value,
            "value": self.value,
            "threat_level": self.threat_level.value,
            "source": self.source.value,
            "description": self.description,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "metadata": self.metadata,
            "times_blocked": self.times_blocked,
            "last_blocked_at": self.last_blocked_at.isoformat() if self.last_blocked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_cache_dict(self) -> dict:
        """
        Redis 캐싱용 경량화된 딕셔너리 변환

        Returns:
            dict: 캐싱에 필요한 최소 정보
        """
        return {
            "threat_type": self.threat_type.value,
            "value": self.value,
            "threat_level": self.threat_level.value,
            "source": self.source.value,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def create_ip_threat(
        cls,
        ip_address: str,
        threat_level: ThreatLevel,
        source: ThreatSource,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> "ThreatIntelligence":
        """
        IP 위협 정보 생성 헬퍼 메서드

        Args:
            ip_address: IP 주소
            threat_level: 위협 수준
            source: 출처
            description: 위협 설명
            expires_at: 만료 일시
            metadata: 추가 메타데이터

        Returns:
            ThreatIntelligence: 생성된 위협 정보 인스턴스
        """
        return cls(
            threat_type=ThreatType.IP,
            value=ip_address,
            threat_level=threat_level,
            source=source,
            description=description,
            expires_at=expires_at,
            metadata=metadata,
        )

    @classmethod
    def create_email_domain_threat(
        cls,
        email_domain: str,
        threat_level: ThreatLevel,
        source: ThreatSource,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> "ThreatIntelligence":
        """
        이메일 도메인 위협 정보 생성 헬퍼 메서드

        Args:
            email_domain: 이메일 도메인
            threat_level: 위협 수준
            source: 출처
            description: 위협 설명
            expires_at: 만료 일시
            metadata: 추가 메타데이터

        Returns:
            ThreatIntelligence: 생성된 위협 정보 인스턴스
        """
        return cls(
            threat_type=ThreatType.EMAIL_DOMAIN,
            value=email_domain,
            threat_level=threat_level,
            source=source,
            description=description,
            expires_at=expires_at,
            metadata=metadata,
        )

    @classmethod
    def create_card_bin_threat(
        cls,
        card_bin: str,
        threat_level: ThreatLevel,
        source: ThreatSource,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> "ThreatIntelligence":
        """
        카드 BIN 위협 정보 생성 헬퍼 메서드

        Args:
            card_bin: 카드 BIN (처음 6자리)
            threat_level: 위협 수준
            source: 출처
            description: 위협 설명
            expires_at: 만료 일시
            metadata: 추가 메타데이터

        Returns:
            ThreatIntelligence: 생성된 위협 정보 인스턴스
        """
        return cls(
            threat_type=ThreatType.CARD_BIN,
            value=card_bin,
            threat_level=threat_level,
            source=source,
            description=description,
            expires_at=expires_at,
            metadata=metadata,
        )
