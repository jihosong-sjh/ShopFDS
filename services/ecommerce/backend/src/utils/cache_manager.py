"""
Redis 캐싱 전략 관리자

상품 목록, CTI 결과, 사용자 세션 등 다양한 데이터에 대한
통합 캐싱 전략 제공
"""

import json
import logging
import functools
import hashlib
from typing import Any, Callable, Optional, List, Dict, TypeVar, Union
from datetime import timedelta
from redis import asyncio as aioredis

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheKeyBuilder:
    """
    캐시 키 생성 유틸리티

    일관성 있고 충돌 없는 캐시 키를 생성합니다.
    """

    @staticmethod
    def product_list(
        category: Optional[str] = None,
        search_query: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 20,
        offset: int = 0
    ) -> str:
        """
        상품 목록 캐시 키 생성

        Args:
            category: 카테고리 필터
            search_query: 검색어
            min_price: 최소 가격
            max_price: 최대 가격
            limit: 조회 개수
            offset: 오프셋

        Returns:
            캐시 키 (예: "product:list:category=electronics:limit=20:offset=0")
        """
        parts = ["product", "list"]

        if category:
            parts.append(f"category={category}")
        if search_query:
            # 검색어는 해시화하여 키 길이 제한
            query_hash = hashlib.md5(search_query.encode()).hexdigest()[:8]
            parts.append(f"query={query_hash}")
        if min_price is not None:
            parts.append(f"min={min_price}")
        if max_price is not None:
            parts.append(f"max={max_price}")

        parts.append(f"limit={limit}")
        parts.append(f"offset={offset}")

        return ":".join(parts)

    @staticmethod
    def product_detail(product_id: str) -> str:
        """상품 상세 캐시 키"""
        return f"product:detail:{product_id}"

    @staticmethod
    def user_cart(user_id: str) -> str:
        """사용자 장바구니 캐시 키"""
        return f"cart:user:{user_id}"

    @staticmethod
    def user_orders(user_id: str, limit: int = 10, offset: int = 0) -> str:
        """사용자 주문 목록 캐시 키"""
        return f"order:user:{user_id}:limit={limit}:offset={offset}"

    @staticmethod
    def order_detail(order_id: str) -> str:
        """주문 상세 캐시 키"""
        return f"order:detail:{order_id}"

    @staticmethod
    def cti_ip_check(ip_address: str) -> str:
        """CTI IP 체크 결과 캐시 키"""
        return f"cti:ip:{ip_address}"

    @staticmethod
    def cti_email_check(email: str) -> str:
        """CTI 이메일 체크 결과 캐시 키"""
        return f"cti:email:{email}"

    @staticmethod
    def fds_user_velocity(user_id: str) -> str:
        """FDS 사용자 속도 체크 캐시 키"""
        return f"fds:velocity:user:{user_id}"

    @staticmethod
    def fds_ip_velocity(ip_address: str) -> str:
        """FDS IP 속도 체크 캐시 키"""
        return f"fds:velocity:ip:{ip_address}"

    @staticmethod
    def user_session(user_id: str) -> str:
        """사용자 세션 캐시 키"""
        return f"session:user:{user_id}"

    @staticmethod
    def otp(user_id: str, purpose: str = "order") -> str:
        """OTP 캐시 키"""
        return f"otp:{purpose}:{user_id}"

    @staticmethod
    def custom(prefix: str, *args, **kwargs) -> str:
        """
        커스텀 캐시 키 생성

        Args:
            prefix: 키 접두사
            *args: 위치 인자들
            **kwargs: 키워드 인자들

        Returns:
            생성된 캐시 키
        """
        parts = [prefix]
        parts.extend(str(arg) for arg in args)
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return ":".join(parts)


class CacheManager:
    """
    통합 캐시 관리자

    Redis 캐싱 작업을 추상화하고 일관성 있는 인터페이스 제공
    """

    # 기본 TTL 설정 (초)
    DEFAULT_TTL = 300  # 5분
    SHORT_TTL = 60  # 1분
    MEDIUM_TTL = 600  # 10분
    LONG_TTL = 3600  # 1시간
    VERY_LONG_TTL = 86400  # 24시간

    def __init__(self, redis_client: aioredis.Redis):
        """
        Args:
            redis_client: Redis 클라이언트
        """
        self.redis = redis_client

    async def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 (없으면 None)
        """
        try:
            value = await self.redis.get(key)
            if value:
                logger.debug(f"캐시 HIT: {key}")
                return json.loads(value)
            logger.debug(f"캐시 MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"캐시 조회 실패: {key} - {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: 만료 시간 (초), None이면 기본값 사용
            nx: True면 키가 없을 때만 저장
            xx: True면 키가 있을 때만 저장

        Returns:
            성공 여부
        """
        if ttl is None:
            ttl = self.DEFAULT_TTL

        try:
            serialized = json.dumps(value, default=str)
            result = await self.redis.set(
                key,
                serialized,
                ex=ttl,
                nx=nx,
                xx=xx
            )
            if result:
                logger.debug(f"캐시 SET: {key} (TTL: {ttl}s)")
            return bool(result)
        except Exception as e:
            logger.error(f"캐시 저장 실패: {key} - {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        캐시에서 값 삭제

        Args:
            key: 캐시 키

        Returns:
            삭제 여부
        """
        try:
            result = await self.redis.delete(key)
            logger.debug(f"캐시 DELETE: {key}")
            return bool(result)
        except Exception as e:
            logger.error(f"캐시 삭제 실패: {key} - {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        패턴과 일치하는 모든 키 삭제

        Args:
            pattern: 키 패턴 (예: "product:*")

        Returns:
            삭제된 키 개수
        """
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"캐시 패턴 삭제: {pattern} - {deleted}개 키 삭제")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"캐시 패턴 삭제 실패: {pattern} - {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        캐시 키 존재 여부 확인

        Args:
            key: 캐시 키

        Returns:
            존재 여부
        """
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"캐시 존재 확인 실패: {key} - {e}")
            return False

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        캐시 키의 남은 TTL 조회

        Args:
            key: 캐시 키

        Returns:
            남은 TTL (초), 키가 없거나 만료 없으면 None
        """
        try:
            ttl = await self.redis.ttl(key)
            return ttl if ttl > 0 else None
        except Exception as e:
            logger.error(f"TTL 조회 실패: {key} - {e}")
            return None

    async def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """
        캐시 값 증가 (카운터)

        Args:
            key: 캐시 키
            amount: 증가량
            ttl: 만료 시간 (초), None이면 기본값 사용

        Returns:
            증가 후 값
        """
        try:
            value = await self.redis.incrby(key, amount)

            # TTL 설정 (키가 새로 생성된 경우)
            if ttl and value == amount:
                await self.redis.expire(key, ttl or self.DEFAULT_TTL)

            return value
        except Exception as e:
            logger.error(f"캐시 증가 실패: {key} - {e}")
            return 0

    async def get_or_set(
        self,
        key: str,
        fetch_func: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """
        캐시에서 조회하고, 없으면 fetch_func 실행 후 저장

        Args:
            key: 캐시 키
            fetch_func: 값을 가져올 비동기 함수
            ttl: 만료 시간 (초)

        Returns:
            캐시된 값 또는 fetch_func 결과
        """
        # 캐시 조회
        cached = await self.get(key)
        if cached is not None:
            return cached

        # 캐시 미스 - 데이터 가져오기
        try:
            value = await fetch_func()
            if value is not None:
                await self.set(key, value, ttl)
            return value
        except Exception as e:
            logger.error(f"캐시 fetch 실패: {key} - {e}")
            raise

    async def invalidate_user_cache(self, user_id: str):
        """
        사용자 관련 모든 캐시 무효화

        Args:
            user_id: 사용자 ID
        """
        patterns = [
            f"cart:user:{user_id}",
            f"order:user:{user_id}:*",
            f"session:user:{user_id}",
            f"otp:*:{user_id}",
            f"fds:velocity:user:{user_id}"
        ]

        for pattern in patterns:
            await self.delete_pattern(pattern)

        logger.info(f"사용자 캐시 무효화 완료: user_id={user_id}")

    async def invalidate_product_cache(self, product_id: Optional[str] = None):
        """
        상품 관련 캐시 무효화

        Args:
            product_id: 특정 상품 ID (None이면 모든 상품 캐시)
        """
        if product_id:
            # 특정 상품만 무효화
            await self.delete(CacheKeyBuilder.product_detail(product_id))
            logger.info(f"상품 캐시 무효화: product_id={product_id}")
        else:
            # 모든 상품 캐시 무효화
            await self.delete_pattern("product:*")
            logger.info("모든 상품 캐시 무효화 완료")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회

        Returns:
            캐시 통계 정보
        """
        try:
            info = await self.redis.info("stats")
            return {
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                ),
                "total_keys": await self.redis.dbsize(),
            }
        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {e}")
            return {}

    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """캐시 히트율 계산"""
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0


def cache_result(
    key_builder: Callable,
    ttl: Optional[int] = None,
    cache_none: bool = False
):
    """
    함수 결과를 캐싱하는 데코레이터

    Args:
        key_builder: 캐시 키를 생성하는 함수
        ttl: 만료 시간 (초)
        cache_none: None 값도 캐싱할지 여부

    Usage:
        @cache_result(
            key_builder=lambda product_id: CacheKeyBuilder.product_detail(product_id),
            ttl=CacheManager.LONG_TTL
        )
        async def get_product(product_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # self가 첫 번째 인자인 경우 (클래스 메서드)
            if args and hasattr(args[0], '__dict__'):
                self_obj = args[0]
                # CacheManager를 찾기
                cache_manager = getattr(self_obj, 'cache_manager', None)
                if not cache_manager:
                    # 캐시 매니저가 없으면 원본 함수 실행
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)

            # 캐시 키 생성
            cache_key = key_builder(*args[1:], **kwargs)

            # 캐시 조회
            cached = await cache_manager.get(cache_key)
            if cached is not None:
                return cached

            # 원본 함수 실행
            result = await func(*args, **kwargs)

            # 캐싱 (None 값 캐싱 여부 확인)
            if result is not None or cache_none:
                await cache_manager.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


class CacheWarmup:
    """
    캐시 워밍업 유틸리티

    자주 사용되는 데이터를 미리 캐시에 로드
    """

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager

    async def warmup_popular_products(self, product_ids: List[str], fetch_func: Callable):
        """
        인기 상품을 미리 캐시에 로드

        Args:
            product_ids: 상품 ID 리스트
            fetch_func: 상품 데이터를 가져올 함수 (product_id를 인자로 받음)
        """
        logger.info(f"인기 상품 캐시 워밍업 시작: {len(product_ids)}개")

        for product_id in product_ids:
            try:
                cache_key = CacheKeyBuilder.product_detail(product_id)
                product_data = await fetch_func(product_id)
                if product_data:
                    await self.cache_manager.set(
                        cache_key,
                        product_data,
                        ttl=CacheManager.LONG_TTL
                    )
            except Exception as e:
                logger.error(f"상품 캐시 워밍업 실패: {product_id} - {e}")

        logger.info("인기 상품 캐시 워밍업 완료")

    async def warmup_categories(self, categories: List[str], fetch_func: Callable):
        """
        카테고리별 상품 목록을 미리 캐시에 로드

        Args:
            categories: 카테고리 리스트
            fetch_func: 상품 목록을 가져올 함수 (category를 인자로 받음)
        """
        logger.info(f"카테고리 캐시 워밍업 시작: {len(categories)}개")

        for category in categories:
            try:
                cache_key = CacheKeyBuilder.product_list(category=category)
                products = await fetch_func(category)
                if products:
                    await self.cache_manager.set(
                        cache_key,
                        products,
                        ttl=CacheManager.MEDIUM_TTL
                    )
            except Exception as e:
                logger.error(f"카테고리 캐시 워밍업 실패: {category} - {e}")

        logger.info("카테고리 캐시 워밍업 완료")
