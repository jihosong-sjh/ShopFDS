/**
 * WishlistPage Component
 *
 * 위시리스트 페이지 - 찜한 상품 목록 및 관리
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useWishlist } from '../hooks/useWishlist';

const WishlistPage: React.FC = () => {
  const {
    wishlistItems,
    totalCount,
    isLoading,
    error,
    removeFromWishlist,
    moveToCart,
    isRemovingFromWishlist,
    isMovingToCart,
  } = useWishlist();

  const [selectedItems, setSelectedItems] = useState<string[]>([]);

  // 체크박스 토글
  const handleToggleSelect = (itemId: string) => {
    setSelectedItems((prev) =>
      prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]
    );
  };

  // 전체 선택/해제
  const handleToggleSelectAll = () => {
    if (selectedItems.length === wishlistItems.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(wishlistItems.map((item) => item.id));
    }
  };

  // 선택 항목 장바구니로 이동
  const handleMoveSelectedToCart = () => {
    if (selectedItems.length === 0) {
      alert('이동할 상품을 선택해주세요.');
      return;
    }

    if (confirm(`선택한 ${selectedItems.length}개 상품을 장바구니로 이동하시겠습니까?`)) {
      moveToCart(selectedItems, {
        onSuccess: () => {
          setSelectedItems([]);
          alert('장바구니로 이동되었습니다.');
        },
      });
    }
  };

  // 개별 삭제
  const handleRemoveItem = (itemId: string) => {
    if (confirm('위시리스트에서 삭제하시겠습니까?')) {
      removeFromWishlist(itemId);
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center items-center min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center text-red-600">
          <p>위시리스트를 불러오는 중 오류가 발생했습니다.</p>
          <p className="text-sm text-gray-500 mt-2">{(error as Error).message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">위시리스트</h1>
        <p className="text-gray-600 mt-2">찜한 상품 {totalCount}개</p>
      </div>

      {/* 빈 상태 */}
      {wishlistItems.length === 0 ? (
        <div
          className="text-center py-16"
          data-testid="wishlist-empty"
        >
          <svg
            className="mx-auto h-24 w-24 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
            />
          </svg>
          <h2 className="mt-6 text-xl font-semibold text-gray-900">위시리스트가 비어있습니다</h2>
          <p className="mt-2 text-gray-600">마음에 드는 상품을 찜해보세요!</p>
          <Link
            to="/"
            className="mt-6 inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            data-testid="continue-shopping"
          >
            쇼핑 계속하기
          </Link>
        </div>
      ) : (
        <>
          {/* 일괄 선택 및 액션 */}
          <div className="flex items-center justify-between mb-4 pb-4 border-b">
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedItems.length === wishlistItems.length}
                  onChange={handleToggleSelectAll}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">전체 선택</span>
              </label>
              <span className="text-sm text-gray-500">
                ({selectedItems.length}/{wishlistItems.length})
              </span>
            </div>

            <button
              onClick={handleMoveSelectedToCart}
              disabled={selectedItems.length === 0 || isMovingToCart}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              data-testid="move-selected-to-cart"
            >
              {isMovingToCart ? '이동 중...' : '선택 상품 장바구니 담기'}
            </button>
          </div>

          {/* 위시리스트 항목 */}
          <div className="space-y-4">
            {wishlistItems.map((item) => (
              <div
                key={item.id}
                className="flex items-center gap-4 p-4 border rounded-lg hover:shadow-md transition-shadow"
                data-testid="wishlist-item"
              >
                {/* 체크박스 */}
                <input
                  type="checkbox"
                  checked={selectedItems.includes(item.id)}
                  onChange={() => handleToggleSelect(item.id)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                  data-testid="item-checkbox"
                />

                {/* 상품 이미지 */}
                <Link to={`/products/${item.product.id}`} className="flex-shrink-0">
                  <img
                    src={item.product.image_url || '/placeholder-product.png'}
                    alt={item.product.name}
                    className="w-24 h-24 object-cover rounded-lg"
                    data-testid="product-image"
                  />
                </Link>

                {/* 상품 정보 */}
                <div className="flex-1">
                  <Link
                    to={`/products/${item.product.id}`}
                    className="text-lg font-semibold text-gray-900 hover:text-blue-600"
                    data-testid="product-name"
                  >
                    {item.product.name}
                  </Link>

                  <div className="mt-1 flex items-center gap-2">
                    {item.product.discounted_price ? (
                      <>
                        <span className="text-xl font-bold text-red-600" data-testid="product-price">
                          {item.product.discounted_price.toLocaleString()}원
                        </span>
                        <span className="text-sm text-gray-500 line-through">
                          {item.product.price.toLocaleString()}원
                        </span>
                      </>
                    ) : (
                      <span className="text-xl font-bold text-gray-900" data-testid="product-price">
                        {item.product.price.toLocaleString()}원
                      </span>
                    )}
                  </div>

                  <div className="mt-2 flex items-center gap-2">
                    <span
                      className={`text-sm ${item.product.in_stock ? 'text-green-600' : 'text-red-600'}`}
                      data-testid="in-stock-status"
                    >
                      {item.product.in_stock ? '재고 있음' : '품절'}
                    </span>
                    <span className="text-gray-400">|</span>
                    <span className="text-sm text-gray-600">
                      평점 {item.product.rating.toFixed(1)} ({item.product.review_count}개 리뷰)
                    </span>
                  </div>
                </div>

                {/* 액션 버튼 */}
                <div className="flex flex-col gap-2">
                  <button
                    onClick={() => moveToCart([item.id])}
                    disabled={!item.product.in_stock || isMovingToCart}
                    className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
                    data-testid="add-to-cart-button"
                  >
                    장바구니 담기
                  </button>
                  <button
                    onClick={() => handleRemoveItem(item.id)}
                    disabled={isRemovingFromWishlist}
                    className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    data-testid="remove-button"
                  >
                    삭제
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default WishlistPage;
