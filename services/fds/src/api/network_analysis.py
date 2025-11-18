"""
네트워크 분석 API

IP 주소 분석, TOR/VPN/Proxy 탐지, GeoIP 조회 등을 제공한다.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session
from src.engines.network_analysis_engine import NetworkAnalysisEngine
from src.models.network_analysis import NetworkAnalysis
from src.utils.cache_utils import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/fds/network-analysis", tags=["Network Analysis"])


# Pydantic 스키마
class NetworkAnalysisRequest(BaseModel):
    """네트워크 분석 요청"""

    transaction_id: UUID = Field(..., description="거래 ID")
    ip_address: str = Field(..., description="분석할 IP 주소")
    billing_country: Optional[str] = Field(None, description="결제 카드 발급국 (ISO 2자리 코드)")

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v):
        """IP 주소 유효성 검증"""
        import ipaddress

        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("Invalid IP address format")
        return v

    @field_validator("billing_country")
    @classmethod
    def validate_billing_country(cls, v):
        """국가 코드 유효성 검증"""
        if v and len(v) != 2:
            raise ValueError("Country code must be 2 characters (ISO 3166-1 alpha-2)")
        return v.upper() if v else None


class NetworkAnalysisResponse(BaseModel):
    """네트워크 분석 응답"""

    transaction_id: UUID
    ip_address: str
    geoip_country: Optional[str] = None
    geoip_city: Optional[str] = None
    asn: Optional[int] = None
    asn_organization: Optional[str] = None
    is_tor: bool = False
    is_vpn: bool = False
    is_proxy: bool = False
    dns_ptr_record: Optional[str] = None
    country_mismatch: bool = False
    risk_score: int = Field(..., ge=0, le=100)

    class Config:
        from_attributes = True


# 네트워크 분석 엔진 싱글톤
_network_engine: Optional[NetworkAnalysisEngine] = None


def get_network_engine() -> NetworkAnalysisEngine:
    """네트워크 분석 엔진 싱글톤 가져오기"""
    global _network_engine
    if _network_engine is None:
        _network_engine = NetworkAnalysisEngine()
    return _network_engine


@router.post(
    "",
    response_model=NetworkAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="네트워크 분석 수행",
    description="IP 주소 분석, TOR/VPN/Proxy 탐지, GeoIP 조회, 국가 불일치 검사를 수행한다.",
)
async def analyze_network(
    request: NetworkAnalysisRequest,
    db_session: AsyncSession = Depends(get_db_session),
    network_engine: NetworkAnalysisEngine = Depends(get_network_engine),
):
    """
    네트워크 분석 수행

    **분석 내용**:
    - TOR Exit Node 확인
    - GeoIP 조회 (국가, 도시)
    - ASN 조회 및 VPN 판정
    - DNS PTR 역방향 조회 및 프록시 판정
    - 국가 불일치 검사
    - 위험 점수 계산 (0-100)

    **점수 체계**:
    - TOR 사용: +50점
    - VPN 사용: +30점
    - Proxy 사용: +20점
    - 국가 불일치: +40점
    """
    try:
        # 1. Redis 캐시 확인 (T047에서 구현)
        redis_client = await get_redis()
        cache_key = f"network_analysis:{request.ip_address}"

        # 캐시된 결과 확인
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            logger.info(f"Network analysis cache hit for IP: {request.ip_address}")
            # 캐시된 결과를 JSON으로 파싱
            import json

            cached_data = json.loads(cached_result)

            # transaction_id는 요청마다 다르므로 업데이트
            cached_data["transaction_id"] = str(request.transaction_id)

            # DB에 저장
            network_analysis = NetworkAnalysis(
                transaction_id=request.transaction_id,
                ip_address=cached_data["ip_address"],
                geoip_country=cached_data.get("geoip_country"),
                geoip_city=cached_data.get("geoip_city"),
                asn=cached_data.get("asn"),
                asn_organization=cached_data.get("asn_organization"),
                is_tor=cached_data.get("is_tor", False),
                is_vpn=cached_data.get("is_vpn", False),
                is_proxy=cached_data.get("is_proxy", False),
                dns_ptr_record=cached_data.get("dns_ptr_record"),
                country_mismatch=cached_data.get("country_mismatch", False),
                risk_score=cached_data.get("risk_score", 0),
            )
            db_session.add(network_analysis)
            await db_session.commit()
            await db_session.refresh(network_analysis)

            return NetworkAnalysisResponse.model_validate(network_analysis)

        # 2. 네트워크 분석 수행
        logger.info(f"Analyzing network for IP: {request.ip_address}")
        analysis_result = await network_engine.analyze_network(
            ip_address=request.ip_address, billing_country=request.billing_country
        )

        # 3. 데이터베이스에 저장
        network_analysis = NetworkAnalysis(
            transaction_id=request.transaction_id,
            ip_address=analysis_result["ip_address"],
            geoip_country=analysis_result["geoip_country"],
            geoip_city=analysis_result["geoip_city"],
            asn=analysis_result["asn"],
            asn_organization=analysis_result["asn_organization"],
            is_tor=analysis_result["is_tor"],
            is_vpn=analysis_result["is_vpn"],
            is_proxy=analysis_result["is_proxy"],
            dns_ptr_record=analysis_result["dns_ptr_record"],
            country_mismatch=analysis_result["country_mismatch"],
            risk_score=analysis_result["risk_score"],
        )

        db_session.add(network_analysis)
        await db_session.commit()
        await db_session.refresh(network_analysis)

        # 4. Redis 캐시에 저장 (TTL 1시간)
        import json

        cache_data = {
            "ip_address": analysis_result["ip_address"],
            "geoip_country": analysis_result["geoip_country"],
            "geoip_city": analysis_result["geoip_city"],
            "asn": analysis_result["asn"],
            "asn_organization": analysis_result["asn_organization"],
            "is_tor": analysis_result["is_tor"],
            "is_vpn": analysis_result["is_vpn"],
            "is_proxy": analysis_result["is_proxy"],
            "dns_ptr_record": analysis_result["dns_ptr_record"],
            "country_mismatch": analysis_result["country_mismatch"],
            "risk_score": analysis_result["risk_score"],
        }
        await redis_client.setex(cache_key, 3600, json.dumps(cache_data))  # 1시간 = 3600초

        logger.info(
            f"Network analysis completed for IP {request.ip_address}: "
            f"TOR={analysis_result['is_tor']}, "
            f"VPN={analysis_result['is_vpn']}, "
            f"Proxy={analysis_result['is_proxy']}, "
            f"Risk={analysis_result['risk_score']}"
        )

        return NetworkAnalysisResponse.model_validate(network_analysis)

    except ValueError as e:
        logger.error(f"Validation error in network analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error analyzing network: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze network",
        )


@router.get(
    "/{transaction_id}",
    response_model=NetworkAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="네트워크 분석 결과 조회",
    description="특정 거래의 네트워크 분석 결과를 조회한다.",
)
async def get_network_analysis(
    transaction_id: UUID, db_session: AsyncSession = Depends(get_db_session)
):
    """
    네트워크 분석 결과 조회

    거래 ID로 이전에 수행한 네트워크 분석 결과를 조회한다.
    """
    try:
        from sqlalchemy import select

        # 네트워크 분석 결과 조회
        stmt = select(NetworkAnalysis).where(
            NetworkAnalysis.transaction_id == transaction_id
        )
        result = await db_session.execute(stmt)
        network_analysis = result.scalar_one_or_none()

        if not network_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Network analysis not found for transaction: {transaction_id}",
            )

        return NetworkAnalysisResponse.model_validate(network_analysis)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching network analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch network analysis",
        )
