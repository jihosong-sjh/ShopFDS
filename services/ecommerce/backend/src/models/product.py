"""
상품(Product) 모델

목적: 판매 중인 상품 정보
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    String,
    Text,
    DECIMAL,
    Integer,
    DateTime,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
import uuid

from .base import Base


class ProductStatus(str, Enum):
    """상품 상태"""

    AVAILABLE = "available"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


class Product(Base):
    """상품 모델"""

    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(DECIMAL(10, 2), nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)
    category = Column(String(100), nullable=False, index=True)
    image_url = Column(String(500), nullable=True)
    status = Column(
        ENUM(ProductStatus, name="product_status_enum", create_type=True),
        nullable=False,
        default=ProductStatus.AVAILABLE,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 제약 조건
    __table_args__ = (
        CheckConstraint("price >= 0", name="check_price_non_negative"),
        CheckConstraint("stock_quantity >= 0", name="check_stock_non_negative"),
        Index("idx_products_category", "category"),
        Index("idx_products_status", "status"),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name}, price={self.price})>"

    def is_available(self) -> bool:
        """상품이 구매 가능한지 확인"""
        return self.status == ProductStatus.AVAILABLE and self.stock_quantity > 0

    def can_purchase(self, quantity: int) -> bool:
        """지정된 수량만큼 구매 가능한지 확인"""
        return self.is_available() and self.stock_quantity >= quantity

    def update_stock(self, quantity_delta: int):
        """재고 수량 업데이트 (음수: 감소, 양수: 증가)"""
        new_quantity = self.stock_quantity + quantity_delta
        if new_quantity < 0:
            raise ValueError(
                f"재고 부족: 현재 {self.stock_quantity}, 요청 {abs(quantity_delta)}"
            )

        self.stock_quantity = new_quantity

        # 재고가 0이 되면 자동으로 품절 상태로 변경
        if self.stock_quantity == 0 and self.status == ProductStatus.AVAILABLE:
            self.status = ProductStatus.OUT_OF_STOCK
        # 재고가 다시 생기면 판매 가능 상태로 복원
        elif self.stock_quantity > 0 and self.status == ProductStatus.OUT_OF_STOCK:
            self.status = ProductStatus.AVAILABLE
