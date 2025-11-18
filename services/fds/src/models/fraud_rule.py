"""
FraudRule 모델

실전 사기 탐지 룰 정의를 저장한다.
"""

from datetime import datetime
import enum
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    Index,
    UUID,
    Enum,
)
from sqlalchemy.dialects.postgresql import JSONB
from src.models.base import Base
import uuid


class RuleCategory(str, enum.Enum):
    """룰 카테고리"""

    PAYMENT = "payment"  # 결제 관련
    ACCOUNT = "account"  # 계정 관련
    SHIPPING = "shipping"  # 배송지 관련


class FraudRule(Base):
    """사기 탐지 룰 모델"""

    __tablename__ = "fraud_rules"

    rule_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="룰 ID"
    )
    rule_name = Column(String(255), nullable=False, comment="룰 이름")
    rule_category = Column(Enum(RuleCategory), nullable=False, comment="룰 카테고리")
    rule_description = Column(Text, nullable=True, comment="룰 설명")
    rule_logic = Column(JSONB, nullable=True, comment="룰 실행 로직")
    risk_score = Column(Integer, nullable=False, comment="이 룰이 매칭되면 부여할 점수")
    is_active = Column(Boolean, default=True, nullable=False, comment="활성화 여부")
    priority = Column(Integer, default=0, nullable=False, comment="우선순위 (높을수록 먼저 실행)")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="생성 일시"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="수정 일시",
    )
    created_by = Column(UUID(as_uuid=True), nullable=True, comment="생성자 ID")

    __table_args__ = (
        Index("idx_fraud_rules_category", "rule_category"),
        Index("idx_fraud_rules_is_active", "is_active"),
        Index("idx_fraud_rules_priority", "priority", postgresql_using="btree"),
    )

    def __repr__(self):
        return f"<FraudRule(rule_id={self.rule_id}, name={self.rule_name}, category={self.rule_category.value})>"
