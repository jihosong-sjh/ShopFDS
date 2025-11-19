"""
리뷰 API Pydantic 스키마

리뷰 요청/응답 데이터 구조를 정의합니다.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class ReviewCreateRequest(BaseModel):
    """리뷰 작성 요청"""

    product_id: UUID = Field(..., description="상품 ID")
    order_id: Optional[UUID] = Field(None, description="주문 ID (선택)")
    rating: int = Field(..., ge=1, le=5, description="별점 (1-5)")
    title: Optional[str] = Field(None, max_length=200, description="리뷰 제목")
    content: str = Field(..., min_length=10, description="리뷰 내용 (최소 10자)")
    images: Optional[List[str]] = Field(default=[], description="이미지 URL 목록 (최대 3장)")

    @field_validator("images")
    @classmethod
    def validate_images(cls, v):
        if v and len(v) > 3:
            raise ValueError("이미지는 최대 3장까지 업로드할 수 있습니다")
        return v


class ReviewUpdateRequest(BaseModel):
    """리뷰 수정 요청"""

    rating: Optional[int] = Field(None, ge=1, le=5, description="별점 (1-5)")
    title: Optional[str] = Field(None, max_length=200, description="리뷰 제목")
    content: Optional[str] = Field(None, min_length=10, description="리뷰 내용")
    images: Optional[List[str]] = Field(None, description="이미지 URL 목록")

    @field_validator("images")
    @classmethod
    def validate_images(cls, v):
        if v and len(v) > 3:
            raise ValueError("이미지는 최대 3장까지 업로드할 수 있습니다")
        return v


class UserInfo(BaseModel):
    """리뷰 작성자 정보"""

    id: str
    name: str
    masked_name: str


class ReviewResponse(BaseModel):
    """리뷰 응답"""

    id: str
    user_id: str
    product_id: str
    order_id: Optional[str]
    rating: int
    title: Optional[str]
    content: str
    images: List[str]
    helpful_count: int
    is_verified_purchase: bool
    is_flagged: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    user: Optional[UserInfo] = None
    is_helpful_by_me: Optional[bool] = None


class ReviewListResponse(BaseModel):
    """리뷰 목록 응답"""

    reviews: List[ReviewResponse]
    total_count: int
    page: int
    total_pages: int
    average_rating: float
    rating_distribution: Dict[str, int]


class ReviewCreateResponse(BaseModel):
    """리뷰 작성 응답"""

    id: str
    message: str = "리뷰가 작성되었습니다"


class ReviewDeleteResponse(BaseModel):
    """리뷰 삭제 응답"""

    message: str = "리뷰가 삭제되었습니다"


class VoteResponse(BaseModel):
    """투표 응답"""

    message: str
    helpful_count: int
