"""
External Verification API Endpoints

Provides endpoints for email, phone, and card BIN verification.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from uuid import UUID

from src.services.external_verification_service import ExternalVerificationService
from src.services.external_verification_logger import ExternalVerificationLogger
from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/fds/verify", tags=["External Verification"])


# Pydantic Models
class EmailVerificationRequest(BaseModel):
    """Email verification request"""

    email: EmailStr = Field(..., description="Email address to verify")
    transaction_id: Optional[UUID] = Field(
        None, description="Associated transaction ID (optional)"
    )


class PhoneVerificationRequest(BaseModel):
    """Phone verification request"""

    phone_number: str = Field(..., description="Phone number to verify")
    country_code: Optional[str] = Field(
        None,
        description="ISO 3166-1 alpha-2 country code (e.g., US, KR)",
        max_length=2,
    )
    transaction_id: Optional[UUID] = Field(
        None, description="Associated transaction ID (optional)"
    )


class CardBINVerificationRequest(BaseModel):
    """Card BIN verification request"""

    bin_number: str = Field(
        ..., description="Card BIN (first 6-8 digits)", min_length=6, max_length=8
    )
    transaction_country: Optional[str] = Field(
        None, description="Transaction country code (ISO alpha-2)", max_length=2
    )
    geoip_country: Optional[str] = Field(
        None, description="GeoIP country code (ISO alpha-2)", max_length=2
    )
    transaction_id: Optional[UUID] = Field(
        None, description="Associated transaction ID (optional)"
    )


class VerificationResponse(BaseModel):
    """Generic verification response"""

    success: bool
    data: Dict[str, Any]
    message: str


# Dependency: Create external verification service
async def get_verification_service() -> ExternalVerificationService:
    """Create external verification service instance"""
    return ExternalVerificationService()


# API Endpoints
@router.post(
    "/email", response_model=VerificationResponse, status_code=status.HTTP_200_OK
)
async def verify_email(
    request: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
    verification_service: ExternalVerificationService = Depends(
        get_verification_service
    ),
):
    """
    Verify email address using EmailRep and HaveIBeenPwned

    Checks:
    - Email reputation (EmailRep)
    - Data breaches (HaveIBeenPwned)
    - Password leaks (HaveIBeenPwned)

    Returns:
    - Risk score (0-100)
    - Recommendation (allow/review/block)
    - Detailed verification data

    Example:
        ```json
        {
            "email": "test@example.com",
            "transaction_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        ```

    Response:
        ```json
        {
            "success": true,
            "data": {
                "email": "test@example.com",
                "overall_risk_score": 45,
                "recommendation": "review",
                "emailrep": {...},
                "hibp": {...}
            },
            "message": "Email verification complete"
        }
        ```
    """
    try:
        logger.info(f"[VerificationAPI] Email verification request: {request.email}")

        # Create logger wrapper
        verification_logger = ExternalVerificationLogger(db, verification_service)

        # Verify email
        result = await verification_logger.verify_email_comprehensive(
            email=request.email, transaction_id=request.transaction_id
        )

        return VerificationResponse(
            success=True, data=result, message="Email verification complete"
        )

    except ValueError as e:
        logger.error(f"[VerificationAPI] Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        logger.error(f"[VerificationAPI] Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed",
        )


@router.post(
    "/phone", response_model=VerificationResponse, status_code=status.HTTP_200_OK
)
async def verify_phone(
    request: PhoneVerificationRequest,
    db: AsyncSession = Depends(get_db),
    verification_service: ExternalVerificationService = Depends(
        get_verification_service
    ),
):
    """
    Verify phone number using Numverify

    Checks:
    - Phone number validity
    - Line type (mobile/landline/toll-free/premium-rate)
    - Carrier information
    - Country/location

    Returns:
    - Risk score (0-100)
    - Recommendation (allow/review/block)
    - Detailed validation data

    Example:
        ```json
        {
            "phone_number": "+821012345678",
            "country_code": "KR",
            "transaction_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        ```

    Response:
        ```json
        {
            "success": true,
            "data": {
                "phone_number": "+821012345678",
                "valid": true,
                "line_type": "mobile",
                "carrier": "SK Telecom",
                "risk_score": 10,
                "recommendation": "allow"
            },
            "message": "Phone verification complete"
        }
        ```
    """
    try:
        logger.info(
            f"[VerificationAPI] Phone verification request: {request.phone_number}"
        )

        # Create logger wrapper
        verification_logger = ExternalVerificationLogger(db, verification_service)

        # Verify phone
        result = await verification_logger.verify_phone_number(
            phone_number=request.phone_number,
            country_code=request.country_code,
            transaction_id=request.transaction_id,
        )

        return VerificationResponse(
            success=True, data=result, message="Phone verification complete"
        )

    except ValueError as e:
        logger.error(f"[VerificationAPI] Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        logger.error(f"[VerificationAPI] Phone verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Phone verification failed",
        )


@router.post(
    "/card-bin", response_model=VerificationResponse, status_code=status.HTTP_200_OK
)
async def verify_card_bin(
    request: CardBINVerificationRequest,
    db: AsyncSession = Depends(get_db),
    verification_service: ExternalVerificationService = Depends(
        get_verification_service
    ),
):
    """
    Verify card BIN using BINList database

    Checks:
    - Card scheme (Visa/Mastercard/Amex/etc)
    - Card type (debit/credit/prepaid)
    - Issuing bank
    - Issuing country
    - Country mismatches (card vs transaction vs GeoIP)

    Returns:
    - Risk score (0-100)
    - Recommendation (allow/review/block)
    - Detailed BIN data

    Example:
        ```json
        {
            "bin_number": "411111",
            "transaction_country": "US",
            "geoip_country": "US",
            "transaction_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        ```

    Response:
        ```json
        {
            "success": true,
            "data": {
                "bin": "411111",
                "scheme": "visa",
                "type": "credit",
                "prepaid": false,
                "country": {"alpha2": "US", "name": "United States"},
                "bank": {"name": "Test Bank"},
                "risk_score": 15,
                "recommendation": "allow",
                "country_mismatch": null
            },
            "message": "Card BIN verification complete"
        }
        ```
    """
    try:
        logger.info(
            f"[VerificationAPI] Card BIN verification request: {request.bin_number}"
        )

        # Create logger wrapper
        verification_logger = ExternalVerificationLogger(db, verification_service)

        # Verify card BIN
        result = await verification_logger.verify_card_bin(
            bin_number=request.bin_number,
            transaction_country=request.transaction_country,
            geoip_country=request.geoip_country,
            transaction_id=request.transaction_id,
        )

        return VerificationResponse(
            success=True, data=result, message="Card BIN verification complete"
        )

    except ValueError as e:
        logger.error(f"[VerificationAPI] Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        logger.error(f"[VerificationAPI] Card BIN verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Card BIN verification failed",
        )
