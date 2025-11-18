"""
FDS 서비스 데이터 모델

이 패키지는 FDS 서비스의 모든 데이터베이스 모델을 포함합니다.
"""

from .base import Base, TimestampMixin, get_db, init_db, drop_db, close_db
from .transaction import (
    Transaction,
    DeviceType,
    RiskLevel,
    EvaluationStatus,
)
from .risk_factor import (
    RiskFactor,
    FactorType,
    FactorSeverity,
)
from .detection_rule import (
    DetectionRule,
    RuleType,
    RulePriority,
)
from .threat_intelligence import (
    ThreatIntelligence,
    ThreatType,
    ThreatLevel,
    ThreatSource,
)
from .review_queue import (
    ReviewQueue,
    ReviewStatus,
    ReviewDecision,
)
from .device_fingerprint import DeviceFingerprint
from .behavior_pattern import BehaviorPattern
from .network_analysis import NetworkAnalysis
from .fraud_rule import FraudRule, RuleCategory
from .rule_execution import RuleExecution
from .xai_explanation import XAIExplanation
from .external_service_log import ExternalServiceLog, ServiceName
from .blacklist_entry import BlacklistEntry, BlacklistEntryType

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "get_db",
    "init_db",
    "drop_db",
    "close_db",
    # Transaction
    "Transaction",
    "DeviceType",
    "RiskLevel",
    "EvaluationStatus",
    # RiskFactor
    "RiskFactor",
    "FactorType",
    "FactorSeverity",
    # DetectionRule
    "DetectionRule",
    "RuleType",
    "RulePriority",
    # ReviewQueue
    "ReviewQueue",
    "ReviewStatus",
    "ReviewDecision",
    # ThreatIntelligence
    "ThreatIntelligence",
    "ThreatType",
    "ThreatLevel",
    "ThreatSource",
    # Advanced FDS - Phase 2
    "DeviceFingerprint",
    "BehaviorPattern",
    "NetworkAnalysis",
    "FraudRule",
    "RuleCategory",
    "RuleExecution",
    "XAIExplanation",
    "ExternalServiceLog",
    "ServiceName",
    "BlacklistEntry",
    "BlacklistEntryType",
]
