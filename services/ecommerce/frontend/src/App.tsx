/**
 * 메인 App 컴포넌트
 *
 * React Router 및 React Query 설정
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { Layout } from './components/Layout';
import { Register } from './pages/Register';
import { Login } from './pages/Login';
import { ProductList } from './pages/ProductList';
import { ProductDetail } from './pages/ProductDetail';
import { Cart } from './pages/Cart';
import { Checkout } from './pages/Checkout';
import { Orders } from './pages/Orders';
import { OrderTracking } from './pages/OrderTracking';

import { useAuthStore } from './stores/authStore';

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

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="register" element={<Register />} />
            <Route path="login" element={<Login />} />
            <Route path="products" element={<ProductList />} />
            <Route path="products/:productId" element={<ProductDetail />} />

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

            {/* 404 */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
