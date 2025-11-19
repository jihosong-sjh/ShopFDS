/**
 * 쿠폰 입력 컴포넌트
 *
 * 쿠폰 코드 입력, 적용, 제거 기능을 제공합니다.
 */

import React, { useState } from 'react';
import { useValidateCoupon, useAvailableCoupons } from '../hooks/useCoupons';

interface CouponInputProps {
  orderAmount: number;
  onApply: (couponCode: string, discountAmount: number) => void;
  onRemove: () => void;
  appliedCoupon?: {
    code: string;
    discountAmount: number;
  };
}

export default function CouponInput({
  orderAmount,
  onApply,
  onRemove,
  appliedCoupon,
}: CouponInputProps) {
  const [couponCode, setCouponCode] = useState('');
  const [showModal, setShowModal] = useState(false);

  const validateCoupon = useValidateCoupon();
  const { data: availableCoupons, isLoading: isLoadingCoupons } = useAvailableCoupons();

  const handleApplyCoupon = async () => {
    if (!couponCode.trim()) return;

    try {
      const result = await validateCoupon.mutateAsync({
        couponCode: couponCode.trim(),
        orderAmount,
      });

      if (result.is_valid) {
        onApply(couponCode.trim(), result.discount_amount);
        setCouponCode('');
      }
    } catch (error) {
      // 에러는 validateCoupon.error에서 처리
    }
  };

  const handleSelectCoupon = async (code: string) => {
    try {
      const result = await validateCoupon.mutateAsync({
        couponCode: code,
        orderAmount,
      });

      if (result.is_valid) {
        onApply(code, result.discount_amount);
        setShowModal(false);
      }
    } catch (error) {
      // 에러 처리
    }
  };

  const handleRemoveCoupon = () => {
    onRemove();
    setCouponCode('');
  };

  return (
    <div className="space-y-4">
      {/* 쿠폰 입력 영역 */}
      {!appliedCoupon ? (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            쿠폰 코드
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={couponCode}
              onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
              placeholder="쿠폰 코드 입력"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              data-testid="coupon-input"
            />
            <button
              onClick={handleApplyCoupon}
              disabled={!couponCode.trim() || validateCoupon.isPending}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              data-testid="apply-coupon-button"
            >
              {validateCoupon.isPending ? '확인 중...' : '적용'}
            </button>
          </div>

          {/* 쿠폰 적용 성공 메시지 */}
          {validateCoupon.isSuccess && validateCoupon.data.is_valid && (
            <div
              className="mt-2 p-3 bg-green-50 border border-green-200 rounded-md text-green-700 text-sm"
              data-testid="coupon-success"
            >
              쿠폰이 적용되었습니다
            </div>
          )}

          {/* 쿠폰 적용 실패 메시지 */}
          {validateCoupon.isError && (
            <div
              className="mt-2 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm"
              data-testid="coupon-error"
            >
              {(validateCoupon.error as any)?.response?.data?.detail || '쿠폰 적용에 실패했습니다'}
            </div>
          )}

          {validateCoupon.isSuccess && !validateCoupon.data.is_valid && (
            <div
              className="mt-2 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm"
              data-testid="coupon-error"
            >
              {validateCoupon.data.message}
            </div>
          )}

          {/* 내 쿠폰 보기 버튼 */}
          <button
            onClick={() => setShowModal(true)}
            className="mt-2 text-sm text-blue-600 hover:text-blue-700 hover:underline"
            data-testid="my-coupons-button"
          >
            내 쿠폰 보기
          </button>
        </div>
      ) : (
        /* 적용된 쿠폰 표시 */
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
          <div className="flex justify-between items-center">
            <div>
              <div className="text-sm font-medium text-gray-700">
                적용된 쿠폰
              </div>
              <div className="text-lg font-semibold text-blue-600">
                {appliedCoupon.code}
              </div>
              <div className="text-sm text-gray-600">
                -{appliedCoupon.discountAmount.toLocaleString()}원 할인
              </div>
            </div>
            <button
              onClick={handleRemoveCoupon}
              className="px-4 py-2 text-sm text-red-600 hover:text-red-700 hover:underline"
              data-testid="remove-coupon-button"
            >
              삭제
            </button>
          </div>
        </div>
      )}

      {/* 쿠폰 목록 모달 */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div
            className="bg-white rounded-lg p-6 max-w-md w-full max-h-[80vh] overflow-y-auto"
            data-testid="coupon-list-modal"
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">내 쿠폰</h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>

            {isLoadingCoupons ? (
              <div className="text-center py-8 text-gray-500">로딩 중...</div>
            ) : availableCoupons && availableCoupons.length > 0 ? (
              <div className="space-y-3">
                {availableCoupons.map((coupon) => (
                  <div
                    key={coupon.id}
                    className="p-4 border border-gray-200 rounded-md hover:border-blue-500 cursor-pointer"
                    data-testid="coupon-item"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <div className="font-medium text-gray-900">
                          {coupon.coupon_name}
                        </div>
                        <div className="text-sm text-gray-600">
                          {coupon.coupon_code}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-semibold text-blue-600">
                          {coupon.discount_type === 'FIXED'
                            ? `${coupon.discount_value.toLocaleString()}원`
                            : `${coupon.discount_value}%`}
                        </div>
                      </div>
                    </div>

                    {coupon.description && (
                      <div className="text-sm text-gray-500 mb-2">
                        {coupon.description}
                      </div>
                    )}

                    <div className="text-xs text-gray-400 mb-2">
                      최소 구매: {coupon.min_purchase_amount.toLocaleString()}원
                      {coupon.max_discount_amount && (
                        <> | 최대 할인: {coupon.max_discount_amount.toLocaleString()}원</>
                      )}
                    </div>

                    <div className="text-xs text-gray-400 mb-3">
                      만료일: {new Date(coupon.valid_until).toLocaleDateString()}
                    </div>

                    <button
                      onClick={() => handleSelectCoupon(coupon.coupon_code)}
                      disabled={!coupon.is_usable}
                      className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm"
                      data-testid="select-coupon-button"
                    >
                      {coupon.is_usable ? '적용하기' : coupon.reason}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                사용 가능한 쿠폰이 없습니다
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
