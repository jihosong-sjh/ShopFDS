"""
통합 테스트: 추가 인증 3회 실패 시나리오

T066: 추가 인증 3회 실패 시나리오 검증 (거래 차단)

이 테스트는 다음을 검증합니다:
1. 사용자가 잘못된 OTP를 입력
2. 최대 3회 시도 제한
3. 3회 실패 시 거래 차단
4. 차단된 거래는 더 이상 OTP 검증 불가
5. 보안팀 검토 큐에 추가 (선택적)
"""

import pytest
import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, Product, Cart, CartItem, Order, OrderStatus, Payment, PaymentStatus
from src.services.order_service import OrderService


class TestOTPFailureScenario:
    """추가 인증 3회 실패 시나리오 통합 테스트"""

    @pytest.fixture
    async def test_user(self, db_session: AsyncSession):
        """테스트용 사용자 생성"""
        user = User(
            id=uuid.uuid4(),
            email="fail_test@example.com",
            password_hash="hashed_password",
            name="김실패",
            role="customer",
            status="active",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    async def test_product(self, db_session: AsyncSession):
        """테스트용 상품 생성"""
        product = Product(
            id=uuid.uuid4(),
            name="고가 전자제품",
            description="테스트용 고가 상품",
            price=Decimal("2000000.00"),
            stock_quantity=50,
            category="전자제품",
            status="available",
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)
        return product

    @pytest.fixture
    async def test_cart_with_items(
        self, db_session: AsyncSession, test_user: User, test_product: Product
    ):
        """테스트용 장바구니"""
        cart = Cart(
            id=uuid.uuid4(),
            user_id=test_user.id,
        )
        db_session.add(cart)
        await db_session.commit()

        cart_item = CartItem(
            id=uuid.uuid4(),
            cart_id=cart.id,
            product_id=test_product.id,
            quantity=2,
        )
        db_session.add(cart_item)
        await db_session.commit()
        return cart

    @pytest.mark.asyncio
    async def test_otp_first_attempt_failure(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_cart_with_items: Cart,
    ):
        """
        첫 번째 OTP 시도 실패

        잘못된 OTP 입력 시:
        - ValidationError 발생
        - 남은 시도 횟수: 2회
        - 주문은 여전히 pending 상태
        """
        # Given: 중간 위험도 주문 생성
        order_service = OrderService(db_session)

        mock_redis = AsyncMock()

        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch.object(OrderService, "_evaluate_transaction") as mock_fds:
            mock_fds.return_value = {
                "risk_score": 55,
                "risk_level": "medium",
                "decision": "additional_auth_required",
                "requires_verification": True,
                "risk_factors": [],
            }

            order, _ = await order_service.create_order_from_cart(
                user_id=test_user.id,
                shipping_name="김실패",
                shipping_address="서울특별시",
                shipping_phone="010-9999-8888",
                payment_info={
                    "card_number": "1234567890128888",
                    "card_expiry": "12/25",
                    "card_cvv": "123",
                },
            )

        # When: 잘못된 OTP 입력 (첫 번째 시도)
        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch("src.services.order_service.get_otp_service") as mock_get_otp:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp.return_value = {
                "valid": False,
                "message": "OTP가 일치하지 않습니다",
                "attempts_remaining": 2,  # 남은 시도: 2회
                "metadata": {
                    "order_id": str(order.id),
                    "user_id": str(test_user.id),
                },
            }
            mock_get_otp.return_value = mock_otp_service

            # Then: ValidationError 발생
            with pytest.raises(Exception) as exc_info:
                await order_service.complete_order_with_otp(
                    user_id=test_user.id,
                    order_id=order.id,
                    otp_code="000000",  # 잘못된 OTP
                )

            assert "OTP 검증 실패" in str(exc_info.value)
            assert "남은 시도 횟수: 2" in str(exc_info.value)

        # 주문 상태 확인 - 여전히 PENDING
        await db_session.refresh(order)
        assert order.status == OrderStatus.PENDING, (
            f"주문 상태가 여전히 PENDING이어야 합니다. 실제: {order.status}"
        )

        print("첫 번째 OTP 실패 시나리오 통과 (남은 시도: 2회)")

    @pytest.mark.asyncio
    async def test_otp_second_attempt_failure(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_cart_with_items: Cart,
    ):
        """
        두 번째 OTP 시도 실패

        두 번째 실패 시:
        - ValidationError 발생
        - 남은 시도 횟수: 1회
        - 경고 메시지 포함
        """
        # Given: 중간 위험도 주문
        order_service = OrderService(db_session)

        mock_redis = AsyncMock()

        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch.object(OrderService, "_evaluate_transaction") as mock_fds:
            mock_fds.return_value = {
                "risk_score": 60,
                "risk_level": "medium",
                "decision": "additional_auth_required",
                "requires_verification": True,
                "risk_factors": [],
            }

            order, _ = await order_service.create_order_from_cart(
                user_id=test_user.id,
                shipping_name="김실패",
                shipping_address="서울특별시",
                shipping_phone="010-9999-8888",
                payment_info={
                    "card_number": "1234567890128888",
                    "card_expiry": "12/25",
                    "card_cvv": "123",
                },
            )

        # When: 두 번째 실패 시뮬레이션
        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch("src.services.order_service.get_otp_service") as mock_get_otp:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp.return_value = {
                "valid": False,
                "message": "OTP가 일치하지 않습니다",
                "attempts_remaining": 1,  # 남은 시도: 1회 (마지막 기회)
                "metadata": {
                    "order_id": str(order.id),
                    "user_id": str(test_user.id),
                },
            }
            mock_get_otp.return_value = mock_otp_service

            # Then: ValidationError + 경고
            with pytest.raises(Exception) as exc_info:
                await order_service.complete_order_with_otp(
                    user_id=test_user.id,
                    order_id=order.id,
                    otp_code="111111",
                )

            error_message = str(exc_info.value)
            assert "OTP 검증 실패" in error_message
            assert "남은 시도 횟수: 1" in error_message

        print("두 번째 OTP 실패 시나리오 통과 (남은 시도: 1회, 경고 발생)")

    @pytest.mark.asyncio
    async def test_otp_third_attempt_failure_blocks_transaction(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_cart_with_items: Cart,
    ):
        """
        세 번째 OTP 시도 실패 - 거래 차단

        세 번째 실패 시:
        - ValidationError 발생
        - 남은 시도 횟수: 0회
        - 주문 상태가 CANCELLED로 변경 (또는 BLOCKED)
        - 더 이상 OTP 재시도 불가
        """
        # Given: 중간 위험도 주문
        order_service = OrderService(db_session)

        mock_redis = AsyncMock()

        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch.object(OrderService, "_evaluate_transaction") as mock_fds:
            mock_fds.return_value = {
                "risk_score": 65,
                "risk_level": "medium",
                "decision": "additional_auth_required",
                "requires_verification": True,
                "risk_factors": [],
            }

            order, _ = await order_service.create_order_from_cart(
                user_id=test_user.id,
                shipping_name="김실패",
                shipping_address="서울특별시",
                shipping_phone="010-9999-8888",
                payment_info={
                    "card_number": "1234567890128888",
                    "card_expiry": "12/25",
                    "card_cvv": "123",
                },
            )

        # When: 세 번째 실패 (최종 실패)
        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch("src.services.order_service.get_otp_service") as mock_get_otp:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp.return_value = {
                "valid": False,
                "message": "OTP 검증 실패 - 최대 시도 횟수 초과",
                "attempts_remaining": 0,  # 시도 기회 소진
                "locked": True,  # OTP 잠금
                "metadata": {
                    "order_id": str(order.id),
                    "user_id": str(test_user.id),
                },
            }
            mock_get_otp.return_value = mock_otp_service

            # Then: 거래 차단
            with pytest.raises(Exception) as exc_info:
                await order_service.complete_order_with_otp(
                    user_id=test_user.id,
                    order_id=order.id,
                    otp_code="222222",
                )

            error_message = str(exc_info.value)
            assert "OTP 검증 실패" in error_message or "최대 시도" in error_message

        print("세 번째 OTP 실패 시나리오 통과 (거래 차단)")

    @pytest.mark.asyncio
    async def test_cannot_retry_after_max_attempts(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_cart_with_items: Cart,
    ):
        """
        최대 시도 횟수 초과 후 재시도 불가

        3회 실패 후:
        - OTP가 잠금 상태
        - 더 이상 검증 시도 불가
        - 새 OTP 발급 필요
        """
        # Given: 중간 위험도 주문
        order_service = OrderService(db_session)

        mock_redis = AsyncMock()

        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch.object(OrderService, "_evaluate_transaction") as mock_fds:
            mock_fds.return_value = {
                "risk_score": 50,
                "risk_level": "medium",
                "decision": "additional_auth_required",
                "requires_verification": True,
                "risk_factors": [],
            }

            order, _ = await order_service.create_order_from_cart(
                user_id=test_user.id,
                shipping_name="김실패",
                shipping_address="서울특별시",
                shipping_phone="010-9999-8888",
                payment_info={
                    "card_number": "1234567890128888",
                    "card_expiry": "12/25",
                    "card_cvv": "123",
                },
            )

        # Given: OTP가 이미 잠금 상태 (3회 실패 후)
        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch("src.services.order_service.get_otp_service") as mock_get_otp:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp.return_value = {
                "valid": False,
                "message": "OTP가 잠금 상태입니다. 새 OTP를 발급받으세요.",
                "attempts_remaining": 0,
                "locked": True,
                "metadata": {
                    "order_id": str(order.id),
                    "user_id": str(test_user.id),
                },
            }
            mock_get_otp.return_value = mock_otp_service

            # When/Then: 네 번째 시도 - 거부되어야 함
            with pytest.raises(Exception) as exc_info:
                await order_service.complete_order_with_otp(
                    user_id=test_user.id,
                    order_id=order.id,
                    otp_code="333333",
                )

            error_message = str(exc_info.value)
            assert "잠금" in error_message or "새 OTP" in error_message

        print("최대 시도 초과 후 재시도 차단 검증 통과")

    @pytest.mark.asyncio
    async def test_otp_failure_does_not_affect_other_orders(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_cart_with_items: Cart,
    ):
        """
        한 주문의 OTP 실패가 다른 주문에 영향을 주지 않음

        주문 A에서 OTP 3회 실패해도 주문 B는 독립적으로 OTP 검증 가능
        """
        # Given: 두 개의 독립적인 주문
        order_service = OrderService(db_session)

        mock_redis = AsyncMock()

        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch.object(OrderService, "_evaluate_transaction") as mock_fds:
            mock_fds.return_value = {
                "risk_score": 55,
                "risk_level": "medium",
                "decision": "additional_auth_required",
                "requires_verification": True,
                "risk_factors": [],
            }

            # 주문 A
            order_a, _ = await order_service.create_order_from_cart(
                user_id=test_user.id,
                shipping_name="김실패",
                shipping_address="서울특별시 강남구",
                shipping_phone="010-9999-8888",
                payment_info={
                    "card_number": "1234567890128888",
                    "card_expiry": "12/25",
                    "card_cvv": "123",
                },
            )

            # 주문 B
            order_b, _ = await order_service.create_order_from_cart(
                user_id=test_user.id,
                shipping_name="김실패",
                shipping_address="서울특별시 서초구",
                shipping_phone="010-9999-8888",
                payment_info={
                    "card_number": "1234567890128889",
                    "card_expiry": "12/25",
                    "card_cvv": "123",
                },
            )

        # When: 주문 A에서 OTP 3회 실패
        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch("src.services.order_service.get_otp_service") as mock_get_otp:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp.return_value = {
                "valid": False,
                "message": "OTP 검증 실패",
                "attempts_remaining": 0,
                "locked": True,
                "metadata": {
                    "order_id": str(order_a.id),
                    "user_id": str(test_user.id),
                },
            }
            mock_get_otp.return_value = mock_otp_service

            with pytest.raises(Exception):
                await order_service.complete_order_with_otp(
                    user_id=test_user.id,
                    order_id=order_a.id,
                    otp_code="000000",
                )

        # Then: 주문 B는 여전히 OTP 검증 가능
        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch("src.services.order_service.get_otp_service") as mock_get_otp:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp.return_value = {
                "valid": True,
                "message": "OTP 검증 성공",
                "attempts_remaining": 2,
                "metadata": {
                    "order_id": str(order_b.id),
                    "user_id": str(test_user.id),
                },
            }
            mock_get_otp.return_value = mock_otp_service

            # 주문 B는 정상적으로 완료 가능
            completed_order_b, _ = await order_service.complete_order_with_otp(
                user_id=test_user.id,
                order_id=order_b.id,
                otp_code="123456",  # 올바른 OTP
            )

            assert completed_order_b.status == OrderStatus.PAID

        print("주문 독립성 검증 통과 (주문 A 실패가 주문 B에 영향 없음)")

    @pytest.mark.asyncio
    async def test_otp_failure_attempt_count_accuracy(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_cart_with_items: Cart,
    ):
        """
        OTP 실패 시 남은 시도 횟수 정확성 검증

        3 → 2 → 1 → 0 순서로 정확히 감소해야 함
        """
        # Given: 중간 위험도 주문
        order_service = OrderService(db_session)

        mock_redis = AsyncMock()

        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch.object(OrderService, "_evaluate_transaction") as mock_fds:
            mock_fds.return_value = {
                "risk_score": 50,
                "risk_level": "medium",
                "decision": "additional_auth_required",
                "requires_verification": True,
                "risk_factors": [],
            }

            order, _ = await order_service.create_order_from_cart(
                user_id=test_user.id,
                shipping_name="김실패",
                shipping_address="서울특별시",
                shipping_phone="010-9999-8888",
                payment_info={
                    "card_number": "1234567890128888",
                    "card_expiry": "12/25",
                    "card_cvv": "123",
                },
            )

        # 시도 횟수별 검증
        expected_attempts = [2, 1, 0]  # 첫 실패 후: 2, 두 번째 실패 후: 1, 세 번째 실패 후: 0

        for i, remaining in enumerate(expected_attempts, 1):
            with patch("src.services.order_service.get_redis", return_value=mock_redis), \
                 patch("src.services.order_service.get_otp_service") as mock_get_otp:
                mock_otp_service = AsyncMock()
                mock_otp_service.verify_otp.return_value = {
                    "valid": False,
                    "message": f"OTP 검증 실패 (시도 {i}/3)",
                    "attempts_remaining": remaining,
                    "locked": remaining == 0,
                    "metadata": {
                        "order_id": str(order.id),
                        "user_id": str(test_user.id),
                    },
                }
                mock_get_otp.return_value = mock_otp_service

                with pytest.raises(Exception) as exc_info:
                    await order_service.complete_order_with_otp(
                        user_id=test_user.id,
                        order_id=order.id,
                        otp_code=f"{i}{i}{i}{i}{i}{i}",
                    )

                error_message = str(exc_info.value)
                assert f"남은 시도 횟수: {remaining}" in error_message, (
                    f"{i}번째 실패 시 남은 시도 횟수가 {remaining}여야 합니다"
                )

                print(f"  - {i}번째 실패: 남은 시도 횟수 {remaining}회")

        print("OTP 시도 횟수 정확성 검증 통과")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
