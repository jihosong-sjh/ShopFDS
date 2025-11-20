"""
API Rate Limiting 미들웨어

DDoS 방어, API 남용 방지, 공정한 리소스 사용을 보장합니다.

**Rate Limiting 전략**:
- IP 기반: 60 requests/minute (일반)
- API Key 기반: 1000 requests/minute (인증된 서비스)
- Endpoint별: 커스텀 제한
- Sliding Window 알고리즘 사용

**응답 헤더**:
- X-RateLimit-Limit: 최대 요청 수
- X-RateLimit-Remaining: 남은 요청 수
- X-RateLimit-Reset: 제한 리셋 시간 (Unix timestamp)
"""

import time
import logging
from typing import Optional, Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from redis import asyncio as aioredis

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Rate Limiting 설정"""

    # IP 기반 제한 (일반 사용자)
    IP_LIMIT = 60  # 60 requests/minute
    IP_WINDOW = 60  # 1분

    # 서비스 토큰 기반 제한 (인증된 서비스)
    SERVICE_LIMIT = 1000  # 1000 requests/minute
    SERVICE_WINDOW = 60  # 1분

    # Endpoint별 커스텀 제한
    ENDPOINT_LIMITS = {
        "/v1/fds/evaluate": {"limit": 100, "window": 60},  # 100 req/min
        "/internal/fds/evaluate": {"limit": 500, "window": 60},  # 500 req/min
        "/v1/fds/health": {"limit": 300, "window": 60},  # 300 req/min
    }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate Limiting 미들웨어

    Sliding Window 알고리즘을 사용하여 요청 속도를 제한합니다.
    """

    def __init__(self, app, redis: Optional[aioredis.Redis] = None):
        """
        Args:
            app: FastAPI 애플리케이션
            redis: Redis 클라이언트 (선택, 없으면 인메모리 사용)
        """
        super().__init__(app)
        self.redis = redis
        self._in_memory_cache = {}  # Redis가 없을 때 사용

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        요청마다 Rate Limiting 체크

        Args:
            request: FastAPI 요청
            call_next: 다음 미들웨어/핸들러

        Returns:
            Response: 응답 (429 Too Many Requests 또는 정상 응답)
        """
        # 헬스 체크 엔드포인트는 Rate Limiting 제외
        if request.url.path in ["/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Rate Limiting 체크
        client_id = self._get_client_id(request)
        endpoint = request.url.path
        limit, window, remaining, reset_time = await self._check_rate_limit(
            client_id, endpoint
        )

        # Rate Limit 초과 시 429 응답
        if remaining < 0:
            logger.warning(
                f"[RATE LIMIT EXCEEDED] client={client_id}, "
                f"endpoint={endpoint}, limit={limit}/{window}s"
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "너무 많은 요청입니다. 잠시 후 다시 시도해주세요.",
                    "details": {
                        "limit": limit,
                        "window_seconds": window,
                        "reset_at": reset_time,
                    },
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(window),
                },
            )

        # 정상 처리
        response = await call_next(request)

        # Rate Limit 헤더 추가
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_client_id(self, request: Request) -> str:
        """
        클라이언트 식별자 추출

        Args:
            request: FastAPI 요청

        Returns:
            str: 클라이언트 식별자 (IP 또는 API Key)
        """
        # 서비스 토큰이 있으면 토큰 기반 식별
        service_token = request.headers.get("x-service-token")
        if service_token:
            return f"service:{service_token[:16]}"  # 보안상 일부만 사용

        # IP 주소 기반 식별
        # X-Forwarded-For 헤더 우선 (프록시/로드밸런서 뒤에 있을 경우)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # 첫 번째 IP 사용 (원본 클라이언트 IP)
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            # 직접 연결된 클라이언트 IP
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    async def _check_rate_limit(
        self, client_id: str, endpoint: str
    ) -> tuple[int, int, int, int]:
        """
        Rate Limit 체크 및 업데이트 (Sliding Window)

        Args:
            client_id: 클라이언트 식별자
            endpoint: 엔드포인트 경로

        Returns:
            tuple: (limit, window, remaining, reset_time)
        """
        # Endpoint별 제한 확인
        if endpoint in RateLimitConfig.ENDPOINT_LIMITS:
            config = RateLimitConfig.ENDPOINT_LIMITS[endpoint]
            limit = config["limit"]
            window = config["window"]
        # 서비스 토큰 기반 제한
        elif client_id.startswith("service:"):
            limit = RateLimitConfig.SERVICE_LIMIT
            window = RateLimitConfig.SERVICE_WINDOW
        # IP 기반 제한 (기본)
        else:
            limit = RateLimitConfig.IP_LIMIT
            window = RateLimitConfig.IP_WINDOW

        current_time = int(time.time())
        window_start = current_time - window

        # Redis 사용 시
        if self.redis:
            return await self._check_rate_limit_redis(
                client_id, endpoint, limit, window, current_time, window_start
            )
        # 인메모리 사용 시 (개발 환경)
        else:
            return self._check_rate_limit_memory(
                client_id, endpoint, limit, window, current_time, window_start
            )

    async def _check_rate_limit_redis(
        self,
        client_id: str,
        endpoint: str,
        limit: int,
        window: int,
        current_time: int,
        window_start: int,
    ) -> tuple[int, int, int, int]:
        """
        Redis 기반 Rate Limiting (Sliding Window)

        Args:
            client_id: 클라이언트 식별자
            endpoint: 엔드포인트
            limit: 최대 요청 수
            window: 시간 윈도우 (초)
            current_time: 현재 시간 (Unix timestamp)
            window_start: 윈도우 시작 시간

        Returns:
            tuple: (limit, window, remaining, reset_time)
        """
        key = f"rate_limit:{client_id}:{endpoint}"

        try:
            # Sorted Set을 사용한 Sliding Window
            # 1. 윈도우 밖의 오래된 요청 제거
            await self.redis.zremrangebyscore(key, 0, window_start)

            # 2. 현재 윈도우 내 요청 수 확인
            request_count = await self.redis.zcard(key)

            # 3. 새 요청 추가
            await self.redis.zadd(key, {str(current_time): current_time})

            # 4. TTL 설정 (윈도우 크기 + 여유)
            await self.redis.expire(key, window + 10)

            # 남은 요청 수 계산
            remaining = max(0, limit - request_count - 1)

            # 리셋 시간 (현재 윈도우 종료 시간)
            reset_time = current_time + window

            return limit, window, remaining, reset_time

        except Exception as e:
            logger.error(f"Redis Rate Limiting 실패: {e}")
            # Redis 실패 시 제한 없이 통과 (Fail-Open)
            return limit, window, limit, current_time + window

    def _check_rate_limit_memory(
        self,
        client_id: str,
        endpoint: str,
        limit: int,
        window: int,
        current_time: int,
        window_start: int,
    ) -> tuple[int, int, int, int]:
        """
        인메모리 Rate Limiting (개발 환경용)

        Args:
            client_id: 클라이언트 식별자
            endpoint: 엔드포인트
            limit: 최대 요청 수
            window: 시간 윈도우 (초)
            current_time: 현재 시간
            window_start: 윈도우 시작 시간

        Returns:
            tuple: (limit, window, remaining, reset_time)
        """
        key = f"{client_id}:{endpoint}"

        # 캐시 초기화
        if key not in self._in_memory_cache:
            self._in_memory_cache[key] = []

        # 오래된 요청 제거
        self._in_memory_cache[key] = [
            t for t in self._in_memory_cache[key] if t > window_start
        ]

        # 현재 요청 추가
        self._in_memory_cache[key].append(current_time)

        # 요청 수 계산
        request_count = len(self._in_memory_cache[key])
        remaining = max(0, limit - request_count)

        # 리셋 시간
        reset_time = current_time + window

        return limit, window, remaining, reset_time


def create_rate_limit_middleware(redis: Optional[aioredis.Redis] = None):
    """
    Rate Limiting 미들웨어 생성 헬퍼

    Args:
        redis: Redis 클라이언트 (선택)

    Returns:
        RateLimitMiddleware: Rate Limiting 미들웨어 인스턴스
    """

    def middleware_factory(app):
        return RateLimitMiddleware(app, redis=redis)

    return middleware_factory
