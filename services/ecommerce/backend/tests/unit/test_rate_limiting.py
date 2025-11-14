"""
Rate Limiting 미들웨어 유닛 테스트
"""

import pytest
import time
from unittest.mock import AsyncMock, Mock
from fastapi import Request, HTTPException
from starlette.datastructures import Headers
from src.middleware.rate_limiting import RateLimiter, RateLimitMiddleware


class TestRateLimiter:
    """RateLimiter 클래스 테스트"""

    def test_rate_limit_within_limit(self):
        """제한 내 요청 (정상)"""
        limiter = RateLimiter()

        # 5회 제한, 10초 창
        for i in range(5):
            result = limiter.check_rate_limit(
                key="test_key",
                max_requests=5,
                window_seconds=10,
            )
            assert result["allowed"] is True
            assert result["requests_made"] == i + 1
            assert result["requests_remaining"] >= 0

    def test_rate_limit_exceeded(self):
        """Rate Limit 초과"""
        limiter = RateLimiter()

        # 3회 제한
        for i in range(3):
            result = limiter.check_rate_limit(
                key="test_key_exceeded",
                max_requests=3,
                window_seconds=10,
            )
            assert result["allowed"] is True

        # 4번째 요청은 거부되어야 함
        result = limiter.check_rate_limit(
            key="test_key_exceeded",
            max_requests=3,
            window_seconds=10,
        )
        assert result["allowed"] is False
        assert result["retry_after"] == 10

    def test_rate_limit_window_expiry(self):
        """시간 창 만료 후 리셋"""
        limiter = RateLimiter()

        # 2회 제한, 1초 창
        result1 = limiter.check_rate_limit(
            key="test_key_expiry",
            max_requests=2,
            window_seconds=1,
        )
        assert result1["allowed"] is True

        result2 = limiter.check_rate_limit(
            key="test_key_expiry",
            max_requests=2,
            window_seconds=1,
        )
        assert result2["allowed"] is True

        # 3번째 요청은 거부
        result3 = limiter.check_rate_limit(
            key="test_key_expiry",
            max_requests=2,
            window_seconds=1,
        )
        assert result3["allowed"] is False

        # 1초 대기 후 리셋
        time.sleep(1.1)

        # 새로운 요청 허용
        result4 = limiter.check_rate_limit(
            key="test_key_expiry",
            max_requests=2,
            window_seconds=1,
        )
        assert result4["allowed"] is True

    def test_rate_limit_different_keys(self):
        """서로 다른 키는 독립적으로 제한"""
        limiter = RateLimiter()

        # 키1: 1회 요청
        result1 = limiter.check_rate_limit(
            key="key1",
            max_requests=1,
            window_seconds=10,
        )
        assert result1["allowed"] is True

        # 키1: 2회 요청 (거부)
        result2 = limiter.check_rate_limit(
            key="key1",
            max_requests=1,
            window_seconds=10,
        )
        assert result2["allowed"] is False

        # 키2: 1회 요청 (허용 - 독립적)
        result3 = limiter.check_rate_limit(
            key="key2",
            max_requests=1,
            window_seconds=10,
        )
        assert result3["allowed"] is True

    def test_rate_limit_reset(self):
        """Rate Limit 리셋"""
        limiter = RateLimiter()

        # 1회 제한 도달
        result1 = limiter.check_rate_limit(
            key="test_reset",
            max_requests=1,
            window_seconds=10,
        )
        assert result1["allowed"] is True

        result2 = limiter.check_rate_limit(
            key="test_reset",
            max_requests=1,
            window_seconds=10,
        )
        assert result2["allowed"] is False

        # 리셋
        limiter.reset("test_reset")

        # 다시 허용
        result3 = limiter.check_rate_limit(
            key="test_reset",
            max_requests=1,
            window_seconds=10,
        )
        assert result3["allowed"] is True

    def test_rate_limit_requests_remaining(self):
        """남은 요청 수 확인"""
        limiter = RateLimiter()

        result1 = limiter.check_rate_limit(
            key="test_remaining",
            max_requests=5,
            window_seconds=10,
        )
        assert result1["requests_remaining"] == 4  # 5 - 1

        result2 = limiter.check_rate_limit(
            key="test_remaining",
            max_requests=5,
            window_seconds=10,
        )
        assert result2["requests_remaining"] == 3  # 5 - 2

    def test_rate_limit_metadata(self):
        """Rate Limit 메타데이터 확인"""
        limiter = RateLimiter()

        result = limiter.check_rate_limit(
            key="test_metadata",
            max_requests=10,
            window_seconds=60,
        )

        assert "allowed" in result
        assert "requests_made" in result
        assert "requests_remaining" in result
        assert "reset_at" in result
        assert "retry_after" in result

        assert isinstance(result["allowed"], bool)
        assert isinstance(result["requests_made"], int)
        assert isinstance(result["retry_after"], int)


class TestRateLimitMiddleware:
    """RateLimitMiddleware 테스트"""

    @pytest.mark.asyncio
    async def test_middleware_allows_normal_request(self):
        """정상 요청 허용"""
        app = Mock()
        middleware = RateLimitMiddleware(app)

        # Mock Request
        request = Mock(spec=Request)
        request.client.host = "192.168.1.1"
        request.url.path = "/v1/products"
        request.headers = Headers({"host": "localhost"})

        # Mock call_next
        async def call_next(request):
            response = Mock()
            response.headers = {}
            return response

        # 요청 처리
        response = await middleware.dispatch(request, call_next)

        # Rate Limit 헤더 확인
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.asyncio
    async def test_middleware_blocks_excess_requests(self):
        """Rate Limit 초과 요청 차단"""
        app = Mock()
        middleware = RateLimitMiddleware(app)

        # Mock Request
        request = Mock(spec=Request)
        request.client.host = "192.168.1.100"
        request.url.path = "/v1/auth/register"
        request.headers = Headers({"host": "localhost"})

        # Mock call_next
        async def call_next(request):
            response = Mock()
            response.headers = {}
            return response

        # 제한(5회) 초과 시도
        for i in range(6):
            response = await middleware.dispatch(request, call_next)

            if i < 5:
                # 처음 5회는 허용
                assert response.status_code != 429
            else:
                # 6번째는 차단
                assert response.status_code == 429
                assert "retry_after" in response.body.decode()

    @pytest.mark.asyncio
    async def test_middleware_excluded_paths(self):
        """제외된 경로는 Rate Limiting 적용 안 함"""
        app = Mock()
        middleware = RateLimitMiddleware(app)

        # Mock Request (Health Check)
        request = Mock(spec=Request)
        request.client.host = "192.168.1.1"
        request.url.path = "/health"
        request.headers = Headers({"host": "localhost"})

        # Mock call_next
        async def call_next(request):
            response = Mock()
            response.headers = {}
            return response

        # Health Check 경로는 Rate Limiting 적용 안 함
        response = await middleware.dispatch(request, call_next)

        # Rate Limit 헤더가 없어야 함
        assert "X-RateLimit-Limit" not in response.headers

    @pytest.mark.asyncio
    async def test_middleware_x_forwarded_for_header(self):
        """X-Forwarded-For 헤더 처리"""
        app = Mock()
        middleware = RateLimitMiddleware(app)

        # Mock Request with X-Forwarded-For
        request = Mock(spec=Request)
        request.client.host = "10.0.0.1"  # 프록시 IP
        request.url.path = "/v1/products"
        request.headers = Headers({
            "host": "localhost",
            "X-Forwarded-For": "203.0.113.1, 10.0.0.1"  # 실제 클라이언트 IP가 첫 번째
        })

        # Mock call_next
        async def call_next(request):
            response = Mock()
            response.headers = {}
            return response

        # X-Forwarded-For의 첫 번째 IP로 Rate Limiting 적용
        response = await middleware.dispatch(request, call_next)

        assert "X-RateLimit-Limit" in response.headers


class TestRateLimitEdgeCases:
    """Rate Limiting 엣지 케이스 테스트"""

    def test_zero_max_requests(self):
        """최대 요청 수가 0인 경우"""
        limiter = RateLimiter()

        result = limiter.check_rate_limit(
            key="test_zero",
            max_requests=0,
            window_seconds=10,
        )

        # 0회 제한이면 모든 요청 거부
        assert result["allowed"] is False

    def test_very_long_window(self):
        """매우 긴 시간 창"""
        limiter = RateLimiter()

        result = limiter.check_rate_limit(
            key="test_long_window",
            max_requests=1000,
            window_seconds=86400,  # 24시간
        )

        assert result["allowed"] is True
        assert result["retry_after"] == 0  # 아직 제한 안 걸림

    def test_concurrent_requests(self):
        """동시 요청 처리"""
        limiter = RateLimiter()

        # 동일 키로 빠르게 여러 요청
        results = []
        for i in range(10):
            result = limiter.check_rate_limit(
                key="test_concurrent",
                max_requests=5,
                window_seconds=10,
            )
            results.append(result)

        # 처음 5개는 허용, 나머지는 거부
        allowed_count = sum(1 for r in results if r["allowed"])
        assert allowed_count == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
