/**
 * 상품 비교 Hook
 * Zustand store를 사용하여 비교 목록 관리
 * 토스트 알림 및 사용자 피드백 제공
 */

import { useCallback } from 'react';
import {
  useComparisonStore,
  ComparisonProduct,
} from '../stores/comparisonStore';

interface UseComparisonReturn {
  products: ComparisonProduct[];
  productCount: number;
  maxProducts: number;
  addProduct: (product: ComparisonProduct) => {
    success: boolean;
    message: string;
  };
  removeProduct: (productId: string) => void;
  clearAll: () => void;
  isInComparison: (productId: string) => boolean;
  canAddMore: boolean;
  toggleProduct: (product: ComparisonProduct) => {
    success: boolean;
    message: string;
  };
}

export const useComparison = (): UseComparisonReturn => {
  const {
    products,
    addProduct: storeAddProduct,
    removeProduct: storeRemoveProduct,
    clearAll: storeClearAll,
    isInComparison: storeIsInComparison,
    canAddMore: storeCanAddMore,
    maxProducts,
  } = useComparisonStore();

  const addProduct = useCallback(
    (product: ComparisonProduct) => {
      // 이미 비교 목록에 있는 경우
      if (storeIsInComparison(product.id)) {
        return {
          success: false,
          message: '이미 비교 목록에 추가된 상품입니다.',
        };
      }

      // 최대 개수 초과
      if (!storeCanAddMore()) {
        return {
          success: false,
          message: `최대 ${maxProducts}개까지만 비교할 수 있습니다.`,
        };
      }

      const success = storeAddProduct(product);

      if (success) {
        return {
          success: true,
          message: `${product.name}이(가) 비교 목록에 추가되었습니다.`,
        };
      }

      return {
        success: false,
        message: '상품 추가에 실패했습니다.',
      };
    },
    [storeAddProduct, storeIsInComparison, storeCanAddMore, maxProducts]
  );

  const removeProduct = useCallback(
    (productId: string) => {
      storeRemoveProduct(productId);
    },
    [storeRemoveProduct]
  );

  const clearAll = useCallback(() => {
    storeClearAll();
  }, [storeClearAll]);

  const isInComparison = useCallback(
    (productId: string) => {
      return storeIsInComparison(productId);
    },
    [storeIsInComparison]
  );

  const toggleProduct = useCallback(
    (product: ComparisonProduct) => {
      if (storeIsInComparison(product.id)) {
        storeRemoveProduct(product.id);
        return {
          success: true,
          message: `${product.name}이(가) 비교 목록에서 제거되었습니다.`,
        };
      } else {
        return addProduct(product);
      }
    },
    [storeIsInComparison, storeRemoveProduct, addProduct]
  );

  return {
    products,
    productCount: products.length,
    maxProducts,
    addProduct,
    removeProduct,
    clearAll,
    isInComparison,
    canAddMore: storeCanAddMore(),
    toggleProduct,
  };
};
