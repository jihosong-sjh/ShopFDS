"""
캐싱 기능이 통합된 상품 서비스 (성능 최적화 버전)

기존 ProductService에 Redis 캐싱을 추가하여 성능을 개선합니다.
상품 조회가 빈번한 경우 캐시를 활용하여 데이터베이스 부하를 줄입니다.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.sql import func
from redis import asyncio as aioredis

from src.models.product import Product, ProductStatus
from src.utils.exceptions import ResourceNotFoundError, ValidationError
from src.utils.cache_manager import CacheManager, CacheKeyBuilder
from src.utils.query_optimizer import monitor_query, QueryOptimizationHelper


class CachedProductService:
    """
    캐싱 기능이 통합된 상품 서비스

    주요 개선사항:
    1. 상품 상세 조회 시 Redis 캐시 활용
    2. 카테고리별 상품 목록 캐시
    3. 인기 상품 목록 캐시
    4. 상품 업데이트 시 캐시 무효화
    5. 쿼리 성능 모니터링
    """

    def __init__(self, db: AsyncSession, redis_client: Optional[aioredis.Redis] = None):
        """
        Args:
            db: 데이터베이스 세션
            redis_client: Redis 클라이언트 (None이면 캐싱 비활성화)
        """
        self.db = db
        self.cache_manager = CacheManager(redis_client) if redis_client else None

    @monitor_query("get_product_list")
    async def get_product_list(
        self,
        category: Optional[str] = None,
        search_query: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        status: Optional[ProductStatus] = None,
        limit: int = 20,
        offset: int = 0,
        use_cache: bool = True
    ) -> tuple[List[Product], int]:
        """
        상품 목록 조회 (캐싱 지원)

        Args:
            category: 카테고리 필터
            search_query: 검색어
            min_price: 최소 가격
            max_price: 최대 가격
            status: 상품 상태 필터
            limit: 조회 개수
            offset: 오프셋
            use_cache: 캐시 사용 여부

        Returns:
            (products, total_count): 상품 목록 및 전체 개수
        """
        # 캐시 확인 (검색어가 없고 캐시가 활성화된 경우)
        if use_cache and self.cache_manager and not search_query:
            cache_key = CacheKeyBuilder.product_list(
                category=category,
                min_price=min_price,
                max_price=max_price,
                limit=limit,
                offset=offset
            )

            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                # 캐시된 데이터를 Product 객체로 변환
                products = [self._dict_to_product(p) for p in cached_data["products"]]
                return products, cached_data["total_count"]

        # 데이터베이스 조회
        query = select(Product)
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
        products = list(result.scalars().all())

        # 캐시 저장 (검색어가 없는 경우만)
        if use_cache and self.cache_manager and not search_query and products:
            cache_data = {
                "products": [self._product_to_dict(p) for p in products],
                "total_count": total_count
            }
            await self.cache_manager.set(
                cache_key,
                cache_data,
                ttl=CacheManager.MEDIUM_TTL  # 10분 캐시
            )

        return products, total_count

    @monitor_query("get_product_by_id")
    async def get_product_by_id(
        self,
        product_id: str,
        use_cache: bool = True
    ) -> Product:
        """
        상품 ID로 상세 조회 (캐싱 지원)

        Args:
            product_id: 상품 ID
            use_cache: 캐시 사용 여부

        Returns:
            Product: 상품 객체

        Raises:
            ResourceNotFoundError: 상품을 찾을 수 없는 경우
        """
        # 캐시 확인
        if use_cache and self.cache_manager:
            cache_key = CacheKeyBuilder.product_detail(product_id)
            cached_data = await self.cache_manager.get(cache_key)

            if cached_data:
                return self._dict_to_product(cached_data)

        # 데이터베이스 조회
        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalars().first()

        if not product:
            raise ResourceNotFoundError(f"상품을 찾을 수 없습니다: {product_id}")

        # 캐시 저장
        if use_cache and self.cache_manager:
            cache_key = CacheKeyBuilder.product_detail(product_id)
            await self.cache_manager.set(
                cache_key,
                self._product_to_dict(product),
                ttl=CacheManager.LONG_TTL  # 1시간 캐시
            )

        return product

    @monitor_query("get_featured_products")
    async def get_featured_products(
        self,
        limit: int = 10,
        use_cache: bool = True
    ) -> List[Product]:
        """
        추천 상품 조회 (캐싱 지원)

        Args:
            limit: 최대 결과 개수
            use_cache: 캐시 사용 여부

        Returns:
            List[Product]: 추천 상품 목록
        """
        # 캐시 확인
        if use_cache and self.cache_manager:
            cache_key = f"product:featured:limit={limit}"
            cached_data = await self.cache_manager.get(cache_key)

            if cached_data:
                return [self._dict_to_product(p) for p in cached_data]

        # 데이터베이스 조회
        result = await self.db.execute(
            select(Product)
            .where(Product.status == ProductStatus.AVAILABLE)
            .where(Product.stock_quantity > 0)
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
        products = list(result.scalars().all())

        # 캐시 저장
        if use_cache and self.cache_manager and products:
            cache_key = f"product:featured:limit={limit}"
            await self.cache_manager.set(
                cache_key,
                [self._product_to_dict(p) for p in products],
                ttl=CacheManager.MEDIUM_TTL  # 10분 캐시
            )

        return products

    @monitor_query("get_categories")
    async def get_categories(self, use_cache: bool = True) -> List[str]:
        """
        전체 카테고리 목록 조회 (캐싱 지원)

        Args:
            use_cache: 캐시 사용 여부

        Returns:
            List[str]: 카테고리 목록
        """
        # 캐시 확인
        if use_cache and self.cache_manager:
            cache_key = "product:categories:all"
            cached_data = await self.cache_manager.get(cache_key)

            if cached_data:
                return cached_data

        # 데이터베이스 조회
        result = await self.db.execute(
            select(Product.category).distinct().order_by(Product.category)
        )
        categories = list(result.scalars().all())

        # 캐시 저장
        if use_cache and self.cache_manager and categories:
            cache_key = "product:categories:all"
            await self.cache_manager.set(
                cache_key,
                categories,
                ttl=CacheManager.VERY_LONG_TTL  # 24시간 캐시 (카테고리는 자주 변경되지 않음)
            )

        return categories

    # 관리자 전용 메서드 (캐시 무효화 포함)

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
        새 상품 등록 (캐시 무효화 포함)

        Args:
            name: 상품명
            price: 가격
            category: 카테고리
            stock_quantity: 초기 재고
            description: 상품 설명
            image_url: 이미지 URL

        Returns:
            Product: 생성된 상품 객체
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

        # 캐시 무효화
        await self._invalidate_product_caches(category)

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
        상품 정보 수정 (캐시 무효화 포함)

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
        product = await self.get_product_by_id(product_id, use_cache=False)
        old_category = product.category

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

        # 캐시 무효화 (상품 상세, 이전 카테고리, 새 카테고리)
        await self._invalidate_product_caches(old_category)
        if category and category != old_category:
            await self._invalidate_product_caches(category)

        if self.cache_manager:
            await self.cache_manager.delete(CacheKeyBuilder.product_detail(product_id))

        return product

    async def update_stock(self, product_id: str, quantity_delta: int) -> Product:
        """
        재고 수량 조정 (캐시 무효화 포함)

        Args:
            product_id: 상품 ID
            quantity_delta: 변경량

        Returns:
            Product: 수정된 상품 객체
        """
        product = await self.get_product_by_id(product_id, use_cache=False)

        try:
            product.update_stock(quantity_delta)
            await self.db.commit()
            await self.db.refresh(product)

            # 캐시 무효화
            if self.cache_manager:
                await self.cache_manager.delete(CacheKeyBuilder.product_detail(product_id))
                await self._invalidate_product_caches(product.category)

            return product
        except ValueError as e:
            raise ValidationError(str(e))

    async def discontinue_product(self, product_id: str) -> Product:
        """
        상품 판매 중단 (캐시 무효화 포함)

        Args:
            product_id: 상품 ID

        Returns:
            Product: 중단된 상품 객체
        """
        product = await self.get_product_by_id(product_id, use_cache=False)
        product.status = ProductStatus.DISCONTINUED

        await self.db.commit()
        await self.db.refresh(product)

        # 캐시 무효화
        await self._invalidate_product_caches(product.category)
        if self.cache_manager:
            await self.cache_manager.delete(CacheKeyBuilder.product_detail(product_id))

        return product

    # 헬퍼 메서드

    async def _invalidate_product_caches(self, category: Optional[str] = None):
        """
        상품 관련 캐시 무효화

        Args:
            category: 특정 카테고리 (None이면 모든 상품 캐시)
        """
        if not self.cache_manager:
            return

        # 카테고리별 목록 캐시 무효화
        if category:
            await self.cache_manager.delete_pattern(f"product:list:category={category}:*")

        # 추천 상품 캐시 무효화
        await self.cache_manager.delete_pattern("product:featured:*")

        # 전체 카테고리 목록 캐시 무효화
        await self.cache_manager.delete("product:categories:all")

    @staticmethod
    def _product_to_dict(product: Product) -> dict:
        """Product 객체를 dict로 변환 (캐싱용)"""
        return {
            "id": str(product.id),
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "category": product.category,
            "stock_quantity": product.stock_quantity,
            "status": product.status.value,
            "image_url": product.image_url,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None
        }

    @staticmethod
    def _dict_to_product(data: dict) -> Product:
        """dict를 Product 객체로 변환 (캐시에서 복원)"""
        from datetime import datetime
        from uuid import UUID

        product = Product(
            id=UUID(data["id"]),
            name=data["name"],
            description=data.get("description"),
            price=data["price"],
            category=data["category"],
            stock_quantity=data["stock_quantity"],
            status=ProductStatus(data["status"]),
            image_url=data.get("image_url")
        )

        if data.get("created_at"):
            product.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            product.updated_at = datetime.fromisoformat(data["updated_at"])

        return product
