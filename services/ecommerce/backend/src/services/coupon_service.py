"""
쿠폰 서비스

목적: 쿠폰 발급, 검증, 사용 로직 처리
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models.coupon import Coupon, DiscountType
from src.models.user_coupon import UserCoupon


class CouponService:
    """쿠폰 서비스"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_coupon_by_code(self, coupon_code: str) -> Optional[Coupon]:
        """
        쿠폰 코드로 쿠폰 조회

        Args:
            coupon_code: 쿠폰 코드

        Returns:
            쿠폰 또는 None
        """
        result = await self.db.execute(
            select(Coupon).where(Coupon.coupon_code == coupon_code)
        )
        return result.scalar_one_or_none()

    async def get_user_coupons(
        self,
        user_id: UUID,
        status: Optional[str] = None,
    ) -> List[dict]:
        """
        사용자 쿠폰 목록 조회

        Args:
            user_id: 사용자 ID
            status: 필터 상태 (available, used, expired)

        Returns:
            쿠폰 목록
        """
        query = (
            select(UserCoupon)
            .options(joinedload(UserCoupon.coupon))
            .where(UserCoupon.user_id == user_id)
        )

        # 상태 필터링
        if status == "available":
            query = query.where(UserCoupon.used_at.is_(None))
        elif status == "used":
            query = query.where(UserCoupon.used_at.isnot(None))

        result = await self.db.execute(query)
        user_coupons = result.scalars().all()

        # 쿠폰 정보 구성
        coupon_list = []
        for user_coupon in user_coupons:
            coupon = user_coupon.coupon

            # 만료 상태 필터링
            if status == "expired" and not coupon.is_expired():
                continue
            if status == "available" and coupon.is_expired():
                continue

            # 쿠폰 사용 가능 여부 확인
            is_usable = (
                user_coupon.is_available()
                and coupon.is_valid()
            )

            reason = ""
            if not is_usable:
                if user_coupon.is_used():
                    reason = "이미 사용한 쿠폰입니다"
                elif coupon.is_expired():
                    reason = "만료된 쿠폰입니다"
                elif not coupon.is_active:
                    reason = "비활성화된 쿠폰입니다"
                elif coupon.is_usage_limit_reached():
                    reason = "쿠폰 사용 횟수가 초과되었습니다"

            coupon_list.append({
                "id": str(user_coupon.id),
                "coupon_code": coupon.coupon_code,
                "coupon_name": coupon.coupon_name,
                "description": coupon.description,
                "discount_type": coupon.discount_type,
                "discount_value": float(coupon.discount_value),
                "max_discount_amount": (
                    float(coupon.max_discount_amount)
                    if coupon.max_discount_amount
                    else None
                ),
                "min_purchase_amount": float(coupon.min_purchase_amount),
                "valid_from": coupon.valid_from.isoformat(),
                "valid_until": coupon.valid_until.isoformat(),
                "issued_at": user_coupon.issued_at.isoformat(),
                "used_at": (
                    user_coupon.used_at.isoformat() if user_coupon.used_at else None
                ),
                "is_usable": is_usable,
                "reason": reason,
            })

        return coupon_list

    async def issue_coupon(self, user_id: UUID, coupon_code: str) -> UserCoupon:
        """
        사용자에게 쿠폰 발급

        Args:
            user_id: 사용자 ID
            coupon_code: 쿠폰 코드

        Returns:
            발급된 UserCoupon

        Raises:
            ValueError: 쿠폰이 없거나, 이미 발급받았거나, 발급 불가능한 경우
        """
        # 쿠폰 조회
        coupon = await self.get_coupon_by_code(coupon_code)
        if not coupon:
            raise ValueError("존재하지 않는 쿠폰 코드입니다")

        # 쿠폰 유효성 검증
        if not coupon.is_active:
            raise ValueError("비활성화된 쿠폰입니다")

        if coupon.is_expired():
            raise ValueError("만료된 쿠폰입니다")

        now = datetime.utcnow()
        if now < coupon.valid_from:
            raise ValueError("쿠폰 사용 기간이 아닙니다")

        if coupon.is_usage_limit_reached():
            raise ValueError("쿠폰 사용 횟수가 초과되었습니다")

        # 사용자별 발급 횟수 확인
        result = await self.db.execute(
            select(UserCoupon).where(
                and_(
                    UserCoupon.user_id == user_id,
                    UserCoupon.coupon_id == coupon.id,
                )
            )
        )
        existing_coupons = result.scalars().all()

        if len(existing_coupons) >= coupon.max_usage_per_user:
            raise ValueError(
                f"사용자당 최대 {coupon.max_usage_per_user}회까지 발급 가능합니다"
            )

        # 쿠폰 발급
        user_coupon = UserCoupon(
            user_id=user_id,
            coupon_id=coupon.id,
            issued_at=datetime.utcnow(),
        )

        self.db.add(user_coupon)
        await self.db.commit()
        await self.db.refresh(user_coupon)

        return user_coupon

    async def validate_coupon(
        self,
        user_id: UUID,
        coupon_code: str,
        order_amount: Decimal,
    ) -> dict:
        """
        쿠폰 사용 가능 여부 확인 및 할인 금액 계산

        Args:
            user_id: 사용자 ID
            coupon_code: 쿠폰 코드
            order_amount: 주문 금액

        Returns:
            검증 결과 (is_valid, discount_amount, final_amount, message)
        """
        # 쿠폰 조회
        coupon = await self.get_coupon_by_code(coupon_code)
        if not coupon:
            return {
                "is_valid": False,
                "discount_amount": 0,
                "final_amount": float(order_amount),
                "message": "존재하지 않는 쿠폰 코드입니다",
            }

        # 사용자가 보유한 쿠폰인지 확인
        result = await self.db.execute(
            select(UserCoupon).where(
                and_(
                    UserCoupon.user_id == user_id,
                    UserCoupon.coupon_id == coupon.id,
                )
            )
        )
        user_coupon = result.scalar_one_or_none()

        if not user_coupon:
            return {
                "is_valid": False,
                "discount_amount": 0,
                "final_amount": float(order_amount),
                "message": "보유하지 않은 쿠폰입니다",
            }

        # 이미 사용한 쿠폰인지 확인
        if user_coupon.is_used():
            return {
                "is_valid": False,
                "discount_amount": 0,
                "final_amount": float(order_amount),
                "message": "이미 사용한 쿠폰입니다",
            }

        # 쿠폰 적용 가능 여부 확인
        can_apply, reason = coupon.can_apply_to_order(order_amount)
        if not can_apply:
            return {
                "is_valid": False,
                "discount_amount": 0,
                "final_amount": float(order_amount),
                "message": reason,
            }

        # 할인 금액 계산
        discount_amount = coupon.calculate_discount(order_amount)
        final_amount = order_amount - discount_amount

        return {
            "is_valid": True,
            "discount_amount": float(discount_amount),
            "final_amount": float(final_amount),
            "message": "",
        }

    async def use_coupon(
        self,
        user_id: UUID,
        coupon_code: str,
        order_id: UUID,
    ) -> tuple[Decimal, UserCoupon]:
        """
        쿠폰 사용 (주문 생성 시 호출)

        Args:
            user_id: 사용자 ID
            coupon_code: 쿠폰 코드
            order_id: 주문 ID

        Returns:
            (할인 금액, UserCoupon)

        Raises:
            ValueError: 쿠폰 사용 불가능한 경우
        """
        # 쿠폰 조회
        coupon = await self.get_coupon_by_code(coupon_code)
        if not coupon:
            raise ValueError("존재하지 않는 쿠폰 코드입니다")

        # 사용자 쿠폰 조회
        result = await self.db.execute(
            select(UserCoupon).where(
                and_(
                    UserCoupon.user_id == user_id,
                    UserCoupon.coupon_id == coupon.id,
                    UserCoupon.used_at.is_(None),
                )
            )
        )
        user_coupon = result.scalar_one_or_none()

        if not user_coupon:
            raise ValueError("사용 가능한 쿠폰이 없습니다")

        # 쿠폰 사용 처리
        user_coupon.mark_as_used(order_id)
        coupon.increment_usage_count()

        await self.db.commit()
        await self.db.refresh(user_coupon)
        await self.db.refresh(coupon)

        return coupon.calculate_discount, user_coupon

    async def cancel_coupon_usage(
        self,
        user_coupon_id: UUID,
    ):
        """
        쿠폰 사용 취소 (주문 취소 시 호출)

        Args:
            user_coupon_id: UserCoupon ID
        """
        result = await self.db.execute(
            select(UserCoupon)
            .options(joinedload(UserCoupon.coupon))
            .where(UserCoupon.id == user_coupon_id)
        )
        user_coupon = result.scalar_one_or_none()

        if not user_coupon:
            return

        if user_coupon.is_used():
            # 쿠폰 복구
            user_coupon.restore()
            user_coupon.coupon.decrement_usage_count()

            await self.db.commit()
