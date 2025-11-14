/**
 * 대시보드 메인 페이지
 *
 * 보안팀을 위한 실시간 거래 통계 및 모니터링 대시보드입니다.
 */

import { useState } from "react";
import { useDashboardStats } from "../hooks/useDashboardData";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

// 색상 팔레트
const RISK_COLORS = {
  low: "#10b981", // green-500
  medium: "#f59e0b", // amber-500
  high: "#ef4444", // red-500
};

const STATUS_COLORS = {
  approved: "#10b981", // green-500
  blocked: "#ef4444", // red-500
  manual_review: "#f59e0b", // amber-500
};

const Dashboard = () => {
  const [timeRange, setTimeRange] = useState<"1h" | "24h" | "7d" | "30d">(
    "24h"
  );
  const { data: stats, isLoading, error, refetch } = useDashboardStats(timeRange);

  // 시간 범위 변경 핸들러
  const handleTimeRangeChange = (range: "1h" | "24h" | "7d" | "30d") => {
    setTimeRange(range);
  };

  // 로딩 상태
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">대시보드 데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-red-800 font-semibold mb-2">
            데이터 로드 실패
          </h2>
          <p className="text-red-600 mb-4">
            대시보드 데이터를 불러오는 중 오류가 발생했습니다.
          </p>
          <button
            onClick={() => refetch()}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  // 차트 데이터 준비
  const riskDistributionData = [
    { name: "낮음", value: stats.risk_distribution.low, color: RISK_COLORS.low },
    { name: "중간", value: stats.risk_distribution.medium, color: RISK_COLORS.medium },
    { name: "높음", value: stats.risk_distribution.high, color: RISK_COLORS.high },
  ];

  const transactionStatusData = [
    { name: "승인", value: stats.transaction_summary.approved },
    { name: "차단", value: stats.transaction_summary.blocked },
    { name: "검토", value: stats.transaction_summary.manual_review },
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* 헤더 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          보안팀 대시보드
        </h1>
        <p className="text-gray-600">실시간 거래 모니터링 및 통계</p>
      </div>

      {/* 시간 범위 선택 */}
      <div className="mb-6 flex gap-2">
        {(["1h", "24h", "7d", "30d"] as const).map((range) => (
          <button
            key={range}
            onClick={() => handleTimeRangeChange(range)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              timeRange === range
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-100"
            }`}
          >
            {range === "1h" && "1시간"}
            {range === "24h" && "24시간"}
            {range === "7d" && "7일"}
            {range === "30d" && "30일"}
          </button>
        ))}
        <div className="ml-auto text-sm text-gray-500 flex items-center">
          마지막 업데이트: {new Date(stats.generated_at).toLocaleTimeString("ko-KR")}
        </div>
      </div>

      {/* 주요 지표 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {/* 총 거래 수 */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">총 거래</h3>
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
              <svg
                className="w-6 h-6 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {stats.transaction_summary.total.toLocaleString()}
          </p>
        </div>

        {/* 차단된 거래 */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">차단됨</h3>
            <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
              <svg
                className="w-6 h-6 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                />
              </svg>
            </div>
          </div>
          <p className="text-3xl font-bold text-red-600">
            {stats.transaction_summary.blocked.toLocaleString()}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {((stats.transaction_summary.blocked / stats.transaction_summary.total) * 100).toFixed(1)}% 차단율
          </p>
        </div>

        {/* 검토 대기 */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">검토 대기</h3>
            <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
              <svg
                className="w-6 h-6 text-amber-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
          </div>
          <p className="text-3xl font-bold text-amber-600">
            {stats.review_queue_summary.pending.toLocaleString()}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            총 {stats.review_queue_summary.total}건 중
          </p>
        </div>

        {/* FDS 평가 시간 */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">평균 평가시간</h3>
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center ${
                stats.performance_status === "good"
                  ? "bg-green-100"
                  : "bg-orange-100"
              }`}
            >
              <svg
                className={`w-6 h-6 ${
                  stats.performance_status === "good"
                    ? "text-green-600"
                    : "text-orange-600"
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {stats.avg_evaluation_time_ms}
            <span className="text-lg text-gray-500 ml-1">ms</span>
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {stats.performance_status === "good" ? "목표 달성 (100ms 이내)" : "성능 저하"}
          </p>
        </div>
      </div>

      {/* 차트 영역 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* 위험도별 분포 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            위험도별 거래 분포
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={riskDistributionData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) =>
                  `${name} ${(percent * 100).toFixed(0)}%`
                }
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {riskDistributionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* 거래 상태별 분포 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            거래 상태별 분포
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={transactionStatusData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" name="거래 수" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 최근 고위험 알림 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          최근 고위험 거래 알림
        </h3>
        {stats.recent_alerts.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            최근 고위험 거래가 없습니다.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    시간
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    주문 ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    금액
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    위험점수
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    IP 주소
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    상태
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {stats.recent_alerts.map((alert) => (
                  <tr key={alert.transaction_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(alert.created_at).toLocaleString("ko-KR")}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {alert.order_id.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ₩{alert.amount.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        {alert.risk_score}점
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {alert.ip_address}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          alert.evaluation_status === "blocked"
                            ? "bg-red-100 text-red-800"
                            : alert.evaluation_status === "manual_review"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-green-100 text-green-800"
                        }`}
                      >
                        {alert.evaluation_status === "blocked" && "차단됨"}
                        {alert.evaluation_status === "manual_review" && "검토중"}
                        {alert.evaluation_status === "approved" && "승인됨"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
