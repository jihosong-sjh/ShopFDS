/**
 * 쿠폰 관리 Hook
 *
 * React Query를 사용하여 쿠폰 조회, 발급, 검증 기능을 제공합니다.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

// 타입 정의
export interface UserCoupon {
  id: string;
  coupon_code: string;
  coupon_name: string;
  description?: string;
  discount_type: 'FIXED' | 'PERCENT';
  discount_value: number;
  max_discount_amount?: number;
  min_purchase_amount: number;
  valid_from: string;
  valid_until: string;
  issued_at: string;
  used_at?: string;
  is_usable: boolean;
  reason: string;
}

export interface CouponValidationResult {
  is_valid: boolean;
  discount_amount: number;
  final_amount: number;
  message: string;
}

/**
 * 사용자 쿠폰 목록 조회 Hook
 */
export function useUserCoupons(status?: 'available' | 'used' | 'expired') {
  return useQuery({
    queryKey: ['coupons', 'me', status],
    queryFn: async () => {
      const params = status ? { status } : {};
      const response = await api.get('/coupons/me', { params });
      return response.data.coupons as UserCoupon[];
    },
  });
}

/**
 * 쿠폰 발급 Hook
 */
export function useIssueCoupon() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (couponCode: string) => {
      const response = await api.post('/coupons/issue', {
        coupon_code: couponCode,
      });
      return response.data;
    },
    onSuccess: () => {
      // 쿠폰 목록 갱신
      queryClient.invalidateQueries({ queryKey: ['coupons', 'me'] });
    },
  });
}

/**
 * 쿠폰 검증 Hook
 */
export function useValidateCoupon() {
  return useMutation({
    mutationFn: async ({
      couponCode,
      orderAmount,
    }: {
      couponCode: string;
      orderAmount: number;
    }) => {
      const response = await api.post('/coupons/validate', {
        coupon_code: couponCode,
        order_amount: orderAmount,
      });
      return response.data as CouponValidationResult;
    },
  });
}

/**
 * 사용 가능한 쿠폰만 조회
 */
export function useAvailableCoupons() {
  return useUserCoupons('available');
}
