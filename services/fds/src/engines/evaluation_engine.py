"""
FDS 평가 엔진

거래의 위험도를 평가하고 적절한 조치를 결정하는 핵심 엔진
"""

import time
from datetime import datetime
from typing import List, Tuple, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from redis import asyncio as aioredis

from ..models.schemas import (
    FDSEvaluationRequest,
    FDSEvaluationResponse,
    RiskFactor,
    EvaluationMetadata,
    RecommendedAction,
    RiskLevelEnum,
    DecisionEnum,
    SeverityEnum,
)
from ..engines.cti_connector import CTIConnector, ThreatLevel


class EvaluationEngine:
    """
    FDS 평가 엔진

    거래를 평가하고 위험 점수를 산정하여 적절한 조치를 결정합니다.
    Phase 3에서는 기본적인 룰 기반 평가만 수행하며,
    Phase 5에서 CTI 통합이 추가되었습니다.
    """

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        redis: Optional[aioredis.Redis] = None,
    ):
        """
        평가 엔진 초기화

        Args:
            db: 데이터베이스 세션 (CTI 사용 시 필수)
            redis: Redis 클라이언트 (CTI 사용 시 필수)
        """
        self.db = db
        self.redis = redis
        self.cti_connector = None

        # CTI 커넥터 초기화 (db와 redis가 모두 제공된 경우)
        if db and redis:
            self.cti_connector = CTIConnector(db, redis)

    async def evaluate(self, request: FDSEvaluationRequest) -> FDSEvaluationResponse:
        """
        거래를 평가하고 위험 점수를 산정합니다.

        Args:
            request: FDS 평가 요청

        Returns:
            FDSEvaluationResponse: 평가 결과
        """
        start_time = time.time()

        # CTI 체크 시간 추적
        self._cti_check_time_ms = 0

        # 1. 위험 요인 평가
        risk_factors = await self._evaluate_risk_factors(request)

        # 2. 위험 점수 산정
        risk_score = self._calculate_risk_score(risk_factors)

        # 3. 위험 수준 분류
        risk_level = self._classify_risk_level(risk_score)

        # 4. 의사결정
        decision = self._make_decision(risk_level)

        # 5. 권장 조치
        recommended_action = self._generate_recommended_action(
            decision, risk_level, risk_score, risk_factors
        )

        # 평가 시간 계산
        evaluation_time_ms = int((time.time() - start_time) * 1000)

        # 평가 메타데이터
        metadata = EvaluationMetadata(
            evaluation_time_ms=evaluation_time_ms,
            rule_engine_time_ms=evaluation_time_ms - self._cti_check_time_ms,
            ml_engine_time_ms=None,  # Phase 6에서 추가 예정
            cti_check_time_ms=self._cti_check_time_ms if self._cti_check_time_ms > 0 else None,
            timestamp=datetime.utcnow(),
        )

        return FDSEvaluationResponse(
            transaction_id=request.transaction_id,
            risk_score=risk_score,
            risk_level=risk_level,
            decision=decision,
            risk_factors=risk_factors,
            evaluation_metadata=metadata,
            recommended_action=recommended_action,
        )

    async def _evaluate_risk_factors(
        self, request: FDSEvaluationRequest
    ) -> List[RiskFactor]:
        """
        위험 요인을 평가합니다.

        Phase 3에서는 정상 거래를 위한 기본 평가만 수행합니다.
        이후 Phase에서 실제 룰 기반 탐지가 추가됩니다.

        Args:
            request: FDS 평가 요청

        Returns:
            List[RiskFactor]: 평가된 위험 요인 목록
        """
        risk_factors = []

        # 기본 위험 요인: 거래 금액 확인
        amount_risk = await self._check_amount_risk(request.amount)
        if amount_risk:
            risk_factors.append(amount_risk)

        # 기본 위험 요인: IP 주소 확인
        ip_risk = await self._check_ip_risk(request.ip_address)
        if ip_risk:
            risk_factors.append(ip_risk)

        # 기본 위험 요인: Velocity check (사용자 ID 기반)
        velocity_risk = await self._check_velocity_risk(
            request.user_id, request.ip_address
        )
        if velocity_risk:
            risk_factors.append(velocity_risk)

        # 기본 위험 요인: 디바이스 유형 확인
        device_risk = await self._check_device_risk(request.device_fingerprint.device_type)
        if device_risk:
            risk_factors.append(device_risk)

        # 위험 요인이 없으면 정상 거래로 표시
        if not risk_factors:
            risk_factors.append(
                RiskFactor(
                    factor_type="normal_transaction",
                    factor_score=10,
                    description="정상 범위 내 거래",
                    severity=SeverityEnum.INFO,
                )
            )

        return risk_factors

    async def _check_amount_risk(self, amount: float) -> RiskFactor | None:
        """
        거래 금액 위험도 확인

        Args:
            amount: 거래 금액

        Returns:
            RiskFactor | None: 위험 요인 (위험이 없으면 None)
        """
        # 고액 거래 단계별 위험 점수
        if amount >= 5_000_000:  # 500만원 이상 → 중간 위험도
            return RiskFactor(
                factor_type="amount_threshold",
                factor_score=50,
                description=f"고액 거래 (금액: {amount:,.0f}원)",
                severity=SeverityEnum.MEDIUM,
            )
        elif amount >= 3_000_000:  # 300만원 이상 → 중간 위험도
            return RiskFactor(
                factor_type="amount_threshold",
                factor_score=45,
                description=f"고액 거래 (금액: {amount:,.0f}원)",
                severity=SeverityEnum.MEDIUM,
            )
        elif amount >= 1_000_000:  # 100만원 이상 → 낮은 위험도
            return RiskFactor(
                factor_type="amount_threshold",
                factor_score=15,
                description=f"고액 거래 (금액: {amount:,.0f}원)",
                severity=SeverityEnum.LOW,
            )
        return None

    async def _check_ip_risk(self, ip_address: str) -> RiskFactor | None:
        """
        IP 주소 위험도 확인 (CTI 통합)

        Phase 5: CTI 커넥터를 사용하여 악성 IP 탐지 (타임아웃 50ms, Redis 캐싱)

        Args:
            ip_address: IP 주소

        Returns:
            RiskFactor | None: 위험 요인 (위험이 없으면 None)
        """
        # CTI 커넥터가 초기화되어 있으면 사용
        if self.cti_connector:
            cti_start_time = time.time()

            try:
                # CTI 체크 (타임아웃 50ms, Redis 캐싱)
                cti_result = await self.cti_connector.check_ip_threat(ip_address)

                # CTI 체크 시간 기록
                self._cti_check_time_ms += int((time.time() - cti_start_time) * 1000)

                # 위협이 탐지되었으면 RiskFactor 반환
                if cti_result.is_threat:
                    # 위협 수준에 따른 점수 및 심각도 매핑
                    if cti_result.threat_level == ThreatLevel.HIGH:
                        factor_score = 90  # 고위험: 자동 차단 수준
                        severity = SeverityEnum.CRITICAL
                    elif cti_result.threat_level == ThreatLevel.MEDIUM:
                        factor_score = 60  # 중간 위험: 추가 인증 필요
                        severity = SeverityEnum.HIGH
                    else:
                        factor_score = 30  # 낮은 위험: 모니터링
                        severity = SeverityEnum.MEDIUM

                    return RiskFactor(
                        factor_type="suspicious_ip",
                        factor_score=factor_score,
                        description=cti_result.description
                        or f"악성 IP 탐지 ({cti_result.source.value if cti_result.source else 'unknown'})",
                        severity=severity,
                    )
            except Exception as e:
                # CTI 체크 실패 시 fallback (기존 로직 사용)
                pass

        # Fallback: 기존 간단한 IP 범위 체크 (CTI가 없거나 실패한 경우)
        # 해외 IP 주소 목록 (간단한 예시)
        suspicious_ip_ranges = [
            "185.",  # 유럽 지역 일부
            "103.",  # 아시아 일부
        ]

        # Tor Exit Node 및 VPN 서비스 IP (예시)
        known_suspicious_ips = [
            "185.220.100.",  # Tor Exit Node 범위
            "185.220.101.",
        ]

        # IP 주소가 의심스러운 범위에 속하는지 확인
        for suspicious_range in known_suspicious_ips:
            if ip_address.startswith(suspicious_range):
                return RiskFactor(
                    factor_type="location_mismatch",
                    factor_score=45,
                    description=f"비정상적인 지역에서 접속 (해외 IP): {ip_address}",
                    severity=SeverityEnum.MEDIUM,
                )

        # 일반 해외 IP 확인
        for suspicious_range in suspicious_ip_ranges:
            if ip_address.startswith(suspicious_range):
                return RiskFactor(
                    factor_type="location_mismatch",
                    factor_score=40,
                    description=f"비정상적인 지역에서 접속: {ip_address}",
                    severity=SeverityEnum.MEDIUM,
                )

        return None

    async def _check_velocity_risk(
        self, user_id: UUID, ip_address: str
    ) -> RiskFactor | None:
        """
        Velocity Check (단시간 내 반복 거래)

        Args:
            user_id: 사용자 ID
            ip_address: IP 주소

        Returns:
            RiskFactor | None: 위험 요인 (위험이 없으면 None)
        """
        # Phase 3: 간단한 인메모리 캐시 사용 (실제로는 Redis 사용)
        if not hasattr(self, "_transaction_cache"):
            self._transaction_cache = {}

        # 사용자별 거래 기록 확인
        cache_key = f"user:{user_id}"
        current_time = time.time()

        if cache_key not in self._transaction_cache:
            # 첫 번째 거래
            self._transaction_cache[cache_key] = [current_time]
            return None

        # 최근 5분 내 거래 횟수 확인
        recent_transactions = [
            t for t in self._transaction_cache[cache_key]
            if current_time - t < 300  # 5분 = 300초
        ]

        # 5분 내 1회 이상 이전 거래가 있으면 → 중간 위험도 (총 2회 이상)
        if len(recent_transactions) >= 1:
            # 거래 기록 업데이트
            self._transaction_cache[cache_key] = recent_transactions + [current_time]

            return RiskFactor(
                factor_type="velocity_check",
                factor_score=40,
                description=f"단시간 내 반복 거래 ({len(recent_transactions) + 1}회)",
                severity=SeverityEnum.MEDIUM,
            )

        # 거래 기록 업데이트 (위험 요인 없음)
        self._transaction_cache[cache_key] = recent_transactions + [current_time]
        return None

    async def _check_device_risk(self, device_type: str) -> RiskFactor | None:
        """
        디바이스 유형 위험도 확인

        Args:
            device_type: 디바이스 유형

        Returns:
            RiskFactor | None: 위험 요인 (위험이 없으면 None)
        """
        # Phase 3: 알 수 없는 디바이스만 약간의 위험 점수
        if device_type == "unknown":
            return RiskFactor(
                factor_type="device_unknown",
                factor_score=10,
                description="디바이스 유형을 식별할 수 없음",
                severity=SeverityEnum.LOW,
            )
        return None

    def _calculate_risk_score(self, risk_factors: List[RiskFactor]) -> int:
        """
        위험 요인들의 점수를 합산하여 총 위험 점수를 계산합니다.

        Args:
            risk_factors: 위험 요인 목록

        Returns:
            int: 총 위험 점수 (0-100)
        """
        total_score = sum(factor.factor_score for factor in risk_factors)
        # 최대 100점으로 제한
        return min(total_score, 100)

    def _classify_risk_level(self, risk_score: int) -> RiskLevelEnum:
        """
        위험 점수에 따라 위험 수준을 분류합니다.

        Args:
            risk_score: 위험 점수 (0-100)

        Returns:
            RiskLevelEnum: 위험 수준
        """
        if risk_score <= 30:
            return RiskLevelEnum.LOW
        elif risk_score <= 70:
            return RiskLevelEnum.MEDIUM
        else:
            return RiskLevelEnum.HIGH

    def _make_decision(self, risk_level: RiskLevelEnum) -> DecisionEnum:
        """
        위험 수준에 따라 의사결정을 내립니다.

        Args:
            risk_level: 위험 수준

        Returns:
            DecisionEnum: 의사결정
        """
        if risk_level == RiskLevelEnum.LOW:
            return DecisionEnum.APPROVE
        elif risk_level == RiskLevelEnum.MEDIUM:
            return DecisionEnum.ADDITIONAL_AUTH_REQUIRED
        else:  # HIGH
            return DecisionEnum.BLOCKED

    def _generate_recommended_action(
        self,
        decision: DecisionEnum,
        risk_level: RiskLevelEnum,
        risk_score: int,
        risk_factors: List[RiskFactor],
    ) -> RecommendedAction:
        """
        의사결정에 따른 권장 조치를 생성합니다.

        Args:
            decision: 의사결정
            risk_level: 위험 수준
            risk_score: 위험 점수
            risk_factors: 위험 요인 목록

        Returns:
            RecommendedAction: 권장 조치
        """
        if decision == DecisionEnum.APPROVE:
            return RecommendedAction(
                action=DecisionEnum.APPROVE,
                reason=f"위험 점수가 낮은 정상 거래 (점수: {risk_score})",
                additional_auth_required=False,
            )
        elif decision == DecisionEnum.ADDITIONAL_AUTH_REQUIRED:
            return RecommendedAction(
                action=DecisionEnum.ADDITIONAL_AUTH_REQUIRED,
                reason=f"중간 위험도 거래 탐지 (점수: {risk_score})",
                additional_auth_required=True,
                auth_methods=["otp_sms", "biometric"],
                auth_timeout_seconds=300,  # 5분
            )
        else:  # BLOCKED
            return RecommendedAction(
                action=DecisionEnum.BLOCKED,
                reason=f"고위험 거래 탐지 (점수: {risk_score})",
                additional_auth_required=False,
                manual_review_required=True,
                review_queue_id=None,  # Phase 5에서 검토 큐 ID 추가 예정
            )


# 싱글톤 인스턴스
evaluation_engine = EvaluationEngine()
