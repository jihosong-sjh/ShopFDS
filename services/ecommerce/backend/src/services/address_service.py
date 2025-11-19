"""
Address Service

배송지 관리 서비스
"""

import uuid
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from fastapi import HTTPException, status

from src.models.address import Address


class AddressService:
    """배송지 서비스"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_addresses(self, user_id: uuid.UUID) -> List[Dict]:
        """
        사용자 배송지 목록 조회

        Args:
            user_id: 사용자 ID

        Returns:
            배송지 목록 (기본 배송지 우선, 최신순)
        """
        result = await self.db.execute(
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.created_at.desc())
        )
        addresses = result.scalars().all()

        return [
            {
                "id": addr.id,
                "address_name": addr.address_name,
                "recipient_name": addr.recipient_name,
                "phone": addr.phone,
                "zipcode": addr.zipcode,
                "address": addr.address,
                "address_detail": addr.address_detail,
                "is_default": addr.is_default,
                "created_at": addr.created_at.isoformat(),
                "updated_at": addr.updated_at.isoformat(),
            }
            for addr in addresses
        ]

    async def get_address_by_id(
        self, address_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Address]:
        """
        배송지 ID로 조회 (사용자 검증 포함)

        Args:
            address_id: 배송지 ID
            user_id: 사용자 ID

        Returns:
            배송지 객체 또는 None
        """
        result = await self.db.execute(
            select(Address).where(
                and_(Address.id == address_id, Address.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def create_address(
        self,
        user_id: uuid.UUID,
        address_name: str,
        recipient_name: str,
        phone: str,
        zipcode: str,
        address: str,
        address_detail: Optional[str] = None,
        is_default: bool = False,
    ) -> Address:
        """
        새 배송지 추가

        Args:
            user_id: 사용자 ID
            address_name: 배송지 별칭 (예: "집", "회사")
            recipient_name: 수령인 이름
            phone: 수령인 전화번호
            zipcode: 우편번호
            address: 기본 주소
            address_detail: 상세 주소 (선택)
            is_default: 기본 배송지 여부

        Returns:
            생성된 배송지 객체
        """
        # 기본 배송지로 설정하는 경우, 기존 기본 배송지 해제
        if is_default:
            await self._unset_default_address(user_id)

        new_address = Address(
            id=uuid.uuid4(),
            user_id=user_id,
            address_name=address_name,
            recipient_name=recipient_name,
            phone=phone,
            zipcode=zipcode,
            address=address,
            address_detail=address_detail,
            is_default=is_default,
        )

        self.db.add(new_address)
        await self.db.commit()
        await self.db.refresh(new_address)

        return new_address

    async def update_address(
        self,
        address_id: uuid.UUID,
        user_id: uuid.UUID,
        address_name: str,
        recipient_name: str,
        phone: str,
        zipcode: str,
        address: str,
        address_detail: Optional[str] = None,
        is_default: bool = False,
    ) -> Address:
        """
        배송지 수정

        Args:
            address_id: 배송지 ID
            user_id: 사용자 ID
            address_name: 배송지 별칭
            recipient_name: 수령인 이름
            phone: 수령인 전화번호
            zipcode: 우편번호
            address: 기본 주소
            address_detail: 상세 주소 (선택)
            is_default: 기본 배송지 여부

        Returns:
            수정된 배송지 객체

        Raises:
            HTTPException: 배송지를 찾을 수 없거나 권한이 없는 경우
        """
        existing_address = await self.get_address_by_id(address_id, user_id)
        if not existing_address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="배송지를 찾을 수 없습니다",
            )

        # 기본 배송지로 설정하는 경우, 기존 기본 배송지 해제
        if is_default and not existing_address.is_default:
            await self._unset_default_address(user_id)

        # 배송지 정보 업데이트
        existing_address.address_name = address_name
        existing_address.recipient_name = recipient_name
        existing_address.phone = phone
        existing_address.zipcode = zipcode
        existing_address.address = address
        existing_address.address_detail = address_detail
        existing_address.is_default = is_default

        await self.db.commit()
        await self.db.refresh(existing_address)

        return existing_address

    async def delete_address(self, address_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        배송지 삭제

        Args:
            address_id: 배송지 ID
            user_id: 사용자 ID

        Raises:
            HTTPException: 배송지를 찾을 수 없거나 권한이 없는 경우
        """
        existing_address = await self.get_address_by_id(address_id, user_id)
        if not existing_address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="배송지를 찾을 수 없습니다",
            )

        await self.db.delete(existing_address)
        await self.db.commit()

    async def set_default_address(
        self, address_id: uuid.UUID, user_id: uuid.UUID
    ) -> Address:
        """
        기본 배송지 설정

        Args:
            address_id: 배송지 ID
            user_id: 사용자 ID

        Returns:
            기본 배송지로 설정된 배송지 객체

        Raises:
            HTTPException: 배송지를 찾을 수 없거나 권한이 없는 경우
        """
        existing_address = await self.get_address_by_id(address_id, user_id)
        if not existing_address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="배송지를 찾을 수 없습니다",
            )

        # 기존 기본 배송지 해제
        await self._unset_default_address(user_id)

        # 새 기본 배송지 설정
        existing_address.is_default = True
        await self.db.commit()
        await self.db.refresh(existing_address)

        return existing_address

    async def get_default_address(self, user_id: uuid.UUID) -> Optional[Address]:
        """
        사용자의 기본 배송지 조회

        Args:
            user_id: 사용자 ID

        Returns:
            기본 배송지 객체 또는 None
        """
        result = await self.db.execute(
            select(Address).where(and_(Address.user_id == user_id, Address.is_default))
        )
        return result.scalar_one_or_none()

    async def _unset_default_address(self, user_id: uuid.UUID) -> None:
        """
        사용자의 기존 기본 배송지 해제 (내부 메서드)

        Args:
            user_id: 사용자 ID
        """
        await self.db.execute(
            update(Address)
            .where(and_(Address.user_id == user_id, Address.is_default))
            .values(is_default=False)
        )
        await self.db.flush()
