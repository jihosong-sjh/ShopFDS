"""
External Verification Service

Unified service for external API integrations with fallback and retry logic.
Integrates: EmailRep, Numverify, BINList, HaveIBeenPwned
"""

import logging
import asyncio
from typing import Dict, Optional
from datetime import datetime
import httpx

from src.services.emailrep_service import EmailRepService
from src.services.numverify_service import NumverifyService
from src.services.bin_service import BINService
from src.services.hibp_service import HIBPService

logger = logging.getLogger(__name__)


class ExternalVerificationService:
    """Unified external verification service with fallback and retry"""

    def __init__(
        self,
        emailrep_api_key: Optional[str] = None,
        numverify_api_key: Optional[str] = None,
        binlist_api_key: Optional[str] = None,
        hibp_api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 5.0,
    ):
        """
        Initialize external verification service

        Args:
            emailrep_api_key: EmailRep API key
            numverify_api_key: Numverify API key
            binlist_api_key: BINList API key
            hibp_api_key: HaveIBeenPwned API key
            max_retries: Maximum retry attempts (default: 3)
            retry_delay: Initial retry delay in seconds (exponential backoff)
            timeout: Request timeout in seconds (default: 5)
        """
        self.emailrep = EmailRepService(api_key=emailrep_api_key)
        self.numverify = NumverifyService(api_key=numverify_api_key)
        self.binlist = BINService(api_key=binlist_api_key)
        self.hibp = HIBPService(api_key=hibp_api_key)

        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    async def _retry_with_exponential_backoff(
        self, func, *args, service_name: str, **kwargs
    ) -> Dict:
        """
        Execute function with exponential backoff retry

        Args:
            func: Async function to execute
            *args: Function arguments
            service_name: Service name for logging
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"[{service_name}] Success after {attempt} retries")
                return result

            except (httpx.TimeoutException, httpx.HTTPError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"[{service_name}] Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"[{service_name}] All {self.max_retries} attempts failed"
                    )

            except Exception as e:
                # Don't retry on non-network errors
                logger.error(f"[{service_name}] Non-retryable error: {e}")
                raise

        # All retries exhausted
        raise last_exception

    async def verify_email_comprehensive(self, email: str) -> Dict:
        """
        Comprehensive email verification (EmailRep + HaveIBeenPwned)

        Args:
            email: Email address to verify

        Returns:
            Dict with combined verification results:
            {
                "email": str,
                "emailrep": {
                    "available": bool,
                    "data": Dict | None,
                    "risk_score": int,
                    "error": str | None
                },
                "hibp": {
                    "available": bool,
                    "data": Dict | None,
                    "risk_score": int,
                    "error": str | None
                },
                "overall_risk_score": int,  # 0-100
                "recommendation": "allow" | "review" | "block",
                "checked_at": str
            }
        """
        logger.info(f"[ExternalVerification] Comprehensive email check: {email}")

        results = {
            "email": email,
            "emailrep": {
                "available": False,
                "data": None,
                "risk_score": 0,
                "error": None,
            },
            "hibp": {"available": False, "data": None, "risk_score": 0, "error": None},
            "overall_risk_score": 0,
            "recommendation": "allow",
            "checked_at": datetime.utcnow().isoformat(),
        }

        # Check EmailRep with retry
        try:
            emailrep_data = await self._retry_with_exponential_backoff(
                self.emailrep.check_email_reputation,
                email,
                service_name="EmailRep",
            )
            emailrep_risk = self.emailrep.calculate_risk_score(emailrep_data)

            results["emailrep"] = {
                "available": True,
                "data": emailrep_data,
                "risk_score": emailrep_risk,
                "error": None,
            }
        except Exception as e:
            logger.error(f"[EmailRep] Failed after retries: {e}")
            results["emailrep"]["error"] = str(e)

        # Check HaveIBeenPwned with retry
        try:
            hibp_data = await self._retry_with_exponential_backoff(
                self.hibp.check_breached_account, email, service_name="HIBP"
            )
            hibp_risk = self.hibp.calculate_risk_score(hibp_data)

            results["hibp"] = {
                "available": True,
                "data": hibp_data,
                "risk_score": hibp_risk,
                "error": None,
            }
        except Exception as e:
            logger.error(f"[HIBP] Failed after retries: {e}")
            results["hibp"]["error"] = str(e)

        # Calculate overall risk score (weighted average)
        available_services = 0
        total_risk = 0

        if results["emailrep"]["available"]:
            total_risk += results["emailrep"]["risk_score"] * 0.6  # 60% weight
            available_services += 1

        if results["hibp"]["available"]:
            total_risk += results["hibp"]["risk_score"] * 0.4  # 40% weight
            available_services += 1

        if available_services > 0:
            results["overall_risk_score"] = int(total_risk)
        else:
            # Fallback if all services failed
            results["overall_risk_score"] = 50  # Medium risk
            logger.warning(
                "[ExternalVerification] All email services failed, using fallback risk score"
            )

        # Determine recommendation
        if results["overall_risk_score"] >= 70:
            results["recommendation"] = "block"
        elif results["overall_risk_score"] >= 40:
            results["recommendation"] = "review"
        else:
            results["recommendation"] = "allow"

        logger.info(
            f"[ExternalVerification] Email verification complete: "
            f"risk_score={results['overall_risk_score']}, "
            f"recommendation={results['recommendation']}"
        )

        return results

    async def verify_phone_number(
        self, phone_number: str, country_code: Optional[str] = None
    ) -> Dict:
        """
        Verify phone number with Numverify (with retry)

        Args:
            phone_number: Phone number to verify
            country_code: ISO country code (optional)

        Returns:
            Dict with verification results:
            {
                "phone_number": str,
                "available": bool,
                "data": Dict | None,
                "risk_score": int,
                "recommendation": "allow" | "review" | "block",
                "error": str | None,
                "checked_at": str
            }
        """
        logger.info(f"[ExternalVerification] Phone verification: {phone_number}")

        result = {
            "phone_number": phone_number,
            "available": False,
            "data": None,
            "risk_score": 0,
            "recommendation": "allow",
            "error": None,
            "checked_at": datetime.utcnow().isoformat(),
        }

        try:
            numverify_data = await self._retry_with_exponential_backoff(
                self.numverify.validate_phone_number,
                phone_number,
                country_code,
                service_name="Numverify",
            )

            result["available"] = True
            result["data"] = numverify_data
            result["risk_score"] = numverify_data["risk_score"]

            # Determine recommendation
            if result["risk_score"] >= 70:
                result["recommendation"] = "block"
            elif result["risk_score"] >= 40:
                result["recommendation"] = "review"
            else:
                result["recommendation"] = "allow"

        except Exception as e:
            logger.error(f"[Numverify] Failed after retries: {e}")
            result["error"] = str(e)
            result["risk_score"] = 50  # Fallback
            result["recommendation"] = "review"

        logger.info(
            f"[ExternalVerification] Phone verification complete: "
            f"risk_score={result['risk_score']}, "
            f"recommendation={result['recommendation']}"
        )

        return result

    async def verify_card_bin(
        self,
        bin_number: str,
        transaction_country: Optional[str] = None,
        geoip_country: Optional[str] = None,
    ) -> Dict:
        """
        Verify card BIN with country mismatch check (with retry)

        Args:
            bin_number: Card BIN (first 6-8 digits)
            transaction_country: Country from billing address
            geoip_country: Country from GeoIP lookup

        Returns:
            Dict with verification results:
            {
                "bin": str,
                "available": bool,
                "data": Dict | None,
                "risk_score": int,
                "country_mismatch": Dict | None,
                "recommendation": "allow" | "review" | "block",
                "error": str | None,
                "checked_at": str
            }
        """
        logger.info(f"[ExternalVerification] BIN verification: {bin_number}")

        result = {
            "bin": bin_number,
            "available": False,
            "data": None,
            "risk_score": 0,
            "country_mismatch": None,
            "recommendation": "allow",
            "error": None,
            "checked_at": datetime.utcnow().isoformat(),
        }

        try:
            bin_data = await self._retry_with_exponential_backoff(
                self.binlist.lookup_bin, bin_number, service_name="BINList"
            )

            result["available"] = True
            result["data"] = bin_data
            result["risk_score"] = bin_data["risk_score"]

            # Check country mismatch if countries provided
            if transaction_country and geoip_country:
                mismatch_data = self.binlist.check_country_mismatch(
                    bin_data, transaction_country, geoip_country
                )
                result["country_mismatch"] = mismatch_data
                # Add mismatch risk to total risk
                result["risk_score"] = min(
                    result["risk_score"] + mismatch_data["risk_score"], 100
                )

            # Determine recommendation
            if result["risk_score"] >= 70:
                result["recommendation"] = "block"
            elif result["risk_score"] >= 40:
                result["recommendation"] = "review"
            else:
                result["recommendation"] = "allow"

        except Exception as e:
            logger.error(f"[BINList] Failed after retries: {e}")
            result["error"] = str(e)
            result["risk_score"] = 50  # Fallback
            result["recommendation"] = "review"

        logger.info(
            f"[ExternalVerification] BIN verification complete: "
            f"risk_score={result['risk_score']}, "
            f"recommendation={result['recommendation']}"
        )

        return result

    async def verify_all(
        self,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        phone_country: Optional[str] = None,
        card_bin: Optional[str] = None,
        transaction_country: Optional[str] = None,
        geoip_country: Optional[str] = None,
    ) -> Dict:
        """
        Run all verifications in parallel

        Args:
            email: Email to verify
            phone_number: Phone to verify
            phone_country: Phone country code
            card_bin: Card BIN to verify
            transaction_country: Transaction country
            geoip_country: GeoIP country

        Returns:
            Dict with all verification results and overall recommendation
        """
        logger.info("[ExternalVerification] Running all verifications in parallel")

        tasks = []
        task_names = []

        if email:
            tasks.append(self.verify_email_comprehensive(email))
            task_names.append("email")

        if phone_number:
            tasks.append(self.verify_phone_number(phone_number, phone_country))
            task_names.append("phone")

        if card_bin:
            tasks.append(
                self.verify_card_bin(card_bin, transaction_country, geoip_country)
            )
            task_names.append("card_bin")

        if not tasks:
            logger.warning("[ExternalVerification] No verification tasks provided")
            return {
                "overall_risk_score": 0,
                "overall_recommendation": "allow",
                "verifications": {},
                "checked_at": datetime.utcnow().isoformat(),
            }

        # Run all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        verifications = {}
        for name, result in zip(task_names, results):
            if isinstance(result, Exception):
                logger.error(f"[ExternalVerification] {name} failed: {result}")
                verifications[name] = {
                    "error": str(result),
                    "risk_score": 50,
                    "recommendation": "review",
                }
            else:
                verifications[name] = result

        # Calculate overall risk score (average of available results)
        risk_scores = []
        for name, result in verifications.items():
            if name == "email" and result.get("overall_risk_score") is not None:
                risk_scores.append(result["overall_risk_score"])
            elif result.get("risk_score") is not None:
                risk_scores.append(result["risk_score"])

        overall_risk = int(sum(risk_scores) / len(risk_scores)) if risk_scores else 0

        # Determine overall recommendation (most restrictive)
        recommendations = [
            result.get("recommendation", "allow") for result in verifications.values()
        ]
        if "block" in recommendations:
            overall_recommendation = "block"
        elif "review" in recommendations:
            overall_recommendation = "review"
        else:
            overall_recommendation = "allow"

        combined_result = {
            "overall_risk_score": overall_risk,
            "overall_recommendation": overall_recommendation,
            "verifications": verifications,
            "checked_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"[ExternalVerification] All verifications complete: "
            f"risk_score={overall_risk}, recommendation={overall_recommendation}"
        )

        return combined_result
