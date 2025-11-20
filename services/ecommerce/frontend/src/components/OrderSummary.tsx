/**
 * 주문 요약 컴포넌트
 *
 * 상품 금액, 할인, 배송비, 총 금액을 표시합니다.
 */

interface OrderSummaryProps {
  subtotal: number;
  discountAmount?: number;
  shippingCost?: number;
  totalAmount: number;
}

export default function OrderSummary({
  subtotal,
  discountAmount = 0,
  shippingCost = 3000,
  totalAmount,
}: OrderSummaryProps) {
  return (
    <div className="bg-gray-50 rounded-lg p-6" data-testid="order-summary">
      <h3 className="text-lg font-semibold mb-4">주문 요약</h3>

      <div className="space-y-3">
        {/* 상품 금액 */}
        <div className="flex justify-between text-gray-700">
          <span>상품 금액</span>
          <span data-testid="subtotal">{subtotal.toLocaleString()}원</span>
        </div>

        {/* 할인 금액 */}
        {discountAmount > 0 && (
          <div className="flex justify-between text-red-600">
            <span>쿠폰 할인</span>
            <span data-testid="discount-amount">
              -{discountAmount.toLocaleString()}원
            </span>
          </div>
        )}

        {/* 배송비 */}
        <div className="flex justify-between text-gray-700">
          <span>배송비</span>
          <span data-testid="shipping-cost">
            {shippingCost === 0 ? '무료' : `${shippingCost.toLocaleString()}원`}
          </span>
        </div>

        <div className="border-t border-gray-300 my-3" />

        {/* 총 결제 금액 */}
        <div className="flex justify-between text-lg font-bold text-gray-900">
          <span>총 결제 금액</span>
          <span className="text-blue-600" data-testid="total-amount">
            {totalAmount.toLocaleString()}원
          </span>
        </div>
      </div>

      {/* 무료 배송 안내 */}
      {subtotal < 50000 && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-700">
          {(50000 - subtotal).toLocaleString()}원 더 구매하시면 무료 배송!
        </div>
      )}
    </div>
  );
}
