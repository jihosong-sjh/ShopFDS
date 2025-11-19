/**
 * SkeletonLoader Component
 * 로딩 중 스켈레톤 스크린 (Shimmer 효과)
 */

import React from "react";

interface SkeletonProps {
  className?: string;
  variant?: "text" | "circular" | "rectangular";
  width?: string | number;
  height?: string | number;
  animation?: "pulse" | "wave" | "none";
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = "",
  variant = "text",
  width,
  height,
  animation = "pulse",
}) => {
  const baseClasses = "bg-gray-300 dark:bg-gray-700";

  const animationClasses = {
    pulse: "animate-pulse",
    wave: "animate-shimmer",
    none: "",
  };

  const variantClasses = {
    text: "rounded h-4",
    circular: "rounded-full",
    rectangular: "rounded",
  };

  const styles: React.CSSProperties = {
    width: width || (variant === "text" ? "100%" : undefined),
    height: height || (variant === "circular" ? "40px" : undefined),
  };

  return (
    <div
      className={`${baseClasses} ${variantClasses[variant]} ${animationClasses[animation]} ${className}`}
      style={styles}
      aria-busy="true"
      aria-live="polite"
      role="status"
    />
  );
};

/**
 * ProductCardSkeleton
 * 상품 카드 스켈레톤 로더
 */
export const ProductCardSkeleton: React.FC = () => (
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4" aria-busy="true">
    <Skeleton variant="rectangular" height="160px" className="mb-3" />
    <Skeleton variant="text" width="80%" className="mb-2" />
    <Skeleton variant="text" width="60%" height="20px" className="mb-2" />
    <div className="flex justify-between items-center mt-3">
      <Skeleton variant="text" width="40%" />
      <Skeleton variant="text" width="30%" />
    </div>
  </div>
);

/**
 * ProductListSkeleton
 * 상품 목록 스켈레톤 로더 (그리드)
 */
export const ProductListSkeleton: React.FC<{ count?: number }> = ({
  count = 6,
}) => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    {Array.from({ length: count }).map((_, index) => (
      <ProductCardSkeleton key={index} />
    ))}
  </div>
);

/**
 * ReviewCardSkeleton
 * 리뷰 카드 스켈레톤 로더
 */
export const ReviewCardSkeleton: React.FC = () => (
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-4" aria-busy="true">
    <div className="flex items-center gap-3 mb-3">
      <Skeleton variant="circular" width="40px" height="40px" />
      <div className="flex-1">
        <Skeleton variant="text" width="120px" className="mb-1" />
        <Skeleton variant="text" width="80px" height="12px" />
      </div>
    </div>
    <Skeleton variant="text" width="100%" className="mb-2" />
    <Skeleton variant="text" width="90%" className="mb-2" />
    <Skeleton variant="text" width="70%" className="mb-3" />
    <Skeleton variant="rectangular" height="100px" />
  </div>
);

/**
 * CheckoutSkeleton
 * 체크아웃 페이지 스켈레톤 로더
 */
export const CheckoutSkeleton: React.FC = () => (
  <div className="max-w-4xl mx-auto p-6" aria-busy="true">
    <Skeleton variant="text" width="200px" height="32px" className="mb-6" />

    {/* 스텝 인디케이터 */}
    <div className="flex justify-between mb-8">
      {[1, 2, 3].map((step) => (
        <div key={step} className="flex items-center">
          <Skeleton variant="circular" width="40px" height="40px" />
          <Skeleton variant="text" width="60px" className="ml-2" />
        </div>
      ))}
    </div>

    {/* 폼 필드 */}
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-4">
      <Skeleton variant="text" width="150px" height="24px" className="mb-4" />
      <Skeleton variant="rectangular" height="40px" className="mb-3" />
      <Skeleton variant="rectangular" height="40px" className="mb-3" />
      <Skeleton variant="rectangular" height="80px" className="mb-3" />
    </div>

    {/* 주문 요약 */}
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <Skeleton variant="text" width="150px" height="24px" className="mb-4" />
      <div className="space-y-3">
        <div className="flex justify-between">
          <Skeleton variant="text" width="100px" />
          <Skeleton variant="text" width="80px" />
        </div>
        <div className="flex justify-between">
          <Skeleton variant="text" width="100px" />
          <Skeleton variant="text" width="80px" />
        </div>
        <Skeleton variant="rectangular" height="48px" className="mt-4" />
      </div>
    </div>
  </div>
);

/**
 * TableSkeleton
 * 테이블 스켈레톤 로더
 */
export const TableSkeleton: React.FC<{ rows?: number; columns?: number }> = ({
  rows = 5,
  columns = 4,
}) => (
  <div className="overflow-x-auto" aria-busy="true">
    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
      <thead className="bg-gray-50 dark:bg-gray-800">
        <tr>
          {Array.from({ length: columns }).map((_, index) => (
            <th key={index} className="px-6 py-3">
              <Skeleton variant="text" width="100px" />
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <tr key={rowIndex}>
            {Array.from({ length: columns }).map((_, colIndex) => (
              <td key={colIndex} className="px-6 py-4">
                <Skeleton variant="text" width="80px" />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

/**
 * Shimmer 애니메이션 CSS (Tailwind CSS에 추가 필요)
 * tailwind.config.js에 다음 추가:
 *
 * module.exports = {
 *   theme: {
 *     extend: {
 *       keyframes: {
 *         shimmer: {
 *           '0%': { transform: 'translateX(-100%)' },
 *           '100%': { transform: 'translateX(100%)' },
 *         },
 *       },
 *       animation: {
 *         shimmer: 'shimmer 2s infinite',
 *       },
 *     },
 *   },
 * }
 */
