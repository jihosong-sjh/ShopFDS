/**
 * PointsCouponsPage Component
 *
 * 적립금 & 쿠폰 목록 페이지
 */

import React from "react";

export const PointsCouponsPage: React.FC = () => {
  // TODO: 적립금/쿠폰 API 연동 (향후 구현)

  return (
    <div className="space-y-8">
      {/* 적립금 섹션 */}
      <section>
        <h2 className="text-xl font-bold mb-4">내 적립금</h2>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="flex justify-between items-center">
            <span className="text-gray-700">사용 가능한 적립금</span>
            <span className="text-2xl font-bold text-blue-600">0원</span>
          </div>
          <p className="mt-2 text-sm text-gray-600">
            구매 확정 시 적립금이 자동으로 적립됩니다.
          </p>
        </div>
      </section>

      {/* 쿠폰 섹션 */}
      <section>
        <h2 className="text-xl font-bold mb-4">내 쿠폰</h2>
        <div className="bg-white border rounded-lg divide-y">
          <div className="p-4 text-center text-gray-500">
            보유한 쿠폰이 없습니다.
          </div>
        </div>
        <p className="mt-4 text-sm text-gray-600">
          [TIP] 이벤트 페이지에서 다양한 쿠폰을 받아보세요!
        </p>
      </section>
    </div>
  );
};
