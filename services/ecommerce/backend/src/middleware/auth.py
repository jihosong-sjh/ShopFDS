"""
JWT 인증 미들웨어

FastAPI 의존성 주입을 활용한 JWT 인증 시스템을 제공합니다.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.security import JWTManager
from src.models.base import get_db
from src.utils.redis_client import get_rate_limiter


# HTTP Bearer 토큰 스킴 (Authorization: Bearer <token>)
security = HTTPBearer()


class AuthenticationError(HTTPException):
    """인증 실패 예외"""

    def __init__(self, detail: str = "인증에 실패했습니다."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """권한 부족 예외"""

    def __init__(self, detail: str = "접근 권한이 없습니다."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    현재 요청의 사용자 ID 추출

    JWT 토큰을 검증하고 사용자 ID를 반환합니다.

    Args:
        credentials: HTTP Bearer 토큰

    Returns:
        str: 사용자 ID

    Raises:
        AuthenticationError: 토큰이 유효하지 않은 경우

    Example:
        ```python
        @app.get("/profile")
        async def get_profile(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}
        ```
    """
    token = credentials.credentials

    try:
        payload = JWTManager.decode_token(token)
    except ValueError as e:
        raise AuthenticationError(detail=str(e))

    # 토큰 타입 검증 (access token만 허용)
    if not JWTManager.verify_token_type(payload, "access"):
        raise AuthenticationError(detail="잘못된 토큰 타입입니다.")

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(detail="토큰에서 사용자 정보를 찾을 수 없습니다.")

    return user_id


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    현재 요청의 사용자 객체 조회

    JWT 토큰에서 사용자 ID를 추출하고 데이터베이스에서 사용자 정보를 조회합니다.

    Args:
        user_id: 사용자 ID
        db: 데이터베이스 세션

    Returns:
        User: 사용자 객체

    Raises:
        AuthenticationError: 사용자를 찾을 수 없거나 비활성화된 경우

    Example:
        ```python
        @app.get("/profile")
        async def get_profile(current_user: User = Depends(get_current_user)):
            return {"email": current_user.email}
        ```
    """
    from sqlalchemy import select
    from src.models.user import User

    from uuid import UUID

    # Convert user_id string to UUID
    try:
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
    except ValueError:
        raise AuthenticationError(detail="잘못된 사용자 ID 형식입니다.")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError(detail="사용자를 찾을 수 없습니다.")

    if user.status != "active":
        raise AuthenticationError(detail="비활성화된 계정입니다.")

    return user


async def get_current_active_user(
    current_user=Depends(get_current_user),
):
    """
    활성화된 사용자만 허용

    Args:
        current_user: 현재 사용자

    Returns:
        User: 활성 사용자 객체

    Raises:
        AuthenticationError: 비활성화된 계정인 경우
    """
    # TODO: User 모델 생성 후 주석 해제
    # if current_user.status != "active":
    #     raise AuthenticationError(detail="비활성화된 계정입니다.")

    return current_user


def require_role(*allowed_roles: str):
    """
    특정 역할을 가진 사용자만 접근 허용하는 데코레이터 팩토리

    Args:
        *allowed_roles: 허용된 역할 목록 (예: "admin", "security_team")

    Returns:
        Callable: FastAPI 의존성 함수

    Example:
        ```python
        @app.get("/admin/dashboard")
        async def admin_dashboard(
            current_user: User = Depends(require_role("admin", "security_team"))
        ):
            return {"message": "관리자 대시보드"}
        ```
    """

    async def role_checker(
        current_user=Depends(get_current_user),
    ):
        if current_user.role not in allowed_roles:
            raise AuthorizationError(
                detail=f"이 기능은 {', '.join(allowed_roles)} 역할만 사용할 수 있습니다."
            )
        return current_user

    return role_checker


# 편의성을 위한 사전 정의된 역할 체커
require_admin = require_role("admin")
require_security_team = require_role("security_team", "admin")
require_customer = require_role("customer", "admin")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> Optional[dict]:
    """
    선택적 인증 (토큰이 있으면 사용자 정보 반환, 없으면 None)

    공개 API에서 로그인한 사용자에게만 추가 정보를 제공할 때 유용합니다.

    Args:
        credentials: HTTP Bearer 토큰 (선택)
        db: 데이터베이스 세션

    Returns:
        Optional[User]: 사용자 객체 또는 None

    Example:
        ```python
        @app.get("/products")
        async def get_products(current_user: Optional[User] = Depends(get_optional_user)):
            # 로그인한 사용자에게는 할인가 표시
            if current_user:
                return {"products": [...], "discount": True}
            return {"products": [...]}
        ```
    """
    if credentials is None:
        return None

    try:
        payload = JWTManager.decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            return None

        # TODO: User 모델 생성 후 데이터베이스 조회
        return {"id": user_id}

    except Exception:
        # 토큰이 유효하지 않으면 None 반환 (에러 발생 안 함)
        return None


class RateLimiter:
    """
    간단한 Rate Limiting (Redis 기반)

    Redis를 사용한 요청 제한 기능을 제공합니다.
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.rate_limiter = None

    async def check_rate_limit(self, user_id: str) -> bool:
        """
        Rate Limit 체크

        Args:
            user_id: 사용자 ID

        Returns:
            bool: 요청 허용 여부
        """
        try:
            # Redis Rate Limiter 가져오기
            if self.rate_limiter is None:
                self.rate_limiter = await get_rate_limiter()

            # Rate Limit 체크
            key = f"rate_limit:user:{user_id}"
            (
                allowed,
                current_count,
                remaining,
            ) = await self.rate_limiter.check_rate_limit(
                key=key,
                max_requests=self.max_requests,
                window_seconds=self.window_seconds,
            )

            return allowed

        except Exception as e:
            # Redis 연결 실패 시 요청 허용 (Fail Open)
            print(f"[WARNING] Rate Limit 체크 실패: {e}")
            return True


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    선택적 인증 - User 객체 반환

    토큰이 있으면 사용자 객체 반환, 없으면 None 반환

    Args:
        credentials: HTTP Bearer 토큰 (선택)
        db: 데이터베이스 세션

    Returns:
        Optional[User]: 사용자 객체 또는 None
    """
    if credentials is None:
        return None

    try:
        from sqlalchemy import select
        from src.models.user import User

        payload = JWTManager.decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            return None

        # 데이터베이스에서 사용자 조회
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user and user.status == "active":
            return user

        return None

    except Exception:
        # 토큰이 유효하지 않으면 None 반환 (에러 발생 안 함)
        return None
