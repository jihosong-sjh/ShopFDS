"""
OAuth API Endpoints

Google, Kakao, Naver 소셜 로그인 API
"""

import secrets
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.models.base import get_db
from src.services.oauth_service import OAuthService


router = APIRouter(prefix="/v1/auth/oauth", tags=["OAuth"])


class OAuthCallbackResponse(BaseModel):
    """OAuth 콜백 응답"""

    access_token: str
    refresh_token: str
    user: dict


# Google OAuth
@router.get("/google")
async def google_oauth_login(db: AsyncSession = Depends(get_db)):
    """
    Google OAuth 로그인 시작

    Google OAuth 인증 페이지로 리다이렉트합니다.
    """
    oauth_service = OAuthService(db)
    state = secrets.token_urlsafe(16)  # CSRF 방지 토큰 생성

    # TODO: state를 Redis 또는 세션에 저장하여 콜백에서 검증

    auth_url = await oauth_service.google_login_url(state)
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/google/callback", response_model=OAuthCallbackResponse)
async def google_oauth_callback(
    code: str = Query(..., description="Google authorization code"),
    state: str = Query(..., description="CSRF 방지 토큰"),
    db: AsyncSession = Depends(get_db),
):
    """
    Google OAuth 콜백

    Google OAuth 인증 후 콜백을 처리하고 JWT 토큰을 반환합니다.
    """
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is required")

    # TODO: state 검증 (Redis 또는 세션에서 확인)

    oauth_service = OAuthService(db)

    try:
        result = await oauth_service.google_callback(code, state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return OAuthCallbackResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user={
            "id": str(result["user_id"]),
            "email": result["email"],
            "name": result["name"],
        },
    )


# Kakao OAuth
@router.get("/kakao")
async def kakao_oauth_login(db: AsyncSession = Depends(get_db)):
    """
    Kakao OAuth 로그인 시작

    Kakao OAuth 인증 페이지로 리다이렉트합니다.
    """
    oauth_service = OAuthService(db)
    state = secrets.token_urlsafe(16)

    # TODO: state를 Redis 또는 세션에 저장하여 콜백에서 검증

    auth_url = await oauth_service.kakao_login_url(state)
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/kakao/callback", response_model=OAuthCallbackResponse)
async def kakao_oauth_callback(
    code: str = Query(..., description="Kakao authorization code"),
    state: str = Query(..., description="CSRF 방지 토큰"),
    db: AsyncSession = Depends(get_db),
):
    """
    Kakao OAuth 콜백

    Kakao OAuth 인증 후 콜백을 처리하고 JWT 토큰을 반환합니다.
    """
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is required")

    # TODO: state 검증

    oauth_service = OAuthService(db)

    try:
        result = await oauth_service.kakao_callback(code, state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return OAuthCallbackResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user={
            "id": str(result["user_id"]),
            "email": result["email"],
            "name": result["name"],
        },
    )


# Naver OAuth
@router.get("/naver")
async def naver_oauth_login(db: AsyncSession = Depends(get_db)):
    """
    Naver OAuth 로그인 시작

    Naver OAuth 인증 페이지로 리다이렉트합니다.
    """
    oauth_service = OAuthService(db)
    state = secrets.token_urlsafe(16)

    # TODO: state를 Redis 또는 세션에 저장하여 콜백에서 검증

    auth_url = await oauth_service.naver_login_url(state)
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/naver/callback", response_model=OAuthCallbackResponse)
async def naver_oauth_callback(
    code: str = Query(..., description="Naver authorization code"),
    state: str = Query(..., description="CSRF 방지 토큰"),
    db: AsyncSession = Depends(get_db),
):
    """
    Naver OAuth 콜백

    Naver OAuth 인증 후 콜백을 처리하고 JWT 토큰을 반환합니다.
    """
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is required")

    # TODO: state 검증

    oauth_service = OAuthService(db)

    try:
        result = await oauth_service.naver_callback(code, state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return OAuthCallbackResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user={
            "id": str(result["user_id"]),
            "email": result["email"],
            "name": result["name"],
        },
    )
