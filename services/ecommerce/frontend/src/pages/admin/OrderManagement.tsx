/**
 * 주문 관리 페이지
 *
 * T093: 주문 관리 페이지 구현
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { adminApi, adminQueryKeys } from '../../services/admin-api';

export const OrderManagement: React.FC = () => {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [page, setPage] = useState(1);

  // 주문 목록 조회
  const { data: ordersData, isLoading } = useQuery({
    queryKey: adminQueryKeys.orders.list({
      status: statusFilter,
      start_date: startDate,
      end_date: endDate,
      page,
    }),
    queryFn: () =>
      adminApi.getAllOrders({
        status: statusFilter || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        page,
        page_size: 20,
      }),
  });

  // 주문 상태 업데이트 뮤테이션
  const updateOrderStatusMutation = useMutation({
    mutationFn: ({ orderId, status, notes }: { orderId: string; status: string; notes?: string }) =>
      adminApi.updateOrderStatus(orderId, { status, admin_notes: notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.orders.all });
      alert('주문 상태가 성공적으로 업데이트되었습니다.');
    },
    onError: (error: any) => {
      alert(`주문 상태 업데이트 실패: ${error.response?.data?.detail || error.message}`);
    },
  });

  // 상태 변경 핸들러
  const handleStatusChange = (orderId: string, newStatus: string) => {
    const notes = prompt('관리자 메모를 입력하세요 (선택사항):');
    if (window.confirm(`주문 상태를 "${newStatus}"로 변경하시겠습니까?`)) {
      updateOrderStatusMutation.mutate({
        orderId,
        status: newStatus,
        notes: notes || undefined,
      });
    }
  };

  // 필터 초기화
  const handleResetFilters = () => {
    setStatusFilter('');
    setStartDate('');
    setEndDate('');
    setPage(1);
  };

  // 주문 상태 목록
  const orderStatuses = [
    { value: 'pending', label: '결제 대기' },
    { value: 'payment_completed', label: '결제 완료' },
    { value: 'processing', label: '처리 중' },
    { value: 'shipped', label: '배송 중' },
    { value: 'delivered', label: '배송 완료' },
    { value: 'cancelled', label: '취소됨' },
    { value: 'refunded', label: '환불됨' },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-4">주문 관리</h1>

        {/* 필터 */}
        <div className="bg-white shadow-md rounded-lg p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* 상태 필터 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">주문 상태</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">전체</option>
                {orderStatuses.map((status) => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 시작일 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">시작일</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* 종료일 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">종료일</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* 필터 초기화 */}
            <div className="flex items-end">
              <button
                onClick={handleResetFilters}
                className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
              >
                필터 초기화
              </button>
            </div>
          </div>
        </div>

        {/* 통계 요약 */}
        {ordersData && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white shadow-md rounded-lg p-4">
              <div className="text-sm text-gray-500">전체 주문</div>
              <div className="text-2xl font-bold">{ordersData.total_count}</div>
            </div>
            <div className="bg-white shadow-md rounded-lg p-4">
              <div className="text-sm text-gray-500">결제 완료</div>
              <div className="text-2xl font-bold text-blue-600">
                {ordersData.orders.filter((o) => o.status === 'payment_completed').length}
              </div>
            </div>
            <div className="bg-white shadow-md rounded-lg p-4">
              <div className="text-sm text-gray-500">배송 중</div>
              <div className="text-2xl font-bold text-green-600">
                {ordersData.orders.filter((o) => o.status === 'shipped').length}
              </div>
            </div>
            <div className="bg-white shadow-md rounded-lg p-4">
              <div className="text-sm text-gray-500">취소/환불</div>
              <div className="text-2xl font-bold text-red-600">
                {ordersData.orders.filter((o) => o.status === 'cancelled' || o.status === 'refunded').length}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 주문 목록 */}
      {isLoading ? (
        <div className="text-center py-8">로딩 중...</div>
      ) : ordersData?.orders.length === 0 ? (
        <div className="text-center py-8 text-gray-500">주문이 없습니다.</div>
      ) : (
        <div className="bg-white shadow-md rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  주문 번호
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  고객 정보
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  주문 금액
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  상태
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  주문일시
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  작업
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {ordersData?.orders.map((order) => (
                <OrderRow
                  key={order.id}
                  order={order}
                  onStatusChange={handleStatusChange}
                  isUpdating={updateOrderStatusMutation.isPending}
                  orderStatuses={orderStatuses}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 페이지네이션 */}
      {ordersData && ordersData.total_count > 0 && (
        <div className="mt-6 flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50"
          >
            이전
          </button>
          <span className="px-4 py-2">
            {page} / {Math.ceil(ordersData.total_count / ordersData.page_size)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(ordersData.total_count / ordersData.page_size)}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50"
          >
            다음
          </button>
        </div>
      )}
    </div>
  );
};

// 주문 행 컴포넌트
interface OrderRowProps {
  order: any;
  onStatusChange: (orderId: string, newStatus: string) => void;
  isUpdating: boolean;
  orderStatuses: Array<{ value: string; label: string }>;
}

const OrderRow: React.FC<OrderRowProps> = ({ order, onStatusChange, isUpdating, orderStatuses }) => {
  // 상태별 색상
  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      payment_completed: 'bg-blue-100 text-blue-800',
      processing: 'bg-indigo-100 text-indigo-800',
      shipped: 'bg-green-100 text-green-800',
      delivered: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
      refunded: 'bg-red-100 text-red-800',
    };
    return colorMap[status] || 'bg-gray-100 text-gray-800';
  };

  const statusLabel = orderStatuses.find((s) => s.value === order.status)?.label || order.status;

  return (
    <tr>
      <td className="px-6 py-4 whitespace-nowrap">
        <Link to={`/admin/orders/${order.id}`} className="text-indigo-600 hover:text-indigo-900">
          <div className="text-sm font-medium">{order.order_number}</div>
          <div className="text-xs text-gray-500">ID: {order.id.slice(0, 8)}...</div>
        </Link>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm font-medium text-gray-900">{order.shipping_name}</div>
        <div className="text-xs text-gray-500">{order.shipping_phone}</div>
        <div className="text-xs text-gray-500">{order.shipping_address}</div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm font-medium text-gray-900">
          {order.total_amount.toLocaleString()}원
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(order.status)}`}>
          {statusLabel}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {new Date(order.created_at).toLocaleString('ko-KR')}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm">
        <select
          onChange={(e) => onStatusChange(order.id, e.target.value)}
          disabled={isUpdating}
          className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
          defaultValue=""
        >
          <option value="" disabled>
            상태 변경
          </option>
          {orderStatuses
            .filter((s) => s.value !== order.status)
            .map((status) => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
        </select>
      </td>
    </tr>
  );
};
