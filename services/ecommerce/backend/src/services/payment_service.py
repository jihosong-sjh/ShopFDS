"""
결제 서비스

결제 처리 및 토큰화 등 결제 관련 비즈니스 로직
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.payment import Payment, PaymentStatus, PaymentMethod
from src.models.order import Order, OrderStatus
from src.utils.exceptions import (
    ResourceNotFoundError,
    BusinessLogicError,
    ValidationError,
)


class PaymentService:
    """결제 관련 비즈니스 로직"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_payment_by_order_id(self, order_id: str) -> Payment:
        """
        주문 ID로 결제 정보 조회

        Args:
            order_id: 주문 ID

        Returns:
            Payment: 결제 객체

        Raises:
            ResourceNotFoundError: 결제 정보를 찾을 수 없는 경우
        """
        result = await self.db.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        payment = result.scalars().first()

        if not payment:
            raise ResourceNotFoundError(f"결제 정보를 찾을 수 없습니다: order_id={order_id}")

        return payment

    async def process_payment(
        self, order_id: str, card_number: str, card_expiry: str, card_cvv: str
    ) -> Payment:
        """
        결제 처리

        실제 구현에서는 PCI-DSS 준수 결제 게이트웨이 (Stripe, Toss Payments 등)를 사용해야 함

        Args:
            order_id: 주문 ID
            card_number: 카드 번호 (토큰화 전)
            card_expiry: 유효기간
            card_cvv: CVV

        Returns:
            Payment: 결제 완료된 Payment 객체

        Raises:
            ValidationError: 결제 정보가 유효하지 않은 경우
            BusinessLogicError: 결제 처리 실패
        """
        # 주문 조회
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        order = result.scalars().first()

        if not order:
            raise ResourceNotFoundError(f"주문을 찾을 수 없습니다: {order_id}")

        if order.status != OrderStatus.PENDING:
            raise BusinessLogicError(f"결제 가능한 상태가 아닙니다: {order.status}")

        # 카드 번호 검증 (기본 검증)
        card_digits = "".join(filter(str.isdigit, card_number))
        if len(card_digits) < 13 or len(card_digits) > 19:
            raise ValidationError("유효하지 않은 카드 번호입니다")

        # 카드 토큰화 (실제로는 외부 결제 게이트웨이 사용)
        card_token = Payment.tokenize_card(card_number)
        card_last_four = Payment.get_last_four_digits(card_number)

        # 결제 정보 생성
        payment = Payment(
            order_id=order_id,
            payment_method=PaymentMethod.CREDIT_CARD,
            amount=order.total_amount,
            status=PaymentStatus.PENDING,
            card_token=card_token,
            card_last_four=card_last_four,
        )

        self.db.add(payment)
        await self.db.flush()

        # 결제 게이트웨이 호출 (시뮬레이션)
        try:
            transaction_id = await self._call_payment_gateway(
                card_token=card_token,
                amount=float(order.total_amount),
                card_expiry=card_expiry,
                card_cvv=card_cvv,
            )

            # 결제 성공
            payment.mark_as_completed(transaction_id=transaction_id)
            order.mark_as_paid()

            await self.db.commit()
            await self.db.refresh(payment)

            return payment

        except Exception as e:
            # 결제 실패
            payment.mark_as_failed(reason=str(e))
            await self.db.commit()
            raise BusinessLogicError(f"결제 처리 실패: {str(e)}")

    async def refund_payment(
        self, payment_id: str, reason: Optional[str] = None
    ) -> Payment:
        """
        결제 환불

        Args:
            payment_id: 결제 ID
            reason: 환불 사유

        Returns:
            Payment: 환불된 Payment 객체

        Raises:
            ResourceNotFoundError: 결제를 찾을 수 없는 경우
            BusinessLogicError: 환불 불가능한 상태
        """
        result = await self.db.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalars().first()

        if not payment:
            raise ResourceNotFoundError(f"결제를 찾을 수 없습니다: {payment_id}")

        if payment.status != PaymentStatus.COMPLETED:
            raise BusinessLogicError(f"환불 가능한 상태가 아닙니다: {payment.status}")

        # 결제 게이트웨이 환불 호출 (시뮬레이션)
        try:
            await self._call_payment_gateway_refund(
                transaction_id=payment.transaction_id, amount=float(payment.amount)
            )

            # 환불 성공
            payment.mark_as_refunded()

            # 주문 상태 변경
            result = await self.db.execute(
                select(Order).where(Order.id == payment.order_id)
            )
            order = result.scalars().first()
            if order:
                order.status = OrderStatus.REFUNDED

            await self.db.commit()
            await self.db.refresh(payment)

            return payment

        except Exception as e:
            raise BusinessLogicError(f"환불 처리 실패: {str(e)}")

    async def verify_payment(self, payment_id: str) -> dict:
        """
        결제 검증

        Args:
            payment_id: 결제 ID

        Returns:
            dict: 결제 상태 정보
        """
        result = await self.db.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalars().first()

        if not payment:
            raise ResourceNotFoundError(f"결제를 찾을 수 없습니다: {payment_id}")

        return {
            "payment_id": str(payment.id),
            "order_id": str(payment.order_id),
            "status": payment.status,
            "amount": float(payment.amount),
            "payment_method": payment.payment_method,
            "card_last_four": payment.card_last_four,
            "transaction_id": payment.transaction_id,
            "created_at": (
                payment.created_at.isoformat() if payment.created_at else None
            ),
            "completed_at": (
                payment.completed_at.isoformat() if payment.completed_at else None
            ),
        }

    # 내부 메서드 (결제 게이트웨이 연동 시뮬레이션)

    async def _call_payment_gateway(
        self, card_token: str, amount: float, card_expiry: str, card_cvv: str
    ) -> str:
        """
        결제 게이트웨이 호출 (시뮬레이션)

        실제 구현에서는 Stripe, Toss Payments 등의 API를 호출해야 함
        """
        import uuid
        import random

        # 10% 확률로 결제 실패 시뮬레이션
        if random.random() < 0.1:
            raise Exception("결제 게이트웨이 오류: 카드 승인 거부")

        # 거래 ID 생성 (실제로는 게이트웨이에서 받음)
        transaction_id = f"PG-{uuid.uuid4().hex[:12].upper()}"

        return transaction_id

    async def _call_payment_gateway_refund(
        self, transaction_id: str, amount: float
    ) -> bool:
        """
        결제 게이트웨이 환불 호출 (시뮬레이션)

        실제 구현에서는 결제 게이트웨이의 환불 API를 호출해야 함
        """
        # 시뮬레이션: 항상 성공
        return True

    @staticmethod
    def mask_card_number(card_number: str) -> str:
        """
        카드 번호 마스킹 (표시용)

        Args:
            card_number: 카드 번호

        Returns:
            str: 마스킹된 카드 번호 (예: ****-****-****-1234)
        """
        card_digits = "".join(filter(str.isdigit, card_number))
        if len(card_digits) < 4:
            return "****"

        last_four = card_digits[-4:]
        return f"****-****-****-{last_four}"
