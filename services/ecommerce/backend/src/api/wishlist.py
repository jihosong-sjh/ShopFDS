"""
Wishlist API Endpoints

위시리스트 관리 API
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.models.base import get_db
from src.services.wishlist_service import WishlistService
from src.middleware.auth import get_current_user
from src.models.user import User


router = APIRouter(prefix="/v1/wishlist", tags=["Wishlist"])


class AddToWishlistRequest(BaseModel):
    """위시리스트 추가 요청"""

    product_id: str


class AddToWishlistResponse(BaseModel):
    """위시리스트 추가 응답"""

    id: str
    message: str


class MoveToCartRequest(BaseModel):
    """장바구니로 이동 요청"""

    item_ids: List[str]


class MoveToCartResponse(BaseModel):
    """장바구니로 이동 응답"""

    message: str
    success_count: int
    failed_items: List[dict]


@router.get("")
async def get_wishlist(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 개수"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    사용자 위시리스트 조회

    로그인한 사용자의 위시리스트 목록을 조회합니다.
    """
    wishlist_service = WishlistService(db)
    result = await wishlist_service.get_wishlist(
        user_id=current_user.id, page=page, limit=limit
    )

    return result


@router.post("", response_model=AddToWishlistResponse)
async def add_to_wishlist(
    request: AddToWishlistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    위시리스트에 상품 추가

    상품을 사용자의 위시리스트에 추가합니다.
    """
    try:
        product_id = uuid.UUID(request.product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")

    wishlist_service = WishlistService(db)

    try:
        wishlist_item = await wishlist_service.add_to_wishlist(
            user_id=current_user.id, product_id=product_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AddToWishlistResponse(
        id=str(wishlist_item.id), message="위시리스트에 추가되었습니다"
    )


@router.delete("/{item_id}")
async def remove_from_wishlist(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    위시리스트에서 상품 삭제

    위시리스트에서 특정 항목을 삭제합니다.
    """
    try:
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid item ID format")

    wishlist_service = WishlistService(db)

    try:
        await wishlist_service.remove_from_wishlist(
            user_id=current_user.id, item_id=item_uuid
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "위시리스트에서 삭제되었습니다"}


@router.post("/move-to-cart", response_model=MoveToCartResponse)
async def move_to_cart(
    request: MoveToCartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    위시리스트 상품을 장바구니로 이동

    선택한 위시리스트 항목을 장바구니로 일괄 이동합니다.
    """
    # UUID 변환
    try:
        item_ids = [uuid.UUID(item_id) for item_id in request.item_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid item ID format")

    wishlist_service = WishlistService(db)
    result = await wishlist_service.move_to_cart(
        user_id=current_user.id, item_ids=item_ids
    )

    success_count = result["success_count"]
    failed_count = len(result["failed_items"])

    message = f"{success_count}개 상품이 장바구니에 추가되었습니다"
    if failed_count > 0:
        message += f" ({failed_count}개 실패)"

    return MoveToCartResponse(
        message=message,
        success_count=success_count,
        failed_items=result["failed_items"],
    )
