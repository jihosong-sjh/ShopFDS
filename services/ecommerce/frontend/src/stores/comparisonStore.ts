/**
 * 상품 비교 상태 관리 스토어 (Zustand + LocalStorage)
 * 최대 4개 상품까지 비교 가능
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface ComparisonProduct {
  id: string;
  name: string;
  price: number;
  image: string;
  category: string;
  brand?: string;
  rating?: number;
  reviewCount?: number;
  stock?: number;
  description?: string;
  specifications?: Record<string, string | number>;
}

interface ComparisonState {
  products: ComparisonProduct[];
  addProduct: (product: ComparisonProduct) => boolean;
  removeProduct: (productId: string) => void;
  clearAll: () => void;
  isInComparison: (productId: string) => boolean;
  canAddMore: () => boolean;
  maxProducts: number;
}

const MAX_COMPARISON_PRODUCTS = 4;
const STORAGE_KEY = 'comparison-products';

export const useComparisonStore = create<ComparisonState>()(
  persist(
    (set, get) => ({
      products: [],
      maxProducts: MAX_COMPARISON_PRODUCTS,

      addProduct: (product: ComparisonProduct) => {
        const { products, maxProducts } = get();

        // 이미 추가된 상품인지 확인
        if (products.some((p) => p.id === product.id)) {
          return false;
        }

        // 최대 개수 확인
        if (products.length >= maxProducts) {
          return false;
        }

        set({ products: [...products, product] });
        return true;
      },

      removeProduct: (productId: string) => {
        set((state) => ({
          products: state.products.filter((p) => p.id !== productId),
        }));
      },

      clearAll: () => {
        set({ products: [] });
      },

      isInComparison: (productId: string) => {
        return get().products.some((p) => p.id === productId);
      },

      canAddMore: () => {
        return get().products.length < get().maxProducts;
      },
    }),
    {
      name: STORAGE_KEY,
      // LocalStorage에 저장
      // 브라우저를 닫아도 비교 목록 유지
    }
  )
);
