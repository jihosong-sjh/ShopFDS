/**
 * 상품 비교 버튼 컴포넌트
 * 상품 카드에 추가하여 비교 목록에 추가/제거
 */

import React, { useState, useEffect } from 'react';
import { useComparison } from '../hooks/useComparison';
import { ComparisonProduct } from '../stores/comparisonStore';

interface CompareButtonProps {
  product: ComparisonProduct;
  variant?: 'icon' | 'text' | 'full';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onToggle?: (isInComparison: boolean) => void;
}

export const CompareButton: React.FC<CompareButtonProps> = ({
  product,
  variant = 'icon',
  size = 'md',
  className = '',
  onToggle,
}) => {
  const { toggleProduct, isInComparison } = useComparison();
  const [isActive, setIsActive] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => {
    setIsActive(isInComparison(product.id));
  }, [product.id, isInComparison]);

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const result = toggleProduct(product);

    if (result.success) {
      const newState = isInComparison(product.id);
      setIsActive(newState);
      onToggle?.(newState);

      // 토스트 알림 (전역 토스트 시스템이 있다면 사용)
      // toast.success(result.message);
      console.log(result.message);
    } else {
      // toast.error(result.message);
      console.error(result.message);
      alert(result.message);
    }
  };

  const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-12 h-12 text-base',
  };

  const buttonSizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-2 text-sm',
    lg: 'px-4 py-2 text-base',
  };

  if (variant === 'icon') {
    return (
      <div className="relative inline-block">
        <button
          type="button"
          onClick={handleClick}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          className={`
            ${sizeClasses[size]}
            flex items-center justify-center
            rounded-lg border-2 transition-all duration-200
            ${
              isActive
                ? 'bg-blue-600 border-blue-600 text-white'
                : 'bg-white border-gray-300 text-gray-700 hover:border-blue-600 hover:text-blue-600'
            }
            ${className}
          `}
          aria-label={isActive ? '비교 목록에서 제거' : '비교 목록에 추가'}
          aria-pressed={isActive}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="w-5 h-5"
          >
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
        </button>

        {showTooltip && (
          <div className="absolute z-10 px-2 py-1 text-xs text-white bg-gray-900 rounded shadow-lg -top-8 left-1/2 transform -translate-x-1/2 whitespace-nowrap">
            {isActive ? '비교 목록에서 제거' : '비교 목록에 추가'}
          </div>
        )}
      </div>
    );
  }

  if (variant === 'text') {
    return (
      <button
        type="button"
        onClick={handleClick}
        className={`
          ${buttonSizeClasses[size]}
          flex items-center gap-2
          font-medium transition-colors duration-200
          ${
            isActive
              ? 'text-blue-600'
              : 'text-gray-700 hover:text-blue-600'
          }
          ${className}
        `}
        aria-pressed={isActive}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-4 h-4"
        >
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
          <polyline points="15 3 21 3 21 9" />
          <line x1="10" y1="14" x2="21" y2="3" />
        </svg>
        {isActive ? '비교 취소' : '비교하기'}
      </button>
    );
  }

  // variant === 'full'
  return (
    <button
      type="button"
      onClick={handleClick}
      className={`
        ${buttonSizeClasses[size]}
        flex items-center justify-center gap-2
        font-medium rounded-lg border-2 transition-all duration-200
        ${
          isActive
            ? 'bg-blue-600 border-blue-600 text-white hover:bg-blue-700'
            : 'bg-white border-gray-300 text-gray-700 hover:border-blue-600 hover:text-blue-600'
        }
        ${className}
      `}
      aria-pressed={isActive}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-4 h-4"
      >
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
        <polyline points="15 3 21 3 21 9" />
        <line x1="10" y1="14" x2="21" y2="3" />
      </svg>
      {isActive ? '비교 목록에서 제거' : '비교 목록에 추가'}
    </button>
  );
};
