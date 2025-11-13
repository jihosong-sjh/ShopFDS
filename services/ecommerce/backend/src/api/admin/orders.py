"""
관리자 주문 관리 API

관리자가 주문 목록을 조회하고 주문 상태를 관리할 수 있는 API 엔드포인트
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from decimal import Decimal

from src.models.order import Order, OrderStatus, OrderItem
from src.models.user import User
from src.models.base import get_db
from src.middleware.auth import get_current_user
from src.middleware.authorization import require_permission, Permission
from src.utils.exceptions import ResourceNotFoundError, ValidationError


router = APIRouter(prefix="/v1/admin/orders", tags=["Admin - Orders"])


# ===== Request/Response 스키마 =====

class OrderItemResponse(BaseModel):
    """주문 항목 응답"""
    id: str
    product_id: str
    quantity: int
    unit_price: Decimal

    class Config:
        from_attributes = True


class OrderListItemResponse(BaseModel):
    """주문 목록 항목 응답 (간소화된 정보)"""
    id: str
    order_number: str
    user_id: str
    user_email: str
    total_amount: Decimal
    status: str
    created_at: str
    paid_at: Optional[str]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "order_number": "ORD-20251114-123",
                "user_id": "650e8400-e29b-41d4-a716-446655440001",
                "user_email": "customer@example.com",
                "total_amount": "89000.00",
                "status": "paid",
                "created_at": "2025-11-14T10:00:00",
                "paid_at": "2025-11-14T10:05:00"
            }
        }


class OrderListResponse(BaseModel):
    """주문 목록 응답"""
    orders: List[OrderListItemResponse]
    total_count: int
    page: int
    page_size: int

    class Config:
        json_schema_extra = {
            "example": {
                "orders": [],
                "total_count": 100,
                "page": 1,
                "page_size": 20
            }
        }


class OrderDetailResponse(BaseModel):
    """주문 상세 응답"""
    id: str
    order_number: str
    user_id: str
    user_email: str
    total_amount: Decimal
    status: str
    shipping_name: str
    shipping_address: str
    shipping_phone: str
    items: List[OrderItemResponse]
    created_at: str
    paid_at: Optional[str]
    shipped_at: Optional[str]
    delivered_at: Optional[str]
    cancelled_at: Optional[str]

    class Config:
        from_attributes = True


class OrderStatusUpdateRequest(BaseModel):
    """주문 상태 수정 요청"""
    status: OrderStatus = Field(..., description="새로운 주문 상태")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "shipped"
            }
        }


class OrderStatusUpdateResponse(BaseModel):
    """주문 상태 수정 응답"""
    id: str
    order_number: str
    old_status: str
    new_status: str
    updated_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "order_number": "ORD-20251114-123",
                "old_status": "paid",
                "new_status": "shipped",
                "updated_at": "2025-11-14T12:00:00"
            }
        }


# ===== API 엔드포인트 =====

@router.get(
    "",
    response_model=OrderListResponse,
    summary="주문 목록 조회",
    description="관리자가 모든 주문 목록을 조회합니다 (필터링 및 페이지네이션 지원)."
)
async def get_orders(
    status: Optional[OrderStatus] = Query(None, description="주문 상태 필터"),
    user_email: Optional[str] = Query(None, description="사용자 이메일 검색"),
    order_number: Optional[str] = Query(None, description="주문 번호 검색"),
    start_date: Optional[datetime] = Query(None, description="시작 날짜 (ISO 8601 형식)"),
    end_date: Optional[datetime] = Query(None, description="종료 날짜 (ISO 8601 형식)"),
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기 (최대 100)"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission(Permission.ORDER_READ_ALL))
):
    """
    모든 주문 목록을 조회합니다.

    **필요 권한**: ORDER_READ_ALL

    **필터 옵션**:
    - status: 주문 상태 (pending, paid, preparing, shipped, delivered, cancelled, refunded)
    - user_email: 사용자 이메일 (부분 일치)
    - order_number: 주문 번호 (부분 일치)
    - start_date: 시작 날짜 (이 날짜 이후 생성된 주문)
    - end_date: 종료 날짜 (이 날짜 이전 생성된 주문)

    **페이지네이션**:
    - page: 페이지 번호 (기본값: 1)
    - page_size: 페이지 크기 (기본값: 20, 최대: 100)

    **반환**:
    - orders: 주문 목록
    - total_count: 전체 주문 개수
    - page: 현재 페이지
    - page_size: 페이지 크기
    """
    # 기본 쿼리 (User 테이블 조인)
    query = select(Order, User).join(User, Order.user_id == User.id)

    # 필터 적용
    filters = []

    if status:
        filters.append(Order.status == status)

    if user_email:
        filters.append(User.email.ilike(f"%{user_email}%"))

    if order_number:
        filters.append(Order.order_number.ilike(f"%{order_number}%"))

    if start_date:
        filters.append(Order.created_at >= start_date)

    if end_date:
        filters.append(Order.created_at <= end_date)

    if filters:
        query = query.where(and_(*filters))

    # 전체 개수 조회
    count_query = select(func.count(Order.id)).select_from(Order).join(User, Order.user_id == User.id)
    if filters:
        count_query = count_query.where(and_(*filters))

    total_count_result = await db.execute(count_query)
    total_count = total_count_result.scalar()

    # 정렬 및 페이지네이션
    offset = (page - 1) * page_size
    query = query.order_by(Order.created_at.desc()).limit(page_size).offset(offset)

    # 실행
    result = await db.execute(query)
    rows = result.all()

    # 응답 생성
    orders = [
        OrderListItemResponse(
            id=str(order.id),
            order_number=order.order_number,
            user_id=str(order.user_id),
            user_email=user.email,
            total_amount=order.total_amount,
            status=order.status.value,
            created_at=order.created_at.isoformat(),
            paid_at=order.paid_at.isoformat() if order.paid_at else None
        )
        for order, user in rows
    ]

    return OrderListResponse(
        orders=orders,
        total_count=total_count,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{order_id}",
    response_model=OrderDetailResponse,
    summary="주문 상세 조회",
    description="관리자가 특정 주문의 상세 정보를 조회합니다."
)
async def get_order_detail(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission(Permission.ORDER_READ_ALL))
):
    """
    특정 주문의 상세 정보를 조회합니다.

    **필요 권한**: ORDER_READ_ALL

    **반환**:
    - 주문 상세 정보 (배송 정보, 주문 항목 포함)

    **에러**:
    - 404: 주문을 찾을 수 없음
    """
    # 주문 조회 (User, OrderItem 조인)
    query = select(Order, User).join(User, Order.user_id == User.id).where(Order.id == order_id)
    result = await db.execute(query)
    row = result.first()

    if not row:
        raise ResourceNotFoundError(detail=f"주문을 찾을 수 없습니다: {order_id}")

    order, user = row

    # 주문 항목 조회
    items_query = select(OrderItem).where(OrderItem.order_id == order.id)
    items_result = await db.execute(items_query)
    items = items_result.scalars().all()

    return OrderDetailResponse(
        id=str(order.id),
        order_number=order.order_number,
        user_id=str(order.user_id),
        user_email=user.email,
        total_amount=order.total_amount,
        status=order.status.value,
        shipping_name=order.shipping_name,
        shipping_address=order.shipping_address,
        shipping_phone=order.shipping_phone,
        items=[
            OrderItemResponse(
                id=str(item.id),
                product_id=str(item.product_id),
                quantity=item.quantity,
                unit_price=item.unit_price
            )
            for item in items
        ],
        created_at=order.created_at.isoformat(),
        paid_at=order.paid_at.isoformat() if order.paid_at else None,
        shipped_at=order.shipped_at.isoformat() if order.shipped_at else None,
        delivered_at=order.delivered_at.isoformat() if order.delivered_at else None,
        cancelled_at=order.cancelled_at.isoformat() if order.cancelled_at else None
    )


@router.patch(
    "/{order_id}/status",
    response_model=OrderStatusUpdateResponse,
    summary="주문 상태 변경",
    description="관리자가 주문 상태를 변경합니다 (예: 배송 중, 배송 완료)."
)
async def update_order_status(
    order_id: str,
    request: OrderStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission(Permission.ORDER_UPDATE))
):
    """
    주문 상태를 변경합니다.

    **필요 권한**: ORDER_UPDATE

    **입력**:
    - status: 새로운 주문 상태

    **허용되는 상태 전환**:
    - pending → paid (결제 완료)
    - paid → preparing (배송 준비)
    - preparing → shipped (배송 시작)
    - shipped → delivered (배송 완료)
    - pending/paid/preparing → cancelled (주문 취소)
    - delivered → refunded (환불)

    **자동 타임스탬프**:
    - paid: paid_at 설정
    - shipped: shipped_at 설정
    - delivered: delivered_at 설정
    - cancelled: cancelled_at 설정

    **반환**:
    - 수정된 주문 정보

    **에러**:
    - 404: 주문을 찾을 수 없음
    - 400: 잘못된 상태 전환
    """
    # 주문 조회
    query = select(Order).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()

    if not order:
        raise ResourceNotFoundError(detail=f"주문을 찾을 수 없습니다: {order_id}")

    old_status = order.status
    new_status = request.status

    # 상태 전환 검증 및 타임스탬프 업데이트
    try:
        if new_status == OrderStatus.PAID:
            order.mark_as_paid()
        elif new_status == OrderStatus.PREPARING:
            if old_status not in [OrderStatus.PAID]:
                raise ValueError(f"'{old_status.value}' 상태에서 '{new_status.value}'로 변경할 수 없습니다.")
            order.status = OrderStatus.PREPARING
        elif new_status == OrderStatus.SHIPPED:
            order.mark_as_shipped()
        elif new_status == OrderStatus.DELIVERED:
            order.mark_as_delivered()
        elif new_status == OrderStatus.CANCELLED:
            order.cancel()
        elif new_status == OrderStatus.REFUNDED:
            if old_status != OrderStatus.DELIVERED:
                raise ValueError(f"'{old_status.value}' 상태에서 환불할 수 없습니다. 배송 완료 후에만 환불 가능합니다.")
            order.status = OrderStatus.REFUNDED
        else:
            raise ValueError(f"지원하지 않는 상태 전환: {old_status.value} → {new_status.value}")

    except ValueError as e:
        raise ValidationError(detail=str(e))

    await db.commit()
    await db.refresh(order)

    return OrderStatusUpdateResponse(
        id=str(order.id),
        order_number=order.order_number,
        old_status=old_status.value,
        new_status=order.status.value,
        updated_at=order.updated_at.isoformat()
    )
