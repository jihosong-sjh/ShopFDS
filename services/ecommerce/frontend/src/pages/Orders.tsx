/**
 * 주문 목록 페이지
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ordersApi, queryKeys } from '../services/api';

const ORDER_STATUS_MAP: Record<string, string> = {
  pending: '결제 대기',
  paid: '결제 완료',
  preparing: '배송 준비 중',
  shipped: '배송 중',
  delivered: '배송 완료',
  cancelled: '취소됨',
  refunded: '환불 완료',
};

const STATUS_COLOR_MAP: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  paid: 'bg-blue-100 text-blue-800',
  preparing: 'bg-purple-100 text-purple-800',
  shipped: 'bg-indigo-100 text-indigo-800',
  delivered: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
  refunded: 'bg-gray-100 text-gray-800',
};

export const Orders: React.FC = () => {
  // 주문 목록 조회
  const { data: orders, isLoading } = useQuery({
    queryKey: queryKeys.orders.list(),
    queryFn: () => ordersApi.getOrders(),
  });

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!orders || orders.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <p className="text-gray-600 mb-4">주문 내역이 없습니다.</p>
        <Link
          to="/products"
          className="inline-block px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          쇼핑하러 가기
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">주문 내역</h1>

      <div className="space-y-4">
        {orders.map((order) => (
          <Link
            key={order.id}
            to={`/orders/${order.id}`}
            className="block border rounded-lg p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-sm text-gray-600">주문번호</p>
                <p className="font-semibold text-gray-900">{order.order_number}</p>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  STATUS_COLOR_MAP[order.status] || 'bg-gray-100 text-gray-800'
                }`}
              >
                {ORDER_STATUS_MAP[order.status] || order.status}
              </span>
            </div>

            <div className="space-y-2 mb-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">주문 일시</span>
                <span className="text-gray-900">
                  {new Date(order.created_at).toLocaleString('ko-KR')}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">수령인</span>
                <span className="text-gray-900">{order.shipping_name}</span>
              </div>
            </div>

            <div className="border-t pt-4 flex justify-between items-center">
              <span className="text-gray-600">총 결제 금액</span>
              <span className="text-xl font-bold text-indigo-600">
                ₩{order.total_amount.toLocaleString()}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
};
