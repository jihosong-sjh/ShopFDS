/**
 * MyPage Component
 *
 * 마이페이지 레이아웃 (사이드바, 메뉴)
 */

import React from "react";
import { Link, Outlet, useLocation } from "react-router-dom";

const menuItems = [
  { path: "/mypage/addresses", label: "배송지 관리" },
  { path: "/mypage/points-coupons", label: "적립금 & 쿠폰" },
  { path: "/mypage/orders", label: "주문 내역" },
  { path: "/mypage/wishlist", label: "위시리스트" },
  { path: "/mypage/reviews", label: "내 리뷰" },
  { path: "/mypage/profile", label: "회원정보 수정" },
];

export const MyPage: React.FC = () => {
  const location = useLocation();

  return (
    <div className="max-w-7xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">마이페이지</h1>

      <div className="flex gap-8">
        {/* 사이드바 */}
        <aside className="w-64 flex-shrink-0">
          <nav className="bg-white border rounded-lg p-4">
            <ul className="space-y-2">
              {menuItems.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <li key={item.path}>
                    <Link
                      to={item.path}
                      className={`block px-4 py-2 rounded-md transition-colors ${
                        isActive
                          ? "bg-blue-600 text-white font-medium"
                          : "text-gray-700 hover:bg-gray-100"
                      }`}
                    >
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        </aside>

        {/* 메인 컨텐츠 영역 */}
        <main className="flex-1">
          <div className="bg-white border rounded-lg p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default MyPage;
