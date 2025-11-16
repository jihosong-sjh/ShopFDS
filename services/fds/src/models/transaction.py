"""
Transaction 모델: FDS가 평가하는 개별 거래 이벤트

이 모델은 이커머스 플랫폼에서 발생하는 모든 거래를 기록하고,
FDS 시스템이 평가한 위험 점수와 대응 결정을 저장합니다.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4
import enum
from sqlalchemy import (
    CheckConstraint,
    Index,
    Integer,
    Text,
    Numeric,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class DeviceType(str, enum.Enum):
    """디바이스 유형"""

    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    UNKNOWN = "unknown"


class RiskLevel(str, enum.Enum):
    """위험 수준"""

    LOW = "low"  # 위험 점수 0-30: 자동 승인
    MEDIUM = "medium"  # 위험 점수 40-70: 추가 인증 요구
    HIGH = "high"  # 위험 점수 80-100: 자동 차단


class EvaluationStatus(str, enum.Enum):
    """평가 상태"""

    EVALUATING = "evaluating"  # 평가 중
    APPROVED = "approved"  # 승인됨
    BLOCKED = "blocked"  # 차단됨
    MANUAL_REVIEW = "manual_review"  # 수동 검토 필요


class Transaction(Base):
    """
    Transaction 모델

    FDS가 평가하는 개별 거래 이벤트를 저장합니다.
    각 주문(Order)마다 하나의 Transaction이 생성되며,
    위험 점수와 평가 결과를 기록합니다.
    """

    __tablename__ = "transactions"

    # 기본 식별자
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="고유 식별자",
    )

    # 관계 필드 (외래 키)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="사용자 ID",
    )

    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        comment="주문 ID (1:1 관계)",
    )

    # 거래 정보
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="거래 금액 (KRW)",
    )

    # 접속 정보
    ip_address: Mapped[str] = mapped_column(
        INET,
        nullable=False,
        index=True,
        comment="접속 IP 주소",
    )

    user_agent: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="User-Agent 헤더 (디바이스 정보)",
    )

    device_type: Mapped[DeviceType] = mapped_column(
        SQLEnum(DeviceType, name="device_type", create_constraint=True),
        nullable=False,
        comment="디바이스 유형",
    )

    # 지리적 위치 정보 (IP 기반)
    geolocation: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="IP 기반 지리적 위치 (country, city, lat, lon)",
    )

    # 위험 평가 결과
    risk_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="위험 점수 (0-100)",
    )

    risk_level: Mapped[RiskLevel] = mapped_column(
        SQLEnum(RiskLevel, name="risk_level", create_constraint=True),
        nullable=False,
        index=True,
        comment="위험 수준 (low/medium/high)",
    )

    evaluation_status: Mapped[EvaluationStatus] = mapped_column(
        SQLEnum(EvaluationStatus, name="evaluation_status", create_constraint=True),
        nullable=False,
        default=EvaluationStatus.EVALUATING,
        index=True,
        comment="평가 상태",
    )

    # 성능 지표
    evaluation_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="FDS 평가 소요 시간 (ms) - 목표: 100ms 이내",
    )

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="거래 발생 일시",
    )

    evaluated_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="평가 완료 일시",
    )

    # CHECK 제약 조건
    __table_args__ = (
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="ck_transactions_risk_score_range",
        ),
        CheckConstraint(
            "evaluation_time_ms >= 0",
            name="ck_transactions_evaluation_time_positive",
        ),
        # 복합 인덱스
        Index(
            "ix_transactions_created_at_desc",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        Index("ix_transactions_user_id_created_at", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, "
            f"order_id={self.order_id}, "
            f"risk_score={self.risk_score}, "
            f"risk_level={self.risk_level}, "
            f"status={self.evaluation_status})>"
        )

    @property
    def is_low_risk(self) -> bool:
        """저위험 거래 여부 (자동 승인)"""
        return self.risk_level == RiskLevel.LOW

    @property
    def is_medium_risk(self) -> bool:
        """중위험 거래 여부 (추가 인증 필요)"""
        return self.risk_level == RiskLevel.MEDIUM

    @property
    def is_high_risk(self) -> bool:
        """고위험 거래 여부 (자동 차단)"""
        return self.risk_level == RiskLevel.HIGH

    @classmethod
    def calculate_risk_level(cls, risk_score: int) -> RiskLevel:
        """
        위험 점수에 따라 위험 수준을 자동 분류

        Args:
            risk_score: 위험 점수 (0-100)

        Returns:
            RiskLevel: 위험 수준

        Raises:
            ValueError: 위험 점수가 0-100 범위를 벗어난 경우
        """
        if not 0 <= risk_score <= 100:
            raise ValueError(f"위험 점수는 0-100 범위여야 합니다: {risk_score}")

        if risk_score <= 30:
            return RiskLevel.LOW
        elif risk_score <= 70:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH

    @classmethod
    def determine_evaluation_status(cls, risk_level: RiskLevel) -> EvaluationStatus:
        """
        위험 수준에 따라 평가 상태를 결정

        Args:
            risk_level: 위험 수준

        Returns:
            EvaluationStatus: 평가 상태
        """
        if risk_level == RiskLevel.LOW:
            return EvaluationStatus.APPROVED
        elif risk_level == RiskLevel.MEDIUM:
            return EvaluationStatus.APPROVED  # 추가 인증 후 승인
        else:  # HIGH
            return EvaluationStatus.BLOCKED
