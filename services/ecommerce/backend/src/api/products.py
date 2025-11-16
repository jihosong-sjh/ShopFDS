"""
상품 API 엔드포인트

상품 목록 조회, 검색, 상세 조회 등 상품 관련 REST API
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import get_db
from src.models.product import ProductStatus
from src.services.product_service import ProductService
from src.utils.exceptions import ResourceNotFoundError


router = APIRouter(prefix="/v1/products", tags=["상품"])


# Response 스키마


class ProductResponse(BaseModel):
    """상품 정보 응답"""

    id: str
    name: str
    description: Optional[str]
    price: float
    stock_quantity: int
    category: str
    image_url: Optional[str]
    status: str
    is_available: bool

    class Config:
        from_attributes = True

    @classmethod
    def from_product(cls, product):
        """Product 모델로부터 생성"""
        return cls(
            id=str(product.id),
            name=product.name,
            description=product.description,
            price=float(product.price),
            stock_quantity=product.stock_quantity,
            category=product.category,
            image_url=product.image_url,
            status=product.status,
            is_available=product.is_available(),
        )


class ProductListResponse(BaseModel):
    """상품 목록 응답"""

    products: List[ProductResponse]
    total_count: int
    page: int
    page_size: int


# API 엔드포인트


@router.get("", response_model=ProductListResponse)
async def get_products(
    category: Optional[str] = Query(None, description="카테고리 필터"),
    search: Optional[str] = Query(None, description="검색어 (상품명 또는 설명)"),
    min_price: Optional[float] = Query(None, ge=0, description="최소 가격"),
    max_price: Optional[float] = Query(None, ge=0, description="최대 가격"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db: AsyncSession = Depends(get_db),
):
    """
    상품 목록 조회

    필터링 및 페이지네이션을 지원하는 상품 목록 API입니다.
    """
    try:
        product_service = ProductService(db)

        offset = (page - 1) * page_size

        products, total_count = await product_service.get_product_list(
            category=category,
            search_query=search,
            min_price=min_price,
            max_price=max_price,
            status=ProductStatus.AVAILABLE,
            limit=page_size,
            offset=offset,
        )

        return ProductListResponse(
            products=[ProductResponse.from_product(p) for p in products],
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상품 목록 조회 중 오류 발생: {str(e)}",
        )


@router.get("/search", response_model=List[ProductResponse])
async def search_products(
    q: str = Query(..., min_length=1, description="검색어"),
    limit: int = Query(20, ge=1, le=100, description="최대 결과 개수"),
    db: AsyncSession = Depends(get_db),
):
    """
    상품 검색

    상품명 또는 설명에서 검색어를 찾습니다.
    """
    try:
        product_service = ProductService(db)
        products = await product_service.search_products(query=q, limit=limit)

        return [ProductResponse.from_product(p) for p in products]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상품 검색 중 오류 발생: {str(e)}",
        )


@router.get("/categories", response_model=List[str])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """
    카테고리 목록 조회

    전체 상품 카테고리 목록을 반환합니다.
    """
    try:
        product_service = ProductService(db)
        categories = await product_service.get_categories()

        return categories

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"카테고리 목록 조회 중 오류 발생: {str(e)}",
        )


@router.get("/featured", response_model=List[ProductResponse])
async def get_featured_products(
    limit: int = Query(10, ge=1, le=50, description="최대 결과 개수"),
    db: AsyncSession = Depends(get_db),
):
    """
    추천 상품 조회

    최신 상품 기준으로 추천 상품을 반환합니다.
    """
    try:
        product_service = ProductService(db)
        products = await product_service.get_featured_products(limit=limit)

        return [ProductResponse.from_product(p) for p in products]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"추천 상품 조회 중 오류 발생: {str(e)}",
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    """
    상품 상세 조회

    상품 ID로 상세 정보를 조회합니다.
    """
    try:
        product_service = ProductService(db)
        product = await product_service.get_product_by_id(product_id)

        return ProductResponse.from_product(product)

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상품 조회 중 오류 발생: {str(e)}",
        )
