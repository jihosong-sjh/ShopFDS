"""
EmailRep API Integration Service

EmailRep provides email reputation scoring and risk assessment.
API: https://emailrep.io/docs
"""

import os
import logging
from typing import Dict, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailRepService:
    """EmailRep API client for email reputation checks"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize EmailRep service

        Args:
            api_key: EmailRep API key (optional for free tier)
        """
        self.api_key = api_key or os.getenv("EMAILREP_API_KEY")
        self.base_url = "https://emailrep.io"
        self.timeout = 5.0  # 5 seconds timeout

    async def check_email_reputation(self, email: str) -> Dict:
        """
        Check email reputation via EmailRep API

        Args:
            email: Email address to check

        Returns:
            Dict with reputation data:
            {
                "email": "test@example.com",
                "reputation": "high" | "medium" | "low" | "none",
                "suspicious": bool,
                "references": int,  # Number of times seen in breach databases
                "details": {
                    "blacklisted": bool,
                    "malicious_activity": bool,
                    "malicious_activity_recent": bool,
                    "credentials_leaked": bool,
                    "data_breach": bool,
                    "first_seen": str,  # ISO 8601 date
                    "last_seen": str,
                    "domain_exists": bool,
                    "domain_reputation": str,
                    "new_domain": bool,
                    "days_since_domain_creation": int,
                    "suspicious_tld": bool,
                    "spam": bool,
                    "free_provider": bool,
                    "disposable": bool,
                    "deliverable": bool,
                    "accept_all": bool,
                    "valid_mx": bool,
                    "spoofable": bool,
                    "spf_strict": bool,
                    "dmarc_enforced": bool
                },
                "raw_response": Dict  # Full API response
            }

        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If email format is invalid
        """
        if not email or "@" not in email:
            raise ValueError(f"Invalid email format: {email}")

        headers = {}
        if self.api_key:
            headers["Key"] = self.api_key

        url = f"{self.base_url}/{email}"

        logger.info(f"[EmailRep] Checking reputation for: {email}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

            # Parse response
            result = {
                "email": email,
                "reputation": data.get("reputation", "none"),
                "suspicious": data.get("suspicious", False),
                "references": data.get("references", 0),
                "details": data.get("details", {}),
                "raw_response": data,
                "checked_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                f"[EmailRep] Email reputation: {result['reputation']}, suspicious: {result['suspicious']}"
            )

            return result

        except httpx.TimeoutException:
            logger.error(f"[EmailRep] Timeout checking email: {email}")
            raise

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Email not found in database
                logger.warning(f"[EmailRep] Email not found: {email}")
                return {
                    "email": email,
                    "reputation": "none",
                    "suspicious": False,
                    "references": 0,
                    "details": {},
                    "raw_response": {},
                    "checked_at": datetime.utcnow().isoformat(),
                }
            else:
                logger.error(
                    f"[EmailRep] HTTP error {e.response.status_code}: {e.response.text}"
                )
                raise

        except Exception as e:
            logger.error(f"[EmailRep] Unexpected error checking email: {e}")
            raise

    def calculate_risk_score(self, reputation_data: Dict) -> int:
        """
        Calculate risk score (0-100) from EmailRep data

        Args:
            reputation_data: Output from check_email_reputation()

        Returns:
            Risk score (0 = safe, 100 = very risky)
        """
        score = 0
        details = reputation_data.get("details", {})

        # High risk factors (20 points each)
        if details.get("blacklisted"):
            score += 20
        if details.get("malicious_activity_recent"):
            score += 20
        if details.get("credentials_leaked"):
            score += 20

        # Medium risk factors (10 points each)
        if details.get("malicious_activity"):
            score += 10
        if details.get("data_breach"):
            score += 10
        if details.get("spam"):
            score += 10
        if details.get("disposable"):
            score += 10
        if details.get("suspicious_tld"):
            score += 10

        # Low risk factors (5 points each)
        if details.get("new_domain"):
            score += 5
        if not details.get("valid_mx"):
            score += 5
        if not details.get("deliverable"):
            score += 5
        if details.get("spoofable"):
            score += 5

        # Reputation-based adjustment
        reputation = reputation_data.get("reputation", "none")
        if reputation == "low":
            score += 15
        elif reputation == "medium":
            score += 5

        # Suspicious flag
        if reputation_data.get("suspicious"):
            score += 10

        # Cap at 100
        score = min(score, 100)

        logger.info(f"[EmailRep] Calculated risk score: {score}/100")

        return score
