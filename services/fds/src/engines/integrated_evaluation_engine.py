"""
통합 FDS 평가 엔진 (Integrated Evaluation Engine)

모든 고급 FDS 엔진을 조합하여 종합적인 사기 탐지를 수행합니다.

**통합 엔진**:
- Fingerprint Engine: 디바이스 핑거프린팅 및 블랙리스트 체크
- Behavior Analysis Engine: 마우스/키보드/클릭스트림 봇 탐지
- Network Analysis Engine: TOR/VPN/Proxy 탐지, GeoIP 분석
- Fraud Rule Engine: 30개 실전 사기 탐지 룰
- ML Engine: 앙상블 ML 모델 기반 정밀 예측
- XAI Service: SHAP/LIME 설명 가능한 AI

**평가 프로세스**:
1. 디바이스 핑거프린팅 검증 (블랙리스트 체크)
2. 행동 패턴 분석 (봇 탐지)
3. 네트워크 분석 (TOR/VPN/Proxy)
4. 룰 기반 평가 (30개 룰 적용)
5. ML 모델 평가 (앙상블 모델)
6. 종합 위험 점수 산출
7. 의사결정 및 권장 조치 생성

**성능 목표**:
- P95 평가 시간: 50ms 이내
- Redis 캐시 히트율: 85% 이상
- CTI 체크: 50ms 타임아웃
"""

import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from redis import asyncio as aioredis

from ..engines.fingerprint_engine import FingerprintEngine
from ..engines.behavior_analysis_engine import BehaviorAnalysisEngine
from ..engines.network_analysis_engine import NetworkAnalysisEngine
from ..engines.fraud_rule_engine import FraudRuleEngine, TransactionData
from ..engines.ml_engine import MLEngine
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

logger = logging.getLogger(__name__)


class IntegratedEvaluationEngine:
    """
    통합 FDS 평가 엔진

    모든 고급 FDS 엔진을 조합하여 다층 사기 탐지를 수행합니다.
    """

    def __init__(
        self,
        db: AsyncSession,
        redis: aioredis.Redis,
        ml_model_path: Optional[str] = None,
        geoip_db_path: Optional[str] = None,
        asn_db_path: Optional[str] = None,
    ):
        """
        통합 평가 엔진 초기화

        Args:
            db: 데이터베이스 세션
            redis: Redis 클라이언트
            ml_model_path: ML 모델 파일 경로 (선택)
            geoip_db_path: GeoIP 데이터베이스 경로 (선택)
            asn_db_path: ASN 데이터베이스 경로 (선택)
        """
        self.db = db
        self.redis = redis

        # 각 엔진 초기화
        self.fingerprint_engine = FingerprintEngine()
        self.behavior_analysis_engine = BehaviorAnalysisEngine()

        # Network Analysis Engine (GeoIP 데이터베이스 경로)
        self.network_analysis_engine = None
        if geoip_db_path and asn_db_path:
            try:
                self.network_analysis_engine = NetworkAnalysisEngine(
                    geoip_db_path=geoip_db_path,
                    asn_db_path=asn_db_path,
                )
                logger.info("Network Analysis Engine initialized with GeoIP databases")
            except Exception as e:
                logger.warning(
                    f"Network Analysis Engine initialization failed: {e}. "
                    "Network analysis will be skipped."
                )

        # Fraud Rule Engine
        self.fraud_rule_engine = FraudRuleEngine(db=db, redis=redis)

        # ML Engine
        self.ml_engine = None
        if ml_model_path:
            try:
                self.ml_engine = MLEngine(model_path=ml_model_path)
                logger.info(f"ML Engine initialized with model: {ml_model_path}")
            except Exception as e:
                logger.warning(
                    f"ML Engine initialization failed: {e}. "
                    "ML-based detection will be skipped."
                )

        # 평가 시간 추적
        self._timing_stats = {
            "fingerprint_time_ms": 0,
            "behavior_time_ms": 0,
            "network_time_ms": 0,
            "rule_time_ms": 0,
            "ml_time_ms": 0,
            "total_time_ms": 0,
        }

    async def evaluate(self, request: FDSEvaluationRequest) -> FDSEvaluationResponse:
        """
        종합 FDS 평가 수행

        Args:
            request: FDS 평가 요청

        Returns:
            FDSEvaluationResponse: 평가 결과
        """
        start_time = time.time()
        risk_factors: List[RiskFactor] = []

        # 평가 시간 초기화
        self._timing_stats = {
            "fingerprint_time_ms": 0,
            "behavior_time_ms": 0,
            "network_time_ms": 0,
            "rule_time_ms": 0,
            "ml_time_ms": 0,
            "total_time_ms": 0,
        }

        # 1. 디바이스 핑거프린팅 평가
        fingerprint_factors = await self._evaluate_fingerprint(request)
        risk_factors.extend(fingerprint_factors)

        # 2. 행동 패턴 분석
        behavior_factors = await self._evaluate_behavior(request)
        risk_factors.extend(behavior_factors)

        # 3. 네트워크 분석
        network_factors = await self._evaluate_network(request)
        risk_factors.extend(network_factors)

        # 4. 룰 기반 평가
        rule_factors = await self._evaluate_rules(request)
        risk_factors.extend(rule_factors)

        # 5. ML 모델 평가
        ml_factors = await self._evaluate_ml(request)
        risk_factors.extend(ml_factors)

        # 6. 종합 위험 점수 산출
        risk_score = self._calculate_risk_score(risk_factors)

        # 7. 위험 수준 분류
        risk_level = self._classify_risk_level(risk_score, risk_factors)

        # 8. 의사결정
        decision = self._make_decision(risk_level, risk_factors)

        # 9. 권장 조치 생성
        recommended_action = self._generate_recommended_action(
            decision, risk_level, risk_score, risk_factors
        )

        # 총 평가 시간 계산
        total_time_ms = int((time.time() - start_time) * 1000)
        self._timing_stats["total_time_ms"] = total_time_ms

        # 평가 메타데이터
        metadata = EvaluationMetadata(
            evaluation_time_ms=total_time_ms,
            rule_engine_time_ms=self._timing_stats["rule_time_ms"],
            ml_engine_time_ms=self._timing_stats["ml_time_ms"],
            cti_check_time_ms=self._timing_stats["network_time_ms"],
            timestamp=datetime.utcnow(),
        )

        # 성능 로그 (P95 50ms 목표)
        if total_time_ms > 50:
            logger.warning(
                f"[PERFORMANCE] FDS evaluation took {total_time_ms}ms "
                f"(target: 50ms) - "
                f"fingerprint: {self._timing_stats['fingerprint_time_ms']}ms, "
                f"behavior: {self._timing_stats['behavior_time_ms']}ms, "
                f"network: {self._timing_stats['network_time_ms']}ms, "
                f"rule: {self._timing_stats['rule_time_ms']}ms, "
                f"ml: {self._timing_stats['ml_time_ms']}ms"
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

    async def _evaluate_fingerprint(
        self, request: FDSEvaluationRequest
    ) -> List[RiskFactor]:
        """
        디바이스 핑거프린팅 평가

        - 디바이스 ID 생성 및 검증
        - 타임존/언어 불일치 검사
        - 블랙리스트 체크 (Redis 캐시)

        Args:
            request: FDS 평가 요청

        Returns:
            List[RiskFactor]: 핑거프린팅 관련 위험 요인
        """
        start_time = time.time()
        risk_factors: List[RiskFactor] = []

        try:
            fingerprint_data = request.device_fingerprint

            # 디바이스 ID 생성
            device_id = self.fingerprint_engine.generate_device_id(
                canvas_hash=fingerprint_data.canvas_hash,
                webgl_hash=fingerprint_data.webgl_hash,
                audio_hash=fingerprint_data.audio_hash,
                cpu_cores=fingerprint_data.cpu_cores,
                screen_resolution=fingerprint_data.screen_resolution,
                timezone=fingerprint_data.timezone,
                language=fingerprint_data.language,
            )

            # Redis 블랙리스트 체크 (TTL 24시간)
            cache_key = f"fds:blacklist:device:{device_id}"
            is_blacklisted = await self.redis.get(cache_key)

            if is_blacklisted:
                risk_factors.append(
                    RiskFactor(
                        factor_type="device_blacklisted",
                        factor_score=95,
                        description=f"블랙리스트 디바이스 탐지 (ID: {device_id[:16]}...)",
                        severity=SeverityEnum.CRITICAL,
                    )
                )

            # 타임존/언어 불일치 검사
            timezone_country = self.fingerprint_engine.get_country_from_timezone(
                fingerprint_data.timezone
            )
            language_country = self.fingerprint_engine.get_country_from_language(
                fingerprint_data.language
            )

            if timezone_country and language_country:
                if timezone_country != language_country:
                    risk_factors.append(
                        RiskFactor(
                            factor_type="timezone_language_mismatch",
                            factor_score=40,
                            description=(
                                f"타임존/언어 불일치 (타임존: {timezone_country}, "
                                f"언어: {language_country})"
                            ),
                            severity=SeverityEnum.MEDIUM,
                        )
                    )

        except Exception as e:
            logger.error(f"Fingerprint evaluation failed: {e}")
            # Fail-open: 오류 발생 시 평가 계속 진행

        self._timing_stats["fingerprint_time_ms"] = int(
            (time.time() - start_time) * 1000
        )
        return risk_factors

    async def _evaluate_behavior(
        self, request: FDSEvaluationRequest
    ) -> List[RiskFactor]:
        """
        행동 패턴 분석

        - 마우스 움직임 분석 (속도, 가속도, 곡률)
        - 키보드 타이핑 분석 (입력 속도, 백스페이스 빈도)
        - 클릭스트림 분석 (페이지 체류 시간)
        - 봇 확률 점수 계산

        Args:
            request: FDS 평가 요청

        Returns:
            List[RiskFactor]: 행동 패턴 관련 위험 요인
        """
        start_time = time.time()
        risk_factors: List[RiskFactor] = []

        try:
            # 행동 데이터가 있는 경우만 분석
            if hasattr(request, "behavior_data") and request.behavior_data:
                behavior_data = request.behavior_data

                # 행동 패턴 종합 분석
                analysis_result = self.behavior_analysis_engine.analyze(
                    mouse_movements=behavior_data.get("mouse_movements", []),
                    keyboard_events=behavior_data.get("keyboard_events", []),
                    clickstream=behavior_data.get("clickstream", []),
                )

                bot_score = analysis_result.get("bot_score", 0)

                # 봇 점수가 높으면 위험 요인 추가
                if bot_score >= 85:
                    risk_factors.append(
                        RiskFactor(
                            factor_type="bot_detected_high",
                            factor_score=90,
                            description=f"자동화된 봇 탐지 (점수: {bot_score})",
                            severity=SeverityEnum.CRITICAL,
                        )
                    )
                elif bot_score >= 70:
                    risk_factors.append(
                        RiskFactor(
                            factor_type="bot_detected_medium",
                            factor_score=60,
                            description=f"봇 의심 행동 패턴 (점수: {bot_score})",
                            severity=SeverityEnum.HIGH,
                        )
                    )
                elif bot_score >= 50:
                    risk_factors.append(
                        RiskFactor(
                            factor_type="bot_detected_low",
                            factor_score=30,
                            description=f"비정상 행동 패턴 (점수: {bot_score})",
                            severity=SeverityEnum.MEDIUM,
                        )
                    )

        except Exception as e:
            logger.error(f"Behavior evaluation failed: {e}")
            # Fail-open: 오류 발생 시 평가 계속 진행

        self._timing_stats["behavior_time_ms"] = int((time.time() - start_time) * 1000)
        return risk_factors

    async def _evaluate_network(
        self, request: FDSEvaluationRequest
    ) -> List[RiskFactor]:
        """
        네트워크 분석

        - TOR Exit Node 탐지 (95% 정확도)
        - VPN/Proxy 탐지 (85% 정확도)
        - GeoIP 불일치 검사
        - ASN 평판 조회

        Args:
            request: FDS 평가 요청

        Returns:
            List[RiskFactor]: 네트워크 관련 위험 요인
        """
        start_time = time.time()
        risk_factors: List[RiskFactor] = []

        try:
            if not self.network_analysis_engine:
                # Network Analysis Engine이 초기화되지 않음
                self._timing_stats["network_time_ms"] = 0
                return risk_factors

            ip_address = request.ip_address

            # 네트워크 종합 분석
            network_result = await self.network_analysis_engine.analyze(
                ip_address=ip_address,
                billing_country=getattr(request, "billing_country", None),
            )

            # TOR 탐지
            if network_result.get("is_tor"):
                risk_factors.append(
                    RiskFactor(
                        factor_type="tor_detected",
                        factor_score=95,
                        description="TOR Exit Node 탐지",
                        severity=SeverityEnum.CRITICAL,
                    )
                )

            # VPN/Proxy 탐지
            if network_result.get("is_vpn"):
                risk_factors.append(
                    RiskFactor(
                        factor_type="vpn_detected",
                        factor_score=70,
                        description="VPN 사용 탐지",
                        severity=SeverityEnum.HIGH,
                    )
                )

            if network_result.get("is_proxy"):
                risk_factors.append(
                    RiskFactor(
                        factor_type="proxy_detected",
                        factor_score=75,
                        description="프록시 서버 사용 탐지",
                        severity=SeverityEnum.HIGH,
                    )
                )

            # GeoIP 불일치
            if network_result.get("country_mismatch"):
                risk_factors.append(
                    RiskFactor(
                        factor_type="geoip_mismatch",
                        factor_score=50,
                        description=(
                            f"GeoIP 국가 불일치 (접속: {network_result.get('geoip_country')}, "
                            f"결제: {network_result.get('billing_country')})"
                        ),
                        severity=SeverityEnum.MEDIUM,
                    )
                )

        except Exception as e:
            logger.error(f"Network evaluation failed: {e}")
            # Fail-open: 오류 발생 시 평가 계속 진행

        self._timing_stats["network_time_ms"] = int((time.time() - start_time) * 1000)
        return risk_factors

    async def _evaluate_rules(self, request: FDSEvaluationRequest) -> List[RiskFactor]:
        """
        룰 기반 평가 (30개 실전 룰)

        - Payment (결제): 테스트 카드, BIN 불일치 등 10개
        - Account (계정): 비밀번호 실패, 세션 하이재킹 등 10개
        - Shipping (배송지): 화물 전달 주소, 일회용 이메일 등 10개

        Args:
            request: FDS 평가 요청

        Returns:
            List[RiskFactor]: 룰 기반 위험 요인
        """
        start_time = time.time()
        risk_factors: List[RiskFactor] = []

        try:
            # TransactionData 생성 (룰 엔진 입력)
            transaction_data = self._convert_to_transaction_data(request)

            # 룰 엔진 평가
            rule_results = await self.fraud_rule_engine.evaluate_all_rules(
                transaction_data
            )

            # RuleResult를 RiskFactor로 변환
            for rule_result in rule_results:
                if rule_result.matched:
                    # 액션별 심각도 매핑
                    severity_map = {
                        "block": SeverityEnum.CRITICAL,
                        "manual_review": SeverityEnum.HIGH,
                        "warning": SeverityEnum.MEDIUM,
                    }

                    risk_factors.append(
                        RiskFactor(
                            factor_type=f"rule_{rule_result.rule_category.value}",
                            factor_score=rule_result.risk_score,
                            description=f"[RULE] {rule_result.description}",
                            severity=severity_map.get(
                                rule_result.action, SeverityEnum.MEDIUM
                            ),
                        )
                    )

        except Exception as e:
            logger.error(f"Rule evaluation failed: {e}")
            # Fail-open: 오류 발생 시 평가 계속 진행

        self._timing_stats["rule_time_ms"] = int((time.time() - start_time) * 1000)
        return risk_factors

    async def _evaluate_ml(self, request: FDSEvaluationRequest) -> List[RiskFactor]:
        """
        ML 모델 평가 (앙상블 모델)

        - Random Forest, XGBoost, Autoencoder, LSTM 조합
        - 가중 투표 (RF 30%, XGB 35%, AE 25%, LSTM 10%)
        - F1 Score 0.95 이상 목표

        Args:
            request: FDS 평가 요청

        Returns:
            List[RiskFactor]: ML 기반 위험 요인
        """
        start_time = time.time()
        risk_factors: List[RiskFactor] = []

        try:
            if not self.ml_engine:
                # ML Engine이 초기화되지 않음
                self._timing_stats["ml_time_ms"] = 0
                return risk_factors

            # 거래 데이터를 딕셔너리로 변환
            transaction_dict = self._convert_to_dict(request)

            # ML 평가
            ml_result = await self.ml_engine.evaluate(transaction_dict)

            anomaly_score = ml_result.get("anomaly_score", 0)
            is_anomaly = ml_result.get("is_anomaly", False)
            confidence = ml_result.get("confidence", 0)

            # 이상 탐지 결과를 RiskFactor로 변환
            if is_anomaly and anomaly_score >= 80:
                risk_factors.append(
                    RiskFactor(
                        factor_type="ml_anomaly_high",
                        factor_score=int(anomaly_score),
                        description=(
                            f"ML 이상 거래 탐지 (점수: {anomaly_score:.1f}, "
                            f"신뢰도: {confidence:.2f})"
                        ),
                        severity=SeverityEnum.HIGH,
                    )
                )
            elif is_anomaly and anomaly_score >= 60:
                risk_factors.append(
                    RiskFactor(
                        factor_type="ml_anomaly_medium",
                        factor_score=int(anomaly_score),
                        description=(
                            f"ML 의심 거래 탐지 (점수: {anomaly_score:.1f}, "
                            f"신뢰도: {confidence:.2f})"
                        ),
                        severity=SeverityEnum.MEDIUM,
                    )
                )

        except Exception as e:
            logger.error(f"ML evaluation failed: {e}")
            # Fail-open: 오류 발생 시 평가 계속 진행

        self._timing_stats["ml_time_ms"] = int((time.time() - start_time) * 1000)
        return risk_factors

    def _convert_to_transaction_data(
        self, request: FDSEvaluationRequest
    ) -> TransactionData:
        """
        FDSEvaluationRequest를 TransactionData로 변환

        Args:
            request: FDS 평가 요청

        Returns:
            TransactionData: 룰 엔진 입력 데이터
        """
        # 카드 정보 추출
        card_number = ""
        if hasattr(request, "payment_method") and request.payment_method:
            card_number = request.payment_method.get("card_number", "")

        card_bin = card_number[:6] if len(card_number) >= 6 else ""
        card_last4 = card_number[-4:] if len(card_number) >= 4 else ""

        return TransactionData(
            transaction_id=request.transaction_id,
            user_id=request.user_id,
            user_email=getattr(request, "user_email", "unknown@example.com"),
            card_number=card_number,
            card_bin=card_bin,
            card_last4=card_last4,
            amount=Decimal(str(request.amount)),
            currency=getattr(request, "currency", "KRW"),
            ip_address=request.ip_address,
            user_agent=getattr(request, "user_agent", ""),
            shipping_address=getattr(request, "shipping_address", ""),
            shipping_city=getattr(request, "shipping_city", ""),
            shipping_country=getattr(request, "shipping_country", ""),
            billing_country=getattr(request, "billing_country", ""),
            device_id=getattr(request.device_fingerprint, "device_id", None),
            session_id=getattr(request, "session_id", None),
            created_at=datetime.utcnow(),
        )

    def _convert_to_dict(self, request: FDSEvaluationRequest) -> Dict[str, Any]:
        """
        FDSEvaluationRequest를 딕셔너리로 변환 (ML 입력)

        Args:
            request: FDS 평가 요청

        Returns:
            Dict[str, Any]: ML 엔진 입력 데이터
        """
        return {
            "transaction_id": str(request.transaction_id),
            "user_id": str(request.user_id),
            "amount": float(request.amount),
            "ip_address": request.ip_address,
            "device_type": request.device_fingerprint.device_type,
            "user_behavior": getattr(request, "behavior_data", {}),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _calculate_risk_score(self, risk_factors: List[RiskFactor]) -> int:
        """
        종합 위험 점수 계산

        - 모든 위험 요인의 점수를 합산
        - 최대 100점으로 제한
        - CRITICAL 요인이 있으면 최소 90점 보장

        Args:
            risk_factors: 위험 요인 목록

        Returns:
            int: 종합 위험 점수 (0-100)
        """
        total_score = sum(factor.factor_score for factor in risk_factors)

        # CRITICAL 요인이 있으면 최소 90점 보장
        has_critical = any(
            factor.severity == SeverityEnum.CRITICAL for factor in risk_factors
        )
        if has_critical and total_score < 90:
            total_score = 90

        # 최대 100점으로 제한
        return min(total_score, 100)

    def _classify_risk_level(
        self, risk_score: int, risk_factors: List[RiskFactor]
    ) -> RiskLevelEnum:
        """
        위험 수준 분류

        - CRITICAL 요인이 있으면 HIGH
        - 점수 기반 분류: 0-30 (LOW), 31-70 (MEDIUM), 71-100 (HIGH)

        Args:
            risk_score: 위험 점수
            risk_factors: 위험 요인 목록

        Returns:
            RiskLevelEnum: 위험 수준
        """
        # CRITICAL 요인이 있으면 자동으로 HIGH
        has_critical = any(
            factor.severity == SeverityEnum.CRITICAL for factor in risk_factors
        )
        if has_critical:
            return RiskLevelEnum.HIGH

        # 점수 기반 분류
        if risk_score <= 30:
            return RiskLevelEnum.LOW
        elif risk_score <= 70:
            return RiskLevelEnum.MEDIUM
        else:
            return RiskLevelEnum.HIGH

    def _make_decision(
        self, risk_level: RiskLevelEnum, risk_factors: List[RiskFactor]
    ) -> DecisionEnum:
        """
        의사결정

        - HIGH: BLOCKED
        - MEDIUM: ADDITIONAL_AUTH_REQUIRED
        - LOW: APPROVE
        - BLOCK 액션 룰이 매칭되면 무조건 BLOCKED

        Args:
            risk_level: 위험 수준
            risk_factors: 위험 요인 목록

        Returns:
            DecisionEnum: 의사결정
        """
        # BLOCK 액션 룰이 있으면 무조건 차단
        has_block_rule = any(
            factor.factor_type.startswith("rule_") and factor.factor_score >= 90
            for factor in risk_factors
        )
        if has_block_rule:
            return DecisionEnum.BLOCKED

        # 위험 수준 기반 결정
        if risk_level == RiskLevelEnum.HIGH:
            return DecisionEnum.BLOCKED
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
        """
        권장 조치 생성

        Args:
            decision: 의사결정
            risk_level: 위험 수준
            risk_score: 위험 점수
            risk_factors: 위험 요인 목록

        Returns:
            RecommendedAction: 권장 조치
        """
        # 주요 위험 요인 추출 (상위 3개)
        top_factors = sorted(risk_factors, key=lambda x: x.factor_score, reverse=True)[
            :3
        ]
        top_factor_descriptions = [f.description for f in top_factors]

        if decision == DecisionEnum.APPROVE:
            return RecommendedAction(
                action=DecisionEnum.APPROVE,
                reason=f"위험 점수가 낮은 정상 거래 (점수: {risk_score})",
                additional_auth_required=False,
            )
        elif decision == DecisionEnum.ADDITIONAL_AUTH_REQUIRED:
            return RecommendedAction(
                action=DecisionEnum.ADDITIONAL_AUTH_REQUIRED,
                reason=(
                    f"중간 위험도 거래 탐지 (점수: {risk_score}). "
                    f"주요 요인: {', '.join(top_factor_descriptions[:2])}"
                ),
                additional_auth_required=True,
                auth_methods=["otp_sms", "biometric"],
                auth_timeout_seconds=300,  # 5분
            )
        else:  # BLOCKED
            return RecommendedAction(
                action=DecisionEnum.BLOCKED,
                reason=(
                    f"고위험 거래 탐지 (점수: {risk_score}). "
                    f"주요 요인: {', '.join(top_factor_descriptions[:3])}"
                ),
                additional_auth_required=False,
                manual_review_required=True,
                review_queue_id=None,  # 검토 큐 ID는 별도 서비스에서 생성
            )
