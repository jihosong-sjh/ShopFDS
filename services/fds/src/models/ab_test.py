"""
ABTest 모델: A/B 테스트 설정 및 결과 저장

이 모델은 보안팀이 FDS 룰이나 ML 모델의 성능을 비교하기 위한
A/B 테스트를 설정하고 결과를 추적합니다.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
import enum
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SQLEnum,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base, TimestampMixin


class ABTestStatus(str, enum.Enum):
    """A/B 테스트 상태"""
    DRAFT = "draft"              # 초안 (아직 시작 안 됨)
    RUNNING = "running"          # 진행 중
    PAUSED = "paused"            # 일시 중지
    COMPLETED = "completed"      # 완료
    CANCELLED = "cancelled"      # 취소됨


class ABTestType(str, enum.Enum):
    """A/B 테스트 유형"""
    RULE = "rule"                # 룰 비교 (기존 룰 vs 새 룰)
    MODEL = "model"              # ML 모델 비교 (기존 모델 vs 새 모델)
    THRESHOLD = "threshold"      # 임계값 비교 (위험 점수 기준 변경)
    HYBRID = "hybrid"            # 복합 테스트


class ABTest(Base, TimestampMixin):
    """
    ABTest 모델

    FDS 룰이나 ML 모델의 A/B 테스트를 관리합니다.
    실시간 거래를 두 그룹(A/B)으로 나누어 각기 다른 로직을 적용하고
    성능 지표(정탐률, 오탐률, 처리 시간)를 비교합니다.
    """

    __tablename__ = "ab_tests"

    # 기본 식별자
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="고유 식별자",
    )

    # 테스트 기본 정보
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="테스트 이름 (예: 'Velocity Rule v2 vs v1')",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="테스트 설명 및 목적",
    )

    test_type: Mapped[ABTestType] = mapped_column(
        SQLEnum(ABTestType, name="ab_test_type", create_type=True),
        nullable=False,
        index=True,
        comment="테스트 유형",
    )

    status: Mapped[ABTestStatus] = mapped_column(
        SQLEnum(ABTestStatus, name="ab_test_status", create_type=True),
        nullable=False,
        default=ABTestStatus.DRAFT,
        index=True,
        comment="테스트 상태",
    )

    # 그룹 A/B 설정
    group_a_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="그룹 A 설정 (기존 룰/모델 ID 또는 파라미터)",
    )

    group_b_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="그룹 B 설정 (새 룰/모델 ID 또는 파라미터)",
    )

    # 트래픽 분할 비율 (%)
    traffic_split_percentage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        comment="그룹 B에 할당할 트래픽 비율 (0-100%, 나머지는 그룹 A)",
    )

    # 테스트 기간
    start_time: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="테스트 시작 일시",
    )

    end_time: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="테스트 종료 일시",
    )

    planned_duration_hours: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="계획된 테스트 기간 (시간)",
    )

    # 생성자 정보
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="생성자 (보안팀 사용자 ID)",
    )

    # 성과 지표 - 그룹 A
    group_a_total_transactions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="그룹 A 총 거래 수",
    )

    group_a_true_positives: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="그룹 A 정탐 수 (실제 사기 거래를 정확히 탐지)",
    )

    group_a_false_positives: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="그룹 A 오탐 수 (정상 거래를 사기로 탐지)",
    )

    group_a_false_negatives: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="그룹 A 미탐 수 (사기 거래를 탐지 못함)",
    )

    group_a_avg_evaluation_time_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="그룹 A 평균 평가 시간 (ms)",
    )

    # 성과 지표 - 그룹 B
    group_b_total_transactions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="그룹 B 총 거래 수",
    )

    group_b_true_positives: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="그룹 B 정탐 수",
    )

    group_b_false_positives: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="그룹 B 오탐 수",
    )

    group_b_false_negatives: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="그룹 B 미탐 수",
    )

    group_b_avg_evaluation_time_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="그룹 B 평균 평가 시간 (ms)",
    )

    # 승자 결정
    winner: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="승자 (A, B, 또는 무승부)",
    )

    confidence_level: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="통계적 신뢰 수준 (0-1, 예: 0.95 = 95% 신뢰도)",
    )

    # CHECK 제약 조건
    __table_args__ = (
        CheckConstraint(
            "traffic_split_percentage >= 0 AND traffic_split_percentage <= 100",
            name="ck_ab_tests_traffic_split_range",
        ),
        CheckConstraint(
            "planned_duration_hours IS NULL OR planned_duration_hours > 0",
            name="ck_ab_tests_duration_positive",
        ),
        CheckConstraint(
            "group_a_total_transactions >= 0",
            name="ck_ab_tests_group_a_total_positive",
        ),
        CheckConstraint(
            "group_b_total_transactions >= 0",
            name="ck_ab_tests_group_b_total_positive",
        ),
        CheckConstraint(
            "confidence_level IS NULL OR (confidence_level >= 0 AND confidence_level <= 1)",
            name="ck_ab_tests_confidence_range",
        ),
        CheckConstraint(
            "winner IS NULL OR winner IN ('A', 'B', 'tie')",
            name="ck_ab_tests_winner_values",
        ),
        # 복합 인덱스: 활성 테스트 조회
        Index("ix_ab_tests_status_start_time", "status", "start_time"),
        # 테스트 유형별 조회
        Index("ix_ab_tests_type_status", "test_type", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ABTest(id={self.id}, "
            f"name='{self.name}', "
            f"type={self.test_type}, "
            f"status={self.status}, "
            f"split={self.traffic_split_percentage}%)>"
        )

    @property
    def is_running(self) -> bool:
        """테스트가 현재 진행 중인지 확인"""
        return self.status == ABTestStatus.RUNNING

    @property
    def is_completed(self) -> bool:
        """테스트가 완료되었는지 확인"""
        return self.status == ABTestStatus.COMPLETED

    @property
    def duration_hours(self) -> Optional[float]:
        """실제 테스트 진행 시간 (시간)"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() / 3600
        elif self.start_time and self.status == ABTestStatus.RUNNING:
            delta = datetime.utcnow() - self.start_time
            return delta.total_seconds() / 3600
        return None

    def calculate_precision(self, group: str) -> Optional[float]:
        """
        정밀도 계산: TP / (TP + FP)

        정밀도는 "탐지한 것 중 실제 사기 거래의 비율"을 의미합니다.

        Args:
            group: 'A' 또는 'B'

        Returns:
            float: 정밀도 (0-1), 계산 불가 시 None
        """
        if group == 'A':
            tp = self.group_a_true_positives
            fp = self.group_a_false_positives
        else:
            tp = self.group_b_true_positives
            fp = self.group_b_false_positives

        if tp + fp == 0:
            return None
        return tp / (tp + fp)

    def calculate_recall(self, group: str) -> Optional[float]:
        """
        재현율 계산: TP / (TP + FN)

        재현율은 "실제 사기 거래 중 탐지한 비율"을 의미합니다.

        Args:
            group: 'A' 또는 'B'

        Returns:
            float: 재현율 (0-1), 계산 불가 시 None
        """
        if group == 'A':
            tp = self.group_a_true_positives
            fn = self.group_a_false_negatives
        else:
            tp = self.group_b_true_positives
            fn = self.group_b_false_negatives

        if tp + fn == 0:
            return None
        return tp / (tp + fn)

    def calculate_f1_score(self, group: str) -> Optional[float]:
        """
        F1 스코어 계산: 2 * (정밀도 * 재현율) / (정밀도 + 재현율)

        F1 스코어는 정밀도와 재현율의 조화 평균입니다.

        Args:
            group: 'A' 또는 'B'

        Returns:
            float: F1 스코어 (0-1), 계산 불가 시 None
        """
        precision = self.calculate_precision(group)
        recall = self.calculate_recall(group)

        if precision is None or recall is None:
            return None
        if precision + recall == 0:
            return None

        return 2 * (precision * recall) / (precision + recall)

    def calculate_false_positive_rate(self, group: str) -> Optional[float]:
        """
        오탐률 계산: FP / (FP + TN)

        참고: TN(True Negative)은 별도로 추적하지 않으므로,
        근사값으로 FP / 총 거래 수를 사용합니다.

        Args:
            group: 'A' 또는 'B'

        Returns:
            float: 오탐률 (0-1), 계산 불가 시 None
        """
        if group == 'A':
            fp = self.group_a_false_positives
            total = self.group_a_total_transactions
        else:
            fp = self.group_b_false_positives
            total = self.group_b_total_transactions

        if total == 0:
            return None
        return fp / total

    def increment_transaction(
        self,
        group: str,
        is_true_positive: bool = False,
        is_false_positive: bool = False,
        is_false_negative: bool = False,
        evaluation_time_ms: Optional[float] = None,
    ) -> None:
        """
        거래 결과 집계

        Args:
            group: 'A' 또는 'B'
            is_true_positive: 정탐 여부
            is_false_positive: 오탐 여부
            is_false_negative: 미탐 여부
            evaluation_time_ms: 평가 소요 시간 (ms)
        """
        if group == 'A':
            self.group_a_total_transactions += 1
            if is_true_positive:
                self.group_a_true_positives += 1
            if is_false_positive:
                self.group_a_false_positives += 1
            if is_false_negative:
                self.group_a_false_negatives += 1

            # 평균 평가 시간 갱신 (이동 평균)
            if evaluation_time_ms is not None:
                if self.group_a_avg_evaluation_time_ms is None:
                    self.group_a_avg_evaluation_time_ms = evaluation_time_ms
                else:
                    n = self.group_a_total_transactions
                    self.group_a_avg_evaluation_time_ms = (
                        (self.group_a_avg_evaluation_time_ms * (n - 1) + evaluation_time_ms) / n
                    )
        else:
            self.group_b_total_transactions += 1
            if is_true_positive:
                self.group_b_true_positives += 1
            if is_false_positive:
                self.group_b_false_positives += 1
            if is_false_negative:
                self.group_b_false_negatives += 1

            if evaluation_time_ms is not None:
                if self.group_b_avg_evaluation_time_ms is None:
                    self.group_b_avg_evaluation_time_ms = evaluation_time_ms
                else:
                    n = self.group_b_total_transactions
                    self.group_b_avg_evaluation_time_ms = (
                        (self.group_b_avg_evaluation_time_ms * (n - 1) + evaluation_time_ms) / n
                    )

    def start(self) -> None:
        """테스트 시작"""
        if self.status != ABTestStatus.DRAFT:
            raise ValueError(f"Cannot start test in {self.status} status")

        self.status = ABTestStatus.RUNNING
        self.start_time = datetime.utcnow()

    def pause(self) -> None:
        """테스트 일시 중지"""
        if self.status != ABTestStatus.RUNNING:
            raise ValueError(f"Cannot pause test in {self.status} status")

        self.status = ABTestStatus.PAUSED

    def resume(self) -> None:
        """테스트 재개"""
        if self.status != ABTestStatus.PAUSED:
            raise ValueError(f"Cannot resume test in {self.status} status")

        self.status = ABTestStatus.RUNNING

    def complete(self, winner: Optional[str] = None, confidence: Optional[float] = None) -> None:
        """
        테스트 완료

        Args:
            winner: 승자 ('A', 'B', 'tie'), None이면 자동 계산
            confidence: 신뢰 수준 (0-1)
        """
        if self.status not in [ABTestStatus.RUNNING, ABTestStatus.PAUSED]:
            raise ValueError(f"Cannot complete test in {self.status} status")

        self.status = ABTestStatus.COMPLETED
        self.end_time = datetime.utcnow()

        # 승자 결정 (제공되지 않은 경우 F1 스코어 기준)
        if winner is not None:
            self.winner = winner
        else:
            f1_a = self.calculate_f1_score('A')
            f1_b = self.calculate_f1_score('B')

            if f1_a is not None and f1_b is not None:
                if abs(f1_a - f1_b) < 0.01:  # 1% 이내 차이면 무승부
                    self.winner = 'tie'
                elif f1_a > f1_b:
                    self.winner = 'A'
                else:
                    self.winner = 'B'

        if confidence is not None:
            self.confidence_level = confidence

    def cancel(self) -> None:
        """테스트 취소"""
        if self.status == ABTestStatus.COMPLETED:
            raise ValueError("Cannot cancel completed test")

        self.status = ABTestStatus.CANCELLED
        self.end_time = datetime.utcnow()

    def to_dict(self) -> dict:
        """
        API 응답용 딕셔너리 변환

        Returns:
            dict: ABTest 정보 및 성과 지표
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "test_type": self.test_type.value,
            "status": self.status.value,
            "group_a_config": self.group_a_config,
            "group_b_config": self.group_b_config,
            "traffic_split_percentage": self.traffic_split_percentage,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "planned_duration_hours": self.planned_duration_hours,
            "actual_duration_hours": self.duration_hours,
            "created_by": str(self.created_by) if self.created_by else None,
            "group_a": {
                "total_transactions": self.group_a_total_transactions,
                "true_positives": self.group_a_true_positives,
                "false_positives": self.group_a_false_positives,
                "false_negatives": self.group_a_false_negatives,
                "avg_evaluation_time_ms": self.group_a_avg_evaluation_time_ms,
                "precision": self.calculate_precision('A'),
                "recall": self.calculate_recall('A'),
                "f1_score": self.calculate_f1_score('A'),
                "false_positive_rate": self.calculate_false_positive_rate('A'),
            },
            "group_b": {
                "total_transactions": self.group_b_total_transactions,
                "true_positives": self.group_b_true_positives,
                "false_positives": self.group_b_false_positives,
                "false_negatives": self.group_b_false_negatives,
                "avg_evaluation_time_ms": self.group_b_avg_evaluation_time_ms,
                "precision": self.calculate_precision('B'),
                "recall": self.calculate_recall('B'),
                "f1_score": self.calculate_f1_score('B'),
                "false_positive_rate": self.calculate_false_positive_rate('B'),
            },
            "winner": self.winner,
            "confidence_level": self.confidence_level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def create_rule_test(
        cls,
        name: str,
        description: str,
        group_a_rule_id: UUID,
        group_b_rule_id: UUID,
        traffic_split: int = 50,
        duration_hours: Optional[int] = 24,
        created_by: Optional[UUID] = None,
    ) -> "ABTest":
        """
        룰 비교 A/B 테스트 생성 헬퍼 메서드

        Args:
            name: 테스트 이름
            description: 테스트 설명
            group_a_rule_id: 그룹 A 룰 ID (기존 룰)
            group_b_rule_id: 그룹 B 룰 ID (새 룰)
            traffic_split: 그룹 B 트래픽 비율 (%)
            duration_hours: 계획된 테스트 기간 (시간)
            created_by: 생성자 ID

        Returns:
            ABTest: 생성된 테스트 인스턴스
        """
        return cls(
            name=name,
            description=description,
            test_type=ABTestType.RULE,
            group_a_config={"rule_id": str(group_a_rule_id)},
            group_b_config={"rule_id": str(group_b_rule_id)},
            traffic_split_percentage=traffic_split,
            planned_duration_hours=duration_hours,
            created_by=created_by,
        )
