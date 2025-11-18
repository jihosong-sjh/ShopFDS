"""
외부 API 공통 클라이언트

EmailRep, Numverify, BIN Database, HaveIBeenPwned 등 외부 API 호출을 위한 공통 클라이언트입니다.
"""

import asyncio
import time
from typing import Optional, Dict, Any
import aiohttp
from src.models.external_service_log import ServiceName
from src.utils.cache_utils import get_cache, CacheKeys, CacheTTL


class ExternalAPIClient:
    """
    외부 API 호출을 위한 공통 클라이언트

    Features:
    - 비동기 HTTP 요청
    - 타임아웃 처리 (기본 5초)
    - 재시도 로직 (최대 3회, 지수 백오프)
    - 응답 캐싱 (Redis)
    - 에러 로깅
    """

    def __init__(
        self,
        timeout: int = 5,
        max_retries: int = 3,
        enable_cache: bool = True,
    ):
        """
        Args:
            timeout: 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
            enable_cache: 캐싱 활성화 여부
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_cache = enable_cache
        self.cache = get_cache() if enable_cache else None
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """비동기 HTTP 세션 가져오기 (싱글톤)"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """HTTP 세션 종료"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        HTTP 요청 실행 (재시도 로직 포함)

        Args:
            method: HTTP 메서드 (GET, POST 등)
            url: 요청 URL
            headers: 요청 헤더
            params: 쿼리 파라미터
            json_data: JSON 요청 본문

        Returns:
            응답 데이터 (딕셔너리)

        Raises:
            aiohttp.ClientError: HTTP 요청 실패 시
            asyncio.TimeoutError: 타임아웃 시
        """
        session = await self._get_session()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_data,
                ) as response:
                    response.raise_for_status()
                    return await response.json()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # 지수 백오프 (1초, 2초, 4초)
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    raise

        raise last_error

    async def call_api(
        self,
        service_name: ServiceName,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        cache_ttl: Optional[int] = None,
        transaction_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        외부 API 호출 (캐싱 및 로깅 포함)

        Args:
            service_name: 서비스 이름 (예: ServiceName.EMAILREP)
            url: API URL
            method: HTTP 메서드
            headers: 요청 헤더
            params: 쿼리 파라미터
            json_data: JSON 요청 본문
            cache_ttl: 캐시 TTL (초), None이면 기본값 사용
            transaction_id: 관련 거래 ID (로깅용)

        Returns:
            API 응답 데이터

        Raises:
            Exception: API 호출 실패 시
        """
        # 캐시 키 생성 (URL + params 해시)
        import hashlib
        import json as json_lib

        request_hash = hashlib.md5(
            f"{url}:{json_lib.dumps(params or {}, sort_keys=True)}".encode()
        ).hexdigest()

        cache_key = CacheKeys.external_api(service_name.value, request_hash)

        # 캐시 조회
        if self.enable_cache and self.cache:
            cached_response = await self.cache.get_json(cache_key)
            if cached_response:
                return cached_response

        # API 호출
        start_time = time.time()
        status_code = None
        error_message = None

        try:
            response_data = await self._make_request(
                method, url, headers, params, json_data
            )
            status_code = 200
            response_time_ms = int((time.time() - start_time) * 1000)

            # 캐시 저장
            if self.enable_cache and self.cache:
                ttl = cache_ttl or CacheTTL.EXTERNAL_API
                await self.cache.set_json(cache_key, response_data, ttl)

            # 로그 저장 (비동기로 실행, 에러 무시)
            asyncio.create_task(
                self._log_api_call(
                    service_name,
                    {"url": url, "method": method, "params": params},
                    response_data,
                    response_time_ms,
                    status_code,
                    error_message,
                    transaction_id,
                )
            )

            return response_data

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)
            status_code = getattr(e, "status", 500) if hasattr(e, "status") else 500

            # 로그 저장 (에러 포함)
            asyncio.create_task(
                self._log_api_call(
                    service_name,
                    {"url": url, "method": method, "params": params},
                    None,
                    response_time_ms,
                    status_code,
                    error_message,
                    transaction_id,
                )
            )

            raise

    async def _log_api_call(
        self,
        service_name: ServiceName,
        request_data: Dict[str, Any],
        response_data: Optional[Dict[str, Any]],
        response_time_ms: int,
        status_code: Optional[int],
        error_message: Optional[str],
        transaction_id: Optional[str],
    ) -> None:
        """
        외부 API 호출 로그 저장

        Args:
            service_name: 서비스 이름
            request_data: 요청 데이터
            response_data: 응답 데이터
            response_time_ms: 응답 시간 (밀리초)
            status_code: HTTP 상태 코드
            error_message: 에러 메시지
            transaction_id: 거래 ID
        """
        try:
            from src.models import ExternalServiceLog
            from src.models.base import AsyncSessionLocal
            from uuid import UUID

            async with AsyncSessionLocal() as session:
                log = ExternalServiceLog(
                    service_name=service_name,
                    request_data=request_data,
                    response_data=response_data,
                    response_time_ms=response_time_ms,
                    status_code=status_code,
                    error_message=error_message,
                    transaction_id=UUID(transaction_id) if transaction_id else None,
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            # 로깅 실패는 무시 (원본 API 호출에 영향 없음)
            print(f"[WARN] Failed to log external API call: {e}")


# 싱글톤 인스턴스
_client_instance: Optional[ExternalAPIClient] = None


def get_external_api_client() -> ExternalAPIClient:
    """
    외부 API 클라이언트 싱글톤 인스턴스 가져오기

    Returns:
        ExternalAPIClient 인스턴스
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = ExternalAPIClient()
    return _client_instance


# Fail-Open 래퍼 (외부 API 실패 시에도 서비스 계속 진행)
async def safe_call_api(
    service_name: ServiceName,
    url: str,
    fallback_value: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Optional[Dict[str, Any]]:
    """
    외부 API 호출 (Fail-Open)

    외부 API 호출이 실패하더라도 예외를 발생시키지 않고 fallback 값을 반환합니다.
    FDS 서비스가 외부 API 장애에 영향받지 않도록 보장합니다.

    Args:
        service_name: 서비스 이름
        url: API URL
        fallback_value: 실패 시 반환할 기본값
        **kwargs: call_api에 전달할 추가 인자

    Returns:
        API 응답 또는 fallback 값
    """
    client = get_external_api_client()
    try:
        return await client.call_api(service_name, url, **kwargs)
    except Exception as e:
        print(f"[WARN] External API call failed ({service_name.value}): {e}")
        print("[INFO] Using fallback value (Fail-Open policy)")
        return fallback_value or {"error": str(e), "fallback": True}
