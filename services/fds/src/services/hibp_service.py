"""
HaveIBeenPwned (HIBP) API Integration Service

HIBP provides breach and paste detection for compromised credentials.
API: https://haveibeenpwned.com/API/v3
"""

import os
import logging
import hashlib
from typing import Dict, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class HIBPService:
    """HaveIBeenPwned API client for breach detection"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize HIBP service

        Args:
            api_key: HIBP API key (required for breach searches)
        """
        self.api_key = api_key or os.getenv("HIBP_API_KEY")
        self.base_url = "https://haveibeenpwned.com/api/v3"
        self.timeout = 5.0  # 5 seconds timeout

    async def check_breached_account(self, email: str) -> Dict:
        """
        Check if email has been in data breaches

        Args:
            email: Email address to check

        Returns:
            Dict with breach data:
            {
                "email": str,
                "breached": bool,
                "breach_count": int,
                "breaches": List[{
                    "name": str,  # e.g., "Adobe", "LinkedIn"
                    "title": str,
                    "domain": str,
                    "breach_date": str,  # ISO 8601
                    "added_date": str,
                    "pwn_count": int,  # Number of accounts in breach
                    "data_classes": List[str],  # e.g., ["Email addresses", "Passwords"]
                    "is_verified": bool,
                    "is_sensitive": bool
                }],
                "paste_count": int,
                "risk_score": int,  # 0-100 (calculated)
                "raw_response": Dict
            }

        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If API key is missing or email is invalid
        """
        if not self.api_key:
            logger.warning(
                "[HIBP] API key not configured, using k-Anonymity password check only"
            )
            # Fall back to password range check (doesn't require API key)
            return await self._check_anonymity_fallback(email)

        if not email or "@" not in email:
            raise ValueError(f"Invalid email format: {email}")

        headers = {
            "hibp-api-key": self.api_key,
            "User-Agent": "ShopFDS-FraudDetection",
        }

        # URL encode email
        import urllib.parse

        encoded_email = urllib.parse.quote(email)
        url = f"{self.base_url}/breachedaccount/{encoded_email}"

        logger.info(f"[HIBP] Checking breaches for: {email}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

                # 404 means no breaches found
                if response.status_code == 404:
                    logger.info(f"[HIBP] No breaches found for: {email}")
                    return {
                        "email": email,
                        "breached": False,
                        "breach_count": 0,
                        "breaches": [],
                        "paste_count": 0,
                        "risk_score": 0,
                        "raw_response": {},
                        "checked_at": datetime.utcnow().isoformat(),
                    }

                response.raise_for_status()
                breaches = response.json()

            # Check pastes (separate API call)
            paste_count = await self._check_pastes(email, headers)

            # Parse breaches
            breach_list = []
            for breach in breaches:
                breach_list.append(
                    {
                        "name": breach.get("Name", ""),
                        "title": breach.get("Title", ""),
                        "domain": breach.get("Domain", ""),
                        "breach_date": breach.get("BreachDate", ""),
                        "added_date": breach.get("AddedDate", ""),
                        "pwn_count": breach.get("PwnCount", 0),
                        "data_classes": breach.get("DataClasses", []),
                        "is_verified": breach.get("IsVerified", False),
                        "is_sensitive": breach.get("IsSensitive", False),
                    }
                )

            result = {
                "email": email,
                "breached": True,
                "breach_count": len(breach_list),
                "breaches": breach_list,
                "paste_count": paste_count,
                "raw_response": breaches,
                "checked_at": datetime.utcnow().isoformat(),
            }

            # Calculate risk score
            result["risk_score"] = self.calculate_risk_score(result)

            logger.info(
                f"[HIBP] Found {result['breach_count']} breaches, "
                f"{result['paste_count']} pastes, risk_score={result['risk_score']}"
            )

            return result

        except httpx.TimeoutException:
            logger.error(f"[HIBP] Timeout checking email: {email}")
            raise

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.error("[HIBP] Rate limit exceeded")
                raise ValueError("HIBP API rate limit exceeded")
            else:
                logger.error(
                    f"[HIBP] HTTP error {e.response.status_code}: {e.response.text}"
                )
                raise

        except Exception as e:
            logger.error(f"[HIBP] Unexpected error checking email: {e}")
            raise

    async def _check_pastes(self, email: str, headers: Dict) -> int:
        """
        Check if email appears in pastes

        Args:
            email: Email address
            headers: Request headers with API key

        Returns:
            Number of paste appearances
        """
        import urllib.parse

        encoded_email = urllib.parse.quote(email)
        url = f"{self.base_url}/pasteaccount/{encoded_email}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 404:
                    return 0

                response.raise_for_status()
                pastes = response.json()
                return len(pastes)

        except Exception as e:
            logger.warning(f"[HIBP] Error checking pastes: {e}")
            return 0

    async def _check_anonymity_fallback(self, email: str) -> Dict:
        """
        Fallback when API key is not available (limited functionality)

        Args:
            email: Email address

        Returns:
            Limited breach data
        """
        logger.info(f"[HIBP] Using k-Anonymity fallback (no API key) for: {email}")

        return {
            "email": email,
            "breached": False,  # Can't determine without API key
            "breach_count": 0,
            "breaches": [],
            "paste_count": 0,
            "risk_score": 0,
            "raw_response": {},
            "checked_at": datetime.utcnow().isoformat(),
            "note": "Limited check - API key required for full breach detection",
        }

    async def check_password_pwned(self, password: str) -> Dict:
        """
        Check if password has been pwned using k-Anonymity model
        (Doesn't require API key, doesn't send actual password)

        Args:
            password: Password to check

        Returns:
            Dict with pwned data:
            {
                "pwned": bool,
                "pwn_count": int,  # Number of times seen in breaches
                "risk_score": int
            }
        """
        # SHA-1 hash of password
        sha1_hash = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        hash_prefix = sha1_hash[:5]
        hash_suffix = sha1_hash[5:]

        url = f"https://api.pwnedpasswords.com/range/{hash_prefix}"

        logger.info(f"[HIBP] Checking password (k-Anonymity: {hash_prefix})")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Parse response (format: SUFFIX:COUNT\r\n)
                for line in response.text.splitlines():
                    parts = line.split(":")
                    if len(parts) == 2 and parts[0] == hash_suffix:
                        pwn_count = int(parts[1])
                        logger.info(f"[HIBP] Password pwned {pwn_count} times")

                        risk_score = min(pwn_count // 10, 100)  # Scale to 0-100

                        return {
                            "pwned": True,
                            "pwn_count": pwn_count,
                            "risk_score": risk_score,
                        }

            # Password not found in breaches
            logger.info("[HIBP] Password not pwned")
            return {"pwned": False, "pwn_count": 0, "risk_score": 0}

        except Exception as e:
            logger.error(f"[HIBP] Error checking password: {e}")
            raise

    def calculate_risk_score(self, breach_data: Dict) -> int:
        """
        Calculate risk score (0-100) from HIBP data

        Args:
            breach_data: Output from check_breached_account()

        Returns:
            Risk score (0 = safe, 100 = very risky)
        """
        score = 0

        breach_count = breach_data.get("breach_count", 0)
        paste_count = breach_data.get("paste_count", 0)
        breaches = breach_data.get("breaches", [])

        # Base score from breach count
        if breach_count > 0:
            score += min(breach_count * 10, 40)  # Up to 40 points
            logger.info(
                f"[HIBP] {breach_count} breaches: +{min(breach_count * 10, 40)} points"
            )

        # Recent breaches are higher risk
        from dateutil import parser as date_parser

        current_year = datetime.utcnow().year
        for breach in breaches:
            breach_date = breach.get("breach_date", "")
            if breach_date:
                try:
                    breach_year = date_parser.parse(breach_date).year
                    if current_year - breach_year <= 1:
                        # Breach within last year
                        score += 15
                        logger.info(f"[HIBP] Recent breach ({breach_year}): +15 points")
                except Exception:
                    pass

        # Sensitive breaches
        sensitive_count = sum(1 for b in breaches if b.get("is_sensitive", False))
        if sensitive_count > 0:
            score += sensitive_count * 10
            logger.info(
                f"[HIBP] {sensitive_count} sensitive breaches: +{sensitive_count * 10} points"
            )

        # Password data compromised (highest risk)
        password_breaches = sum(
            1 for b in breaches if "Passwords" in b.get("data_classes", [])
        )
        if password_breaches > 0:
            score += 25
            logger.info(f"[HIBP] {password_breaches} password breaches: +25 points")

        # Paste appearances
        if paste_count > 0:
            score += min(paste_count * 5, 20)  # Up to 20 points
            logger.info(
                f"[HIBP] {paste_count} paste appearances: +{min(paste_count * 5, 20)} points"
            )

        # Cap at 100
        score = min(score, 100)

        logger.info(f"[HIBP] Calculated risk score: {score}/100")

        return score
