"""
데이터베이스 모델 패키지

이 패키지는 모든 SQLAlchemy 모델을 관리합니다.
새로운 모델을 추가할 때는 이 파일에서 import하여 Alembic이 자동으로 감지할 수 있도록 합니다.
"""

from src.models.base import Base, TimestampMixin, get_db, init_db, drop_db, close_db

# 향후 추가될 모델들을 여기서 import합니다
# from src.models.user import User
# from src.models.product import Product
# from src.models.cart import Cart, CartItem
# from src.models.order import Order, OrderItem
# from src.models.payment import Payment

__all__ = [
    "Base",
    "TimestampMixin",
    "get_db",
    "init_db",
    "drop_db",
    "close_db",
    # "User",
    # "Product",
    # "Cart",
    # "CartItem",
    # "Order",
    # "OrderItem",
    # "Payment",
]
