"""
DetectionRule 모델: FDS가 사용하는 룰 기반 탐지 규칙

이 모델은 보안팀이 동적으로 생성/수정할 수 있는 탐지 룰을 저장합니다.
코드 배포 없이 데이터베이스에서 활성 룰을 로드하여 적용할 수 있습니다.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
import enum
from sqlalchemy import (
    Boolean,
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

from .base import Base, TimestampMixin


class RuleType(str, enum.Enum):
    """룰 유형"""
    VELOCITY = "velocity"              # 단시간 내 반복 거래
    THRESHOLD = "threshold"            # 금액/빈도 임계값
    BLACKLIST = "blacklist"            # 블랙리스트 (IP, 이메일, 카드 BIN)
    LOCATION = "location"              # 지역 불일치
    TIME_PATTERN = "time_pattern"      # 시간 패턴 (비정상 시간대)
    DEVICE_PATTERN = "device_pattern"  # 디바이스 패턴 (동일 계정에서 여러 디바이스)


class RulePriority(enum.IntEnum):
    """룰 우선순위 (높을수록 먼저 평가)"""
    CRITICAL = 100   # 매우 높음 (블랙리스트 등)
    HIGH = 75        # 높음
    MEDIUM = 50      # 중간 (기본값)
    LOW = 25         # 낮음
    INFO = 0         # 정보성


class DetectionRule(Base, TimestampMixin):
    """
    DetectionRule 모델

    FDS가 사용하는 룰 기반 탐지 규칙을 저장합니다.
    보안팀은 이 테이블을 통해 코드 배포 없이 동적으로 룰을 추가/수정할 수 있습니다.
    """

    __tablename__ = "detection_rules"

    # 기본 식별자
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="고유 식별자",
    )

    # 룰 기본 정보
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="룰 이름 (예: '5분 내 3회 거래 차단')",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="룰 설명",
    )

    rule_type: Mapped[RuleType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="룰 유형",
    )

    # 룰 조건 (JSON 형식)
    condition: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="룰 조건 (JSON 형식)",
    )

    # 위험 점수 가중치
    risk_score_weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        comment="위험 점수 가중치 (0-100)",
    )

    # 활성화 상태
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="활성화 여부",
    )

    # 우선순위
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=RulePriority.MEDIUM,
        comment="우선순위 (높을수록 먼저 평가)",
    )

    # 생성자 정보
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="생성자 (보안팀 사용자 ID)",
    )

    # 적용 통계
    times_triggered: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="룰이 트리거된 횟수",
    )

    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="마지막 트리거 일시",
    )

    # CHECK 제약 조건
    __table_args__ = (
        CheckConstraint(
            "risk_score_weight >= 0 AND risk_score_weight <= 100",
            name="ck_detection_rules_weight_range",
        ),
        CheckConstraint(
            "priority >= 0 AND priority <= 100",
            name="ck_detection_rules_priority_range",
        ),
        CheckConstraint(
            "times_triggered >= 0",
            name="ck_detection_rules_times_triggered_positive",
        ),
        # 복합 인덱스: 활성화된 룰을 우선순위 순으로 조회
        Index(
            "ix_detection_rules_active_priority",
            "is_active",
            "priority",
            postgresql_ops={"priority": "DESC"},
        ),
        # 룰 유형별 조회 최적화
        Index("ix_detection_rules_type_active", "rule_type", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<DetectionRule(id={self.id}, "
            f"name='{self.name}', "
            f"type={self.rule_type}, "
            f"active={self.is_active}, "
            f"priority={self.priority})>"
        )

    @property
    def is_critical_priority(self) -> bool:
        """매우 높은 우선순위 여부"""
        return self.priority >= RulePriority.CRITICAL

    @property
    def is_high_priority(self) -> bool:
        """높은 우선순위 여부"""
        return self.priority >= RulePriority.HIGH

    def increment_trigger_count(self) -> None:
        """
        룰 트리거 횟수 증가 및 마지막 트리거 시간 갱신
        """
        self.times_triggered += 1
        self.last_triggered_at = datetime.utcnow()

    def validate_condition(self) -> bool:
        """
        룰 조건 JSON의 유효성 검증

        Returns:
            bool: 조건이 유효하면 True, 그렇지 않으면 False

        Note:
            각 rule_type에 따라 필수 필드가 다릅니다:
            - velocity: window_seconds, max_transactions, scope
            - threshold: field, operator, value
            - blacklist: type, values
            - location: max_distance_km
            - time_pattern: start_hour, end_hour
            - device_pattern: max_devices
        """
        if not isinstance(self.condition, dict):
            return False

        required_fields_by_type = {
            RuleType.VELOCITY: ["window_seconds", "max_transactions", "scope"],
            RuleType.THRESHOLD: ["field", "operator", "value"],
            RuleType.BLACKLIST: ["type", "values"],
            RuleType.LOCATION: ["max_distance_km"],
            RuleType.TIME_PATTERN: ["start_hour", "end_hour"],
            RuleType.DEVICE_PATTERN: ["max_devices"],
        }

        required_fields = required_fields_by_type.get(self.rule_type, [])
        return all(field in self.condition for field in required_fields)

    def to_dict(self) -> dict:
        """
        API 응답용 딕셔너리 변환

        Returns:
            dict: DetectionRule 정보
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type.value,
            "condition": self.condition,
            "risk_score_weight": self.risk_score_weight,
            "is_active": self.is_active,
            "priority": self.priority,
            "created_by": str(self.created_by) if self.created_by else None,
            "times_triggered": self.times_triggered,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def create_velocity_rule(
        cls,
        name: str,
        window_seconds: int,
        max_transactions: int,
        scope: str,
        risk_score_weight: int = 40,
        priority: int = RulePriority.HIGH,
    ) -> "DetectionRule":
        """
        Velocity Check 룰 생성 헬퍼 메서드

        Args:
            name: 룰 이름
            window_seconds: 시간 윈도우 (초)
            max_transactions: 최대 거래 횟수
            scope: 적용 범위 (ip_address, user_id, card_bin)
            risk_score_weight: 위험 점수 가중치
            priority: 우선순위

        Returns:
            DetectionRule: 생성된 룰 인스턴스
        """
        return cls(
            name=name,
            rule_type=RuleType.VELOCITY,
            condition={
                "window_seconds": window_seconds,
                "max_transactions": max_transactions,
                "scope": scope,
            },
            risk_score_weight=risk_score_weight,
            priority=priority,
        )

    @classmethod
    def create_threshold_rule(
        cls,
        name: str,
        field: str,
        operator: str,
        value: float,
        risk_score_weight: int = 30,
        priority: int = RulePriority.MEDIUM,
    ) -> "DetectionRule":
        """
        Threshold 룰 생성 헬퍼 메서드

        Args:
            name: 룰 이름
            field: 비교할 필드 (amount, transaction_count 등)
            operator: 비교 연산자 (gt, gte, lt, lte, eq)
            value: 임계값
            risk_score_weight: 위험 점수 가중치
            priority: 우선순위

        Returns:
            DetectionRule: 생성된 룰 인스턴스
        """
        return cls(
            name=name,
            rule_type=RuleType.THRESHOLD,
            condition={
                "field": field,
                "operator": operator,
                "value": value,
            },
            risk_score_weight=risk_score_weight,
            priority=priority,
        )
