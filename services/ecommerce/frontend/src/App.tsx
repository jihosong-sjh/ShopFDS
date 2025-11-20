/**
 * 메인 App 컴포넌트
 *
 * React Router 및 React Query 설정
 * 코드 스플리팅 적용 (React.lazy, Suspense)
 */

import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { Layout } from './components/Layout';
import { useAuthStore } from './stores/authStore';

// 코드 스플리팅: Lazy Loading으로 초기 번들 크기 최소화
const Register = lazy(() => import('./pages/Register').then(module => ({ default: module.Register })));
const Login = lazy(() => import('./pages/Login').then(module => ({ default: module.Login })));
const ProductList = lazy(() => import('./pages/ProductList').then(module => ({ default: module.ProductList })));
const ProductDetail = lazy(() => import('./pages/ProductDetail').then(module => ({ default: module.ProductDetail })));
const Cart = lazy(() => import('./pages/Cart').then(module => ({ default: module.Cart })));
const Checkout = lazy(() => import('./pages/Checkout').then(module => ({ default: module.Checkout })));
const Orders = lazy(() => import('./pages/Orders').then(module => ({ default: module.Orders })));
const OrderTracking = lazy(() => import('./pages/OrderTracking').then(module => ({ default: module.OrderTracking })));

// Phase 10에서 추가된 페이지들 (Lazy Loading)
const SearchPage = lazy(() => import('./pages/SearchPage'));
const WishlistPage = lazy(() => import('./pages/WishlistPage'));
const ComparisonPage = lazy(() => import('./pages/ComparisonPage'));
const MyPage = lazy(() => import('./pages/MyPage'));
const AddressManagementPage = lazy(() => import('./pages/AddressManagementPage'));
const PointsCouponsPage = lazy(() => import('./pages/PointsCouponsPage'));
const CheckoutPage = lazy(() => import('./pages/CheckoutPage'));
const OrderCompletePage = lazy(() => import('./pages/OrderCompletePage'));
const OfflinePage = lazy(() => import('./pages/OfflinePage'));

// React Query 클라이언트 설정
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5분
    },
  },
});

// 인증이 필요한 라우트 보호 컴포넌트
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// 홈 페이지 컴포넌트
const Home: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          ShopFDS에 오신 것을 환영합니다
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          AI/ML 기반 사기 탐지 시스템이 통합된 안전한 이커머스 플랫폼
        </p>
        <div className="flex justify-center gap-4">
          <a
            href="/products"
            className="px-8 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-lg"
          >
            쇼핑 시작하기
          </a>
          <a
            href="/register"
            className="px-8 py-3 border border-indigo-600 text-indigo-600 rounded-md hover:bg-indigo-50 text-lg"
          >
            회원가입
          </a>
        </div>
      </div>

      {/* 특징 섹션 */}
      <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="text-center">
          <div className="text-4xl mb-4">🛡️</div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">안전한 거래</h3>
          <p className="text-gray-600">
            실시간 사기 탐지 시스템으로 안전하게 쇼핑하세요
          </p>
        </div>
        <div className="text-center">
          <div className="text-4xl mb-4">⚡</div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">빠른 배송</h3>
          <p className="text-gray-600">
            주문 후 신속하게 배송해드립니다
          </p>
        </div>
        <div className="text-center">
          <div className="text-4xl mb-4">💳</div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">간편 결제</h3>
          <p className="text-gray-600">
            다양한 결제 수단으로 편리하게 결제하세요
          </p>
        </div>
      </div>
    </div>
  );
};

// Suspense 로딩 폴백 컴포넌트
const LoadingFallback: React.FC = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
    <span className="ml-3 text-gray-600">로딩 중...</span>
  </div>
);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="register" element={<Register />} />
              <Route path="login" element={<Login />} />
              <Route path="products" element={<ProductList />} />
              <Route path="products/:productId" element={<ProductDetail />} />
              <Route path="search" element={<SearchPage />} />

              {/* 인증 필요한 라우트 */}
              <Route
                path="cart"
                element={
                  <ProtectedRoute>
                    <Cart />
                  </ProtectedRoute>
                }
              />
              <Route
                path="checkout"
                element={
                  <ProtectedRoute>
                    <Checkout />
                  </ProtectedRoute>
                }
              />
              <Route
                path="orders"
                element={
                  <ProtectedRoute>
                    <Orders />
                  </ProtectedRoute>
                }
              />
              <Route
                path="orders/:orderId"
                element={
                  <ProtectedRoute>
                    <OrderTracking />
                  </ProtectedRoute>
                }
              />
              <Route
                path="wishlist"
                element={
                  <ProtectedRoute>
                    <WishlistPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="comparison"
                element={
                  <ProtectedRoute>
                    <ComparisonPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="my"
                element={
                  <ProtectedRoute>
                    <MyPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="my/addresses"
                element={
                  <ProtectedRoute>
                    <AddressManagementPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="my/points-coupons"
                element={
                  <ProtectedRoute>
                    <PointsCouponsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="checkout-new"
                element={
                  <ProtectedRoute>
                    <CheckoutPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="order-complete"
                element={
                  <ProtectedRoute>
                    <OrderCompletePage />
                  </ProtectedRoute>
                }
              />
              <Route path="offline" element={<OfflinePage />} />

              {/* 404 */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
