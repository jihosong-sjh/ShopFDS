"""
OAuth Service

Google, Kakao, Naver 소셜 로그인 처리 서비스
"""

import os
import uuid
import httpx
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.user import User
from src.models.oauth_account import OAuthAccount, OAuthProvider
from src.services.auth_service import AuthService


class OAuthService:
    """OAuth 소셜 로그인 서비스"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.auth_service = AuthService(db_session)

    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv(
        "GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/v1/auth/oauth/google/callback"
    )

    # Kakao OAuth
    KAKAO_CLIENT_ID = os.getenv("KAKAO_OAUTH_CLIENT_ID", "")
    KAKAO_CLIENT_SECRET = os.getenv("KAKAO_OAUTH_CLIENT_SECRET", "")
    KAKAO_REDIRECT_URI = os.getenv(
        "KAKAO_OAUTH_REDIRECT_URI", "http://localhost:8000/v1/auth/oauth/kakao/callback"
    )

    # Naver OAuth
    NAVER_CLIENT_ID = os.getenv("NAVER_OAUTH_CLIENT_ID", "")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_OAUTH_CLIENT_SECRET", "")
    NAVER_REDIRECT_URI = os.getenv(
        "NAVER_OAUTH_REDIRECT_URI", "http://localhost:8000/v1/auth/oauth/naver/callback"
    )

    async def google_login_url(self, state: str) -> str:
        """
        Google OAuth 로그인 URL 생성

        Args:
            state: CSRF 방지 토큰

        Returns:
            Google OAuth 인증 URL
        """
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={self.GOOGLE_CLIENT_ID}&"
            f"redirect_uri={self.GOOGLE_REDIRECT_URI}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile&"
            f"state={state}"
        )

    async def google_callback(self, code: str, state: str) -> Dict:
        """
        Google OAuth 콜백 처리

        Args:
            code: Google authorization code
            state: CSRF 방지 토큰 (검증 필요)

        Returns:
            사용자 정보 및 JWT 토큰
        """
        # 1. Authorization code로 access token 교환
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": self.GOOGLE_CLIENT_ID,
                    "client_secret": self.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": self.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )

            if token_response.status_code != 200:
                raise ValueError("Invalid authorization code")

            token_data = token_response.json()
            access_token = token_data["access_token"]

            # 2. Access token으로 사용자 프로필 조회
            profile_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if profile_response.status_code != 200:
                raise ValueError("Failed to fetch user profile")

            profile_data = profile_response.json()

        # 3. 사용자 생성 또는 연동
        user = await self._find_or_create_user_by_oauth(
            provider=OAuthProvider.GOOGLE,
            provider_user_id=profile_data["id"],
            email=profile_data["email"],
            name=profile_data.get("name", ""),
            profile_data=profile_data,
            access_token=access_token,
            refresh_token=token_data.get("refresh_token"),
        )

        # 4. JWT 토큰 생성
        jwt_access_token = self.auth_service.create_access_token(user.id)
        jwt_refresh_token = self.auth_service.create_refresh_token(user.id)

        return {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "access_token": jwt_access_token,
            "refresh_token": jwt_refresh_token,
        }

    async def kakao_login_url(self, state: str) -> str:
        """
        Kakao OAuth 로그인 URL 생성

        Args:
            state: CSRF 방지 토큰

        Returns:
            Kakao OAuth 인증 URL
        """
        return (
            f"https://kauth.kakao.com/oauth/authorize?"
            f"client_id={self.KAKAO_CLIENT_ID}&"
            f"redirect_uri={self.KAKAO_REDIRECT_URI}&"
            f"response_type=code&"
            f"state={state}"
        )

    async def kakao_callback(self, code: str, state: str) -> Dict:
        """
        Kakao OAuth 콜백 처리

        Args:
            code: Kakao authorization code
            state: CSRF 방지 토큰

        Returns:
            사용자 정보 및 JWT 토큰
        """
        # 1. Authorization code로 access token 교환
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://kauth.kakao.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.KAKAO_CLIENT_ID,
                    "client_secret": self.KAKAO_CLIENT_SECRET,
                    "redirect_uri": self.KAKAO_REDIRECT_URI,
                    "code": code,
                },
            )

            if token_response.status_code != 200:
                raise ValueError("Invalid authorization code")

            token_data = token_response.json()
            access_token = token_data["access_token"]

            # 2. Access token으로 사용자 프로필 조회
            profile_response = await client.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if profile_response.status_code != 200:
                raise ValueError("Failed to fetch user profile")

            profile_data = profile_response.json()

        # 3. 사용자 생성 또는 연동
        kakao_account = profile_data.get("kakao_account", {})
        email = kakao_account.get("email", f"kakao_{profile_data['id']}@kakao.local")
        name = kakao_account.get("profile", {}).get("nickname", "Kakao User")

        user = await self._find_or_create_user_by_oauth(
            provider=OAuthProvider.KAKAO,
            provider_user_id=str(profile_data["id"]),
            email=email,
            name=name,
            profile_data=profile_data,
            access_token=access_token,
            refresh_token=token_data.get("refresh_token"),
        )

        # 4. JWT 토큰 생성
        jwt_access_token = self.auth_service.create_access_token(user.id)
        jwt_refresh_token = self.auth_service.create_refresh_token(user.id)

        return {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "access_token": jwt_access_token,
            "refresh_token": jwt_refresh_token,
        }

    async def naver_login_url(self, state: str) -> str:
        """
        Naver OAuth 로그인 URL 생성

        Args:
            state: CSRF 방지 토큰

        Returns:
            Naver OAuth 인증 URL
        """
        return (
            f"https://nid.naver.com/oauth2.0/authorize?"
            f"response_type=code&"
            f"client_id={self.NAVER_CLIENT_ID}&"
            f"redirect_uri={self.NAVER_REDIRECT_URI}&"
            f"state={state}"
        )

    async def naver_callback(self, code: str, state: str) -> Dict:
        """
        Naver OAuth 콜백 처리

        Args:
            code: Naver authorization code
            state: CSRF 방지 토큰

        Returns:
            사용자 정보 및 JWT 토큰
        """
        # 1. Authorization code로 access token 교환
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://nid.naver.com/oauth2.0/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.NAVER_CLIENT_ID,
                    "client_secret": self.NAVER_CLIENT_SECRET,
                    "code": code,
                    "state": state,
                },
            )

            if token_response.status_code != 200:
                raise ValueError("Invalid authorization code")

            token_data = token_response.json()
            access_token = token_data["access_token"]

            # 2. Access token으로 사용자 프로필 조회
            profile_response = await client.get(
                "https://openapi.naver.com/v1/nid/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if profile_response.status_code != 200:
                raise ValueError("Failed to fetch user profile")

            profile_data = profile_response.json()

        # 3. 사용자 생성 또는 연동
        response = profile_data.get("response", {})
        email = response.get("email", f"naver_{response.get('id')}@naver.local")
        name = response.get("name", "Naver User")

        user = await self._find_or_create_user_by_oauth(
            provider=OAuthProvider.NAVER,
            provider_user_id=response.get("id"),
            email=email,
            name=name,
            profile_data=profile_data,
            access_token=access_token,
            refresh_token=token_data.get("refresh_token"),
        )

        # 4. JWT 토큰 생성
        jwt_access_token = self.auth_service.create_access_token(user.id)
        jwt_refresh_token = self.auth_service.create_refresh_token(user.id)

        return {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "access_token": jwt_access_token,
            "refresh_token": jwt_refresh_token,
        }

    async def _find_or_create_user_by_oauth(
        self,
        provider: OAuthProvider,
        provider_user_id: str,
        email: str,
        name: str,
        profile_data: Dict,
        access_token: str,
        refresh_token: Optional[str] = None,
    ) -> User:
        """
        OAuth 계정으로 사용자 찾기 또는 생성

        1. provider + provider_user_id로 기존 OAuth 계정 찾기
        2. 있으면 연동된 사용자 반환
        3. 없으면 이메일로 기존 사용자 찾기
        4. 사용자 없으면 신규 생성

        Args:
            provider: OAuth 제공자
            provider_user_id: OAuth 제공자의 사용자 고유 ID
            email: 이메일
            name: 이름
            profile_data: 프로필 데이터
            access_token: OAuth access token
            refresh_token: OAuth refresh token

        Returns:
            User 객체
        """
        # 1. 기존 OAuth 계정 찾기
        result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
        oauth_account = result.scalar_one_or_none()

        if oauth_account:
            # 기존 OAuth 계정 - 토큰 업데이트
            oauth_account.access_token = access_token
            oauth_account.refresh_token = refresh_token
            oauth_account.token_expires_at = datetime.utcnow() + timedelta(hours=1)
            oauth_account.profile_data = profile_data
            await self.db.commit()
            await self.db.refresh(oauth_account, ["user"])
            return oauth_account.user

        # 2. 이메일로 기존 사용자 찾기
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            # 3. 신규 사용자 생성
            user = User(
                id=uuid.uuid4(),
                email=email,
                password_hash="oauth_no_password",  # OAuth 사용자는 비밀번호 없음
                name=name,
            )
            self.db.add(user)
            await self.db.flush()

        # 4. OAuth 계정 연동
        new_oauth_account = OAuthAccount(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            profile_data=profile_data,
        )
        self.db.add(new_oauth_account)
        await self.db.commit()
        await self.db.refresh(user)

        return user
