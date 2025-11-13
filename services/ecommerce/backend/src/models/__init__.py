"""
데이터베이스 모델 패키지

이 패키지는 모든 SQLAlchemy 모델을 관리합니다.
새로운 모델을 추가할 때는 이 파일에서 import하여 Alembic이 자동으로 감지할 수 있도록 합니다.
"""

from src.models.base import Base, TimestampMixin, get_db, init_db, drop_db, close_db
from src.models.user import User, UserRole, UserStatus
from src.models.product import Product, ProductStatus
from src.models.cart import Cart, CartItem
from src.models.order import Order, OrderItem, OrderStatus
from src.models.payment import Payment, PaymentMethod, PaymentStatus

__all__ = [
    "Base",
    "TimestampMixin",
    "get_db",
    "init_db",
    "drop_db",
    "close_db",
    "User",
    "UserRole",
    "UserStatus",
    "Product",
    "ProductStatus",
    "Cart",
    "CartItem",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Payment",
    "PaymentMethod",
    "PaymentStatus",
]
