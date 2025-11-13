"""
pytest 설정 파일

pytest-anyio 백엔드를 asyncio만 사용하도록 설정합니다.
"""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.models.base import Base


@pytest.fixture(scope="session")
def anyio_backend():
    """pytest-anyio 백엔드를 asyncio로 제한"""
    return "asyncio"


@pytest.fixture(scope="function")
async def db_session():
    """
    테스트용 데이터베이스 세션 픽스처

    각 테스트마다 독립된 트랜잭션을 제공하며,
    테스트 종료 후 자동으로 롤백됩니다.
    """
    # 테스트용 인메모리 SQLite 데이터베이스 사용
    # Note: 실제로는 PostgreSQL 테스트 DB를 사용하는 것이 좋지만,
    # 간단한 테스트를 위해 SQLite를 사용합니다.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 세션 팩토리 생성
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # 세션 생성
    async with async_session_factory() as session:
        yield session
        await session.rollback()

    # 정리
    await engine.dispose()
