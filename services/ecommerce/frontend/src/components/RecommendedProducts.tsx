/**
 * RecommendedProducts Component
 *
 * 추천 상품 섹션 (홈 페이지용)
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import axios from 'axios';
import WishlistButton from './WishlistButton';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface Product {
  id: string;
  name: string;
  price: number;
  discounted_price?: number;
  image_url?: string;
  rating: number;
  review_count: number;
}

interface RecommendationsResponse {
  products: Product[];
  algorithm: string;
}

const fetchRecommendations = async (limit = 10): Promise<RecommendationsResponse> => {
  const token = localStorage.getItem('access_token');
  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const response = await axios.get(`${API_BASE_URL}/v1/recommendations/for-you`, {
    params: { limit },
    headers,
  });
  return response.data;
};

interface RecommendedProductsProps {
  limit?: number;
  title?: string;
}

const RecommendedProducts: React.FC<RecommendedProductsProps> = ({
  limit = 10,
  title = '추천 상품',
}) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['recommendations', limit],
    queryFn: () => fetchRecommendations(limit),
    staleTime: 60000, // 1분
  });

  if (isLoading) {
    return (
      <div className="py-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">{title}</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6">
          {[...Array(limit)].map((_, index) => (
            <div key={index} className="animate-pulse">
              <div className="bg-gray-200 rounded-lg h-48 mb-3"></div>
              <div className="bg-gray-200 rounded h-4 mb-2"></div>
              <div className="bg-gray-200 rounded h-4 w-2/3"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error || !data || data.products.length === 0) {
    return null; // 오류 또는 빈 데이터면 섹션을 숨김
  }

  return (
    <div className="py-8">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">{title}</h2>
        <span className="text-sm text-gray-500">
          {data.algorithm === 'collaborative_filtering' ? '맞춤 추천' : '인기 상품'}
        </span>
      </div>

      {/* 상품 그리드 */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6">
        {data.products.map((product) => (
          <div
            key={product.id}
            className="group relative border rounded-lg hover:shadow-lg transition-shadow"
          >
            {/* 위시리스트 버튼 */}
            <div className="absolute top-2 right-2 z-10">
              <WishlistButton productId={product.id} size="sm" />
            </div>

            {/* 상품 이미지 */}
            <Link to={`/products/${product.id}`}>
              <div className="aspect-square overflow-hidden rounded-t-lg bg-gray-200">
                <img
                  src={product.image_url || '/placeholder-product.png'}
                  alt={product.name}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
              </div>
            </Link>

            {/* 상품 정보 */}
            <div className="p-4">
              <Link to={`/products/${product.id}`}>
                <h3 className="font-medium text-gray-900 line-clamp-2 hover:text-blue-600 transition-colors">
                  {product.name}
                </h3>
              </Link>

              {/* 가격 */}
              <div className="mt-2">
                {product.discounted_price ? (
                  <>
                    <div className="text-lg font-bold text-red-600">
                      {product.discounted_price.toLocaleString()}원
                    </div>
                    <div className="text-sm text-gray-500 line-through">
                      {product.price.toLocaleString()}원
                    </div>
                  </>
                ) : (
                  <div className="text-lg font-bold text-gray-900">
                    {product.price.toLocaleString()}원
                  </div>
                )}
              </div>

              {/* 평점 */}
              {product.review_count > 0 && (
                <div className="mt-2 flex items-center gap-1 text-sm text-gray-600">
                  <svg className="w-4 h-4 text-yellow-400 fill-current" viewBox="0 0 20 20">
                    <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z" />
                  </svg>
                  <span>{product.rating.toFixed(1)}</span>
                  <span className="text-gray-400">({product.review_count})</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RecommendedProducts;
