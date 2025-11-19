"""
[OK] Integration Tests: Address Management API

Tests for address listing, creating, updating, deleting, and setting default addresses.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from src.models.user import User


@pytest.mark.asyncio
class TestAddressListing:
    """Address listing API integration tests"""

    async def test_get_addresses_empty(
        self, async_client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Test: Get addresses returns empty list for new user"""
        # Given: New user with no addresses

        # When: Request user's addresses
        response = await async_client.get(
            "/v1/addresses",
            headers=auth_headers
        )

        # Then: Response is empty list
        assert response.status_code == 200
        data = response.json()
        assert "addresses" in data
        assert len(data["addresses"]) == 0

    async def test_get_addresses_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test: Get addresses requires authentication"""
        # When: Request without auth headers
        response = await async_client.get("/v1/addresses")

        # Then: Forbidden error (HTTPBearer returns 403)
        assert response.status_code == 403


@pytest.mark.asyncio
class TestAddressCreation:
    """Address creation API integration tests"""

    async def test_create_address_success(
        self, async_client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Test: Successfully create a new address"""
        # Given: Valid address data
        address_data = {
            "address_name": "집",
            "recipient_name": "홍길동",
            "phone": "010-1234-5678",
            "zipcode": "06234",
            "address": "서울특별시 강남구 테헤란로 123",
            "address_detail": "456동 789호",
            "is_default": True
        }

        # When: Request to create address
        response = await async_client.post(
            "/v1/addresses",
            json=address_data,
            headers=auth_headers
        )

        # Then: Address created successfully
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["address_name"] == "집"
        assert data["recipient_name"] == "홍길동"
        assert data["phone"] == "010-1234-5678"
        assert data["zipcode"] == "06234"
        assert data["address"] == "서울특별시 강남구 테헤란로 123"
        assert data["address_detail"] == "456동 789호"
        assert data["is_default"] is True

    async def test_create_address_missing_required_fields(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test: Cannot create address without required fields"""
        # Given: Incomplete address data (missing recipient_name)
        address_data = {
            "address_name": "집",
            "phone": "010-1234-5678",
            "zipcode": "06234",
            "address": "서울특별시 강남구 테헤란로 123"
        }

        # When: Request to create address
        response = await async_client.post(
            "/v1/addresses",
            json=address_data,
            headers=auth_headers
        )

        # Then: Validation error
        assert response.status_code == 422

    async def test_create_multiple_addresses(
        self, async_client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Test: User can create multiple addresses"""
        # Given: Two different addresses
        address1 = {
            "address_name": "집",
            "recipient_name": "홍길동",
            "phone": "010-1234-5678",
            "zipcode": "06234",
            "address": "서울특별시 강남구 테헤란로 123",
            "is_default": True
        }
        address2 = {
            "address_name": "회사",
            "recipient_name": "홍길동",
            "phone": "010-1234-5678",
            "zipcode": "06345",
            "address": "서울특별시 강남구 역삼로 456",
            "is_default": False
        }

        # When: Create first address
        response1 = await async_client.post(
            "/v1/addresses",
            json=address1,
            headers=auth_headers
        )

        # Then: First address created successfully
        assert response1.status_code == 201
        data1 = response1.json()
        assert data1["is_default"] is True

        # When: Create second address
        response2 = await async_client.post(
            "/v1/addresses",
            json=address2,
            headers=auth_headers
        )

        # Then: Second address created successfully
        assert response2.status_code == 201
        data2 = response2.json()
        assert data2["is_default"] is False

        # Verify both addresses exist
        response = await async_client.get("/v1/addresses", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["addresses"]) == 2


@pytest.mark.asyncio
class TestAddressUpdate:
    """Address update API integration tests"""

    async def test_update_address_success(
        self, async_client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Test: Successfully update an existing address"""
        # Given: Existing address
        create_response = await async_client.post(
            "/v1/addresses",
            json={
                "address_name": "집",
                "recipient_name": "홍길동",
                "phone": "010-1234-5678",
                "zipcode": "06234",
                "address": "서울특별시 강남구 테헤란로 123",
                "is_default": True
            },
            headers=auth_headers
        )
        assert create_response.status_code == 201
        address_id = create_response.json()["id"]

        # When: Update address
        update_data = {
            "address_name": "새집",
            "recipient_name": "김철수",
            "phone": "010-9876-5432",
            "zipcode": "06345",
            "address": "서울특별시 강남구 역삼로 456",
            "address_detail": "101동 202호",
            "is_default": True
        }
        response = await async_client.put(
            f"/v1/addresses/{address_id}",
            json=update_data,
            headers=auth_headers
        )

        # Then: Address updated successfully
        assert response.status_code == 200
        data = response.json()
        assert data["address_name"] == "새집"
        assert data["recipient_name"] == "김철수"
        assert data["phone"] == "010-9876-5432"
        assert data["zipcode"] == "06345"
        assert data["address"] == "서울특별시 강남구 역삼로 456"
        assert data["address_detail"] == "101동 202호"

    async def test_update_nonexistent_address(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test: Cannot update non-existent address"""
        # Given: Non-existent address ID
        fake_id = str(uuid4())

        # When: Attempt to update
        response = await async_client.put(
            f"/v1/addresses/{fake_id}",
            json={
                "address_name": "집",
                "recipient_name": "홍길동",
                "phone": "010-1234-5678",
                "zipcode": "06234",
                "address": "서울특별시 강남구 테헤란로 123"
            },
            headers=auth_headers
        )

        # Then: Not found error
        assert response.status_code == 404


@pytest.mark.asyncio
class TestAddressDeletion:
    """Address deletion API integration tests"""

    async def test_delete_address_success(
        self, async_client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Test: Successfully delete an address"""
        # Given: Existing address
        create_response = await async_client.post(
            "/v1/addresses",
            json={
                "address_name": "임시 주소",
                "recipient_name": "홍길동",
                "phone": "010-1234-5678",
                "zipcode": "06234",
                "address": "서울특별시 강남구 테헤란로 123",
                "is_default": False
            },
            headers=auth_headers
        )
        assert create_response.status_code == 201
        address_id = create_response.json()["id"]

        # When: Delete address
        response = await async_client.delete(
            f"/v1/addresses/{address_id}",
            headers=auth_headers
        )

        # Then: Address deleted successfully
        assert response.status_code == 204

        # Verify address is deleted
        get_response = await async_client.get("/v1/addresses", headers=auth_headers)
        data = get_response.json()
        address_ids = [addr["id"] for addr in data["addresses"]]
        assert address_id not in address_ids

    async def test_delete_nonexistent_address(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test: Cannot delete non-existent address"""
        # Given: Non-existent address ID
        fake_id = str(uuid4())

        # When: Attempt to delete
        response = await async_client.delete(
            f"/v1/addresses/{fake_id}",
            headers=auth_headers
        )

        # Then: Not found error
        assert response.status_code == 404


@pytest.mark.asyncio
class TestDefaultAddress:
    """Default address management integration tests"""

    async def test_set_default_address_success(
        self, async_client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Test: Successfully set an address as default"""
        # Given: Two addresses, first one is default
        response1 = await async_client.post(
            "/v1/addresses",
            json={
                "address_name": "집",
                "recipient_name": "홍길동",
                "phone": "010-1234-5678",
                "zipcode": "06234",
                "address": "서울특별시 강남구 테헤란로 123",
                "is_default": True
            },
            headers=auth_headers
        )
        assert response1.status_code == 201
        address1_id = response1.json()["id"]

        response2 = await async_client.post(
            "/v1/addresses",
            json={
                "address_name": "회사",
                "recipient_name": "홍길동",
                "phone": "010-1234-5678",
                "zipcode": "06345",
                "address": "서울특별시 강남구 역삼로 456",
                "is_default": False
            },
            headers=auth_headers
        )
        assert response2.status_code == 201
        address2_id = response2.json()["id"]

        # When: Set second address as default
        response = await async_client.post(
            f"/v1/addresses/{address2_id}/set-default",
            headers=auth_headers
        )

        # Then: Second address is now default
        assert response.status_code == 200
        data = response.json()
        assert data["is_default"] is True

        # Verify first address is no longer default
        get_response = await async_client.get("/v1/addresses", headers=auth_headers)
        addresses = get_response.json()["addresses"]

        address1 = next(addr for addr in addresses if addr["id"] == address1_id)
        address2 = next(addr for addr in addresses if addr["id"] == address2_id)

        assert address1["is_default"] is False
        assert address2["is_default"] is True

    async def test_set_default_address_nonexistent(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test: Cannot set non-existent address as default"""
        # Given: Non-existent address ID
        fake_id = str(uuid4())

        # When: Attempt to set as default
        response = await async_client.post(
            f"/v1/addresses/{fake_id}/set-default",
            headers=auth_headers
        )

        # Then: Not found error
        assert response.status_code == 404

    async def test_only_one_default_address(
        self, async_client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Test: Only one address can be default at a time"""
        # Given: Three addresses created
        addresses = []
        for i, name in enumerate(["집", "회사", "친구집"]):
            response = await async_client.post(
                "/v1/addresses",
                json={
                    "address_name": name,
                    "recipient_name": "홍길동",
                    "phone": "010-1234-5678",
                    "zipcode": f"0634{i}",
                    "address": f"서울특별시 강남구 테헤란로 {100 + i * 100}",
                    "is_default": i == 0  # First one is default
                },
                headers=auth_headers
            )
            assert response.status_code == 201
            addresses.append(response.json()["id"])

        # When: Set third address as default
        response = await async_client.post(
            f"/v1/addresses/{addresses[2]}/set-default",
            headers=auth_headers
        )

        # Then: Only third address is default
        assert response.status_code == 200

        get_response = await async_client.get("/v1/addresses", headers=auth_headers)
        all_addresses = get_response.json()["addresses"]

        default_count = sum(1 for addr in all_addresses if addr["is_default"])
        assert default_count == 1

        default_address = next(addr for addr in all_addresses if addr["is_default"])
        assert default_address["id"] == addresses[2]
        assert default_address["address_name"] == "친구집"


@pytest.mark.asyncio
class TestAddressAccessControl:
    """Address access control integration tests"""

    async def test_cannot_access_other_users_addresses(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: User cannot access another user's addresses"""
        # Given: Another user with an address
        other_user = User(
            id=uuid4(),
            email="other@example.com",
            password_hash="hashed",
            name="다른 사용자"
        )
        db_session.add(other_user)
        await db_session.commit()

        # Create address for other user
        from src.models.address import Address
        other_address = Address(
            id=uuid4(),
            user_id=other_user.id,
            address_name="타인의 집",
            recipient_name="김철수",
            phone="010-9999-8888",
            zipcode="06789",
            address="서울특별시 강남구 선릉로 999",
            is_default=True
        )
        db_session.add(other_address)
        await db_session.commit()

        # When: Current user tries to update other user's address
        response = await async_client.put(
            f"/v1/addresses/{other_address.id}",
            json={
                "address_name": "해킹 시도",
                "recipient_name": "홍길동",
                "phone": "010-1234-5678",
                "zipcode": "06234",
                "address": "서울특별시 강남구 테헤란로 123"
            },
            headers=auth_headers
        )

        # Then: Forbidden or Not Found error
        assert response.status_code in [403, 404]

    async def test_cannot_delete_other_users_addresses(
        self, async_client: AsyncClient, db_session: AsyncSession,
        test_user: User, auth_headers: dict
    ):
        """Test: User cannot delete another user's addresses"""
        # Given: Another user with an address
        other_user = User(
            id=uuid4(),
            email="other2@example.com",
            password_hash="hashed",
            name="다른 사용자2"
        )
        db_session.add(other_user)
        await db_session.commit()

        from src.models.address import Address
        other_address = Address(
            id=uuid4(),
            user_id=other_user.id,
            address_name="타인의 회사",
            recipient_name="이영희",
            phone="010-8888-7777",
            zipcode="06789",
            address="서울특별시 강남구 역삼로 888",
            is_default=True
        )
        db_session.add(other_address)
        await db_session.commit()

        # When: Current user tries to delete other user's address
        response = await async_client.delete(
            f"/v1/addresses/{other_address.id}",
            headers=auth_headers
        )

        # Then: Forbidden or Not Found error
        assert response.status_code in [403, 404]


@pytest.mark.asyncio
class TestAddressValidation:
    """Address validation integration tests"""

    async def test_invalid_phone_number_format(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test: Reject invalid phone number format"""
        # Given: Address with invalid phone number
        address_data = {
            "address_name": "집",
            "recipient_name": "홍길동",
            "phone": "123",  # Invalid format
            "zipcode": "06234",
            "address": "서울특별시 강남구 테헤란로 123"
        }

        # When: Attempt to create address
        response = await async_client.post(
            "/v1/addresses",
            json=address_data,
            headers=auth_headers
        )

        # Then: Validation error
        assert response.status_code == 422

    async def test_empty_address_name(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test: Reject empty address name"""
        # Given: Address with empty name
        address_data = {
            "address_name": "",  # Empty
            "recipient_name": "홍길동",
            "phone": "010-1234-5678",
            "zipcode": "06234",
            "address": "서울특별시 강남구 테헤란로 123"
        }

        # When: Attempt to create address
        response = await async_client.post(
            "/v1/addresses",
            json=address_data,
            headers=auth_headers
        )

        # Then: Validation error
        assert response.status_code == 422

    async def test_address_name_too_long(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test: Reject address name exceeding max length"""
        # Given: Address with very long name
        address_data = {
            "address_name": "A" * 101,  # Exceeds 100 chars
            "recipient_name": "홍길동",
            "phone": "010-1234-5678",
            "zipcode": "06234",
            "address": "서울특별시 강남구 테헤란로 123"
        }

        # When: Attempt to create address
        response = await async_client.post(
            "/v1/addresses",
            json=address_data,
            headers=auth_headers
        )

        # Then: Validation error
        assert response.status_code == 422
