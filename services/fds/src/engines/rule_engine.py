"""
룰 엔진 (Rule Engine)

FDS의 핵심 컴포넌트로, 데이터베이스에 저장된 탐지 룰을 로드하여
거래를 평가하고 위험 요인을 탐지합니다.

룰 엔진은 다음과 같은 기능을 제공합니다:
1. 활성화된 룰을 데이터베이스에서 동적으로 로드
2. 우선순위에 따라 룰을 순차적으로 평가
3. 각 룰의 조건을 검증하고 위험 점수 산정
4. 탐지된 위험 요인을 RiskFactor로 기록
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis import asyncio as aioredis

from ..models import (
    DetectionRule,
    RiskFactor,
    FactorType,
    FactorSeverity,
    RuleType,
)


class TransactionContext:
    """
    거래 평가를 위한 컨텍스트 정보

    룰 평가 시 필요한 모든 거래 정보를 담고 있습니다.
    """

    def __init__(
        self,
        transaction_id: UUID,
        user_id: UUID,
        order_id: UUID,
        amount: Decimal,
        ip_address: str,
        user_agent: str,
        device_type: str,
        geolocation: Optional[Dict[str, Any]] = None,
        payment_info: Optional[Dict[str, Any]] = None,
        session_context: Optional[Dict[str, Any]] = None,
        user_profile: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.transaction_id = transaction_id
        self.user_id = user_id
        self.order_id = order_id
        self.amount = amount
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.device_type = device_type
        self.geolocation = geolocation or {}
        self.payment_info = payment_info or {}
        self.session_context = session_context or {}
        self.user_profile = user_profile or {}
        self.timestamp = timestamp or datetime.utcnow()


class RuleEvaluationResult:
    """룰 평가 결과"""

    def __init__(
        self,
        rule_id: UUID,
        rule_name: str,
        rule_type: RuleType,
        triggered: bool,
        risk_score: int = 0,
        severity: FactorSeverity = FactorSeverity.INFO,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.rule_type = rule_type
        self.triggered = triggered
        self.risk_score = risk_score
        self.severity = severity
        self.description = description
        self.metadata = metadata or {}


class RuleEngine:
    """
    룰 엔진

    데이터베이스에 저장된 탐지 룰을 로드하여 거래를 평가합니다.
    """

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        """
        Args:
            db: 데이터베이스 세션
            redis: Redis 클라이언트
        """
        self.db = db
        self.redis = redis
        self._rule_cache: List[DetectionRule] = []
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5분마다 룰 재로드

    async def load_active_rules(self, force_reload: bool = False) -> List[DetectionRule]:
        """
        활성화된 룰을 데이터베이스에서 로드

        Args:
            force_reload: 캐시를 무시하고 강제로 재로드

        Returns:
            List[DetectionRule]: 활성화된 룰 목록 (우선순위 순으로 정렬)

        Note:
            - 캐시 TTL은 5분입니다.
            - 룰 관리 API를 통해 룰이 추가/수정/삭제되면 자동으로 최대 5분 내에 반영됩니다.
            - 즉시 반영이 필요한 경우 force_reload=True를 사용하세요.
        """
        # 캐시 유효성 검사
        if not force_reload and self._rule_cache:
            if self._cache_timestamp:
                cache_age = (datetime.utcnow() - self._cache_timestamp).total_seconds()
                if cache_age < self._cache_ttl_seconds:
                    return self._rule_cache

        # 데이터베이스에서 활성화된 룰 조회
        query = (
            select(DetectionRule)
            .where(DetectionRule.is_active == True)
            .order_by(DetectionRule.priority.desc(), DetectionRule.created_at)
        )

        result = await self.db.execute(query)
        rules = result.scalars().all()

        # 캐시 업데이트
        self._rule_cache = list(rules)
        self._cache_timestamp = datetime.utcnow()

        return self._rule_cache

    def invalidate_cache(self) -> None:
        """
        룰 캐시를 무효화합니다.

        보안팀이 룰 관리 API를 통해 룰을 추가/수정/삭제한 경우,
        다음 evaluate_transaction 호출 시 최신 룰을 로드하도록 합니다.

        Note:
            - 이 메서드는 관리자 대시보드 API에서 호출될 수 있습니다.
            - 캐시를 무효화하면 다음 평가 시 자동으로 데이터베이스에서 재로드됩니다.
        """
        self._rule_cache = []
        self._cache_timestamp = None

    async def evaluate_transaction(
        self, context: TransactionContext
    ) -> List[RuleEvaluationResult]:
        """
        거래를 평가하여 위험 요인을 탐지

        Args:
            context: 거래 컨텍스트

        Returns:
            List[RuleEvaluationResult]: 평가 결과 목록 (트리거된 룰만 포함)
        """
        # 활성화된 룰 로드
        rules = await self.load_active_rules()

        # 각 룰을 순차적으로 평가
        results: List[RuleEvaluationResult] = []

        for rule in rules:
            try:
                result = await self._evaluate_rule(rule, context)
                if result.triggered:
                    results.append(result)

                    # 룰 트리거 통계 업데이트
                    rule.increment_trigger_count()

            except Exception as e:
                # 개별 룰 평가 실패 시 로깅하고 계속 진행
                print(f"룰 평가 실패: {rule.name}, {e}")
                continue

        return results

    async def _evaluate_rule(
        self, rule: DetectionRule, context: TransactionContext
    ) -> RuleEvaluationResult:
        """
        개별 룰을 평가

        Args:
            rule: 탐지 룰
            context: 거래 컨텍스트

        Returns:
            RuleEvaluationResult: 평가 결과
        """
        # 룰 유형에 따라 평가 로직 분기
        if rule.rule_type == RuleType.VELOCITY:
            return await self._evaluate_velocity_rule(rule, context)

        elif rule.rule_type == RuleType.THRESHOLD:
            return await self._evaluate_threshold_rule(rule, context)

        elif rule.rule_type == RuleType.LOCATION:
            return await self._evaluate_location_rule(rule, context)

        elif rule.rule_type == RuleType.BLACKLIST:
            return await self._evaluate_blacklist_rule(rule, context)

        elif rule.rule_type == RuleType.TIME_PATTERN:
            return await self._evaluate_time_pattern_rule(rule, context)

        elif rule.rule_type == RuleType.DEVICE_PATTERN:
            return await self._evaluate_device_pattern_rule(rule, context)

        else:
            # 알 수 없는 룰 유형
            return RuleEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                triggered=False,
            )

    async def _evaluate_velocity_rule(
        self, rule: DetectionRule, context: TransactionContext
    ) -> RuleEvaluationResult:
        """
        Velocity Check 룰 평가 (단시간 내 반복 거래)

        조건 예시:
        {
            "window_seconds": 300,
            "max_transactions": 3,
            "scope": "ip_address"  # ip_address, user_id, card_bin
        }
        """
        condition = rule.condition
        window_seconds = condition.get("window_seconds", 300)
        max_transactions = condition.get("max_transactions", 3)
        scope = condition.get("scope", "ip_address")

        # Redis 키 생성
        if scope == "ip_address":
            redis_key = f"velocity:ip:{context.ip_address}"
            scope_value = context.ip_address
        elif scope == "user_id":
            redis_key = f"velocity:user:{context.user_id}"
            scope_value = str(context.user_id)
        elif scope == "card_bin":
            card_bin = context.payment_info.get("card_bin", "unknown")
            redis_key = f"velocity:card:{card_bin}"
            scope_value = card_bin
        else:
            # 알 수 없는 scope
            return RuleEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                triggered=False,
            )

        # Redis에서 현재 거래 횟수 조회 및 증가
        try:
            transaction_count = await self.redis.incr(redis_key)

            # 첫 거래이면 만료 시간 설정
            if transaction_count == 1:
                await self.redis.expire(redis_key, window_seconds)

            # 임계값 초과 여부 확인
            if transaction_count > max_transactions:
                return RuleEvaluationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    rule_type=rule.rule_type,
                    triggered=True,
                    risk_score=rule.risk_score_weight,
                    severity=FactorSeverity.determine_severity(rule.risk_score_weight),
                    description=f"{scope}={scope_value}에서 {window_seconds}초 내 {transaction_count}회 거래 시도 (임계값: {max_transactions}회)",
                    metadata={
                        "scope": scope,
                        "scope_value": scope_value,
                        "transaction_count": transaction_count,
                        "max_transactions": max_transactions,
                        "window_seconds": window_seconds,
                    },
                )

        except Exception as e:
            print(f"Velocity Check 실패: {e}")

        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            triggered=False,
        )

    async def _evaluate_threshold_rule(
        self, rule: DetectionRule, context: TransactionContext
    ) -> RuleEvaluationResult:
        """
        Threshold 룰 평가 (금액 임계값)

        조건 예시:
        {
            "field": "amount",
            "operator": "gt",  # gt, gte, lt, lte, eq
            "value": 500000
        }
        """
        condition = rule.condition
        field = condition.get("field", "amount")
        operator = condition.get("operator", "gt")
        threshold_value = condition.get("value", 0)

        # 필드 값 가져오기
        if field == "amount":
            actual_value = float(context.amount)
        else:
            # 알 수 없는 필드
            return RuleEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                triggered=False,
            )

        # 연산자에 따라 비교
        triggered = False
        if operator == "gt":
            triggered = actual_value > threshold_value
        elif operator == "gte":
            triggered = actual_value >= threshold_value
        elif operator == "lt":
            triggered = actual_value < threshold_value
        elif operator == "lte":
            triggered = actual_value <= threshold_value
        elif operator == "eq":
            triggered = actual_value == threshold_value

        if triggered:
            return RuleEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                triggered=True,
                risk_score=rule.risk_score_weight,
                severity=FactorSeverity.determine_severity(rule.risk_score_weight),
                description=f"거래 금액({actual_value:,.0f}원)이 임계값({threshold_value:,.0f}원) {operator}",
                metadata={
                    "field": field,
                    "operator": operator,
                    "actual_value": actual_value,
                    "threshold_value": threshold_value,
                },
            )

        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            triggered=False,
        )

    async def _evaluate_location_rule(
        self, rule: DetectionRule, context: TransactionContext
    ) -> RuleEvaluationResult:
        """
        Location 룰 평가 (지역 불일치)

        조건 예시:
        {
            "max_distance_km": 100
        }
        """
        from utils.geolocation import calculate_distance_km, parse_geolocation, get_region_name

        condition = rule.condition
        max_distance_km = condition.get("max_distance_km", 100)

        # 사용자 등록 주소의 지리적 위치 (user_profile에서 가져옴)
        registered_location = parse_geolocation(context.user_profile.get("geolocation"))

        # 현재 IP 주소의 지리적 위치
        current_location = parse_geolocation(context.geolocation)

        # 둘 다 있어야 비교 가능
        if not registered_location or not current_location:
            return RuleEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                triggered=False,
            )

        # 거리 계산
        registered_lat, registered_lon = registered_location
        current_lat, current_lon = current_location

        distance_km = calculate_distance_km(
            registered_lat, registered_lon, current_lat, current_lon
        )

        # 임계값 초과 여부 확인
        if distance_km > max_distance_km:
            registered_region = get_region_name(context.user_profile.get("geolocation"))
            current_region = get_region_name(context.geolocation)

            return RuleEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                triggered=True,
                risk_score=rule.risk_score_weight,
                severity=FactorSeverity.determine_severity(rule.risk_score_weight),
                description=f"등록 주소({registered_region})와 IP 위치({current_region}) 불일치: {distance_km:.1f}km (임계값: {max_distance_km}km)",
                metadata={
                    "registered_location": {
                        "lat": registered_lat,
                        "lon": registered_lon,
                        "region": registered_region,
                    },
                    "current_location": {
                        "lat": current_lat,
                        "lon": current_lon,
                        "region": current_region,
                    },
                    "distance_km": round(distance_km, 2),
                    "max_distance_km": max_distance_km,
                },
            )

        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            triggered=False,
        )

    async def _evaluate_blacklist_rule(
        self, rule: DetectionRule, context: TransactionContext
    ) -> RuleEvaluationResult:
        """
        Blacklist 룰 평가

        조건 예시:
        {
            "type": "ip",  # ip, email_domain, card_bin
            "values": ["1.2.3.4", "5.6.7.8"]
        }
        """
        condition = rule.condition
        blacklist_type = condition.get("type", "ip")
        blacklist_values = condition.get("values", [])

        # 블랙리스트 확인
        if blacklist_type == "ip":
            if context.ip_address in blacklist_values:
                return RuleEvaluationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    rule_type=rule.rule_type,
                    triggered=True,
                    risk_score=rule.risk_score_weight,
                    severity=FactorSeverity.CRITICAL,
                    description=f"블랙리스트 IP 주소 탐지: {context.ip_address}",
                    metadata={"type": blacklist_type, "value": context.ip_address},
                )

        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            triggered=False,
        )

    async def _evaluate_time_pattern_rule(
        self, rule: DetectionRule, context: TransactionContext
    ) -> RuleEvaluationResult:
        """
        Time Pattern 룰 평가 (비정상 시간대 거래)

        조건 예시:
        {
            "start_hour": 0,
            "end_hour": 5
        }
        """
        condition = rule.condition
        start_hour = condition.get("start_hour", 0)
        end_hour = condition.get("end_hour", 5)

        current_hour = context.timestamp.hour

        # 시간대 확인
        if start_hour <= current_hour < end_hour:
            return RuleEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                triggered=True,
                risk_score=rule.risk_score_weight,
                severity=FactorSeverity.determine_severity(rule.risk_score_weight),
                description=f"비정상 시간대 거래: {current_hour}시 (허용: {end_hour}시 이후)",
                metadata={
                    "current_hour": current_hour,
                    "start_hour": start_hour,
                    "end_hour": end_hour,
                },
            )

        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            triggered=False,
        )

    async def _evaluate_device_pattern_rule(
        self, rule: DetectionRule, context: TransactionContext
    ) -> RuleEvaluationResult:
        """
        Device Pattern 룰 평가 (동일 계정에서 여러 디바이스)

        조건 예시:
        {
            "max_devices": 3
        }
        """
        # 이 메서드는 향후 구현할 수 있습니다
        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            triggered=False,
        )

    async def create_risk_factors(
        self, transaction_id: UUID, results: List[RuleEvaluationResult]
    ) -> List[RiskFactor]:
        """
        룰 평가 결과를 RiskFactor로 변환하여 데이터베이스에 저장

        Args:
            transaction_id: 거래 ID
            results: 룰 평가 결과 목록

        Returns:
            List[RiskFactor]: 생성된 위험 요인 목록
        """
        risk_factors: List[RiskFactor] = []

        for result in results:
            # 룰 유형을 FactorType으로 매핑
            factor_type_map = {
                RuleType.VELOCITY: FactorType.VELOCITY_CHECK,
                RuleType.THRESHOLD: FactorType.AMOUNT_THRESHOLD,
                RuleType.LOCATION: FactorType.LOCATION_MISMATCH,
                RuleType.BLACKLIST: FactorType.SUSPICIOUS_IP,
                RuleType.TIME_PATTERN: FactorType.SUSPICIOUS_TIME,
            }

            factor_type = factor_type_map.get(result.rule_type, FactorType.VELOCITY_CHECK)

            risk_factor = RiskFactor(
                transaction_id=transaction_id,
                factor_type=factor_type,
                factor_score=result.risk_score,
                severity=result.severity,
                description=result.description,
                risk_metadata={
                    "rule_id": str(result.rule_id),
                    "rule_name": result.rule_name,
                    **result.metadata,
                },
            )

            self.db.add(risk_factor)
            risk_factors.append(risk_factor)

        await self.db.flush()

        return risk_factors
