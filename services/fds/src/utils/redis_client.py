"""
Redis 연결 풀 관리 (FDS Service)

비동기 Redis 클라이언트 및 연결 풀을 제공합니다.
Velocity Check, CTI 캐싱 등에 사용됩니다.
"""

from typing import Optional, Any
import json
import os
from redis import asyncio as aioredis
from redis.asyncio import ConnectionPool

# 전역 Redis 연결 풀 및 클라이언트
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> aioredis.Redis:
    """
    Redis 연결 풀 및 클라이언트 초기화

    Returns:
        aioredis.Redis: Redis 클라이언트 인스턴스
    """
    global _redis_pool, _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")

        # 연결 풀 생성
        _redis_pool = ConnectionPool.from_url(
            redis_url,
            max_connections=20,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            decode_responses=True,  # 문자열 자동 디코딩
        )

        # Redis 클라이언트 생성
        _redis_client = aioredis.Redis(connection_pool=_redis_pool)

        # 연결 테스트
        await _redis_client.ping()

        return _redis_client

    except Exception as e:
        print(f"Redis 연결 실패: {e}")
        raise


async def close_redis() -> None:
    """
    Redis 연결 종료

    애플리케이션 종료 시 호출하여 리소스를 정리합니다.
    """
    global _redis_pool, _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None

    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None


async def get_redis() -> aioredis.Redis:
    """
    Redis 클라이언트 가져오기

    FastAPI 의존성 주입용 함수입니다.

    Returns:
        aioredis.Redis: Redis 클라이언트
    """
    if _redis_client is None:
        await init_redis()

    return _redis_client
