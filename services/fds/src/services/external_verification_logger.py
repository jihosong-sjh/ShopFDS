"""
External Verification Logger

Wraps ExternalVerificationService to log all API calls to the database.
"""

import logging
import time
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.services.external_verification_service import ExternalVerificationService
from src.models.external_service_log import ExternalServiceLog, ServiceName

logger = logging.getLogger(__name__)


class ExternalVerificationLogger:
    """
    Wrapper around ExternalVerificationService that logs all calls
    """

    def __init__(
        self,
        db_session: AsyncSession,
        verification_service: ExternalVerificationService,
    ):
        """
        Initialize logger

        Args:
            db_session: SQLAlchemy async session
            verification_service: ExternalVerificationService instance
        """
        self.db = db_session
        self.service = verification_service

    async def _log_api_call(
        self,
        service_name: ServiceName,
        request_data: Dict,
        response_data: Dict,
        response_time_ms: int,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        transaction_id: Optional[UUID] = None,
    ):
        """
        Log external API call to database

        Args:
            service_name: External service name
            request_data: Request payload
            response_data: Response data
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
            error_message: Error message if failed
            transaction_id: Associated transaction ID (optional)
        """
        try:
            log_entry = ExternalServiceLog(
                service_name=service_name,
                request_data=request_data,
                response_data=response_data,
                response_time_ms=response_time_ms,
                status_code=status_code,
                error_message=error_message,
                transaction_id=transaction_id,
            )

            self.db.add(log_entry)
            await self.db.commit()

            logger.info(
                f"[ExternalLog] Logged {service_name.value} call: "
                f"time={response_time_ms}ms, status={status_code}"
            )

        except Exception as e:
            logger.error(f"[ExternalLog] Failed to log API call: {e}")
            await self.db.rollback()

    async def verify_email_comprehensive(
        self, email: str, transaction_id: Optional[UUID] = None
    ) -> Dict:
        """
        Verify email with logging

        Args:
            email: Email address
            transaction_id: Associated transaction ID

        Returns:
            Verification result
        """
        start_time = time.time()
        result = None
        error = None

        try:
            result = await self.service.verify_email_comprehensive(email)
            return result

        except Exception as e:
            error = str(e)
            logger.error(f"[ExternalLog] Email verification failed: {e}")
            raise

        finally:
            response_time_ms = int((time.time() - start_time) * 1000)

            # Log EmailRep call
            if result and result.get("emailrep", {}).get("available"):
                await self._log_api_call(
                    service_name=ServiceName.EMAILREP,
                    request_data={"email": email},
                    response_data=result.get("emailrep", {}).get("data", {}),
                    response_time_ms=response_time_ms // 2,  # Approximate
                    status_code=200 if not result["emailrep"].get("error") else None,
                    error_message=result["emailrep"].get("error"),
                    transaction_id=transaction_id,
                )

            # Log HIBP call
            if result and result.get("hibp", {}).get("available"):
                await self._log_api_call(
                    service_name=ServiceName.HAVEIBEENPWNED,
                    request_data={"email": email},
                    response_data=result.get("hibp", {}).get("data", {}),
                    response_time_ms=response_time_ms // 2,  # Approximate
                    status_code=200 if not result["hibp"].get("error") else None,
                    error_message=result["hibp"].get("error"),
                    transaction_id=transaction_id,
                )

            # Log overall error if service failed completely
            if error:
                await self._log_api_call(
                    service_name=ServiceName.EMAILREP,  # Primary service
                    request_data={"email": email},
                    response_data={},
                    response_time_ms=response_time_ms,
                    status_code=None,
                    error_message=error,
                    transaction_id=transaction_id,
                )

    async def verify_phone_number(
        self,
        phone_number: str,
        country_code: Optional[str] = None,
        transaction_id: Optional[UUID] = None,
    ) -> Dict:
        """
        Verify phone number with logging

        Args:
            phone_number: Phone number
            country_code: Country code
            transaction_id: Associated transaction ID

        Returns:
            Verification result
        """
        start_time = time.time()
        result = None
        error = None

        try:
            result = await self.service.verify_phone_number(phone_number, country_code)
            return result

        except Exception as e:
            error = str(e)
            logger.error(f"[ExternalLog] Phone verification failed: {e}")
            raise

        finally:
            response_time_ms = int((time.time() - start_time) * 1000)

            await self._log_api_call(
                service_name=ServiceName.NUMVERIFY,
                request_data={
                    "phone_number": phone_number,
                    "country_code": country_code,
                },
                response_data=result.get("data", {}) if result else {},
                response_time_ms=response_time_ms,
                status_code=200 if result and result.get("available") else None,
                error_message=result.get("error") if result else error,
                transaction_id=transaction_id,
            )

    async def verify_card_bin(
        self,
        bin_number: str,
        transaction_country: Optional[str] = None,
        geoip_country: Optional[str] = None,
        transaction_id: Optional[UUID] = None,
    ) -> Dict:
        """
        Verify card BIN with logging

        Args:
            bin_number: Card BIN
            transaction_country: Transaction country
            geoip_country: GeoIP country
            transaction_id: Associated transaction ID

        Returns:
            Verification result
        """
        start_time = time.time()
        result = None
        error = None

        try:
            result = await self.service.verify_card_bin(
                bin_number, transaction_country, geoip_country
            )
            return result

        except Exception as e:
            error = str(e)
            logger.error(f"[ExternalLog] BIN verification failed: {e}")
            raise

        finally:
            response_time_ms = int((time.time() - start_time) * 1000)

            await self._log_api_call(
                service_name=ServiceName.BIN_DATABASE,
                request_data={
                    "bin_number": bin_number,
                    "transaction_country": transaction_country,
                    "geoip_country": geoip_country,
                },
                response_data=result.get("data", {}) if result else {},
                response_time_ms=response_time_ms,
                status_code=200 if result and result.get("available") else None,
                error_message=result.get("error") if result else error,
                transaction_id=transaction_id,
            )

    async def verify_all(
        self,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        phone_country: Optional[str] = None,
        card_bin: Optional[str] = None,
        transaction_country: Optional[str] = None,
        geoip_country: Optional[str] = None,
        transaction_id: Optional[UUID] = None,
    ) -> Dict:
        """
        Run all verifications in parallel with logging

        Args:
            email: Email to verify
            phone_number: Phone to verify
            phone_country: Phone country code
            card_bin: Card BIN to verify
            transaction_country: Transaction country
            geoip_country: GeoIP country
            transaction_id: Associated transaction ID

        Returns:
            Combined verification results
        """
        start_time = time.time()
        result = None

        try:
            result = await self.service.verify_all(
                email=email,
                phone_number=phone_number,
                phone_country=phone_country,
                card_bin=card_bin,
                transaction_country=transaction_country,
                geoip_country=geoip_country,
            )

            # Log individual service calls
            if email and result.get("verifications", {}).get("email"):
                email_result = result["verifications"]["email"]
                if email_result.get("emailrep", {}).get("available"):
                    await self._log_api_call(
                        service_name=ServiceName.EMAILREP,
                        request_data={"email": email},
                        response_data=email_result.get("emailrep", {}).get("data", {}),
                        response_time_ms=int((time.time() - start_time) * 1000) // 3,
                        status_code=200
                        if not email_result["emailrep"].get("error")
                        else None,
                        error_message=email_result["emailrep"].get("error"),
                        transaction_id=transaction_id,
                    )

                if email_result.get("hibp", {}).get("available"):
                    await self._log_api_call(
                        service_name=ServiceName.HAVEIBEENPWNED,
                        request_data={"email": email},
                        response_data=email_result.get("hibp", {}).get("data", {}),
                        response_time_ms=int((time.time() - start_time) * 1000) // 3,
                        status_code=200
                        if not email_result["hibp"].get("error")
                        else None,
                        error_message=email_result["hibp"].get("error"),
                        transaction_id=transaction_id,
                    )

            if phone_number and result.get("verifications", {}).get("phone"):
                phone_result = result["verifications"]["phone"]
                await self._log_api_call(
                    service_name=ServiceName.NUMVERIFY,
                    request_data={
                        "phone_number": phone_number,
                        "country_code": phone_country,
                    },
                    response_data=phone_result.get("data", {}),
                    response_time_ms=int((time.time() - start_time) * 1000) // 3,
                    status_code=200 if phone_result.get("available") else None,
                    error_message=phone_result.get("error"),
                    transaction_id=transaction_id,
                )

            if card_bin and result.get("verifications", {}).get("card_bin"):
                bin_result = result["verifications"]["card_bin"]
                await self._log_api_call(
                    service_name=ServiceName.BIN_DATABASE,
                    request_data={
                        "bin_number": card_bin,
                        "transaction_country": transaction_country,
                        "geoip_country": geoip_country,
                    },
                    response_data=bin_result.get("data", {}),
                    response_time_ms=int((time.time() - start_time) * 1000) // 3,
                    status_code=200 if bin_result.get("available") else None,
                    error_message=bin_result.get("error"),
                    transaction_id=transaction_id,
                )

            return result

        except Exception as e:
            logger.error(f"[ExternalLog] verify_all failed: {e}")
            raise
