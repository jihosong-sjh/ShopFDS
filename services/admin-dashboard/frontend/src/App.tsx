/**
 * App 컴포넌트
 *
 * 보안팀 대시보드의 메인 애플리케이션 컴포넌트입니다.
 * 라우팅 및 전역 상태 관리를 설정합니다.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import ReviewQueue from "./pages/ReviewQueue";
import TransactionDetail from "./pages/TransactionDetail";
import NotificationBell from "./components/NotificationBell";

// React Query 클라이언트 생성
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// 레이아웃 컴포넌트
const Layout = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 네비게이션 헤더 */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-8">
              <h1 className="text-2xl font-bold text-gray-900">
                ShopFDS 보안팀
              </h1>
              <nav className="flex space-x-4">
                <Link
                  to="/"
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive("/")
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  대시보드
                </Link>
                <Link
                  to="/review-queue"
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive("/review-queue")
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  검토 큐
                </Link>
              </nav>
            </div>
            <div className="flex items-center space-x-4">
              <NotificationBell />
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-sm font-medium">관</span>
                </div>
                <span className="text-sm text-gray-700">관리자</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main>{children}</main>
    </div>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/review-queue" element={<ReviewQueue />} />
            <Route path="/review-queue/:reviewQueueId" element={<TransactionDetail />} />
            <Route path="/transactions/:transactionId" element={<TransactionDetail />} />
            <Route
              path="*"
              element={
                <div className="flex items-center justify-center min-h-screen">
                  <div className="text-center">
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">
                      404 - 페이지를 찾을 수 없습니다
                    </h2>
                    <p className="text-gray-600 mb-4">
                      요청하신 페이지가 존재하지 않습니다.
                    </p>
                    <Link
                      to="/"
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      대시보드로 돌아가기
                    </Link>
                  </div>
                </div>
              }
            />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
