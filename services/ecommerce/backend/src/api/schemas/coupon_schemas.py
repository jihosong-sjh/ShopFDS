"""
쿠폰 API 요청/응답 스키마
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal


class CouponIssueRequest(BaseModel):
    """쿠폰 발급 요청"""

    coupon_code: str = Field(..., description="쿠폰 코드", min_length=1, max_length=50)


class CouponIssueResponse(BaseModel):
    """쿠폰 발급 응답"""

    id: str = Field(..., description="발급된 UserCoupon ID")
    message: str = Field(..., description="응답 메시지")


class CouponValidateRequest(BaseModel):
    """쿠폰 검증 요청"""

    coupon_code: str = Field(..., description="쿠폰 코드")
    order_amount: Decimal = Field(..., description="주문 금액", gt=0)


class CouponValidateResponse(BaseModel):
    """쿠폰 검증 응답"""

    is_valid: bool = Field(..., description="쿠폰 사용 가능 여부")
    discount_amount: float = Field(..., description="할인 금액")
    final_amount: float = Field(..., description="할인 후 최종 금액")
    message: str = Field(default="", description="메시지 (불가능한 경우 사유)")


class UserCouponItem(BaseModel):
    """사용자 쿠폰 항목"""

    id: str = Field(..., description="UserCoupon ID")
    coupon_code: str = Field(..., description="쿠폰 코드")
    coupon_name: str = Field(..., description="쿠폰 이름")
    description: Optional[str] = Field(None, description="설명")
    discount_type: str = Field(..., description="할인 유형 (FIXED, PERCENT)")
    discount_value: float = Field(..., description="할인 값")
    max_discount_amount: Optional[float] = Field(None, description="최대 할인 금액 (정률 할인 시)")
    min_purchase_amount: float = Field(..., description="최소 구매 금액")
    valid_from: str = Field(..., description="사용 가능 시작일")
    valid_until: str = Field(..., description="사용 가능 종료일")
    issued_at: str = Field(..., description="발급일")
    used_at: Optional[str] = Field(None, description="사용일")
    is_usable: bool = Field(..., description="현재 사용 가능 여부")
    reason: str = Field(default="", description="사용 불가능한 경우 사유")


class UserCouponListResponse(BaseModel):
    """사용자 쿠폰 목록 응답"""

    coupons: List[UserCouponItem] = Field(..., description="쿠폰 목록")
