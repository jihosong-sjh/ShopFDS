"""
인증 API 엔드포인트

회원가입, 로그인 등 인증 관련 REST API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import get_db
from src.models.user import UserRole
from src.services.user_service import UserService
from src.utils.exceptions import AuthenticationError, ValidationError


router = APIRouter(prefix="/v1/auth", tags=["인증"])


# Request/Response 스키마

class RegisterRequest(BaseModel):
    """회원가입 요청"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="비밀번호 (최소 8자)")
    name: str = Field(..., min_length=1, max_length=100, description="사용자 이름")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "name": "홍길동"
            }
        }


class LoginRequest(BaseModel):
    """로그인 요청"""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!"
            }
        }


class UserResponse(BaseModel):
    """사용자 정보 응답"""
    id: str
    email: str
    name: str
    role: str
    status: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """인증 응답 (토큰 포함)"""
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# API 엔드포인트

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    회원가입

    새로운 사용자 계정을 생성하고 JWT 토큰을 발급합니다.
    """
    try:
        user_service = UserService(db)
        user, tokens = await user_service.register(
            email=request.email,
            password=request.password,
            name=request.name
        )

        return AuthResponse(
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                name=user.name,
                role=user.role,
                status=user.status
            ),
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"]
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회원가입 처리 중 오류 발생: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    로그인

    이메일과 비밀번호로 로그인하고 JWT 토큰을 발급합니다.
    """
    try:
        user_service = UserService(db)
        user, tokens = await user_service.login(
            email=request.email,
            password=request.password
        )

        return AuthResponse(
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                name=user.name,
                role=user.role,
                status=user.status
            ),
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"]
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"로그인 처리 중 오류 발생: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # JWT 인증 의존성 (Phase 2에서 구현됨)
):
    """
    현재 로그인한 사용자 정보 조회

    JWT 토큰을 사용하여 현재 사용자 정보를 조회합니다.
    """
    # TODO: JWT 인증 미들웨어 통합
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="JWT 인증 통합 예정"
    )
