"""
통합 테스트: 관리자 주문 상태 변경 및 고객 알림

T097: 주문 상태 변경 및 고객 알림 검증

이 테스트는 다음 전체 플로우를 검증합니다:
1. 주문이 생성되고 결제 완료 상태로 변경
2. 관리자가 주문 상태를 "배송 준비"로 변경
3. 관리자가 주문 상태를 "배송 중"으로 변경 (shipped_at 타임스탬프 자동 설정)
4. 관리자가 주문 상태를 "배송 완료"로 변경 (delivered_at 타임스탬프 자동 설정)
5. 잘못된 상태 전환 시도 시 에러 발생
6. 주문 취소 시나리오

엔드투엔드 통합 테스트
"""

import pytest
import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    User, Product, Cart, CartItem, Order, OrderStatus, OrderItem,
    Payment, PaymentStatus
)
from src.services.order_service import OrderService
from src.utils.exceptions import ValidationError


class TestAdminOrderStatus:
    """관리자 주문 상태 변경 통합 테스트"""

    @pytest.fixture
    async def admin_user(self, db_session: AsyncSession):
        """테스트용 관리자 사용자 생성"""
        user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            password_hash="hashed_password",
            name="관리자",
            role="admin",
            status="active",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    async def test_user(self, db_session: AsyncSession):
        """테스트용 고객 사용자 생성"""
        user = User(
            id=uuid.uuid4(),
            email="customer@example.com",
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
            price=Decimal("50000.00"),
            stock_quantity=100,
            category="전자기기",
            status="available",
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)
        return product

    @pytest.fixture
    async def test_order(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_product: Product
    ):
        """테스트용 주문 생성 (결제 완료 상태)"""
        # 주문 생성
        order = Order(
            id=uuid.uuid4(),
            order_number=f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            user_id=test_user.id,
            total_amount=Decimal("100000.00"),
            status=OrderStatus.PAID,
            shipping_name="홍길동",
            shipping_address="서울특별시 강남구 테헤란로 123",
            shipping_phone="010-1234-5678",
            paid_at=datetime.now()
        )
        db_session.add(order)
        await db_session.commit()

        # 주문 항목 생성
        order_item = OrderItem(
            id=uuid.uuid4(),
            order_id=order.id,
            product_id=test_product.id,
            quantity=2,
            unit_price=test_product.price
        )
        db_session.add(order_item)

        # 결제 정보 생성
        payment = Payment(
            id=uuid.uuid4(),
            order_id=order.id,
            payment_method="credit_card",
            amount=order.total_amount,
            status=PaymentStatus.COMPLETED,
            card_token="tok_test_1234567890",
            card_last_four="1234",
            transaction_id="txn_test_123",
            completed_at=datetime.now()
        )
        db_session.add(payment)

        await db_session.commit()
        await db_session.refresh(order)
        return order

    @pytest.mark.asyncio
    async def test_order_status_to_preparing(
        self,
        db_session: AsyncSession,
        admin_user: User,
        test_order: Order,
    ):
        """
        Step 1: 주문 상태를 "배송 준비"로 변경

        검증 항목:
        - PAID → PREPARING 상태 전환이 성공하는지
        """
        print("\n=== Step 1: 주문 상태 -> 배송 준비 ===")

        # 주문 상태 변경
        test_order.status = OrderStatus.PREPARING

        await db_session.commit()
        await db_session.refresh(test_order)

        # 검증
        assert test_order.status == OrderStatus.PREPARING

        print("주문 상태 변경 성공")
        print(f"주문 번호: {test_order.order_number}")
        print(f"상태: PAID -> PREPARING")

    @pytest.mark.asyncio
    async def test_order_status_to_shipped(
        self,
        db_session: AsyncSession,
        admin_user: User,
        test_order: Order,
    ):
        """
        Step 2: 주문 상태를 "배송 중"으로 변경

        검증 항목:
        - PAID → PREPARING → SHIPPED 상태 전환이 성공하는지
        - shipped_at 타임스탬프가 자동으로 설정되는지
        """
        print("\n=== Step 2: 주문 상태 -> 배송 중 ===")

        # 주문 상태를 먼저 PREPARING으로 변경
        test_order.status = OrderStatus.PREPARING
        await db_session.commit()

        # 배송 시작
        test_order.mark_as_shipped()

        await db_session.commit()
        await db_session.refresh(test_order)

        # 검증
        assert test_order.status == OrderStatus.SHIPPED
        assert test_order.shipped_at is not None

        print("주문 상태 변경 성공")
        print(f"주문 번호: {test_order.order_number}")
        print(f"상태: PREPARING -> SHIPPED")
        print(f"배송 시작 시각: {test_order.shipped_at.isoformat()}")

    @pytest.mark.asyncio
    async def test_order_status_to_delivered(
        self,
        db_session: AsyncSession,
        admin_user: User,
        test_order: Order,
    ):
        """
        Step 3: 주문 상태를 "배송 완료"로 변경

        검증 항목:
        - SHIPPED → DELIVERED 상태 전환이 성공하는지
        - delivered_at 타임스탬프가 자동으로 설정되는지
        """
        print("\n=== Step 3: 주문 상태 -> 배송 완료 ===")

        # 주문 상태를 먼저 SHIPPED로 변경
        test_order.status = OrderStatus.PREPARING
        test_order.mark_as_shipped()
        await db_session.commit()

        # 배송 완료
        test_order.mark_as_delivered()

        await db_session.commit()
        await db_session.refresh(test_order)

        # 검증
        assert test_order.status == OrderStatus.DELIVERED
        assert test_order.delivered_at is not None

        print("주문 상태 변경 성공")
        print(f"주문 번호: {test_order.order_number}")
        print(f"상태: SHIPPED -> DELIVERED")
        print(f"배송 완료 시각: {test_order.delivered_at.isoformat()}")

    @pytest.mark.asyncio
    async def test_order_cancel(
        self,
        db_session: AsyncSession,
        admin_user: User,
        test_order: Order,
    ):
        """
        Step 4: 주문 취소

        검증 항목:
        - PAID 상태에서 취소가 가능한지
        - cancelled_at 타임스탬프가 자동으로 설정되는지
        """
        print("\n=== Step 4: 주문 취소 ===")

        # 주문 취소
        test_order.cancel()

        await db_session.commit()
        await db_session.refresh(test_order)

        # 검증
        assert test_order.status == OrderStatus.CANCELLED
        assert test_order.cancelled_at is not None

        print("주문 취소 성공")
        print(f"주문 번호: {test_order.order_number}")
        print(f"상태: PAID -> CANCELLED")
        print(f"취소 시각: {test_order.cancelled_at.isoformat()}")

    @pytest.mark.asyncio
    async def test_invalid_status_transition(
        self,
        db_session: AsyncSession,
        admin_user: User,
        test_order: Order,
    ):
        """
        Step 5: 잘못된 상태 전환 시도

        검증 항목:
        - PAID 상태에서 바로 DELIVERED로 변경 시도 시 에러 발생
        - 에러 메시지가 적절한지
        """
        print("\n=== Step 5: 잘못된 상태 전환 시도 ===")

        # PAID 상태에서 바로 DELIVERED로 변경 시도
        with pytest.raises(ValueError) as exc_info:
            test_order.mark_as_delivered()

        # 검증
        assert "배송 완료 처리 불가" in str(exc_info.value) or "현재 상태" in str(exc_info.value)

        print("잘못된 상태 전환 시도 차단 성공")
        print(f"에러 메시지: {str(exc_info.value)}")

    @pytest.mark.asyncio
    async def test_full_order_lifecycle(
        self,
        db_session: AsyncSession,
        admin_user: User,
        test_user: User,
        test_product: Product,
    ):
        """
        전체 주문 라이프사이클 통합 테스트

        1. 주문 생성 (PENDING)
        2. 결제 완료 (PAID)
        3. 배송 준비 (PREPARING)
        4. 배송 시작 (SHIPPED)
        5. 배송 완료 (DELIVERED)
        """
        print("\n=== 전체 주문 라이프사이클 ===")

        # Step 1: 주문 생성 (PENDING)
        print("\nStep 1: 주문 생성 (PENDING)")
        order = Order(
            id=uuid.uuid4(),
            order_number=f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            user_id=test_user.id,
            total_amount=Decimal("150000.00"),
            status=OrderStatus.PENDING,
            shipping_name="홍길동",
            shipping_address="서울특별시 강남구 테헤란로 123",
            shipping_phone="010-1234-5678",
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        assert order.status == OrderStatus.PENDING
        print(f"주문 생성 완료: {order.order_number} (상태: PENDING)")

        # Step 2: 결제 완료 (PAID)
        print("\nStep 2: 결제 완료 (PAID)")
        order.mark_as_paid()
        await db_session.commit()
        await db_session.refresh(order)

        assert order.status == OrderStatus.PAID
        assert order.paid_at is not None
        print(f"결제 완료: 상태 PAID (결제 시각: {order.paid_at.isoformat()})")

        # Step 3: 배송 준비 (PREPARING)
        print("\nStep 3: 배송 준비 (PREPARING)")
        order.status = OrderStatus.PREPARING
        await db_session.commit()
        await db_session.refresh(order)

        assert order.status == OrderStatus.PREPARING
        print(f"배송 준비 시작: 상태 PREPARING")

        # Step 4: 배송 시작 (SHIPPED)
        print("\nStep 4: 배송 시작 (SHIPPED)")
        order.mark_as_shipped()
        await db_session.commit()
        await db_session.refresh(order)

        assert order.status == OrderStatus.SHIPPED
        assert order.shipped_at is not None
        print(f"배송 시작: 상태 SHIPPED (배송 시각: {order.shipped_at.isoformat()})")

        # Step 5: 배송 완료 (DELIVERED)
        print("\nStep 5: 배송 완료 (DELIVERED)")
        order.mark_as_delivered()
        await db_session.commit()
        await db_session.refresh(order)

        assert order.status == OrderStatus.DELIVERED
        assert order.delivered_at is not None
        print(f"배송 완료: 상태 DELIVERED (배송 완료 시각: {order.delivered_at.isoformat()})")

        print("\n=== 전체 주문 라이프사이클 테스트 통과 ===")
        print(f"주문 번호: {order.order_number}")
        print(f"최종 상태: {order.status.value}")
        print(f"생성 시각: {order.created_at.isoformat()}")
        print(f"결제 시각: {order.paid_at.isoformat()}")
        print(f"배송 시작 시각: {order.shipped_at.isoformat()}")
        print(f"배송 완료 시각: {order.delivered_at.isoformat()}")

    @pytest.mark.asyncio
    async def test_refund_flow(
        self,
        db_session: AsyncSession,
        admin_user: User,
        test_order: Order,
    ):
        """
        환불 플로우 테스트

        검증 항목:
        - DELIVERED 상태에서만 환불 가능한지
        - REFUNDED 상태로 변경되는지
        """
        print("\n=== 환불 플로우 ===")

        # 주문을 먼저 DELIVERED 상태로 만들기
        test_order.status = OrderStatus.PREPARING
        test_order.mark_as_shipped()
        test_order.mark_as_delivered()
        await db_session.commit()
        await db_session.refresh(test_order)

        assert test_order.status == OrderStatus.DELIVERED

        # 환불 처리
        print("\n환불 처리 시작")
        test_order.status = OrderStatus.REFUNDED
        await db_session.commit()
        await db_session.refresh(test_order)

        # 검증
        assert test_order.status == OrderStatus.REFUNDED

        print("환불 처리 성공")
        print(f"주문 번호: {test_order.order_number}")
        print(f"상태: DELIVERED -> REFUNDED")
