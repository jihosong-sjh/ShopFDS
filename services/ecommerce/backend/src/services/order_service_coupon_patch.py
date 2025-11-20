"""
주문 서비스 쿠폰 적용 패치

이 파일은 order_service.py의 create_order_from_cart 메서드에 쿠폰 적용 기능을 추가하는 방법을 보여줍니다.
"""

# 1. create_order_from_cart 메서드 시그니처에 coupon_code 파라미터 추가:
#    coupon_code: Optional[str] = None,

# 2. 총 금액 계산 후 (# 2. 재고 확인 및 총 금액 계산 섹션 뒤에) 다음 코드 추가:

"""
        # 2.5 쿠폰 적용 (있는 경우)
        discount_amount = 0.0
        applied_coupon_code = None
        
        if coupon_code:
            from decimal import Decimal
            coupon_service = CouponService(self.db)
            
            # 쿠폰 검증
            validation_result = await coupon_service.validate_coupon(
                user_id=user_id,
                coupon_code=coupon_code,
                order_amount=Decimal(str(total_amount)),
            )
            
            if validation_result["is_valid"]:
                discount_amount = validation_result["discount_amount"]
                applied_coupon_code = coupon_code
                total_amount = validation_result["final_amount"]
            else:
                raise ValidationError(f"쿠폰 적용 실패: {validation_result['message']}")
"""

# 3. Order 생성 시 (# 3. 주문 생성 섹션) discount_amount와 coupon_code 추가:

"""
        order = Order(
            order_number=Order.generate_order_number(),
            user_id=user_id,
            total_amount=total_amount,
            discount_amount=discount_amount,  # 추가
            coupon_code=applied_coupon_code,  # 추가
            status=OrderStatus.PENDING,
            shipping_name=shipping_name,
            shipping_address=shipping_address,
            shipping_phone=shipping_phone,
        )
"""

# 4. 주문 확정 후 쿠폰 사용 처리 (# 7. FDS 결과에 따른 처리 섹션에서 정상 거래 시):

"""
        if fds_result["risk_level"] == "low":
            # 정상 거래: 자동 승인
            payment.mark_as_completed(transaction_id=f"TXN-{order.order_number}")
            order.mark_as_paid()
            
            # 쿠폰 사용 처리 (추가)
            if applied_coupon_code:
                coupon_service = CouponService(self.db)
                await coupon_service.use_coupon(
                    user_id=user_id,
                    coupon_code=applied_coupon_code,
                    order_id=order.id,
                )
"""

# 5. 주문 취소 시 쿠폰 복구 (cancel_order 메서드에 추가):

"""
    async def cancel_order(self, order_id: str, reason: str = "사용자 요청"):
        # 기존 코드...
        
        # 쿠폰 복구 (추가)
        if order.coupon_code:
            result = await self.db.execute(
                select(UserCoupon).where(
                    and_(
                        UserCoupon.order_id == order.id,
                        UserCoupon.used_at.isnot(None),
                    )
                )
            )
            user_coupon = result.scalar_one_or_none()
            if user_coupon:
                coupon_service = CouponService(self.db)
                await coupon_service.cancel_coupon_usage(user_coupon.id)
"""
