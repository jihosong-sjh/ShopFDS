"""
네트워크 분석 엔진

TOR/VPN/Proxy 탐지, GeoIP 분석, ASN 평판 조회, DNS PTR 조회 등
네트워크 수준의 사기 패턴을 탐지한다.
"""

import asyncio
import ipaddress
import logging
import socket
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set
from urllib.request import urlopen

import geoip2.database
import geoip2.errors

logger = logging.getLogger(__name__)


class NetworkAnalysisEngine:
    """네트워크 분석 종합 엔진"""

    def __init__(
        self,
        geoip_db_path: str = "/usr/share/GeoIP/GeoLite2-City.mmdb",
        asn_db_path: str = "/usr/share/GeoIP/GeoLite2-ASN.mmdb",
    ):
        """
        Args:
            geoip_db_path: MaxMind GeoIP2 City 데이터베이스 경로
            asn_db_path: MaxMind GeoIP2 ASN 데이터베이스 경로
        """
        self.geoip_db_path = geoip_db_path
        self.asn_db_path = asn_db_path

        # TOR Exit Node 캐시 (메모리)
        self.tor_exit_nodes: Set[str] = set()
        self.tor_list_last_updated: Optional[datetime] = None
        self.tor_list_update_interval = timedelta(hours=1)

        # GeoIP Reader (lazy loading)
        self._geoip_reader: Optional[geoip2.database.Reader] = None
        self._asn_reader: Optional[geoip2.database.Reader] = None

        # 알려진 VPN/프록시 ASN (예시 - 실제로는 DB나 외부 서비스 사용)
        self.vpn_asn_list = {
            13335,  # Cloudflare
            16509,  # AWS
            15169,  # Google Cloud
            8075,  # Microsoft Azure
            14061,  # DigitalOcean
            20473,  # AS-CHOOPA (Vultr)
            # 상용 VPN 서비스
            62371,  # NordVPN
            9009,  # ExpressVPN
            # 더 많은 VPN ASN 추가 가능
        }

        # 프록시 키워드 (DNS PTR 레코드에서 탐지)
        self.proxy_keywords = [
            "proxy",
            "vpn",
            "tor",
            "exit",
            "relay",
            "anonymizer",
            "privacy",
            "hide",
            "mask",
        ]

    @property
    def geoip_reader(self) -> geoip2.database.Reader:
        """GeoIP Reader (lazy loading)"""
        if self._geoip_reader is None:
            try:
                self._geoip_reader = geoip2.database.Reader(self.geoip_db_path)
                logger.info(f"GeoIP database loaded: {self.geoip_db_path}")
            except Exception as e:
                logger.error(f"Failed to load GeoIP database: {e}")
                raise
        return self._geoip_reader

    @property
    def asn_reader(self) -> geoip2.database.Reader:
        """ASN Reader (lazy loading)"""
        if self._asn_reader is None:
            try:
                self._asn_reader = geoip2.database.Reader(self.asn_db_path)
                logger.info(f"ASN database loaded: {self.asn_db_path}")
            except Exception as e:
                logger.error(f"Failed to load ASN database: {e}")
                raise
        return self._asn_reader

    async def load_tor_exit_nodes(self) -> None:
        """
        TOR Exit Node 리스트를 다운로드하여 메모리에 캐시한다.

        데이터 소스: https://check.torproject.org/torbulkexitlist
        업데이트 주기: 1시간
        """
        now = datetime.utcnow()

        # 캐시가 유효하면 스킵
        if (
            self.tor_list_last_updated
            and now - self.tor_list_last_updated < self.tor_list_update_interval
        ):
            logger.debug("TOR exit node list is up-to-date")
            return

        try:
            logger.info("Downloading TOR exit node list...")
            # 비동기로 다운로드 (asyncio.to_thread 사용)
            tor_list_url = "https://check.torproject.org/torbulkexitlist"
            response = await asyncio.to_thread(urlopen, tor_list_url, timeout=10)
            content = response.read().decode("utf-8")

            # IP 주소 파싱
            tor_ips = set()
            for line in content.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    # IP 주소 유효성 검사
                    try:
                        ipaddress.ip_address(line)
                        tor_ips.add(line)
                    except ValueError:
                        logger.warning(f"Invalid IP in TOR list: {line}")
                        continue

            self.tor_exit_nodes = tor_ips
            self.tor_list_last_updated = now
            logger.info(f"TOR exit node list updated: {len(tor_ips)} nodes")

        except Exception as e:
            logger.error(f"Failed to load TOR exit node list: {e}")
            # 기존 캐시 유지 (실패해도 계속 작동)

    def is_tor_exit_node(self, ip_address: str) -> bool:
        """
        주어진 IP가 TOR Exit Node인지 확인한다.

        Args:
            ip_address: 확인할 IP 주소

        Returns:
            TOR Exit Node 여부
        """
        return ip_address in self.tor_exit_nodes

    def get_geoip_info(self, ip_address: str) -> Dict[str, Any]:
        """
        GeoIP 데이터베이스에서 IP의 지리적 정보를 조회한다.

        Args:
            ip_address: 조회할 IP 주소

        Returns:
            {
                "country": "KR",
                "city": "Seoul",
                "latitude": 37.5665,
                "longitude": 126.9780,
                "accuracy_radius": 100
            }
        """
        try:
            response = self.geoip_reader.city(ip_address)
            return {
                "country": response.country.iso_code,
                "city": response.city.name,
                "latitude": response.location.latitude,
                "longitude": response.location.longitude,
                "accuracy_radius": response.location.accuracy_radius,
            }
        except geoip2.errors.AddressNotFoundError:
            logger.warning(f"GeoIP not found for IP: {ip_address}")
            return {
                "country": None,
                "city": None,
                "latitude": None,
                "longitude": None,
                "accuracy_radius": None,
            }
        except Exception as e:
            logger.error(f"GeoIP lookup failed for {ip_address}: {e}")
            return {
                "country": None,
                "city": None,
                "latitude": None,
                "longitude": None,
                "accuracy_radius": None,
            }

    def get_asn_info(self, ip_address: str) -> Dict[str, Any]:
        """
        ASN (Autonomous System Number) 정보를 조회한다.

        Args:
            ip_address: 조회할 IP 주소

        Returns:
            {
                "asn": 13335,
                "organization": "Cloudflare, Inc."
            }
        """
        try:
            response = self.asn_reader.asn(ip_address)
            return {
                "asn": response.autonomous_system_number,
                "organization": response.autonomous_system_organization,
            }
        except geoip2.errors.AddressNotFoundError:
            logger.warning(f"ASN not found for IP: {ip_address}")
            return {"asn": None, "organization": None}
        except Exception as e:
            logger.error(f"ASN lookup failed for {ip_address}: {e}")
            return {"asn": None, "organization": None}

    def is_vpn_or_proxy_asn(self, asn: Optional[int]) -> bool:
        """
        ASN이 VPN/프록시 서비스에 속하는지 확인한다.

        Args:
            asn: AS 번호

        Returns:
            VPN/프록시 ASN 여부
        """
        if asn is None:
            return False
        return asn in self.vpn_asn_list

    async def get_dns_ptr_record(self, ip_address: str) -> Optional[str]:
        """
        DNS PTR 역방향 조회를 수행한다.

        Args:
            ip_address: 조회할 IP 주소

        Returns:
            PTR 레코드 (호스트명) 또는 None
        """
        try:
            # 비동기로 DNS 조회 (asyncio.to_thread 사용)
            hostname = await asyncio.to_thread(
                socket.gethostbyaddr, ip_address, timeout=5
            )
            ptr_record = hostname[0]
            logger.debug(f"DNS PTR for {ip_address}: {ptr_record}")
            return ptr_record
        except socket.herror:
            logger.debug(f"No PTR record for IP: {ip_address}")
            return None
        except socket.timeout:
            logger.warning(f"DNS PTR lookup timeout for IP: {ip_address}")
            return None
        except Exception as e:
            logger.error(f"DNS PTR lookup failed for {ip_address}: {e}")
            return None

    def is_proxy_hostname(self, hostname: Optional[str]) -> bool:
        """
        호스트명에 프록시 관련 키워드가 포함되어 있는지 확인한다.

        Args:
            hostname: 확인할 호스트명

        Returns:
            프록시 키워드 포함 여부
        """
        if not hostname:
            return False

        hostname_lower = hostname.lower()
        for keyword in self.proxy_keywords:
            if keyword in hostname_lower:
                logger.info(f"Proxy keyword '{keyword}' found in hostname: {hostname}")
                return True
        return False

    def check_country_mismatch(
        self, geoip_country: Optional[str], billing_country: Optional[str]
    ) -> bool:
        """
        GeoIP 국가와 결제 카드 발급국이 일치하는지 확인한다.

        Args:
            geoip_country: GeoIP로 탐지된 국가 코드 (ISO 2자리)
            billing_country: 결제 카드 발급국 코드 (ISO 2자리)

        Returns:
            국가 불일치 여부 (True: 불일치, False: 일치)
        """
        if not geoip_country or not billing_country:
            return False

        # 대소문자 구분 없이 비교
        return geoip_country.upper() != billing_country.upper()

    def calculate_network_risk_score(
        self, is_tor: bool, is_vpn: bool, is_proxy: bool, country_mismatch: bool
    ) -> int:
        """
        네트워크 분석 결과를 종합하여 위험 점수를 계산한다.

        점수 체계:
        - TOR 사용: +50점
        - VPN 사용: +30점
        - Proxy 사용: +20점
        - 국가 불일치: +40점

        Args:
            is_tor: TOR 사용 여부
            is_vpn: VPN 사용 여부
            is_proxy: 프록시 사용 여부
            country_mismatch: 국가 불일치 여부

        Returns:
            위험 점수 (0-100)
        """
        score = 0

        if is_tor:
            score += 50
        if is_vpn:
            score += 30
        if is_proxy:
            score += 20
        if country_mismatch:
            score += 40

        # 최대 100점으로 제한
        return min(score, 100)

    async def analyze_network(
        self, ip_address: str, billing_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        네트워크 분석을 종합적으로 수행한다.

        이 메서드는 다음을 수행한다:
        1. TOR Exit Node 확인
        2. GeoIP 조회
        3. ASN 조회 및 VPN 판정
        4. DNS PTR 역방향 조회 및 프록시 판정
        5. 국가 불일치 검사
        6. 위험 점수 계산

        Args:
            ip_address: 분석할 IP 주소
            billing_country: 결제 카드 발급국 (선택)

        Returns:
            {
                "ip_address": "1.2.3.4",
                "geoip_country": "KR",
                "geoip_city": "Seoul",
                "asn": 13335,
                "asn_organization": "Cloudflare",
                "is_tor": False,
                "is_vpn": False,
                "is_proxy": False,
                "dns_ptr_record": "example.com",
                "country_mismatch": False,
                "risk_score": 0
            }
        """
        # 1. TOR Exit Node 리스트 업데이트 (비동기)
        await self.load_tor_exit_nodes()

        # 2. TOR 확인
        is_tor = self.is_tor_exit_node(ip_address)

        # 3. GeoIP 조회
        geoip_info = self.get_geoip_info(ip_address)
        geoip_country = geoip_info["country"]
        geoip_city = geoip_info["city"]

        # 4. ASN 조회
        asn_info = self.get_asn_info(ip_address)
        asn = asn_info["asn"]
        asn_organization = asn_info["organization"]

        # 5. VPN 판정 (ASN 기반)
        is_vpn = self.is_vpn_or_proxy_asn(asn)

        # 6. DNS PTR 역방향 조회 (비동기)
        dns_ptr_record = await self.get_dns_ptr_record(ip_address)

        # 7. 프록시 판정 (호스트명 기반)
        is_proxy = self.is_proxy_hostname(dns_ptr_record)

        # 8. 국가 불일치 검사
        country_mismatch = self.check_country_mismatch(geoip_country, billing_country)

        # 9. 위험 점수 계산
        risk_score = self.calculate_network_risk_score(
            is_tor, is_vpn, is_proxy, country_mismatch
        )

        return {
            "ip_address": ip_address,
            "geoip_country": geoip_country,
            "geoip_city": geoip_city,
            "asn": asn,
            "asn_organization": asn_organization,
            "is_tor": is_tor,
            "is_vpn": is_vpn,
            "is_proxy": is_proxy,
            "dns_ptr_record": dns_ptr_record,
            "country_mismatch": country_mismatch,
            "risk_score": risk_score,
        }

    def close(self):
        """데이터베이스 리더 종료"""
        if self._geoip_reader:
            self._geoip_reader.close()
            logger.info("GeoIP reader closed")
        if self._asn_reader:
            self._asn_reader.close()
            logger.info("ASN reader closed")
