"""
인증 API 엔드포인트

회원가입, 로그인 등 인증 관련 REST API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from models.user import UserRole
from services.user_service import UserService
from utils.exceptions import AuthenticationError, ValidationError
from utils.otp import get_otp_service
from utils.redis_client import get_redis


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


# OTP 관련 스키마 및 엔드포인트

class OTPRequest(BaseModel):
    """OTP 요청"""
    user_id: str = Field(..., description="사용자 ID")
    purpose: str = Field(default="transaction", description="OTP 목적 (transaction, login 등)")
    metadata: dict = Field(default_factory=dict, description="추가 메타데이터 (주문 ID 등)")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "purpose": "transaction",
                "metadata": {
                    "order_id": "ORD-20250114-123456",
                    "amount": 150000
                }
            }
        }


class OTPResponse(BaseModel):
    """OTP 생성 응답"""
    success: bool
    message: str
    otp_code: str = Field(description="OTP 코드 (개발 환경에서만 반환, 프로덕션에서는 SMS/이메일 발송)")
    expires_at: str
    attempts_remaining: int

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "OTP가 생성되었습니다. SMS로 발송되었습니다.",
                "otp_code": "123456",
                "expires_at": "2025-01-14T10:05:00",
                "attempts_remaining": 3
            }
        }


class OTPVerifyRequest(BaseModel):
    """OTP 검증 요청"""
    user_id: str = Field(..., description="사용자 ID")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6자리 OTP 코드")
    purpose: str = Field(default="transaction", description="OTP 목적")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "otp_code": "123456",
                "purpose": "transaction"
            }
        }


class OTPVerifyResponse(BaseModel):
    """OTP 검증 응답"""
    valid: bool
    message: str
    attempts_remaining: int
    metadata: dict = Field(default_factory=dict, description="OTP 생성 시 저장된 메타데이터")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "message": "OTP 검증 성공",
                "attempts_remaining": 2,
                "metadata": {
                    "order_id": "ORD-20250114-123456",
                    "amount": 150000
                }
            }
        }


@router.post("/request-otp", response_model=OTPResponse)
async def request_otp(
    request: OTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    추가 인증을 위한 OTP 요청

    의심 거래 시 사용자에게 추가 인증을 위한 OTP를 발급합니다.
    실제 프로덕션 환경에서는 SMS 또는 이메일로 OTP를 발송하고,
    응답에서 OTP 코드를 제거해야 합니다.

    Args:
        request: OTP 요청 정보

    Returns:
        OTPResponse: OTP 생성 결과

    Raises:
        HTTPException: OTP 생성 실패 시
    """
    try:
        # Redis 클라이언트 가져오기
        redis_client = await get_redis()
        otp_service = await get_otp_service(redis_client)

        # OTP 생성
        result = await otp_service.generate_otp(
            user_id=request.user_id,
            purpose=request.purpose,
            metadata=request.metadata
        )

        # TODO: 프로덕션 환경에서는 SMS/이메일로 OTP 발송
        # await send_sms(phone_number, result["otp_code"])
        # await send_email(email, result["otp_code"])

        return OTPResponse(
            success=True,
            message="OTP가 생성되었습니다. (개발 환경: 응답에 포함, 프로덕션: SMS/이메일 발송)",
            otp_code=result["otp_code"],  # 개발 환경에서만 반환
            expires_at=result["expires_at"],
            attempts_remaining=result["attempts_remaining"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OTP 생성 중 오류 발생: {str(e)}"
        )


@router.post("/verify-otp", response_model=OTPVerifyResponse)
async def verify_otp(
    request: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    OTP 검증

    사용자가 입력한 OTP 코드를 검증합니다.
    최대 3회 시도 가능하며, 실패 시 시도 횟수가 감소합니다.

    Args:
        request: OTP 검증 요청

    Returns:
        OTPVerifyResponse: 검증 결과

    Raises:
        HTTPException: OTP 검증 실패 또는 오류 시
    """
    try:
        # Redis 클라이언트 가져오기
        redis_client = await get_redis()
        otp_service = await get_otp_service(redis_client)

        # OTP 검증
        result = await otp_service.verify_otp(
            user_id=request.user_id,
            otp_code=request.otp_code,
            purpose=request.purpose
        )

        if not result["valid"]:
            # 검증 실패
            status_code = status.HTTP_401_UNAUTHORIZED
            if result["attempts_remaining"] == 0:
                status_code = status.HTTP_429_TOO_MANY_REQUESTS

            raise HTTPException(
                status_code=status_code,
                detail=result["message"]
            )

        # 검증 성공
        return OTPVerifyResponse(
            valid=result["valid"],
            message=result["message"],
            attempts_remaining=result["attempts_remaining"],
            metadata=result.get("metadata", {})
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OTP 검증 중 오류 발생: {str(e)}"
        )
