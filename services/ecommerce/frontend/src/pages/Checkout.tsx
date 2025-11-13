/**
 * 주문/결제 페이지
 *
 * T043: 주문/결제 페이지 구현
 * T063: 결제 페이지에 추가 인증 플로우 통합
 */

import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { cartApi, ordersApi, authApi, queryKeys } from '../services/api';
import { useCartStore } from '../stores/cartStore';
import { OTPModal } from '../components/OTPModal';

export const Checkout: React.FC = () => {
  const navigate = useNavigate();
  const resetCartCount = useCartStore((state) => state.resetCartCount);

  const [formData, setFormData] = useState({
    shipping_name: '',
    shipping_address: '',
    shipping_phone: '',
    card_number: '',
    card_expiry: '',
    card_cvv: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // OTP 모달 상태 (T063)
  const [showOtpModal, setShowOtpModal] = useState(false);
  const [otpToken, setOtpToken] = useState('');
  const [otpAttempts, setOtpAttempts] = useState(3);
  const [pendingOrderData, setPendingOrderData] = useState<any>(null);

  // 장바구니 조회
  const { data: cart, isLoading: cartLoading } = useQuery({
    queryKey: queryKeys.cart.current,
    queryFn: cartApi.getCart,
  });

  // 주문 생성 (T063: OTP 플로우 통합)
  const createOrderMutation = useMutation({
    mutationFn: ordersApi.createOrder,
    onSuccess: (data) => {
      // FDS 위험도에 따른 처리
      if (data.fds_result.requires_verification) {
        // 중간 위험도: 추가 인증 필요
        setPendingOrderData({
          shipping_name: formData.shipping_name,
          shipping_address: formData.shipping_address,
          shipping_phone: formData.shipping_phone,
          payment_info: {
            card_number: formData.card_number,
            card_expiry: formData.card_expiry,
            card_cvv: formData.card_cvv,
          },
        });

        // OTP 요청
        requestOtpMutation.mutate({ phone_number: formData.shipping_phone });
      } else if (data.order) {
        // 낮은 위험도: 주문 완료
        resetCartCount();
        navigate(`/orders/${data.order.id}`);
      } else {
        // 고위험: 차단됨
        setErrors({
          submit: data.message || '거래가 차단되었습니다. 고객센터로 문의해주세요.',
        });
      }
    },
    onError: (error: any) => {
      setErrors({
        submit: error.response?.data?.detail || '주문 처리 중 오류가 발생했습니다.',
      });
    },
  });

  // OTP 요청 (T063)
  const requestOtpMutation = useMutation({
    mutationFn: authApi.requestOtp,
    onSuccess: (data) => {
      setOtpToken(data.otp_token);
      setOtpAttempts(3);
      setShowOtpModal(true);
    },
    onError: (error: any) => {
      setErrors({
        submit: error.response?.data?.detail || 'OTP 전송에 실패했습니다.',
      });
    },
  });

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.shipping_name) newErrors.shipping_name = '수령인 이름을 입력해주세요.';
    if (!formData.shipping_address) newErrors.shipping_address = '배송 주소를 입력해주세요.';

    const phoneRegex = /^010-\d{4}-\d{4}$/;
    if (!formData.shipping_phone) {
      newErrors.shipping_phone = '연락처를 입력해주세요.';
    } else if (!phoneRegex.test(formData.shipping_phone)) {
      newErrors.shipping_phone = '올바른 형식이 아닙니다. (예: 010-1234-5678)';
    }

    const cardRegex = /^\d{16}$/;
    if (!formData.card_number) {
      newErrors.card_number = '카드 번호를 입력해주세요.';
    } else if (!cardRegex.test(formData.card_number.replace(/-/g, ''))) {
      newErrors.card_number = '16자리 카드 번호를 입력해주세요.';
    }

    const expiryRegex = /^(0[1-9]|1[0-2])\/\d{2}$/;
    if (!formData.card_expiry) {
      newErrors.card_expiry = '유효기간을 입력해주세요.';
    } else if (!expiryRegex.test(formData.card_expiry)) {
      newErrors.card_expiry = '올바른 형식이 아닙니다. (예: 12/25)';
    }

    const cvvRegex = /^\d{3}$/;
    if (!formData.card_cvv) {
      newErrors.card_cvv = 'CVV를 입력해주세요.';
    } else if (!cvvRegex.test(formData.card_cvv)) {
      newErrors.card_cvv = '3자리 숫자를 입력해주세요.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    createOrderMutation.mutate({
      shipping_name: formData.shipping_name,
      shipping_address: formData.shipping_address,
      shipping_phone: formData.shipping_phone,
      payment_info: {
        card_number: formData.card_number,
        card_expiry: formData.card_expiry,
        card_cvv: formData.card_cvv,
      },
    });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  // OTP 검증 핸들러 (T063)
  const handleOtpVerify = async (otpCode: string) => {
    try {
      const result = await authApi.verifyOtp({
        otp_token: otpToken,
        otp_code: otpCode,
      });

      if (result.verified) {
        // OTP 검증 성공: otp_token을 포함하여 주문 재시도
        const orderData = {
          ...pendingOrderData,
          otp_token: otpToken,
        };

        const response = await ordersApi.createOrder(orderData);

        if (response.order) {
          setShowOtpModal(false);
          resetCartCount();
          navigate(`/orders/${response.order.id}`);
        } else {
          throw new Error(response.message || '주문 처리에 실패했습니다.');
        }
      } else {
        setOtpAttempts((prev) => prev - 1);
        if (otpAttempts <= 1) {
          setShowOtpModal(false);
          setErrors({
            submit: '인증 실패 횟수를 초과했습니다. 거래가 차단되었습니다.',
          });
        }
        throw new Error('인증번호가 올바르지 않습니다.');
      }
    } catch (error: any) {
      throw error;
    }
  };

  // OTP 재전송 핸들러 (T063)
  const handleOtpResend = async () => {
    await requestOtpMutation.mutateAsync({ phone_number: formData.shipping_phone });
  };

  // OTP 모달 닫기 핸들러 (T063)
  const handleOtpModalClose = () => {
    setShowOtpModal(false);
    setPendingOrderData(null);
    setOtpToken('');
    setErrors({
      submit: '추가 인증을 취소했습니다.',
    });
  };

  if (cartLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <p className="text-gray-600 mb-4">장바구니가 비어있습니다.</p>
        <button
          onClick={() => navigate('/products')}
          className="px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          쇼핑하러 가기
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">주문/결제</h1>

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 왼쪽: 배송 정보 및 결제 정보 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 배송 정보 */}
            <div className="border rounded-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">배송 정보</h2>

              <div className="space-y-4">
                <div>
                  <label htmlFor="shipping_name" className="block text-sm font-medium text-gray-700">
                    수령인 이름 *
                  </label>
                  <input
                    type="text"
                    id="shipping_name"
                    name="shipping_name"
                    value={formData.shipping_name}
                    onChange={handleChange}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="홍길동"
                  />
                  {errors.shipping_name && (
                    <p className="mt-1 text-sm text-red-600">{errors.shipping_name}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="shipping_address" className="block text-sm font-medium text-gray-700">
                    배송 주소 *
                  </label>
                  <textarea
                    id="shipping_address"
                    name="shipping_address"
                    value={formData.shipping_address}
                    onChange={handleChange}
                    rows={3}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="서울특별시 강남구 테헤란로 123"
                  />
                  {errors.shipping_address && (
                    <p className="mt-1 text-sm text-red-600">{errors.shipping_address}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="shipping_phone" className="block text-sm font-medium text-gray-700">
                    연락처 *
                  </label>
                  <input
                    type="tel"
                    id="shipping_phone"
                    name="shipping_phone"
                    value={formData.shipping_phone}
                    onChange={handleChange}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="010-1234-5678"
                  />
                  {errors.shipping_phone && (
                    <p className="mt-1 text-sm text-red-600">{errors.shipping_phone}</p>
                  )}
                </div>
              </div>
            </div>

            {/* 결제 정보 */}
            <div className="border rounded-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">결제 정보</h2>

              <div className="space-y-4">
                <div>
                  <label htmlFor="card_number" className="block text-sm font-medium text-gray-700">
                    카드 번호 *
                  </label>
                  <input
                    type="text"
                    id="card_number"
                    name="card_number"
                    value={formData.card_number}
                    onChange={handleChange}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="1234567890123456"
                    maxLength={16}
                  />
                  {errors.card_number && (
                    <p className="mt-1 text-sm text-red-600">{errors.card_number}</p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="card_expiry" className="block text-sm font-medium text-gray-700">
                      유효기간 *
                    </label>
                    <input
                      type="text"
                      id="card_expiry"
                      name="card_expiry"
                      value={formData.card_expiry}
                      onChange={handleChange}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="12/25"
                      maxLength={5}
                    />
                    {errors.card_expiry && (
                      <p className="mt-1 text-sm text-red-600">{errors.card_expiry}</p>
                    )}
                  </div>

                  <div>
                    <label htmlFor="card_cvv" className="block text-sm font-medium text-gray-700">
                      CVV *
                    </label>
                    <input
                      type="text"
                      id="card_cvv"
                      name="card_cvv"
                      value={formData.card_cvv}
                      onChange={handleChange}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="123"
                      maxLength={3}
                    />
                    {errors.card_cvv && (
                      <p className="mt-1 text-sm text-red-600">{errors.card_cvv}</p>
                    )}
                  </div>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
                  <p className="text-sm text-yellow-800">
                    💳 테스트 환경입니다. 실제 결제는 발생하지 않습니다.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* 오른쪽: 주문 요약 */}
          <div className="lg:col-span-1">
            <div className="border rounded-lg p-6 sticky top-4">
              <h2 className="text-xl font-bold text-gray-900 mb-4">주문 요약</h2>

              {/* 주문 상품 목록 */}
              <div className="space-y-3 mb-4 max-h-60 overflow-y-auto">
                {cart.items.map((item) => (
                  <div key={item.cart_item_id} className="flex gap-2">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{item.product_name}</p>
                      <p className="text-sm text-gray-600">
                        {item.quantity}개 × ₩{item.unit_price.toLocaleString()}
                      </p>
                    </div>
                    <div className="text-sm font-semibold text-gray-900">
                      ₩{item.subtotal.toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>

              <div className="border-t pt-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">상품 금액</span>
                  <span className="font-semibold">₩{cart.total_amount.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">배송비</span>
                  <span className="font-semibold">무료</span>
                </div>
                <div className="border-t pt-2 flex justify-between text-lg font-bold">
                  <span>총 결제 금액</span>
                  <span className="text-indigo-600">₩{cart.total_amount.toLocaleString()}</span>
                </div>
              </div>

              {errors.submit && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-800">{errors.submit}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={createOrderMutation.isPending}
                className="w-full mt-6 px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {createOrderMutation.isPending ? '처리 중...' : `₩${cart.total_amount.toLocaleString()} 결제하기`}
              </button>
            </div>
          </div>
        </div>
      </form>

      {/* OTP 모달 (T063) */}
      <OTPModal
        isOpen={showOtpModal}
        onClose={handleOtpModalClose}
        onVerify={handleOtpVerify}
        onResend={handleOtpResend}
        phoneNumber={formData.shipping_phone}
        remainingAttempts={otpAttempts}
      />
    </div>
  );
};
