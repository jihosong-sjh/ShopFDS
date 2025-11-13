"""
상품 서비스

상품 목록 조회, 검색, 상세 조회 등 상품 관련 비즈니스 로직
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.sql import func

from models.product import Product, ProductStatus
from utils.exceptions import ResourceNotFoundError, ValidationError


class ProductService:
    """상품 관련 비즈니스 로직"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_product_list(
        self,
        category: Optional[str] = None,
        search_query: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        status: Optional[ProductStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[Product], int]:
        """
        상품 목록 조회 (필터링 및 페이지네이션 지원)

        Args:
            category: 카테고리 필터
            search_query: 검색어 (상품명 또는 설명)
            min_price: 최소 가격
            max_price: 최대 가격
            status: 상품 상태 필터
            limit: 조회 개수
            offset: 오프셋

        Returns:
            (products, total_count): 상품 목록 및 전체 개수
        """
        # 기본 쿼리
        query = select(Product)

        # 필터 적용
        filters = []

        if category:
            filters.append(Product.category == category)

        if search_query:
            search_pattern = f"%{search_query}%"
            filters.append(
                or_(
                    Product.name.ilike(search_pattern),
                    Product.description.ilike(search_pattern)
                )
            )

        if min_price is not None:
            filters.append(Product.price >= min_price)

        if max_price is not None:
            filters.append(Product.price <= max_price)

        if status:
            filters.append(Product.status == status)
        else:
            # 기본적으로 중단되지 않은 상품만 표시
            filters.append(Product.status != ProductStatus.DISCONTINUED)

        if filters:
            query = query.where(and_(*filters))

        # 전체 개수 조회
        count_query = select(func.count()).select_from(Product)
        if filters:
            count_query = count_query.where(and_(*filters))

        total_count_result = await self.db.execute(count_query)
        total_count = total_count_result.scalar()

        # 정렬 및 페이지네이션
        query = query.order_by(Product.created_at.desc()).limit(limit).offset(offset)

        # 실행
        result = await self.db.execute(query)
        products = result.scalars().all()

        return list(products), total_count

    async def get_product_by_id(self, product_id: str) -> Product:
        """
        상품 ID로 상세 조회

        Args:
            product_id: 상품 ID (UUID 문자열)

        Returns:
            Product: 상품 객체

        Raises:
            ResourceNotFoundError: 상품을 찾을 수 없는 경우
        """
        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalars().first()

        if not product:
            raise ResourceNotFoundError(f"상품을 찾을 수 없습니다: {product_id}")

        return product

    async def search_products(self, query: str, limit: int = 20) -> List[Product]:
        """
        상품 검색 (간편 검색)

        Args:
            query: 검색어
            limit: 최대 결과 개수

        Returns:
            List[Product]: 검색된 상품 목록
        """
        products, _ = await self.get_product_list(
            search_query=query,
            limit=limit,
            offset=0
        )
        return products

    async def get_products_by_category(self, category: str, limit: int = 20) -> List[Product]:
        """
        카테고리별 상품 조회

        Args:
            category: 카테고리명
            limit: 최대 결과 개수

        Returns:
            List[Product]: 상품 목록
        """
        products, _ = await self.get_product_list(
            category=category,
            limit=limit,
            offset=0
        )
        return products

    async def check_stock_availability(self, product_id: str, quantity: int) -> bool:
        """
        재고 확인

        Args:
            product_id: 상품 ID
            quantity: 요청 수량

        Returns:
            bool: 재고 충분 여부

        Raises:
            ResourceNotFoundError: 상품을 찾을 수 없는 경우
        """
        product = await self.get_product_by_id(product_id)
        return product.can_purchase(quantity)

    async def get_categories(self) -> List[str]:
        """
        전체 카테고리 목록 조회

        Returns:
            List[str]: 카테고리 목록 (중복 제거)
        """
        result = await self.db.execute(
            select(Product.category).distinct().order_by(Product.category)
        )
        categories = result.scalars().all()
        return list(categories)

    async def get_featured_products(self, limit: int = 10) -> List[Product]:
        """
        추천 상품 조회 (최신 상품 기준)

        Args:
            limit: 최대 결과 개수

        Returns:
            List[Product]: 추천 상품 목록
        """
        result = await self.db.execute(
            select(Product)
            .where(Product.status == ProductStatus.AVAILABLE)
            .where(Product.stock_quantity > 0)
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
        products = result.scalars().all()
        return list(products)

    # 관리자 전용 메서드

    async def create_product(
        self,
        name: str,
        price: float,
        category: str,
        stock_quantity: int,
        description: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Product:
        """
        새 상품 등록 (관리자 전용)

        Args:
            name: 상품명
            price: 가격
            category: 카테고리
            stock_quantity: 초기 재고
            description: 상품 설명
            image_url: 이미지 URL

        Returns:
            Product: 생성된 상품 객체

        Raises:
            ValidationError: 입력 검증 실패
        """
        if price < 0:
            raise ValidationError("가격은 0 이상이어야 합니다")

        if stock_quantity < 0:
            raise ValidationError("재고 수량은 0 이상이어야 합니다")

        product = Product(
            name=name,
            price=price,
            category=category,
            stock_quantity=stock_quantity,
            description=description,
            image_url=image_url,
            status=ProductStatus.AVAILABLE if stock_quantity > 0 else ProductStatus.OUT_OF_STOCK
        )

        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)

        return product

    async def update_product(
        self,
        product_id: str,
        name: Optional[str] = None,
        price: Optional[float] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Product:
        """
        상품 정보 수정 (관리자 전용)

        Args:
            product_id: 상품 ID
            name: 상품명
            price: 가격
            category: 카테고리
            description: 설명
            image_url: 이미지 URL

        Returns:
            Product: 수정된 상품 객체
        """
        product = await self.get_product_by_id(product_id)

        if name:
            product.name = name
        if price is not None:
            if price < 0:
                raise ValidationError("가격은 0 이상이어야 합니다")
            product.price = price
        if category:
            product.category = category
        if description is not None:
            product.description = description
        if image_url is not None:
            product.image_url = image_url

        await self.db.commit()
        await self.db.refresh(product)

        return product

    async def update_stock(self, product_id: str, quantity_delta: int) -> Product:
        """
        재고 수량 조정 (관리자 전용)

        Args:
            product_id: 상품 ID
            quantity_delta: 변경량 (양수: 증가, 음수: 감소)

        Returns:
            Product: 수정된 상품 객체

        Raises:
            ValidationError: 재고 부족
        """
        product = await self.get_product_by_id(product_id)

        try:
            product.update_stock(quantity_delta)
            await self.db.commit()
            await self.db.refresh(product)
            return product
        except ValueError as e:
            raise ValidationError(str(e))

    async def discontinue_product(self, product_id: str) -> Product:
        """
        상품 판매 중단 (관리자 전용)

        Args:
            product_id: 상품 ID

        Returns:
            Product: 중단된 상품 객체
        """
        product = await self.get_product_by_id(product_id)
        product.status = ProductStatus.DISCONTINUED

        await self.db.commit()
        await self.db.refresh(product)

        return product
