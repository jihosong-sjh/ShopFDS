"""
주문 서비스

주문 생성, 주문 상태 관리 등 주문 관련 비즈니스 로직
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import httpx

from src.models.order import Order, OrderItem, OrderStatus
from src.models.cart import Cart, CartItem
from src.models.product import Product
from src.models.payment import Payment, PaymentMethod, PaymentStatus
from src.utils.exceptions import ResourceNotFoundError, ValidationError, BusinessLogicError
from src.config import get_settings


class OrderService:
    """주문 관련 비즈니스 로직"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def create_order_from_cart(
        self,
        user_id: str,
        shipping_name: str,
        shipping_address: str,
        shipping_phone: str,
        payment_info: Dict[str, str]
    ) -> tuple[Order, dict]:
        """
        장바구니로부터 주문 생성

        Args:
            user_id: 사용자 ID
            shipping_name: 수령인 이름
            shipping_address: 배송 주소
            shipping_phone: 연락처
            payment_info: 결제 정보 {"card_number", "card_expiry", "card_cvv"}

        Returns:
            (Order, fds_result): 생성된 주문 및 FDS 평가 결과

        Raises:
            ValidationError: 장바구니가 비어있거나 재고 부족
            BusinessLogicError: 주문 생성 실패
        """
        # 1. 장바구니 조회
        result = await self.db.execute(
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
        )
        cart = result.scalars().first()

        if not cart or not cart.items:
            raise ValidationError("장바구니가 비어있습니다")

        # 2. 재고 확인 및 총 금액 계산
        total_amount = 0.0
        order_items_data = []

        for cart_item in cart.items:
            product = cart_item.product
            if not product:
                raise ValidationError(f"상품을 찾을 수 없습니다")

            if not product.can_purchase(cart_item.quantity):
                raise ValidationError(
                    f"재고 부족: {product.name} (요청 {cart_item.quantity}개, 재고 {product.stock_quantity}개)"
                )

            subtotal = float(product.price) * cart_item.quantity
            total_amount += subtotal

            order_items_data.append({
                "product": product,
                "quantity": cart_item.quantity,
                "unit_price": float(product.price)
            })

        # 3. 주문 생성
        order = Order(
            order_number=Order.generate_order_number(),
            user_id=user_id,
            total_amount=total_amount,
            status=OrderStatus.PENDING,
            shipping_name=shipping_name,
            shipping_address=shipping_address,
            shipping_phone=shipping_phone
        )
        self.db.add(order)
        await self.db.flush()  # ID 생성

        # 4. 주문 항목 생성 및 재고 차감
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data["product"].id,
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"]
            )
            self.db.add(order_item)

            # 재고 차감
            item_data["product"].update_stock(-item_data["quantity"])

        # 5. 결제 정보 생성 (토큰화)
        from src.models.payment import Payment
        payment = await self._create_payment(order.id, total_amount, payment_info)

        # 6. FDS 평가 요청 (비동기)
        fds_result = await self._evaluate_transaction(
            user_id=user_id,
            order_id=str(order.id),
            amount=total_amount,
            ip_address="127.0.0.1"  # 실제로는 request에서 가져와야 함
        )

        # 7. FDS 결과에 따른 처리
        if fds_result["risk_level"] == "low":
            # 정상 거래: 자동 승인
            payment.mark_as_completed(transaction_id=f"TXN-{order.order_number}")
            order.mark_as_paid()
        elif fds_result["risk_level"] == "medium":
            # 중간 위험: 추가 인증 필요 (Phase 4에서 구현)
            pass
        elif fds_result["risk_level"] == "high":
            # 고위험: 자동 차단 (Phase 4에서 구현)
            payment.mark_as_failed(reason="고위험 거래로 자동 차단됨")
            order.cancel()

        await self.db.commit()
        await self.db.refresh(order)

        # 8. 장바구니 비우기
        for cart_item in cart.items:
            await self.db.delete(cart_item)
        await self.db.commit()

        return order, fds_result

    async def get_order_by_id(self, user_id: str, order_id: str) -> Order:
        """
        주문 상세 조회

        Args:
            user_id: 사용자 ID (권한 확인용)
            order_id: 주문 ID

        Returns:
            Order: 주문 객체

        Raises:
            ResourceNotFoundError: 주문을 찾을 수 없거나 권한이 없는 경우
        """
        result = await self.db.execute(
            select(Order)
            .where(and_(Order.id == order_id, Order.user_id == user_id))
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.payment)
            )
        )
        order = result.scalars().first()

        if not order:
            raise ResourceNotFoundError(f"주문을 찾을 수 없습니다: {order_id}")

        return order

    async def get_user_orders(
        self,
        user_id: str,
        status: Optional[OrderStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Order]:
        """
        사용자의 주문 목록 조회

        Args:
            user_id: 사용자 ID
            status: 주문 상태 필터 (선택)
            limit: 조회 개수
            offset: 오프셋

        Returns:
            List[Order]: 주문 목록
        """
        query = select(Order).where(Order.user_id == user_id)

        if status:
            query = query.where(Order.status == status)

        query = query.order_by(Order.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        orders = result.scalars().all()

        return list(orders)

    async def cancel_order(self, user_id: str, order_id: str) -> Order:
        """
        주문 취소

        Args:
            user_id: 사용자 ID
            order_id: 주문 ID

        Returns:
            Order: 취소된 주문 객체

        Raises:
            ResourceNotFoundError: 주문을 찾을 수 없는 경우
            BusinessLogicError: 취소 불가능한 상태
        """
        order = await self.get_order_by_id(user_id, order_id)

        if not order.can_cancel():
            raise BusinessLogicError(f"주문 취소 불가: 현재 상태 {order.status}")

        # 재고 복원
        for item in order.items:
            if item.product:
                item.product.update_stock(item.quantity)

        order.cancel()

        # 결제 취소
        if order.payment and order.payment.status == PaymentStatus.COMPLETED:
            order.payment.mark_as_refunded()

        await self.db.commit()
        await self.db.refresh(order)

        return order

    async def track_order(self, user_id: str, order_id: str) -> dict:
        """
        주문 추적 정보

        Args:
            user_id: 사용자 ID
            order_id: 주문 ID

        Returns:
            dict: 주문 추적 정보
        """
        order = await self.get_order_by_id(user_id, order_id)

        tracking_info = {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": order.status,
            "status_history": [],
            "estimated_delivery": None
        }

        # 상태 히스토리 구성
        if order.created_at:
            tracking_info["status_history"].append({
                "status": "pending",
                "timestamp": order.created_at.isoformat(),
                "description": "주문 접수"
            })

        if order.paid_at:
            tracking_info["status_history"].append({
                "status": "paid",
                "timestamp": order.paid_at.isoformat(),
                "description": "결제 완료"
            })

        if order.shipped_at:
            tracking_info["status_history"].append({
                "status": "shipped",
                "timestamp": order.shipped_at.isoformat(),
                "description": "배송 시작"
            })

        if order.delivered_at:
            tracking_info["status_history"].append({
                "status": "delivered",
                "timestamp": order.delivered_at.isoformat(),
                "description": "배송 완료"
            })

        if order.cancelled_at:
            tracking_info["status_history"].append({
                "status": "cancelled",
                "timestamp": order.cancelled_at.isoformat(),
                "description": "주문 취소"
            })

        return tracking_info

    # 관리자 전용 메서드

    async def update_order_status(self, order_id: str, new_status: OrderStatus) -> Order:
        """
        주문 상태 변경 (관리자 전용)

        Args:
            order_id: 주문 ID
            new_status: 새로운 상태

        Returns:
            Order: 업데이트된 주문 객체
        """
        result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalars().first()

        if not order:
            raise ResourceNotFoundError(f"주문을 찾을 수 없습니다: {order_id}")

        # 상태 전이 처리
        if new_status == OrderStatus.SHIPPED:
            order.mark_as_shipped()
        elif new_status == OrderStatus.DELIVERED:
            order.mark_as_delivered()
        elif new_status == OrderStatus.CANCELLED:
            order.cancel()
        else:
            order.status = new_status

        await self.db.commit()
        await self.db.refresh(order)

        return order

    # 내부 메서드

    async def _create_payment(
        self,
        order_id: str,
        amount: float,
        payment_info: Dict[str, str]
    ) -> Payment:
        """결제 정보 생성 (내부 메서드)"""
        card_number = payment_info.get("card_number", "")
        card_token = Payment.tokenize_card(card_number)
        card_last_four = Payment.get_last_four_digits(card_number)

        payment = Payment(
            order_id=order_id,
            payment_method=PaymentMethod.CREDIT_CARD,
            amount=amount,
            status=PaymentStatus.PENDING,
            card_token=card_token,
            card_last_four=card_last_four
        )

        self.db.add(payment)
        return payment

    async def _evaluate_transaction(
        self,
        user_id: str,
        order_id: str,
        amount: float,
        ip_address: str
    ) -> dict:
        """
        FDS 서비스에 거래 평가 요청 (내부 메서드)

        Args:
            user_id: 사용자 ID
            order_id: 주문 ID
            amount: 거래 금액
            ip_address: IP 주소

        Returns:
            dict: FDS 평가 결과
        """
        fds_url = f"{self.settings.FDS_SERVICE_URL}/internal/fds/evaluate"

        request_data = {
            "transaction_id": order_id,
            "user_id": user_id,
            "amount": amount,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.post(fds_url, json=request_data)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            # FDS 서비스 연결 실패 시 기본 승인 (개발 환경)
            return {
                "transaction_id": order_id,
                "risk_score": 15,
                "risk_level": "low",
                "decision": "approve",
                "evaluation_metadata": {
                    "evaluation_time_ms": 0,
                    "error": f"FDS service unavailable: {str(e)}"
                }
            }
