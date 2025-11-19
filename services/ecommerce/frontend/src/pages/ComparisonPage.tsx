/**
 * 상품 비교 페이지
 * 최대 4개 상품을 나란히 비교하는 테이블 UI
 */

import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useComparison } from '../hooks/useComparison';
import { ComparisonProduct } from '../stores/comparisonStore';

export const ComparisonPage: React.FC = () => {
  const navigate = useNavigate();
  const { products, productCount, removeProduct, clearAll } = useComparison();

  // 비교 속성 추출
  const comparisonRows = useMemo(() => {
    if (productCount === 0) return [];

    // 모든 상품의 specifications를 합쳐서 비교 항목 생성
    const allSpecs = new Set<string>();
    products.forEach((product) => {
      if (product.specifications) {
        Object.keys(product.specifications).forEach((key) => allSpecs.add(key));
      }
    });

    return [
      {
        label: '상품 이미지',
        type: 'image' as const,
        getValue: (p: ComparisonProduct) => p.image,
      },
      {
        label: '상품명',
        type: 'text' as const,
        getValue: (p: ComparisonProduct) => p.name,
      },
      {
        label: '가격',
        type: 'price' as const,
        getValue: (p: ComparisonProduct) => p.price,
      },
      {
        label: '브랜드',
        type: 'text' as const,
        getValue: (p: ComparisonProduct) => p.brand || '-',
      },
      {
        label: '카테고리',
        type: 'text' as const,
        getValue: (p: ComparisonProduct) => p.category,
      },
      {
        label: '평점',
        type: 'rating' as const,
        getValue: (p: ComparisonProduct) =>
          p.rating ? `${p.rating} / 5.0` : '-',
      },
      {
        label: '리뷰 수',
        type: 'text' as const,
        getValue: (p: ComparisonProduct) =>
          p.reviewCount ? `${p.reviewCount}개` : '-',
      },
      {
        label: '재고',
        type: 'stock' as const,
        getValue: (p: ComparisonProduct) =>
          p.stock !== undefined ? p.stock : null,
      },
      {
        label: '설명',
        type: 'description' as const,
        getValue: (p: ComparisonProduct) => p.description || '-',
      },
      // 사양 (specifications)
      ...Array.from(allSpecs).map((specKey) => ({
        label: specKey,
        type: 'text' as const,
        getValue: (p: ComparisonProduct) =>
          p.specifications?.[specKey]?.toString() || '-',
      })),
    ];
  }, [products, productCount]);

  if (productCount === 0) {
    return (
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-md mx-auto text-center">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="w-24 h-24 mx-auto text-gray-400 mb-4"
          >
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            비교할 상품이 없습니다
          </h2>
          <p className="text-gray-600 mb-6">
            상품 페이지에서 '비교하기' 버튼을 눌러 상품을 추가해보세요.
          </p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            홈으로 이동
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">상품 비교</h1>
          <p className="text-gray-600">
            {productCount}개 상품을 비교하고 있습니다
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            뒤로 가기
          </button>
          <button
            type="button"
            onClick={() => {
              if (window.confirm('비교 목록을 모두 삭제하시겠습니까?')) {
                clearAll();
              }
            }}
            className="px-4 py-2 text-red-600 border border-red-600 rounded-lg hover:bg-red-50 transition-colors"
          >
            전체 삭제
          </button>
        </div>
      </div>

      {/* 비교 테이블 */}
      <div className="overflow-x-auto bg-white rounded-lg shadow">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="sticky left-0 z-10 bg-gray-50 px-6 py-4 text-left font-semibold text-gray-900 min-w-[200px]">
                비교 항목
              </th>
              {products.map((product) => (
                <th
                  key={product.id}
                  className="px-6 py-4 text-center font-semibold text-gray-900 min-w-[250px]"
                >
                  <button
                    type="button"
                    onClick={() => removeProduct(product.id)}
                    className="ml-auto text-red-600 hover:text-red-700 text-sm font-normal"
                    aria-label={`${product.name} 제거`}
                  >
                    X 제거
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {comparisonRows.map((row, index) => (
              <tr
                key={index}
                className="border-b border-gray-200 hover:bg-gray-50 transition-colors"
              >
                <td className="sticky left-0 z-10 bg-white px-6 py-4 font-medium text-gray-900 border-r border-gray-200">
                  {row.label}
                </td>
                {products.map((product) => {
                  const value = row.getValue(product);

                  return (
                    <td key={product.id} className="px-6 py-4 text-center">
                      {row.type === 'image' && typeof value === 'string' && (
                        <img
                          src={value}
                          alt={product.name}
                          className="w-32 h-32 object-cover rounded mx-auto"
                        />
                      )}

                      {row.type === 'price' && typeof value === 'number' && (
                        <span className="text-lg font-bold text-blue-600">
                          {value.toLocaleString()}원
                        </span>
                      )}

                      {row.type === 'rating' && (
                        <div className="flex items-center justify-center gap-1">
                          <span className="text-yellow-500">★</span>
                          <span className="font-medium">{value}</span>
                        </div>
                      )}

                      {row.type === 'stock' && value !== null && (
                        <span
                          className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                            (value as number) > 0
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {(value as number) > 0 ? '재고 있음' : '품절'}
                        </span>
                      )}

                      {row.type === 'description' && (
                        <p className="text-sm text-gray-700 text-left max-w-xs">
                          {value as string}
                        </p>
                      )}

                      {row.type === 'text' && (
                        <span className="text-gray-700">{value as string}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 액션 버튼 */}
      <div className="mt-6 flex justify-center gap-4">
        {products.map((product) => (
          <button
            key={product.id}
            type="button"
            onClick={() => navigate(`/products/${product.id}`)}
            className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            {product.name} 상세보기
          </button>
        ))}
      </div>
    </div>
  );
};
