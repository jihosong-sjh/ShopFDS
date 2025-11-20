"""
성능 최적화 유틸리티

Redis 캐싱 전략, 쿼리 최적화, 성능 모니터링을 제공합니다.

**캐싱 전략**:
- Device Fingerprint: 24시간 TTL
- Network Analysis (IP): 1시간 TTL
- Rule Execution Results: 10분 TTL
- ML Model Predictions: 5분 TTL
- GeoIP Lookups: 24시간 TTL

**성능 목표**:
- Redis 캐시 히트율: 85% 이상
- 캐시 조회 시간: <5ms
- DB 쿼리 시간: <10ms (인덱스 활용)
"""

import time
import logging
import hashlib
import json
from typing import Any, Optional, Callable, Dict
from functools import wraps
from redis import asyncio as aioredis

logger = logging.getLogger(__name__)


class CacheStrategy:
    """캐시 전략 정의"""

    DEVICE_FINGERPRINT = {"ttl": 86400, "prefix": "fds:device"}  # 24시간
    IP_REPUTATION = {"ttl": 3600, "prefix": "fds:ip"}  # 1시간
    RULE_RESULT = {"ttl": 600, "prefix": "fds:rule"}  # 10분
    ML_PREDICTION = {"ttl": 300, "prefix": "fds:ml"}  # 5분
    GEOIP_LOOKUP = {"ttl": 86400, "prefix": "fds:geo"}  # 24시간
    USER_VELOCITY = {"ttl": 300, "prefix": "fds:velocity"}  # 5분
    BLACKLIST = {"ttl": 3600, "prefix": "fds:blacklist"}  # 1시간


class PerformanceOptimizer:
    """
    성능 최적화 매니저

    Redis 캐싱, 쿼리 최적화, 성능 모니터링을 제공합니다.
    """

    def __init__(self, redis: aioredis.Redis):
        """
        Args:
            redis: Redis 클라이언트
        """
        self.redis = redis
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_queries = 0

    async def get_cached(
        self,
        key: str,
        strategy: Dict[str, Any],
        fetch_func: Optional[Callable] = None,
    ) -> Optional[Any]:
        """
        캐시된 데이터 조회 (캐시 미스 시 fetch_func 호출)

        Args:
            key: 캐시 키 (prefix 제외)
            strategy: 캐시 전략 (CacheStrategy)
            fetch_func: 캐시 미스 시 호출할 함수 (선택)

        Returns:
            캐시된 데이터 또는 None
        """
        start_time = time.time()
        cache_key = f"{strategy['prefix']}:{key}"

        try:
            # Redis에서 캐시 조회
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                self._cache_hits += 1
                elapsed_ms = int((time.time() - start_time) * 1000)

                logger.debug(
                    f"[CACHE HIT] key={cache_key}, time={elapsed_ms}ms, "
                    f"hit_rate={self.cache_hit_rate:.2%}"
                )

                # JSON 디코딩
                return json.loads(cached_data)

            # 캐시 미스
            self._cache_misses += 1
            logger.debug(
                f"[CACHE MISS] key={cache_key}, " f"hit_rate={self.cache_hit_rate:.2%}"
            )

            # fetch_func이 제공되면 데이터 가져와서 캐싱
            if fetch_func:
                data = await fetch_func()
                if data is not None:
                    await self.set_cached(key, data, strategy)
                return data

            return None

        except Exception as e:
            logger.error(f"캐시 조회 실패: key={cache_key}, error={e}")
            # 캐시 실패 시에도 fetch_func 시도
            if fetch_func:
                try:
                    return await fetch_func()
                except Exception as fetch_error:
                    logger.error(f"fetch_func 실패: {fetch_error}")
            return None

    async def set_cached(self, key: str, data: Any, strategy: Dict[str, Any]) -> bool:
        """
        데이터 캐싱

        Args:
            key: 캐시 키 (prefix 제외)
            data: 캐싱할 데이터
            strategy: 캐시 전략 (CacheStrategy)

        Returns:
            bool: 캐싱 성공 여부
        """
        cache_key = f"{strategy['prefix']}:{key}"
        ttl = strategy["ttl"]

        try:
            # JSON 인코딩
            cached_data = json.dumps(data, default=str)

            # Redis에 저장 (TTL 포함)
            await self.redis.setex(cache_key, ttl, cached_data)

            logger.debug(f"[CACHE SET] key={cache_key}, ttl={ttl}s")
            return True

        except Exception as e:
            logger.error(f"캐싱 실패: key={cache_key}, error={e}")
            return False

    async def delete_cached(self, key: str, strategy: Dict[str, Any]) -> bool:
        """
        캐시 삭제

        Args:
            key: 캐시 키 (prefix 제외)
            strategy: 캐시 전략

        Returns:
            bool: 삭제 성공 여부
        """
        cache_key = f"{strategy['prefix']}:{key}"

        try:
            await self.redis.delete(cache_key)
            logger.debug(f"[CACHE DELETE] key={cache_key}")
            return True

        except Exception as e:
            logger.error(f"캐시 삭제 실패: key={cache_key}, error={e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        패턴에 매칭되는 모든 캐시 삭제

        Args:
            pattern: Redis 키 패턴 (예: "fds:device:*")

        Returns:
            int: 삭제된 키 개수
        """
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"[CACHE INVALIDATE] pattern={pattern}, deleted={deleted}")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"캐시 무효화 실패: pattern={pattern}, error={e}")
            return 0

    @property
    def cache_hit_rate(self) -> float:
        """
        캐시 히트율 계산

        Returns:
            float: 캐시 히트율 (0.0 ~ 1.0)
        """
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return self._cache_hits / total

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회

        Returns:
            Dict: 캐시 통계 (히트/미스 횟수, 히트율)
        """
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "total_cache_queries": self._cache_hits + self._cache_misses,
        }

    def reset_cache_stats(self):
        """캐시 통계 초기화"""
        self._cache_hits = 0
        self._cache_misses = 0


def cache_result(strategy: Dict[str, Any], key_func: Callable):
    """
    함수 결과를 캐싱하는 데코레이터

    Args:
        strategy: 캐시 전략 (CacheStrategy)
        key_func: 캐시 키 생성 함수 (함수 인자를 받아 키 반환)

    Usage:
        @cache_result(CacheStrategy.IP_REPUTATION, lambda ip: f"ip:{ip}")
        async def check_ip_reputation(ip: str):
            return await fetch_ip_reputation(ip)
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Redis 클라이언트가 첫 번째 인자인지 확인
            redis = kwargs.get("redis") or (args[0] if args else None)

            if not redis or not isinstance(redis, aioredis.Redis):
                # Redis가 없으면 캐싱 없이 함수 실행
                return await func(*args, **kwargs)

            # 캐시 키 생성
            cache_key = key_func(*args, **kwargs)
            optimizer = PerformanceOptimizer(redis)

            # 캐시 조회
            cached_result = await optimizer.get_cached(cache_key, strategy)
            if cached_result is not None:
                return cached_result

            # 캐시 미스 - 함수 실행 및 캐싱
            result = await func(*args, **kwargs)
            await optimizer.set_cached(cache_key, result, strategy)

            return result

        return wrapper

    return decorator


def generate_cache_key(*parts: Any) -> str:
    """
    캐시 키 생성 (여러 파트를 조합하여 해시)

    Args:
        *parts: 캐시 키에 포함할 파트들

    Returns:
        str: 생성된 캐시 키
    """
    # 파트들을 문자열로 변환하고 조합
    key_parts = [str(part) for part in parts if part is not None]
    combined = ":".join(key_parts)

    # 긴 키는 SHA256 해시로 축약
    if len(combined) > 100:
        hash_digest = hashlib.sha256(combined.encode()).hexdigest()
        return f"hash:{hash_digest[:16]}"

    return combined


class QueryOptimizer:
    """
    데이터베이스 쿼리 최적화 헬퍼

    인덱스 활용, N+1 쿼리 방지, 배치 로딩 등을 제공합니다.
    """

    @staticmethod
    def log_slow_query(query_name: str, duration_ms: int, threshold_ms: int = 10):
        """
        느린 쿼리 로깅

        Args:
            query_name: 쿼리 이름
            duration_ms: 쿼리 실행 시간 (밀리초)
            threshold_ms: 느린 쿼리 임계값 (기본: 10ms)
        """
        if duration_ms > threshold_ms:
            logger.warning(
                f"[SLOW QUERY] {query_name} took {duration_ms}ms "
                f"(threshold: {threshold_ms}ms)"
            )

    @staticmethod
    def measure_query(query_name: str):
        """
        쿼리 실행 시간 측정 데코레이터

        Usage:
            @QueryOptimizer.measure_query("get_user_transactions")
            async def get_user_transactions(user_id):
                ...
        """

        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                result = await func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)

                QueryOptimizer.log_slow_query(query_name, duration_ms)
                return result

            return wrapper

        return decorator


class PerformanceMonitor:
    """
    성능 모니터링 유틸리티

    평가 시간, 캐시 히트율, 쿼리 성능 등을 추적합니다.
    """

    def __init__(self):
        self.metrics = {
            "total_evaluations": 0,
            "total_evaluation_time_ms": 0,
            "avg_evaluation_time_ms": 0,
            "p95_evaluation_time_ms": 0,
            "max_evaluation_time_ms": 0,
            "evaluation_times": [],  # 최근 1000개 기록
        }

    def record_evaluation(self, evaluation_time_ms: int):
        """
        평가 시간 기록

        Args:
            evaluation_time_ms: 평가 시간 (밀리초)
        """
        self.metrics["total_evaluations"] += 1
        self.metrics["total_evaluation_time_ms"] += evaluation_time_ms

        # 최근 1000개만 유지
        self.metrics["evaluation_times"].append(evaluation_time_ms)
        if len(self.metrics["evaluation_times"]) > 1000:
            self.metrics["evaluation_times"].pop(0)

        # 평균 계산
        self.metrics["avg_evaluation_time_ms"] = (
            self.metrics["total_evaluation_time_ms"] / self.metrics["total_evaluations"]
        )

        # P95 계산 (최근 1000개 기준)
        if self.metrics["evaluation_times"]:
            sorted_times = sorted(self.metrics["evaluation_times"])
            p95_index = int(len(sorted_times) * 0.95)
            self.metrics["p95_evaluation_time_ms"] = sorted_times[p95_index]

        # 최대값 갱신
        if evaluation_time_ms > self.metrics["max_evaluation_time_ms"]:
            self.metrics["max_evaluation_time_ms"] = evaluation_time_ms

        # P95 목표(50ms) 초과 시 경고
        if self.metrics["p95_evaluation_time_ms"] > 50:
            logger.warning(
                f"[PERFORMANCE] P95 evaluation time ({self.metrics['p95_evaluation_time_ms']}ms) "
                f"exceeds target (50ms)"
            )

    def get_metrics(self) -> Dict[str, Any]:
        """
        성능 메트릭 조회

        Returns:
            Dict: 성능 메트릭
        """
        return {
            "total_evaluations": self.metrics["total_evaluations"],
            "avg_evaluation_time_ms": round(self.metrics["avg_evaluation_time_ms"], 2),
            "p95_evaluation_time_ms": self.metrics["p95_evaluation_time_ms"],
            "max_evaluation_time_ms": self.metrics["max_evaluation_time_ms"],
            "target_p95_ms": 50,
            "target_met": self.metrics["p95_evaluation_time_ms"] <= 50,
        }


# 전역 성능 모니터 인스턴스
performance_monitor = PerformanceMonitor()
