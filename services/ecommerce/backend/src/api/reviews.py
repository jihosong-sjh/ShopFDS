"""
리뷰 API 엔드포인트

리뷰 작성, 조회, 수정, 삭제 및 투표 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from src.models.base import get_db
from src.models.user import User
from src.services.review_service import ReviewService
from src.api.schemas.review_schemas import (
    ReviewCreateRequest,
    ReviewUpdateRequest,
    ReviewCreateResponse,
    ReviewResponse,
    ReviewListResponse,
    ReviewDeleteResponse,
    VoteResponse,
)
from src.middleware.auth import get_current_user

router = APIRouter(prefix="/v1", tags=["reviews"])


@router.get("/products/{product_id}/reviews", response_model=ReviewListResponse)
async def get_product_reviews(
    product_id: UUID,
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(10, ge=1, le=100, description="페이지당 개수"),
    sort: str = Query(
        "recent", description="정렬 방식 (recent, helpful, rating_desc, rating_asc)"
    ),
    rating: Optional[int] = Query(None, ge=1, le=5, description="별점 필터 (1-5)"),
    has_images: Optional[bool] = Query(None, description="사진 리뷰만 보기"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    상품 리뷰 목록 조회

    정렬, 필터링, 페이지네이션 지원
    """
    service = ReviewService(db)

    result = await service.get_product_reviews(
        product_id=product_id,
        page=page,
        limit=limit,
        sort=sort,
        rating_filter=rating,
        has_images=has_images,
    )

    # 현재 사용자가 각 리뷰에 투표했는지 확인
    if current_user:
        for review in result["reviews"]:
            review_id = UUID(review["id"])
            is_voted = await service.check_user_vote(review_id, current_user.id)
            review["is_helpful_by_me"] = is_voted

    return result


@router.post(
    "/reviews", response_model=ReviewCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_review(
    request: ReviewCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    리뷰 작성

    구매 확정 고객만 작성 가능
    """
    service = ReviewService(db)

    review = await service.create_review(
        user_id=current_user.id,
        product_id=request.product_id,
        rating=request.rating,
        content=request.content,
        title=request.title,
        images=request.images,
        order_id=request.order_id,
    )

    return ReviewCreateResponse(id=str(review.id))


@router.put("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: UUID,
    request: ReviewUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    리뷰 수정

    작성자만 수정 가능
    """
    service = ReviewService(db)

    review = await service.update_review(
        review_id=review_id,
        user_id=current_user.id,
        rating=request.rating,
        title=request.title,
        content=request.content,
        images=request.images,
    )

    return review.to_dict_with_user()


@router.delete("/reviews/{review_id}", response_model=ReviewDeleteResponse)
async def delete_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    리뷰 삭제

    작성자만 삭제 가능
    """
    service = ReviewService(db)

    await service.delete_review(review_id=review_id, user_id=current_user.id)

    return ReviewDeleteResponse()


@router.post("/reviews/{review_id}/vote", response_model=VoteResponse)
async def vote_helpful(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    리뷰에 "도움돼요" 투표

    중복 투표 불가
    """
    service = ReviewService(db)

    result = await service.vote_helpful(review_id=review_id, user_id=current_user.id)

    return VoteResponse(**result)


@router.delete("/reviews/{review_id}/vote", response_model=VoteResponse)
async def cancel_vote(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    "도움돼요" 투표 취소
    """
    service = ReviewService(db)

    result = await service.cancel_vote(review_id=review_id, user_id=current_user.id)

    return VoteResponse(**result)
