/**
 * useWishlist Hook
 *
 * 위시리스트 관리를 위한 React Query 기반 Hook
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface WishlistItem {
  id: string;
  product: {
    id: string;
    name: string;
    price: number;
    discounted_price?: number;
    image_url?: string;
    in_stock: boolean;
    rating: number;
    review_count: number;
  };
  added_at: string;
}

interface WishlistResponse {
  items: WishlistItem[];
  total_count: number;
}

interface MoveToCartRequest {
  item_ids: string[];
}

interface MoveToCartResponse {
  message: string;
  success_count: number;
  failed_items: Array<{ item_id: string; reason: string }>;
}

// API 클라이언트 함수들
const wishlistApi = {
  // 위시리스트 조회
  getWishlist: async (page = 1, limit = 20): Promise<WishlistResponse> => {
    const token = localStorage.getItem('access_token');
    const response = await axios.get(`${API_BASE_URL}/v1/wishlist`, {
      params: { page, limit },
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  },

  // 위시리스트에 추가
  addToWishlist: async (productId: string): Promise<{ id: string; message: string }> => {
    const token = localStorage.getItem('access_token');
    const response = await axios.post(
      `${API_BASE_URL}/v1/wishlist`,
      { product_id: productId },
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  },

  // 위시리스트에서 삭제
  removeFromWishlist: async (itemId: string): Promise<{ message: string }> => {
    const token = localStorage.getItem('access_token');
    const response = await axios.delete(`${API_BASE_URL}/v1/wishlist/${itemId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  },

  // 장바구니로 이동
  moveToCart: async (itemIds: string[]): Promise<MoveToCartResponse> => {
    const token = localStorage.getItem('access_token');
    const response = await axios.post(
      `${API_BASE_URL}/v1/wishlist/move-to-cart`,
      { item_ids: itemIds },
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  },
};

export const useWishlist = (page = 1, limit = 20) => {
  const queryClient = useQueryClient();

  // 위시리스트 조회
  const {
    data: wishlistData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['wishlist', page, limit],
    queryFn: () => wishlistApi.getWishlist(page, limit),
    staleTime: 30000, // 30초
  });

  // 위시리스트 추가 Mutation
  const addToWishlistMutation = useMutation({
    mutationFn: wishlistApi.addToWishlist,
    onSuccess: () => {
      // 위시리스트 캐시 무효화 (자동 리패치)
      queryClient.invalidateQueries({ queryKey: ['wishlist'] });
    },
  });

  // 위시리스트 삭제 Mutation
  const removeFromWishlistMutation = useMutation({
    mutationFn: wishlistApi.removeFromWishlist,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wishlist'] });
    },
  });

  // 장바구니로 이동 Mutation
  const moveToCartMutation = useMutation({
    mutationFn: wishlistApi.moveToCart,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wishlist'] });
      queryClient.invalidateQueries({ queryKey: ['cart'] }); // 장바구니도 리패치
    },
  });

  return {
    // 데이터
    wishlistItems: wishlistData?.items || [],
    totalCount: wishlistData?.total_count || 0,
    isLoading,
    error,

    // 액션
    addToWishlist: addToWishlistMutation.mutate,
    removeFromWishlist: removeFromWishlistMutation.mutate,
    moveToCart: moveToCartMutation.mutate,
    refetch,

    // 로딩 상태
    isAddingToWishlist: addToWishlistMutation.isPending,
    isRemovingFromWishlist: removeFromWishlistMutation.isPending,
    isMovingToCart: moveToCartMutation.isPending,

    // 에러
    addError: addToWishlistMutation.error,
    removeError: removeFromWishlistMutation.error,
    moveError: moveToCartMutation.error,
  };
};

export default useWishlist;
