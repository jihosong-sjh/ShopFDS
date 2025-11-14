/**
 * 재고 관리 페이지
 *
 * T092: 재고 관리 페이지 구현
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productsApi, queryKeys as publicQueryKeys } from '../../services/api';
import { adminApi, adminQueryKeys } from '../../services/admin-api';

export const StockManagement: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [page, setPage] = useState(1);

  // 상품 목록 조회
  const { data: productsData, isLoading } = useQuery({
    queryKey: publicQueryKeys.products.list({
      category: selectedCategory,
      search: searchQuery,
      page,
    }),
    queryFn: () =>
      productsApi.getProducts({
        category: selectedCategory || undefined,
        search: searchQuery || undefined,
        page,
        page_size: 20,
      }),
  });

  // 카테고리 목록 조회
  const { data: categories } = useQuery({
    queryKey: publicQueryKeys.products.categories,
    queryFn: productsApi.getCategories,
  });

  // 재고 업데이트 뮤테이션
  const updateStockMutation = useMutation({
    mutationFn: ({ productId, data }: { productId: string; data: any }) =>
      adminApi.updateStock(productId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: publicQueryKeys.products.all });
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.products.all });
      alert('재고가 성공적으로 업데이트되었습니다.');
    },
    onError: (error: any) => {
      alert(`재고 업데이트 실패: ${error.response?.data?.detail || error.message}`);
    },
  });

  // 재고 조정 핸들러
  const handleStockAdjustment = (productId: string, operation: 'increment' | 'decrement', amount: number) => {
    if (amount <= 0) {
      alert('수량은 0보다 커야 합니다.');
      return;
    }

    const confirmMessage =
      operation === 'increment'
        ? `재고를 ${amount}개 증가시키시겠습니까?`
        : `재고를 ${amount}개 감소시키시겠습니까?`;

    if (window.confirm(confirmMessage)) {
      updateStockMutation.mutate({
        productId,
        data: {
          stock_quantity: amount,
          operation,
        },
      });
    }
  };

  // 재고 직접 설정 핸들러
  const handleSetStock = (productId: string, newStock: number) => {
    if (newStock < 0) {
      alert('재고는 0 이상이어야 합니다.');
      return;
    }

    if (window.confirm(`재고를 ${newStock}개로 설정하시겠습니까?`)) {
      updateStockMutation.mutate({
        productId,
        data: {
          stock_quantity: newStock,
          operation: 'set',
        },
      });
    }
  };

  // 검색 핸들러
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  // 카테고리 변경 핸들러
  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    setPage(1);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-4">재고 관리</h1>

        {/* 검색 및 필터 */}
        <div className="bg-white shadow-md rounded-lg p-4 mb-6">
          <form onSubmit={handleSearch} className="mb-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="상품 검색..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                type="submit"
                className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                검색
              </button>
            </div>
          </form>

          {/* 카테고리 필터 */}
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => handleCategoryChange('')}
              className={`px-4 py-2 rounded-md ${
                selectedCategory === ''
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              전체
            </button>
            {categories?.map((category) => (
              <button
                key={category}
                onClick={() => handleCategoryChange(category)}
                className={`px-4 py-2 rounded-md ${
                  selectedCategory === category
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {category}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 재고 목록 */}
      {isLoading ? (
        <div className="text-center py-8">로딩 중...</div>
      ) : productsData?.products.length === 0 ? (
        <div className="text-center py-8 text-gray-500">상품이 없습니다.</div>
      ) : (
        <div className="bg-white shadow-md rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  상품명
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  카테고리
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  현재 재고
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  상태
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  재고 조정
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {productsData?.products.map((product) => (
                <StockRow
                  key={product.id}
                  product={product}
                  onAdjustment={handleStockAdjustment}
                  onSetStock={handleSetStock}
                  isUpdating={updateStockMutation.isPending}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 페이지네이션 */}
      {productsData && productsData.total_count > 0 && (
        <div className="mt-6 flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50"
          >
            이전
          </button>
          <span className="px-4 py-2">
            {page} / {Math.ceil(productsData.total_count / productsData.page_size)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(productsData.total_count / productsData.page_size)}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50"
          >
            다음
          </button>
        </div>
      )}
    </div>
  );
};

// 재고 행 컴포넌트
interface StockRowProps {
  product: any;
  onAdjustment: (productId: string, operation: 'increment' | 'decrement', amount: number) => void;
  onSetStock: (productId: string, newStock: number) => void;
  isUpdating: boolean;
}

const StockRow: React.FC<StockRowProps> = ({ product, onAdjustment, onSetStock, isUpdating }) => {
  const [adjustAmount, setAdjustAmount] = useState(1);
  const [newStock, setNewStock] = useState(product.stock_quantity);

  // 재고 부족 경고
  const isLowStock = product.stock_quantity < 10;
  const isOutOfStock = product.stock_quantity === 0;

  return (
    <tr className={isOutOfStock ? 'bg-red-50' : isLowStock ? 'bg-yellow-50' : ''}>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm font-medium text-gray-900">{product.name}</div>
        <div className="text-sm text-gray-500">ID: {product.id.slice(0, 8)}...</div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded">
          {product.category}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm font-medium text-gray-900">{product.stock_quantity}개</div>
        {isOutOfStock && <div className="text-xs text-red-600 font-medium">품절</div>}
        {isLowStock && !isOutOfStock && <div className="text-xs text-yellow-600 font-medium">재고 부족</div>}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span
          className={`px-2 py-1 text-xs font-medium rounded ${
            product.is_available ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
          }`}
        >
          {product.is_available ? '판매중' : '판매중지'}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex flex-col gap-2">
          {/* 빠른 조정 버튼 */}
          <div className="flex gap-1">
            <input
              type="number"
              value={adjustAmount}
              onChange={(e) => setAdjustAmount(Number(e.target.value))}
              min="1"
              className="w-16 px-2 py-1 border border-gray-300 rounded text-sm"
            />
            <button
              onClick={() => onAdjustment(product.id, 'increment', adjustAmount)}
              disabled={isUpdating}
              className="px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50"
            >
              +
            </button>
            <button
              onClick={() => onAdjustment(product.id, 'decrement', adjustAmount)}
              disabled={isUpdating}
              className="px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700 disabled:opacity-50"
            >
              -
            </button>
          </div>
          {/* 직접 설정 */}
          <div className="flex gap-1">
            <input
              type="number"
              value={newStock}
              onChange={(e) => setNewStock(Number(e.target.value))}
              min="0"
              className="w-16 px-2 py-1 border border-gray-300 rounded text-sm"
            />
            <button
              onClick={() => onSetStock(product.id, newStock)}
              disabled={isUpdating}
              className="px-2 py-1 bg-indigo-600 text-white text-xs rounded hover:bg-indigo-700 disabled:opacity-50"
            >
              설정
            </button>
          </div>
        </div>
      </td>
    </tr>
  );
};
