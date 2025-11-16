"""
샘플 상품 데이터 생성 스크립트

개발 환경에서 테스트용 상품 데이터를 생성합니다.
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import uuid
from decimal import Decimal

from src.models.product import Product, ProductStatus
from src.models.base import Base

# 데이터베이스 URL
DATABASE_URL = "postgresql+asyncpg://shopfds_user:shopfds_password@localhost:5432/shopfds"

# 샘플 상품 데이터
SAMPLE_PRODUCTS = [
    # 전자기기
    {
        "name": "갤럭시 S24 Ultra",
        "description": "최신 삼성 플래그십 스마트폰. 200MP 카메라, S펜 내장, 6.8인치 AMOLED 디스플레이",
        "price": Decimal("1450000"),
        "stock_quantity": 50,
        "category": "전자기기",
        "image_url": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    {
        "name": "아이폰 15 Pro",
        "description": "Apple의 최신 프로 모델. A17 Pro 칩, 티타늄 디자인, 48MP 메인 카메라",
        "price": Decimal("1550000"),
        "stock_quantity": 35,
        "category": "전자기기",
        "image_url": "https://images.unsplash.com/photo-1592286927505-f0e2c0b1e5d1?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    {
        "name": "맥북 프로 14인치",
        "description": "M3 Pro 칩 탑재. 14인치 Liquid Retina XDR 디스플레이, 18시간 배터리",
        "price": Decimal("2890000"),
        "stock_quantity": 20,
        "category": "전자기기",
        "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    {
        "name": "에어팟 프로 2세대",
        "description": "능동 소음 차단, 적응형 투명 모드, MagSafe 충전 케이스",
        "price": Decimal("359000"),
        "stock_quantity": 100,
        "category": "전자기기",
        "image_url": "https://images.unsplash.com/photo-1606841837239-c5a1a4a07af7?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    # 의류
    {
        "name": "나이키 에어맥스 270",
        "description": "편안한 쿠셔닝과 세련된 디자인. 다양한 컬러 옵션 제공",
        "price": Decimal("189000"),
        "stock_quantity": 80,
        "category": "의류",
        "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    {
        "name": "아디다스 울트라부스트",
        "description": "BOOST 미드솔로 최고의 쿠셔닝 제공. 러닝에 최적화",
        "price": Decimal("220000"),
        "stock_quantity": 60,
        "category": "의류",
        "image_url": "https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    {
        "name": "노스페이스 다운 재킷",
        "description": "700 필 파워 구스 다운. 방수 및 방풍 기능",
        "price": Decimal("329000"),
        "stock_quantity": 45,
        "category": "의류",
        "image_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    # 도서
    {
        "name": "클린 코드 (Clean Code)",
        "description": "로버트 C. 마틴 저. 애자일 소프트웨어 장인 정신",
        "price": Decimal("33000"),
        "stock_quantity": 150,
        "category": "도서",
        "image_url": "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    {
        "name": "디자인 패턴",
        "description": "GoF의 디자인 패턴. 소프트웨어 설계의 고전",
        "price": Decimal("38000"),
        "stock_quantity": 120,
        "category": "도서",
        "image_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    {
        "name": "파이썬 코딩의 기술",
        "description": "브렛 슬래킨 저. Effective Python 2nd Edition",
        "price": Decimal("30000"),
        "stock_quantity": 100,
        "category": "도서",
        "image_url": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    # 가구
    {
        "name": "에르고휴먼 의자",
        "description": "메쉬 소재 인체공학 의자. 요추 지지대, 팔걸이 조절 가능",
        "price": Decimal("890000"),
        "stock_quantity": 25,
        "category": "가구",
        "image_url": "https://images.unsplash.com/photo-1580480055273-228ff5388ef8?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    {
        "name": "높이조절 책상",
        "description": "전동 높이 조절 스탠딩 데스크. 140x70cm, 메모리 기능",
        "price": Decimal("550000"),
        "stock_quantity": 30,
        "category": "가구",
        "image_url": "https://images.unsplash.com/photo-1595515106969-1ce29566ff1c?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    # 식품
    {
        "name": "프리미엄 아라비카 원두",
        "description": "에티오피아 예가체프 원두 1kg. 플로럴한 향과 부드러운 산미",
        "price": Decimal("35000"),
        "stock_quantity": 200,
        "category": "식품",
        "image_url": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    {
        "name": "유기농 녹차 세트",
        "description": "제주 유기농 녹차 100g x 3종 세트. 우전, 세작, 중작",
        "price": Decimal("42000"),
        "stock_quantity": 150,
        "category": "식품",
        "image_url": "https://images.unsplash.com/photo-1564890369478-c89ca6d9cde9?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    # 재고 부족 상품 (테스트용)
    {
        "name": "한정판 스니커즈",
        "description": "한정 수량 스페셜 에디션. 재입고 미정",
        "price": Decimal("450000"),
        "stock_quantity": 3,
        "category": "의류",
        "image_url": "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=500",
        "status": ProductStatus.AVAILABLE.value,
    },
    # 품절 상품 (테스트용)
    {
        "name": "품절된 상품",
        "description": "현재 재고가 없습니다. 곧 재입고 예정",
        "price": Decimal("99000"),
        "stock_quantity": 0,
        "category": "전자기기",
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500",
        "status": ProductStatus.OUT_OF_STOCK.value,
    },
]


async def create_products():
    """샘플 상품 데이터 생성"""
    # 데이터베이스 엔진 생성
    engine = create_async_engine(DATABASE_URL, echo=True)

    # 세션 팩토리 생성
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # 기존 상품 수 확인
            from sqlalchemy import select, func

            result = await session.execute(select(func.count(Product.id)))
            existing_count = result.scalar()

            if existing_count > 0:
                print(f"⚠️  이미 {existing_count}개의 상품이 존재합니다.")
                overwrite = input("기존 상품을 모두 삭제하고 새로 생성하시겠습니까? (y/N): ")
                if overwrite.lower() != "y":
                    print("❌ 취소되었습니다.")
                    return

                # 기존 상품 삭제
                await session.execute(Product.__table__.delete())
                print("🗑️  기존 상품을 모두 삭제했습니다.")

            # 샘플 상품 생성
            print(f"\n📦 {len(SAMPLE_PRODUCTS)}개의 샘플 상품을 생성합니다...\n")

            for idx, product_data in enumerate(SAMPLE_PRODUCTS, 1):
                product = Product(
                    id=uuid.uuid4(),
                    **product_data,
                )
                session.add(product)
                print(
                    f"  {idx}. {product.name} - ₩{product.price:,} ({product.category})"
                )

            await session.commit()
            print(f"\n✅ {len(SAMPLE_PRODUCTS)}개의 상품이 성공적으로 생성되었습니다!")

            # 카테고리별 통계
            print("\n📊 카테고리별 상품 수:")
            from collections import Counter

            categories = Counter([p["category"] for p in SAMPLE_PRODUCTS])
            for category, count in categories.items():
                print(f"  - {category}: {count}개")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ 오류 발생: {str(e)}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("🛍️  샘플 상품 데이터 생성 스크립트")
    print("=" * 60)
    asyncio.run(create_products())
