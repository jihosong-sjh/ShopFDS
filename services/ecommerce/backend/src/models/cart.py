"""
장바구니(Cart) 및 장바구니 항목(CartItem) 모델

목적: 사용자별 구매 예정 상품 목록
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class Cart(Base):
    """장바구니 모델 (사용자당 1개)"""

    __tablename__ = "carts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 관계
    user = relationship("User", back_populates="cart")
    items = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Cart(id={self.id}, user_id={self.user_id})>"

    def get_total_amount(self) -> float:
        """장바구니 총 금액 계산"""
        total = 0.0
        for item in self.items:
            if item.product:
                total += float(item.product.price) * item.quantity
        return total

    def get_item_count(self) -> int:
        """장바구니 아이템 총 개수"""
        return sum(item.quantity for item in self.items)


class CartItem(Base):
    """장바구니 항목 모델"""

    __tablename__ = "cart_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    cart_id = Column(Uuid, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(
        Uuid,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity = Column(Integer, nullable=False, default=1)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 관계
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")

    # 제약 조건
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_cart_quantity_positive"),
        UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),  # 중복 상품 방지
    )

    def __repr__(self):
        return f"<CartItem(id={self.id}, product_id={self.product_id}, quantity={self.quantity})>"

    def get_subtotal(self) -> float:
        """이 항목의 소계 계산"""
        if self.product:
            return float(self.product.price) * self.quantity
        return 0.0

    def update_quantity(self, new_quantity: int):
        """수량 업데이트"""
        if new_quantity <= 0:
            raise ValueError("수량은 1 이상이어야 합니다")

        if self.product and not self.product.can_purchase(new_quantity):
            raise ValueError(
                f"재고 부족: 요청 {new_quantity}, 재고 {self.product.stock_quantity}"
            )

        self.quantity = new_quantity
