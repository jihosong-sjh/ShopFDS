"""
Pytest configuration and shared fixtures
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base
from src.models.user import User
from src.main import app


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test.

    Uses in-memory SQLite database for fast test execution.
    """
    # Create async engine with in-memory SQLite
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create and yield session
    async with async_session_factory() as session:
        yield session
        await session.rollback()

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="session")
def mock_redis():
    """Mock Redis client for testing"""
    from unittest.mock import AsyncMock

    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.expire.return_value = True

    return mock


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing FastAPI endpoints.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession):
    """
    Create a test user for authentication.
    """
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
        name="Test User",
        role="customer",
        status="active",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> dict:
    """
    Create mock authentication headers for testing.
    
    Note: This is a simplified version. In production, you would use actual JWT tokens.
    """
    from jose import jwt
    import os
    from datetime import datetime, timedelta
    
    # Create a JWT token for the test user
    token_data = {
        "sub": str(test_user.id),
        "email": test_user.email,
        "role": test_user.role,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    
    secret_key = os.getenv("JWT_SECRET_KEY", "test_secret_key_12345")
    token = jwt.encode(token_data, secret_key, algorithm="HS256")
    
    return {"Authorization": f"Bearer {token}"}
