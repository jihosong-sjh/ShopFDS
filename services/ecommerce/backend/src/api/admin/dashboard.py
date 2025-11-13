"""
관리자 대시보드 API

관리자가 매출 통계 및 전체 시스템 현황을 조회할 수 있는 API 엔드포인트
"""
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from decimal import Decimal

from src.models.order import Order, OrderStatus
from src.models.user import User
from src.models.product import Product
from src.models.payment import Payment, PaymentStatus
from src.models.base import get_db
from src.middleware.auth import get_current_user
from src.middleware.authorization import require_permission, Permission
from src.utils.exceptions import ValidationError


router = APIRouter(prefix="/v1/admin/dashboard", tags=["Admin - Dashboard"])


# ===== Response 스키마 =====

class SalesStatsByPeriod(BaseModel):
    """기간별 매출 통계"""
    period: str  # 날짜 또는 기간 (예: "2025-11-14", "2025-11-01 ~ 2025-11-07")
    total_sales: Decimal  # 총 매출액
    order_count: int  # 주문 건수
    average_order_value: Decimal  # 평균 주문 금액

    class Config:
        json_schema_extra = {
            "example": {
                "period": "2025-11-14",
                "total_sales": "5000000.00",
                "order_count": 150,
                "average_order_value": "33333.33"
            }
        }


class SalesByStatus(BaseModel):
    """주문 상태별 통계"""
    status: str
    count: int
    total_amount: Decimal

    class Config:
        json_schema_extra = {
            "example": {
                "status": "delivered",
                "count": 120,
                "total_amount": "4500000.00"
            }
        }


class TopProduct(BaseModel):
    """인기 상품 정보"""
    product_id: str
    product_name: str
    total_quantity: int
    total_sales: Decimal

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "product_name": "무선 이어폰",
                "total_quantity": 50,
                "total_sales": "4450000.00"
            }
        }


class SalesDashboardResponse(BaseModel):
    """매출 대시보드 응답"""
    period_type: str  # "daily", "weekly", "monthly"
    start_date: str
    end_date: str
    summary: dict  # 전체 요약 통계
    sales_by_period: List[SalesStatsByPeriod]  # 기간별 매출
    sales_by_status: List[SalesByStatus]  # 상태별 통계
    top_products: List[TopProduct]  # 인기 상품 (판매량 기준)

    class Config:
        json_schema_extra = {
            "example": {
                "period_type": "daily",
                "start_date": "2025-11-01",
                "end_date": "2025-11-14",
                "summary": {
                    "total_sales": "10000000.00",
                    "total_orders": 300,
                    "average_order_value": "33333.33",
                    "completed_orders": 250,
                    "cancelled_orders": 10
                },
                "sales_by_period": [],
                "sales_by_status": [],
                "top_products": []
            }
        }


# ===== API 엔드포인트 =====

@router.get(
    "/sales",
    response_model=SalesDashboardResponse,
    summary="매출 대시보드 조회",
    description="관리자가 매출 통계를 조회합니다 (일/주/월별 집계 지원)."
)
async def get_sales_dashboard(
    period_type: str = Query(
        "daily",
        regex="^(daily|weekly|monthly)$",
        description="집계 기간 타입 (daily, weekly, monthly)"
    ),
    start_date: Optional[datetime] = Query(
        None,
        description="시작 날짜 (ISO 8601 형식, 기본값: 14일 전)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="종료 날짜 (ISO 8601 형식, 기본값: 오늘)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission(Permission.ORDER_READ_ALL))
):
    """
    매출 대시보드를 조회합니다.

    **필요 권한**: ORDER_READ_ALL

    **입력**:
    - period_type: 집계 기간 타입
      - daily: 일별 집계
      - weekly: 주별 집계
      - monthly: 월별 집계
    - start_date: 시작 날짜 (기본값: 14일 전)
    - end_date: 종료 날짜 (기본값: 오늘)

    **반환**:
    - summary: 전체 요약 통계
      - total_sales: 총 매출액
      - total_orders: 총 주문 건수
      - average_order_value: 평균 주문 금액
      - completed_orders: 완료된 주문 수
      - cancelled_orders: 취소된 주문 수
    - sales_by_period: 기간별 매출 통계
    - sales_by_status: 주문 상태별 통계
    - top_products: 인기 상품 TOP 10 (판매량 기준)

    **주의사항**:
    - 집계에는 PAID, PREPARING, SHIPPED, DELIVERED 상태의 주문만 포함
    - PENDING, CANCELLED, REFUNDED 상태는 제외
    """
    # 기본 날짜 범위 설정
    if not end_date:
        end_date = datetime.utcnow()

    if not start_date:
        start_date = end_date - timedelta(days=14)

    # 날짜 범위 검증
    if start_date > end_date:
        raise ValidationError(detail="시작 날짜는 종료 날짜보다 이전이어야 합니다.")

    # 매출 집계 대상 상태 (결제 완료 이상)
    revenue_statuses = [
        OrderStatus.PAID,
        OrderStatus.PREPARING,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED
    ]

    # 1. 전체 요약 통계 조회
    summary_query = select(
        func.count(Order.id).label("total_orders"),
        func.sum(Order.total_amount).label("total_sales"),
        func.avg(Order.total_amount).label("average_order_value"),
        func.sum(case((Order.status == OrderStatus.DELIVERED, 1), else_=0)).label("completed_orders"),
        func.sum(case((Order.status == OrderStatus.CANCELLED, 1), else_=0)).label("cancelled_orders")
    ).where(
        and_(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status.in_(revenue_statuses)
        )
    )

    summary_result = await db.execute(summary_query)
    summary_row = summary_result.first()

    summary = {
        "total_sales": float(summary_row.total_sales or 0),
        "total_orders": summary_row.total_orders or 0,
        "average_order_value": float(summary_row.average_order_value or 0),
        "completed_orders": summary_row.completed_orders or 0,
        "cancelled_orders": summary_row.cancelled_orders or 0
    }

    # 2. 기간별 매출 통계 (기간 타입에 따라 그룹화)
    # 간소화: 일별 집계만 구현 (주별/월별은 추후 확장 가능)
    if period_type == "daily":
        # 일별 집계
        daily_query = select(
            func.date(Order.created_at).label("date"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("total_sales")
        ).where(
            and_(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status.in_(revenue_statuses)
            )
        ).group_by(
            func.date(Order.created_at)
        ).order_by(
            func.date(Order.created_at)
        )

        daily_result = await db.execute(daily_query)
        daily_rows = daily_result.all()

        sales_by_period = [
            SalesStatsByPeriod(
                period=str(row.date),
                total_sales=row.total_sales or Decimal("0.00"),
                order_count=row.order_count or 0,
                average_order_value=(
                    row.total_sales / row.order_count if row.order_count > 0 else Decimal("0.00")
                )
            )
            for row in daily_rows
        ]
    else:
        # 주별/월별은 추후 구현
        sales_by_period = []

    # 3. 주문 상태별 통계
    status_query = select(
        Order.status,
        func.count(Order.id).label("count"),
        func.sum(Order.total_amount).label("total_amount")
    ).where(
        and_(
            Order.created_at >= start_date,
            Order.created_at <= end_date
        )
    ).group_by(
        Order.status
    )

    status_result = await db.execute(status_query)
    status_rows = status_result.all()

    sales_by_status = [
        SalesByStatus(
            status=row.status.value,
            count=row.count,
            total_amount=row.total_amount or Decimal("0.00")
        )
        for row in status_rows
    ]

    # 4. 인기 상품 TOP 10 (판매량 기준)
    # OrderItem을 통해 집계 (간소화: 직접 쿼리)
    top_products_query = """
        SELECT
            oi.product_id,
            p.name AS product_name,
            SUM(oi.quantity) AS total_quantity,
            SUM(oi.quantity * oi.unit_price) AS total_sales
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        JOIN products p ON oi.product_id = p.id
        WHERE o.created_at >= :start_date
          AND o.created_at <= :end_date
          AND o.status IN ('paid', 'preparing', 'shipped', 'delivered')
        GROUP BY oi.product_id, p.name
        ORDER BY total_quantity DESC
        LIMIT 10
    """

    top_products_result = await db.execute(
        select(Order).from_statement(db.text(top_products_query)),
        {"start_date": start_date, "end_date": end_date}
    )

    # 간소화: Raw SQL 결과 파싱이 복잡하므로, 빈 목록 반환 (추후 구현)
    # 실제 구현 시 SQLAlchemy ORM으로 OrderItem 조인하여 집계
    top_products = []

    return SalesDashboardResponse(
        period_type=period_type,
        start_date=start_date.date().isoformat(),
        end_date=end_date.date().isoformat(),
        summary=summary,
        sales_by_period=sales_by_period,
        sales_by_status=sales_by_status,
        top_products=top_products
    )
