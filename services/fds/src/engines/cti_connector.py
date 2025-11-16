"""
CTI 커넥터 (Cyber Threat Intelligence Connector)

외부 CTI 소스(AbuseIPDB 등)와 연동하여 악성 IP, 이메일 도메인 등의
위협 정보를 조회하고 Redis에 캐싱합니다.

주요 기능:
1. AbuseIPDB API 연동 (IP 평판 조회)
2. 타임아웃 50ms 이내 응답 보장
3. Redis 캐싱으로 O(1) 조회 성능
4. 자체 블랙리스트와 통합 관리
"""

from typing import Optional, Dict, Any
import json
import os

import httpx
from redis import asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    ThreatIntelligence,
    ThreatType,
    ThreatLevel,
    ThreatSource,
)


class CTIConfig:
    """CTI 설정"""

    # AbuseIPDB API
    ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY", "")
    ABUSEIPDB_API_URL = "https://api.abuseipdb.com/api/v2/check"
    ABUSEIPDB_TIMEOUT = 0.05  # 50ms
    ABUSEIPDB_MAX_AGE_DAYS = 90  # 최근 90일 데이터만 조회

    # Redis 캐싱
    CACHE_TTL_CLEAN = 3600 * 24  # 24시간 (정상 IP)
    CACHE_TTL_SUSPICIOUS = 3600 * 12  # 12시간 (의심 IP)
    CACHE_TTL_MALICIOUS = 3600 * 24 * 7  # 7일 (악성 IP)

    # 위협 수준 임계값 (AbuseIPDB Confidence Score)
    THREAT_LEVEL_HIGH_THRESHOLD = 75  # 75% 이상: HIGH
    THREAT_LEVEL_MEDIUM_THRESHOLD = 25  # 25% 이상: MEDIUM


class CTICheckResult:
    """CTI 조회 결과"""

    def __init__(
        self,
        threat_type: ThreatType,
        value: str,
        is_threat: bool,
        threat_level: Optional[ThreatLevel] = None,
        source: Optional[ThreatSource] = None,
        confidence_score: int = 0,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.threat_type = threat_type
        self.value = value
        self.is_threat = is_threat
        self.threat_level = threat_level
        self.source = source
        self.confidence_score = confidence_score
        self.description = description
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "threat_type": self.threat_type.value if self.threat_type else None,
            "value": self.value,
            "is_threat": self.is_threat,
            "threat_level": self.threat_level.value if self.threat_level else None,
            "source": self.source.value if self.source else None,
            "confidence_score": self.confidence_score,
            "description": self.description,
            "metadata": self.metadata,
        }


class CTIConnector:
    """
    CTI 커넥터

    외부 CTI 소스와 자체 블랙리스트를 통합하여 위협 정보를 조회합니다.
    """

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        """
        Args:
            db: 데이터베이스 세션
            redis: Redis 클라이언트
        """
        self.db = db
        self.redis = redis
        self.http_client = httpx.AsyncClient(timeout=CTIConfig.ABUSEIPDB_TIMEOUT)

    async def close(self):
        """HTTP 클라이언트 종료"""
        await self.http_client.aclose()

    async def check_ip_threat(
        self,
        ip_address: str,
        use_cache: bool = True,
    ) -> CTICheckResult:
        """
        IP 주소의 위협 여부 확인

        조회 순서:
        1. Redis 캐시 확인
        2. 자체 블랙리스트(ThreatIntelligence 테이블) 확인
        3. AbuseIPDB API 조회
        4. Redis에 캐싱

        Args:
            ip_address: 조회할 IP 주소
            use_cache: Redis 캐시 사용 여부

        Returns:
            CTICheckResult: CTI 조회 결과
        """
        # 1. Redis 캐시 확인
        if use_cache:
            cached_result = await self._get_from_cache(ThreatType.IP, ip_address)
            if cached_result:
                return cached_result

        # 2. 자체 블랙리스트 확인
        internal_result = await self._check_internal_blacklist(
            ThreatType.IP, ip_address
        )
        if internal_result.is_threat:
            # 캐시에 저장
            await self._save_to_cache(internal_result)
            return internal_result

        # 3. AbuseIPDB API 조회 (타임아웃 50ms)
        abuseipdb_result = await self._check_abuseipdb(ip_address)
        if abuseipdb_result.is_threat:
            # 자체 블랙리스트에 추가
            await self._save_to_internal_blacklist(abuseipdb_result)

        # 4. 캐시에 저장
        await self._save_to_cache(abuseipdb_result)

        return abuseipdb_result

    async def check_email_domain_threat(
        self, email_domain: str, use_cache: bool = True
    ) -> CTICheckResult:
        """
        이메일 도메인의 위협 여부 확인

        Args:
            email_domain: 조회할 이메일 도메인
            use_cache: Redis 캐시 사용 여부

        Returns:
            CTICheckResult: CTI 조회 결과
        """
        # 1. Redis 캐시 확인
        if use_cache:
            cached_result = await self._get_from_cache(
                ThreatType.EMAIL_DOMAIN, email_domain
            )
            if cached_result:
                return cached_result

        # 2. 자체 블랙리스트 확인 (현재는 내부 블랙리스트만 지원)
        internal_result = await self._check_internal_blacklist(
            ThreatType.EMAIL_DOMAIN, email_domain
        )

        # 3. 캐시에 저장
        await self._save_to_cache(internal_result)

        return internal_result

    async def check_card_bin_threat(
        self, card_bin: str, use_cache: bool = True
    ) -> CTICheckResult:
        """
        카드 BIN의 위협 여부 확인

        Args:
            card_bin: 조회할 카드 BIN (처음 6자리)
            use_cache: Redis 캐시 사용 여부

        Returns:
            CTICheckResult: CTI 조회 결과
        """
        # 1. Redis 캐시 확인
        if use_cache:
            cached_result = await self._get_from_cache(ThreatType.CARD_BIN, card_bin)
            if cached_result:
                return cached_result

        # 2. 자체 블랙리스트 확인
        internal_result = await self._check_internal_blacklist(
            ThreatType.CARD_BIN, card_bin
        )

        # 3. 캐시에 저장
        await self._save_to_cache(internal_result)

        return internal_result

    async def _check_internal_blacklist(
        self, threat_type: ThreatType, value: str
    ) -> CTICheckResult:
        """
        자체 블랙리스트(ThreatIntelligence 테이블) 확인

        Args:
            threat_type: 위협 유형
            value: 조회할 값

        Returns:
            CTICheckResult: 조회 결과
        """
        stmt = select(ThreatIntelligence).where(
            ThreatIntelligence.threat_type == threat_type,
            ThreatIntelligence.value == value,
            ThreatIntelligence.is_active,
        )
        result = await self.db.execute(stmt)
        threat = result.scalar_one_or_none()

        if threat and not threat.is_expired:
            return CTICheckResult(
                threat_type=threat_type,
                value=value,
                is_threat=True,
                threat_level=threat.threat_level,
                source=threat.source,
                confidence_score=100,  # 내부 블랙리스트는 100% 신뢰
                description=threat.description,
                metadata=threat.metadata or {},
            )

        # 위협 없음
        return CTICheckResult(
            threat_type=threat_type,
            value=value,
            is_threat=False,
        )

    async def _check_abuseipdb(self, ip_address: str) -> CTICheckResult:
        """
        AbuseIPDB API로 IP 평판 조회

        Args:
            ip_address: 조회할 IP 주소

        Returns:
            CTICheckResult: 조회 결과
        """
        # API 키가 없으면 조회 생략
        if not CTIConfig.ABUSEIPDB_API_KEY:
            return CTICheckResult(
                threat_type=ThreatType.IP,
                value=ip_address,
                is_threat=False,
            )

        try:
            # AbuseIPDB API 호출 (타임아웃 50ms)
            response = await self.http_client.get(
                CTIConfig.ABUSEIPDB_API_URL,
                params={
                    "ipAddress": ip_address,
                    "maxAgeInDays": CTIConfig.ABUSEIPDB_MAX_AGE_DAYS,
                    "verbose": True,
                },
                headers={
                    "Key": CTIConfig.ABUSEIPDB_API_KEY,
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                # API 오류 시 안전하게 위협 없음으로 처리
                return CTICheckResult(
                    threat_type=ThreatType.IP,
                    value=ip_address,
                    is_threat=False,
                )

            data = response.json().get("data", {})
            abuse_confidence_score = data.get("abuseConfidenceScore", 0)
            is_whitelisted = data.get("isWhitelisted", False)

            # 화이트리스트면 안전
            if is_whitelisted:
                return CTICheckResult(
                    threat_type=ThreatType.IP,
                    value=ip_address,
                    is_threat=False,
                )

            # 위협 수준 판단
            threat_level = None
            is_threat = False

            if abuse_confidence_score >= CTIConfig.THREAT_LEVEL_HIGH_THRESHOLD:
                threat_level = ThreatLevel.HIGH
                is_threat = True
            elif abuse_confidence_score >= CTIConfig.THREAT_LEVEL_MEDIUM_THRESHOLD:
                threat_level = ThreatLevel.MEDIUM
                is_threat = True

            description = None
            if is_threat:
                total_reports = data.get("totalReports", 0)
                usage_type = data.get("usageType", "Unknown")
                description = (
                    f"AbuseIPDB 신뢰도 점수: {abuse_confidence_score}%, "
                    f"총 신고 횟수: {total_reports}, "
                    f"용도: {usage_type}"
                )

            return CTICheckResult(
                threat_type=ThreatType.IP,
                value=ip_address,
                is_threat=is_threat,
                threat_level=threat_level,
                source=ThreatSource.ABUSEIPDB,
                confidence_score=abuse_confidence_score,
                description=description,
                metadata={
                    "total_reports": data.get("totalReports", 0),
                    "num_distinct_users": data.get("numDistinctUsers", 0),
                    "last_reported_at": data.get("lastReportedAt"),
                    "usage_type": data.get("usageType"),
                    "country_code": data.get("countryCode"),
                    "domain": data.get("domain"),
                },
            )

        except (httpx.TimeoutException, httpx.HTTPError) as e:
            # 타임아웃 또는 네트워크 오류 시 안전하게 위협 없음으로 처리
            # (FDS 성능 목표 100ms를 지키기 위해)
            return CTICheckResult(
                threat_type=ThreatType.IP,
                value=ip_address,
                is_threat=False,
                metadata={"error": str(e), "fallback": True},
            )

    async def _save_to_internal_blacklist(self, result: CTICheckResult) -> None:
        """
        자체 블랙리스트(ThreatIntelligence 테이블)에 저장

        Args:
            result: CTI 조회 결과
        """
        if not result.is_threat:
            return

        # 이미 존재하는지 확인
        stmt = select(ThreatIntelligence).where(
            ThreatIntelligence.threat_type == result.threat_type,
            ThreatIntelligence.value == result.value,
        )
        existing = await self.db.execute(stmt)
        if existing.scalar_one_or_none():
            return  # 이미 존재하면 저장하지 않음

        # 새로 생성
        threat = ThreatIntelligence(
            threat_type=result.threat_type,
            value=result.value,
            threat_level=result.threat_level,
            source=result.source,
            description=result.description,
            metadata=result.metadata,
        )
        self.db.add(threat)
        await self.db.commit()

    async def _get_from_cache(
        self, threat_type: ThreatType, value: str
    ) -> Optional[CTICheckResult]:
        """
        Redis 캐시에서 조회

        Args:
            threat_type: 위협 유형
            value: 조회할 값

        Returns:
            Optional[CTICheckResult]: 캐시된 결과 (없으면 None)
        """
        redis_key = f"threat:{threat_type.value}:{value}"
        cached = await self.redis.get(redis_key)

        if not cached:
            return None

        # JSON 디코딩
        data = json.loads(cached)

        return CTICheckResult(
            threat_type=ThreatType(data["threat_type"]),
            value=data["value"],
            is_threat=data["is_threat"],
            threat_level=ThreatLevel(data["threat_level"])
            if data.get("threat_level")
            else None,
            source=ThreatSource(data["source"]) if data.get("source") else None,
            confidence_score=data.get("confidence_score", 0),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )

    async def _save_to_cache(self, result: CTICheckResult) -> None:
        """
        Redis 캐시에 저장

        Args:
            result: CTI 조회 결과
        """
        redis_key = f"threat:{result.threat_type.value}:{result.value}"

        # TTL 결정 (위협 수준에 따라)
        if result.is_threat:
            if result.threat_level == ThreatLevel.HIGH:
                ttl = CTIConfig.CACHE_TTL_MALICIOUS
            elif result.threat_level == ThreatLevel.MEDIUM:
                ttl = CTIConfig.CACHE_TTL_SUSPICIOUS
            else:
                ttl = CTIConfig.CACHE_TTL_CLEAN
        else:
            ttl = CTIConfig.CACHE_TTL_CLEAN

        # JSON 인코딩
        data = result.to_dict()

        # Redis에 저장
        await self.redis.setex(redis_key, ttl, json.dumps(data))

    async def get_statistics(self) -> Dict[str, Any]:
        """
        CTI 통계 조회

        Returns:
            Dict[str, Any]: CTI 통계 정보
        """
        # 위협 수준별 통계
        from sqlalchemy import func

        stmt = (
            select(
                ThreatIntelligence.threat_type,
                ThreatIntelligence.threat_level,
                func.count(ThreatIntelligence.id).label("count"),
            )
            .where(ThreatIntelligence.is_active)
            .group_by(ThreatIntelligence.threat_type, ThreatIntelligence.threat_level)
        )

        result = await self.db.execute(stmt)
        stats = result.all()

        return {
            "threats_by_type_and_level": [
                {
                    "threat_type": row.threat_type.value,
                    "threat_level": row.threat_level.value,
                    "count": row.count,
                }
                for row in stats
            ]
        }
