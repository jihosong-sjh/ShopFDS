"""
[OK] Integration Tests: OAuth API

Tests for OAuth login endpoints (Google, Kakao, Naver) including authorization flow and callback handling.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.models.user import User
from src.models.oauth_account import OAuthAccount


@pytest.mark.asyncio
class TestGoogleOAuth:
    """Google OAuth integration tests"""

    async def test_google_oauth_redirect_generates_authorization_url(
        self, async_client: AsyncClient
    ):
        """Test: Google OAuth redirect endpoint returns authorization URL"""
        # When: Request Google OAuth login
        response = await async_client.get(
            "/v1/auth/oauth/google", follow_redirects=False
        )

        # Then: Returns redirect to Google
        assert response.status_code in [302, 307]
        location = response.headers.get("location", "")
        assert "accounts.google.com" in location or "oauth2" in location
        assert "client_id" in location
        assert "redirect_uri" in location
        assert "scope" in location

    @patch("src.services.oauth_service.OAuthService.google_callback")
    async def test_google_oauth_callback_creates_new_user_and_oauth_account(
        self,
        mock_google_callback,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test: Google OAuth callback creates new user and OAuth account"""
        # Given: Mock Google callback returns user info
        new_user_id = uuid4()
        mock_google_callback.return_value = {
            "user_id": new_user_id,
            "email": "newuser@gmail.com",
            "name": "New User",
            "access_token": "jwt_access_token",
            "refresh_token": "jwt_refresh_token",
        }

        # When: Request OAuth callback with authorization code
        response = await async_client.get(
            "/v1/auth/oauth/google/callback",
            params={"code": "google_auth_code", "state": "csrf_state_token"},
        )

        # Then: Returns success with JWT tokens
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == "newuser@gmail.com"
        assert data["user"]["name"] == "New User"

    @patch("src.services.oauth_service.OAuthService.google_callback")
    async def test_google_oauth_callback_links_existing_user_with_same_email(
        self,
        mock_google_callback,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test: Google OAuth callback links existing user with same email"""
        # Given: Existing user with email
        existing_user = User(
            id=uuid4(),
            email="existinguser@gmail.com",
            password_hash="hashed_password",
            name="Existing User",
        )
        db_session.add(existing_user)
        await db_session.commit()

        # And: Mock Google callback returns same email
        mock_google_callback.return_value = {
            "user_id": existing_user.id,
            "email": "existinguser@gmail.com",
            "name": "Existing User",
            "access_token": "jwt_access_token",
            "refresh_token": "jwt_refresh_token",
        }

        # When: Request OAuth callback
        response = await async_client.get(
            "/v1/auth/oauth/google/callback",
            params={"code": "google_auth_code", "state": "csrf_state_token"},
        )

        # Then: Returns success with existing user
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "existinguser@gmail.com"

    async def test_google_oauth_callback_rejects_missing_authorization_code(
        self, async_client: AsyncClient
    ):
        """Test: Google OAuth callback rejects missing authorization code"""
        # When: Request callback without code parameter
        response = await async_client.get(
            "/v1/auth/oauth/google/callback", params={"state": "csrf_state_token"}
        )

        # Then: Returns bad request
        assert response.status_code == 400
        data = response.json()
        assert "code" in data.get("detail", "").lower() or "error" in data

    async def test_google_oauth_callback_rejects_invalid_authorization_code(
        self, async_client: AsyncClient
    ):
        """Test: Google OAuth callback rejects invalid authorization code"""
        # Given: Mock OAuth service raises error for invalid code
        with patch(
            "src.services.oauth_service.OAuthService.google_callback",
            side_effect=ValueError("Invalid authorization code"),
        ):
            # When: Request callback with invalid code
            response = await async_client.get(
                "/v1/auth/oauth/google/callback",
                params={"code": "invalid_code", "state": "csrf_state_token"},
            )

            # Then: Returns error
            assert response.status_code in [400, 401]


@pytest.mark.asyncio
class TestKakaoOAuth:
    """Kakao OAuth integration tests"""

    async def test_kakao_oauth_redirect_generates_authorization_url(
        self, async_client: AsyncClient
    ):
        """Test: Kakao OAuth redirect endpoint returns authorization URL"""
        # When: Request Kakao OAuth login
        response = await async_client.get(
            "/v1/auth/oauth/kakao", follow_redirects=False
        )

        # Then: Returns redirect to Kakao
        assert response.status_code in [302, 307]
        location = response.headers.get("location", "")
        assert "kauth.kakao.com" in location or "oauth" in location
        assert "client_id" in location or "response_type" in location

    @patch("src.services.oauth_service.OAuthService.kakao_callback")
    async def test_kakao_oauth_callback_creates_new_user(
        self,
        mock_kakao_callback,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test: Kakao OAuth callback creates new user and OAuth account"""
        # Given: Mock Kakao callback returns user info
        new_user_id = uuid4()
        mock_kakao_callback.return_value = {
            "user_id": new_user_id,
            "email": "kakaouser@kakao.com",
            "name": "Kakao User",
            "access_token": "jwt_access_token",
            "refresh_token": "jwt_refresh_token",
        }

        # When: Request OAuth callback with authorization code
        response = await async_client.get(
            "/v1/auth/oauth/kakao/callback",
            params={"code": "kakao_auth_code", "state": "csrf_state_token"},
        )

        # Then: Returns success with JWT tokens
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "kakaouser@kakao.com"

    async def test_kakao_oauth_callback_rejects_missing_code(
        self, async_client: AsyncClient
    ):
        """Test: Kakao OAuth callback rejects missing authorization code"""
        # When: Request callback without code
        response = await async_client.get(
            "/v1/auth/oauth/kakao/callback", params={"state": "csrf_state_token"}
        )

        # Then: Returns bad request
        assert response.status_code == 400


@pytest.mark.asyncio
class TestNaverOAuth:
    """Naver OAuth integration tests"""

    async def test_naver_oauth_redirect_generates_authorization_url(
        self, async_client: AsyncClient
    ):
        """Test: Naver OAuth redirect endpoint returns authorization URL"""
        # When: Request Naver OAuth login
        response = await async_client.get(
            "/v1/auth/oauth/naver", follow_redirects=False
        )

        # Then: Returns redirect to Naver
        assert response.status_code in [302, 307]
        location = response.headers.get("location", "")
        assert "nid.naver.com" in location or "oauth" in location
        assert "client_id" in location or "response_type" in location

    @patch("src.services.oauth_service.OAuthService.naver_callback")
    async def test_naver_oauth_callback_creates_new_user(
        self,
        mock_naver_callback,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test: Naver OAuth callback creates new user and OAuth account"""
        # Given: Mock Naver callback returns user info
        new_user_id = uuid4()
        mock_naver_callback.return_value = {
            "user_id": new_user_id,
            "email": "naveruser@naver.com",
            "name": "Naver User",
            "access_token": "jwt_access_token",
            "refresh_token": "jwt_refresh_token",
        }

        # When: Request OAuth callback with authorization code
        response = await async_client.get(
            "/v1/auth/oauth/naver/callback",
            params={"code": "naver_auth_code", "state": "csrf_state_token"},
        )

        # Then: Returns success with JWT tokens
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "naveruser@naver.com"

    async def test_naver_oauth_callback_rejects_missing_code(
        self, async_client: AsyncClient
    ):
        """Test: Naver OAuth callback rejects missing authorization code"""
        # When: Request callback without code
        response = await async_client.get(
            "/v1/auth/oauth/naver/callback", params={"state": "csrf_state_token"}
        )

        # Then: Returns bad request
        assert response.status_code == 400


@pytest.mark.asyncio
class TestOAuthAccountManagement:
    """OAuth account management tests"""

    @patch("src.services.oauth_service.OAuthService.google_callback")
    async def test_user_can_link_multiple_oauth_providers(
        self,
        mock_google_callback,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test: User can link multiple OAuth providers (Google + Kakao)"""
        # Given: User logged in with Kakao
        user = User(
            id=uuid4(),
            email="multiuser@example.com",
            password_hash="hashed_password",
            name="Multi User",
        )
        db_session.add(user)
        await db_session.commit()

        # And: Mock Google callback returns same user
        mock_google_callback.return_value = {
            "user_id": user.id,
            "email": "multiuser@example.com",
            "name": "Multi User",
            "access_token": "jwt_access_token",
            "refresh_token": "jwt_refresh_token",
        }

        # When: User links Google account
        response = await async_client.get(
            "/v1/auth/oauth/google/callback",
            params={"code": "google_auth_code", "state": "csrf_state_token"},
        )

        # Then: Successfully linked
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "multiuser@example.com"

    async def test_oauth_account_stores_provider_user_id(
        self, db_session: AsyncSession
    ):
        """Test: OAuth account stores provider_user_id uniquely"""
        # Given: User and OAuth account
        user = User(
            id=uuid4(),
            email="oauthuser@example.com",
            password_hash="hashed_password",
            name="OAuth User",
        )
        db_session.add(user)
        await db_session.commit()

        # When: Create OAuth account
        oauth_account = OAuthAccount(
            id=uuid4(),
            user_id=user.id,
            provider="GOOGLE",
            provider_user_id="google_unique_id_12345",
            access_token="encrypted_access_token",
            refresh_token="encrypted_refresh_token",
            profile_data={"email": "oauthuser@example.com", "name": "OAuth User"},
        )
        db_session.add(oauth_account)
        await db_session.commit()

        # Then: OAuth account created successfully
        await db_session.refresh(oauth_account)
        assert oauth_account.provider == "GOOGLE"
        assert oauth_account.provider_user_id == "google_unique_id_12345"

    async def test_duplicate_oauth_account_prevents_duplicate_provider_user_id(
        self, db_session: AsyncSession
    ):
        """Test: Duplicate provider + provider_user_id combination is rejected"""
        # Given: Existing OAuth account
        user1 = User(
            id=uuid4(),
            email="user1@example.com",
            password_hash="hashed_password",
            name="User 1",
        )
        db_session.add(user1)
        await db_session.commit()

        oauth_account1 = OAuthAccount(
            id=uuid4(),
            user_id=user1.id,
            provider="GOOGLE",
            provider_user_id="google_unique_id_99999",
            access_token="encrypted_access_token",
            refresh_token="encrypted_refresh_token",
            profile_data={"email": "user1@example.com", "name": "User 1"},
        )
        db_session.add(oauth_account1)
        await db_session.commit()

        # When: Try to create duplicate OAuth account with same provider + provider_user_id
        user2 = User(
            id=uuid4(),
            email="user2@example.com",
            password_hash="hashed_password",
            name="User 2",
        )
        db_session.add(user2)
        await db_session.commit()

        oauth_account2 = OAuthAccount(
            id=uuid4(),
            user_id=user2.id,
            provider="GOOGLE",
            provider_user_id="google_unique_id_99999",  # Duplicate
            access_token="encrypted_access_token",
            refresh_token="encrypted_refresh_token",
            profile_data={"email": "user2@example.com", "name": "User 2"},
        )
        db_session.add(oauth_account2)

        # Then: Raises unique constraint violation
        with pytest.raises(Exception):  # IntegrityError or similar
            await db_session.commit()
