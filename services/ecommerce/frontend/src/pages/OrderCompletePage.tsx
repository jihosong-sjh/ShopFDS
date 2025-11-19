/**
 * 주문 완료 페이지
 *
 * 주문 번호, 예상 배송일, 주문 상세 정보를 표시합니다.
 */

import { useNavigate, useSearchParams } from 'react-router-dom';

export default function OrderCompletePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get('order_id');

  // 임시 데이터 (실제로는 API에서 가져와야 함)
  const orderData = {
    orderNumber: orderId || 'ORD-20251119-001',
    estimatedDelivery: '2025-11-22',
    items: [
      { name: '샘플 상품 1', quantity: 1, price: 50000 },
      { name: '샘플 상품 2', quantity: 2, price: 25000 },
    ],
    subtotal: 100000,
    discountAmount: 10000,
    shippingCost: 3000,
    totalAmount: 93000,
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        {/* 성공 아이콘 */}
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg
            className="w-12 h-12 text-green-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>

        <h1
          className="text-3xl font-bold text-gray-900 mb-2"
          data-testid="order-complete-message"
        >
          주문이 완료되었습니다!
        </h1>
        <p className="text-gray-600">주문해 주셔서 감사합니다.</p>
      </div>

      {/* 주문 번호 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
        <div className="text-sm text-gray-600 mb-1">주문 번호</div>
        <div className="text-2xl font-bold text-blue-600" data-testid="order-number">
          {orderData.orderNumber}
        </div>
      </div>

      {/* 예상 배송일 */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-600 mb-1">예상 배송일</div>
            <div className="text-lg font-semibold" data-testid="estimated-delivery">
              {orderData.estimatedDelivery}
            </div>
          </div>
          <div className="text-4xl">📦</div>
        </div>
      </div>

      {/* 쿠폰 할인 적용 표시 */}
      {orderData.discountAmount > 0 && (
        <div
          className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6"
          data-testid="discount-applied"
        >
          <div className="flex items-center gap-2">
            <svg
              className="w-5 h-5 text-green-600"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            <span className="text-green-700 font-medium">
              쿠폰 할인 {orderData.discountAmount.toLocaleString()}원 적용됨
            </span>
          </div>
        </div>
      )}

      {/* 주문 상세 */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">주문 상세</h2>

        {/* 주문 상품 목록 */}
        <div className="space-y-3 mb-4">
          {orderData.items.map((item, index) => (
            <div key={index} className="flex justify-between text-sm">
              <span className="text-gray-700">
                {item.name} × {item.quantity}
              </span>
              <span className="font-medium">{item.price.toLocaleString()}원</span>
            </div>
          ))}
        </div>

        <div className="border-t border-gray-200 pt-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">상품 금액</span>
            <span>{orderData.subtotal.toLocaleString()}원</span>
          </div>
          {orderData.discountAmount > 0 && (
            <div className="flex justify-between text-sm text-red-600">
              <span>쿠폰 할인</span>
              <span>-{orderData.discountAmount.toLocaleString()}원</span>
            </div>
          )}
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">배송비</span>
            <span>{orderData.shippingCost.toLocaleString()}원</span>
          </div>
          <div className="border-t border-gray-200 pt-2 flex justify-between font-bold text-lg">
            <span>총 결제 금액</span>
            <span className="text-blue-600">
              {orderData.totalAmount.toLocaleString()}원
            </span>
          </div>
        </div>
      </div>

      {/* 액션 버튼 */}
      <div className="flex gap-4">
        <button
          onClick={() => navigate('/orders')}
          className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium"
        >
          주문 내역 보기
        </button>
        <button
          onClick={() => navigate('/')}
          className="flex-1 px-6 py-3 border border-gray-300 rounded-md hover:bg-gray-50 font-medium"
        >
          쇼핑 계속하기
        </button>
      </div>
    </div>
  );
}
