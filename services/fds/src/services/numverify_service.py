"""
Numverify API Integration Service

Numverify provides phone number validation and carrier lookup.
API: https://numverify.com/documentation
"""

import os
import logging
from typing import Dict, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class NumverifyService:
    """Numverify API client for phone number validation"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Numverify service

        Args:
            api_key: Numverify API key (required)
        """
        self.api_key = api_key or os.getenv("NUMVERIFY_API_KEY")
        if not self.api_key:
            logger.warning("[Numverify] API key not configured")

        self.base_url = "http://apilayer.net/api"  # Free plan uses HTTP
        self.timeout = 5.0  # 5 seconds timeout

    async def validate_phone_number(
        self, phone_number: str, country_code: Optional[str] = None
    ) -> Dict:
        """
        Validate phone number via Numverify API

        Args:
            phone_number: Phone number to validate (with or without country code)
            country_code: ISO 3166-1 alpha-2 country code (e.g., "US", "KR")

        Returns:
            Dict with validation data:
            {
                "valid": bool,
                "number": str,  # E.164 format
                "local_format": str,
                "international_format": str,
                "country_prefix": str,  # e.g., "+1", "+82"
                "country_code": str,  # e.g., "US", "KR"
                "country_name": str,
                "location": str,  # Region/state
                "carrier": str,  # Mobile carrier name
                "line_type": "mobile" | "landline" | "toll_free" | "premium_rate" | "unknown",
                "risk_score": int,  # 0-100 (calculated)
                "raw_response": Dict
            }

        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If API key is missing
        """
        if not self.api_key:
            raise ValueError("Numverify API key is required")

        if not phone_number:
            raise ValueError("Phone number is required")

        params = {"access_key": self.api_key, "number": phone_number, "format": 1}

        if country_code:
            params["country_code"] = country_code

        logger.info(f"[Numverify] Validating phone number: {phone_number}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/validate", params=params)
                response.raise_for_status()
                data = response.json()

            # Check for API errors
            if not data.get("valid", False) and "error" in data:
                error_info = data.get("error", {})
                logger.error(
                    f"[Numverify] API error: {error_info.get('type')} - {error_info.get('info')}"
                )
                raise ValueError(
                    f"Numverify API error: {error_info.get('info', 'Unknown error')}"
                )

            # Parse response
            result = {
                "valid": data.get("valid", False),
                "number": data.get("number", ""),
                "local_format": data.get("local_format", ""),
                "international_format": data.get("international_format", ""),
                "country_prefix": data.get("country_prefix", ""),
                "country_code": data.get("country_code", ""),
                "country_name": data.get("country_name", ""),
                "location": data.get("location", ""),
                "carrier": data.get("carrier", ""),
                "line_type": data.get("line_type", "unknown"),
                "raw_response": data,
                "checked_at": datetime.utcnow().isoformat(),
            }

            # Calculate risk score
            result["risk_score"] = self.calculate_risk_score(result)

            logger.info(
                f"[Numverify] Phone validation: valid={result['valid']}, "
                f"line_type={result['line_type']}, risk_score={result['risk_score']}"
            )

            return result

        except httpx.TimeoutException:
            logger.error(f"[Numverify] Timeout validating phone: {phone_number}")
            raise

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[Numverify] HTTP error {e.response.status_code}: {e.response.text}"
            )
            raise

        except Exception as e:
            logger.error(f"[Numverify] Unexpected error validating phone: {e}")
            raise

    def calculate_risk_score(self, validation_data: Dict) -> int:
        """
        Calculate risk score (0-100) from Numverify data

        Args:
            validation_data: Output from validate_phone_number()

        Returns:
            Risk score (0 = safe, 100 = very risky)
        """
        score = 0

        # Invalid phone number (highest risk)
        if not validation_data.get("valid"):
            score += 50
            logger.info("[Numverify] Invalid phone number: +50 points")

        # Line type risk assessment
        line_type = validation_data.get("line_type", "unknown")
        if line_type == "premium_rate":
            # Premium rate numbers are often used in fraud
            score += 30
            logger.info("[Numverify] Premium rate number: +30 points")
        elif line_type == "toll_free":
            # Toll-free numbers can be suspicious for user accounts
            score += 15
            logger.info("[Numverify] Toll-free number: +15 points")
        elif line_type == "unknown":
            # Unknown line type is suspicious
            score += 10
            logger.info("[Numverify] Unknown line type: +10 points")
        elif line_type == "landline":
            # Landlines are less common for modern e-commerce
            score += 5
            logger.info("[Numverify] Landline: +5 points")

        # Missing carrier information (mobile should have carrier)
        if line_type == "mobile" and not validation_data.get("carrier"):
            score += 10
            logger.info("[Numverify] Mobile without carrier: +10 points")

        # Missing location information
        if not validation_data.get("location"):
            score += 5
            logger.info("[Numverify] Missing location: +5 points")

        # Cap at 100
        score = min(score, 100)

        logger.info(f"[Numverify] Calculated risk score: {score}/100")

        return score

    async def check_carrier_reputation(self, carrier: str) -> Dict:
        """
        Check carrier reputation (placeholder for future enhancement)

        This could be extended to check carriers against a known fraud database.

        Args:
            carrier: Carrier name from validation

        Returns:
            Dict with carrier reputation data
        """
        # TODO: Implement carrier reputation database
        # For now, return neutral reputation
        return {
            "carrier": carrier,
            "reputation": "unknown",
            "fraud_reports": 0,
            "risk_score": 0,
        }
