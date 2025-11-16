"""
Rate Limiting 미들웨어 (FastAPI 레벨)

목적: API 남용 방지, DDoS 공격 완화, 서버 자원 보호
전략:
- IP 기반 제한: 동일 IP에서 일정 시간 내 요청 횟수 제한
- 사용자 기반 제한: 인증된 사용자별 요청 제한
- 엔드포인트별 제한: 민감한 API는 더 엄격한 제한 적용
"""

import time
import logging
from typing import Dict, Callable
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate Limiting 로직 (Redis 또는 인메모리)"""

    def __init__(self, redis_client=None):
        """
        Args:
            redis_client: Redis 클라이언트 (None이면 인메모리 사용)
        """
        self.redis = redis_client
        # 인메모리 저장소 (Redis 없을 때 사용)
        self.memory_store: Dict[str, Dict] = defaultdict(dict)

    def check_rate_limit(
        self, key: str, max_requests: int, window_seconds: int
    ) -> Dict[str, any]:
        """
        Rate Limit 확인

        Args:
            key: 고유 키 (예: "ip:192.168.1.1" 또는 "user:123")
            max_requests: 시간 창 내 최대 요청 수
            window_seconds: 시간 창 (초)

        Returns:
            {
                "allowed": bool,  # 요청 허용 여부
                "requests_made": int,  # 현재까지 요청 수
                "requests_remaining": int,  # 남은 요청 수
                "reset_at": datetime,  # 제한 리셋 시간
                "retry_after": int,  # 재시도 가능 시간 (초)
            }
        """
        current_time = time.time()

        if self.redis:
            return self._check_rate_limit_redis(
                key, max_requests, window_seconds, current_time
            )
        else:
            return self._check_rate_limit_memory(
                key, max_requests, window_seconds, current_time
            )

    def _check_rate_limit_redis(
        self, key: str, max_requests: int, window_seconds: int, current_time: float
    ) -> Dict[str, any]:
        """Redis 기반 Rate Limiting"""
        redis_key = f"rate_limit:{key}"

        # Redis Pipeline 사용
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, current_time - window_seconds)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {str(current_time): current_time})
        pipe.expire(redis_key, window_seconds)
        _, requests_made, _, _ = pipe.execute()

        requests_remaining = max(0, max_requests - requests_made)
        allowed = requests_made <= max_requests
        reset_at = datetime.fromtimestamp(current_time + window_seconds)
        retry_after = window_seconds if not allowed else 0

        return {
            "allowed": allowed,
            "requests_made": requests_made,
            "requests_remaining": requests_remaining,
            "reset_at": reset_at,
            "retry_after": retry_after,
        }

    def _check_rate_limit_memory(
        self, key: str, max_requests: int, window_seconds: int, current_time: float
    ) -> Dict[str, any]:
        """인메모리 Rate Limiting (Redis 없을 때)"""
        # 만료된 요청 제거
        if key in self.memory_store:
            self.memory_store[key] = {
                timestamp: count
                for timestamp, count in self.memory_store[key].items()
                if current_time - float(timestamp) < window_seconds
            }

        # 현재 요청 수 계산
        requests_made = sum(self.memory_store[key].values())

        # 요청 추가
        if requests_made < max_requests:
            self.memory_store[key][str(current_time)] = 1

        requests_remaining = max(0, max_requests - requests_made - 1)
        allowed = requests_made < max_requests
        reset_at = datetime.fromtimestamp(current_time + window_seconds)
        retry_after = window_seconds if not allowed else 0

        return {
            "allowed": allowed,
            "requests_made": requests_made + (1 if allowed else 0),
            "requests_remaining": requests_remaining,
            "reset_at": reset_at,
            "retry_after": retry_after,
        }

    def reset(self, key: str):
        """특정 키의 Rate Limit 리셋 (테스트용)"""
        if self.redis:
            redis_key = f"rate_limit:{key}"
            self.redis.delete(redis_key)
        else:
            if key in self.memory_store:
                del self.memory_store[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI Rate Limiting 미들웨어"""

    # 기본 Rate Limit 설정 (IP 기반)
    DEFAULT_RATE_LIMIT = {
        "max_requests": 100,  # 100 요청
        "window_seconds": 60,  # 1분
    }

    # 엔드포인트별 Rate Limit 설정
    ENDPOINT_RATE_LIMITS = {
        "/v1/auth/register": {"max_requests": 5, "window_seconds": 3600},  # 5회/1시간
        "/v1/auth/login": {"max_requests": 10, "window_seconds": 900},  # 10회/15분
        "/v1/auth/request-otp": {"max_requests": 3, "window_seconds": 300},  # 3회/5분
        "/v1/orders": {"max_requests": 30, "window_seconds": 60},  # 30회/1분
    }

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.limiter = RateLimiter(redis_client)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        """모든 요청에 대해 Rate Limiting 적용"""
        # Rate Limit 제외 경로 (Health Check 등)
        excluded_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
        if request.url.path in excluded_paths:
            return await call_next(request)

        # 클라이언트 IP 추출
        client_ip = request.client.host

        # X-Forwarded-For 헤더 확인 (프록시 뒤에 있을 경우)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # 엔드포인트별 Rate Limit 설정 가져오기
        path = request.url.path
        rate_limit_config = self.ENDPOINT_RATE_LIMITS.get(path, self.DEFAULT_RATE_LIMIT)

        # Rate Limit 키 생성
        rate_limit_key = f"ip:{client_ip}:{path}"

        # Rate Limit 확인
        result = self.limiter.check_rate_limit(
            key=rate_limit_key,
            max_requests=rate_limit_config["max_requests"],
            window_seconds=rate_limit_config["window_seconds"],
        )

        # 응답 헤더 추가
        headers = {
            "X-RateLimit-Limit": str(rate_limit_config["max_requests"]),
            "X-RateLimit-Remaining": str(result["requests_remaining"]),
            "X-RateLimit-Reset": result["reset_at"].isoformat(),
        }

        # Rate Limit 초과 시
        if not result["allowed"]:
            logger.warning(
                f"Rate limit exceeded for IP {client_ip} on {path}. "
                f"Requests: {result['requests_made']}/{rate_limit_config['max_requests']}"
            )

            headers["Retry-After"] = str(result["retry_after"])

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. "
                    f"Max {rate_limit_config['max_requests']} requests "
                    f"per {rate_limit_config['window_seconds']} seconds.",
                    "retry_after": result["retry_after"],
                },
                headers=headers,
            )

        # 정상 요청 처리
        response = await call_next(request)

        # Rate Limit 헤더 추가
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value

        return response


# 데코레이터 방식 Rate Limiting (특정 엔드포인트에만 적용)
def rate_limit(max_requests: int, window_seconds: int, redis_client=None):
    """
    Rate Limiting 데코레이터

    Usage:
        @app.get("/api/data")
        @rate_limit(max_requests=10, window_seconds=60)
        async def get_data(request: Request):
            return {"data": "..."}
    """
    limiter = RateLimiter(redis_client)

    def decorator(func: Callable):
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host

            # X-Forwarded-For 헤더 확인
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()

            # Rate Limit 키 생성
            rate_limit_key = f"ip:{client_ip}:{request.url.path}"

            # Rate Limit 확인
            result = limiter.check_rate_limit(
                key=rate_limit_key,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )

            # Rate Limit 초과 시
            if not result["allowed"]:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Too Many Requests",
                        "retry_after": result["retry_after"],
                    },
                    headers={"Retry-After": str(result["retry_after"])},
                )

            # 정상 요청 처리
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


# 사용 예시
if __name__ == "__main__":
    # 인메모리 Rate Limiter 테스트
    limiter = RateLimiter()

    print("=== Rate Limiter 테스트 ===")
    for i in range(1, 8):
        result = limiter.check_rate_limit(
            key="ip:192.168.1.1",
            max_requests=5,
            window_seconds=10,
        )
        print(
            f"요청 {i}: 허용={result['allowed']}, "
            f"남은 요청={result['requests_remaining']}"
        )

        if not result["allowed"]:
            print(f"  → {result['retry_after']}초 후 재시도")
            break

        time.sleep(0.5)
