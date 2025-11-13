"""
장바구니 API 엔드포인트

장바구니 CRUD 관련 REST API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from services.cart_service import CartService
from utils.exceptions import ResourceNotFoundError, ValidationError


router = APIRouter(prefix="/v1/cart", tags=["장바구니"])


# Request/Response 스키마

class AddToCartRequest(BaseModel):
    """장바구니 추가 요청"""
    product_id: str
    quantity: int = Field(1, ge=1, description="수량")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "quantity": 2
            }
        }


class UpdateCartItemRequest(BaseModel):
    """장바구니 수량 변경 요청"""
    quantity: int = Field(..., ge=1, description="수량")


class CartItemResponse(BaseModel):
    """장바구니 항목 응답"""
    cart_item_id: str
    product_id: str
    product_name: str
    unit_price: float
    quantity: int
    subtotal: float
    image_url: Optional[str]
    is_available: bool


class CartSummaryResponse(BaseModel):
    """장바구니 요약 응답"""
    cart_id: str
    total_amount: float
    total_items: int
    items: List[CartItemResponse]


# API 엔드포인트

@router.get("", response_model=CartSummaryResponse)
async def get_cart(
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # JWT 인증
):
    """
    장바구니 조회

    현재 사용자의 장바구니 정보를 조회합니다.
    """
    # TODO: JWT 인증에서 user_id 가져오기
    # 임시로 테스트 user_id 사용
    user_id = "test-user-id"

    try:
        cart_service = CartService(db)
        cart_summary = await cart_service.get_cart_summary(user_id)

        return CartSummaryResponse(**cart_summary)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"장바구니 조회 중 오류 발생: {str(e)}"
        )


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    request: AddToCartRequest,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # JWT 인증
):
    """
    장바구니에 상품 추가

    지정한 상품을 장바구니에 추가합니다.
    이미 장바구니에 있는 상품이면 수량이 증가합니다.
    """
    # TODO: JWT 인증에서 user_id 가져오기
    user_id = "test-user-id"

    try:
        cart_service = CartService(db)
        cart_item = await cart_service.add_item(
            user_id=user_id,
            product_id=request.product_id,
            quantity=request.quantity
        )

        return {
            "message": "장바구니에 추가되었습니다",
            "cart_item_id": str(cart_item.id)
        }

    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"장바구니 추가 중 오류 발생: {str(e)}"
        )


@router.put("/items/{cart_item_id}")
async def update_cart_item(
    cart_item_id: str,
    request: UpdateCartItemRequest,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # JWT 인증
):
    """
    장바구니 항목 수량 변경

    지정한 장바구니 항목의 수량을 변경합니다.
    """
    # TODO: JWT 인증에서 user_id 가져오기
    user_id = "test-user-id"

    try:
        cart_service = CartService(db)
        cart_item = await cart_service.update_item_quantity(
            user_id=user_id,
            cart_item_id=cart_item_id,
            quantity=request.quantity
        )

        return {
            "message": "수량이 변경되었습니다",
            "cart_item_id": str(cart_item.id),
            "quantity": cart_item.quantity
        }

    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"수량 변경 중 오류 발생: {str(e)}"
        )


@router.delete("/items/{cart_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    cart_item_id: str,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # JWT 인증
):
    """
    장바구니 항목 삭제

    지정한 항목을 장바구니에서 삭제합니다.
    """
    # TODO: JWT 인증에서 user_id 가져오기
    user_id = "test-user-id"

    try:
        cart_service = CartService(db)
        await cart_service.remove_item(user_id=user_id, cart_item_id=cart_item_id)

        return None

    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"장바구니 항목 삭제 중 오류 발생: {str(e)}"
        )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # JWT 인증
):
    """
    장바구니 전체 비우기

    현재 사용자의 장바구니를 전부 비웁니다.
    """
    # TODO: JWT 인증에서 user_id 가져오기
    user_id = "test-user-id"

    try:
        cart_service = CartService(db)
        await cart_service.clear_cart(user_id=user_id)

        return None

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"장바구니 비우기 중 오류 발생: {str(e)}"
        )
