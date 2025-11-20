"""
Fingerprint Engine

디바이스 핑거프린팅 분석 및 검증 엔진
- 디바이스 ID 생성 (SHA-256)
- 타임존/언어 불일치 검사
- 디바이스 신뢰도 점수 계산
"""

import hashlib
import logging
from typing import Dict, Optional, Any
import pycountry

logger = logging.getLogger(__name__)


class FingerprintEngine:
    """디바이스 핑거프린팅 분석 엔진"""

    # 타임존과 언어 매핑 (일반적인 패턴)
    TIMEZONE_COUNTRY_MAP = {
        "Asia/Seoul": "KR",
        "Asia/Tokyo": "JP",
        "America/New_York": "US",
        "America/Los_Angeles": "US",
        "Europe/London": "GB",
        "Europe/Paris": "FR",
        "Australia/Sydney": "AU",
    }

    LANGUAGE_COUNTRY_MAP = {
        "ko": "KR",
        "ko-KR": "KR",
        "ja": "JP",
        "ja-JP": "JP",
        "en": "US",
        "en-US": "US",
        "en-GB": "GB",
        "fr": "FR",
        "fr-FR": "FR",
        "de": "DE",
        "de-DE": "DE",
        "zh": "CN",
        "zh-CN": "CN",
    }

    def __init__(self):
        """초기화"""
        pass

    def generate_device_id(
        self,
        canvas_hash: str,
        webgl_hash: str,
        audio_hash: str,
        cpu_cores: int,
        screen_resolution: str,
        timezone: str,
        language: str,
    ) -> str:
        """
        디바이스 ID 생성 (SHA-256)

        Args:
            canvas_hash: Canvas API 해시
            webgl_hash: WebGL API 해시
            audio_hash: Audio API 해시
            cpu_cores: CPU 코어 수
            screen_resolution: 화면 해상도
            timezone: 타임존
            language: 언어

        Returns:
            64자 SHA-256 해시 문자열
        """
        components = [
            canvas_hash,
            webgl_hash,
            audio_hash,
            str(cpu_cores),
            screen_resolution,
            timezone,
            language,
        ]
        combined = "|".join(components)
        device_id = hashlib.sha256(combined.encode()).hexdigest()

        logger.debug(f"Generated device ID: {device_id} from components: {components}")
        return device_id

    def get_country_from_timezone(self, timezone: str) -> Optional[str]:
        """
        타임존에서 국가 코드 추출

        Args:
            timezone: 타임존 (예: "Asia/Seoul")

        Returns:
            2자 국가 코드 (예: "KR") 또는 None
        """
        # 직접 매핑
        if timezone in self.TIMEZONE_COUNTRY_MAP:
            return self.TIMEZONE_COUNTRY_MAP[timezone]

        # pytz를 사용한 추론
        try:
            if "/" in timezone:
                parts = timezone.split("/")
                if len(parts) >= 2:
                    region = parts[0]
                    city = parts[1]

                    # 지역별 국가 추론
                    if region == "Asia":
                        if city in ["Seoul", "Pyongyang"]:
                            return "KR"
                        elif city in ["Tokyo", "Osaka"]:
                            return "JP"
                        elif city in ["Shanghai", "Beijing", "Hong_Kong"]:
                            return "CN"
                        elif city in ["Singapore"]:
                            return "SG"
                    elif region == "America":
                        if city in ["New_York", "Chicago", "Los_Angeles", "Denver"]:
                            return "US"
                        elif city in ["Toronto", "Vancouver"]:
                            return "CA"
                        elif city in ["Mexico_City"]:
                            return "MX"
                    elif region == "Europe":
                        if city in ["London", "Manchester"]:
                            return "GB"
                        elif city in ["Paris"]:
                            return "FR"
                        elif city in ["Berlin", "Munich"]:
                            return "DE"
                    elif region == "Australia":
                        return "AU"
        except Exception as e:
            logger.warning(f"Failed to infer country from timezone {timezone}: {e}")

        return None

    def get_country_from_language(self, language: str) -> Optional[str]:
        """
        언어에서 국가 코드 추출

        Args:
            language: 언어 코드 (예: "ko-KR", "en-US")

        Returns:
            2자 국가 코드 (예: "KR") 또는 None
        """
        # 직접 매핑
        if language in self.LANGUAGE_COUNTRY_MAP:
            return self.LANGUAGE_COUNTRY_MAP[language]

        # "ko-KR" 형식에서 국가 코드 추출
        if "-" in language:
            parts = language.split("-")
            if len(parts) == 2:
                country_code = parts[1].upper()
                # pycountry로 검증
                try:
                    if pycountry.countries.get(alpha_2=country_code):
                        return country_code
                except Exception:
                    pass

        return None

    def check_timezone_language_mismatch(
        self, timezone: str, language: str, geoip_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        타임존/언어 불일치 검사

        Args:
            timezone: 타임존 (예: "Asia/Seoul")
            language: 언어 코드 (예: "ko-KR")
            geoip_country: GeoIP로 탐지한 국가 코드 (선택)

        Returns:
            {
                "timezone_country": "KR",
                "language_country": "KR",
                "geoip_country": "US",
                "mismatch": True,
                "risk_score": 50,
                "reasons": ["Timezone/GeoIP mismatch: KR vs US"]
            }
        """
        timezone_country = self.get_country_from_timezone(timezone)
        language_country = self.get_country_from_language(language)

        reasons = []
        mismatch = False
        risk_score = 0

        # 타임존과 언어 불일치
        if (
            timezone_country
            and language_country
            and timezone_country != language_country
        ):
            mismatch = True
            risk_score += 30
            reasons.append(
                f"Timezone/Language mismatch: {timezone_country} vs {language_country}"
            )

        # GeoIP와 타임존 불일치
        if geoip_country and timezone_country and geoip_country != timezone_country:
            mismatch = True
            risk_score += 40
            reasons.append(
                f"Timezone/GeoIP mismatch: {timezone_country} vs {geoip_country}"
            )

        # GeoIP와 언어 불일치
        if geoip_country and language_country and geoip_country != language_country:
            mismatch = True
            risk_score += 20
            reasons.append(
                f"Language/GeoIP mismatch: {language_country} vs {geoip_country}"
            )

        # VPN/Proxy 의심 케이스 (3개 모두 다른 경우)
        if (
            timezone_country
            and language_country
            and geoip_country
            and len(set([timezone_country, language_country, geoip_country])) == 3
        ):
            risk_score += 30
            reasons.append("All three sources (Timezone/Language/GeoIP) mismatch")

        return {
            "timezone_country": timezone_country,
            "language_country": language_country,
            "geoip_country": geoip_country,
            "mismatch": mismatch,
            "risk_score": min(risk_score, 100),  # 최대 100
            "reasons": reasons,
        }

    def validate_fingerprint_consistency(
        self,
        canvas_hash: str,
        webgl_hash: str,
        audio_hash: str,
        user_agent: str,
    ) -> Dict[str, Any]:
        """
        핑거프린트 일관성 검증

        Args:
            canvas_hash: Canvas API 해시
            webgl_hash: WebGL API 해시
            audio_hash: Audio API 해시
            user_agent: User-Agent 문자열

        Returns:
            {
                "valid": True,
                "risk_score": 0,
                "issues": []
            }
        """
        issues = []
        risk_score = 0

        # 해시 값이 "not_supported" 또는 "error"인 경우
        if "not_supported" in canvas_hash or "error" in canvas_hash:
            issues.append("Canvas fingerprinting not supported or failed")
            risk_score += 20

        if "not_supported" in webgl_hash or "error" in webgl_hash:
            issues.append("WebGL fingerprinting not supported or failed")
            risk_score += 30

        if "not_supported" in audio_hash or "error" in audio_hash:
            issues.append("Audio fingerprinting not supported or failed")
            risk_score += 10

        # 해시 길이 검증 (SHA-256은 64자)
        if len(canvas_hash) != 64:
            issues.append(f"Invalid canvas hash length: {len(canvas_hash)}")
            risk_score += 10

        if len(webgl_hash) != 64:
            issues.append(f"Invalid WebGL hash length: {len(webgl_hash)}")
            risk_score += 10

        if len(audio_hash) != 64:
            issues.append(f"Invalid audio hash length: {len(audio_hash)}")
            risk_score += 10

        # User-Agent 검증
        if not user_agent or len(user_agent) < 10:
            issues.append("Invalid or missing User-Agent")
            risk_score += 20

        # 봇 탐지: Headless Chrome 등
        if "Headless" in user_agent or "PhantomJS" in user_agent:
            issues.append("Headless browser detected")
            risk_score += 60

        valid = len(issues) == 0

        return {
            "valid": valid,
            "risk_score": min(risk_score, 100),
            "issues": issues,
        }

    def calculate_device_trust_score(
        self,
        fingerprint_data: Dict[str, Any],
        is_blacklisted: bool = False,
        previous_fraud_count: int = 0,
    ) -> int:
        """
        디바이스 신뢰도 점수 계산 (0-100, 높을수록 신뢰)

        Args:
            fingerprint_data: 핑거프린트 데이터
            is_blacklisted: 블랙리스트 여부
            previous_fraud_count: 이전 사기 시도 횟수

        Returns:
            신뢰도 점수 (0-100)
        """
        trust_score = 100

        # 블랙리스트 등록 시 즉시 0점
        if is_blacklisted:
            return 0

        # 핑거프린트 일관성 검증
        consistency = self.validate_fingerprint_consistency(
            canvas_hash=fingerprint_data.get("canvas_hash", ""),
            webgl_hash=fingerprint_data.get("webgl_hash", ""),
            audio_hash=fingerprint_data.get("audio_hash", ""),
            user_agent=fingerprint_data.get("user_agent", ""),
        )
        trust_score -= consistency["risk_score"]

        # 타임존/언어 불일치 검사
        mismatch_result = self.check_timezone_language_mismatch(
            timezone=fingerprint_data.get("timezone", ""),
            language=fingerprint_data.get("language", ""),
            geoip_country=fingerprint_data.get("geoip_country"),
        )
        trust_score -= mismatch_result["risk_score"]

        # 이전 사기 시도 패널티
        trust_score -= min(previous_fraud_count * 10, 50)

        return max(trust_score, 0)
