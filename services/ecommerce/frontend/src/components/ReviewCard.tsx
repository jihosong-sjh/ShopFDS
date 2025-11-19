import React, { useState } from 'react';
import LazyImage from './LazyImage';

export interface Review {
  id: string;
  user: {
    id: string;
    name: string;
    masked_name: string;
  };
  rating: number;
  title: string;
  content: string;
  images: string[];
  helpful_count: number;
  is_verified_purchase: boolean;
  is_helpful_by_me: boolean;
  created_at: string;
}

interface ReviewCardProps {
  review: Review;
  onHelpfulClick: (reviewId: string, isHelpful: boolean) => Promise<void>;
  onImageClick?: (images: string[], index: number) => void;
  currentUserId?: string;
  onEdit?: (review: Review) => void;
  onDelete?: (reviewId: string) => void;
}

/**
 * ReviewCard 컴포넌트
 *
 * 개별 리뷰를 카드 형태로 표시합니다.
 * 별점, 내용, 사진, 도움돼요 버튼, 인증 배지를 포함합니다.
 *
 * @param review - 리뷰 데이터
 * @param onHelpfulClick - 도움돼요 클릭 콜백
 * @param onImageClick - 이미지 클릭 콜백 (확대 보기)
 * @param currentUserId - 현재 로그인한 사용자 ID
 * @param onEdit - 수정 버튼 클릭 콜백
 * @param onDelete - 삭제 버튼 클릭 콜백
 */
const ReviewCard: React.FC<ReviewCardProps> = ({
  review,
  onHelpfulClick,
  onImageClick,
  currentUserId,
  onEdit,
  onDelete,
}) => {
  const [isHelpful, setIsHelpful] = useState<boolean>(review.is_helpful_by_me);
  const [helpfulCount, setHelpfulCount] = useState<number>(
    review.helpful_count
  );
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const isOwnReview = currentUserId === review.user.id;

  const handleHelpfulClick = async () => {
    if (isProcessing || isOwnReview) return;

    setIsProcessing(true);
    try {
      const newIsHelpful = !isHelpful;
      await onHelpfulClick(review.id, newIsHelpful);

      setIsHelpful(newIsHelpful);
      setHelpfulCount((prev) => (newIsHelpful ? prev + 1 : prev - 1));
    } catch (error) {
      console.error('도움돼요 처리 실패:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const renderStars = (rating: number) => {
    return (
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <svg
            key={star}
            className={`w-5 h-5 ${
              star <= rating ? 'text-yellow-400 fill-current' : 'text-gray-300'
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1}
              d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
            />
          </svg>
        ))}
      </div>
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInDays = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (diffInDays === 0) return '오늘';
    if (diffInDays === 1) return '어제';
    if (diffInDays < 7) return `${diffInDays}일 전`;
    if (diffInDays < 30) return `${Math.floor(diffInDays / 7)}주 전`;
    if (diffInDays < 365) return `${Math.floor(diffInDays / 30)}개월 전`;
    return date.toLocaleDateString('ko-KR');
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
      {/* 헤더: 사용자 정보 및 별점 */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900">
                {review.user.masked_name}
              </span>
              {review.is_verified_purchase && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded">
                  <svg
                    className="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  구매 인증
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1">
              {renderStars(review.rating)}
              <span className="text-sm text-gray-500">
                {formatDate(review.created_at)}
              </span>
            </div>
          </div>
        </div>

        {/* 수정/삭제 버튼 (본인 리뷰만) */}
        {isOwnReview && (onEdit || onDelete) && (
          <div className="flex gap-2">
            {onEdit && (
              <button
                onClick={() => onEdit(review)}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                수정
              </button>
            )}
            {onDelete && (
              <button
                onClick={() => onDelete(review.id)}
                className="text-sm text-red-600 hover:text-red-900"
              >
                삭제
              </button>
            )}
          </div>
        )}
      </div>

      {/* 제목 */}
      <h3 className="font-semibold text-gray-900 mb-2">{review.title}</h3>

      {/* 내용 */}
      <p className="text-gray-700 leading-relaxed mb-4 whitespace-pre-wrap">
        {review.content}
      </p>

      {/* 사진 리뷰 */}
      {review.images && review.images.length > 0 && (
        <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
          {review.images.map((image, index) => (
            <button
              key={index}
              onClick={() =>
                onImageClick && onImageClick(review.images, index)
              }
              className="flex-shrink-0 w-24 h-24 rounded-lg overflow-hidden hover:ring-2 hover:ring-blue-500 transition-all"
            >
              <LazyImage
                src={image}
                alt={`리뷰 이미지 ${index + 1}`}
                className="w-full h-full object-cover"
              />
            </button>
          ))}
        </div>
      )}

      {/* 도움돼요 버튼 */}
      <div className="flex items-center gap-2 pt-4 border-t border-gray-100">
        <button
          onClick={handleHelpfulClick}
          disabled={isProcessing || isOwnReview}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border transition-all ${
            isHelpful
              ? 'bg-blue-50 border-blue-500 text-blue-700'
              : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
          } ${
            isOwnReview || isProcessing
              ? 'opacity-50 cursor-not-allowed'
              : 'cursor-pointer'
          }`}
          aria-label={isHelpful ? '도움돼요 취소' : '도움돼요'}
        >
          <svg
            className="w-5 h-5"
            fill={isHelpful ? 'currentColor' : 'none'}
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
            />
          </svg>
          <span className="text-sm font-medium">
            도움돼요 {helpfulCount > 0 && `(${helpfulCount})`}
          </span>
        </button>

        {isOwnReview && (
          <span className="text-xs text-gray-500">본인이 작성한 리뷰입니다</span>
        )}
      </div>
    </div>
  );
};

export default ReviewCard;
