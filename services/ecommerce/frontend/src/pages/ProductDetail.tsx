/**
 * 상품 상세 페이지
 *
 * T041: 상품 상세 페이지 구현
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { productsApi, cartApi, queryKeys } from '../services/api';
import { useCartStore } from '../stores/cartStore';

export const ProductDetail: React.FC = () => {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const incrementCartCount = useCartStore((state) => state.incrementCartCount);

  const [quantity, setQuantity] = useState(1);
  const [showSuccess, setShowSuccess] = useState(false);

  // 상품 상세 조회
  const { data: product, isLoading } = useQuery({
    queryKey: queryKeys.products.detail(productId!),
    queryFn: () => productsApi.getProduct(productId!),
    enabled: !!productId,
  });

  // 장바구니 추가
  const addToCartMutation = useMutation({
    mutationFn: cartApi.addToCart,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.cart.current });
      incrementCartCount();
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 3000);
    },
  });

  const handleAddToCart = () => {
    if (product) {
      addToCartMutation.mutate({
        product_id: product.id,
        quantity,
      });
    }
  };

  const handleBuyNow = () => {
    handleAddToCart();
    setTimeout(() => navigate('/cart'), 500);
  };

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <p className="text-gray-600">상품을 찾을 수 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 성공 알림 */}
      {showSuccess && (
        <div className="fixed top-4 right-4 bg-green-50 border border-green-200 rounded-md p-4 shadow-lg z-50">
          <p className="text-green-800">장바구니에 추가되었습니다!</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* 상품 이미지 */}
        <div className="aspect-w-1 aspect-h-1">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="w-full h-full object-cover rounded-lg"
            />
          ) : (
            <div className="w-full h-96 flex items-center justify-center bg-gray-200 rounded-lg">
              <span className="text-gray-400">이미지 없음</span>
            </div>
          )}
        </div>

        {/* 상품 정보 */}
        <div>
          <div className="mb-4">
            <span className="inline-block px-3 py-1 text-sm bg-indigo-100 text-indigo-800 rounded-full">
              {product.category}
            </span>
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-4">{product.name}</h1>

          <p className="text-2xl font-bold text-gray-900 mb-6">
            ₩{product.price.toLocaleString()}
          </p>

          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">상품 설명</h3>
            <p className="text-gray-600">{product.description || '상품 설명이 없습니다.'}</p>
          </div>

          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">재고</h3>
            <p className={product.is_available ? 'text-green-600' : 'text-red-600'}>
              {product.is_available
                ? `${product.stock_quantity}개 재고 있음`
                : '품절'}
            </p>
          </div>

          {/* 수량 선택 */}
          {product.is_available && (
            <div className="mb-6">
              <label htmlFor="quantity" className="block text-sm font-medium text-gray-700 mb-2">
                수량
              </label>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                  className="px-3 py-1 border rounded-md hover:bg-gray-100"
                >
                  -
                </button>
                <input
                  type="number"
                  id="quantity"
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                  min="1"
                  max={product.stock_quantity}
                  className="w-20 text-center px-3 py-1 border rounded-md"
                />
                <button
                  onClick={() => setQuantity((q) => Math.min(product.stock_quantity, q + 1))}
                  className="px-3 py-1 border rounded-md hover:bg-gray-100"
                >
                  +
                </button>
              </div>
            </div>
          )}

          {/* 버튼 */}
          <div className="flex gap-4">
            <button
              onClick={handleAddToCart}
              disabled={!product.is_available || addToCartMutation.isPending}
              className="flex-1 px-6 py-3 border border-indigo-600 text-indigo-600 rounded-md hover:bg-indigo-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {addToCartMutation.isPending ? '추가 중...' : '장바구니'}
            </button>
            <button
              onClick={handleBuyNow}
              disabled={!product.is_available || addToCartMutation.isPending}
              className="flex-1 px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              바로 구매
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
