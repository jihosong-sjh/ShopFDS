"""
통합 테스트: 추가 인증 성공 시나리오

T065: 추가 인증 성공 시나리오 검증 (거래 승인)

이 테스트는 다음 전체 플로우를 검증합니다:
1. 사용자가 의심스러운 거래 시도
2. FDS가 중간 위험도로 판정
3. OTP 발송
4. 사용자가 올바른 OTP 입력
5. 주문 완료 및 결제 처리

엔드투엔드 통합 테스트
"""

import pytest
import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, Product, Cart, CartItem, Order, OrderStatus, Payment, PaymentStatus
from src.services.order_service import OrderService
from src.services.cart_service import CartService
from src.services.user_service import UserService


class TestOTPSuccessScenario:
    """추가 인증 성공 시나리오 통합 테스트"""

    @pytest.fixture
    async def test_user(self, db_session: AsyncSession):
        """테스트용 사용자 생성"""
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            password_hash="hashed_password",
            name="홍길동",
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
            name="테스트 상품",
            description="테스트용 상품입니다",
            price=Decimal("150000.00"),
            stock_quantity=100,
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
        """테스트용 장바구니 및 상품 추가"""
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
            quantity=3,
        )
        db_session.add(cart_item)
        await db_session.commit()
        await db_session.refresh(cart)
        return cart

    @pytest.mark.asyncio
    async def test_full_otp_success_flow(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_cart_with_items: Cart,
    ):
        """
        전체 OTP 성공 플로우 테스트

        시나리오:
        1. 고액 거래 시도 (450만원)
        2. FDS가 중간 위험도 탐지
        3. 주문은 pending 상태로 생성됨
        4. OTP 발송
        5. 사용자가 올바른 OTP 입력
        6. 주문이 paid 상태로 변경
        7. 결제 완료 처리
        """
        # Given: OrderService 초기화
        order_service = OrderService(db_session)

        # Redis 모킹
        mock_redis = AsyncMock()

        # FDS를 모킹하여 중간 위험도 반환
        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch.object(OrderService, "_evaluate_transaction") as mock_fds:
            # FDS가 중간 위험도를 반환하도록 설정
            mock_fds.return_value = {
                "risk_score": 55,
                "risk_level": "medium",
                "decision": "additional_auth_required",
                "requires_verification": True,
                "risk_factors": [
                    {
                        "factor_type": "amount_threshold",
                        "factor_score": 55,
                        "description": "고액 거래 탐지: 4,500,000원",
                    }
                ],
            }

            # When 1: 주문 생성 (중간 위험도)
            order, fds_result = await order_service.create_order_from_cart(
                user_id=test_user.id,
                shipping_name="홍길동",
                shipping_address="서울특별시 강남구 테헤란로 123",
                shipping_phone="010-1234-5678",
                payment_info={
                    "card_number": "1234567890125678",
                    "card_expiry": "12/25",
                    "card_cvv": "123",
                },
            )

            # Then 1: 주문이 pending 상태로 생성됨
            assert order.status == OrderStatus.PENDING, (
                f"주문 상태가 PENDING이어야 합니다. 실제: {order.status}"
            )
            assert fds_result["requires_verification"] is True, (
                "추가 인증이 필요해야 합니다."
            )
            assert fds_result["risk_score"] == 55, (
                f"위험 점수가 55여야 합니다. 실제: {fds_result['risk_score']}"
            )

            print(f"Step 1: 주문 생성 완료 (PENDING) - order_id={order.id}")
            print(f"  - 위험 점수: {fds_result['risk_score']}")
            print(f"  - 추가 인증 필요: {fds_result['requires_verification']}")

        # Given 2: OTP 서비스를 모킹
        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch("src.services.order_service.get_otp_service") as mock_get_otp:
            mock_otp_service = AsyncMock()

            # OTP 검증 성공 시뮬레이션
            mock_otp_service.verify_otp.return_value = {
                "valid": True,
                "message": "OTP 검증 성공",
                "attempts_remaining": 2,
                "metadata": {
                    "order_id": str(order.id),
                    "user_id": str(test_user.id),
                },
            }
            mock_get_otp.return_value = mock_otp_service

            # When 2: OTP 검증 및 주문 완료
            completed_order, otp_result = await order_service.complete_order_with_otp(
                user_id=test_user.id,
                order_id=order.id,
                otp_code="123456",  # 테스트용 OTP
            )

            # Then 2: 주문 완료 처리
            assert completed_order.status == OrderStatus.PAID, (
                f"주문 상태가 PAID여야 합니다. 실제: {completed_order.status}"
            )
            assert completed_order.paid_at is not None, (
                "결제 완료 일시가 기록되어야 합니다."
            )
            assert otp_result["valid"] is True, (
                "OTP 검증이 성공해야 합니다."
            )

            # 결제 정보 검증
            await db_session.refresh(completed_order, ["payment"])
            assert completed_order.payment is not None, (
                "결제 정보가 있어야 합니다."
            )
            assert completed_order.payment.status == PaymentStatus.COMPLETED, (
                f"결제 상태가 COMPLETED여야 합니다. "
                f"실제: {completed_order.payment.status}"
            )

            print(f"Step 2: OTP 검증 및 주문 완료")
            print(f"  - 최종 주문 상태: {completed_order.status}")
            print(f"  - 결제 상태: {completed_order.payment.status}")
            print(f"  - 결제 완료 일시: {completed_order.paid_at}")

        print("\n전체 OTP 성공 플로우 테스트 통과")

    @pytest.mark.asyncio
    async def test_otp_verification_with_correct_order_id(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_cart_with_items: Cart,
    ):
        """
        OTP 메타데이터의 주문 ID 일치 검증

        OTP는 특정 주문에 대해서만 유효해야 합니다.
        """
        # Given: 주문 생성
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
                shipping_name="홍길동",
                shipping_address="서울특별시 강남구",
                shipping_phone="010-1234-5678",
                payment_info={
                    "card_number": "1234567890125678",
                    "card_expiry": "12/25",
                    "card_cvv": "123",
                },
            )

        # Given: OTP 서비스 모킹 (잘못된 주문 ID)
        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch("src.services.order_service.get_otp_service") as mock_get_otp:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp.return_value = {
                "valid": True,
                "message": "OTP 검증 성공",
                "attempts_remaining": 2,
                "metadata": {
                    "order_id": str(uuid.uuid4()),  # 다른 주문 ID
                    "user_id": str(test_user.id),
                },
            }
            mock_get_otp.return_value = mock_otp_service

            # When/Then: 주문 ID 불일치로 실패해야 함
            with pytest.raises(Exception) as exc_info:
                await order_service.complete_order_with_otp(
                    user_id=test_user.id,
                    order_id=order.id,
                    otp_code="123456",
                )

            assert "OTP가 이 주문에 대한 것이 아닙니다" in str(exc_info.value)

        print("OTP 주문 ID 일치 검증 통과")

    @pytest.mark.asyncio
    async def test_otp_success_updates_payment_status(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_cart_with_items: Cart,
    ):
        """
        OTP 검증 성공 시 결제 상태 업데이트 확인

        결제가 pending에서 completed로 변경되어야 합니다.
        """
        # Given: 주문 생성
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
                shipping_name="홍길동",
                shipping_address="서울특별시",
                shipping_phone="010-1234-5678",
                payment_info={
                    "card_number": "1234567890125678",
                    "card_expiry": "12/25",
                    "card_cvv": "123",
                },
            )

            # 결제 정보 확인
            await db_session.refresh(order, ["payment"])
            initial_payment = order.payment
            assert initial_payment is not None
            assert initial_payment.status == PaymentStatus.PENDING

            print(f"초기 결제 상태: {initial_payment.status}")

        # When: OTP 검증 성공
        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch("src.services.order_service.get_otp_service") as mock_get_otp:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp.return_value = {
                "valid": True,
                "message": "OTP 검증 성공",
                "attempts_remaining": 2,
                "metadata": {
                    "order_id": str(order.id),
                    "user_id": str(test_user.id),
                },
            }
            mock_get_otp.return_value = mock_otp_service

            completed_order, _ = await order_service.complete_order_with_otp(
                user_id=test_user.id,
                order_id=order.id,
                otp_code="123456",
            )

        # Then: 결제 상태가 COMPLETED로 변경
        await db_session.refresh(completed_order, ["payment"])
        final_payment = completed_order.payment

        assert final_payment.status == PaymentStatus.COMPLETED, (
            f"결제 상태가 COMPLETED여야 합니다. 실제: {final_payment.status}"
        )
        assert final_payment.completed_at is not None, (
            "결제 완료 시간이 기록되어야 합니다."
        )
        assert final_payment.transaction_id is not None, (
            "거래 ID가 생성되어야 합니다."
        )

        print(f"결제 상태 업데이트 검증 통과")
        print(f"  - 초기: {PaymentStatus.PENDING} → 최종: {final_payment.status}")
        print(f"  - 거래 ID: {final_payment.transaction_id}")

    @pytest.mark.asyncio
    async def test_cannot_complete_already_paid_order(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product,
        test_cart_with_items: Cart,
    ):
        """
        이미 완료된 주문에 대한 OTP 재검증 방지

        중복 결제를 막기 위해 이미 paid 상태인 주문은 OTP 검증을 거부해야 합니다.
        """
        # Given: 이미 완료된 주문
        order_service = OrderService(db_session)

        mock_redis = AsyncMock()

        with patch("src.services.order_service.get_redis", return_value=mock_redis), \
             patch.object(OrderService, "_evaluate_transaction") as mock_fds:
            mock_fds.return_value = {
                "risk_score": 10,
                "risk_level": "low",
                "decision": "approve",
                "requires_verification": False,
                "risk_factors": [],
            }

            order, _ = await order_service.create_order_from_cart(
                user_id=test_user.id,
                shipping_name="홍길동",
                shipping_address="서울특별시",
                shipping_phone="010-1234-5678",
                payment_info={
                    "card_number": "1234567890125678",
                    "card_expiry": "12/25",
                    "card_cvv": "123",
                },
            )

            # 주문 완료 처리 (낮은 위험도이므로 즉시 완료)
            assert order.status == OrderStatus.PAID

        # When/Then: 이미 완료된 주문에 OTP 재검증 시도 - 실패해야 함
        with patch("src.services.order_service.get_otp_service") as mock_get_otp:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp.return_value = {
                "valid": True,
                "message": "OTP 검증 성공",
                "attempts_remaining": 2,
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
                    otp_code="123456",
                )

            assert "이미 결제가 완료된 주문입니다" in str(exc_info.value)

        print("중복 결제 방지 검증 통과")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
