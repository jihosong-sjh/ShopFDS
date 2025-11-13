"""
주문 API 엔드포인트

주문 생성, 조회, 추적 등 주문 관련 REST API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from models.order import OrderStatus
from services.order_service import OrderService
from utils.exceptions import ResourceNotFoundError, ValidationError, BusinessLogicError


router = APIRouter(prefix="/v1/orders", tags=["주문"])


# Request/Response 스키마

class PaymentInfoRequest(BaseModel):
    """결제 정보 (내부 필드는 토큰화됨)"""
    card_number: str = Field(..., description="카드 번호")
    card_expiry: str = Field(..., description="유효기간 (MM/YY)")
    card_cvv: str = Field(..., description="CVV")


class CreateOrderRequest(BaseModel):
    """주문 생성 요청"""
    shipping_name: str = Field(..., min_length=1, max_length=100, description="수령인 이름")
    shipping_address: str = Field(..., min_length=1, description="배송 주소")
    shipping_phone: str = Field(..., description="연락처")
    payment_info: PaymentInfoRequest

    class Config:
        json_schema_extra = {
            "example": {
                "shipping_name": "홍길동",
                "shipping_address": "서울특별시 강남구 테헤란로 123",
                "shipping_phone": "010-1234-5678",
                "payment_info": {
                    "card_number": "1234567890123456",
                    "card_expiry": "12/25",
                    "card_cvv": "123"
                }
            }
        }


class OrderItemResponse(BaseModel):
    """주문 항목 응답"""
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float


class OrderResponse(BaseModel):
    """주문 응답"""
    id: str
    order_number: str
    status: str
    total_amount: float
    shipping_name: str
    shipping_address: str
    shipping_phone: str
    created_at: str
    items: Optional[List[OrderItemResponse]] = None


class CreateOrderResponse(BaseModel):
    """주문 생성 응답"""
    order: OrderResponse
    fds_result: dict


# API 엔드포인트

@router.post("", response_model=CreateOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # JWT 인증
):
    """
    주문 생성

    장바구니의 상품으로 주문을 생성하고 결제를 처리합니다.
    FDS 평가를 거쳐 위험도에 따라 자동 승인/추가 인증/자동 차단됩니다.
    """
    # TODO: JWT 인증에서 user_id 가져오기
    user_id = "test-user-id"

    try:
        order_service = OrderService(db)

        order, fds_result = await order_service.create_order_from_cart(
            user_id=user_id,
            shipping_name=request.shipping_name,
            shipping_address=request.shipping_address,
            shipping_phone=request.shipping_phone,
            payment_info=request.payment_info.dict()
        )

        # 주문 항목 변환
        items = []
        for item in order.items:
            items.append(OrderItemResponse(
                product_id=str(item.product_id),
                product_name=item.product.name if item.product else "상품명 없음",
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                subtotal=item.get_subtotal()
            ))

        return CreateOrderResponse(
            order=OrderResponse(
                id=str(order.id),
                order_number=order.order_number,
                status=order.status,
                total_amount=float(order.total_amount),
                shipping_name=order.shipping_name,
                shipping_address=order.shipping_address,
                shipping_phone=order.shipping_phone,
                created_at=order.created_at.isoformat(),
                items=items
            ),
            fds_result=fds_result
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"주문 생성 중 오류 발생: {str(e)}"
        )


@router.get("", response_model=List[OrderResponse])
async def get_orders(
    status_filter: Optional[str] = Query(None, description="주문 상태 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # JWT 인증
):
    """
    주문 목록 조회

    현재 사용자의 주문 목록을 조회합니다.
    """
    # TODO: JWT 인증에서 user_id 가져오기
    user_id = "test-user-id"

    try:
        order_service = OrderService(db)

        # 상태 필터 변환
        status_enum = None
        if status_filter:
            try:
                status_enum = OrderStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"유효하지 않은 주문 상태: {status_filter}"
                )

        offset = (page - 1) * page_size
        orders = await order_service.get_user_orders(
            user_id=user_id,
            status=status_enum,
            limit=page_size,
            offset=offset
        )

        return [
            OrderResponse(
                id=str(order.id),
                order_number=order.order_number,
                status=order.status,
                total_amount=float(order.total_amount),
                shipping_name=order.shipping_name,
                shipping_address=order.shipping_address,
                shipping_phone=order.shipping_phone,
                created_at=order.created_at.isoformat(),
                items=None  # 목록에서는 항목 제외
            )
            for order in orders
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"주문 목록 조회 중 오류 발생: {str(e)}"
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # JWT 인증
):
    """
    주문 상세 조회

    지정한 주문의 상세 정보를 조회합니다.
    """
    # TODO: JWT 인증에서 user_id 가져오기
    user_id = "test-user-id"

    try:
        order_service = OrderService(db)
        order = await order_service.get_order_by_id(user_id=user_id, order_id=order_id)

        # 주문 항목 변환
        items = []
        for item in order.items:
            items.append(OrderItemResponse(
                product_id=str(item.product_id),
                product_name=item.product.name if item.product else "상품명 없음",
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                subtotal=item.get_subtotal()
            ))

        return OrderResponse(
            id=str(order.id),
            order_number=order.order_number,
            status=order.status,
            total_amount=float(order.total_amount),
            shipping_name=order.shipping_name,
            shipping_address=order.shipping_address,
            shipping_phone=order.shipping_phone,
            created_at=order.created_at.isoformat(),
            items=items
        )

    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"주문 조회 중 오류 발생: {str(e)}"
        )


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # JWT 인증
):
    """
    주문 취소

    지정한 주문을 취소합니다.
    """
    # TODO: JWT 인증에서 user_id 가져오기
    user_id = "test-user-id"

    try:
        order_service = OrderService(db)
        order = await order_service.cancel_order(user_id=user_id, order_id=order_id)

        return {
            "message": "주문이 취소되었습니다",
            "order_id": str(order.id),
            "status": order.status
        }

    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"주문 취소 중 오류 발생: {str(e)}"
        )


@router.get("/{order_id}/tracking")
async def track_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # JWT 인증
):
    """
    주문 추적

    주문의 배송 상태를 추적합니다.
    """
    # TODO: JWT 인증에서 user_id 가져오기
    user_id = "test-user-id"

    try:
        order_service = OrderService(db)
        tracking_info = await order_service.track_order(user_id=user_id, order_id=order_id)

        return tracking_info

    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"주문 추적 중 오류 발생: {str(e)}"
        )
