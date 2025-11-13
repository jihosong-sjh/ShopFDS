"""
위험 점수 산정 엔진 (Risk Scorer)

여러 위험 요인의 점수를 가중치에 따라 합산하여 최종 위험 점수를 계산합니다.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal

from models import RiskFactor, FactorType, FactorSeverity, RiskLevel
from engines.rule_engine import RuleEvaluationResult


class RiskScoreConfig:
    """
    위험 점수 산정 설정

    각 요인 유형별 가중치 및 점수 계산 방식을 정의합니다.
    """

    # 요인 유형별 기본 가중치
    DEFAULT_WEIGHTS = {
        FactorType.VELOCITY_CHECK: 1.0,       # 단시간 내 반복 거래
        FactorType.AMOUNT_THRESHOLD: 0.8,     # 비정상적 고액 거래
        FactorType.LOCATION_MISMATCH: 0.9,    # 지역 불일치
        FactorType.SUSPICIOUS_IP: 1.2,        # 악성 IP (CTI)
        FactorType.SUSPICIOUS_TIME: 0.6,      # 비정상 시간대
        FactorType.ML_ANOMALY: 1.1,           # ML 이상 탐지
        FactorType.STOLEN_CARD: 1.5,          # 도난 카드
    }

    # 심각도별 가중치 배율
    SEVERITY_MULTIPLIERS = {
        FactorSeverity.INFO: 0.5,
        FactorSeverity.LOW: 0.7,
        FactorSeverity.MEDIUM: 1.0,
        FactorSeverity.HIGH: 1.3,
        FactorSeverity.CRITICAL: 1.5,
    }

    # 위험 수준 임계값
    RISK_LEVEL_THRESHOLDS = {
        RiskLevel.LOW: (0, 30),        # 0-30: 저위험 (자동 승인)
        RiskLevel.MEDIUM: (40, 70),    # 40-70: 중위험 (추가 인증)
        RiskLevel.HIGH: (80, 100),     # 80-100: 고위험 (자동 차단)
    }

    # 31-39, 71-79는 경계 구간 (보수적으로 상위 등급으로 분류)


class RiskScorer:
    """
    위험 점수 산정 엔진

    여러 위험 요인을 종합하여 최종 위험 점수를 계산합니다.
    """

    def __init__(self, config: Optional[RiskScoreConfig] = None):
        """
        Args:
            config: 위험 점수 산정 설정 (None이면 기본 설정 사용)
        """
        self.config = config or RiskScoreConfig()

    def calculate_risk_score(
        self, evaluation_results: List[RuleEvaluationResult]
    ) -> Dict[str, Any]:
        """
        룰 평가 결과를 기반으로 최종 위험 점수 계산

        Args:
            evaluation_results: 룰 평가 결과 목록 (트리거된 룰만 포함)

        Returns:
            Dict[str, Any]: 위험 점수 산정 결과
                {
                    "risk_score": 85,
                    "risk_level": "high",
                    "factor_contributions": [
                        {
                            "factor_type": "suspicious_ip",
                            "base_score": 50,
                            "weight": 1.2,
                            "severity_multiplier": 1.5,
                            "weighted_score": 90
                        },
                        ...
                    ],
                    "total_weighted_score": 150,  # 가중치 적용 후 합계
                    "normalized_score": 85,        # 100으로 정규화
                }
        """
        if not evaluation_results:
            # 위험 요인이 없으면 위험 점수 0
            return {
                "risk_score": 0,
                "risk_level": RiskLevel.LOW.value,
                "factor_contributions": [],
                "total_weighted_score": 0,
                "normalized_score": 0,
            }

        factor_contributions = []
        total_weighted_score = 0

        for result in evaluation_results:
            # 기본 점수
            base_score = result.risk_score

            # 요인 유형별 가중치
            factor_weight = self.config.DEFAULT_WEIGHTS.get(
                self._map_rule_type_to_factor_type(result.rule_type),
                1.0,
            )

            # 심각도별 배율
            severity_multiplier = self.config.SEVERITY_MULTIPLIERS.get(
                result.severity, 1.0
            )

            # 가중치 적용 점수
            weighted_score = base_score * factor_weight * severity_multiplier

            factor_contributions.append(
                {
                    "rule_id": str(result.rule_id),
                    "rule_name": result.rule_name,
                    "rule_type": result.rule_type.value,
                    "base_score": base_score,
                    "factor_weight": factor_weight,
                    "severity": result.severity.value,
                    "severity_multiplier": severity_multiplier,
                    "weighted_score": round(weighted_score, 2),
                    "description": result.description,
                }
            )

            total_weighted_score += weighted_score

        # 0-100으로 정규화
        normalized_score = min(100, int(total_weighted_score))

        # 위험 수준 결정
        risk_level = self._determine_risk_level(normalized_score)

        return {
            "risk_score": normalized_score,
            "risk_level": risk_level.value,
            "factor_contributions": factor_contributions,
            "total_weighted_score": round(total_weighted_score, 2),
            "normalized_score": normalized_score,
        }

    def calculate_risk_score_from_factors(
        self, risk_factors: List[RiskFactor]
    ) -> Dict[str, Any]:
        """
        RiskFactor 모델 인스턴스 목록으로부터 위험 점수 계산

        Args:
            risk_factors: 위험 요인 목록

        Returns:
            Dict[str, Any]: 위험 점수 산정 결과
        """
        if not risk_factors:
            return {
                "risk_score": 0,
                "risk_level": RiskLevel.LOW.value,
                "factor_contributions": [],
                "total_weighted_score": 0,
                "normalized_score": 0,
            }

        factor_contributions = []
        total_weighted_score = 0

        for factor in risk_factors:
            # 기본 점수
            base_score = factor.factor_score

            # 요인 유형별 가중치
            factor_weight = self.config.DEFAULT_WEIGHTS.get(factor.factor_type, 1.0)

            # 심각도별 배율
            severity_multiplier = self.config.SEVERITY_MULTIPLIERS.get(
                factor.severity, 1.0
            )

            # 가중치 적용 점수
            weighted_score = base_score * factor_weight * severity_multiplier

            factor_contributions.append(
                {
                    "factor_id": str(factor.id),
                    "factor_type": factor.factor_type.value,
                    "base_score": base_score,
                    "factor_weight": factor_weight,
                    "severity": factor.severity.value,
                    "severity_multiplier": severity_multiplier,
                    "weighted_score": round(weighted_score, 2),
                    "description": factor.description,
                }
            )

            total_weighted_score += weighted_score

        # 0-100으로 정규화
        normalized_score = min(100, int(total_weighted_score))

        # 위험 수준 결정
        risk_level = self._determine_risk_level(normalized_score)

        return {
            "risk_score": normalized_score,
            "risk_level": risk_level.value,
            "factor_contributions": factor_contributions,
            "total_weighted_score": round(total_weighted_score, 2),
            "normalized_score": normalized_score,
        }

    def _determine_risk_level(self, risk_score: int) -> RiskLevel:
        """
        위험 점수에 따라 위험 수준 결정

        Args:
            risk_score: 위험 점수 (0-100)

        Returns:
            RiskLevel: 위험 수준
        """
        if risk_score <= 30:
            return RiskLevel.LOW
        elif risk_score <= 39:
            # 경계 구간: 보수적으로 MEDIUM으로 분류
            return RiskLevel.MEDIUM
        elif risk_score <= 70:
            return RiskLevel.MEDIUM
        elif risk_score <= 79:
            # 경계 구간: 보수적으로 HIGH로 분류
            return RiskLevel.HIGH
        else:  # 80-100
            return RiskLevel.HIGH

    def _map_rule_type_to_factor_type(self, rule_type) -> FactorType:
        """
        RuleType을 FactorType으로 매핑

        Args:
            rule_type: 룰 유형

        Returns:
            FactorType: 요인 유형
        """
        from models import RuleType

        mapping = {
            RuleType.VELOCITY: FactorType.VELOCITY_CHECK,
            RuleType.THRESHOLD: FactorType.AMOUNT_THRESHOLD,
            RuleType.LOCATION: FactorType.LOCATION_MISMATCH,
            RuleType.BLACKLIST: FactorType.SUSPICIOUS_IP,
            RuleType.TIME_PATTERN: FactorType.SUSPICIOUS_TIME,
        }

        return mapping.get(rule_type, FactorType.VELOCITY_CHECK)

    def get_recommended_action(self, risk_score: int, risk_level: RiskLevel) -> Dict[str, Any]:
        """
        위험 점수와 위험 수준에 따른 권장 조치 결정

        Args:
            risk_score: 위험 점수
            risk_level: 위험 수준

        Returns:
            Dict[str, Any]: 권장 조치
                {
                    "action": "approve|additional_auth_required|blocked",
                    "reason": "사유",
                    "additional_auth_required": bool,
                    "manual_review_required": bool,
                    "auth_methods": ["otp_sms", "biometric"] (추가 인증 필요 시만),
                    "auth_timeout_seconds": 300 (추가 인증 필요 시만)
                }
        """
        if risk_level == RiskLevel.LOW:
            return {
                "action": "approve",
                "reason": "위험 점수가 낮은 정상 거래",
                "additional_auth_required": False,
                "manual_review_required": False,
            }

        elif risk_level == RiskLevel.MEDIUM:
            return {
                "action": "additional_auth_required",
                "reason": "중간 위험도 거래 - 추가 인증 필요",
                "additional_auth_required": True,
                "manual_review_required": False,
                "auth_methods": ["otp_sms", "biometric"],
                "auth_timeout_seconds": 300,  # 5분
            }

        else:  # HIGH
            return {
                "action": "blocked",
                "reason": "고위험 거래 - 자동 차단",
                "additional_auth_required": False,
                "manual_review_required": True,
            }

    def explain_risk_score(
        self, risk_score: int, factor_contributions: List[Dict[str, Any]]
    ) -> str:
        """
        위험 점수 산정 이유를 사람이 읽을 수 있는 형태로 설명

        Args:
            risk_score: 위험 점수
            factor_contributions: 요인별 기여도 목록

        Returns:
            str: 설명 텍스트
        """
        if risk_score == 0:
            return "위험 요인이 탐지되지 않았습니다."

        explanations = [f"총 위험 점수: {risk_score}점"]

        # 기여도가 높은 순으로 정렬
        sorted_contributions = sorted(
            factor_contributions,
            key=lambda x: x["weighted_score"],
            reverse=True,
        )

        explanations.append("\n주요 위험 요인:")
        for idx, contrib in enumerate(sorted_contributions[:5], 1):  # 상위 5개만
            rule_name = contrib.get("rule_name", contrib.get("factor_type", "알 수 없음"))
            weighted_score = contrib["weighted_score"]
            description = contrib.get("description", "설명 없음")

            explanations.append(
                f"{idx}. {rule_name} (기여도: {weighted_score:.1f}점)\n   - {description}"
            )

        return "\n".join(explanations)
