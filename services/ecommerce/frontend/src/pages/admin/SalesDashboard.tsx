/**
 * 매출 대시보드 페이지
 *
 * T095: 매출 대시보드 페이지 구현
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { adminApi, adminQueryKeys } from '../../services/admin-api';

export const SalesDashboard: React.FC = () => {
  const today = new Date();
  const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

  const [startDate, setStartDate] = useState(thirtyDaysAgo.toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(today.toISOString().split('T')[0]);
  const [groupBy, setGroupBy] = useState<'day' | 'week' | 'month'>('day');

  // 매출 통계 조회
  const { data: salesStats, isLoading } = useQuery({
    queryKey: adminQueryKeys.sales.stats({
      start_date: startDate,
      end_date: endDate,
      group_by: groupBy,
    }),
    queryFn: () =>
      adminApi.getSalesStats({
        start_date: startDate,
        end_date: endDate,
        group_by: groupBy,
      }),
  });

  // 빠른 날짜 선택
  const handleQuickDateSelect = (days: number) => {
    const end = new Date();
    const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
    setStartDate(start.toISOString().split('T')[0]);
    setEndDate(end.toISOString().split('T')[0]);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-4">매출 대시보드</h1>

        {/* 날짜 및 그룹 필터 */}
        <div className="bg-white shadow-md rounded-lg p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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

            {/* 그룹화 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">그룹화</label>
              <select
                value={groupBy}
                onChange={(e) => setGroupBy(e.target.value as 'day' | 'week' | 'month')}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="day">일별</option>
                <option value="week">주별</option>
                <option value="month">월별</option>
              </select>
            </div>

            {/* 빠른 선택 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">빠른 선택</label>
              <div className="flex gap-2">
                <button
                  onClick={() => handleQuickDateSelect(7)}
                  className="px-3 py-2 bg-gray-200 text-gray-700 text-sm rounded-md hover:bg-gray-300"
                >
                  7일
                </button>
                <button
                  onClick={() => handleQuickDateSelect(30)}
                  className="px-3 py-2 bg-gray-200 text-gray-700 text-sm rounded-md hover:bg-gray-300"
                >
                  30일
                </button>
                <button
                  onClick={() => handleQuickDateSelect(90)}
                  className="px-3 py-2 bg-gray-200 text-gray-700 text-sm rounded-md hover:bg-gray-300"
                >
                  90일
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-8">로딩 중...</div>
      ) : (
        <>
          {/* 주요 지표 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-white shadow-md rounded-lg p-6">
              <div className="text-sm text-gray-500 mb-2">총 매출</div>
              <div className="text-3xl font-bold text-indigo-600">
                {salesStats?.total_sales.toLocaleString()}원
              </div>
            </div>
            <div className="bg-white shadow-md rounded-lg p-6">
              <div className="text-sm text-gray-500 mb-2">총 주문 수</div>
              <div className="text-3xl font-bold text-green-600">{salesStats?.total_orders.toLocaleString()}</div>
            </div>
            <div className="bg-white shadow-md rounded-lg p-6">
              <div className="text-sm text-gray-500 mb-2">평균 주문 금액</div>
              <div className="text-3xl font-bold text-blue-600">
                {salesStats?.average_order_value.toLocaleString()}원
              </div>
            </div>
          </div>

          {/* 기간별 매출 그래프 (간단한 막대 그래프) */}
          {salesStats && salesStats.sales_by_period.length > 0 && (
            <div className="bg-white shadow-md rounded-lg p-6 mb-6">
              <h2 className="text-xl font-bold mb-4">기간별 매출</h2>
              <div className="overflow-x-auto">
                <div className="flex items-end gap-2 h-64">
                  {salesStats.sales_by_period.map((item, index) => {
                    const maxSales = Math.max(...salesStats.sales_by_period.map((p) => p.sales));
                    const height = (item.sales / maxSales) * 100;
                    return (
                      <div key={index} className="flex-1 flex flex-col items-center">
                        <div className="relative w-full">
                          <div
                            className="bg-indigo-600 hover:bg-indigo-700 rounded-t transition-all"
                            style={{ height: `${height * 2}px` }}
                            title={`${item.sales.toLocaleString()}원`}
                          ></div>
                        </div>
                        <div className="mt-2 text-xs text-gray-600 text-center">
                          {item.period}
                        </div>
                        <div className="text-xs font-medium text-gray-900">
                          {(item.sales / 1000).toFixed(0)}K
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* 인기 상품 Top 10 */}
          {salesStats && salesStats.top_products.length > 0 && (
            <div className="bg-white shadow-md rounded-lg p-6 mb-6">
              <h2 className="text-xl font-bold mb-4">인기 상품 Top 10</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        순위
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        상품명
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        판매 수량
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        매출액
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {salesStats.top_products.slice(0, 10).map((product, index) => (
                      <tr key={product.product_id}>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center justify-center w-8 h-8 rounded-full ${
                              index < 3 ? 'bg-yellow-100 text-yellow-800 font-bold' : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {index + 1}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{product.product_name}</div>
                          <div className="text-xs text-gray-500">ID: {product.product_id.slice(0, 8)}...</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {product.total_sold.toLocaleString()}개
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-indigo-600">
                          {product.revenue.toLocaleString()}원
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 카테고리별 매출 */}
          {salesStats && salesStats.top_categories.length > 0 && (
            <div className="bg-white shadow-md rounded-lg p-6">
              <h2 className="text-xl font-bold mb-4">카테고리별 매출</h2>
              <div className="space-y-4">
                {salesStats.top_categories.map((category) => {
                  const totalRevenue = salesStats.top_categories.reduce((sum, c) => sum + c.revenue, 0);
                  const percentage = ((category.revenue / totalRevenue) * 100).toFixed(1);
                  return (
                    <div key={category.category}>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm font-medium text-gray-700">{category.category}</span>
                        <span className="text-sm text-gray-500">
                          {category.revenue.toLocaleString()}원 ({percentage}%)
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div
                          className="bg-indigo-600 h-2.5 rounded-full"
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        판매 수량: {category.total_sold.toLocaleString()}개
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
