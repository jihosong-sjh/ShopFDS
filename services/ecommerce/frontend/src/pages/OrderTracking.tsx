/**
 * 주문 추적 페이지
 *
 * T044: 주문 추적 페이지 구현
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { ordersApi, queryKeys } from '../services/api';

export const OrderTracking: React.FC = () => {
  const { orderId } = useParams<{ orderId: string }>();

  // 주문 상세 조회
  const { data: order, isLoading } = useQuery({
    queryKey: queryKeys.orders.detail(orderId!),
    queryFn: () => ordersApi.getOrder(orderId!),
    enabled: !!orderId,
  });

  // 주문 추적 정보 조회
  const { data: trackingInfo } = useQuery({
    queryKey: ['order-tracking', orderId],
    queryFn: () => ordersApi.trackOrder(orderId!),
    enabled: !!orderId,
  });

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <p className="text-gray-600 mb-4">주문을 찾을 수 없습니다.</p>
        <Link
          to="/orders"
          className="inline-block px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          주문 목록으로
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 주문 번호 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">주문 추적</h1>
        <p className="mt-2 text-gray-600">
          주문번호: <span className="font-semibold">{order.order_number}</span>
        </p>
      </div>

      {/* 주문 상태 타임라인 */}
      {trackingInfo && (
        <div className="mb-8 border rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6">배송 현황</h2>

          <div className="space-y-4">
            {trackingInfo.status_history.map((status: any, index: number) => (
              <div key={index} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div className="w-3 h-3 bg-indigo-600 rounded-full"></div>
                  {index < trackingInfo.status_history.length - 1 && (
                    <div className="w-0.5 h-full bg-gray-300 my-1"></div>
                  )}
                </div>
                <div className="flex-1 pb-4">
                  <p className="font-semibold text-gray-900">{status.description}</p>
                  <p className="text-sm text-gray-600">
                    {new Date(status.timestamp).toLocaleString('ko-KR')}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 배송 정보 */}
      <div className="mb-8 border rounded-lg p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">배송 정보</h2>

        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="text-gray-600">수령인</span>
            <span className="font-semibold">{order.shipping_name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">연락처</span>
            <span className="font-semibold">{order.shipping_phone}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">주소</span>
            <span className="font-semibold text-right">{order.shipping_address}</span>
          </div>
        </div>
      </div>

      {/* 주문 상품 */}
      <div className="border rounded-lg p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">주문 상품</h2>

        <div className="space-y-4">
          {order.items?.map((item, index) => (
            <div key={index} className="flex justify-between items-start">
              <div className="flex-1">
                <Link
                  to={`/products/${item.product_id}`}
                  className="text-gray-900 hover:text-indigo-600 font-medium"
                >
                  {item.product_name}
                </Link>
                <p className="text-sm text-gray-600 mt-1">
                  {item.quantity}개 × ₩{item.unit_price.toLocaleString()}
                </p>
              </div>
              <div className="text-right">
                <p className="font-semibold text-gray-900">₩{item.subtotal.toLocaleString()}</p>
              </div>
            </div>
          ))}

          <div className="border-t pt-4">
            <div className="flex justify-between text-lg font-bold">
              <span>총 결제 금액</span>
              <span className="text-indigo-600">₩{order.total_amount.toLocaleString()}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 액션 버튼 */}
      <div className="mt-8 flex gap-4">
        <Link
          to="/orders"
          className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 text-center rounded-md hover:bg-gray-50"
        >
          주문 목록으로
        </Link>
        {order.status === 'paid' || order.status === 'preparing' ? (
          <button
            onClick={() => {
              if (confirm('주문을 취소하시겠습니까?')) {
                ordersApi.cancelOrder(order.id).then(() => {
                  window.location.reload();
                });
              }
            }}
            className="flex-1 px-6 py-3 border border-red-600 text-red-600 rounded-md hover:bg-red-50"
          >
            주문 취소
          </button>
        ) : null}
      </div>
    </div>
  );
};
