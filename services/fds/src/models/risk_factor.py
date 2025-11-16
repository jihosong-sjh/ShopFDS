"""
RiskFactor 모델: 거래의 위험 점수 산정에 기여한 개별 요인

이 모델은 각 거래에 대해 FDS가 탐지한 위험 요인을 기록합니다.
하나의 거래는 여러 위험 요인을 가질 수 있으며,
각 요인의 점수가 합산되어 최종 위험 점수가 계산됩니다.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
import enum
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class FactorType(str, enum.Enum):
    """위험 요인 유형"""

    VELOCITY_CHECK = "velocity_check"  # 단시간 내 반복 거래
    AMOUNT_THRESHOLD = "amount_threshold"  # 비정상적 고액 거래
    LOCATION_MISMATCH = "location_mismatch"  # 지역 불일치 (등록 주소 vs IP 위치)
    SUSPICIOUS_IP = "suspicious_ip"  # 악성 IP (CTI 블랙리스트)
    SUSPICIOUS_TIME = "suspicious_time"  # 비정상 시간대 거래
    ML_ANOMALY = "ml_anomaly"  # ML 모델이 탐지한 이상 패턴
    STOLEN_CARD = "stolen_card"  # 도난 카드 정보 (CTI)


class FactorSeverity(str, enum.Enum):
    """위험 요인 심각도"""

    INFO = "info"  # 정보성 (위험하지 않음)
    LOW = "low"  # 낮음 (주의 필요)
    MEDIUM = "medium"  # 중간 (경고)
    HIGH = "high"  # 높음 (위험)
    CRITICAL = "critical"  # 매우 높음 (즉시 차단)


class RiskFactor(Base):
    """
    RiskFactor 모델

    거래의 위험 점수 산정에 기여한 개별 요인을 저장합니다.
    각 Transaction은 0개 이상의 RiskFactor를 가질 수 있으며,
    이를 통해 왜 해당 거래가 위험하다고 판단되었는지 추적할 수 있습니다.
    """

    __tablename__ = "risk_factors"

    # 기본 식별자
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="고유 식별자",
    )

    # 관계 필드 (외래 키)
    transaction_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="거래 ID",
    )

    # 위험 요인 정보
    factor_type: Mapped[FactorType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="요인 유형",
    )

    factor_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="요인별 위험 점수 (0-100)",
    )

    severity: Mapped[FactorSeverity] = mapped_column(
        String(20),
        nullable=False,
        default=FactorSeverity.INFO,
        comment="심각도",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="요인 설명 (예: '동일 IP에서 5분 내 3회 거래')",
    )

    # 추가 메타데이터 (룰 ID, ML 모델 feature importance 등)
    risk_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="추가 메타데이터 (JSON 형식)",
    )

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        comment="생성 일시",
    )

    # CHECK 제약 조건
    __table_args__ = (
        CheckConstraint(
            "factor_score >= 0 AND factor_score <= 100",
            name="ck_risk_factors_score_range",
        ),
        # 복합 인덱스: 특정 거래의 모든 위험 요인 조회 최적화
        Index("ix_risk_factors_transaction_id_score", "transaction_id", "factor_score"),
        # 요인 유형별 통계 조회 최적화
        Index("ix_risk_factors_factor_type_created_at", "factor_type", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<RiskFactor(id={self.id}, "
            f"transaction_id={self.transaction_id}, "
            f"type={self.factor_type}, "
            f"score={self.factor_score}, "
            f"severity={self.severity})>"
        )

    @property
    def is_critical(self) -> bool:
        """매우 높은 위험도 여부"""
        return self.severity == FactorSeverity.CRITICAL

    @property
    def is_high_severity(self) -> bool:
        """높은 위험도 여부"""
        return self.severity in (FactorSeverity.HIGH, FactorSeverity.CRITICAL)

    @classmethod
    def determine_severity(cls, factor_score: int) -> FactorSeverity:
        """
        위험 점수에 따라 심각도를 자동 분류

        Args:
            factor_score: 요인별 위험 점수 (0-100)

        Returns:
            FactorSeverity: 심각도

        Raises:
            ValueError: 위험 점수가 0-100 범위를 벗어난 경우
        """
        if not 0 <= factor_score <= 100:
            raise ValueError(f"위험 점수는 0-100 범위여야 합니다: {factor_score}")

        if factor_score == 0:
            return FactorSeverity.INFO
        elif factor_score <= 20:
            return FactorSeverity.LOW
        elif factor_score <= 40:
            return FactorSeverity.MEDIUM
        elif factor_score <= 60:
            return FactorSeverity.HIGH
        else:  # 61-100
            return FactorSeverity.CRITICAL

    def to_dict(self) -> dict:
        """
        API 응답용 딕셔너리 변환

        Returns:
            dict: RiskFactor 정보
        """
        return {
            "id": str(self.id),
            "transaction_id": str(self.transaction_id),
            "factor_type": self.factor_type.value,
            "factor_score": self.factor_score,
            "severity": self.severity.value,
            "description": self.description,
            "metadata": self.risk_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
