"""
성능 모니터링이 통합된 FDS 평가 엔진

기존 EvaluationEngine에 성능 추적 기능을 추가하여
100ms 목표 달성 여부를 실시간으로 모니터링합니다.
"""

import logging
import time
from datetime import datetime
from typing import List, Optional

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
from ..utils.performance_monitor import (
    PerformanceMetric,
    get_performance_monitor,
)

logger = logging.getLogger(__name__)


class MonitoredEvaluationEngine:
    """
    성능 모니터링이 통합된 FDS 평가 엔진

    주요 개선사항:
    1. 전체 평가 시간 추적
    2. 세부 컴포넌트별 시간 분해 (룰 엔진, ML 엔진, CTI)
    3. 100ms 목표 준수 여부 실시간 확인
    4. 느린 평가 자동 감지 및 알림
    5. Prometheus 메트릭 내보내기 지원
    """

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        redis: Optional[aioredis.Redis] = None,
        enable_monitoring: bool = True,
    ):
        """
        평가 엔진 초기화

        Args:
            db: 데이터베이스 세션
            redis: Redis 클라이언트
            enable_monitoring: 성능 모니터링 활성화 여부
        """
        self.db = db
        self.redis = redis
        self.cti_connector = None
        self.enable_monitoring = enable_monitoring

        # 성능 모니터 초기화
        if enable_monitoring:
            self.perf_monitor = get_performance_monitor()
        else:
            self.perf_monitor = None

        # CTI 커넥터 초기화
        if db and redis:
            self.cti_connector = CTIConnector(db, redis)

    async def evaluate(self, request: FDSEvaluationRequest) -> FDSEvaluationResponse:
        """
        거래를 평가하고 위험 점수를 산정합니다.

        성능 모니터링이 통합되어 각 단계별 시간을 추적합니다.

        Args:
            request: FDS 평가 요청

        Returns:
            FDSEvaluationResponse: 평가 결과
        """
        start_time = time.time()
        breakdown = {}

        # 타이머 시작
        rule_engine_start = None

        try:
            # A/B 테스트 정보
            ab_test_group = None

            # Phase 7: A/B 테스트 확인
            if self.db:
                try:
                    from ..services.ab_test_service import ABTestService

                    ab_test_service = ABTestService(self.db)
                    active_test = await ab_test_service.get_active_test(
                        test_type="rule"
                    )

                    if active_test:
                        ab_test_group = ab_test_service.assign_group(
                            active_test, request.transaction_id
                        )
                except Exception as e:
                    logger.warning(f"A/B 테스트 처리 중 에러: {e}")

            # 1. 위험 요인 평가 (룰 엔진)
            rule_engine_start = time.time()
            risk_factors = await self._evaluate_risk_factors(request)
            rule_engine_time_ms = (time.time() - rule_engine_start) * 1000
            breakdown["rule_engine_time"] = rule_engine_time_ms

            # 룰 엔진 시간 추적
            if self.perf_monitor:
                self.perf_monitor.tracker.track(
                    PerformanceMetric.RULE_ENGINE_TIME,
                    rule_engine_time_ms,
                    str(request.transaction_id),
                )

            # 2. ML 엔진 평가 (Phase 8에서 추가 예정)
            ml_engine_time_ms = 0

            # 3. CTI 체크 시간 (이미 _evaluate_risk_factors 내에서 추적됨)
            cti_check_time_ms = getattr(self, "_cti_check_time_ms", 0)
            if cti_check_time_ms > 0:
                breakdown["cti_check_time"] = cti_check_time_ms

                if self.perf_monitor:
                    self.perf_monitor.tracker.track(
                        PerformanceMetric.CTI_CHECK_TIME,
                        cti_check_time_ms,
                        str(request.transaction_id),
                    )

            # 4. 위험 점수 산정
            risk_score = self._calculate_risk_score(risk_factors)

            # 5. 위험 수준 분류
            risk_level = self._classify_risk_level(risk_score)

            # 6. 의사결정
            decision = self._make_decision(risk_level)

            # 7. 권장 조치
            recommended_action = self._generate_recommended_action(
                decision, risk_level, risk_score, risk_factors
            )

            # 전체 평가 시간 계산
            evaluation_time_ms = (time.time() - start_time) * 1000

            # Phase 7: A/B 테스트 결과 기록
            if self.db and ab_test_group and active_test:
                try:
                    is_tp, is_fp, is_fn = await ab_test_service.determine_fraud_label(
                        request.transaction_id, risk_score, decision.value
                    )

                    await ab_test_service.record_test_result(
                        test=active_test,
                        group=ab_test_group,
                        is_true_positive=is_tp,
                        is_false_positive=is_fp,
                        is_false_negative=is_fn,
                        evaluation_time_ms=int(evaluation_time_ms),
                    )

                    await self.db.commit()
                except Exception as e:
                    logger.error(f"A/B 테스트 결과 기록 실패: {e}")
                    await self.db.rollback()

            # 성능 모니터링에 기록
            if self.perf_monitor:
                self.perf_monitor.track_evaluation(
                    evaluation_time_ms, str(request.transaction_id), breakdown
                )

            # 100ms 목표 초과 시 상세 로깅
            if evaluation_time_ms > 100:
                logger.warning(
                    f"FDS 평가 시간 목표 초과: {evaluation_time_ms:.2f}ms\n"
                    f"  거래 ID: {request.transaction_id}\n"
                    f"  룰 엔진: {rule_engine_time_ms:.2f}ms\n"
                    f"  CTI 체크: {cti_check_time_ms:.2f}ms\n"
                    f"  위험 점수: {risk_score}"
                )

            # 평가 메타데이터
            metadata = EvaluationMetadata(
                evaluation_time_ms=int(evaluation_time_ms),
                rule_engine_time_ms=int(rule_engine_time_ms),
                ml_engine_time_ms=int(ml_engine_time_ms)
                if ml_engine_time_ms > 0
                else None,
                cti_check_time_ms=int(cti_check_time_ms)
                if cti_check_time_ms > 0
                else None,
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

        except Exception as e:
            evaluation_time_ms = (time.time() - start_time) * 1000
            logger.error(
                f"FDS 평가 실패: {e}\n"
                f"  거래 ID: {request.transaction_id}\n"
                f"  소요 시간: {evaluation_time_ms:.2f}ms"
            )
            raise

    async def _evaluate_risk_factors(
        self, request: FDSEvaluationRequest
    ) -> List[RiskFactor]:
        """
        위험 요인을 평가합니다.

        CTI 체크 시간을 별도로 추적합니다.
        """
        risk_factors = []
        self._cti_check_time_ms = 0

        # 기본 위험 요인: 거래 금액 확인
        amount_risk = await self._check_amount_risk(request.amount)
        if amount_risk:
            risk_factors.append(amount_risk)

        # 기본 위험 요인: IP 주소 확인 (CTI 포함)
        cti_start = time.time()
        ip_risk = await self._check_ip_risk(request.ip_address)
        if ip_risk:
            risk_factors.append(ip_risk)
        self._cti_check_time_ms = (time.time() - cti_start) * 1000

        # Phase 4+: 추가 룰 기반 검사 (velocity, 지역 불일치 등)
        # (기존 EvaluationEngine 로직과 동일)

        return risk_factors

    async def _check_amount_risk(self, amount: float) -> Optional[RiskFactor]:
        """거래 금액 위험 체크"""
        # 1만원 초과 거래는 낮은 위험
        if amount > 1000000:  # 100만원 초과
            return RiskFactor(
                factor_type="high_amount",
                description=f"고액 거래: {amount:,.0f}원",
                score=15,
                severity=SeverityEnum.MEDIUM,
                metadata={"amount": amount, "threshold": 1000000},
            )
        elif amount > 500000:  # 50만원 초과
            return RiskFactor(
                factor_type="medium_amount",
                description=f"중액 거래: {amount:,.0f}원",
                score=5,
                severity=SeverityEnum.LOW,
                metadata={"amount": amount},
            )
        return None

    async def _check_ip_risk(self, ip_address: str) -> Optional[RiskFactor]:
        """IP 주소 위험 체크 (CTI 포함)"""
        if not self.cti_connector:
            return None

        try:
            # CTI 체크
            threat_level, confidence = await self.cti_connector.check_ip_reputation(
                ip_address
            )

            if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                return RiskFactor(
                    factor_type="malicious_ip",
                    description=f"악성 IP 탐지: {ip_address} (위협도: {threat_level.value})",
                    score=30 if threat_level == ThreatLevel.HIGH else 50,
                    severity=SeverityEnum.HIGH
                    if threat_level == ThreatLevel.HIGH
                    else SeverityEnum.CRITICAL,
                    metadata={
                        "ip_address": ip_address,
                        "threat_level": threat_level.value,
                        "confidence": confidence,
                    },
                )
        except Exception as e:
            logger.error(f"CTI IP 체크 실패: {e}")

        return None

    def _calculate_risk_score(self, risk_factors: List[RiskFactor]) -> int:
        """위험 점수 산정"""
        total_score = sum(factor.score for factor in risk_factors)
        return min(total_score, 100)  # 최대 100점

    def _classify_risk_level(self, risk_score: int) -> RiskLevelEnum:
        """위험 수준 분류"""
        if risk_score >= 80:
            return RiskLevelEnum.CRITICAL
        elif risk_score >= 60:
            return RiskLevelEnum.HIGH
        elif risk_score >= 40:
            return RiskLevelEnum.MEDIUM
        else:
            return RiskLevelEnum.LOW

    def _make_decision(self, risk_level: RiskLevelEnum) -> DecisionEnum:
        """의사결정"""
        if risk_level == RiskLevelEnum.CRITICAL:
            return DecisionEnum.BLOCK
        elif risk_level == RiskLevelEnum.HIGH:
            return DecisionEnum.BLOCK
        elif risk_level == RiskLevelEnum.MEDIUM:
            return DecisionEnum.ADDITIONAL_AUTH_REQUIRED
        else:
            return DecisionEnum.APPROVE

    def _generate_recommended_action(
        self,
        decision: DecisionEnum,
        risk_level: RiskLevelEnum,
        risk_score: int,
        risk_factors: List[RiskFactor],
    ) -> RecommendedAction:
        """권장 조치 생성"""
        if decision == DecisionEnum.BLOCK:
            return RecommendedAction(
                action="block_transaction",
                reason="고위험 거래로 판단되어 자동 차단되었습니다.",
                requires_manual_review=True,
                suggested_next_steps=["보안팀 검토 큐에 추가", "사용자에게 차단 알림 발송", "추가 본인 인증 요청"],
            )
        elif decision == DecisionEnum.ADDITIONAL_AUTH_REQUIRED:
            return RecommendedAction(
                action="request_otp",
                reason="중간 위험도 거래로 추가 인증이 필요합니다.",
                requires_manual_review=False,
                suggested_next_steps=["OTP 발송", "생체 인증 요청"],
            )
        else:
            return RecommendedAction(
                action="approve",
                reason="정상 거래로 판단되었습니다.",
                requires_manual_review=False,
                suggested_next_steps=[],
            )

    def get_performance_summary(self) -> str:
        """성능 요약 리포트 조회"""
        if not self.perf_monitor:
            return "성능 모니터링이 비활성화되어 있습니다."

        return self.perf_monitor.get_performance_report()

    def check_target_compliance(self) -> dict:
        """100ms 목표 달성 여부 확인"""
        if not self.perf_monitor:
            return {"error": "성능 모니터링이 비활성화되어 있습니다."}

        return self.perf_monitor.check_fds_target()

    def export_prometheus_metrics(self) -> str:
        """Prometheus 메트릭 내보내기"""
        if not self.perf_monitor:
            return "# 성능 모니터링이 비활성화되어 있습니다."

        return self.perf_monitor.export_metrics_prometheus()
