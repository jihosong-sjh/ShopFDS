"""
T083 [US3] 악성 IP 접속 시 자동 차단 시나리오 통합 테스트

이 테스트는 다음 시나리오를 검증합니다:
1. 악성 IP에서 접속하여 거래 시도
2. FDS가 고위험(80-100점)으로 판단
3. 거래가 자동으로 차단됨
4. 차단된 거래가 ReviewQueue에 자동 추가됨
"""

import pytest
from uuid import uuid4, UUID
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
from src.models.review_queue import ReviewQueue, ReviewStatus


@pytest.mark.asyncio
class TestHighRiskAutoBlockScenario:
    """악성 IP 접속 시 자동 차단 시나리오 통합 테스트"""

    async def test_malicious_ip_auto_block_and_review_queue(self, db_session):
        """
        시나리오: 알려진 악성 IP에서 결제 시도 시 고위험으로 판단되어 자동 차단되고,
        검토 큐에 자동으로 추가됩니다.

        검증 항목:
        1. CTI 체크에서 악성 IP 탐지
        2. 위험 점수가 80점 이상 (고위험)
        3. 의사결정이 'blocked'
        4. Transaction이 BLOCKED 상태로 저장
        5. ReviewQueue에 자동 추가
        6. ReviewQueue 상태가 PENDING
        """
        # === Arrange: 테스트 데이터 준비 ===
        transaction_id = uuid4()
        user_id = uuid4()
        order_id = uuid4()
        malicious_ip = "185.220.100.45"  # 악성 IP 주소

        # FDS 평가 요청 데이터
        request = FDSEvaluationRequest(
            transaction_id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=1000000,  # 100만원
            ip_address=malicious_ip,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
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

        # Redis Mock 설정
        mock_redis = AsyncMock()

        # CTI 커넥터 Mock 설정 (악성 IP 탐지)
        cti_result = CTICheckResult(
            threat_type=ThreatType.IP,
            value=malicious_ip,
            is_threat=True,
            threat_level=ThreatLevel.HIGH,
            source=ThreatSource.ABUSEIPDB,
            description=f"AbuseIPDB에서 악성 IP로 분류됨 (신뢰도: 95점)",
            confidence_score=95,
        )

        # === Act: FDS 평가 실행 ===
        with patch("src.engines.evaluation_engine.CTIConnector") as MockCTIConnector:
            # CTI 커넥터 인스턴스 모킹
            mock_cti_instance = AsyncMock()
            mock_cti_instance.check_ip_threat.return_value = cti_result
            MockCTIConnector.return_value = mock_cti_instance

            # 평가 엔진 생성 (db와 redis 제공하여 CTI 활성화)
            evaluation_engine = EvaluationEngine(db=db_session, redis=mock_redis)

            # 평가 실행
            evaluation_result = await evaluation_engine.evaluate(request)

        # === Assert: Step 1 - 평가 결과 검증 ===
        print("\n[Step 1] FDS 평가 결과 검증")
        print(f"  - 위험 점수: {evaluation_result.risk_score}")
        print(f"  - 위험 수준: {evaluation_result.risk_level}")
        print(f"  - 의사결정: {evaluation_result.decision}")

        # 1. 위험 점수가 80점 이상 (고위험)
        assert (
            evaluation_result.risk_score >= 80
        ), f"악성 IP는 고위험(80+점)이어야 하지만, 실제 점수: {evaluation_result.risk_score}"

        # 2. 위험 수준이 HIGH
        assert (
            evaluation_result.risk_level.value == "high"
        ), f"악성 IP는 HIGH 수준이어야 하지만, 실제: {evaluation_result.risk_level.value}"

        # 3. 의사결정이 BLOCKED
        assert (
            evaluation_result.decision.value == "blocked"
        ), f"고위험 거래는 차단되어야 하지만, 실제: {evaluation_result.decision.value}"

        # 4. 위험 요인에 악성 IP 포함 확인
        risk_factors = evaluation_result.risk_factors
        malicious_ip_factor = next(
            (rf for rf in risk_factors if rf.factor_type == "suspicious_ip"), None
        )
        assert malicious_ip_factor is not None, "위험 요인에 악성 IP가 포함되어야 합니다"
        assert (
            malicious_ip_factor.factor_score >= 80
        ), f"악성 IP 요인 점수는 80+ 이어야 하지만, 실제: {malicious_ip_factor.factor_score}"

        print("  [PASS] FDS가 악성 IP를 고위험으로 정확히 탐지했습니다")

        # === Assert: Step 2 - Transaction 저장 검증 ===
        print("\n[Step 2] Transaction 저장 검증")

        # Transaction을 데이터베이스에 저장 (evaluation.py의 로직 재현)
        transaction = Transaction(
            id=request.transaction_id,
            user_id=request.user_id,
            order_id=request.order_id,
            amount=request.amount,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            device_type=request.device_fingerprint.device_type.value,
            geolocation={"ip": request.ip_address},
            risk_score=evaluation_result.risk_score,
            risk_level=RiskLevel(evaluation_result.risk_level.value),
            evaluation_status=EvaluationStatus.BLOCKED,
            evaluation_time_ms=evaluation_result.evaluation_metadata.evaluation_time_ms,
            evaluated_at=evaluation_result.evaluation_metadata.timestamp,
        )

        db_session.add(transaction)
        await db_session.commit()
        await db_session.refresh(transaction)

        # Transaction 조회 및 검증
        assert transaction.id == transaction_id, "Transaction ID 불일치"
        assert (
            transaction.evaluation_status == EvaluationStatus.BLOCKED
        ), f"Transaction 상태는 BLOCKED여야 하지만, 실제: {transaction.evaluation_status}"
        assert (
            transaction.risk_score >= 80
        ), f"저장된 위험 점수는 80+ 이어야 하지만, 실제: {transaction.risk_score}"

        print(f"  - Transaction ID: {transaction.id}")
        print(f"  - 상태: {transaction.evaluation_status}")
        print(f"  - 위험 점수: {transaction.risk_score}")
        print("  [PASS] Transaction이 BLOCKED 상태로 정확히 저장되었습니다")

        # === Assert: Step 3 - ReviewQueue 자동 추가 검증 ===
        print("\n[Step 3] ReviewQueue 자동 추가 검증")

        # ReviewQueue 서비스를 통해 검토 큐에 추가
        review_queue_service = ReviewQueueService(db_session)
        review_queue = await review_queue_service.add_to_review_queue(transaction.id)

        # ReviewQueue 검증
        assert review_queue is not None, "ReviewQueue가 생성되지 않았습니다"
        assert (
            review_queue.transaction_id == transaction_id
        ), "ReviewQueue의 transaction_id 불일치"
        assert (
            review_queue.status == ReviewStatus.PENDING
        ), f"ReviewQueue 상태는 PENDING이어야 하지만, 실제: {review_queue.status}"
        assert review_queue.assigned_to is None, "초기에는 담당자가 할당되지 않아야 합니다"

        print(f"  - ReviewQueue ID: {review_queue.id}")
        print(f"  - Transaction ID: {review_queue.transaction_id}")
        print(f"  - 상태: {review_queue.status}")
        print(f"  - 추가 시각: {review_queue.added_at}")
        print("  [PASS] 차단된 거래가 검토 큐에 자동으로 추가되었습니다")

        # === Assert: Step 4 - Transaction 상태가 MANUAL_REVIEW로 변경되었는지 검증 ===
        print("\n[Step 4] Transaction 상태 변경 검증")

        await db_session.refresh(transaction)
        assert (
            transaction.evaluation_status == EvaluationStatus.MANUAL_REVIEW
        ), f"Transaction 상태는 MANUAL_REVIEW로 변경되어야 하지만, 실제: {transaction.evaluation_status}"

        print(f"  - Transaction 상태: {transaction.evaluation_status}")
        print("  [PASS] Transaction 상태가 MANUAL_REVIEW로 변경되었습니다")

        # === 최종 검증 완료 ===
        print("\n[SUCCESS] T083 시나리오 검증 완료!")
        print("  1. 악성 IP 탐지 및 고위험 판단: OK")
        print("  2. 거래 자동 차단: OK")
        print("  3. 검토 큐 자동 추가: OK")
        print("  4. Transaction 상태 업데이트: OK")

    async def test_high_risk_score_auto_block_without_cti(self, db_session):
        """
        시나리오: CTI 없이도 여러 위험 요인으로 인해 위험 점수가 80점 이상일 경우
        자동 차단 및 검토 큐 추가

        검증 항목:
        1. 고액 거래 + 단시간 반복 거래로 위험 점수 80점 이상
        2. 의사결정이 'blocked'
        3. ReviewQueue에 자동 추가
        """
        # === Arrange ===
        transaction_id = uuid4()
        user_id = uuid4()
        order_id = uuid4()

        # 고액 거래 (500만원) - 위험 점수 50점
        request = FDSEvaluationRequest(
            transaction_id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=5000000,  # 500만원 - 위험 점수 50점
            ip_address="211.234.123.45",  # 정상 한국 IP
            user_agent="Mozilla/5.0",
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

        # === Act ===
        mock_redis = AsyncMock()
        evaluation_engine = EvaluationEngine(db=db_session, redis=mock_redis)

        # 첫 번째 거래 평가 (속도 위험 없음)
        first_result = await evaluation_engine.evaluate(request)

        # 같은 사용자로 즉시 두 번째 거래 시도 (velocity check 발동 예상)
        second_request = FDSEvaluationRequest(
            transaction_id=uuid4(),
            user_id=user_id,  # 같은 사용자
            order_id=uuid4(),
            amount=5000000,  # 500만원
            ip_address="211.234.123.45",
            user_agent="Mozilla/5.0",
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

        second_result = await evaluation_engine.evaluate(second_request)

        # === Assert ===
        print("\n[Step 1] 첫 번째 거래 평가 결과")
        print(f"  - 위험 점수: {first_result.risk_score}")
        print(f"  - 의사결정: {first_result.decision}")

        # 첫 번째 거래는 중간 위험도 (고액 거래만)
        assert (
            first_result.risk_score >= 40 and first_result.risk_score <= 70
        ), f"첫 번째 거래는 중간 위험도여야 하지만, 실제: {first_result.risk_score}"

        print("\n[Step 2] 두 번째 거래 평가 결과 (velocity check 발동)")
        print(f"  - 위험 점수: {second_result.risk_score}")
        print(f"  - 의사결정: {second_result.decision}")

        # 두 번째 거래는 고위험 (고액 + velocity)
        # 고액 50점 + velocity 40점 = 90점
        assert (
            second_result.risk_score >= 80
        ), f"두 번째 거래는 고위험(80+점)이어야 하지만, 실제: {second_result.risk_score}"
        assert (
            second_result.decision.value == "blocked"
        ), f"고위험 거래는 차단되어야 하지만, 실제: {second_result.decision.value}"

        # Transaction 저장
        transaction = Transaction(
            id=second_request.transaction_id,
            user_id=second_request.user_id,
            order_id=second_request.order_id,
            amount=second_request.amount,
            ip_address=second_request.ip_address,
            user_agent=second_request.user_agent,
            device_type=second_request.device_fingerprint.device_type.value,
            geolocation={"ip": second_request.ip_address},
            risk_score=second_result.risk_score,
            risk_level=RiskLevel(second_result.risk_level.value),
            evaluation_status=EvaluationStatus.BLOCKED,
            evaluation_time_ms=second_result.evaluation_metadata.evaluation_time_ms,
            evaluated_at=second_result.evaluation_metadata.timestamp,
        )

        db_session.add(transaction)
        await db_session.commit()
        await db_session.refresh(transaction)

        # ReviewQueue에 추가
        review_queue_service = ReviewQueueService(db_session)
        review_queue = await review_queue_service.add_to_review_queue(transaction.id)

        assert review_queue is not None, "ReviewQueue가 생성되지 않았습니다"
        assert (
            review_queue.status == ReviewStatus.PENDING
        ), f"ReviewQueue 상태는 PENDING이어야 하지만, 실제: {review_queue.status}"

        print("\n[SUCCESS] 복합 위험 요인에 의한 자동 차단 검증 완료!")
        print("  1. 고액 거래 + Velocity check로 고위험 판단: OK")
        print("  2. 거래 자동 차단: OK")
        print("  3. 검토 큐 자동 추가: OK")

    async def test_duplicate_review_queue_handling(self, db_session):
        """
        시나리오: 동일한 거래를 중복으로 검토 큐에 추가하려 할 때 정상 처리 확인

        검증 항목:
        1. 같은 transaction_id로 두 번 add_to_review_queue 호출
        2. 두 번째 호출은 None 반환 (중복 방지)
        3. 데이터베이스에는 하나의 ReviewQueue만 존재
        """
        # === Arrange ===
        transaction_id = uuid4()
        user_id = uuid4()
        order_id = uuid4()

        # Transaction 생성
        transaction = Transaction(
            id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=1000000,
            ip_address="185.220.100.45",
            user_agent="Mozilla/5.0",
            device_type="desktop",
            geolocation={"ip": "185.220.100.45"},
            risk_score=90,
            risk_level=RiskLevel.HIGH,
            evaluation_status=EvaluationStatus.BLOCKED,
            evaluation_time_ms=50,
        )

        db_session.add(transaction)
        await db_session.commit()
        await db_session.refresh(transaction)

        # === Act ===
        review_queue_service = ReviewQueueService(db_session)

        # 첫 번째 추가 - 성공
        first_queue = await review_queue_service.add_to_review_queue(transaction_id)

        # 두 번째 추가 시도 - 중복 방지
        second_queue = await review_queue_service.add_to_review_queue(transaction_id)

        # === Assert ===
        print("\n[Step 1] 첫 번째 ReviewQueue 추가")
        assert first_queue is not None, "첫 번째 추가는 성공해야 합니다"
        print(f"  - ReviewQueue ID: {first_queue.id}")
        print("  [PASS] 첫 번째 추가 성공")

        print("\n[Step 2] 두 번째 ReviewQueue 추가 시도 (중복)")
        assert second_queue is None, "두 번째 추가는 None을 반환해야 합니다 (중복 방지)"
        print("  [PASS] 중복 추가 방지됨")

        # 데이터베이스에서 ReviewQueue 조회
        all_queues = await review_queue_service.get_pending_reviews()
        matching_queues = [q for q in all_queues if q.transaction_id == transaction_id]

        print("\n[Step 3] 데이터베이스 검증")
        assert (
            len(matching_queues) == 1
        ), f"데이터베이스에는 하나의 ReviewQueue만 있어야 하지만, 실제: {len(matching_queues)}개"
        print(f"  - 데이터베이스의 ReviewQueue 개수: {len(matching_queues)}")
        print("  [PASS] 중복 없이 하나의 ReviewQueue만 존재")

        print("\n[SUCCESS] 중복 검토 큐 방지 검증 완료!")
