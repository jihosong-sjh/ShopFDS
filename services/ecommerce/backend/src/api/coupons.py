"""
쿠폰 API 엔드포인트

쿠폰 조회, 발급, 검증 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.models.base import get_db
from src.models.user import User
from src.services.coupon_service import CouponService
from src.api.schemas.coupon_schemas import (
    CouponIssueRequest,
    CouponIssueResponse,
    CouponValidateRequest,
    CouponValidateResponse,
    UserCouponListResponse,
)
from src.middleware.auth import get_current_user

router = APIRouter(prefix="/v1/coupons", tags=["coupons"])


@router.get("/me", response_model=UserCouponListResponse)
async def get_user_coupons(
    status: Optional[str] = Query(
        None,
        description="필터 상태 (available: 사용 가능, used: 사용 완료, expired: 만료)",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    사용자 쿠폰 목록 조회

    **상태 필터**:
    - `available`: 사용 가능한 쿠폰만
    - `used`: 사용 완료한 쿠폰만
    - `expired`: 만료된 쿠폰만
    - 없음: 전체 쿠폰
    """
    service = CouponService(db)

    coupons = await service.get_user_coupons(
        user_id=current_user.id,
        status=status,
    )

    return {"coupons": coupons}


@router.post("/issue", response_model=CouponIssueResponse, status_code=status.HTTP_201_CREATED)
async def issue_coupon(
    request: CouponIssueRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    쿠폰 코드로 발급받기

    **오류 케이스**:
    - `400`: 존재하지 않는 쿠폰, 이미 발급받음, 사용 횟수 초과, 만료됨
    - `401`: 로그인 필요
    """
    service = CouponService(db)

    try:
        user_coupon = await service.issue_coupon(
            user_id=current_user.id,
            coupon_code=request.coupon_code,
        )

        return CouponIssueResponse(
            id=str(user_coupon.id),
            message="쿠폰이 발급되었습니다",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/validate", response_model=CouponValidateResponse)
async def validate_coupon(
    request: CouponValidateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    쿠폰 사용 가능 여부 확인

    주문 금액에 대해 쿠폰이 사용 가능한지 확인하고 할인 금액을 계산합니다.

    **응답**:
    - `is_valid`: 사용 가능 여부
    - `discount_amount`: 할인 금액
    - `final_amount`: 할인 후 최종 금액
    - `message`: 사용 불가능한 경우 사유
    """
    service = CouponService(db)

    result = await service.validate_coupon(
        user_id=current_user.id,
        coupon_code=request.coupon_code,
        order_amount=request.order_amount,
    )

    return CouponValidateResponse(**result)
