"""
데이터베이스 시드 데이터 생성 스크립트

테스트 및 데모용 초기 데이터를 생성합니다.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
import random
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

# 모델 임포트
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.models import Base
from src.models.user import User, UserRole, UserStatus
from src.models.product import Product, ProductStatus
from src.models.cart import Cart, CartItem
from src.models.order import Order, OrderItem, OrderStatus
from src.models.payment import Payment, PaymentStatus, PaymentMethod
from src.config import get_settings
from src.utils.security import hash_password

settings = get_settings()

# 데이터베이스 엔진 설정
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def create_users(session: AsyncSession) -> dict:
    """사용자 생성"""
    print("[INFO] 사용자 생성 중...")

    users_data = [
        # 테스트 고객
        {
            "email": "customer1@example.com",
            "password": "password123",
            "name": "김철수",
            "role": UserRole.CUSTOMER,
        },
        {
            "email": "customer2@example.com",
            "password": "password123",
            "name": "이영희",
            "role": UserRole.CUSTOMER,
        },
        {
            "email": "customer3@example.com",
            "password": "password123",
            "name": "박민수",
            "role": UserRole.CUSTOMER,
        },
        # 관리자
        {
            "email": "admin@shopfds.com",
            "password": "admin123",
            "name": "관리자",
            "role": UserRole.ADMIN,
        },
        # 보안팀
        {
            "email": "security@shopfds.com",
            "password": "security123",
            "name": "보안팀",
            "role": UserRole.SECURITY_TEAM,
        },
    ]

    users = {}
    for data in users_data:
        user = User(
            id=uuid.uuid4(),
            email=data["email"],
            password_hash=hash_password(data["password"]),
            name=data["name"],
            role=data["role"],
            status=UserStatus.ACTIVE,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(user)
        users[data["email"]] = user

    await session.commit()
    print(f"[SUCCESS] {len(users)} 명 사용자 생성 완료")
    return users


async def create_products(session: AsyncSession) -> list:
    """상품 생성"""
    print("[INFO] 상품 생성 중...")

    products_data = [
        # 전자제품
        {
            "name": "노트북 Pro 15",
            "category": "전자제품",
            "price": 1890000,
            "stock": 50,
            "description": "고성능 프로세서와 대용량 메모리를 탑재한 프리미엄 노트북",
            "image_url": "https://via.placeholder.com/300x300?text=Laptop",
        },
        {
            "name": "스마트폰 X12",
            "category": "전자제품",
            "price": 1290000,
            "stock": 100,
            "description": "최신 카메라 기술과 5G를 지원하는 플래그십 스마트폰",
            "image_url": "https://via.placeholder.com/300x300?text=Smartphone",
        },
        {
            "name": "무선 이어폰",
            "category": "전자제품",
            "price": 299000,
            "stock": 200,
            "description": "노이즈 캔슬링 기능을 갖춘 프리미엄 무선 이어폰",
            "image_url": "https://via.placeholder.com/300x300?text=Earphones",
        },
        # 의류
        {
            "name": "캐주얼 셔츠",
            "category": "의류",
            "price": 59000,
            "stock": 150,
            "description": "데일리룩에 완벽한 편안한 캐주얼 셔츠",
            "image_url": "https://via.placeholder.com/300x300?text=Shirt",
        },
        {
            "name": "슬림 진",
            "category": "의류",
            "price": 89000,
            "stock": 100,
            "description": "스타일리시한 슬림핏 데님 진",
            "image_url": "https://via.placeholder.com/300x300?text=Jeans",
        },
        # 도서
        {
            "name": "파이썬 프로그래밍",
            "category": "도서",
            "price": 35000,
            "stock": 50,
            "description": "초보자를 위한 파이썬 프로그래밍 완벽 가이드",
            "image_url": "https://via.placeholder.com/300x300?text=Python+Book",
        },
        {
            "name": "머신러닝 입문",
            "category": "도서",
            "price": 42000,
            "stock": 30,
            "description": "실습으로 배우는 머신러닝 기초",
            "image_url": "https://via.placeholder.com/300x300?text=ML+Book",
        },
        # 식품
        {
            "name": "프리미엄 커피 원두",
            "category": "식품",
            "price": 25000,
            "stock": 80,
            "description": "콜롬비아산 100% 아라비카 원두",
            "image_url": "https://via.placeholder.com/300x300?text=Coffee",
        },
        {
            "name": "유기농 꿀",
            "category": "식품",
            "price": 18000,
            "stock": 60,
            "description": "국내산 100% 천연 유기농 꿀",
            "image_url": "https://via.placeholder.com/300x300?text=Honey",
        },
        # 가구
        {
            "name": "인체공학 의자",
            "category": "가구",
            "price": 489000,
            "stock": 20,
            "description": "장시간 사용해도 편안한 인체공학적 설계",
            "image_url": "https://via.placeholder.com/300x300?text=Chair",
        },
        {
            "name": "스탠딩 데스크",
            "category": "가구",
            "price": 689000,
            "stock": 15,
            "description": "높이 조절 가능한 전동 스탠딩 데스크",
            "image_url": "https://via.placeholder.com/300x300?text=Desk",
        },
        # 스포츠
        {
            "name": "요가 매트",
            "category": "스포츠",
            "price": 39000,
            "stock": 100,
            "description": "미끄럼 방지 프리미엄 요가 매트",
            "image_url": "https://via.placeholder.com/300x300?text=Yoga+Mat",
        },
        {
            "name": "덤벨 세트",
            "category": "스포츠",
            "price": 129000,
            "stock": 40,
            "description": "홈트레이닝용 조절식 덤벨 세트",
            "image_url": "https://via.placeholder.com/300x300?text=Dumbbells",
        },
    ]

    products = []
    for data in products_data:
        product = Product(
            id=uuid.uuid4(),
            name=data["name"],
            description=data["description"],
            price=Decimal(str(data["price"])),
            stock_quantity=data["stock"],
            category=data["category"],
            status=ProductStatus.AVAILABLE,
            image_url=data.get("image_url"),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(product)
        products.append(product)

    await session.commit()
    print(f"[SUCCESS] {len(products)} 개 상품 생성 완료")
    return products


async def create_sample_orders(
    session: AsyncSession,
    users: dict,
    products: list
) -> list:
    """샘플 주문 생성"""
    print("[INFO] 샘플 주문 생성 중...")

    orders = []

    # 각 고객별로 주문 생성
    for email in ["customer1@example.com", "customer2@example.com"]:
        user = users[email]

        # 2-3개의 주문 생성
        for order_idx in range(random.randint(2, 3)):
            # 주문 생성
            order = Order(
                id=uuid.uuid4(),
                user_id=user.id,
                order_number=f"ORD{datetime.now().strftime('%y%m%d')}{uuid.uuid4().hex[:6].upper()}",
                status=random.choice([
                    OrderStatus.DELIVERED,
                    OrderStatus.PREPARING,
                    OrderStatus.PENDING,
                ]),
                shipping_name=user.name,
                shipping_address=f"서울시 강남구 테스트로 {random.randint(1, 100)}",
                shipping_phone=f"010-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
                created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=random.randint(1, 30)),
            )

            # 주문 항목 추가 (1-3개)
            total_amount = Decimal("0")
            selected_products = random.sample(products, random.randint(1, 3))

            for product in selected_products:
                quantity = random.randint(1, 3)
                subtotal = product.price * quantity
                total_amount += subtotal

                order_item = OrderItem(
                    id=uuid.uuid4(),
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=product.price,
                )
                session.add(order_item)

            order.total_amount = total_amount

            # 결제 정보 추가
            if order.status in [OrderStatus.DELIVERED, OrderStatus.PREPARING]:
                payment = Payment(
                    id=uuid.uuid4(),
                    order_id=order.id,
                    amount=total_amount,
                    payment_method=PaymentMethod.CREDIT_CARD,
                    status=PaymentStatus.COMPLETED if order.status == OrderStatus.DELIVERED
                           else PaymentStatus.PENDING,
                    card_token=f"tok_{uuid.uuid4().hex[:16]}",
                    card_last_four=f"{random.randint(1000, 9999)}",
                    created_at=order.created_at,
                )
                session.add(payment)

            session.add(order)
            orders.append(order)

    await session.commit()
    print(f"[SUCCESS] {len(orders)} 개 주문 생성 완료")
    return orders


async def create_carts(session: AsyncSession, users: dict, products: list) -> None:
    """장바구니 샘플 데이터 생성"""
    print("[INFO] 장바구니 데이터 생성 중...")

    # customer3에게만 장바구니 생성
    user = users["customer3@example.com"]

    cart = Cart(
        id=uuid.uuid4(),
        user_id=user.id,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(cart)

    # 장바구니에 2-3개 상품 추가
    selected_products = random.sample(products, random.randint(2, 3))
    for product in selected_products:
        cart_item = CartItem(
            id=uuid.uuid4(),
            cart_id=cart.id,
            product_id=product.id,
            quantity=random.randint(1, 2),
            added_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(cart_item)

    await session.commit()
    print("[SUCCESS] 장바구니 데이터 생성 완료")


async def main():
    """메인 실행 함수"""
    print("[START] 시드 데이터 생성 시작")
    print(f"[INFO] 데이터베이스: {settings.DATABASE_URL}")

    try:
        # 테이블 생성
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[SUCCESS] 데이터베이스 테이블 생성/확인 완료")

        # 시드 데이터 생성
        async with AsyncSessionLocal() as session:
            # 기존 데이터 확인
            result = await session.execute(select(User).limit(1))
            if result.scalar():
                print("[WARNING] 이미 데이터가 존재합니다.")

                # 사용자에게 확인
                response = input("기존 데이터를 삭제하고 새로 생성하시겠습니까? (y/N): ")
                if response.lower() != 'y':
                    print("[SKIP] 시드 데이터 생성을 건너뜁니다.")
                    return

                print("[INFO] 기존 데이터 삭제 중...")
                # 테이블 순서대로 삭제 (외래 키 제약 고려)
                await session.execute(text("DELETE FROM cart_items"))
                await session.execute(text("DELETE FROM carts"))
                await session.execute(text("DELETE FROM order_items"))
                await session.execute(text("DELETE FROM payments"))
                await session.execute(text("DELETE FROM orders"))
                await session.execute(text("DELETE FROM products"))
                await session.execute(text("DELETE FROM users"))
                await session.commit()
                print("[SUCCESS] 기존 데이터 삭제 완료")

            # 데이터 생성
            users = await create_users(session)
            products = await create_products(session)
            await create_sample_orders(session, users, products)
            await create_carts(session, users, products)

        print("[COMPLETE] 시드 데이터 생성 완료!")
        print("\n[테스트 계정 정보]")
        print("- 고객: customer1@example.com / password123")
        print("- 고객: customer2@example.com / password123")
        print("- 고객: customer3@example.com / password123 (장바구니 있음)")
        print("- 관리자: admin@shopfds.com / admin123")
        print("- 보안팀: security@shopfds.com / security123")

    except Exception as e:
        print(f"[ERROR] 시드 데이터 생성 실패: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())