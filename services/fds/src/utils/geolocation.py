"""
지리적 위치 유틸리티

IP 주소 기반 지리적 위치 확인 및 거리 계산 기능을 제공합니다.
"""

from typing import Optional, Dict, Any, Tuple
import math


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    두 지점 간의 거리를 계산 (Haversine 공식 사용)

    Args:
        lat1: 첫 번째 지점의 위도
        lon1: 첫 번째 지점의 경도
        lat2: 두 번째 지점의 위도
        lon2: 두 번째 지점의 경도

    Returns:
        float: 거리 (킬로미터)

    참고:
        Haversine 공식은 지구를 완전한 구로 가정하므로,
        실제 거리와 약간의 오차가 있을 수 있습니다 (±0.5% 이내).
    """
    # 지구 반지름 (킬로미터)
    R = 6371.0

    # 라디안으로 변환
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # 위도/경도 차이
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine 공식
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c

    return distance


def parse_geolocation(
    geolocation: Optional[Dict[str, Any]]
) -> Optional[Tuple[float, float]]:
    """
    지리적 위치 딕셔너리에서 위도/경도 추출

    Args:
        geolocation: 지리적 위치 정보 (예: {"lat": 37.5, "lon": 127.0})

    Returns:
        Optional[Tuple[float, float]]: (위도, 경도) 또는 None
    """
    if not geolocation:
        return None

    lat = geolocation.get("lat") or geolocation.get("latitude")
    lon = geolocation.get("lon") or geolocation.get("longitude")

    if lat is None or lon is None:
        return None

    try:
        return float(lat), float(lon)
    except (ValueError, TypeError):
        return None


def get_region_name(geolocation: Optional[Dict[str, Any]]) -> str:
    """
    지리적 위치에서 지역명 추출

    Args:
        geolocation: 지리적 위치 정보

    Returns:
        str: 지역명 (예: "서울", "부산")
    """
    if not geolocation:
        return "알 수 없음"

    # 우선순위: city > region > country
    city = geolocation.get("city")
    if city:
        return city

    region = geolocation.get("region")
    if region:
        return region

    country = geolocation.get("country")
    if country:
        return country

    return "알 수 없음"


async def get_ip_geolocation(ip_address: str) -> Optional[Dict[str, Any]]:
    """
    IP 주소로부터 지리적 위치 정보 조회

    Args:
        ip_address: IP 주소

    Returns:
        Optional[Dict[str, Any]]: 지리적 위치 정보 또는 None

    Note:
        실제 구현 시 GeoIP2, ip-api.com 등의 서비스를 사용해야 합니다.
        현재는 샘플 데이터를 반환합니다.
    """
    # TODO: 실제 GeoIP 서비스 연동
    # 예: MaxMind GeoIP2, ip-api.com, ipinfo.io 등

    # 샘플 데이터 (서울)
    return {
        "country": "KR",
        "city": "서울",
        "region": "Seoul",
        "lat": 37.5665,
        "lon": 126.9780,
    }
