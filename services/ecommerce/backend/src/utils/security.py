"""
보안 유틸리티 모듈

비밀번호 해싱, JWT 토큰 생성/검증, 보안 관련 헬퍼 함수를 제공합니다.
"""

from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
import secrets
import os
import hashlib
import base64

# JWT 설정
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-INSECURE")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class PasswordHasher:
    """
    비밀번호 해싱 및 검증 클래스

    bcrypt 알고리즘을 사용하여 안전하게 비밀번호를 저장합니다.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """
        비밀번호를 bcrypt로 해시화

        bcrypt의 72바이트 제한을 우회하기 위해 먼저 SHA256으로 해싱합니다.

        Args:
            password: 평문 비밀번호

        Returns:
            str: 해시된 비밀번호

        Example:
            >>> hashed = PasswordHasher.hash_password("SecurePass123!")
            >>> print(hashed)  # $2b$12$...
        """
        # bcrypt의 72바이트 제한을 우회하기 위해 먼저 SHA256으로 해싱
        # SHA256은 항상 32바이트를 생성하므로 bcrypt 제한 내에 있음
        sha256_hash = hashlib.sha256(password.encode("utf-8")).digest()
        # Base64 인코딩하여 bcrypt에 전달 (44자)
        b64_hash = base64.b64encode(sha256_hash).decode("utf-8")
        # bcrypt 직접 사용 (passlib 호환성 문제 회피)
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(b64_hash.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        비밀번호 검증

        Args:
            plain_password: 평문 비밀번호
            hashed_password: 해시된 비밀번호

        Returns:
            bool: 일치 여부

        Example:
            >>> hashed = PasswordHasher.hash_password("SecurePass123!")
            >>> PasswordHasher.verify_password("SecurePass123!", hashed)
            True
            >>> PasswordHasher.verify_password("WrongPassword", hashed)
            False
        """
        # 동일한 SHA256 해싱 적용 후 검증
        sha256_hash = hashlib.sha256(plain_password.encode("utf-8")).digest()
        b64_hash = base64.b64encode(sha256_hash).decode("utf-8")
        # bcrypt 직접 사용하여 검증
        return bcrypt.checkpw(b64_hash.encode("utf-8"), hashed_password.encode("utf-8"))

    @staticmethod
    def needs_update(hashed_password: str) -> bool:
        """
        비밀번호 해시가 업데이트 필요한지 확인

        bcrypt의 cost factor가 변경되었을 때 재해싱이 필요합니다.

        Args:
            hashed_password: 해시된 비밀번호

        Returns:
            bool: 업데이트 필요 여부
        """
        # 기본 cost factor는 12
        # bcrypt 해시 형식: $2b$12$...
        try:
            parts = hashed_password.split("$")
            if len(parts) >= 3:
                current_cost = int(parts[2])
                return current_cost < 12
        except:
            pass
        return False


class JWTManager:
    """
    JWT 토큰 생성 및 검증 관리 클래스
    """

    @staticmethod
    def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Access Token 생성

        Args:
            data: 토큰에 포함할 데이터 (user_id, role 등)
            expires_delta: 만료 시간 (기본값: 15분)

        Returns:
            str: JWT 토큰

        Example:
            >>> token = JWTManager.create_access_token({"sub": "user_id_123", "role": "customer"})
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """
        Refresh Token 생성

        Args:
            data: 토큰에 포함할 데이터

        Returns:
            str: JWT 토큰 (만료 시간: 7일)

        Example:
            >>> refresh_token = JWTManager.create_refresh_token({"sub": "user_id_123"})
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> dict:
        """
        JWT 토큰 디코딩 및 검증

        Args:
            token: JWT 토큰

        Returns:
            dict: 디코딩된 페이로드

        Raises:
            JWTError: 토큰이 유효하지 않거나 만료된 경우
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    @staticmethod
    def verify_token_type(payload: dict, expected_type: str) -> bool:
        """
        토큰 타입 검증 (access vs refresh)

        Args:
            payload: 디코딩된 토큰 페이로드
            expected_type: 기대하는 토큰 타입 ("access" 또는 "refresh")

        Returns:
            bool: 타입 일치 여부
        """
        return payload.get("type") == expected_type


class SecurityUtils:
    """
    기타 보안 유틸리티
    """

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        안전한 랜덤 토큰 생성 (OTP, API 키 등)

        Args:
            length: 토큰 길이 (바이트)

        Returns:
            str: Hex 인코딩된 토큰

        Example:
            >>> token = SecurityUtils.generate_secure_token()
            >>> len(token)  # 64 (32 bytes * 2)
            64
        """
        return secrets.token_hex(length)

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """
        숫자 OTP 생성

        Args:
            length: OTP 자릿수

        Returns:
            str: 숫자 OTP

        Example:
            >>> otp = SecurityUtils.generate_otp()
            >>> len(otp)
            6
        """
        return "".join([str(secrets.randbelow(10)) for _ in range(length)])

    @staticmethod
    def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
        """
        민감 데이터 마스킹 (카드 번호, 이메일 등)

        Args:
            data: 마스킹할 데이터
            visible_chars: 뒤에서 보이는 문자 수

        Returns:
            str: 마스킹된 데이터

        Example:
            >>> SecurityUtils.mask_sensitive_data("1234567890123456", 4)
            '************3456'
            >>> SecurityUtils.mask_sensitive_data("user@example.com", 4)
            '*************com'
        """
        if len(data) <= visible_chars:
            return data

        masked_length = len(data) - visible_chars
        return "*" * masked_length + data[-visible_chars:]

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """
        비밀번호 강도 검증

        요구사항:
        - 최소 8자 이상
        - 대문자 1개 이상
        - 소문자 1개 이상
        - 숫자 1개 이상
        - 특수문자 1개 이상

        Args:
            password: 검증할 비밀번호

        Returns:
            tuple: (검증 성공 여부, 에러 메시지)

        Example:
            >>> SecurityUtils.validate_password_strength("Weak")
            (False, "비밀번호는 최소 8자 이상이어야 합니다.")
            >>> SecurityUtils.validate_password_strength("StrongPass123!")
            (True, "")
        """
        if len(password) < 8:
            return False, "비밀번호는 최소 8자 이상이어야 합니다."

        if not any(c.isupper() for c in password):
            return False, "비밀번호에 대문자가 1개 이상 포함되어야 합니다."

        if not any(c.islower() for c in password):
            return False, "비밀번호에 소문자가 1개 이상 포함되어야 합니다."

        if not any(c.isdigit() for c in password):
            return False, "비밀번호에 숫자가 1개 이상 포함되어야 합니다."

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "비밀번호에 특수문자가 1개 이상 포함되어야 합니다."

        return True, ""


# 편의를 위한 래퍼 함수들
def hash_password(password: str) -> str:
    """비밀번호 해싱 (PasswordHasher의 래퍼 함수)"""
    return PasswordHasher.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증 (PasswordHasher의 래퍼 함수)"""
    return PasswordHasher.verify_password(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Access Token 생성 (JWTManager의 래퍼 함수)"""
    return JWTManager.create_access_token(data, expires_delta)


def create_refresh_token(data: dict) -> str:
    """Refresh Token 생성 (JWTManager의 래퍼 함수)"""
    return JWTManager.create_refresh_token(data)
