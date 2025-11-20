/**
 * 체크아웃 페이지
 *
 * 3단계 주문 프로세스:
 * 1. 배송 정보 입력
 * 2. 결제 수단 선택
 * 3. 주문 확인
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CouponInput from '../components/CouponInput';
import PaymentMethodSelector, { PaymentMethod } from '../components/PaymentMethodSelector';
import OrderSummary from '../components/OrderSummary';

type CheckoutStep = 1 | 2 | 3;

interface ShippingInfo {
  name: string;
  phone: string;
  zipcode: string;
  address: string;
}

export default function CheckoutPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<CheckoutStep>(1);

  // 배송 정보
  const [shippingInfo, setShippingInfo] = useState<ShippingInfo>({
    name: '',
    phone: '',
    zipcode: '',
    address: '',
  });

  // 결제 정보
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>();
  const [cardInfo, setCardInfo] = useState({
    cardNumber: '',
    cardExpiry: '',
    cardCvv: '',
  });

  // 쿠폰 정보
  const [appliedCoupon, setAppliedCoupon] = useState<{
    code: string;
    discountAmount: number;
  }>();

  // 임시 주문 데이터 (실제로는 장바구니에서 가져와야 함)
  const [orderData] = useState({
    subtotal: 100000,
    shippingCost: 3000,
  });

  const totalAmount =
    orderData.subtotal + orderData.shippingCost - (appliedCoupon?.discountAmount || 0);

  const [errorMessage, setErrorMessage] = useState('');

  const handleApplyCoupon = (code: string, discountAmount: number) => {
    setAppliedCoupon({ code, discountAmount });
  };

  const handleRemoveCoupon = () => {
    setAppliedCoupon(undefined);
  };

  const handleNextStep = () => {
    setErrorMessage('');

    if (currentStep === 1) {
      // 배송 정보 검증
      if (!shippingInfo.name || !shippingInfo.phone || !shippingInfo.address || !shippingInfo.zipcode) {
        setErrorMessage('배송 정보를 모두 입력해주세요');
        return;
      }
      setCurrentStep(2);
    } else if (currentStep === 2) {
      // 결제 수단 검증
      if (!paymentMethod) {
        setErrorMessage('결제 수단을 선택해주세요');
        return;
      }
      if (paymentMethod === 'card') {
        if (!cardInfo.cardNumber || !cardInfo.cardExpiry || !cardInfo.cardCvv) {
          setErrorMessage('카드 정보를 모두 입력해주세요');
          return;
        }
      }
      setCurrentStep(3);
    }
  };

  const handlePrevStep = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => (prev - 1) as CheckoutStep);
    }
  };

  const handleCompleteOrder = async () => {
    // TODO: API 호출하여 주문 생성
    // 주문 완료 페이지로 이동
    navigate('/orders/complete?order_id=ORD-20251119-001');
  };

  const handleEditShipping = () => {
    setCurrentStep(1);
  };

  const handleEditPayment = () => {
    setCurrentStep(2);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* 스텝 인디케이터 */}
      <div className="mb-8" data-testid="checkout-steps">
        <div className="flex items-center justify-center">
          {[1, 2, 3].map((step) => (
            <React.Fragment key={step}>
              <div className="flex items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                    currentStep >= step
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-500'
                  }`}
                  data-testid={`step-${step}`}
                  data-active={currentStep === step}
                >
                  {step}
                </div>
                <div className="ml-2 text-sm font-medium">
                  {step === 1 && '배송 정보'}
                  {step === 2 && '결제 수단'}
                  {step === 3 && '주문 확인'}
                </div>
              </div>
              {step < 3 && (
                <div
                  className={`w-24 h-1 mx-4 ${
                    currentStep > step ? 'bg-blue-600' : 'bg-gray-200'
                  }`}
                />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* 왼쪽: 메인 콘텐츠 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 에러 메시지 */}
          {errorMessage && (
            <div
              className="p-4 bg-red-50 border border-red-200 rounded-md text-red-700"
              data-testid="error-message"
            >
              {errorMessage}
            </div>
          )}

          {/* Step 1: 배송 정보 */}
          {currentStep === 1 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">배송 정보</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    받는 사람
                  </label>
                  <input
                    type="text"
                    value={shippingInfo.name}
                    onChange={(e) =>
                      setShippingInfo({ ...shippingInfo, name: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    data-testid="shipping-name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    연락처
                  </label>
                  <input
                    type="tel"
                    value={shippingInfo.phone}
                    onChange={(e) =>
                      setShippingInfo({ ...shippingInfo, phone: e.target.value })
                    }
                    placeholder="010-1234-5678"
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    data-testid="shipping-phone"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    우편번호
                  </label>
                  <input
                    type="text"
                    value={shippingInfo.zipcode}
                    onChange={(e) =>
                      setShippingInfo({ ...shippingInfo, zipcode: e.target.value })
                    }
                    placeholder="06000"
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    data-testid="shipping-zipcode"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    주소
                  </label>
                  <input
                    type="text"
                    value={shippingInfo.address}
                    onChange={(e) =>
                      setShippingInfo({ ...shippingInfo, address: e.target.value })
                    }
                    placeholder="서울특별시 강남구"
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    data-testid="shipping-address"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: 결제 수단 */}
          {currentStep === 2 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">결제 수단</h2>
              <PaymentMethodSelector
                selectedMethod={paymentMethod}
                onSelect={setPaymentMethod}
                cardInfo={cardInfo}
                onCardInfoChange={setCardInfo}
              />
            </div>
          )}

          {/* Step 3: 주문 확인 */}
          {currentStep === 3 && (
            <div className="space-y-6">
              {/* 배송 정보 확인 */}
              <div className="bg-white rounded-lg shadow p-6" data-testid="confirm-shipping-info">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold">배송 정보</h3>
                  <button
                    onClick={handleEditShipping}
                    className="text-sm text-blue-600 hover:underline"
                    data-testid="edit-shipping-button"
                  >
                    수정
                  </button>
                </div>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-gray-600">받는 사람:</span> {shippingInfo.name}
                  </div>
                  <div>
                    <span className="text-gray-600">연락처:</span> {shippingInfo.phone}
                  </div>
                  <div>
                    <span className="text-gray-600">주소:</span> [{shippingInfo.zipcode}]{' '}
                    {shippingInfo.address}
                  </div>
                </div>
              </div>

              {/* 결제 수단 확인 */}
              <div className="bg-white rounded-lg shadow p-6" data-testid="confirm-payment-method">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold">결제 수단</h3>
                  <button
                    onClick={handleEditPayment}
                    className="text-sm text-blue-600 hover:underline"
                  >
                    수정
                  </button>
                </div>
                <div className="text-sm">
                  {paymentMethod === 'card' && '신용카드'}
                  {paymentMethod === 'toss' && '토스페이'}
                  {paymentMethod === 'kakao' && '카카오페이'}
                  {paymentMethod === 'card' && cardInfo.cardNumber && (
                    <span className="text-gray-600 ml-2">
                      ({cardInfo.cardNumber.slice(0, 4)} **** **** ****)
                    </span>
                  )}
                </div>
              </div>

              {/* 주문 상품 확인 */}
              <div className="bg-white rounded-lg shadow p-6" data-testid="confirm-order-items">
                <h3 className="text-lg font-semibold mb-4">주문 상품</h3>
                <div className="text-sm text-gray-600">
                  장바구니 상품 (임시 데이터)
                </div>
              </div>

              {/* 총 결제 금액 */}
              <div className="bg-white rounded-lg shadow p-6" data-testid="confirm-total-amount">
                <OrderSummary
                  subtotal={orderData.subtotal}
                  discountAmount={appliedCoupon?.discountAmount}
                  shippingCost={orderData.shippingCost}
                  totalAmount={totalAmount}
                />
              </div>
            </div>
          )}

          {/* 네비게이션 버튼 */}
          <div className="flex justify-between">
            {currentStep > 1 && (
              <button
                onClick={handlePrevStep}
                className="px-6 py-3 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                이전
              </button>
            )}
            {currentStep < 3 ? (
              <button
                onClick={handleNextStep}
                className="ml-auto px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                data-testid="next-button"
              >
                다음
              </button>
            ) : (
              <button
                onClick={handleCompleteOrder}
                className="ml-auto px-8 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 font-semibold"
                data-testid="complete-order-button"
              >
                주문 완료
              </button>
            )}
          </div>
        </div>

        {/* 오른쪽: 주문 요약 & 쿠폰 */}
        <div className="space-y-6">
          {/* 주문 요약 */}
          <OrderSummary
            subtotal={orderData.subtotal}
            discountAmount={appliedCoupon?.discountAmount}
            shippingCost={orderData.shippingCost}
            totalAmount={totalAmount}
          />

          {/* 쿠폰 입력 */}
          {currentStep < 3 && (
            <div className="bg-white rounded-lg shadow p-6">
              <CouponInput
                orderAmount={orderData.subtotal}
                onApply={handleApplyCoupon}
                onRemove={handleRemoveCoupon}
                appliedCoupon={appliedCoupon}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
