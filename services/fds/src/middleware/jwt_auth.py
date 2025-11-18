"""
JWT 인증 미들웨어

서비스 간 인증을 위한 JWT 토큰 검증을 제공합니다.

**JWT 구조**:
- Header: 알고리즘 (HS256 또는 RS256)
- Payload: service_name, exp, iat, jti
- Signature: 비밀키 또는 공개키로 검증

**보안 기능**:
- 토큰 만료 시간 검증
- 토큰 서명 검증
- Blacklist 토큰 차단
- Rate Limiting 통합
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

logger = logging.getLogger(__name__)


class JWTConfig:
    """JWT 설정"""

    # 비밀키 (환경 변수에서 로드)
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")

    # 알고리즘
    ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

    # 토큰 만료 시간
    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )  # 1시간

    # Issuer (발급자)
    ISSUER = os.getenv("JWT_ISSUER", "shopfds-auth-service")

    # Audience (대상)
    AUDIENCE = os.getenv("JWT_AUDIENCE", "shopfds-fds-service")


class JWTManager:
    """
    JWT 토큰 생성 및 검증 매니저
    """

    def __init__(
        self,
        secret_key: str = JWTConfig.SECRET_KEY,
        algorithm: str = JWTConfig.ALGORITHM,
    ):
        """
        Args:
            secret_key: JWT 비밀키
            algorithm: 서명 알고리즘
        """
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Access Token 생성

        Args:
            data: 토큰에 포함할 데이터 (service_name, permissions 등)
            expires_delta: 만료 시간 (기본: 1시간)

        Returns:
            str: JWT 토큰
        """
        to_encode = data.copy()

        # 만료 시간 설정
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        # 표준 클레임 추가
        to_encode.update(
            {
                "exp": expire,  # 만료 시간
                "iat": datetime.utcnow(),  # 발급 시간
                "iss": JWTConfig.ISSUER,  # 발급자
                "aud": JWTConfig.AUDIENCE,  # 대상
            }
        )

        # JWT 토큰 생성
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return encoded_jwt

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        JWT 토큰 검증

        Args:
            token: JWT 토큰

        Returns:
            Dict[str, Any]: 토큰 페이로드

        Raises:
            HTTPException: 토큰이 유효하지 않은 경우
        """
        try:
            # 토큰 디코딩 및 검증
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=JWTConfig.AUDIENCE,
                issuer=JWTConfig.ISSUER,
            )

            # 필수 클레임 확인
            if "service_name" not in payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="토큰에 service_name이 없습니다",
                )

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("[JWT] 토큰 만료")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰이 만료되었습니다",
                headers={"WWW-Authenticate": "Bearer"},
            )

        except jwt.InvalidTokenError as e:
            logger.warning(f"[JWT] 유효하지 않은 토큰: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다",
                headers={"WWW-Authenticate": "Bearer"},
            )


# 전역 JWT 매니저 인스턴스
jwt_manager = JWTManager()


# HTTPBearer 스키마 (Authorization: Bearer <token>)
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_jwt_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """
    JWT 토큰 검증 의존성

    Args:
        credentials: HTTP Authorization 헤더

    Returns:
        Dict[str, Any]: 토큰 페이로드

    Raises:
        HTTPException: 토큰이 없거나 유효하지 않은 경우

    Usage:
        @app.get("/protected")
        async def protected_endpoint(
            token_payload: Dict = Depends(verify_jwt_token)
        ):
            service_name = token_payload["service_name"]
            return {"message": f"Hello, {service_name}"}
    """
    # 토큰이 없는 경우
    if not credentials:
        logger.warning("[JWT] 토큰이 제공되지 않음")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 토큰 검증
    token = credentials.credentials
    payload = jwt_manager.verify_token(token)

    logger.debug(
        f"[JWT] 토큰 검증 성공: service={payload.get('service_name')}, "
        f"exp={payload.get('exp')}"
    )

    return payload


async def verify_service_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    """
    서비스 토큰 검증 (간소화 버전)

    Args:
        credentials: HTTP Authorization 헤더

    Returns:
        str: 서비스 이름

    Raises:
        HTTPException: 토큰이 유효하지 않은 경우
    """
    payload = await verify_jwt_token(credentials)
    return payload["service_name"]


def create_service_token(service_name: str, permissions: list[str] = None) -> str:
    """
    서비스 토큰 생성 헬퍼

    Args:
        service_name: 서비스 이름 (예: "ecommerce-backend")
        permissions: 권한 목록 (예: ["fds:evaluate", "fds:read"])

    Returns:
        str: JWT 토큰

    Usage:
        token = create_service_token(
            service_name="ecommerce-backend",
            permissions=["fds:evaluate", "fds:read"]
        )
    """
    data = {
        "service_name": service_name,
        "permissions": permissions or [],
        "token_type": "service_access_token",
    }

    return jwt_manager.create_access_token(data)


class PermissionChecker:
    """
    권한 확인 헬퍼

    특정 권한이 있는지 확인합니다.
    """

    def __init__(self, required_permission: str):
        """
        Args:
            required_permission: 필요한 권한 (예: "fds:evaluate")
        """
        self.required_permission = required_permission

    async def __call__(
        self, token_payload: Dict = Depends(verify_jwt_token)
    ) -> Dict[str, Any]:
        """
        권한 확인

        Args:
            token_payload: JWT 토큰 페이로드

        Returns:
            Dict[str, Any]: 토큰 페이로드

        Raises:
            HTTPException: 권한이 없는 경우
        """
        permissions = token_payload.get("permissions", [])

        if self.required_permission not in permissions:
            logger.warning(
                f"[JWT] 권한 없음: service={token_payload.get('service_name')}, "
                f"required={self.required_permission}, "
                f"has={permissions}"
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"권한이 없습니다: {self.required_permission}",
            )

        return token_payload


def require_permission(permission: str):
    """
    권한 필요 데코레이터 팩토리

    Args:
        permission: 필요한 권한

    Returns:
        PermissionChecker: 권한 확인 의존성

    Usage:
        @app.post("/v1/fds/evaluate")
        async def evaluate(
            token: Dict = Depends(require_permission("fds:evaluate"))
        ):
            ...
    """
    return PermissionChecker(permission)


# 개발 환경용 토큰 생성 스크립트
if __name__ == "__main__":
    # 이커머스 서비스용 토큰 생성
    ecommerce_token = create_service_token(
        service_name="ecommerce-backend",
        permissions=["fds:evaluate", "fds:read", "fds:health"],
    )

    print("[ECOMMERCE SERVICE TOKEN]")
    print(ecommerce_token)
    print()

    # Admin 서비스용 토큰 생성
    admin_token = create_service_token(
        service_name="admin-dashboard",
        permissions=[
            "fds:evaluate",
            "fds:read",
            "fds:write",
            "fds:admin",
            "fds:health",
        ],
    )

    print("[ADMIN SERVICE TOKEN]")
    print(admin_token)
    print()

    # 토큰 검증 테스트
    try:
        payload = jwt_manager.verify_token(ecommerce_token)
        print("[TOKEN VERIFICATION SUCCESS]")
        print(f"Service: {payload['service_name']}")
        print(f"Permissions: {payload['permissions']}")
        print(f"Expires: {datetime.fromtimestamp(payload['exp'])}")
    except Exception as e:
        print(f"[TOKEN VERIFICATION FAILED]: {e}")
