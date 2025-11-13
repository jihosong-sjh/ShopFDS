"""
SQLAlchemy Base 모델 및 데이터베이스 세션 관리

이 모듈은 모든 데이터베이스 모델의 기본 클래스와 비동기 데이터베이스 세션을 제공합니다.
"""

from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
import os


# 네이밍 컨벤션 정의 (Alembic 마이그레이션 시 일관된 제약 조건 이름 생성)
convention = {
    "ix": "ix_%(column_0_label)s",  # 인덱스
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # UNIQUE 제약
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # CHECK 제약
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # 외래 키
    "pk": "pk_%(table_name)s",  # 기본 키
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """
    모든 데이터베이스 모델의 기본 클래스

    이 클래스를 상속받는 모든 모델은 자동으로 SQLAlchemy ORM 기능을 사용할 수 있습니다.
    """

    metadata = metadata

    # 타입 어노테이션 (Python 3.11+)
    type_annotation_map = {}


class TimestampMixin:
    """
    생성/수정 시간 자동 추적 Mixin

    이 Mixin을 상속받으면 created_at과 updated_at 컬럼이 자동으로 추가됩니다.
    """

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        comment="생성 일시",
    )

    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="수정 일시",
    )


# 데이터베이스 연결 설정
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://shopfds:dev_password@localhost:5432/shopfds_dev",
)

# 비동기 엔진 생성
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # SQL 쿼리 로깅
    pool_size=10,  # 연결 풀 크기
    max_overflow=20,  # 추가 연결 허용 개수
    pool_pre_ping=True,  # 연결 전 핑 테스트 (연결 끊김 방지)
    pool_recycle=3600,  # 1시간마다 연결 재생성
)

# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 커밋 후 객체 만료 방지
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 의존성 주입용 데이터베이스 세션 생성기

    사용 예시:
    ```python
    @app.get("/users")
    async def get_users(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(User))
        return result.scalars().all()
    ```

    Yields:
        AsyncSession: 비동기 데이터베이스 세션
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    데이터베이스 초기화 (테이블 생성)

    주의: 프로덕션 환경에서는 Alembic 마이그레이션을 사용하세요.
    이 함수는 개발 및 테스트 환경에서만 사용됩니다.
    """
    async with engine.begin() as conn:
        # 모든 테이블 생성 (존재하지 않는 경우에만)
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """
    모든 테이블 삭제 (테스트용)

    주의: 이 함수는 모든 데이터를 삭제합니다!
    테스트 환경에서만 사용하세요.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def close_db() -> None:
    """
    데이터베이스 연결 종료

    애플리케이션 종료 시 호출하여 모든 연결을 정리합니다.
    """
    await engine.dispose()
