"""
ReviewQueue 통합 테스트

고위험 거래 자동 차단 및 검토 큐 추가 로직 검증
"""

import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from src.models.schemas import (
    FDSEvaluationRequest,
    DeviceFingerprint,
    DeviceTypeEnum,
    ShippingInfo,
    PaymentInfo,
    SessionContext,
    DecisionEnum,
    RiskLevelEnum,
)
from src.models import (
    Transaction,
    ReviewQueue,
    ReviewStatus,
    ReviewDecision,
    EvaluationStatus,
)
from src.engines.evaluation_engine import EvaluationEngine
from src.services.review_queue_service import ReviewQueueService


@pytest.mark.asyncio
class TestReviewQueueIntegration:
    """ReviewQueue 통합 테스트"""

    async def test_high_risk_transaction_auto_blocked_and_queued(self, db_session):
        """
        T071-T073: 고위험 거래 자동 차단 및 검토 큐 추가 검증

        시나리오:
        1. 악성 IP에서 고액 거래 시도 (위험 점수 90+)
        2. FDS가 자동 차단 결정 (BLOCKED)
        3. 거래가 검토 큐에 자동 추가
        4. 검토 큐 상태가 PENDING
        """
        # Given: 고위험 거래 요청 (악성 IP + 고액 거래)
        transaction_id = uuid4()
        user_id = uuid4()
        order_id = uuid4()

        request = FDSEvaluationRequest(
            transaction_id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=Decimal("5000000.00"),  # 500만원 (고액 거래: +50점)
            currency="KRW",
            ip_address="185.220.100.50",  # Tor Exit Node (의심스러운 IP: +45점)
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            device_fingerprint=DeviceFingerprint(
                device_type=DeviceTypeEnum.DESKTOP,
                os="Windows 10",
                browser="Chrome",
            ),
            shipping_info=ShippingInfo(
                name="홍길동",
                address="서울특별시 강남구",
                phone="010-1234-5678",
            ),
            payment_info=PaymentInfo(
                method="credit_card",
                card_bin="123456",
                card_last_four="7890",
            ),
            session_context=SessionContext(
                session_id="test-session-123",
                session_duration_seconds=120,
            ),
            timestamp=datetime.utcnow(),
        )

        # When: FDS 평가 수행
        engine = EvaluationEngine(db=db_session, redis=None)
        evaluation_result = await engine.evaluate(request)

        # Then 1: 고위험으로 분류되어 자동 차단
        assert evaluation_result.risk_score >= 80, (
            f"위험 점수가 80점 이상이어야 합니다 (실제: {evaluation_result.risk_score})"
        )
        assert evaluation_result.risk_level == RiskLevelEnum.HIGH, (
            "위험 수준이 HIGH여야 합니다"
        )
        assert evaluation_result.decision == DecisionEnum.BLOCKED, (
            "의사결정이 BLOCKED여야 합니다"
        )
        assert evaluation_result.recommended_action.manual_review_required is True, (
            "수동 검토가 필요해야 합니다"
        )

        # Then 2: 거래가 데이터베이스에 저장되고 BLOCKED 상태
        transaction = Transaction(
            id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=request.amount,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            device_type=request.device_fingerprint.device_type.value,
            geolocation={"ip": request.ip_address},
            risk_score=evaluation_result.risk_score,
            risk_level=evaluation_result.risk_level.value,
            evaluation_status=EvaluationStatus.BLOCKED,
            evaluation_time_ms=evaluation_result.evaluation_metadata.evaluation_time_ms,
            evaluated_at=evaluation_result.evaluation_metadata.timestamp,
        )
        db_session.add(transaction)
        await db_session.commit()
        await db_session.refresh(transaction)

        # Then 3: 검토 큐 서비스로 거래를 검토 큐에 추가
        review_queue_service = ReviewQueueService(db_session)
        review_queue = await review_queue_service.add_to_review_queue(transaction_id)

        assert review_queue is not None, "검토 큐 엔트리가 생성되어야 합니다"
        assert review_queue.transaction_id == transaction_id, (
            "검토 큐의 transaction_id가 일치해야 합니다"
        )
        assert review_queue.status == ReviewStatus.PENDING, (
            "검토 큐 상태가 PENDING이어야 합니다"
        )
        assert review_queue.assigned_to is None, (
            "초기 상태에서는 담당자가 없어야 합니다"
        )
        assert review_queue.decision is None, (
            "초기 상태에서는 검토 결과가 없어야 합니다"
        )

        # Then 4: 거래 상태가 MANUAL_REVIEW로 업데이트
        await db_session.refresh(transaction)
        assert transaction.evaluation_status == EvaluationStatus.MANUAL_REVIEW, (
            "거래 상태가 MANUAL_REVIEW로 업데이트되어야 합니다"
        )

        print(f"[PASS] 고위험 거래 자동 차단 및 검토 큐 추가 완료")
        print(f"  - transaction_id: {transaction_id}")
        print(f"  - risk_score: {evaluation_result.risk_score}")
        print(f"  - decision: {evaluation_result.decision.value}")
        print(f"  - review_queue_id: {review_queue.id}")

    async def test_review_queue_workflow(self, db_session):
        """
        검토 큐 워크플로우 검증

        시나리오:
        1. 고위험 거래를 검토 큐에 추가
        2. 보안팀 담당자 할당
        3. 검토 완료 (승인/차단 결정)
        """
        # Given: 고위험 거래 생성
        transaction_id = uuid4()
        user_id = uuid4()
        order_id = uuid4()

        transaction = Transaction(
            id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=Decimal("8000000.00"),
            ip_address="185.220.101.25",
            user_agent="Mozilla/5.0",
            device_type="desktop",
            geolocation={"ip": "185.220.101.25"},
            risk_score=95,
            risk_level="high",
            evaluation_status=EvaluationStatus.BLOCKED,
            evaluation_time_ms=85,
            evaluated_at=datetime.utcnow(),
        )
        db_session.add(transaction)
        await db_session.commit()

        # When 1: 검토 큐에 추가
        review_queue_service = ReviewQueueService(db_session)
        review_queue = await review_queue_service.add_to_review_queue(transaction_id)

        assert review_queue is not None
        assert review_queue.status == ReviewStatus.PENDING

        # When 2: 담당자 할당
        reviewer_id = uuid4()
        review_queue = await review_queue_service.assign_reviewer(
            review_queue.id, reviewer_id
        )

        # Then 2: 상태가 IN_REVIEW로 변경
        assert review_queue.status == ReviewStatus.IN_REVIEW
        assert review_queue.assigned_to == reviewer_id

        # When 3: 검토 완료 (오탐으로 판단하여 승인)
        review_queue = await review_queue_service.complete_review(
            queue_id=review_queue.id,
            decision=ReviewDecision.APPROVE,
            notes="고객 확인 결과 정상 거래로 확인. 고액이지만 실제 구매 의도 있음.",
        )

        # Then 3: 검토 완료 상태
        assert review_queue.status == ReviewStatus.COMPLETED
        assert review_queue.decision == ReviewDecision.APPROVE
        assert review_queue.review_notes is not None
        assert review_queue.reviewed_at is not None
        assert review_queue.review_time_seconds is not None

        print(f"[PASS] 검토 큐 워크플로우 완료")
        print(f"  - 검토 소요 시간: {review_queue.review_time_seconds}초")
        print(f"  - 검토 결과: {review_queue.decision.value}")

    async def test_duplicate_review_queue_entry_prevented(self, db_session):
        """
        중복 검토 큐 엔트리 방지 검증

        시나리오:
        1. 동일한 거래를 두 번 검토 큐에 추가 시도
        2. 두 번째 시도는 None 반환 (중복 방지)
        """
        # Given: 고위험 거래 생성
        transaction_id = uuid4()
        transaction = Transaction(
            id=transaction_id,
            user_id=uuid4(),
            order_id=uuid4(),
            amount=Decimal("9000000.00"),
            ip_address="185.220.102.50",
            user_agent="Mozilla/5.0",
            device_type="mobile",
            geolocation={"ip": "185.220.102.50"},
            risk_score=92,
            risk_level="high",
            evaluation_status=EvaluationStatus.BLOCKED,
            evaluation_time_ms=78,
            evaluated_at=datetime.utcnow(),
        )
        db_session.add(transaction)
        await db_session.commit()

        # When: 첫 번째 검토 큐 추가
        review_queue_service = ReviewQueueService(db_session)
        first_entry = await review_queue_service.add_to_review_queue(transaction_id)

        assert first_entry is not None, "첫 번째 엔트리는 생성되어야 합니다"

        # When: 두 번째 검토 큐 추가 시도 (중복)
        second_entry = await review_queue_service.add_to_review_queue(transaction_id)

        # Then: 중복 엔트리는 생성되지 않음
        assert second_entry is None, "중복 엔트리는 None을 반환해야 합니다"

        # Verify: 검토 큐에 하나만 존재
        review = await review_queue_service.get_review_by_transaction(transaction_id)
        assert review is not None
        assert review.id == first_entry.id

        print(f"[PASS] 중복 검토 큐 엔트리 방지 확인")

    async def test_get_pending_reviews(self, db_session):
        """
        검토 대기 중인 항목 조회 검증
        """
        # Given: 여러 개의 고위험 거래 생성
        review_queue_service = ReviewQueueService(db_session)

        for i in range(5):
            transaction = Transaction(
                id=uuid4(),
                user_id=uuid4(),
                order_id=uuid4(),
                amount=Decimal("5000000.00"),
                ip_address=f"185.220.100.{i}",
                user_agent="Mozilla/5.0",
                device_type="desktop",
                geolocation={"ip": f"185.220.100.{i}"},
                risk_score=85 + i,
                risk_level="high",
                evaluation_status=EvaluationStatus.BLOCKED,
                evaluation_time_ms=80,
                evaluated_at=datetime.utcnow(),
            )
            db_session.add(transaction)
            await db_session.commit()

            # 검토 큐에 추가
            await review_queue_service.add_to_review_queue(transaction.id)

        # When: 검토 대기 중인 항목 조회
        pending_reviews = await review_queue_service.get_pending_reviews(limit=10)

        # Then: 5개의 PENDING 항목이 조회되어야 함
        assert len(pending_reviews) >= 5, (
            f"최소 5개의 PENDING 항목이 있어야 합니다 (실제: {len(pending_reviews)})"
        )

        for review in pending_reviews:
            assert review.status == ReviewStatus.PENDING

        print(f"[PASS] 검토 대기 중인 항목 조회: {len(pending_reviews)}개")
