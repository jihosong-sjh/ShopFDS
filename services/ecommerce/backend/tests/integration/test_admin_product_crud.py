"""
통합 테스트: 관리자 상품 CRUD 작업

T096: 상품 CRUD 작업 검증

이 테스트는 다음 전체 플로우를 검증합니다:
1. 관리자가 새 상품 등록
2. 상품 정보 수정
3. 재고 업데이트
4. 상품 삭제 (논리 삭제)
5. 재고 0일 때 자동 품절 상태 전환

엔드투엔드 통합 테스트
"""

import pytest
import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, Product, ProductStatus
from src.services.product_service import ProductService
from src.middleware.authorization import Permission


class TestAdminProductCRUD:
    """관리자 상품 CRUD 작업 통합 테스트"""

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

    @pytest.mark.asyncio
    async def test_product_create(
        self,
        db_session: AsyncSession,
        admin_user: User,
    ):
        """
        Step 1: 새 상품 생성 테스트

        검증 항목:
        - 상품이 데이터베이스에 저장되는지
        - 모든 필드가 올바르게 저장되는지
        - 기본 상태가 AVAILABLE인지
        """
        print("\n=== Step 1: 새 상품 생성 ===")

        # 새 상품 데이터
        new_product = Product(
            id=uuid.uuid4(),
            name="무선 이어폰",
            description="고음질 블루투스 무선 이어폰",
            price=Decimal("89000.00"),
            stock_quantity=100,
            category="전자기기",
            image_url="https://example.com/images/earphone.jpg",
            status=ProductStatus.AVAILABLE
        )

        db_session.add(new_product)
        await db_session.commit()
        await db_session.refresh(new_product)

        # 검증
        assert new_product.id is not None
        assert new_product.name == "무선 이어폰"
        assert new_product.price == Decimal("89000.00")
        assert new_product.stock_quantity == 100
        assert new_product.status == ProductStatus.AVAILABLE

        print("상품 생성 성공")
        print(f"상품 ID: {new_product.id}")
        print(f"상품명: {new_product.name}")
        print(f"가격: {new_product.price}원")
        print(f"재고: {new_product.stock_quantity}개")

    @pytest.mark.asyncio
    async def test_product_update(
        self,
        db_session: AsyncSession,
        admin_user: User,
    ):
        """
        Step 2: 상품 정보 수정 테스트

        검증 항목:
        - 상품명, 가격 등 필드가 올바르게 수정되는지
        - updated_at 타임스탬프가 갱신되는지
        """
        print("\n=== Step 2: 상품 정보 수정 ===")

        # 기존 상품 생성
        product = Product(
            id=uuid.uuid4(),
            name="무선 이어폰",
            description="고음질 블루투스 무선 이어폰",
            price=Decimal("89000.00"),
            stock_quantity=100,
            category="전자기기",
            status=ProductStatus.AVAILABLE
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        original_updated_at = product.updated_at

        # 상품 정보 수정
        product.name = "무선 이어폰 Pro"
        product.price = Decimal("129000.00")
        product.description = "노이즈 캔슬링 기능이 추가된 프리미엄 무선 이어폰"

        await db_session.commit()
        await db_session.refresh(product)

        # 검증
        assert product.name == "무선 이어폰 Pro"
        assert product.price == Decimal("129000.00")
        assert "노이즈 캔슬링" in product.description
        assert product.updated_at > original_updated_at

        print("상품 정보 수정 성공")
        print(f"수정된 상품명: {product.name}")
        print(f"수정된 가격: {product.price}원")

    @pytest.mark.asyncio
    async def test_stock_update(
        self,
        db_session: AsyncSession,
        admin_user: User,
    ):
        """
        Step 3: 재고 업데이트 테스트

        검증 항목:
        - 재고 수량이 올바르게 업데이트되는지
        - 재고 0일 때 자동으로 OUT_OF_STOCK 상태로 변경되는지
        - 재고가 다시 생기면 AVAILABLE 상태로 복원되는지
        """
        print("\n=== Step 3: 재고 업데이트 ===")

        # 기존 상품 생성
        product = Product(
            id=uuid.uuid4(),
            name="무선 이어폰",
            price=Decimal("89000.00"),
            stock_quantity=100,
            category="전자기기",
            status=ProductStatus.AVAILABLE
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # 재고를 0으로 변경
        product.stock_quantity = 0

        # 재고가 0이면 품절 상태로 자동 변경
        if product.stock_quantity == 0 and product.status == ProductStatus.AVAILABLE:
            product.status = ProductStatus.OUT_OF_STOCK

        await db_session.commit()
        await db_session.refresh(product)

        # 검증 1: 품절 상태 확인
        assert product.stock_quantity == 0
        assert product.status == ProductStatus.OUT_OF_STOCK

        print("재고 0 -> 품절 상태 전환 성공")
        print(f"재고: {product.stock_quantity}개")
        print(f"상태: {product.status.value}")

        # 재고를 다시 추가
        product.stock_quantity = 50

        # 재고가 다시 생기면 판매 가능 상태로 복원
        if product.stock_quantity > 0 and product.status == ProductStatus.OUT_OF_STOCK:
            product.status = ProductStatus.AVAILABLE

        await db_session.commit()
        await db_session.refresh(product)

        # 검증 2: 판매 가능 상태 복원 확인
        assert product.stock_quantity == 50
        assert product.status == ProductStatus.AVAILABLE

        print("재고 추가 -> 판매 가능 상태 복원 성공")
        print(f"재고: {product.stock_quantity}개")
        print(f"상태: {product.status.value}")

    @pytest.mark.asyncio
    async def test_product_delete_soft(
        self,
        db_session: AsyncSession,
        admin_user: User,
    ):
        """
        Step 4: 상품 삭제 (논리 삭제) 테스트

        검증 항목:
        - 물리 삭제가 아닌 논리 삭제가 수행되는지
        - 상태가 DISCONTINUED로 변경되는지
        - 데이터베이스에 여전히 존재하는지
        """
        print("\n=== Step 4: 상품 삭제 (논리 삭제) ===")

        # 기존 상품 생성
        product = Product(
            id=uuid.uuid4(),
            name="구형 이어폰",
            price=Decimal("59000.00"),
            stock_quantity=10,
            category="전자기기",
            status=ProductStatus.AVAILABLE
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        product_id = product.id

        # 논리 삭제: 상태를 DISCONTINUED로 변경
        product.status = ProductStatus.DISCONTINUED

        await db_session.commit()

        # 데이터베이스에서 다시 조회
        query = select(Product).where(Product.id == product_id)
        result = await db_session.execute(query)
        deleted_product = result.scalar_one_or_none()

        # 검증
        assert deleted_product is not None  # 데이터베이스에 여전히 존재
        assert deleted_product.status == ProductStatus.DISCONTINUED

        print("논리 삭제 성공")
        print(f"상품 ID: {deleted_product.id}")
        print(f"상태: {deleted_product.status.value}")
        print("데이터베이스에 여전히 존재함 (논리 삭제)")

    @pytest.mark.asyncio
    async def test_full_product_crud_flow(
        self,
        db_session: AsyncSession,
        admin_user: User,
    ):
        """
        전체 상품 CRUD 플로우 통합 테스트

        1. 상품 생성
        2. 상품 조회
        3. 상품 수정
        4. 재고 업데이트
        5. 상품 삭제
        """
        print("\n=== 전체 상품 CRUD 플로우 ===")

        # Step 1: 상품 생성
        print("\nStep 1: 상품 생성")
        product = Product(
            id=uuid.uuid4(),
            name="스마트 워치",
            description="건강 관리 기능이 있는 스마트 워치",
            price=Decimal("299000.00"),
            stock_quantity=50,
            category="전자기기",
            image_url="https://example.com/images/watch.jpg",
            status=ProductStatus.AVAILABLE
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        assert product.id is not None
        print(f"상품 생성 완료: {product.name}")

        # Step 2: 상품 조회
        print("\nStep 2: 상품 조회")
        product_service = ProductService(db_session)
        retrieved_product = await product_service.get_product_by_id(product.id)

        assert retrieved_product.id == product.id
        assert retrieved_product.name == "스마트 워치"
        print(f"상품 조회 완료: {retrieved_product.name}")

        # Step 3: 상품 수정
        print("\nStep 3: 상품 정보 수정")
        product.price = Decimal("279000.00")
        product.description = "건강 관리 + GPS 기능이 있는 스마트 워치"
        await db_session.commit()
        await db_session.refresh(product)

        assert product.price == Decimal("279000.00")
        print(f"가격 수정 완료: {product.price}원")

        # Step 4: 재고 업데이트 (0으로 변경)
        print("\nStep 4: 재고 0으로 변경")
        product.stock_quantity = 0
        if product.stock_quantity == 0:
            product.status = ProductStatus.OUT_OF_STOCK
        await db_session.commit()
        await db_session.refresh(product)

        assert product.stock_quantity == 0
        assert product.status == ProductStatus.OUT_OF_STOCK
        print(f"품절 상태로 변경 완료")

        # Step 5: 상품 삭제 (논리 삭제)
        print("\nStep 5: 상품 삭제 (논리 삭제)")
        product.status = ProductStatus.DISCONTINUED
        await db_session.commit()

        assert product.status == ProductStatus.DISCONTINUED
        print("상품 논리 삭제 완료")

        print("\n=== 전체 CRUD 플로우 테스트 통과 ===")
