"""
주문(Order) 및 주문 항목(OrderItem) 모델

목적: 고객의 구매 주문
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Text, DECIMAL, Integer, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class OrderStatus(str, Enum):
    """주문 상태"""
    PENDING = "pending"        # 주문 접수 (결제 대기)
    PAID = "paid"              # 결제 완료 (배송 준비)
    PREPARING = "preparing"    # 배송 준비 중
    SHIPPED = "shipped"        # 배송 중
    DELIVERED = "delivered"    # 배송 완료
    CANCELLED = "cancelled"    # 취소됨
    REFUNDED = "refunded"      # 환불 완료


class Order(Base):
    """주문 모델"""
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(20), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(
        ENUM(OrderStatus, name="order_status_enum", create_type=True),
        nullable=False,
        default=OrderStatus.PENDING,
        index=True
    )

    # 배송 정보
    shipping_name = Column(String(100), nullable=False)
    shipping_address = Column(Text, nullable=False)
    shipping_phone = Column(String(20), nullable=False)

    # 타임스탬프
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    paid_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # 관계
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="order", uselist=False)

    # 제약 조건
    __table_args__ = (
        CheckConstraint('total_amount > 0', name='check_total_amount_positive'),
        Index('idx_orders_user_id', 'user_id'),
        Index('idx_orders_status', 'status'),
        Index('idx_orders_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<Order(id={self.id}, order_number={self.order_number}, status={self.status})>"

    @staticmethod
    def generate_order_number() -> str:
        """주문 번호 생성: ORD-YYYYMMDD-###"""
        from datetime import datetime
        date_str = datetime.utcnow().strftime("%Y%m%d")
        random_suffix = str(uuid.uuid4().int)[:3]
        return f"ORD-{date_str}-{random_suffix}"

    def can_cancel(self) -> bool:
        """주문 취소 가능 여부"""
        return self.status in [OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.PREPARING]

    def mark_as_paid(self):
        """결제 완료로 상태 변경"""
        if self.status != OrderStatus.PENDING:
            raise ValueError(f"결제 완료 처리 불가: 현재 상태 {self.status}")
        self.status = OrderStatus.PAID
        self.paid_at = datetime.utcnow()

    def mark_as_shipped(self):
        """배송 시작으로 상태 변경"""
        if self.status not in [OrderStatus.PAID, OrderStatus.PREPARING]:
            raise ValueError(f"배송 시작 처리 불가: 현재 상태 {self.status}")
        self.status = OrderStatus.SHIPPED
        self.shipped_at = datetime.utcnow()

    def mark_as_delivered(self):
        """배송 완료로 상태 변경"""
        if self.status != OrderStatus.SHIPPED:
            raise ValueError(f"배송 완료 처리 불가: 현재 상태 {self.status}")
        self.status = OrderStatus.DELIVERED
        self.delivered_at = datetime.utcnow()

    def cancel(self):
        """주문 취소"""
        if not self.can_cancel():
            raise ValueError(f"주문 취소 불가: 현재 상태 {self.status}")
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()


class OrderItem(Base):
    """주문 항목 모델 (주문 시점의 가격 기록)"""
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)  # 주문 시점의 가격

    # 관계
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

    # 제약 조건
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_order_item_quantity_positive'),
    )

    def __repr__(self):
        return f"<OrderItem(id={self.id}, product_id={self.product_id}, quantity={self.quantity})>"

    def get_subtotal(self) -> float:
        """이 항목의 소계 계산"""
        return float(self.unit_price) * self.quantity
