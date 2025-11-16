"""
사용자 서비스

회원가입, 로그인, 프로필 조회 등 사용자 관련 비즈니스 로직
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.models.user import User, UserRole, UserStatus
from src.models.cart import Cart
from src.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from src.utils.exceptions import (
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
)


class UserService:
    """사용자 관련 비즈니스 로직"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(
        self, email: str, password: str, name: str, role: UserRole = UserRole.CUSTOMER
    ) -> tuple[User, dict]:
        """
        새 사용자 회원가입

        Args:
            email: 이메일 (로그인 ID)
            password: 비밀번호
            name: 사용자 이름
            role: 사용자 역할 (기본값: customer)

        Returns:
            (User, tokens): 생성된 사용자 객체 및 JWT 토큰

        Raises:
            ValidationError: 이메일이 이미 존재하거나 유효하지 않은 경우
        """
        # 비밀번호 검증
        if len(password) < 8:
            raise ValidationError("비밀번호는 최소 8자 이상이어야 합니다")

        # 이메일 중복 확인
        existing_user = await self._get_user_by_email(email)
        if existing_user:
            raise ValidationError(f"이미 등록된 이메일입니다: {email}")

        # 비밀번호 해싱
        password_hash = hash_password(password)

        # 사용자 생성
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
            role=role.value,
            status=UserStatus.ACTIVE.value,
        )

        self.db.add(user)
        await self.db.flush()  # ID 생성

        # 장바구니 자동 생성
        cart = Cart(user_id=user.id)
        self.db.add(cart)

        try:
            await self.db.commit()
            await self.db.refresh(user)
        except IntegrityError as e:
            await self.db.rollback()
            raise ValidationError(f"사용자 생성 실패: {str(e)}")

        # JWT 토큰 생성
        tokens = {
            "access_token": create_access_token(
                {"sub": str(user.id), "email": user.email, "role": user.role}
            ),
            "refresh_token": create_refresh_token({"sub": str(user.id)}),
            "token_type": "bearer",
        }

        return user, tokens

    async def login(self, email: str, password: str) -> tuple[User, dict]:
        """
        사용자 로그인

        Args:
            email: 이메일
            password: 비밀번호

        Returns:
            (User, tokens): 사용자 객체 및 JWT 토큰

        Raises:
            AuthenticationError: 로그인 실패
        """
        user = await self._get_user_by_email(email)
        if not user:
            raise AuthenticationError("이메일 또는 비밀번호가 올바르지 않습니다")

        # 계정 상태 확인
        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError(f"계정이 비활성 상태입니다: {user.status}")

        # 계정 잠금 확인 (3회 초과 로그인 실패)
        if user.is_locked():
            raise AuthenticationError("로그인 실패 횟수 초과로 계정이 일시 잠금되었습니다. 15분 후 다시 시도해주세요.")

        # 비밀번호 검증
        if not verify_password(password, user.password_hash):
            user.increment_failed_attempts()
            await self.db.commit()

            remaining_attempts = 3 - user.failed_login_attempts
            if remaining_attempts > 0:
                raise AuthenticationError(
                    f"비밀번호가 올바르지 않습니다. 남은 시도 횟수: {remaining_attempts}"
                )
            else:
                raise AuthenticationError("로그인 실패 횟수 초과로 계정이 일시 잠금되었습니다.")

        # 로그인 성공: 실패 횟수 초기화 및 마지막 로그인 시각 업데이트
        user.reset_failed_attempts()
        user.last_login_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)

        # JWT 토큰 생성
        tokens = {
            "access_token": create_access_token(
                {"sub": str(user.id), "email": user.email, "role": user.role}
            ),
            "refresh_token": create_refresh_token({"sub": str(user.id)}),
            "token_type": "bearer",
        }

        return user, tokens

    async def get_user_profile(self, user_id: str) -> User:
        """
        사용자 프로필 조회

        Args:
            user_id: 사용자 ID (UUID 문자열)

        Returns:
            User: 사용자 객체

        Raises:
            ResourceNotFoundError: 사용자를 찾을 수 없는 경우
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"사용자를 찾을 수 없습니다: {user_id}")

        return user

    async def update_user_profile(
        self, user_id: str, name: Optional[str] = None
    ) -> User:
        """
        사용자 프로필 업데이트

        Args:
            user_id: 사용자 ID
            name: 변경할 이름 (선택)

        Returns:
            User: 업데이트된 사용자 객체
        """
        user = await self.get_user_profile(user_id)

        if name:
            user.name = name

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> bool:
        """
        비밀번호 변경

        Args:
            user_id: 사용자 ID
            current_password: 현재 비밀번호
            new_password: 새 비밀번호

        Returns:
            bool: 변경 성공 여부

        Raises:
            AuthenticationError: 현재 비밀번호가 올바르지 않은 경우
            ValidationError: 새 비밀번호가 조건을 만족하지 않는 경우
        """
        user = await self.get_user_profile(user_id)

        # 현재 비밀번호 검증
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("현재 비밀번호가 올바르지 않습니다")

        # 새 비밀번호 검증
        if len(new_password) < 8:
            raise ValidationError("새 비밀번호는 최소 8자 이상이어야 합니다")

        # 비밀번호 해싱 및 업데이트
        user.password_hash = hash_password(new_password)
        await self.db.commit()

        return True

    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회 (내부 메서드)"""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """ID로 사용자 조회 (내부 메서드)"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()
