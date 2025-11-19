import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Review } from '../components/ReviewCard';
import { ReviewFormData } from '../components/ReviewForm';
import { ReviewFilters, SortOption } from '../components/ReviewList';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface ReviewsResponse {
  reviews: Review[];
  total_count: number;
  average_rating: number;
  rating_distribution: Record<string, number>;
  page: number;
  total_pages: number;
}

interface UseReviewsParams {
  productId: string;
  page?: number;
  limit?: number;
  filters?: ReviewFilters;
  sort?: SortOption;
  enabled?: boolean;
}

/**
 * useReviews Hook
 *
 * React Query를 사용하여 리뷰 데이터를 관리합니다.
 * 리뷰 조회, 작성, 수정, 삭제, 도움돼요 기능을 제공합니다.
 *
 * @param productId - 상품 ID
 * @param page - 페이지 번호
 * @param limit - 페이지당 리뷰 수
 * @param filters - 필터 옵션 (별점, 사진 리뷰)
 * @param sort - 정렬 옵션
 * @param enabled - 쿼리 활성화 여부
 */
export const useReviews = ({
  productId,
  page = 1,
  limit = 10,
  filters = {},
  sort = 'recent',
  enabled = true,
}: UseReviewsParams) => {
  const queryClient = useQueryClient();

  // 리뷰 목록 조회
  const {
    data: reviewsData,
    isLoading,
    error,
    refetch,
  } = useQuery<ReviewsResponse>({
    queryKey: ['reviews', productId, page, limit, filters, sort],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
        sort,
      });

      if (filters.rating) {
        params.append('rating', filters.rating.toString());
      }

      if (filters.has_photos) {
        params.append('has_photos', 'true');
      }

      const response = await axios.get<ReviewsResponse>(
        `${API_BASE_URL}/v1/products/${productId}/reviews?${params.toString()}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );

      return response.data;
    },
    enabled,
    staleTime: 60 * 1000, // 1분간 캐시 유지
  });

  // 리뷰 작성
  const createReviewMutation = useMutation({
    mutationFn: async (data: ReviewFormData) => {
      const response = await axios.post(
        `${API_BASE_URL}/v1/reviews`,
        data,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json',
          },
        }
      );
      return response.data;
    },
    onSuccess: () => {
      // 리뷰 목록 다시 조회
      queryClient.invalidateQueries({ queryKey: ['reviews', productId] });
    },
  });

  // 리뷰 수정
  const updateReviewMutation = useMutation({
    mutationFn: async ({
      reviewId,
      data,
    }: {
      reviewId: string;
      data: Partial<ReviewFormData>;
    }) => {
      const response = await axios.put(
        `${API_BASE_URL}/v1/reviews/${reviewId}`,
        data,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json',
          },
        }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews', productId] });
    },
  });

  // 리뷰 삭제
  const deleteReviewMutation = useMutation({
    mutationFn: async (reviewId: string) => {
      const response = await axios.delete(
        `${API_BASE_URL}/v1/reviews/${reviewId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews', productId] });
    },
  });

  // 도움돼요 투표
  const helpfulVoteMutation = useMutation({
    mutationFn: async ({
      reviewId,
      isHelpful,
    }: {
      reviewId: string;
      isHelpful: boolean;
    }) => {
      if (isHelpful) {
        // 도움돼요 추가
        const response = await axios.post(
          `${API_BASE_URL}/v1/reviews/${reviewId}/vote`,
          {},
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            },
          }
        );
        return response.data;
      } else {
        // 도움돼요 취소
        const response = await axios.delete(
          `${API_BASE_URL}/v1/reviews/${reviewId}/vote`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            },
          }
        );
        return response.data;
      }
    },
    onMutate: async ({ reviewId, isHelpful }) => {
      // 낙관적 업데이트: 즉시 UI 반영
      await queryClient.cancelQueries({ queryKey: ['reviews', productId] });

      const previousData = queryClient.getQueryData<ReviewsResponse>([
        'reviews',
        productId,
        page,
        limit,
        filters,
        sort,
      ]);

      if (previousData) {
        const updatedReviews = previousData.reviews.map((review) =>
          review.id === reviewId
            ? {
                ...review,
                is_helpful_by_me: isHelpful,
                helpful_count: review.helpful_count + (isHelpful ? 1 : -1),
              }
            : review
        );

        queryClient.setQueryData(['reviews', productId, page, limit, filters, sort], {
          ...previousData,
          reviews: updatedReviews,
        });
      }

      return { previousData };
    },
    onError: (err, variables, context) => {
      // 에러 발생 시 이전 데이터로 복구
      if (context?.previousData) {
        queryClient.setQueryData(
          ['reviews', productId, page, limit, filters, sort],
          context.previousData
        );
      }
    },
    onSettled: () => {
      // 서버 데이터와 동기화
      queryClient.invalidateQueries({ queryKey: ['reviews', productId] });
    },
  });

  return {
    // 데이터
    reviews: reviewsData?.reviews || [],
    totalCount: reviewsData?.total_count || 0,
    averageRating: reviewsData?.average_rating || 0,
    ratingDistribution: reviewsData?.rating_distribution || {},
    currentPage: reviewsData?.page || 1,
    totalPages: reviewsData?.total_pages || 1,

    // 상태
    isLoading,
    error,

    // 함수
    refetch,
    createReview: createReviewMutation.mutateAsync,
    updateReview: updateReviewMutation.mutateAsync,
    deleteReview: deleteReviewMutation.mutateAsync,
    voteHelpful: helpfulVoteMutation.mutateAsync,

    // 뮤테이션 상태
    isCreating: createReviewMutation.isPending,
    isUpdating: updateReviewMutation.isPending,
    isDeleting: deleteReviewMutation.isPending,
    isVoting: helpfulVoteMutation.isPending,
  };
};

export default useReviews;
