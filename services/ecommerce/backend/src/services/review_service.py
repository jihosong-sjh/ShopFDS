"""
리뷰 서비스

리뷰 작성, 수정, 삭제, 조회 및 투표 관련 비즈니스 로직을 처리합니다.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, or_
from sqlalchemy.orm import selectinload

from src.models.review import Review
from src.models.review_vote import ReviewVote
from src.models.user import User
from src.models.product import Product
from src.models.order import Order, OrderStatus
from src.utils.exceptions import ValidationException, NotFoundException


class ReviewService:
    """리뷰 관련 비즈니스 로직을 처리하는 서비스"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_review(
        self,
        user_id: UUID,
        product_id: UUID,
        rating: int,
        content: str,
        title: Optional[str] = None,
        images: Optional[List[str]] = None,
        order_id: Optional[UUID] = None,
    ) -> Review:
        """
        리뷰 생성

        Args:
            user_id: 사용자 ID
            product_id: 상품 ID
            rating: 별점 (1-5)
            content: 리뷰 내용 (최소 10자)
            title: 리뷰 제목 (선택)
            images: 이미지 URL 목록 (최대 3장)
            order_id: 주문 ID (선택)

        Returns:
            생성된 Review 객체

        Raises:
            ValidationException: 유효성 검증 실패 (중복 리뷰, 구매하지 않은 상품 등)
            NotFoundException: 상품이 존재하지 않음
        """
        # 1. 상품 존재 확인
        product = await self.db.get(Product, product_id)
        if not product:
            raise NotFoundException(f"상품을 찾을 수 없습니다: {product_id}")

        # 2. 중복 리뷰 확인 (사용자당 상품당 하나만)
        existing_review_stmt = select(Review).where(
            and_(Review.user_id == user_id, Review.product_id == product_id)
        )
        existing_review_result = await self.db.execute(existing_review_stmt)
        existing_review = existing_review_result.scalar_one_or_none()

        if existing_review:
            raise ValidationException("이미 해당 상품에 대한 리뷰를 작성하셨습니다")

        # 3. 구매 여부 확인 (구매 확정 상태 주문이 있어야 함)
        is_verified_purchase = False
        if order_id:
            # 특정 주문 ID가 제공된 경우 해당 주문 검증
            order = await self.db.get(Order, order_id)
            if not order:
                raise ValidationException(f"주문을 찾을 수 없습니다: {order_id}")

            if order.user_id != user_id:
                raise ValidationException("본인의 주문이 아닙니다")

            if order.status != OrderStatus.DELIVERED:
                raise ValidationException("배송 완료된 주문만 리뷰를 작성할 수 있습니다")

            # 주문에 해당 상품이 포함되어 있는지 확인
            order_with_items_stmt = (
                select(Order)
                .where(Order.id == order_id)
                .options(selectinload(Order.items))
            )
            order_with_items_result = await self.db.execute(order_with_items_stmt)
            order_with_items = order_with_items_result.scalar_one_or_none()

            product_in_order = any(
                item.product_id == product_id for item in order_with_items.items
            )

            if not product_in_order:
                raise ValidationException("해당 주문에 포함되지 않은 상품입니다")

            is_verified_purchase = True
        else:
            # order_id가 없으면 해당 사용자의 모든 배송 완료 주문에서 해당 상품이 있는지 확인
            orders_with_product_stmt = (
                select(Order)
                .join(Order.items)
                .where(
                    and_(
                        Order.user_id == user_id,
                        Order.status == OrderStatus.DELIVERED,
                        Order.items.any(product_id=product_id),
                    )
                )
            )
            orders_with_product_result = await self.db.execute(
                orders_with_product_stmt
            )
            orders_with_product = orders_with_product_result.scalars().all()

            if not orders_with_product:
                raise ValidationException("구매하지 않은 상품에는 리뷰를 작성할 수 없습니다")

            is_verified_purchase = True

        # 4. 유효성 검증
        if rating < 1 or rating > 5:
            raise ValidationException("별점은 1-5 사이여야 합니다")

        if len(content) < 10:
            raise ValidationException("리뷰 내용은 최소 10자 이상이어야 합니다")

        if images and len(images) > 3:
            raise ValidationException("이미지는 최대 3장까지 업로드할 수 있습니다")

        # 5. 리뷰 생성
        review = Review(
            user_id=user_id,
            product_id=product_id,
            order_id=order_id,
            rating=rating,
            title=title,
            content=content,
            images=images or [],
            is_verified_purchase=is_verified_purchase,
        )

        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)

        return review

    async def get_product_reviews(
        self,
        product_id: UUID,
        page: int = 1,
        limit: int = 10,
        sort: str = "recent",
        rating_filter: Optional[int] = None,
        has_images: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        상품 리뷰 목록 조회

        Args:
            product_id: 상품 ID
            page: 페이지 번호 (1부터 시작)
            limit: 페이지당 개수
            sort: 정렬 방식 (recent, helpful, rating_desc, rating_asc)
            rating_filter: 별점 필터 (1-5)
            has_images: 사진 리뷰만 보기

        Returns:
            리뷰 목록 및 통계 정보
        """
        # 기본 쿼리
        query = select(Review).where(Review.product_id == product_id)

        # 필터 적용
        if rating_filter:
            query = query.where(Review.rating == rating_filter)

        if has_images:
            # JSONB 배열 길이 확인 (PostgreSQL)
            query = query.where(func.jsonb_array_length(Review.images) > 0)

        # 정렬
        if sort == "helpful":
            query = query.order_by(Review.helpful_count.desc())
        elif sort == "rating_desc":
            query = query.order_by(Review.rating.desc())
        elif sort == "rating_asc":
            query = query.order_by(Review.rating.asc())
        else:  # recent (default)
            query = query.order_by(Review.created_at.desc())

        # 총 개수 조회
        count_query = select(func.count()).select_from(query.subquery())
        total_count_result = await self.db.execute(count_query)
        total_count = total_count_result.scalar()

        # 페이지네이션
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        # 리뷰 조회 (사용자 정보 포함)
        query = query.options(selectinload(Review.user))

        result = await self.db.execute(query)
        reviews = result.scalars().all()

        # 평균 별점 및 별점 분포 계산
        stats_query = select(
            func.avg(Review.rating).label("average_rating"),
            func.count(case((Review.rating == 5, 1))).label("rating_5"),
            func.count(case((Review.rating == 4, 1))).label("rating_4"),
            func.count(case((Review.rating == 3, 1))).label("rating_3"),
            func.count(case((Review.rating == 2, 1))).label("rating_2"),
            func.count(case((Review.rating == 1, 1))).label("rating_1"),
        ).where(Review.product_id == product_id)

        stats_result = await self.db.execute(stats_query)
        stats = stats_result.one()

        return {
            "reviews": [review.to_dict_with_user() for review in reviews],
            "total_count": total_count,
            "page": page,
            "total_pages": (total_count + limit - 1) // limit,
            "average_rating": float(stats.average_rating) if stats.average_rating else 0.0,
            "rating_distribution": {
                "5": stats.rating_5,
                "4": stats.rating_4,
                "3": stats.rating_3,
                "2": stats.rating_2,
                "1": stats.rating_1,
            },
        }

    async def update_review(
        self,
        review_id: UUID,
        user_id: UUID,
        rating: Optional[int] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        images: Optional[List[str]] = None,
    ) -> Review:
        """
        리뷰 수정 (작성자만 가능)

        Args:
            review_id: 리뷰 ID
            user_id: 사용자 ID
            rating: 새 별점 (선택)
            title: 새 제목 (선택)
            content: 새 내용 (선택)
            images: 새 이미지 목록 (선택)

        Returns:
            수정된 Review 객체

        Raises:
            NotFoundException: 리뷰를 찾을 수 없음
            ValidationException: 권한 없음 또는 유효성 검증 실패
        """
        review = await self.db.get(Review, review_id)
        if not review:
            raise NotFoundException(f"리뷰를 찾을 수 없습니다: {review_id}")

        if review.user_id != user_id:
            raise ValidationException("본인이 작성한 리뷰만 수정할 수 있습니다")

        # 필드 업데이트
        if rating is not None:
            if rating < 1 or rating > 5:
                raise ValidationException("별점은 1-5 사이여야 합니다")
            review.rating = rating

        if title is not None:
            review.title = title

        if content is not None:
            if len(content) < 10:
                raise ValidationException("리뷰 내용은 최소 10자 이상이어야 합니다")
            review.content = content

        if images is not None:
            if len(images) > 3:
                raise ValidationException("이미지는 최대 3장까지 업로드할 수 있습니다")
            review.images = images

        await self.db.commit()
        await self.db.refresh(review)

        return review

    async def delete_review(self, review_id: UUID, user_id: UUID) -> None:
        """
        리뷰 삭제 (작성자만 가능)

        Args:
            review_id: 리뷰 ID
            user_id: 사용자 ID

        Raises:
            NotFoundException: 리뷰를 찾을 수 없음
            ValidationException: 권한 없음
        """
        review = await self.db.get(Review, review_id)
        if not review:
            raise NotFoundException(f"리뷰를 찾을 수 없습니다: {review_id}")

        if review.user_id != user_id:
            raise ValidationException("본인이 작성한 리뷰만 삭제할 수 있습니다")

        await self.db.delete(review)
        await self.db.commit()

    async def vote_helpful(self, review_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        리뷰에 "도움돼요" 투표

        Args:
            review_id: 리뷰 ID
            user_id: 사용자 ID

        Returns:
            업데이트된 helpful_count

        Raises:
            NotFoundException: 리뷰를 찾을 수 없음
            ValidationException: 이미 투표함
        """
        review = await self.db.get(Review, review_id)
        if not review:
            raise NotFoundException(f"리뷰를 찾을 수 없습니다: {review_id}")

        # 중복 투표 확인
        existing_vote_stmt = select(ReviewVote).where(
            and_(ReviewVote.review_id == review_id, ReviewVote.user_id == user_id)
        )
        existing_vote_result = await self.db.execute(existing_vote_stmt)
        existing_vote = existing_vote_result.scalar_one_or_none()

        if existing_vote:
            raise ValidationException("이미 투표하셨습니다")

        # 투표 생성
        vote = ReviewVote(review_id=review_id, user_id=user_id)
        self.db.add(vote)

        # helpful_count 증가
        review.helpful_count += 1

        await self.db.commit()
        await self.db.refresh(review)

        return {
            "message": "투표가 완료되었습니다",
            "helpful_count": review.helpful_count,
        }

    async def cancel_vote(self, review_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        "도움돼요" 투표 취소

        Args:
            review_id: 리뷰 ID
            user_id: 사용자 ID

        Returns:
            업데이트된 helpful_count

        Raises:
            NotFoundException: 리뷰 또는 투표를 찾을 수 없음
        """
        review = await self.db.get(Review, review_id)
        if not review:
            raise NotFoundException(f"리뷰를 찾을 수 없습니다: {review_id}")

        # 투표 찾기
        vote_stmt = select(ReviewVote).where(
            and_(ReviewVote.review_id == review_id, ReviewVote.user_id == user_id)
        )
        vote_result = await self.db.execute(vote_stmt)
        vote = vote_result.scalar_one_or_none()

        if not vote:
            raise NotFoundException("투표를 찾을 수 없습니다")

        # 투표 삭제
        await self.db.delete(vote)

        # helpful_count 감소
        review.helpful_count = max(0, review.helpful_count - 1)

        await self.db.commit()
        await self.db.refresh(review)

        return {
            "message": "투표가 취소되었습니다",
            "helpful_count": review.helpful_count,
        }

    async def check_user_vote(self, review_id: UUID, user_id: UUID) -> bool:
        """
        사용자가 특정 리뷰에 투표했는지 확인

        Args:
            review_id: 리뷰 ID
            user_id: 사용자 ID

        Returns:
            투표 여부
        """
        vote_stmt = select(ReviewVote).where(
            and_(ReviewVote.review_id == review_id, ReviewVote.user_id == user_id)
        )
        vote_result = await self.db.execute(vote_stmt)
        vote = vote_result.scalar_one_or_none()

        return vote is not None
