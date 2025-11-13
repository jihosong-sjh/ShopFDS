"""
Redis 연결 풀 관리

비동기 Redis 클라이언트 및 연결 풀을 제공합니다.
캐싱, 세션 관리, Rate Limiting에 사용됩니다.
"""

from typing import Optional, Any
import json
from redis import asyncio as aioredis
from redis.asyncio import ConnectionPool
from config import get_settings
from utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

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
        logger.info("Redis 연결 풀 초기화 중...")

        # 연결 풀 생성
        _redis_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_POOL_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            decode_responses=True,  # 문자열 자동 디코딩
        )

        # Redis 클라이언트 생성
        _redis_client = aioredis.Redis(connection_pool=_redis_pool)

        # 연결 테스트
        await _redis_client.ping()
        logger.info("✅ Redis 연결 성공")

        return _redis_client

    except Exception as e:
        logger.error(f"❌ Redis 연결 실패: {e}")
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
        logger.info("Redis 클라이언트 종료")

    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
        logger.info("Redis 연결 풀 종료")


async def get_redis() -> aioredis.Redis:
    """
    Redis 클라이언트 가져오기

    FastAPI 의존성 주입용 함수입니다.

    Returns:
        aioredis.Redis: Redis 클라이언트

    Example:
        ```python
        from fastapi import Depends
        from src.utils.redis_client import get_redis

        @app.get("/cache-test")
        async def cache_test(redis: aioredis.Redis = Depends(get_redis)):
            await redis.set("test_key", "test_value", ex=60)
            value = await redis.get("test_key")
            return {"value": value}
        ```
    """
    if _redis_client is None:
        await init_redis()

    return _redis_client


class RedisCache:
    """
    Redis 캐싱 헬퍼 클래스

    JSON 직렬화/역직렬화를 자동으로 처리합니다.
    """

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def get(self, key: str, default: Any = None) -> Any:
        """
        캐시에서 값 가져오기

        Args:
            key: 캐시 키
            default: 키가 없을 때 반환할 기본값

        Returns:
            Any: 캐시된 값 (JSON 역직렬화됨)
        """
        try:
            value = await self.redis.get(key)
            if value is None:
                return default

            # JSON 역직렬화 시도
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Redis GET 실패: {key}, {e}")
            return default

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값 (자동 JSON 직렬화)
            ttl: 만료 시간 (초, None이면 영구)

        Returns:
            bool: 성공 여부
        """
        try:
            # JSON 직렬화 시도
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)

            if ttl:
                await self.redis.setex(key, ttl, value)
            else:
                await self.redis.set(key, value)

            return True

        except Exception as e:
            logger.error(f"Redis SET 실패: {key}, {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        캐시에서 키 삭제

        Args:
            key: 삭제할 키

        Returns:
            bool: 성공 여부
        """
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE 실패: {key}, {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        키 존재 여부 확인

        Args:
            key: 확인할 키

        Returns:
            bool: 존재 여부
        """
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS 실패: {key}, {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        카운터 증가

        Args:
            key: 카운터 키
            amount: 증가량

        Returns:
            int: 증가 후 값
        """
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR 실패: {key}, {e}")
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """
        키에 만료 시간 설정

        Args:
            key: 키
            ttl: 만료 시간 (초)

        Returns:
            bool: 성공 여부
        """
        try:
            await self.redis.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Redis EXPIRE 실패: {key}, {e}")
            return False


async def get_redis_cache() -> RedisCache:
    """
    RedisCache 인스턴스 가져오기 (FastAPI 의존성 주입용)

    Returns:
        RedisCache: Redis 캐시 헬퍼

    Example:
        ```python
        @app.get("/products/{product_id}")
        async def get_product(
            product_id: str,
            cache: RedisCache = Depends(get_redis_cache)
        ):
            # 캐시에서 조회
            cached = await cache.get(f"product:{product_id}")
            if cached:
                return cached

            # DB에서 조회
            product = await db.get_product(product_id)

            # 캐시에 저장 (TTL: 5분)
            await cache.set(f"product:{product_id}", product, ttl=300)

            return product
        ```
    """
    redis = await get_redis()
    return RedisCache(redis)


class RateLimiter:
    """
    Redis 기반 Rate Limiter

    슬라이딩 윈도우 알고리즘을 사용한 요청 제한
    """

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int]:
        """
        Rate Limit 확인

        Args:
            key: Rate Limit 키 (예: f"rate_limit:user:{user_id}")
            max_requests: 윈도우 내 최대 요청 수
            window_seconds: 시간 윈도우 (초)

        Returns:
            tuple: (허용 여부, 현재 카운트, 남은 요청 수)
        """
        try:
            # 현재 카운트 증가
            current_count = await self.redis.incr(key)

            # 첫 요청이면 만료 시간 설정
            if current_count == 1:
                await self.redis.expire(key, window_seconds)

            remaining = max(0, max_requests - current_count)
            allowed = current_count <= max_requests

            return allowed, current_count, remaining

        except Exception as e:
            logger.error(f"Rate Limit 체크 실패: {key}, {e}")
            # Redis 오류 시 요청 허용 (Fail Open)
            return True, 0, max_requests


async def get_rate_limiter() -> RateLimiter:
    """
    RateLimiter 인스턴스 가져오기 (FastAPI 의존성 주입용)

    Returns:
        RateLimiter: Rate Limiter 인스턴스
    """
    redis = await get_redis()
    return RateLimiter(redis)
