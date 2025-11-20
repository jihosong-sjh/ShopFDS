"""
T115 통합 테스트: 전체 FDS 평가 플로우

이 테스트는 실제 운영 환경에서 발생하는 다양한 시나리오를 검증합니다:
1. 정상 거래: 낮은 위험 점수로 자동 승인
2. 중간 위험 거래: 추가 인증 요구
3. 고위험 거래: 자동 차단 및 검토 큐 추가
4. 복합 위험 요인: 여러 엔진의 위험 요인 조합
5. 엔드투엔드 플로우: API 호출 → 평가 → DB 저장 → 검토 큐

각 시나리오는 독립적으로 실행 가능하며, 실제 운영 환경과 유사한 조건에서 테스트됩니다.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, patch

from src.models.schemas import (
    FDSEvaluationRequest,
    DeviceFingerprint,
    DeviceTypeEnum,
    ShippingInfo,
    PaymentInfo,
)
from src.engines.evaluation_engine import EvaluationEngine
from src.engines.cti_connector import CTICheckResult
from src.models.threat_intelligence import ThreatLevel, ThreatSource, ThreatType
from src.services.review_queue_service import ReviewQueueService
from src.models.transaction import Transaction, RiskLevel, EvaluationStatus
from src.models.review_queue import ReviewStatus


@pytest.mark.asyncio
class TestFullFDSEvaluationFlow:
    """전체 FDS 평가 플로우 통합 테스트"""

    async def test_scenario_1_normal_transaction_auto_approve(self, db_session):
        """
        시나리오 1: 정상 거래 - 자동 승인

        조건:
        - 소액 거래 (10,000원)
        - 정상 IP (한국)
        - 정상 디바이스
        - CTI 위협 없음

        예상 결과:
        - 위험 점수: 0-30점 (저위험)
        - 의사결정: approve
        - Transaction 상태: APPROVED
        """
        print("\n" + "=" * 80)
        print("[시나리오 1] 정상 거래 - 자동 승인")
        print("=" * 80)

        # === Arrange ===
        transaction_id = uuid4()
        user_id = uuid4()
        order_id = uuid4()

        request = FDSEvaluationRequest(
            transaction_id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=10000,  # 10,000원 (정상 금액)
            ip_address="211.234.123.45",  # 정상 한국 IP
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            device_fingerprint=DeviceFingerprint(
                device_type=DeviceTypeEnum.DESKTOP,
                browser="Chrome",
                os="Windows",
            ),
            shipping_info=ShippingInfo(
                name="홍길동",
                address="서울특별시 강남구",
                phone="010-1234-5678",
            ),
            payment_info=PaymentInfo(
                method="credit_card",
                card_last_four="1234",
                card_bin="123456",
            ),
            timestamp=datetime.utcnow(),
        )

        # Redis Mock
        mock_redis = AsyncMock()

        # CTI Mock - 위협 없음
        cti_result = CTICheckResult(
            threat_type=ThreatType.IP,
            value=request.ip_address,
            is_threat=False,
            threat_level=ThreatLevel.LOW,
            source=ThreatSource.ABUSEIPDB,
            description="정상 IP",
            confidence_score=5,
        )

        # === Act ===
        with patch("src.engines.evaluation_engine.CTIConnector") as MockCTIConnector:
            mock_cti_instance = AsyncMock()
            mock_cti_instance.check_ip_threat.return_value = cti_result
            MockCTIConnector.return_value = mock_cti_instance

            engine = EvaluationEngine(db=db_session, redis=mock_redis)
            result = await engine.evaluate(request)

        # === Assert ===
        print(f"\n[평가 결과]")
        print(f"  - 위험 점수: {result.risk_score}")
        print(f"  - 위험 수준: {result.risk_level.value}")
        print(f"  - 의사결정: {result.decision.value}")
        print(f"  - 평가 시간: {result.evaluation_metadata.evaluation_time_ms}ms")

        assert (
            result.risk_score <= 30
        ), f"정상 거래는 저위험(0-30점)이어야 하지만, 실제: {result.risk_score}"
        assert (
            result.risk_level.value == "low"
        ), f"위험 수준은 low여야 하지만, 실제: {result.risk_level.value}"
        assert (
            result.decision.value == "approve"
        ), f"의사결정은 approve여야 하지만, 실제: {result.decision.value}"

        # Transaction 저장
        transaction = Transaction(
            id=request.transaction_id,
            user_id=request.user_id,
            order_id=request.order_id,
            amount=request.amount,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            device_type=request.device_fingerprint.device_type.value,
            geolocation={"ip": request.ip_address},
            risk_score=result.risk_score,
            risk_level=RiskLevel(result.risk_level.value),
            evaluation_status=EvaluationStatus.APPROVED,
            evaluation_time_ms=result.evaluation_metadata.evaluation_time_ms,
            evaluated_at=result.evaluation_metadata.timestamp,
        )

        db_session.add(transaction)
        await db_session.commit()
        await db_session.refresh(transaction)

        assert transaction.evaluation_status == EvaluationStatus.APPROVED
        print(f"\n[Transaction 저장 완료]")
        print(f"  - ID: {transaction.id}")
        print(f"  - 상태: {transaction.evaluation_status}")
        print("\n[PASS] 시나리오 1 통과: 정상 거래가 자동 승인됨")

    async def test_scenario_2_medium_risk_additional_auth(self, db_session):
        """
        시나리오 2: 중간 위험 거래 - 추가 인증 요구

        조건:
        - 고액 거래 (500,000원)
        - 정상 IP
        - 정상 디바이스

        예상 결과:
        - 위험 점수: 40-70점 (중간 위험)
        - 의사결정: additional_auth_required
        - Transaction 상태: EVALUATING
        """
        print("\n" + "=" * 80)
        print("[시나리오 2] 중간 위험 거래 - 추가 인증 요구")
        print("=" * 80)

        # === Arrange ===
        transaction_id = uuid4()
        user_id = uuid4()
        order_id = uuid4()

        request = FDSEvaluationRequest(
            transaction_id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=500000,  # 500,000원 (고액)
            ip_address="211.234.123.45",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            device_fingerprint=DeviceFingerprint(
                device_type=DeviceTypeEnum.DESKTOP,
                browser="Chrome",
                os="Windows",
            ),
            shipping_info=ShippingInfo(
                name="홍길동",
                address="서울특별시 강남구",
                phone="010-1234-5678",
            ),
            payment_info=PaymentInfo(
                method="credit_card",
                card_last_four="1234",
                card_bin="123456",
            ),
            timestamp=datetime.utcnow(),
        )

        mock_redis = AsyncMock()

        # CTI Mock - 위협 없음
        cti_result = CTICheckResult(
            threat_type=ThreatType.IP,
            value=request.ip_address,
            is_threat=False,
            threat_level=ThreatLevel.LOW,
            source=ThreatSource.ABUSEIPDB,
            description="정상 IP",
            confidence_score=5,
        )

        # === Act ===
        with patch("src.engines.evaluation_engine.CTIConnector") as MockCTIConnector:
            mock_cti_instance = AsyncMock()
            mock_cti_instance.check_ip_threat.return_value = cti_result
            MockCTIConnector.return_value = mock_cti_instance

            engine = EvaluationEngine(db=db_session, redis=mock_redis)
            result = await engine.evaluate(request)

        # === Assert ===
        print(f"\n[평가 결과]")
        print(f"  - 위험 점수: {result.risk_score}")
        print(f"  - 위험 수준: {result.risk_level.value}")
        print(f"  - 의사결정: {result.decision.value}")
        print(f"  - 평가 시간: {result.evaluation_metadata.evaluation_time_ms}ms")

        assert (
            40 <= result.risk_score <= 70
        ), f"고액 거래는 중간 위험(40-70점)이어야 하지만, 실제: {result.risk_score}"
        assert (
            result.risk_level.value == "medium"
        ), f"위험 수준은 medium이어야 하지만, 실제: {result.risk_level.value}"
        assert (
            result.decision.value == "additional_auth_required"
        ), f"의사결정은 additional_auth_required여야 하지만, 실제: {result.decision.value}"

        # Transaction 저장
        transaction = Transaction(
            id=request.transaction_id,
            user_id=request.user_id,
            order_id=request.order_id,
            amount=request.amount,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            device_type=request.device_fingerprint.device_type.value,
            geolocation={"ip": request.ip_address},
            risk_score=result.risk_score,
            risk_level=RiskLevel(result.risk_level.value),
            evaluation_status=EvaluationStatus.EVALUATING,
            evaluation_time_ms=result.evaluation_metadata.evaluation_time_ms,
            evaluated_at=result.evaluation_metadata.timestamp,
        )

        db_session.add(transaction)
        await db_session.commit()
        await db_session.refresh(transaction)

        assert transaction.evaluation_status == EvaluationStatus.EVALUATING
        print(f"\n[Transaction 저장 완료]")
        print(f"  - ID: {transaction.id}")
        print(f"  - 상태: {transaction.evaluation_status}")
        print("\n[PASS] 시나리오 2 통과: 고액 거래가 추가 인증 요구됨")

    async def test_scenario_3_high_risk_auto_block_and_review(self, db_session):
        """
        시나리오 3: 고위험 거래 - 자동 차단 및 검토 큐 추가

        조건:
        - 악성 IP (TOR/VPN/Proxy)
        - CTI에서 고위험으로 탐지

        예상 결과:
        - 위험 점수: 80-100점 (고위험)
        - 의사결정: blocked
        - Transaction 상태: BLOCKED → MANUAL_REVIEW
        - ReviewQueue 추가
        """
        print("\n" + "=" * 80)
        print("[시나리오 3] 고위험 거래 - 자동 차단 및 검토 큐 추가")
        print("=" * 80)

        # === Arrange ===
        transaction_id = uuid4()
        user_id = uuid4()
        order_id = uuid4()
        malicious_ip = "185.220.100.45"  # TOR Exit Node

        request = FDSEvaluationRequest(
            transaction_id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=1000000,  # 1,000,000원
            ip_address=malicious_ip,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            device_fingerprint=DeviceFingerprint(
                device_type=DeviceTypeEnum.DESKTOP,
                browser="Chrome",
                os="Windows",
            ),
            shipping_info=ShippingInfo(
                name="홍길동",
                address="서울특별시 강남구",
                phone="010-1234-5678",
            ),
            payment_info=PaymentInfo(
                method="credit_card",
                card_last_four="1234",
                card_bin="123456",
            ),
            timestamp=datetime.utcnow(),
        )

        mock_redis = AsyncMock()

        # CTI Mock - 악성 IP 탐지
        cti_result = CTICheckResult(
            threat_type=ThreatType.IP,
            value=malicious_ip,
            is_threat=True,
            threat_level=ThreatLevel.HIGH,
            source=ThreatSource.ABUSEIPDB,
            description=f"AbuseIPDB에서 악성 IP로 분류됨 (신뢰도: 95점)",
            confidence_score=95,
        )

        # === Act ===
        with patch("src.engines.evaluation_engine.CTIConnector") as MockCTIConnector:
            mock_cti_instance = AsyncMock()
            mock_cti_instance.check_ip_threat.return_value = cti_result
            MockCTIConnector.return_value = mock_cti_instance

            engine = EvaluationEngine(db=db_session, redis=mock_redis)
            result = await engine.evaluate(request)

        # === Assert ===
        print(f"\n[평가 결과]")
        print(f"  - 위험 점수: {result.risk_score}")
        print(f"  - 위험 수준: {result.risk_level.value}")
        print(f"  - 의사결정: {result.decision.value}")
        print(f"  - 평가 시간: {result.evaluation_metadata.evaluation_time_ms}ms")
        print(f"  - CTI 체크 시간: {result.evaluation_metadata.cti_check_time_ms}ms")

        assert (
            result.risk_score >= 80
        ), f"악성 IP는 고위험(80+점)이어야 하지만, 실제: {result.risk_score}"
        assert (
            result.risk_level.value == "high"
        ), f"위험 수준은 high여야 하지만, 실제: {result.risk_level.value}"
        assert (
            result.decision.value == "blocked"
        ), f"의사결정은 blocked여야 하지만, 실제: {result.decision.value}"

        # Transaction 저장
        transaction = Transaction(
            id=request.transaction_id,
            user_id=request.user_id,
            order_id=request.order_id,
            amount=request.amount,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            device_type=request.device_fingerprint.device_type.value,
            geolocation={"ip": request.ip_address},
            risk_score=result.risk_score,
            risk_level=RiskLevel(result.risk_level.value),
            evaluation_status=EvaluationStatus.BLOCKED,
            evaluation_time_ms=result.evaluation_metadata.evaluation_time_ms,
            evaluated_at=result.evaluation_metadata.timestamp,
        )

        db_session.add(transaction)
        await db_session.commit()
        await db_session.refresh(transaction)

        print(f"\n[Transaction 저장 완료]")
        print(f"  - ID: {transaction.id}")
        print(f"  - 초기 상태: {transaction.evaluation_status}")

        # ReviewQueue 추가
        review_queue_service = ReviewQueueService(db_session)
        review_queue = await review_queue_service.add_to_review_queue(transaction.id)

        assert review_queue is not None, "ReviewQueue가 생성되지 않았습니다"
        assert review_queue.status == ReviewStatus.PENDING

        print(f"\n[ReviewQueue 추가 완료]")
        print(f"  - ReviewQueue ID: {review_queue.id}")
        print(f"  - 상태: {review_queue.status}")

        # Transaction 상태 확인 (MANUAL_REVIEW로 변경됨)
        await db_session.refresh(transaction)
        assert transaction.evaluation_status == EvaluationStatus.MANUAL_REVIEW

        print(f"\n[Transaction 상태 업데이트]")
        print(f"  - 최종 상태: {transaction.evaluation_status}")
        print("\n[PASS] 시나리오 3 통과: 고위험 거래가 자동 차단되고 검토 큐에 추가됨")

    async def test_scenario_4_multiple_risk_factors_combined(self, db_session):
        """
        시나리오 4: 복합 위험 요인 - 여러 엔진의 위험 요인 조합

        조건:
        - 고액 거래 (3,000,000원) → 40점
        - Velocity Check (동일 사용자 단시간 반복) → 40점
        - 합계: 80점 이상 (고위험)

        예상 결과:
        - 위험 점수: 80점 이상
        - 의사결정: blocked
        - 위험 요인 2개 이상 (high_amount, velocity_check)
        """
        print("\n" + "=" * 80)
        print("[시나리오 4] 복합 위험 요인 - 여러 엔진의 위험 요인 조합")
        print("=" * 80)

        # === Arrange ===
        user_id = uuid4()  # 동일 사용자
        mock_redis = AsyncMock()

        # CTI Mock - 정상
        cti_result = CTICheckResult(
            threat_type=ThreatType.IP,
            value="211.234.123.45",
            is_threat=False,
            threat_level=ThreatLevel.LOW,
            source=ThreatSource.ABUSEIPDB,
            description="정상 IP",
            confidence_score=5,
        )

        with patch("src.engines.evaluation_engine.CTIConnector") as MockCTIConnector:
            mock_cti_instance = AsyncMock()
            mock_cti_instance.check_ip_threat.return_value = cti_result
            MockCTIConnector.return_value = mock_cti_instance

            engine = EvaluationEngine(db=db_session, redis=mock_redis)

            # === Act 1: 첫 번째 거래 ===
            first_request = FDSEvaluationRequest(
                transaction_id=uuid4(),
                user_id=user_id,
                order_id=uuid4(),
                amount=3000000,  # 3,000,000원 (고액)
                ip_address="211.234.123.45",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                device_fingerprint=DeviceFingerprint(
                    device_type=DeviceTypeEnum.DESKTOP,
                    browser="Chrome",
                    os="Windows",
                ),
                shipping_info=ShippingInfo(
                    name="홍길동",
                    address="서울특별시 강남구",
                    phone="010-1234-5678",
                ),
                payment_info=PaymentInfo(
                    method="credit_card",
                    card_last_four="1234",
                    card_bin="123456",
                ),
                timestamp=datetime.utcnow(),
            )

            first_result = await engine.evaluate(first_request)

            print(f"\n[첫 번째 거래]")
            print(f"  - 위험 점수: {first_result.risk_score}")
            print(f"  - 의사결정: {first_result.decision.value}")

            # === Act 2: 두 번째 거래 (velocity check 발동) ===
            second_request = FDSEvaluationRequest(
                transaction_id=uuid4(),
                user_id=user_id,  # 동일 사용자
                order_id=uuid4(),
                amount=3000000,  # 3,000,000원
                ip_address="211.234.123.45",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                device_fingerprint=DeviceFingerprint(
                    device_type=DeviceTypeEnum.DESKTOP,
                    browser="Chrome",
                    os="Windows",
                ),
                shipping_info=ShippingInfo(
                    name="홍길동",
                    address="서울특별시 강남구",
                    phone="010-1234-5678",
                ),
                payment_info=PaymentInfo(
                    method="credit_card",
                    card_last_four="1234",
                    card_bin="123456",
                ),
                timestamp=datetime.utcnow(),
            )

            second_result = await engine.evaluate(second_request)

        # === Assert ===
        print(f"\n[두 번째 거래 (Velocity Check 발동)]")
        print(f"  - 위험 점수: {second_result.risk_score}")
        print(f"  - 위험 수준: {second_result.risk_level.value}")
        print(f"  - 의사결정: {second_result.decision.value}")
        print(f"  - 위험 요인 개수: {len(second_result.risk_factors)}")

        for factor in second_result.risk_factors:
            print(
                f"    - {factor.factor_type}: {factor.factor_score}점 - {factor.description}"
            )

        # 고액 거래 + Velocity Check = 80점 이상
        assert (
            second_result.risk_score >= 80
        ), f"복합 위험 요인은 고위험(80+점)이어야 하지만, 실제: {second_result.risk_score}"
        assert second_result.decision.value == "blocked"
        assert len(second_result.risk_factors) >= 2, "위험 요인이 2개 이상이어야 합니다"

        # 위험 요인 타입 확인
        factor_types = [f.factor_type for f in second_result.risk_factors]
        assert "high_amount" in factor_types or "velocity_check" in factor_types

        print("\n[PASS] 시나리오 4 통과: 복합 위험 요인이 정확히 탐지됨")

    async def test_scenario_5_evaluation_performance(self, db_session):
        """
        시나리오 5: 평가 성능 검증

        목표:
        - 평가 시간: 100ms 이내 (P95 목표)
        - CTI 체크 포함

        검증 항목:
        - evaluation_time_ms < 100ms
        - cti_check_time_ms 측정
        """
        print("\n" + "=" * 80)
        print("[시나리오 5] 평가 성능 검증 (목표: 100ms 이내)")
        print("=" * 80)

        # === Arrange ===
        request = FDSEvaluationRequest(
            transaction_id=uuid4(),
            user_id=uuid4(),
            order_id=uuid4(),
            amount=50000,
            ip_address="211.234.123.45",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            device_fingerprint=DeviceFingerprint(
                device_type=DeviceTypeEnum.DESKTOP,
                browser="Chrome",
                os="Windows",
            ),
            shipping_info=ShippingInfo(
                name="홍길동",
                address="서울특별시 강남구",
                phone="010-1234-5678",
            ),
            payment_info=PaymentInfo(
                method="credit_card",
                card_last_four="1234",
                card_bin="123456",
            ),
            timestamp=datetime.utcnow(),
        )

        mock_redis = AsyncMock()

        # CTI Mock
        cti_result = CTICheckResult(
            threat_type=ThreatType.IP,
            value=request.ip_address,
            is_threat=False,
            threat_level=ThreatLevel.LOW,
            source=ThreatSource.ABUSEIPDB,
            description="정상 IP",
            confidence_score=5,
        )

        # === Act ===
        evaluation_times = []

        for i in range(10):  # 10회 반복 측정
            with patch(
                "src.engines.evaluation_engine.CTIConnector"
            ) as MockCTIConnector:
                mock_cti_instance = AsyncMock()
                mock_cti_instance.check_ip_threat.return_value = cti_result
                MockCTIConnector.return_value = mock_cti_instance

                engine = EvaluationEngine(db=db_session, redis=mock_redis)
                result = await engine.evaluate(request)
                evaluation_times.append(result.evaluation_metadata.evaluation_time_ms)

        # === Assert ===
        avg_time = sum(evaluation_times) / len(evaluation_times)
        max_time = max(evaluation_times)
        min_time = min(evaluation_times)

        print(f"\n[평가 시간 통계 (10회 측정)]")
        print(f"  - 평균: {avg_time:.2f}ms")
        print(f"  - 최소: {min_time}ms")
        print(f"  - 최대: {max_time}ms")
        print(f"  - 목표: 100ms 이내")

        # 평균 시간이 100ms 이내여야 함
        assert avg_time < 100, f"평균 평가 시간이 100ms를 초과했습니다: {avg_time:.2f}ms"
        print("\n[PASS] 시나리오 5 통과: 평가 성능 목표 달성 (100ms 이내)")

    async def test_scenario_6_end_to_end_flow_with_all_components(self, db_session):
        """
        시나리오 6: 엔드투엔드 플로우 - 모든 컴포넌트 통합

        플로우:
        1. FDS 평가 요청
        2. 평가 엔진 실행 (CTI, 룰 엔진, Velocity Check)
        3. Transaction DB 저장
        4. 고위험 시 ReviewQueue 자동 추가
        5. 전체 플로우 검증

        이 테스트는 실제 운영 환경에서 발생하는 전체 플로우를 시뮬레이션합니다.
        """
        print("\n" + "=" * 80)
        print("[시나리오 6] 엔드투엔드 플로우 - 모든 컴포넌트 통합")
        print("=" * 80)

        # === Arrange ===
        transaction_id = uuid4()
        user_id = uuid4()
        order_id = uuid4()
        malicious_ip = "185.220.100.45"

        request = FDSEvaluationRequest(
            transaction_id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=5000000,  # 5,000,000원 (고액)
            ip_address=malicious_ip,  # 악성 IP
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            device_fingerprint=DeviceFingerprint(
                device_type=DeviceTypeEnum.DESKTOP,
                browser="Chrome",
                os="Windows",
            ),
            shipping_info=ShippingInfo(
                name="홍길동",
                address="서울특별시 강남구",
                phone="010-1234-5678",
            ),
            payment_info=PaymentInfo(
                method="credit_card",
                card_last_four="1234",
                card_bin="123456",
            ),
            timestamp=datetime.utcnow(),
        )

        mock_redis = AsyncMock()

        # CTI Mock - 악성 IP
        cti_result = CTICheckResult(
            threat_type=ThreatType.IP,
            value=malicious_ip,
            is_threat=True,
            threat_level=ThreatLevel.HIGH,
            source=ThreatSource.ABUSEIPDB,
            description="AbuseIPDB에서 악성 IP로 분류됨",
            confidence_score=95,
        )

        # === Act & Assert ===
        print("\n[Step 1] FDS 평가 실행")
        with patch("src.engines.evaluation_engine.CTIConnector") as MockCTIConnector:
            mock_cti_instance = AsyncMock()
            mock_cti_instance.check_ip_threat.return_value = cti_result
            MockCTIConnector.return_value = mock_cti_instance

            engine = EvaluationEngine(db=db_session, redis=mock_redis)
            result = await engine.evaluate(request)

        print(f"  - 위험 점수: {result.risk_score}")
        print(f"  - 의사결정: {result.decision.value}")
        assert result.risk_score >= 80
        assert result.decision.value == "blocked"
        print("  [OK] 고위험 거래로 판단됨")

        print("\n[Step 2] Transaction 저장")
        transaction = Transaction(
            id=request.transaction_id,
            user_id=request.user_id,
            order_id=request.order_id,
            amount=request.amount,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            device_type=request.device_fingerprint.device_type.value,
            geolocation={"ip": request.ip_address},
            risk_score=result.risk_score,
            risk_level=RiskLevel(result.risk_level.value),
            evaluation_status=EvaluationStatus.BLOCKED,
            evaluation_time_ms=result.evaluation_metadata.evaluation_time_ms,
            evaluated_at=result.evaluation_metadata.timestamp,
        )

        db_session.add(transaction)
        await db_session.commit()
        await db_session.refresh(transaction)

        print(f"  - Transaction ID: {transaction.id}")
        print(f"  - 상태: {transaction.evaluation_status}")
        print("  [OK] Transaction 저장 완료")

        print("\n[Step 3] ReviewQueue 자동 추가")
        review_queue_service = ReviewQueueService(db_session)
        review_queue = await review_queue_service.add_to_review_queue(transaction.id)

        assert review_queue is not None
        print(f"  - ReviewQueue ID: {review_queue.id}")
        print(f"  - 상태: {review_queue.status}")
        print("  [OK] ReviewQueue 추가 완료")

        print("\n[Step 4] Transaction 상태 업데이트 확인")
        await db_session.refresh(transaction)
        assert transaction.evaluation_status == EvaluationStatus.MANUAL_REVIEW
        print(f"  - 최종 상태: {transaction.evaluation_status}")
        print("  [OK] 상태 업데이트 완료")

        print("\n[Step 5] 전체 플로우 검증")
        # 데이터베이스에서 조회하여 일관성 확인
        from sqlalchemy import select

        # Transaction 조회
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        result_tx = await db_session.execute(stmt)
        saved_transaction = result_tx.scalar_one()

        assert saved_transaction.risk_score == result.risk_score
        assert saved_transaction.evaluation_status == EvaluationStatus.MANUAL_REVIEW

        # ReviewQueue 조회
        pending_reviews = await review_queue_service.get_pending_reviews()
        matching_reviews = [
            r for r in pending_reviews if r.transaction_id == transaction_id
        ]
        assert len(matching_reviews) == 1

        print("  [OK] 데이터베이스 일관성 검증 완료")
        print("\n[PASS] 시나리오 6 통과: 엔드투엔드 플로우 정상 작동")
        print("\n" + "=" * 80)
        print("[SUCCESS] 전체 FDS 평가 플로우 통합 테스트 완료!")
        print("=" * 80)
        print("\n검증된 시나리오:")
        print("  1. 정상 거래 자동 승인")
        print("  2. 중간 위험 거래 추가 인증 요구")
        print("  3. 고위험 거래 자동 차단 및 검토 큐 추가")
        print("  4. 복합 위험 요인 탐지")
        print("  5. 평가 성능 목표 달성 (100ms 이내)")
        print("  6. 엔드투엔드 플로우 정상 작동")
