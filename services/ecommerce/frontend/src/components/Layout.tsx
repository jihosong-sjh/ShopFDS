/**
 * 메인 레이아웃 컴포넌트
 *
 * 헤더, 네비게이션 바, 푸터 포함
 */

import React from 'react';
import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useCartStore } from '../stores/cartStore';

export const Layout: React.FC = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated, clearAuth } = useAuthStore();
  const cartCount = useCartStore((state) => state.cartCount);

  const handleLogout = () => {
    clearAuth();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* 헤더 */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* 로고 */}
            <Link to="/" className="flex items-center">
              <span className="text-2xl font-bold text-indigo-600">ShopFDS</span>
            </Link>

            {/* 네비게이션 */}
            <nav className="flex items-center gap-6">
              <Link to="/products" className="text-gray-700 hover:text-indigo-600">
                상품
              </Link>

              {isAuthenticated ? (
                <>
                  <Link to="/orders" className="text-gray-700 hover:text-indigo-600">
                    주문 내역
                  </Link>

                  <Link to="/cart" className="relative text-gray-700 hover:text-indigo-600">
                    장바구니
                    {cartCount > 0 && (
                      <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                        {cartCount}
                      </span>
                    )}
                  </Link>

                  <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-600">{user?.name}님</span>
                    <button
                      onClick={handleLogout}
                      className="text-sm text-gray-700 hover:text-indigo-600"
                    >
                      로그아웃
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="text-gray-700 hover:text-indigo-600"
                  >
                    로그인
                  </Link>
                  <Link
                    to="/register"
                    className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                  >
                    회원가입
                  </Link>
                </>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* 푸터 */}
      <footer className="bg-gray-50 border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <p className="text-center text-gray-600 text-sm">
            © 2025 ShopFDS. AI/ML 기반 이커머스 FDS 플랫폼
          </p>
        </div>
      </footer>
    </div>
  );
};
