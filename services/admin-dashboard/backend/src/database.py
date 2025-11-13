"""
데이터베이스 연결 및 세션 관리

SQLAlchemy를 사용하여 비동기 데이터베이스 연결을 관리합니다.
FDS 서비스와 동일한 데이터베이스를 사용합니다.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from src.config import settings

# 비동기 데이터베이스 엔진 생성
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # 연결 상태 확인
)

# 테스트 환경용 엔진 (연결 풀 비활성화)
test_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    poolclass=NullPool,
)

# 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    데이터베이스 세션 의존성

    FastAPI의 Depends()와 함께 사용됩니다.

    Yields:
        AsyncSession: 데이터베이스 세션

    Example:
        ```python
        @router.get("/stats")
        async def get_stats(db: AsyncSession = Depends(get_db)):
            # 데이터베이스 작업
            pass
        ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db():
    """
    데이터베이스 연결 종료

    애플리케이션 종료 시 호출됩니다.
    """
    await engine.dispose()
