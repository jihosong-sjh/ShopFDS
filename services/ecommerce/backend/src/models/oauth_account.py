"""
OAuthAccount Model

소셜 로그인(Google, Kakao, Naver) 연동 정보를 저장하는 모델
"""

from sqlalchemy import Column, String, Text, ForeignKey, Enum as SQLEnum, DateTime, Uuid
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from src.models.base import Base


class OAuthProvider(str, enum.Enum):
    """OAuth 제공자 열거형"""

    GOOGLE = "GOOGLE"
    KAKAO = "KAKAO"
    NAVER = "NAVER"


class OAuthAccount(Base):
    """
    OAuthAccount 모델

    사용자의 소셜 로그인 연동 정보를 저장합니다.
    - 사용자당 여러 OAuth 제공자 연동 가능 (Google + Kakao + Naver)
    - provider와 provider_user_id 조합이 고유해야 함 (UNIQUE 제약)
    """

    __tablename__ = "oauth_accounts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(SQLEnum(OAuthProvider), nullable=False)
    provider_user_id = Column(
        String(200), nullable=False, comment="OAuth 제공자의 사용자 고유 ID"
    )
    access_token = Column(Text, nullable=True, comment="OAuth Access Token (암호화 권장)")
    refresh_token = Column(Text, nullable=True, comment="OAuth Refresh Token")
    token_expires_at = Column(
        DateTime(timezone=True), nullable=True, comment="Access Token 만료 시각"
    )
    profile_data = Column(
        JSONB,
        nullable=True,
        comment="OAuth 제공자로부터 받은 프로필 정보 (이름, 이메일, 아바타)",
    )
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="oauth_accounts")

    # Unique constraint: 동일한 provider + provider_user_id 조합 불가
    __table_args__ = (
        {"comment": "소셜 로그인 OAuth 계정 연동 정보"},
        # UniqueConstraint는 Alembic 마이그레이션에서 생성
    )

    def __repr__(self):
        return f"<OAuthAccount(id={self.id}, user_id={self.user_id}, provider={self.provider.value})>"
