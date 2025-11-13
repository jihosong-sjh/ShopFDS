"""
pytest 설정 파일

pytest-anyio 백엔드를 asyncio만 사용하도록 설정합니다.
"""

import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    """pytest-anyio 백엔드를 asyncio로 제한"""
    return "asyncio"
