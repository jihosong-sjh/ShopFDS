"""
Search Service: PostgreSQL Trigram Similarity Search

Provides product search with autocomplete, filtering, and sorting capabilities.
Uses PostgreSQL pg_trgm extension for fuzzy text matching.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, or_, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from uuid import UUID

from src.models.product import Product
from src.models.base import get_db


class SearchService:
    """Search service with PostgreSQL Trigram similarity"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def autocomplete(
        self, query: str, limit: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get autocomplete suggestions for search query.

        Returns:
        - Product suggestions (top matching products)
        - Brand suggestions (unique brands matching query)
        - Category suggestions (unique categories matching query)
        """
        if len(query) < 2:
            return {"suggestions": []}

        suggestions = []

        # 1. Product suggestions (top 5 products by similarity)
        product_suggestions = await self._get_product_suggestions(query, limit=5)
        suggestions.extend(product_suggestions)

        # 2. Brand suggestions (unique brands)
        brand_suggestions = await self._get_brand_suggestions(query, limit=3)
        suggestions.extend(brand_suggestions)

        # 3. Category suggestions (unique categories)
        category_suggestions = await self._get_category_suggestions(query, limit=2)
        suggestions.extend(category_suggestions)

        return {"suggestions": suggestions[:limit]}

    async def _get_product_suggestions(
        self, query: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Get product name suggestions using trigram similarity"""
        # PostgreSQL similarity function: similarity(name, query) > 0.3
        # Order by similarity DESC
        stmt = (
            select(Product)
            .where(
                or_(
                    func.lower(Product.name).contains(query.lower()),
                    func.similarity(Product.name, query) > 0.3,
                )
            )
            .order_by(desc(func.similarity(Product.name, query)))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        products = result.scalars().all()

        return [
            {
                "type": "product",
                "text": product.name,
                "product_id": str(product.id),
                "image_url": product.images[0] if product.images else None,
            }
            for product in products
        ]

    async def _get_brand_suggestions(
        self, query: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Get unique brand suggestions"""
        stmt = (
            select(Product.brand)
            .distinct()
            .where(func.lower(Product.brand).contains(query.lower()))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        brands = result.scalars().all()

        return [{"type": "brand", "text": brand} for brand in brands if brand]

    async def _get_category_suggestions(
        self, query: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Get unique category suggestions"""
        stmt = (
            select(Product.category)
            .distinct()
            .where(func.lower(Product.category).contains(query.lower()))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        categories = result.scalars().all()

        return [
            {"type": "category", "text": category}
            for category in categories
            if category
        ]

    async def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        in_stock: Optional[bool] = None,
        sort: str = "popular",
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Search products with filters and sorting.

        Args:
            query: Search query string
            category: Filter by category
            brand: Filter by brand
            min_price: Minimum price filter
            max_price: Maximum price filter
            in_stock: Show only in-stock products
            sort: Sort option (popular, price_asc, price_desc, newest, rating)
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Dict with products, total_count, page, total_pages, filters_applied
        """
        # Build WHERE conditions
        conditions = []

        # Text search: name, description, brand, category
        if query:
            conditions.append(
                or_(
                    func.lower(Product.name).contains(query.lower()),
                    func.lower(Product.description).contains(query.lower()),
                    func.lower(Product.brand).contains(query.lower()),
                    func.lower(Product.category).contains(query.lower()),
                    func.similarity(Product.name, query) > 0.2,
                )
            )

        # Filters
        if category:
            conditions.append(Product.category == category)

        if brand:
            conditions.append(Product.brand == brand)

        if min_price is not None:
            conditions.append(Product.price >= min_price)

        if max_price is not None:
            conditions.append(Product.price <= max_price)

        if in_stock:
            conditions.append(Product.stock > 0)

        # Count total matching products
        count_stmt = select(func.count(Product.id)).where(and_(*conditions))
        total_count_result = await self.db.execute(count_stmt)
        total_count = total_count_result.scalar() or 0

        # Build main query with sorting
        stmt = select(Product).where(and_(*conditions))

        # Apply sorting
        if sort == "price_asc":
            stmt = stmt.order_by(asc(Product.price))
        elif sort == "price_desc":
            stmt = stmt.order_by(desc(Product.price))
        elif sort == "newest":
            stmt = stmt.order_by(desc(Product.created_at))
        elif sort == "rating":
            # TODO: Add average rating from reviews (Phase 4)
            stmt = stmt.order_by(desc(Product.created_at))
        else:  # "popular" - default
            # TODO: Add popularity metric (view count, order count)
            stmt = stmt.order_by(desc(Product.created_at))

        # Pagination
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        # Execute query
        result = await self.db.execute(stmt)
        products = result.scalars().all()

        # Calculate total pages
        total_pages = (total_count + limit - 1) // limit  # Ceiling division

        return {
            "products": [self._product_to_dict(p) for p in products],
            "total_count": total_count,
            "page": page,
            "total_pages": total_pages,
            "filters_applied": {
                "query": query,
                "category": category,
                "brand": brand,
                "min_price": min_price,
                "max_price": max_price,
                "in_stock": in_stock,
            },
        }

    def _product_to_dict(self, product: Product) -> Dict[str, Any]:
        """Convert Product model to dictionary for API response"""
        return {
            "id": str(product.id),
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "discounted_price": (
                float(product.discounted_price) if product.discounted_price else None
            ),
            "images": product.images if product.images else [],
            "brand": product.brand,
            "category": product.category,
            "stock": product.stock,
            "in_stock": product.stock > 0,
            # TODO: Add rating and review_count from reviews (Phase 4)
            "rating": 0.0,
            "review_count": 0,
        }


async def get_search_service(db: AsyncSession = Depends(get_db)) -> SearchService:
    """Dependency injection for SearchService"""
    return SearchService(db)
