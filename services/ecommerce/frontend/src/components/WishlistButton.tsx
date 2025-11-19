/**
 * WishlistButton Component
 *
 * 위시리스트 추가/삭제 토글 버튼 (하트 아이콘)
 */

import React, { useState, useEffect } from 'react';
import { useWishlist } from '../hooks/useWishlist';

interface WishlistButtonProps {
  productId: string;
  initialInWishlist?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const WishlistButton: React.FC<WishlistButtonProps> = ({
  productId,
  initialInWishlist = false,
  size = 'md',
  className = '',
}) => {
  const [inWishlist, setInWishlist] = useState(initialInWishlist);
  const { addToWishlist, removeFromWishlist, isAddingToWishlist, isRemovingFromWishlist } =
    useWishlist();

  useEffect(() => {
    setInWishlist(initialInWishlist);
  }, [initialInWishlist]);

  const handleToggle = (e: React.MouseEvent) => {
    e.preventDefault(); // 부모 요소 클릭 이벤트 방지

    if (inWishlist) {
      // 위시리스트에서 삭제
      removeFromWishlist(productId, {
        onSuccess: () => {
          setInWishlist(false);
        },
      });
    } else {
      // 위시리스트에 추가
      addToWishlist(productId, {
        onSuccess: () => {
          setInWishlist(true);
        },
      });
    }
  };

  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-10 h-10',
  };

  const iconSizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  const isLoading = isAddingToWishlist || isRemovingFromWishlist;

  return (
    <button
      onClick={handleToggle}
      disabled={isLoading}
      className={`
        ${sizeClasses[size]}
        flex items-center justify-center
        rounded-full
        ${inWishlist ? 'bg-red-50 hover:bg-red-100' : 'bg-gray-100 hover:bg-gray-200'}
        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500
        transition-all duration-200
        ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${className}
      `}
      data-testid="wishlist-button"
      aria-label={inWishlist ? '위시리스트에서 제거' : '위시리스트에 추가'}
      aria-pressed={inWishlist}
    >
      {isLoading ? (
        // 로딩 스피너
        <svg
          className={`${iconSizeClasses[size]} animate-spin text-gray-400`}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : inWishlist ? (
        // 채워진 하트 (위시리스트에 있음)
        <svg
          className={`${iconSizeClasses[size]} text-red-500 filled active`}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.36 2.25 12.174 2.25 8.25 2.25 5.322 4.714 3 7.688 3A5.5 5.5 0 0112 5.052 5.5 5.5 0 0116.313 3c2.973 0 5.437 2.322 5.437 5.25 0 3.925-2.438 7.111-4.739 9.256a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.219l-.022.012-.007.004-.003.001a.752.752 0 01-.704 0l-.003-.001z" />
        </svg>
      ) : (
        // 빈 하트 (위시리스트에 없음)
        <svg
          className={`${iconSizeClasses[size]} text-gray-400`}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
          />
        </svg>
      )}
    </button>
  );
};

export default WishlistButton;
