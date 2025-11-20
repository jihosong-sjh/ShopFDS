/**
 * 비교 목록 플로팅 버튼
 * 화면 하단에 고정되어 비교 중인 상품 수를 표시하고 비교 페이지로 이동
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useComparison } from '../hooks/useComparison';

export const ComparisonFloatingButton: React.FC = () => {
  const navigate = useNavigate();
  const { products, productCount, clearAll } = useComparison();
  const [isExpanded, setIsExpanded] = useState(false);

  // 비교 목록이 비어있으면 표시하지 않음
  if (productCount === 0) {
    return null;
  }

  const handleCompare = () => {
    navigate('/comparison');
  };

  const handleClearAll = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('비교 목록을 모두 삭제하시겠습니까?')) {
      clearAll();
    }
  };

  return (
    <div
      className="fixed bottom-6 right-6 z-50"
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => setIsExpanded(false)}
    >
      {/* 확장된 상태: 상품 썸네일 미리보기 */}
      {isExpanded && (
        <div className="absolute bottom-full right-0 mb-2 bg-white rounded-lg shadow-2xl p-4 w-80 max-h-96 overflow-y-auto">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-900">
              비교 목록 ({productCount})
            </h3>
            <button
              type="button"
              onClick={handleClearAll}
              className="text-xs text-red-600 hover:text-red-700 font-medium"
              aria-label="비교 목록 전체 삭제"
            >
              전체 삭제
            </button>
          </div>

          <div className="space-y-2">
            {products.map((product) => (
              <div
                key={product.id}
                className="flex items-center gap-3 p-2 rounded hover:bg-gray-50 transition-colors"
              >
                <img
                  src={product.image}
                  alt={product.name}
                  className="w-12 h-12 object-cover rounded"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {product.name}
                  </p>
                  <p className="text-xs text-gray-600">
                    {product.price.toLocaleString()}원
                  </p>
                </div>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={handleCompare}
            className="w-full mt-3 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            비교하기
          </button>
        </div>
      )}

      {/* 플로팅 버튼 */}
      <button
        type="button"
        onClick={handleCompare}
        className="relative flex items-center gap-3 px-5 py-3 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 hover:shadow-xl transition-all duration-200 group"
        aria-label={`비교 목록 (${productCount}개)`}
      >
        {/* 비교 아이콘 */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-6 h-6"
        >
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
          <polyline points="15 3 21 3 21 9" />
          <line x1="10" y1="14" x2="21" y2="3" />
        </svg>

        {/* 상품 수 뱃지 */}
        <span className="absolute -top-1 -right-1 flex items-center justify-center w-6 h-6 bg-red-500 text-white text-xs font-bold rounded-full border-2 border-white">
          {productCount}
        </span>

        {/* 텍스트 (호버 시 표시) */}
        <span className="text-sm font-medium whitespace-nowrap hidden group-hover:inline">
          비교하기
        </span>
      </button>
    </div>
  );
};
