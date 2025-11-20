"""
BIN Database API Integration Service

BIN (Bank Identification Number) Database provides card issuer information.
API: https://binlist.net/
"""

import os
import logging
from typing import Dict, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class BINService:
    """BIN Database API client for card issuer lookup"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize BIN service

        Args:
            api_key: BINList API key (optional for free tier, 10 requests/minute)
        """
        self.api_key = api_key or os.getenv("BINLIST_API_KEY")
        self.base_url = "https://lookup.binlist.net"
        self.timeout = 5.0  # 5 seconds timeout

    async def lookup_bin(self, bin_number: str) -> Dict:
        """
        Lookup card BIN information

        Args:
            bin_number: First 6-8 digits of card number (BIN/IIN)

        Returns:
            Dict with BIN data:
            {
                "bin": str,  # BIN number
                "scheme": "visa" | "mastercard" | "amex" | "discover" | "jcb" | "unknown",
                "type": "debit" | "credit" | "prepaid" | "unknown",
                "brand": str,  # Card brand/product name
                "prepaid": bool,
                "country": {
                    "alpha2": str,  # e.g., "US", "KR"
                    "name": str,
                    "currency": str  # e.g., "USD", "KRW"
                },
                "bank": {
                    "name": str,
                    "url": str,
                    "phone": str,
                    "city": str
                },
                "risk_score": int,  # 0-100 (calculated)
                "raw_response": Dict
            }

        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If BIN format is invalid
        """
        # Validate BIN format (6-8 digits)
        if not bin_number or not bin_number.isdigit():
            raise ValueError(f"Invalid BIN format: {bin_number}")

        if len(bin_number) < 6 or len(bin_number) > 8:
            raise ValueError(f"BIN must be 6-8 digits, got: {len(bin_number)}")

        # Use first 6 digits for lookup (most common)
        bin_prefix = bin_number[:6]

        headers = {"Accept-Version": "3"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}/{bin_prefix}"

        logger.info(f"[BINList] Looking up BIN: {bin_prefix}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

            # Parse response
            result = {
                "bin": bin_prefix,
                "scheme": data.get("scheme", "unknown"),
                "type": data.get("type", "unknown"),
                "brand": data.get("brand", ""),
                "prepaid": data.get("prepaid", False),
                "country": {
                    "alpha2": data.get("country", {}).get("alpha2", ""),
                    "name": data.get("country", {}).get("name", ""),
                    "currency": data.get("country", {}).get("currency", ""),
                },
                "bank": {
                    "name": data.get("bank", {}).get("name", ""),
                    "url": data.get("bank", {}).get("url", ""),
                    "phone": data.get("bank", {}).get("phone", ""),
                    "city": data.get("bank", {}).get("city", ""),
                },
                "raw_response": data,
                "checked_at": datetime.utcnow().isoformat(),
            }

            # Calculate risk score
            result["risk_score"] = self.calculate_risk_score(result)

            logger.info(
                f"[BINList] BIN lookup: scheme={result['scheme']}, "
                f"type={result['type']}, country={result['country']['alpha2']}, "
                f"risk_score={result['risk_score']}"
            )

            return result

        except httpx.TimeoutException:
            logger.error(f"[BINList] Timeout looking up BIN: {bin_prefix}")
            raise

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # BIN not found
                logger.warning(f"[BINList] BIN not found: {bin_prefix}")
                return {
                    "bin": bin_prefix,
                    "scheme": "unknown",
                    "type": "unknown",
                    "brand": "",
                    "prepaid": False,
                    "country": {"alpha2": "", "name": "", "currency": ""},
                    "bank": {"name": "", "url": "", "phone": "", "city": ""},
                    "risk_score": 50,  # Unknown BIN is medium risk
                    "raw_response": {},
                    "checked_at": datetime.utcnow().isoformat(),
                }
            elif e.response.status_code == 429:
                # Rate limit exceeded
                logger.error("[BINList] Rate limit exceeded")
                raise ValueError("BINList API rate limit exceeded")
            else:
                logger.error(
                    f"[BINList] HTTP error {e.response.status_code}: {e.response.text}"
                )
                raise

        except Exception as e:
            logger.error(f"[BINList] Unexpected error looking up BIN: {e}")
            raise

    def calculate_risk_score(self, bin_data: Dict) -> int:
        """
        Calculate risk score (0-100) from BIN data

        Args:
            bin_data: Output from lookup_bin()

        Returns:
            Risk score (0 = safe, 100 = very risky)
        """
        score = 0

        # Unknown BIN (highest risk)
        if bin_data.get("scheme") == "unknown":
            score += 50
            logger.info("[BINList] Unknown card scheme: +50 points")

        # Prepaid cards (often used in fraud)
        if bin_data.get("prepaid"):
            score += 25
            logger.info("[BINList] Prepaid card: +25 points")

        # Card type risk
        card_type = bin_data.get("type", "unknown")
        if card_type == "unknown":
            score += 20
            logger.info("[BINList] Unknown card type: +20 points")

        # Missing bank information
        bank = bin_data.get("bank", {})
        if not bank.get("name"):
            score += 15
            logger.info("[BINList] Missing bank name: +15 points")

        # Missing country information
        country = bin_data.get("country", {})
        if not country.get("alpha2"):
            score += 10
            logger.info("[BINList] Missing country: +10 points")

        # High-risk countries (placeholder - should be configurable)
        # This is a simplified example and should be replaced with actual risk data
        high_risk_countries = ["XX", "YY"]  # Placeholder
        if country.get("alpha2") in high_risk_countries:
            score += 30
            logger.info(
                f"[BINList] High-risk country {country.get('alpha2')}: +30 points"
            )

        # Cap at 100
        score = min(score, 100)

        logger.info(f"[BINList] Calculated risk score: {score}/100")

        return score

    def check_country_mismatch(
        self, bin_data: Dict, transaction_country: str, geoip_country: str
    ) -> Dict:
        """
        Check for country mismatches between card, transaction, and user location

        Args:
            bin_data: Output from lookup_bin()
            transaction_country: Country from transaction/billing address (ISO alpha-2)
            geoip_country: Country from GeoIP lookup of user's IP (ISO alpha-2)

        Returns:
            Dict with mismatch analysis:
            {
                "card_country": str,
                "transaction_country": str,
                "geoip_country": str,
                "card_transaction_mismatch": bool,
                "card_geoip_mismatch": bool,
                "transaction_geoip_mismatch": bool,
                "risk_score": int,  # 0-100
                "explanation": str
            }
        """
        card_country = bin_data.get("country", {}).get("alpha2", "")

        mismatches = []
        risk_score = 0

        # Card vs Transaction country
        card_transaction_mismatch = (
            card_country != transaction_country if card_country else False
        )
        if card_transaction_mismatch:
            mismatches.append("card-transaction")
            risk_score += 20

        # Card vs GeoIP country
        card_geoip_mismatch = card_country != geoip_country if card_country else False
        if card_geoip_mismatch:
            mismatches.append("card-geoip")
            risk_score += 15

        # Transaction vs GeoIP country
        transaction_geoip_mismatch = transaction_country != geoip_country
        if transaction_geoip_mismatch:
            mismatches.append("transaction-geoip")
            risk_score += 10

        # All three different (highest risk)
        if len(set([card_country, transaction_country, geoip_country])) == 3:
            risk_score += 25

        explanation = (
            f"Country mismatch detected: {', '.join(mismatches)}"
            if mismatches
            else "No country mismatch"
        )

        result = {
            "card_country": card_country,
            "transaction_country": transaction_country,
            "geoip_country": geoip_country,
            "card_transaction_mismatch": card_transaction_mismatch,
            "card_geoip_mismatch": card_geoip_mismatch,
            "transaction_geoip_mismatch": transaction_geoip_mismatch,
            "risk_score": min(risk_score, 100),
            "explanation": explanation,
        }

        logger.info(
            f"[BINList] Country mismatch check: {explanation}, risk_score={result['risk_score']}"
        )

        return result
