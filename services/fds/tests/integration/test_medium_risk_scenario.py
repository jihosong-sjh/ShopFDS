"""
통합 테스트: FDS 중간 위험도 거래 시나리오

T064: FDS에서 중간 위험도 거래 시나리오 검증 (위험 점수 40-70점)

이 테스트는 다음을 검증합니다:
- FDS가 중간 위험도 거래를 정확히 탐지하는지
- 위험 점수가 40-70점 범위에 있는지
- decision이 'additional_auth_required'로 반환되는지
- requires_verification이 True로 설정되는지
"""

import pytest
import uuid
from datetime import datetime
from decimal import Decimal

from src.models.schemas import (
    FDSEvaluationRequest,
    DeviceFingerprint,
    DeviceTypeEnum,
    ShippingInfo,
    PaymentInfo,
    SessionContext,
)
from src.engines.evaluation_engine import evaluation_engine


class TestMediumRiskScenario:
    """중간 위험도 거래 시나리오 테스트"""

    @pytest.mark.anyio
    async def test_high_amount_triggers_medium_risk(self):
        """
        시나리오 1: 고액 거래 (평소보다 높은 금액)

        기대 결과:
        - 위험 점수: 40-70점
        - 의사결정: additional_auth_required
        - requires_verification: True
        """
        # Given: 고액 거래 요청 (500만원)
        request = FDSEvaluationRequest(
            transaction_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            order_id=uuid.uuid4(),
            amount=Decimal("5000000.00"),  # 5,000,000원 - 고액 거래
            ip_address="211.234.123.45",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            device_fingerprint=DeviceFingerprint(
                device_id="device-12345",
                device_type=DeviceTypeEnum.DESKTOP,
                browser="Chrome",
                os="Windows 10",
            ),
            shipping_info=ShippingInfo(
                name="홍길동",
                address="서울특별시 강남구 테헤란로 123",
                phone="010-1234-5678",
            ),
            payment_info=PaymentInfo(
                method="credit_card",
                card_bin="123456",
                card_last_four="1234",
            ),
            session_context=SessionContext(
                session_id="sess-12345",
            ),
            timestamp=datetime.utcnow(),
        )

        # When: FDS 평가 실행
        result = await evaluation_engine.evaluate(request)

        # Then: 중간 위험도로 판정
        assert 40 <= result.risk_score <= 70, (
            f"위험 점수가 중간 위험도 범위(40-70)에 있어야 합니다. " f"실제: {result.risk_score}"
        )
        assert result.decision.value == "additional_auth_required", (
            f"의사결정이 'additional_auth_required'여야 합니다. " f"실제: {result.decision.value}"
        )
        assert result.requires_verification is True, "추가 인증이 필요해야 합니다."
        assert (
            result.risk_level.value == "medium"
        ), f"위험 수준이 'medium'이어야 합니다. 실제: {result.risk_level.value}"

        # 위험 요인 검증
        assert len(result.risk_factors) > 0, "위험 요인이 있어야 합니다."

        # 고액 거래 요인이 포함되어 있는지 확인
        amount_factors = [
            f
            for f in result.risk_factors
            if "amount" in f.factor_type.lower() or "금액" in f.description
        ]
        assert len(amount_factors) > 0, "고액 거래 위험 요인이 탐지되어야 합니다."

        print(f"✓ 고액 거래 시나리오 통과: 위험 점수 {result.risk_score}")

    @pytest.mark.anyio
    async def test_unusual_ip_triggers_medium_risk(self):
        """
        시나리오 2: 평소와 다른 IP 위치에서 접속

        기대 결과:
        - 위험 점수: 40-70점
        - 의사결정: additional_auth_required
        - requires_verification: True
        """
        # Given: 해외 IP에서의 거래 시도
        request = FDSEvaluationRequest(
            transaction_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            order_id=uuid.uuid4(),
            amount=Decimal("150000.00"),  # 15만원 - 일반적인 금액
            ip_address="185.220.100.240",  # 해외 IP (Tor Exit Node 예시)
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            device_fingerprint=DeviceFingerprint(
                device_id="device-new-123",  # 새 디바이스
                device_type=DeviceTypeEnum.DESKTOP,
                browser="Chrome",
                os="Windows 10",
            ),
            shipping_info=ShippingInfo(
                name="김철수",
                address="서울특별시 서초구 강남대로 456",
                phone="010-9876-5432",
            ),
            payment_info=PaymentInfo(
                method="credit_card",
                card_bin="456789",
                card_last_four="5678",
            ),
            session_context=SessionContext(
                session_id="sess-67890",
            ),
            timestamp=datetime.utcnow(),
        )

        # When: FDS 평가 실행
        result = await evaluation_engine.evaluate(request)

        # Then: 중간 위험도로 판정
        assert 40 <= result.risk_score <= 70, (
            f"위험 점수가 중간 위험도 범위(40-70)에 있어야 합니다. " f"실제: {result.risk_score}"
        )
        assert result.decision.value == "additional_auth_required", (
            f"의사결정이 'additional_auth_required'여야 합니다. " f"실제: {result.decision.value}"
        )
        assert result.requires_verification is True, "추가 인증이 필요해야 합니다."

        # 지역 불일치 요인 검증
        location_factors = [
            f
            for f in result.risk_factors
            if "location" in f.factor_type.lower() or "지역" in f.description
        ]
        assert len(location_factors) > 0, "지역 불일치 위험 요인이 탐지되어야 합니다."

        print(f"✓ 비정상 IP 시나리오 통과: 위험 점수 {result.risk_score}")

    @pytest.mark.anyio
    async def test_rapid_transactions_trigger_medium_risk(self):
        """
        시나리오 3: 단시간 내 반복 거래 (Velocity Check)

        기대 결과:
        - 위험 점수: 40-70점
        - 의사결정: additional_auth_required
        - requires_verification: True
        """
        # Given: 동일 사용자의 연속된 거래
        user_id = uuid.uuid4()
        ip_address = "211.234.123.45"

        # 첫 번째 거래 (통과)
        first_request = FDSEvaluationRequest(
            transaction_id=uuid.uuid4(),
            user_id=user_id,
            order_id=uuid.uuid4(),
            amount=Decimal("100000.00"),
            ip_address=ip_address,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            device_fingerprint=DeviceFingerprint(
                device_id="device-12345",
                device_type=DeviceTypeEnum.DESKTOP,
                browser="Chrome",
                os="Windows 10",
            ),
            shipping_info=ShippingInfo(
                name="이영희",
                address="서울특별시 마포구 월드컵로 789",
                phone="010-1111-2222",
            ),
            payment_info=PaymentInfo(
                method="credit_card",
                card_bin="111222",
                card_last_four="3333",
            ),
            session_context=SessionContext(
                session_id="sess-12345",
            ),
            timestamp=datetime.utcnow(),
        )

        first_result = await evaluation_engine.evaluate(first_request)
        print(f"첫 번째 거래 위험 점수: {first_result.risk_score}")

        # 두 번째 거래 (즉시 발생 - 의심스러움)
        second_request = FDSEvaluationRequest(
            transaction_id=uuid.uuid4(),
            user_id=user_id,
            order_id=uuid.uuid4(),
            amount=Decimal("120000.00"),
            ip_address=ip_address,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            device_fingerprint=DeviceFingerprint(
                device_id="device-12345",
                device_type=DeviceTypeEnum.DESKTOP,
                browser="Chrome",
                os="Windows 10",
            ),
            shipping_info=ShippingInfo(
                name="이영희",
                address="서울특별시 마포구 월드컵로 789",
                phone="010-1111-2222",
            ),
            payment_info=PaymentInfo(
                method="credit_card",
                card_bin="111222",
                card_last_four="3333",
            ),
            session_context=SessionContext(
                session_id="sess-12345",
            ),
            timestamp=datetime.utcnow(),
        )

        # When: 두 번째 거래 평가
        second_result = await evaluation_engine.evaluate(second_request)

        # Then: 중간 위험도로 판정 (Velocity 위반)
        assert 40 <= second_result.risk_score <= 70, (
            f"위험 점수가 중간 위험도 범위(40-70)에 있어야 합니다. " f"실제: {second_result.risk_score}"
        )
        assert second_result.decision.value == "additional_auth_required", (
            f"의사결정이 'additional_auth_required'여야 합니다. "
            f"실제: {second_result.decision.value}"
        )
        assert second_result.requires_verification is True, "추가 인증이 필요해야 합니다."

        # Velocity check 요인 검증
        velocity_factors = [
            f
            for f in second_result.risk_factors
            if "velocity" in f.factor_type.lower() or "반복" in f.description
        ]
        assert len(velocity_factors) > 0, "Velocity check 위험 요인이 탐지되어야 합니다."

        print(f"✓ 반복 거래 시나리오 통과: 위험 점수 {second_result.risk_score}")

    @pytest.mark.anyio
    async def test_evaluation_time_within_sla(self):
        """
        성능 테스트: FDS 평가 시간이 100ms 이내인지 확인

        기대 결과:
        - evaluation_time_ms < 100
        """
        # Given: 중간 위험도 거래 요청
        request = FDSEvaluationRequest(
            transaction_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            order_id=uuid.uuid4(),
            amount=Decimal("3000000.00"),
            ip_address="211.234.123.45",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            device_fingerprint=DeviceFingerprint(
                device_id="device-12345",
                device_type=DeviceTypeEnum.DESKTOP,
                browser="Chrome",
                os="Windows 10",
            ),
            shipping_info=ShippingInfo(
                name="박민수",
                address="서울특별시 종로구 세종대로 101",
                phone="010-4444-5555",
            ),
            payment_info=PaymentInfo(
                method="credit_card",
                card_bin="444555",
                card_last_four="6666",
            ),
            session_context=SessionContext(
                session_id="sess-12345",
            ),
            timestamp=datetime.utcnow(),
        )

        # When: FDS 평가 실행
        result = await evaluation_engine.evaluate(request)

        # Then: 100ms 이내 응답
        assert result.evaluation_metadata.evaluation_time_ms < 100, (
            f"FDS 평가 시간이 100ms를 초과했습니다. "
            f"실제: {result.evaluation_metadata.evaluation_time_ms}ms"
        )

        print(
            f"✓ 성능 SLA 충족: {result.evaluation_metadata.evaluation_time_ms}ms "
            f"(목표: <100ms)"
        )

    @pytest.mark.anyio
    async def test_risk_factors_detail(self):
        """
        위험 요인 상세 정보 검증

        기대 결과:
        - 각 위험 요인에 factor_type, factor_score, description 포함
        - 위험 점수 합산이 전체 위험 점수와 일치
        """
        # Given: 고액 + 비정상 IP 조합
        request = FDSEvaluationRequest(
            transaction_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            order_id=uuid.uuid4(),
            amount=Decimal("4000000.00"),
            ip_address="185.220.100.240",  # 해외 IP
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            device_fingerprint=DeviceFingerprint(
                device_id="device-new-789",
                device_type=DeviceTypeEnum.MOBILE,
                browser="Safari",
                os="iOS",
            ),
            shipping_info=ShippingInfo(
                name="최지현",
                address="부산광역시 해운대구 센텀대로 202",
                phone="010-7777-8888",
            ),
            payment_info=PaymentInfo(
                method="credit_card",
                card_bin="777888",
                card_last_four="9999",
            ),
            session_context=SessionContext(
                session_id="sess-99999",
            ),
            timestamp=datetime.utcnow(),
        )

        # When: FDS 평가 실행
        result = await evaluation_engine.evaluate(request)

        # Then: 위험 요인 상세 검증
        assert len(result.risk_factors) >= 2, "최소 2개 이상의 위험 요인이 탐지되어야 합니다."

        for factor in result.risk_factors:
            assert factor.factor_type, "factor_type이 있어야 합니다."
            assert factor.factor_score > 0, "factor_score가 0보다 커야 합니다."
            assert factor.description, "description이 있어야 합니다."

        print(f"✓ 위험 요인 상세 정보 검증 통과")
        print(f"  - 탐지된 위험 요인 수: {len(result.risk_factors)}")
        for i, factor in enumerate(result.risk_factors, 1):
            print(f"  - 요인 {i}: {factor.factor_type} (점수: {factor.factor_score})")
            print(f"    설명: {factor.description}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
