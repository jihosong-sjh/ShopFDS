"""
Redis 캐시 유틸리티

FDS 서비스에서 사용하는 Redis 캐싱 유틸리티 함수들을 제공합니다.
디바이스 ID 조회, IP 주소 분석 결과, 외부 API 응답 등을 캐싱합니다.
"""

import json
import os
from typing import Optional, Any, Dict
import redis.asyncio as redis


class RedisCache:
    """
    Redis 캐시 클라이언트 래퍼

    비동기 Redis 연결을 관리하고 캐싱 작업을 단순화합니다.
    """

    def __init__(self):
        """Redis 클라이언트 초기화"""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client: Optional[redis.Redis] = None
        self._redis_url = redis_url

    async def connect(self) -> None:
        """Redis 서버에 연결"""
        if self.client is None:
            self.client = await redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )

    async def disconnect(self) -> None:
        """Redis 연결 종료"""
        if self.client:
            await self.client.close()
            await self.client.connection_pool.disconnect()
            self.client = None

    async def get(self, key: str) -> Optional[str]:
        """
        키에 대한 값 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 (문자열) 또는 None
        """
        if self.client is None:
            await self.connect()
        return await self.client.get(key)

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        JSON 형식의 값 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 (딕셔너리) 또는 None
        """
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        키-값 쌍 저장

        Args:
            key: 캐시 키
            value: 저장할 값 (문자열)
            ttl: Time-To-Live (초 단위), None이면 만료 없음

        Returns:
            성공 여부
        """
        if self.client is None:
            await self.connect()

        if ttl:
            return await self.client.setex(key, ttl, value)
        else:
            return await self.client.set(key, value)

    async def set_json(
        self, key: str, value: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """
        JSON 형식의 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값 (딕셔너리)
            ttl: Time-To-Live (초 단위), None이면 만료 없음

        Returns:
            성공 여부
        """
        json_value = json.dumps(value, ensure_ascii=False)
        return await self.set(key, json_value, ttl)

    async def delete(self, key: str) -> int:
        """
        키 삭제

        Args:
            key: 삭제할 캐시 키

        Returns:
            삭제된 키 개수
        """
        if self.client is None:
            await self.connect()
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """
        키 존재 여부 확인

        Args:
            key: 확인할 캐시 키

        Returns:
            존재 여부
        """
        if self.client is None:
            await self.connect()
        return await self.client.exists(key) > 0

    async def ttl(self, key: str) -> int:
        """
        키의 남은 TTL 확인

        Args:
            key: 확인할 캐시 키

        Returns:
            남은 시간 (초), -1이면 만료 없음, -2이면 키 없음
        """
        if self.client is None:
            await self.connect()
        return await self.client.ttl(key)

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        정수 값 증가

        Args:
            key: 캐시 키
            amount: 증가량

        Returns:
            증가 후 값
        """
        if self.client is None:
            await self.connect()
        return await self.client.incrby(key, amount)

    async def flush_pattern(self, pattern: str) -> int:
        """
        패턴과 일치하는 모든 키 삭제

        Args:
            pattern: 삭제할 키 패턴 (예: "device:*")

        Returns:
            삭제된 키 개수
        """
        if self.client is None:
            await self.connect()

        deleted = 0
        async for key in self.client.scan_iter(pattern):
            await self.client.delete(key)
            deleted += 1
        return deleted


# 싱글톤 인스턴스
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """
    Redis 캐시 싱글톤 인스턴스 가져오기

    Returns:
        RedisCache 인스턴스
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance


# 도메인별 캐시 키 빌더
class CacheKeys:
    """캐시 키 네이밍 규칙"""

    @staticmethod
    def device_fingerprint(device_id: str) -> str:
        """디바이스 핑거프린트 캐시 키"""
        return f"device:{device_id}"

    @staticmethod
    def network_analysis(ip_address: str) -> str:
        """네트워크 분석 캐시 키"""
        return f"network:{ip_address}"

    @staticmethod
    def blacklist_check(entry_type: str, entry_value: str) -> str:
        """블랙리스트 체크 캐시 키"""
        return f"blacklist:{entry_type}:{entry_value}"

    @staticmethod
    def external_api(service_name: str, request_hash: str) -> str:
        """외부 API 응답 캐시 키"""
        return f"external:{service_name}:{request_hash}"

    @staticmethod
    def fraud_rule_result(transaction_id: str) -> str:
        """사기 탐지 룰 결과 캐시 키"""
        return f"rule_result:{transaction_id}"


# TTL 상수 (초 단위)
class CacheTTL:
    """캐시 만료 시간 상수"""

    DEVICE_FINGERPRINT = 86400  # 24시간
    NETWORK_ANALYSIS = 3600  # 1시간
    BLACKLIST_CHECK = 300  # 5분
    EXTERNAL_API = 1800  # 30분
    FRAUD_RULE_RESULT = 600  # 10분


# 편의 함수
async def cache_device_fingerprint(
    device_id: str, fingerprint_data: Dict[str, Any]
) -> bool:
    """
    디바이스 핑거프린트 캐싱

    Args:
        device_id: 디바이스 ID
        fingerprint_data: 핑거프린트 데이터

    Returns:
        성공 여부
    """
    cache = get_cache()
    key = CacheKeys.device_fingerprint(device_id)
    return await cache.set_json(key, fingerprint_data, CacheTTL.DEVICE_FINGERPRINT)


async def get_cached_device_fingerprint(
    device_id: str,
) -> Optional[Dict[str, Any]]:
    """
    캐시된 디바이스 핑거프린트 조회

    Args:
        device_id: 디바이스 ID

    Returns:
        캐시된 핑거프린트 데이터 또는 None
    """
    cache = get_cache()
    key = CacheKeys.device_fingerprint(device_id)
    return await cache.get_json(key)


async def cache_network_analysis(
    ip_address: str, analysis_data: Dict[str, Any]
) -> bool:
    """
    네트워크 분석 결과 캐싱

    Args:
        ip_address: IP 주소
        analysis_data: 분석 결과 데이터

    Returns:
        성공 여부
    """
    cache = get_cache()
    key = CacheKeys.network_analysis(ip_address)
    return await cache.set_json(key, analysis_data, CacheTTL.NETWORK_ANALYSIS)


async def get_cached_network_analysis(
    ip_address: str,
) -> Optional[Dict[str, Any]]:
    """
    캐시된 네트워크 분석 결과 조회

    Args:
        ip_address: IP 주소

    Returns:
        캐시된 분석 결과 또는 None
    """
    cache = get_cache()
    key = CacheKeys.network_analysis(ip_address)
    return await cache.get_json(key)
