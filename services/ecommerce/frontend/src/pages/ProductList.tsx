/**
 * 상품 목록 페이지
 *
 * T040: 상품 목록 페이지 및 검색 기능 구현
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { productsApi, queryKeys } from '../services/api';

export const ProductList: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [page, setPage] = useState(1);

  // 카테고리 목록 조회
  const { data: categories } = useQuery({
    queryKey: queryKeys.products.categories,
    queryFn: productsApi.getCategories,
  });

  // 상품 목록 조회
  const { data: productsData, isLoading } = useQuery({
    queryKey: queryKeys.products.list({
      category: selectedCategory,
      search: searchQuery,
      page,
    }),
    queryFn: () =>
      productsApi.getProducts({
        category: selectedCategory || undefined,
        search: searchQuery || undefined,
        page,
        page_size: 12,
      }),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    setPage(1);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 검색 및 필터 */}
      <div className="mb-8">
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

      {/* 상품 목록 */}
      {isLoading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {productsData?.products.map((product) => (
              <Link
                key={product.id}
                to={`/products/${product.id}`}
                className="group border rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
              >
                <div className="aspect-w-1 aspect-h-1 bg-gray-200">
                  {product.image_url ? (
                    <img
                      src={product.image_url}
                      alt={product.name}
                      className="w-full h-48 object-cover"
                    />
                  ) : (
                    <div className="w-full h-48 flex items-center justify-center bg-gray-200">
                      <span className="text-gray-400">이미지 없음</span>
                    </div>
                  )}
                </div>
                <div className="p-4">
                  <h3 className="text-lg font-semibold text-gray-900 group-hover:text-indigo-600">
                    {product.name}
                  </h3>
                  <p className="mt-1 text-sm text-gray-500 line-clamp-2">
                    {product.description}
                  </p>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-xl font-bold text-gray-900">
                      ₩{product.price.toLocaleString()}
                    </span>
                    {!product.is_available && (
                      <span className="text-sm text-red-600">품절</span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* 페이지네이션 */}
          {productsData && productsData.total_count > 12 && (
            <div className="mt-8 flex justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 border rounded-md disabled:opacity-50"
              >
                이전
              </button>
              <span className="px-4 py-2">
                {page} / {Math.ceil(productsData.total_count / 12)}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(productsData.total_count / 12)}
                className="px-4 py-2 border rounded-md disabled:opacity-50"
              >
                다음
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};
