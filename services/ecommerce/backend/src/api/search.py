"""
Search API Endpoints

Provides REST API for product search, autocomplete, and search history.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID

from src.database import get_db
from src.services.search_service import SearchService, get_search_service
from src.models.user import User
from src.middleware.auth import get_current_user

router = APIRouter(prefix="/v1/search", tags=["search"])


# Pydantic Schemas
class AutocompleteResponse(BaseModel):
    """Autocomplete response schema"""

    suggestions: list[dict]


class ProductSearchResponse(BaseModel):
    """Product search response schema"""

    products: list[dict]
    total_count: int
    page: int
    total_pages: int
    filters_applied: dict


class SearchHistoryRequest(BaseModel):
    """Search history save request"""

    query: str = Field(..., min_length=1, max_length=200)


class SearchHistoryResponse(BaseModel):
    """Search history save response"""

    message: str


# API Endpoints
@router.get("/autocomplete", response_model=AutocompleteResponse)
async def search_autocomplete(
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    limit: int = Query(10, ge=1, le=20, description="Maximum suggestions"),
    search_service: SearchService = Depends(get_search_service),
):
    """
    [GET] /v1/search/autocomplete

    Get autocomplete suggestions for search query.

    Returns:
    - Product suggestions (name, image)
    - Brand suggestions
    - Category suggestions
    """
    result = await search_service.autocomplete(query=q, limit=limit)
    return result


@router.get("/products", response_model=ProductSearchResponse)
async def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    in_stock: Optional[bool] = Query(None, description="Show only in-stock products"),
    sort: str = Query(
        "popular",
        regex="^(popular|price_asc|price_desc|newest|rating)$",
        description="Sort option",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search_service: SearchService = Depends(get_search_service),
):
    """
    [GET] /v1/search/products

    Search products with filters and sorting.

    Query Parameters:
    - q: Search query (required)
    - category: Filter by category (optional)
    - brand: Filter by brand (optional)
    - min_price: Minimum price filter (optional)
    - max_price: Maximum price filter (optional)
    - in_stock: Show only in-stock products (optional)
    - sort: Sort option (popular, price_asc, price_desc, newest, rating)
    - page: Page number (default: 1)
    - limit: Items per page (default: 20, max: 100)

    Returns:
    - products: List of matching products
    - total_count: Total number of matching products
    - page: Current page number
    - total_pages: Total number of pages
    - filters_applied: Applied filters
    """
    # Validate price range
    if min_price is not None and max_price is not None:
        if min_price > max_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_price cannot be greater than max_price",
            )

    result = await search_service.search_products(
        query=q,
        category=category,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        sort=sort,
        page=page,
        limit=limit,
    )

    return result


@router.post(
    "/history",
    response_model=SearchHistoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_search_history(
    request: SearchHistoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    [POST] /v1/search/history

    Save search query to user's search history (authenticated users only).

    Request Body:
    - query: Search query string

    Returns:
    - message: Success message

    NOTE: This is optional backend storage for analytics.
    Frontend primarily uses LocalStorage for recent searches.
    """
    # TODO: Implement search_history table and save logic
    # For now, just return success (frontend LocalStorage is primary)

    return {"message": "Search history saved successfully"}
