import React, { useState } from 'react';
import ReviewCard, { Review } from './ReviewCard';

interface ReviewListProps {
  reviews: Review[];
  totalCount: number;
  averageRating: number;
  ratingDistribution: Record<string, number>;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onFilterChange: (filters: ReviewFilters) => void;
  onSortChange: (sort: SortOption) => void;
  onHelpfulClick: (reviewId: string, isHelpful: boolean) => Promise<void>;
  onImageClick?: (images: string[], index: number) => void;
  currentUserId?: string;
  onEditReview?: (review: Review) => void;
  onDeleteReview?: (reviewId: string) => void;
  isLoading?: boolean;
}

export interface ReviewFilters {
  rating?: number;
  has_photos?: boolean;
}

export type SortOption = 'recent' | 'rating_desc' | 'rating_asc' | 'helpful';

/**
 * ReviewList 컴포넌트
 *
 * 리뷰 목록을 표시하고, 정렬 및 필터링 기능을 제공합니다.
 * 평균 평점, 별점 분포, 페이지네이션을 포함합니다.
 *
 * @param reviews - 리뷰 배열
 * @param totalCount - 전체 리뷰 수
 * @param averageRating - 평균 평점
 * @param ratingDistribution - 별점별 리뷰 수
 * @param currentPage - 현재 페이지
 * @param totalPages - 전체 페이지 수
 * @param onPageChange - 페이지 변경 콜백
 * @param onFilterChange - 필터 변경 콜백
 * @param onSortChange - 정렬 변경 콜백
 * @param onHelpfulClick - 도움돼요 클릭 콜백
 * @param onImageClick - 이미지 클릭 콜백
 * @param currentUserId - 현재 사용자 ID
 * @param onEditReview - 리뷰 수정 콜백
 * @param onDeleteReview - 리뷰 삭제 콜백
 * @param isLoading - 로딩 상태
 */
const ReviewList: React.FC<ReviewListProps> = ({
  reviews,
  totalCount,
  averageRating,
  ratingDistribution,
  currentPage,
  totalPages,
  onPageChange,
  onFilterChange,
  onSortChange,
  onHelpfulClick,
  onImageClick,
  currentUserId,
  onEditReview,
  onDeleteReview,
  isLoading = false,
}) => {
  const [selectedRating, setSelectedRating] = useState<number | undefined>(
    undefined
  );
  const [hasPhotos, setHasPhotos] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<SortOption>('recent');

  const handleRatingFilter = (rating: number | undefined) => {
    setSelectedRating(rating);
    onFilterChange({ rating, has_photos: hasPhotos });
  };

  const handlePhotosFilter = () => {
    const newHasPhotos = !hasPhotos;
    setHasPhotos(newHasPhotos);
    onFilterChange({ rating: selectedRating, has_photos: newHasPhotos });
  };

  const handleSortChange = (sort: SortOption) => {
    setSortBy(sort);
    onSortChange(sort);
  };

  const renderRatingDistribution = () => {
    const maxCount = Math.max(...Object.values(ratingDistribution));

    return (
      <div className="space-y-2">
        {[5, 4, 3, 2, 1].map((rating) => {
          const count = ratingDistribution[rating.toString()] || 0;
          const percentage = totalCount > 0 ? (count / totalCount) * 100 : 0;

          return (
            <button
              key={rating}
              onClick={() =>
                handleRatingFilter(
                  selectedRating === rating ? undefined : rating
                )
              }
              className={`w-full flex items-center gap-3 p-2 rounded-lg transition-colors ${
                selectedRating === rating
                  ? 'bg-blue-50 border border-blue-500'
                  : 'hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-1">
                <span className="text-sm font-medium w-3">{rating}</span>
                <svg
                  className="w-4 h-4 text-yellow-400 fill-current"
                  viewBox="0 0 24 24"
                >
                  <path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                </svg>
              </div>
              <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-yellow-400 transition-all duration-300"
                  style={{ width: `${percentage}%` }}
                />
              </div>
              <span className="text-sm text-gray-600 w-12 text-right">
                {count.toLocaleString()}
              </span>
            </button>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* 리뷰 요약 */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex flex-col md:flex-row gap-6">
          {/* 평균 평점 */}
          <div className="flex flex-col items-center justify-center p-6 bg-gray-50 rounded-lg">
            <div className="text-4xl font-bold text-gray-900 mb-2">
              {averageRating.toFixed(1)}
            </div>
            <div className="flex gap-1 mb-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <svg
                  key={star}
                  className={`w-6 h-6 ${
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
            <div className="text-sm text-gray-600">
              {totalCount.toLocaleString()}개 리뷰
            </div>
          </div>

          {/* 별점 분포 */}
          <div className="flex-1">{renderRatingDistribution()}</div>
        </div>
      </div>

      {/* 필터 및 정렬 */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
        <div className="flex gap-2">
          <button
            onClick={handlePhotosFilter}
            className={`px-4 py-2 rounded-lg border transition-colors ${
              hasPhotos
                ? 'bg-blue-50 border-blue-500 text-blue-700'
                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            사진 리뷰만
          </button>
          {selectedRating && (
            <button
              onClick={() => handleRatingFilter(undefined)}
              className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 flex items-center gap-2"
            >
              {selectedRating}점
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
        </div>

        <select
          value={sortBy}
          onChange={(e) => handleSortChange(e.target.value as SortOption)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="recent">최신순</option>
          <option value="rating_desc">평점 높은순</option>
          <option value="rating_asc">평점 낮은순</option>
          <option value="helpful">도움돼요순</option>
        </select>
      </div>

      {/* 리뷰 목록 */}
      {isLoading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
        </div>
      ) : reviews.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">리뷰가 없습니다</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reviews.map((review) => (
            <ReviewCard
              key={review.id}
              review={review}
              onHelpfulClick={onHelpfulClick}
              onImageClick={onImageClick}
              currentUserId={currentUserId}
              onEdit={onEditReview}
              onDelete={onDeleteReview}
            />
          ))}
        </div>
      )}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
          >
            이전
          </button>

          <div className="flex gap-1">
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }

              return (
                <button
                  key={pageNum}
                  onClick={() => onPageChange(pageNum)}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    currentPage === pageNum
                      ? 'bg-blue-600 text-white'
                      : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
          >
            다음
          </button>
        </div>
      )}
    </div>
  );
};

export default ReviewList;
