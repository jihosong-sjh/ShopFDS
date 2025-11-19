"""
Recommendations API Endpoints

추천 상품 API
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from src.database import get_db
from src.models.product import Product
from src.middleware.auth import get_current_user_optional
from src.models.user import User


router = APIRouter(prefix="/v1/recommendations", tags=["Recommendations"])


class ProductRecommendation(BaseModel):
    """추천 상품 응답"""

    id: str
    name: str
    price: int
    discounted_price: Optional[int]
    image_url: Optional[str]
    rating: float
    review_count: int


@router.get("/for-you")
async def get_recommendations_for_you(
    limit: int = Query(10, ge=1, le=50, description="추천 상품 개수"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    사용자 맞춤 추천 상품

    로그인 사용자: 협업 필터링 기반 추천 (향후 구현)
    비로그인 사용자: 인기 상품 추천
    """
    # TODO: 협업 필터링 알고리즘 구현
    # 현재는 인기 상품(재고 많은 순) 반환

    result = await db.execute(
        select(Product)
        .where(Product.stock > 0)
        .order_by(Product.stock.desc())
        .limit(limit)
    )
    products = result.scalars().all()

    recommendations = []
    for product in products:
        recommendations.append(
            {
                "id": str(product.id),
                "name": product.name,
                "price": product.price,
                "discounted_price": product.discounted_price,
                "image_url": product.images[0] if product.images else None,
                "rating": 0.0,  # TODO: 리뷰 평균 평점 계산
                "review_count": 0,  # TODO: 리뷰 개수 계산
            }
        )

    algorithm = "collaborative_filtering" if current_user else "popular"

    return {"products": recommendations, "algorithm": algorithm}


@router.get("/recently-viewed")
async def get_recently_viewed(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    최근 본 상품 조회

    프론트엔드 LocalStorage + 백엔드 동기화
    """
    # TODO: 백엔드에 최근 본 상품 저장 기능 구현
    # 현재는 빈 배열 반환

    return {"products": []}


@router.post("/recently-viewed")
async def save_recently_viewed(
    product_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    최근 본 상품 저장

    상품 조회 시 호출하여 최근 본 상품 목록에 추가합니다.
    """
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")

    # 상품 존재 여부 확인
    result = await db.execute(select(Product).where(Product.id == product_uuid))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")

    # TODO: 백엔드 최근 본 상품 저장 로직 구현
    # 현재는 성공 메시지만 반환

    return {"message": "최근 본 상품에 추가되었습니다"}


@router.get("/products/{product_id}/related")
async def get_related_products(
    product_id: str,
    limit: int = Query(10, ge=1, le=20, description="연관 상품 개수"),
    db: AsyncSession = Depends(get_db),
):
    """
    연관 상품 조회

    동일 카테고리의 다른 상품을 추천합니다.
    """
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")

    # 1. 현재 상품 조회
    result = await db.execute(select(Product).where(Product.id == product_uuid))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")

    # 2. 동일 카테고리 상품 조회 (현재 상품 제외)
    result = await db.execute(
        select(Product)
        .where(Product.category == product.category, Product.id != product_uuid)
        .order_by(func.random())  # 랜덤 정렬
        .limit(limit)
    )
    related_products = result.scalars().all()

    products = []
    for p in related_products:
        products.append(
            {
                "id": str(p.id),
                "name": p.name,
                "price": p.price,
                "discounted_price": p.discounted_price,
                "image_url": p.images[0] if p.images else None,
                "rating": 0.0,  # TODO: 리뷰 평균 평점 계산
                "review_count": 0,  # TODO: 리뷰 개수 계산
            }
        )

    return {"products": products, "category": product.category}
