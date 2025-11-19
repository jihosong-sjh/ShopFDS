import React from 'react';
import { Link } from 'react-router-dom';
import LazyImage from './LazyImage';

export interface Product {
  id: string;
  name: string;
  description?: string;
  price: number;
  image_url?: string;
  images?: string[];
  category?: string;
  is_available: boolean;
  stock_quantity?: number;
  rating?: number;
  review_count?: number;
}

interface ProductCardProps {
  product: Product;
}

/**
 * ProductCard 컴포넌트
 *
 * T057: 상품 목록 카드에 평균 평점 및 리뷰 수 표시
 *
 * 상품을 카드 형태로 표시합니다.
 * 이미지, 이름, 가격, 평균 평점, 리뷰 수, 재고 상태를 포함합니다.
 *
 * @param product - 상품 데이터
 */
const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const imageUrl = product.images?.[0] || product.image_url;
  const hasReviews = product.review_count && product.review_count > 0;

  const renderStars = (rating: number) => {
    return (
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <svg
            key={star}
            className={`w-4 h-4 ${
              star <= Math.round(rating)
                ? 'text-yellow-400 fill-current'
                : 'text-gray-300'
            }`}
            viewBox="0 0 24 24"
          >
            <path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
          </svg>
        ))}
      </div>
    );
  };

  return (
    <Link
      to={`/products/${product.id}`}
      className="group border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-all duration-200 bg-white"
    >
      {/* 상품 이미지 */}
      <div className="aspect-w-1 aspect-h-1 bg-gray-100 relative overflow-hidden">
        {imageUrl ? (
          <LazyImage
            src={imageUrl}
            alt={product.name}
            className="w-full h-48 object-cover group-hover:scale-105 transition-transform duration-200"
          />
        ) : (
          <div className="w-full h-48 flex items-center justify-center bg-gray-200">
            <span className="text-gray-400">이미지 없음</span>
          </div>
        )}

        {/* 품절 오버레이 */}
        {!product.is_available && (
          <div className="absolute inset-0 bg-black bg-opacity-40 flex items-center justify-center">
            <span className="bg-white text-gray-900 px-4 py-2 rounded-lg font-semibold">
              품절
            </span>
          </div>
        )}

        {/* 카테고리 뱃지 */}
        {product.category && (
          <div className="absolute top-2 left-2">
            <span className="inline-block px-2 py-1 text-xs bg-white bg-opacity-90 text-gray-700 rounded">
              {product.category}
            </span>
          </div>
        )}
      </div>

      {/* 상품 정보 */}
      <div className="p-4">
        <h3 className="text-lg font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors line-clamp-2 mb-2">
          {product.name}
        </h3>

        {/* 평균 평점 및 리뷰 수 */}
        {hasReviews && product.rating !== undefined && (
          <div className="flex items-center gap-2 mb-2">
            {renderStars(product.rating)}
            <span className="text-sm font-medium text-gray-900">
              {product.rating.toFixed(1)}
            </span>
            <span className="text-sm text-gray-500">
              ({product.review_count?.toLocaleString()})
            </span>
          </div>
        )}

        {/* 상품 설명 */}
        {product.description && (
          <p className="text-sm text-gray-600 line-clamp-2 mb-3">
            {product.description}
          </p>
        )}

        {/* 가격 및 재고 */}
        <div className="flex items-center justify-between">
          <span className="text-xl font-bold text-gray-900">
            ₩{product.price.toLocaleString()}
          </span>

          {product.is_available && product.stock_quantity !== undefined && product.stock_quantity <= 5 && (
            <span className="text-xs text-orange-600 font-medium">
              {product.stock_quantity}개 남음
            </span>
          )}
        </div>
      </div>
    </Link>
  );
};

export default ProductCard;
