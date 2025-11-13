/**
 * 장바구니 상태 관리 (Zustand)
 *
 * 장바구니 임시 상태 관리 (서버와 동기화)
 */

import { create } from 'zustand';

interface CartState {
  cartCount: number;

  // Actions
  setCartCount: (count: number) => void;
  incrementCartCount: () => void;
  decrementCartCount: () => void;
  resetCartCount: () => void;
}

export const useCartStore = create<CartState>((set) => ({
  cartCount: 0,

  setCartCount: (count) => set({ cartCount: count }),

  incrementCartCount: () =>
    set((state) => ({ cartCount: state.cartCount + 1 })),

  decrementCartCount: () =>
    set((state) => ({ cartCount: Math.max(0, state.cartCount - 1) })),

  resetCartCount: () => set({ cartCount: 0 }),
}));
