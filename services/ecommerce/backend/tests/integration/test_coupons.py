"""
[OK] Integration Tests: Coupon API

Tests for coupon listing, issuing, and validation endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from uuid import uuid4
from decimal import Decimal

from src.models.user import User
from src.models.product import Product


@pytest.mark.asyncio
class TestCouponListing:
    """Coupon listing API integration tests"""

    async def test_get_user_coupons_empty(
        self, async_client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Test: Get user coupons returns empty list for new user"""
        # Given: New user with no coupons

        # When: Request user's coupons
        response = await async_client.get(
            "/v1/coupons/me",
            headers=auth_headers
        )

        # Then: Response is empty list
        assert response.status_code == 200
        data = response.json()
        assert "coupons" in data
        assert len(data["coupons"]) == 0

    async def test_get_user_coupons_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test: Get user coupons requires authentication"""
        # When: Request without auth headers
        response = await async_client.get("/v1/coupons/me")

        # Then: Unauthorized error
        assert response.status_code == 401


@pytest.mark.asyncio
class TestCouponIssuing:
    """Coupon issuing API integration tests"""

    async def test_issue_coupon_success(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: Successfully issue a valid coupon"""
        # Given: Active coupon in database
        from src.models.coupon import Coupon, DiscountType

        coupon = Coupon(
            id=uuid4(),
            coupon_code="WELCOME2025",
            coupon_name="신규 회원 환영 쿠폰",
            description="첫 구매 시 사용 가능",
            discount_type=DiscountType.PERCENT,
            discount_value=Decimal("10"),
            max_discount_amount=Decimal("10000"),
            min_purchase_amount=Decimal("50000"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=365),
            max_usage_count=1000,
            max_usage_per_user=1,
            current_usage_count=0,
            is_active=True
        )
        db_session.add(coupon)
        await db_session.commit()

        # When: Request to issue coupon
        response = await async_client.post(
            "/v1/coupons/issue",
            json={"coupon_code": "WELCOME2025"},
            headers=auth_headers
        )

        # Then: Coupon issued successfully
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "message" in data
        assert "쿠폰이 발급되었습니다" in data["message"]

    async def test_issue_coupon_nonexistent_code(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test: Cannot issue non-existent coupon"""
        # When: Request to issue non-existent coupon
        response = await async_client.post(
            "/v1/coupons/issue",
            json={"coupon_code": "INVALID999"},
            headers=auth_headers
        )

        # Then: Bad request error
        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "detail" in data

    async def test_issue_coupon_already_issued(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: Cannot issue coupon twice to same user"""
        # Given: Active coupon
        from src.models.coupon import Coupon, DiscountType
        from src.models.user_coupon import UserCoupon

        coupon = Coupon(
            id=uuid4(),
            coupon_code="ONCE2025",
            coupon_name="1회 한정 쿠폰",
            description="사용자당 1번만",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("5000"),
            min_purchase_amount=Decimal("30000"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            max_usage_per_user=1,
            is_active=True
        )
        db_session.add(coupon)
        await db_session.commit()
        await db_session.refresh(coupon)

        # And: User already has this coupon
        user_coupon = UserCoupon(
            id=uuid4(),
            user_id=test_user.id,
            coupon_id=coupon.id,
            issued_at=datetime.utcnow()
        )
        db_session.add(user_coupon)
        await db_session.commit()

        # When: Try to issue same coupon again
        response = await async_client.post(
            "/v1/coupons/issue",
            json={"coupon_code": "ONCE2025"},
            headers=auth_headers
        )

        # Then: Bad request - already issued
        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "detail" in data

    async def test_issue_coupon_expired(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: Cannot issue expired coupon"""
        # Given: Expired coupon
        from src.models.coupon import Coupon, DiscountType

        coupon = Coupon(
            id=uuid4(),
            coupon_code="EXPIRED2024",
            coupon_name="만료된 쿠폰",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("10000"),
            min_purchase_amount=Decimal("0"),
            valid_from=datetime.utcnow() - timedelta(days=60),
            valid_until=datetime.utcnow() - timedelta(days=1),  # Expired yesterday
            is_active=True
        )
        db_session.add(coupon)
        await db_session.commit()

        # When: Try to issue expired coupon
        response = await async_client.post(
            "/v1/coupons/issue",
            json={"coupon_code": "EXPIRED2024"},
            headers=auth_headers
        )

        # Then: Bad request - expired
        assert response.status_code == 400

    async def test_issue_coupon_usage_limit_exceeded(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: Cannot issue coupon when usage limit exceeded"""
        # Given: Coupon with max usage count reached
        from src.models.coupon import Coupon, DiscountType

        coupon = Coupon(
            id=uuid4(),
            coupon_code="LIMITED10",
            coupon_name="선착순 10명",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("5000"),
            min_purchase_amount=Decimal("0"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            max_usage_count=10,
            current_usage_count=10,  # Already reached limit
            is_active=True
        )
        db_session.add(coupon)
        await db_session.commit()

        # When: Try to issue coupon
        response = await async_client.post(
            "/v1/coupons/issue",
            json={"coupon_code": "LIMITED10"},
            headers=auth_headers
        )

        # Then: Bad request - usage limit exceeded
        assert response.status_code == 400


@pytest.mark.asyncio
class TestCouponValidation:
    """Coupon validation API integration tests"""

    async def test_validate_coupon_valid_percent_discount(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: Validate coupon with percent discount"""
        # Given: User has a 10% discount coupon (max 10,000 won)
        from src.models.coupon import Coupon, DiscountType
        from src.models.user_coupon import UserCoupon

        coupon = Coupon(
            id=uuid4(),
            coupon_code="PERCENT10",
            coupon_name="10% 할인",
            discount_type=DiscountType.PERCENT,
            discount_value=Decimal("10"),
            max_discount_amount=Decimal("10000"),
            min_purchase_amount=Decimal("50000"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            is_active=True
        )
        db_session.add(coupon)
        await db_session.commit()
        await db_session.refresh(coupon)

        user_coupon = UserCoupon(
            id=uuid4(),
            user_id=test_user.id,
            coupon_id=coupon.id,
            issued_at=datetime.utcnow()
        )
        db_session.add(user_coupon)
        await db_session.commit()

        # When: Validate coupon for 80,000 won order
        response = await async_client.post(
            "/v1/coupons/validate",
            json={
                "coupon_code": "PERCENT10",
                "order_amount": 80000
            },
            headers=auth_headers
        )

        # Then: Valid with 8,000 won discount (10% of 80,000)
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["discount_amount"] == 8000
        assert data["final_amount"] == 72000

    async def test_validate_coupon_valid_fixed_discount(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: Validate coupon with fixed discount"""
        # Given: User has a 5,000 won discount coupon
        from src.models.coupon import Coupon, DiscountType
        from src.models.user_coupon import UserCoupon

        coupon = Coupon(
            id=uuid4(),
            coupon_code="FIXED5000",
            coupon_name="5천원 할인",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("5000"),
            min_purchase_amount=Decimal("30000"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            is_active=True
        )
        db_session.add(coupon)
        await db_session.commit()
        await db_session.refresh(coupon)

        user_coupon = UserCoupon(
            id=uuid4(),
            user_id=test_user.id,
            coupon_id=coupon.id,
            issued_at=datetime.utcnow()
        )
        db_session.add(user_coupon)
        await db_session.commit()

        # When: Validate coupon for 50,000 won order
        response = await async_client.post(
            "/v1/coupons/validate",
            json={
                "coupon_code": "FIXED5000",
                "order_amount": 50000
            },
            headers=auth_headers
        )

        # Then: Valid with 5,000 won discount
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["discount_amount"] == 5000
        assert data["final_amount"] == 45000

    async def test_validate_coupon_below_minimum_purchase(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: Coupon invalid when order amount below minimum"""
        # Given: Coupon with 50,000 won minimum purchase
        from src.models.coupon import Coupon, DiscountType
        from src.models.user_coupon import UserCoupon

        coupon = Coupon(
            id=uuid4(),
            coupon_code="MIN50K",
            coupon_name="5만원 이상 구매시",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("5000"),
            min_purchase_amount=Decimal("50000"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            is_active=True
        )
        db_session.add(coupon)
        await db_session.commit()
        await db_session.refresh(coupon)

        user_coupon = UserCoupon(
            id=uuid4(),
            user_id=test_user.id,
            coupon_id=coupon.id,
            issued_at=datetime.utcnow()
        )
        db_session.add(user_coupon)
        await db_session.commit()

        # When: Validate coupon for 30,000 won order (below minimum)
        response = await async_client.post(
            "/v1/coupons/validate",
            json={
                "coupon_code": "MIN50K",
                "order_amount": 30000
            },
            headers=auth_headers
        )

        # Then: Invalid - below minimum purchase
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert "최소" in data["message"] or "minimum" in data["message"].lower()

    async def test_validate_coupon_percent_with_max_discount(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: Percent coupon discount capped at max amount"""
        # Given: 10% discount coupon with max 10,000 won
        from src.models.coupon import Coupon, DiscountType
        from src.models.user_coupon import UserCoupon

        coupon = Coupon(
            id=uuid4(),
            coupon_code="PERCENT10MAX",
            coupon_name="10% 할인 (최대 1만원)",
            discount_type=DiscountType.PERCENT,
            discount_value=Decimal("10"),
            max_discount_amount=Decimal("10000"),
            min_purchase_amount=Decimal("0"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            is_active=True
        )
        db_session.add(coupon)
        await db_session.commit()
        await db_session.refresh(coupon)

        user_coupon = UserCoupon(
            id=uuid4(),
            user_id=test_user.id,
            coupon_id=coupon.id,
            issued_at=datetime.utcnow()
        )
        db_session.add(user_coupon)
        await db_session.commit()

        # When: Validate coupon for 200,000 won order (10% would be 20,000)
        response = await async_client.post(
            "/v1/coupons/validate",
            json={
                "coupon_code": "PERCENT10MAX",
                "order_amount": 200000
            },
            headers=auth_headers
        )

        # Then: Discount capped at 10,000 won (not 20,000)
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["discount_amount"] == 10000  # Not 20,000
        assert data["final_amount"] == 190000

    async def test_validate_coupon_user_does_not_own(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: Cannot validate coupon user doesn't own"""
        # Given: Coupon exists but user doesn't have it
        from src.models.coupon import Coupon, DiscountType

        coupon = Coupon(
            id=uuid4(),
            coupon_code="NOTMINE",
            coupon_name="다른 사람 쿠폰",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("5000"),
            min_purchase_amount=Decimal("0"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            is_active=True
        )
        db_session.add(coupon)
        await db_session.commit()

        # When: Try to validate coupon
        response = await async_client.post(
            "/v1/coupons/validate",
            json={
                "coupon_code": "NOTMINE",
                "order_amount": 50000
            },
            headers=auth_headers
        )

        # Then: Invalid - user doesn't own coupon
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False

    async def test_validate_coupon_already_used(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: Cannot validate already used coupon"""
        # Given: User has coupon but already used it
        from src.models.coupon import Coupon, DiscountType
        from src.models.user_coupon import UserCoupon

        coupon = Coupon(
            id=uuid4(),
            coupon_code="USEDCOUPON",
            coupon_name="이미 사용한 쿠폰",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("5000"),
            min_purchase_amount=Decimal("0"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            is_active=True
        )
        db_session.add(coupon)
        await db_session.commit()
        await db_session.refresh(coupon)

        user_coupon = UserCoupon(
            id=uuid4(),
            user_id=test_user.id,
            coupon_id=coupon.id,
            issued_at=datetime.utcnow() - timedelta(days=5),
            used_at=datetime.utcnow() - timedelta(days=2)  # Already used
        )
        db_session.add(user_coupon)
        await db_session.commit()

        # When: Try to validate used coupon
        response = await async_client.post(
            "/v1/coupons/validate",
            json={
                "coupon_code": "USEDCOUPON",
                "order_amount": 50000
            },
            headers=auth_headers
        )

        # Then: Invalid - already used
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert "사용" in data["message"] or "used" in data["message"].lower()


@pytest.mark.asyncio
class TestCouponFiltering:
    """Test coupon list filtering by status"""

    async def test_filter_available_coupons(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: Filter coupons by 'available' status"""
        # Given: User has available and used coupons
        from src.models.coupon import Coupon, DiscountType
        from src.models.user_coupon import UserCoupon

        # Available coupon
        available_coupon = Coupon(
            id=uuid4(),
            coupon_code="AVAILABLE1",
            coupon_name="사용 가능한 쿠폰",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("5000"),
            min_purchase_amount=Decimal("0"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            is_active=True
        )
        db_session.add(available_coupon)

        # Used coupon
        used_coupon = Coupon(
            id=uuid4(),
            coupon_code="USED1",
            coupon_name="사용한 쿠폰",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("3000"),
            min_purchase_amount=Decimal("0"),
            valid_from=datetime.utcnow() - timedelta(days=10),
            valid_until=datetime.utcnow() + timedelta(days=20),
            is_active=True
        )
        db_session.add(used_coupon)
        await db_session.commit()
        await db_session.refresh(available_coupon)
        await db_session.refresh(used_coupon)

        # User coupons
        user_coupon_available = UserCoupon(
            id=uuid4(),
            user_id=test_user.id,
            coupon_id=available_coupon.id,
            issued_at=datetime.utcnow()
        )
        user_coupon_used = UserCoupon(
            id=uuid4(),
            user_id=test_user.id,
            coupon_id=used_coupon.id,
            issued_at=datetime.utcnow() - timedelta(days=5),
            used_at=datetime.utcnow() - timedelta(days=2)
        )
        db_session.add_all([user_coupon_available, user_coupon_used])
        await db_session.commit()

        # When: Request available coupons
        response = await async_client.get(
            "/v1/coupons/me",
            params={"status": "available"},
            headers=auth_headers
        )

        # Then: Only available coupons returned
        assert response.status_code == 200
        data = response.json()
        coupons = data["coupons"]
        assert len(coupons) >= 1
        assert all(c["used_at"] is None for c in coupons)
