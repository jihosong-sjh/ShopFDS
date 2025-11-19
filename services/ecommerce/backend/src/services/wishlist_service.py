"""
Wishlist Service

위시리스트(찜 목록) 관리 서비스
"""

import uuid
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from src.models.wishlist_item import WishlistItem
from src.models.product import Product
from src.models.cart import Cart
from src.models.cart_item import CartItem


class WishlistService:
    """위시리스트 서비스"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_wishlist(
        self, user_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> Dict:
        """
        사용자 위시리스트 조회

        Args:
            user_id: 사용자 ID
            page: 페이지 번호
            limit: 페이지당 개수

        Returns:
            위시리스트 항목 목록 및 총 개수
        """
        offset = (page - 1) * limit

        # 위시리스트 항목 조회 (최신순 정렬)
        result = await self.db.execute(
            select(WishlistItem)
            .where(WishlistItem.user_id == user_id)
            .options(selectinload(WishlistItem.product))
            .order_by(WishlistItem.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        wishlist_items = result.scalars().all()

        # 총 개수 조회
        count_result = await self.db.execute(
            select(WishlistItem).where(WishlistItem.user_id == user_id)
        )
        total_count = len(count_result.scalars().all())

        # 응답 포맷팅
        items = []
        for item in wishlist_items:
            product = item.product
            items.append(
                {
                    "id": item.id,
                    "product": {
                        "id": product.id,
                        "name": product.name,
                        "price": product.price,
                        "discounted_price": product.discounted_price,
                        "image_url": product.images[0]
                        if product.images
                        else None,  # 첫 번째 이미지
                        "in_stock": product.stock > 0,
                        "rating": 0.0,  # TODO: 리뷰 평균 평점 계산
                        "review_count": 0,  # TODO: 리뷰 개수 계산
                    },
                    "added_at": item.created_at.isoformat(),
                }
            )

        return {"items": items, "total_count": total_count}

    async def add_to_wishlist(
        self, user_id: uuid.UUID, product_id: uuid.UUID
    ) -> WishlistItem:
        """
        위시리스트에 상품 추가

        Args:
            user_id: 사용자 ID
            product_id: 상품 ID

        Returns:
            생성된 WishlistItem

        Raises:
            ValueError: 이미 위시리스트에 있거나 상품이 존재하지 않는 경우
        """
        # 1. 상품 존재 여부 확인
        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise ValueError("상품을 찾을 수 없습니다")

        # 2. 중복 확인
        result = await self.db.execute(
            select(WishlistItem).where(
                and_(
                    WishlistItem.user_id == user_id,
                    WishlistItem.product_id == product_id,
                )
            )
        )
        existing_item = result.scalar_one_or_none()
        if existing_item:
            raise ValueError("이미 위시리스트에 추가된 상품입니다")

        # 3. 위시리스트 항목 생성
        wishlist_item = WishlistItem(
            id=uuid.uuid4(), user_id=user_id, product_id=product_id
        )
        self.db.add(wishlist_item)
        await self.db.commit()
        await self.db.refresh(wishlist_item)

        return wishlist_item

    async def remove_from_wishlist(
        self, user_id: uuid.UUID, item_id: uuid.UUID
    ) -> bool:
        """
        위시리스트에서 상품 삭제

        Args:
            user_id: 사용자 ID
            item_id: 위시리스트 항목 ID

        Returns:
            삭제 성공 여부

        Raises:
            ValueError: 항목을 찾을 수 없거나 권한이 없는 경우
        """
        # 1. 위시리스트 항목 조회 (본인 확인)
        result = await self.db.execute(
            select(WishlistItem).where(
                and_(WishlistItem.id == item_id, WishlistItem.user_id == user_id)
            )
        )
        wishlist_item = result.scalar_one_or_none()

        if not wishlist_item:
            raise ValueError("위시리스트 항목을 찾을 수 없거나 권한이 없습니다")

        # 2. 삭제
        await self.db.delete(wishlist_item)
        await self.db.commit()

        return True

    async def move_to_cart(
        self, user_id: uuid.UUID, item_ids: List[uuid.UUID]
    ) -> Dict:
        """
        위시리스트 항목을 장바구니로 이동

        Args:
            user_id: 사용자 ID
            item_ids: 위시리스트 항목 ID 목록

        Returns:
            성공/실패 개수 및 실패 항목 목록
        """
        success_count = 0
        failed_items = []

        # 사용자의 장바구니 조회
        result = await self.db.execute(select(Cart).where(Cart.user_id == user_id))
        cart = result.scalar_one_or_none()

        if not cart:
            # 장바구니가 없으면 생성
            cart = Cart(id=uuid.uuid4(), user_id=user_id)
            self.db.add(cart)
            await self.db.flush()

        for item_id in item_ids:
            try:
                # 1. 위시리스트 항목 조회
                result = await self.db.execute(
                    select(WishlistItem)
                    .where(
                        and_(
                            WishlistItem.id == item_id,
                            WishlistItem.user_id == user_id,
                        )
                    )
                    .options(selectinload(WishlistItem.product))
                )
                wishlist_item = result.scalar_one_or_none()

                if not wishlist_item:
                    failed_items.append(
                        {"item_id": item_id, "reason": "위시리스트 항목을 찾을 수 없습니다"}
                    )
                    continue

                # 2. 상품 재고 확인
                product = wishlist_item.product
                if product.stock <= 0:
                    failed_items.append(
                        {"item_id": item_id, "reason": "재고가 없습니다"}
                    )
                    continue

                # 3. 장바구니에 추가 (기존 항목 있으면 수량 증가)
                result = await self.db.execute(
                    select(CartItem).where(
                        and_(
                            CartItem.cart_id == cart.id,
                            CartItem.product_id == wishlist_item.product_id,
                        )
                    )
                )
                cart_item = result.scalar_one_or_none()

                if cart_item:
                    # 기존 장바구니 항목 - 수량 증가
                    cart_item.quantity += 1
                else:
                    # 새 장바구니 항목 생성
                    cart_item = CartItem(
                        id=uuid.uuid4(),
                        cart_id=cart.id,
                        product_id=wishlist_item.product_id,
                        quantity=1,
                    )
                    self.db.add(cart_item)

                # 4. 위시리스트에서 삭제
                await self.db.delete(wishlist_item)

                success_count += 1

            except Exception as e:
                failed_items.append({"item_id": item_id, "reason": str(e)})

        await self.db.commit()

        return {"success_count": success_count, "failed_items": failed_items}

    async def check_product_in_wishlist(
        self, user_id: uuid.UUID, product_id: uuid.UUID
    ) -> bool:
        """
        상품이 사용자 위시리스트에 있는지 확인

        Args:
            user_id: 사용자 ID
            product_id: 상품 ID

        Returns:
            위시리스트에 있으면 True, 없으면 False
        """
        result = await self.db.execute(
            select(WishlistItem).where(
                and_(
                    WishlistItem.user_id == user_id,
                    WishlistItem.product_id == product_id,
                )
            )
        )
        item = result.scalar_one_or_none()
        return item is not None
