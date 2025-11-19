/**
 * 상품 상세 페이지
 *
 * T041: 상품 상세 페이지 구현
 * T056: 이미지 갤러리 및 리뷰 섹션 업데이트
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { productsApi, cartApi, queryKeys } from '../services/api';
import { useCartStore } from '../stores/cartStore';
import ImageGallery from '../components/ImageGallery';
import ImageZoomModal from '../components/ImageZoomModal';
import ReviewList from '../components/ReviewList';
import ReviewForm, { ReviewFormData } from '../components/ReviewForm';
import { useReviews } from '../hooks/useReviews';
import { Review } from '../components/ReviewCard';
import { ReviewFilters, SortOption } from '../components/ReviewList';

export const ProductDetailPage: React.FC = () => {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const incrementCartCount = useCartStore((state) => state.incrementCartCount);

  const [quantity, setQuantity] = useState(1);
  const [showSuccess, setShowSuccess] = useState(false);
  const [activeTab, setActiveTab] = useState<'description' | 'reviews'>('description');
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [editingReview, setEditingReview] = useState<Review | null>(null);

  // 이미지 확대 모달 상태
  const [zoomModalOpen, setZoomModalOpen] = useState(false);
  const [zoomImageIndex, setZoomImageIndex] = useState(0);

  // 리뷰 필터 및 정렬 상태
  const [reviewPage, setReviewPage] = useState(1);
  const [reviewFilters, setReviewFilters] = useState<ReviewFilters>({});
  const [reviewSort, setReviewSort] = useState<SortOption>('recent');

  // 상품 상세 조회
  const { data: product, isLoading } = useQuery({
    queryKey: queryKeys.products.detail(productId!),
    queryFn: () => productsApi.getProduct(productId!),
    enabled: !!productId,
  });

  // 리뷰 데이터 조회
  const {
    reviews,
    totalCount,
    averageRating,
    ratingDistribution,
    currentPage,
    totalPages,
    isLoading: reviewsLoading,
    createReview,
    updateReview,
    deleteReview,
    voteHelpful,
  } = useReviews({
    productId: productId!,
    page: reviewPage,
    limit: 10,
    filters: reviewFilters,
    sort: reviewSort,
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

  const handleImageClick = (index: number) => {
    setZoomImageIndex(index);
    setZoomModalOpen(true);
  };

  const handleReviewSubmit = async (data: ReviewFormData) => {
    if (editingReview) {
      await updateReview({ reviewId: editingReview.id, data });
      setEditingReview(null);
    } else {
      await createReview(data);
    }
    setShowReviewForm(false);
  };

  const handleEditReview = (review: Review) => {
    setEditingReview(review);
    setShowReviewForm(true);
    setActiveTab('reviews');
  };

  const handleDeleteReview = async (reviewId: string) => {
    if (confirm('정말 이 리뷰를 삭제하시겠습니까?')) {
      await deleteReview(reviewId);
    }
  };

  const handleHelpfulClick = async (reviewId: string, isHelpful: boolean) => {
    await voteHelpful({ reviewId, isHelpful });
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

  // 상품 이미지 배열 (image_url을 images 배열로 변환)
  const productImages = product.images || (product.image_url ? [product.image_url] : []);

  // 현재 로그인 사용자 ID 가져오기 (실제 구현에서는 인증 context에서 가져와야 함)
  const currentUserId = localStorage.getItem('user_id') || undefined;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 성공 알림 */}
      {showSuccess && (
        <div className="fixed top-4 right-4 bg-green-50 border border-green-200 rounded-md p-4 shadow-lg z-50">
          <p className="text-green-800">장바구니에 추가되었습니다!</p>
        </div>
      )}

      {/* 이미지 확대 모달 */}
      <ImageZoomModal
        images={productImages}
        initialIndex={zoomImageIndex}
        alt={product.name}
        isOpen={zoomModalOpen}
        onClose={() => setZoomModalOpen(false)}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
        {/* 상품 이미지 갤러리 */}
        <div>
          {productImages.length > 0 ? (
            <ImageGallery
              images={productImages}
              alt={product.name}
              onImageClick={handleImageClick}
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

          {/* 평균 평점 및 리뷰 수 */}
          {totalCount > 0 && (
            <div className="flex items-center gap-3 mb-4">
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <svg
                    key={star}
                    className={`w-5 h-5 ${
                      star <= Math.round(averageRating)
                        ? 'text-yellow-400 fill-current'
                        : 'text-gray-300'
                    }`}
                    viewBox="0 0 24 24"
                  >
                    <path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                  </svg>
                ))}
              </div>
              <span className="text-lg font-semibold text-gray-900">
                {averageRating.toFixed(1)}
              </span>
              <button
                onClick={() => setActiveTab('reviews')}
                className="text-sm text-indigo-600 hover:underline"
              >
                ({totalCount.toLocaleString()}개 리뷰)
              </button>
            </div>
          )}

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

      {/* 탭: 상품 설명 / 리뷰 */}
      <div className="border-t border-gray-200">
        <div className="flex gap-8 border-b border-gray-200">
          <button
            onClick={() => setActiveTab('description')}
            className={`py-4 px-2 border-b-2 font-medium transition-colors ${
              activeTab === 'description'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            상품 상세
          </button>
          <button
            onClick={() => setActiveTab('reviews')}
            className={`py-4 px-2 border-b-2 font-medium transition-colors ${
              activeTab === 'reviews'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            리뷰 ({totalCount.toLocaleString()})
          </button>
        </div>

        <div className="py-8">
          {activeTab === 'description' && (
            <div className="prose max-w-none">
              <p className="text-gray-700">{product.description || '상품 설명이 없습니다.'}</p>
            </div>
          )}

          {activeTab === 'reviews' && (
            <div>
              {/* 리뷰 작성 버튼 */}
              {!showReviewForm && (
                <div className="mb-6">
                  <button
                    onClick={() => setShowReviewForm(true)}
                    className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                  >
                    리뷰 작성하기
                  </button>
                </div>
              )}

              {/* 리뷰 작성 폼 */}
              {showReviewForm && (
                <div className="mb-8 p-6 bg-gray-50 rounded-lg">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    {editingReview ? '리뷰 수정' : '리뷰 작성'}
                  </h3>
                  <ReviewForm
                    productId={productId!}
                    onSubmit={handleReviewSubmit}
                    onCancel={() => {
                      setShowReviewForm(false);
                      setEditingReview(null);
                    }}
                    initialData={editingReview ? {
                      rating: editingReview.rating,
                      title: editingReview.title,
                      content: editingReview.content,
                      images: editingReview.images,
                    } : undefined}
                  />
                </div>
              )}

              {/* 리뷰 목록 */}
              <ReviewList
                reviews={reviews}
                totalCount={totalCount}
                averageRating={averageRating}
                ratingDistribution={ratingDistribution}
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setReviewPage}
                onFilterChange={setReviewFilters}
                onSortChange={setReviewSort}
                onHelpfulClick={handleHelpfulClick}
                onImageClick={(images, index) => {
                  setZoomImageIndex(index);
                  setZoomModalOpen(true);
                }}
                currentUserId={currentUserId}
                onEditReview={handleEditReview}
                onDeleteReview={handleDeleteReview}
                isLoading={reviewsLoading}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProductDetailPage;
