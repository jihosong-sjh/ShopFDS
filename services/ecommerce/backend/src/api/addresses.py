"""
Address API Endpoints

배송지 관리 API
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator
import re

from src.models.base import get_db
from src.services.address_service import AddressService
from src.middleware.auth import get_current_user
from src.models.user import User


router = APIRouter(prefix="/v1/addresses", tags=["Addresses"])


class CreateAddressRequest(BaseModel):
    """배송지 추가 요청"""

    address_name: str = Field(..., min_length=1, max_length=100, description="배송지 별칭 (예: 집, 회사)")
    recipient_name: str = Field(..., min_length=1, max_length=100, description="수령인 이름")
    phone: str = Field(..., description="수령인 전화번호")
    zipcode: str = Field(..., min_length=5, max_length=10, description="우편번호")
    address: str = Field(..., min_length=1, max_length=500, description="기본 주소")
    address_detail: Optional[str] = Field(None, max_length=500, description="상세 주소")
    is_default: bool = Field(False, description="기본 배송지 여부")

    @validator("phone")
    def validate_phone(cls, v):
        """전화번호 형식 검증"""
        # 한국 전화번호 형식: 010-1234-5678, 02-1234-5678 등
        phone_pattern = r"^0\d{1,2}-\d{3,4}-\d{4}$"
        if not re.match(phone_pattern, v):
            raise ValueError("전화번호 형식이 올바르지 않습니다 (예: 010-1234-5678)")
        return v


class UpdateAddressRequest(BaseModel):
    """배송지 수정 요청"""

    address_name: str = Field(..., min_length=1, max_length=100)
    recipient_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(...)
    zipcode: str = Field(..., min_length=5, max_length=10)
    address: str = Field(..., min_length=1, max_length=500)
    address_detail: Optional[str] = Field(None, max_length=500)
    is_default: bool = Field(False)

    @validator("phone")
    def validate_phone(cls, v):
        """전화번호 형식 검증"""
        phone_pattern = r"^0\d{1,2}-\d{3,4}-\d{4}$"
        if not re.match(phone_pattern, v):
            raise ValueError("전화번호 형식이 올바르지 않습니다 (예: 010-1234-5678)")
        return v


class AddressResponse(BaseModel):
    """배송지 응답"""

    id: str
    address_name: str
    recipient_name: str
    phone: str
    zipcode: str
    address: str
    address_detail: Optional[str]
    is_default: bool
    created_at: str
    updated_at: str


class AddressListResponse(BaseModel):
    """배송지 목록 응답"""

    addresses: List[AddressResponse]


@router.get("", response_model=AddressListResponse)
async def get_addresses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    배송지 목록 조회

    로그인한 사용자의 배송지 목록을 조회합니다.
    기본 배송지가 최상단에 표시됩니다.
    """
    address_service = AddressService(db)
    addresses = await address_service.get_addresses(user_id=current_user.id)

    return AddressListResponse(
        addresses=[AddressResponse(**addr) for addr in addresses]
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AddressResponse)
async def create_address(
    request: CreateAddressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    배송지 추가

    새 배송지를 추가합니다.
    is_default를 true로 설정하면 기존 기본 배송지가 자동으로 해제됩니다.
    """
    address_service = AddressService(db)

    new_address = await address_service.create_address(
        user_id=current_user.id,
        address_name=request.address_name,
        recipient_name=request.recipient_name,
        phone=request.phone,
        zipcode=request.zipcode,
        address=request.address,
        address_detail=request.address_detail,
        is_default=request.is_default,
    )

    return AddressResponse(
        id=str(new_address.id),
        address_name=new_address.address_name,
        recipient_name=new_address.recipient_name,
        phone=new_address.phone,
        zipcode=new_address.zipcode,
        address=new_address.address,
        address_detail=new_address.address_detail,
        is_default=new_address.is_default,
        created_at=new_address.created_at.isoformat(),
        updated_at=new_address.updated_at.isoformat(),
    )


@router.put("/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: str,
    request: UpdateAddressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    배송지 수정

    기존 배송지 정보를 수정합니다.
    is_default를 true로 설정하면 기존 기본 배송지가 자동으로 해제됩니다.
    """
    try:
        address_uuid = uuid.UUID(address_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="올바르지 않은 배송지 ID 형식입니다",
        )

    address_service = AddressService(db)

    updated_address = await address_service.update_address(
        address_id=address_uuid,
        user_id=current_user.id,
        address_name=request.address_name,
        recipient_name=request.recipient_name,
        phone=request.phone,
        zipcode=request.zipcode,
        address=request.address,
        address_detail=request.address_detail,
        is_default=request.is_default,
    )

    return AddressResponse(
        id=str(updated_address.id),
        address_name=updated_address.address_name,
        recipient_name=updated_address.recipient_name,
        phone=updated_address.phone,
        zipcode=updated_address.zipcode,
        address=updated_address.address,
        address_detail=updated_address.address_detail,
        is_default=updated_address.is_default,
        created_at=updated_address.created_at.isoformat(),
        updated_at=updated_address.updated_at.isoformat(),
    )


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    배송지 삭제

    배송지를 삭제합니다.
    """
    try:
        address_uuid = uuid.UUID(address_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="올바르지 않은 배송지 ID 형식입니다",
        )

    address_service = AddressService(db)
    await address_service.delete_address(
        address_id=address_uuid, user_id=current_user.id
    )

    return None


@router.post("/{address_id}/set-default", response_model=AddressResponse)
async def set_default_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    기본 배송지 설정

    지정한 배송지를 기본 배송지로 설정합니다.
    기존 기본 배송지는 자동으로 해제됩니다.
    """
    try:
        address_uuid = uuid.UUID(address_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="올바르지 않은 배송지 ID 형식입니다",
        )

    address_service = AddressService(db)
    default_address = await address_service.set_default_address(
        address_id=address_uuid, user_id=current_user.id
    )

    return AddressResponse(
        id=str(default_address.id),
        address_name=default_address.address_name,
        recipient_name=default_address.recipient_name,
        phone=default_address.phone,
        zipcode=default_address.zipcode,
        address=default_address.address,
        address_detail=default_address.address_detail,
        is_default=default_address.is_default,
        created_at=default_address.created_at.isoformat(),
        updated_at=default_address.updated_at.isoformat(),
    )
