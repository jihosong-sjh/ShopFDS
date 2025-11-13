"""
장바구니 서비스

장바구니 추가/수정/삭제 등 장바구니 관련 비즈니스 로직
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.cart import Cart, CartItem
from models.product import Product
from utils.exceptions import ResourceNotFoundError, ValidationError


class CartService:
    """장바구니 관련 비즈니스 로직"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_cart(self, user_id: str) -> Cart:
        """
        사용자의 장바구니 조회 또는 생성

        Args:
            user_id: 사용자 ID

        Returns:
            Cart: 장바구니 객체
        """
        # 기존 장바구니 조회
        result = await self.db.execute(
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
        )
        cart = result.scalars().first()

        if not cart:
            # 장바구니가 없으면 생성
            cart = Cart(user_id=user_id)
            self.db.add(cart)
            await self.db.commit()
            await self.db.refresh(cart)

        return cart

    async def get_cart(self, user_id: str) -> Cart:
        """
        사용자의 장바구니 조회

        Args:
            user_id: 사용자 ID

        Returns:
            Cart: 장바구니 객체 (상품 정보 포함)
        """
        cart = await self.get_or_create_cart(user_id)

        # 장바구니 아이템 새로고침 (상품 정보 포함)
        await self.db.refresh(cart, ["items"])

        return cart

    async def add_item(self, user_id: str, product_id: str, quantity: int = 1) -> CartItem:
        """
        장바구니에 상품 추가

        Args:
            user_id: 사용자 ID
            product_id: 상품 ID
            quantity: 수량

        Returns:
            CartItem: 추가된 장바구니 항목

        Raises:
            ResourceNotFoundError: 상품을 찾을 수 없는 경우
            ValidationError: 재고 부족 또는 유효하지 않은 수량
        """
        if quantity <= 0:
            raise ValidationError("수량은 1 이상이어야 합니다")

        # 상품 조회 및 재고 확인
        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalars().first()

        if not product:
            raise ResourceNotFoundError(f"상품을 찾을 수 없습니다: {product_id}")

        if not product.can_purchase(quantity):
            raise ValidationError(
                f"재고 부족: 요청 {quantity}개, 재고 {product.stock_quantity}개"
            )

        # 장바구니 조회
        cart = await self.get_or_create_cart(user_id)

        # 이미 장바구니에 있는 상품인지 확인
        result = await self.db.execute(
            select(CartItem)
            .where(CartItem.cart_id == cart.id)
            .where(CartItem.product_id == product_id)
        )
        existing_item = result.scalars().first()

        if existing_item:
            # 기존 항목의 수량 증가
            new_quantity = existing_item.quantity + quantity
            if not product.can_purchase(new_quantity):
                raise ValidationError(
                    f"재고 부족: 요청 {new_quantity}개, 재고 {product.stock_quantity}개"
                )
            existing_item.quantity = new_quantity
            await self.db.commit()
            await self.db.refresh(existing_item)
            return existing_item
        else:
            # 새 항목 추가
            cart_item = CartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=quantity
            )
            self.db.add(cart_item)
            await self.db.commit()
            await self.db.refresh(cart_item)
            return cart_item

    async def update_item_quantity(
        self,
        user_id: str,
        cart_item_id: str,
        quantity: int
    ) -> CartItem:
        """
        장바구니 항목 수량 수정

        Args:
            user_id: 사용자 ID
            cart_item_id: 장바구니 항목 ID
            quantity: 새로운 수량

        Returns:
            CartItem: 수정된 장바구니 항목

        Raises:
            ResourceNotFoundError: 항목을 찾을 수 없는 경우
            ValidationError: 재고 부족 또는 유효하지 않은 수량
        """
        if quantity <= 0:
            raise ValidationError("수량은 1 이상이어야 합니다")

        # 장바구니 항목 조회 (사용자 권한 확인 포함)
        cart = await self.get_or_create_cart(user_id)

        result = await self.db.execute(
            select(CartItem)
            .where(CartItem.id == cart_item_id)
            .where(CartItem.cart_id == cart.id)
            .options(selectinload(CartItem.product))
        )
        cart_item = result.scalars().first()

        if not cart_item:
            raise ResourceNotFoundError(f"장바구니 항목을 찾을 수 없습니다: {cart_item_id}")

        # 재고 확인
        if cart_item.product and not cart_item.product.can_purchase(quantity):
            raise ValidationError(
                f"재고 부족: 요청 {quantity}개, 재고 {cart_item.product.stock_quantity}개"
            )

        cart_item.quantity = quantity
        await self.db.commit()
        await self.db.refresh(cart_item)

        return cart_item

    async def remove_item(self, user_id: str, cart_item_id: str) -> bool:
        """
        장바구니 항목 삭제

        Args:
            user_id: 사용자 ID
            cart_item_id: 장바구니 항목 ID

        Returns:
            bool: 삭제 성공 여부

        Raises:
            ResourceNotFoundError: 항목을 찾을 수 없는 경우
        """
        # 장바구니 항목 조회 (사용자 권한 확인 포함)
        cart = await self.get_or_create_cart(user_id)

        result = await self.db.execute(
            select(CartItem)
            .where(CartItem.id == cart_item_id)
            .where(CartItem.cart_id == cart.id)
        )
        cart_item = result.scalars().first()

        if not cart_item:
            raise ResourceNotFoundError(f"장바구니 항목을 찾을 수 없습니다: {cart_item_id}")

        await self.db.delete(cart_item)
        await self.db.commit()

        return True

    async def clear_cart(self, user_id: str) -> bool:
        """
        장바구니 전체 비우기

        Args:
            user_id: 사용자 ID

        Returns:
            bool: 성공 여부
        """
        cart = await self.get_or_create_cart(user_id)

        # 모든 항목 삭제
        result = await self.db.execute(
            select(CartItem).where(CartItem.cart_id == cart.id)
        )
        cart_items = result.scalars().all()

        for item in cart_items:
            await self.db.delete(item)

        await self.db.commit()

        return True

    async def get_cart_summary(self, user_id: str) -> dict:
        """
        장바구니 요약 정보

        Args:
            user_id: 사용자 ID

        Returns:
            dict: 장바구니 요약 (총 금액, 아이템 수 등)
        """
        cart = await self.get_cart(user_id)

        total_amount = 0.0
        total_items = 0
        items_detail = []

        for item in cart.items:
            if item.product:
                subtotal = item.get_subtotal()
                total_amount += subtotal
                total_items += item.quantity

                items_detail.append({
                    "cart_item_id": str(item.id),
                    "product_id": str(item.product.id),
                    "product_name": item.product.name,
                    "unit_price": float(item.product.price),
                    "quantity": item.quantity,
                    "subtotal": subtotal,
                    "image_url": item.product.image_url,
                    "is_available": item.product.is_available()
                })

        return {
            "cart_id": str(cart.id),
            "total_amount": total_amount,
            "total_items": total_items,
            "items": items_detail
        }
