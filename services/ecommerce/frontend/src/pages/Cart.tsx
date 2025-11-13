/**
 * 장바구니 페이지
 *
 * T042: 장바구니 페이지 구현
 */

import React, { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { cartApi, queryKeys, Cart as CartType } from '../services/api';
import { useCartStore } from '../stores/cartStore';

export const Cart: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setCartCount, decrementCartCount } = useCartStore();

  // 장바구니 조회
  const { data: cart = { cart_id: '', total_amount: 0, total_items: 0, items: [] } as CartType, isLoading } = useQuery<CartType>({
    queryKey: queryKeys.cart.current,
    queryFn: cartApi.getCart,
  });

  // 장바구니 데이터가 로드되면 카운트 업데이트
  useEffect(() => {
    if (cart && cart.items.length > 0) {
      setCartCount(cart.total_items);
    }
  }, [cart, setCartCount]);

  // 수량 변경
  const updateMutation = useMutation({
    mutationFn: ({ cartItemId, quantity }: { cartItemId: string; quantity: number }) =>
      cartApi.updateCartItem(cartItemId, quantity),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.cart.current });
    },
  });

  // 항목 삭제
  const removeMutation = useMutation({
    mutationFn: cartApi.removeCartItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.cart.current });
      decrementCartCount();
    },
  });

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <p className="text-gray-600 mb-4">장바구니가 비어있습니다.</p>
        <Link
          to="/products"
          className="inline-block px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          쇼핑 계속하기
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">장바구니</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* 장바구니 항목 목록 */}
        <div className="lg:col-span-2">
          <div className="space-y-4">
            {cart.items.map((item) => (
              <div key={item.cart_item_id} className="border rounded-lg p-4 flex gap-4">
                {/* 상품 이미지 */}
                <div className="flex-shrink-0">
                  {item.image_url ? (
                    <img
                      src={item.image_url}
                      alt={item.product_name}
                      className="w-24 h-24 object-cover rounded"
                    />
                  ) : (
                    <div className="w-24 h-24 bg-gray-200 rounded flex items-center justify-center">
                      <span className="text-gray-400 text-xs">이미지 없음</span>
                    </div>
                  )}
                </div>

                {/* 상품 정보 */}
                <div className="flex-1">
                  <Link
                    to={`/products/${item.product_id}`}
                    className="text-lg font-semibold text-gray-900 hover:text-indigo-600"
                  >
                    {item.product_name}
                  </Link>
                  <p className="text-gray-600 mt-1">₩{item.unit_price.toLocaleString()}</p>

                  {!item.is_available && (
                    <p className="text-red-600 text-sm mt-1">품절된 상품입니다</p>
                  )}

                  {/* 수량 조절 */}
                  <div className="flex items-center gap-2 mt-2">
                    <button
                      onClick={() =>
                        updateMutation.mutate({
                          cartItemId: item.cart_item_id,
                          quantity: item.quantity - 1,
                        })
                      }
                      disabled={item.quantity <= 1}
                      className="px-2 py-1 border rounded hover:bg-gray-100 disabled:opacity-50"
                    >
                      -
                    </button>
                    <span className="w-12 text-center">{item.quantity}</span>
                    <button
                      onClick={() =>
                        updateMutation.mutate({
                          cartItemId: item.cart_item_id,
                          quantity: item.quantity + 1,
                        })
                      }
                      className="px-2 py-1 border rounded hover:bg-gray-100"
                    >
                      +
                    </button>
                  </div>
                </div>

                {/* 가격 및 삭제 */}
                <div className="text-right">
                  <p className="text-lg font-bold text-gray-900">
                    ₩{item.subtotal.toLocaleString()}
                  </p>
                  <button
                    onClick={() => removeMutation.mutate(item.cart_item_id)}
                    className="mt-2 text-sm text-red-600 hover:text-red-700"
                  >
                    삭제
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 주문 요약 */}
        <div className="lg:col-span-1">
          <div className="border rounded-lg p-6 sticky top-4">
            <h2 className="text-xl font-bold text-gray-900 mb-4">주문 요약</h2>

            <div className="space-y-2 mb-4">
              <div className="flex justify-between">
                <span className="text-gray-600">상품 수</span>
                <span className="font-semibold">{cart.total_items}개</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">배송비</span>
                <span className="font-semibold">무료</span>
              </div>
              <div className="border-t pt-2 flex justify-between text-lg font-bold">
                <span>총 금액</span>
                <span className="text-indigo-600">₩{cart.total_amount.toLocaleString()}</span>
              </div>
            </div>

            <button
              onClick={() => navigate('/checkout')}
              disabled={cart.items.some((item) => !item.is_available)}
              className="w-full px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              주문하기
            </button>

            <Link
              to="/products"
              className="block w-full mt-2 px-6 py-3 border border-gray-300 text-gray-700 text-center rounded-md hover:bg-gray-50"
            >
              쇼핑 계속하기
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
