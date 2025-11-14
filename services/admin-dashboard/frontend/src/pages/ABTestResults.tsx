/**
 * A/B 테스트 결과 대시보드
 *
 * A/B 테스트의 성과 지표를 비교하고 분석하는 페이지입니다.
 */

import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { abTestsApi } from "../services/api";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface GroupMetrics {
  total_transactions: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  avg_evaluation_time_ms: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  false_positive_rate: number | null;
}

interface ABTestResults {
  test_id: string;
  test_name: string;
  test_type: string;
  status: string;
  duration_hours: number | null;
  group_a: GroupMetrics;
  group_b: GroupMetrics;
  comparison: {
    f1_score_difference?: number;
    f1_score_improvement_percentage?: number;
    fpr_difference?: number;
    fpr_reduction_percentage?: number;
    evaluation_time_difference_ms?: number;
    evaluation_time_change_percentage?: number;
  };
  recommendation: string;
  winner: string | null;
  confidence_level: number | null;
}

const ABTestResults = () => {
  const { testId } = useParams<{ testId: string }>();
  const navigate = useNavigate();

  // 테스트 결과 조회
  const {
    data: results,
    isLoading,
    error,
    refetch,
  } = useQuery<ABTestResults>({
    queryKey: ["abTestResults", testId],
    queryFn: () => abTestsApi.getResults(testId!),
    enabled: !!testId,
  });

  // 로딩 상태
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">테스트 결과를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-red-800 font-semibold mb-2">데이터 로드 실패</h2>
          <p className="text-red-600 mb-4">
            테스트 결과를 불러오는 중 오류가 발생했습니다.
          </p>
          <button
            onClick={() => refetch()}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 mr-2"
          >
            다시 시도
          </button>
          <button
            onClick={() => navigate("/ab-tests")}
            className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
          >
            목록으로
          </button>
        </div>
      </div>
    );
  }

  if (!results) return null;

  // 비교 차트 데이터
  const metricsComparisonData = [
    {
      name: "정밀도",
      "그룹 A": results.group_a.precision ? results.group_a.precision * 100 : 0,
      "그룹 B": results.group_b.precision ? results.group_b.precision * 100 : 0,
    },
    {
      name: "재현율",
      "그룹 A": results.group_a.recall ? results.group_a.recall * 100 : 0,
      "그룹 B": results.group_b.recall ? results.group_b.recall * 100 : 0,
    },
    {
      name: "F1 스코어",
      "그룹 A": results.group_a.f1_score ? results.group_a.f1_score * 100 : 0,
      "그룹 B": results.group_b.f1_score ? results.group_b.f1_score * 100 : 0,
    },
  ];

  const evaluationTimeData = [
    {
      name: "평가 시간 (ms)",
      "그룹 A": results.group_a.avg_evaluation_time_ms || 0,
      "그룹 B": results.group_b.avg_evaluation_time_ms || 0,
    },
  ];

  // 승자 뱃지 색상
  const getWinnerBadgeClass = (winner: string | null) => {
    if (!winner) return "bg-gray-100 text-gray-800";
    if (winner === "A") return "bg-blue-100 text-blue-800";
    if (winner === "B") return "bg-green-100 text-green-800";
    return "bg-yellow-100 text-yellow-800";
  };

  const getWinnerText = (winner: string | null) => {
    if (!winner) return "미정";
    if (winner === "tie") return "무승부";
    return `그룹 ${winner} 승`;
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* 헤더 */}
      <div className="mb-6">
        <button
          onClick={() => navigate("/ab-tests")}
          className="text-blue-600 hover:text-blue-800 mb-2 flex items-center gap-1"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          테스트 목록으로
        </button>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          {results.test_name}
        </h1>
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span>테스트 타입: {results.test_type}</span>
          <span className="text-gray-400">|</span>
          <span>
            진행 시간: {results.duration_hours?.toFixed(1) || "0"}시간
          </span>
          <span className="text-gray-400">|</span>
          <span
            className={`px-3 py-1 rounded-full text-xs font-medium ${getWinnerBadgeClass(
              results.winner
            )}`}
          >
            {getWinnerText(results.winner)}
          </span>
        </div>
      </div>

      {/* 권장 사항 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
        <div className="flex items-start gap-3">
          <svg
            className="w-6 h-6 text-blue-600 mt-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div>
            <h3 className="text-lg font-semibold text-blue-900 mb-2">
              권장 사항
            </h3>
            <p className="text-blue-800">{results.recommendation}</p>
            {results.confidence_level && (
              <p className="text-sm text-blue-600 mt-2">
                통계적 신뢰 수준: {(results.confidence_level * 100).toFixed(1)}
                %
              </p>
            )}
          </div>
        </div>
      </div>

      {/* 주요 지표 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {/* 그룹 A 총 거래 수 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">
            그룹 A 총 거래
          </h3>
          <p className="text-3xl font-bold text-gray-900">
            {results.group_a.total_transactions.toLocaleString()}
          </p>
        </div>

        {/* 그룹 B 총 거래 수 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">
            그룹 B 총 거래
          </h3>
          <p className="text-3xl font-bold text-gray-900">
            {results.group_b.total_transactions.toLocaleString()}
          </p>
        </div>

        {/* F1 스코어 차이 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">
            F1 스코어 개선
          </h3>
          <p
            className={`text-3xl font-bold ${
              (results.comparison.f1_score_improvement_percentage || 0) > 0
                ? "text-green-600"
                : "text-red-600"
            }`}
          >
            {results.comparison.f1_score_improvement_percentage
              ? `${results.comparison.f1_score_improvement_percentage > 0 ? "+" : ""}${results.comparison.f1_score_improvement_percentage.toFixed(2)}%`
              : "N/A"}
          </p>
        </div>

        {/* 오탐률 변화 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">
            오탐률 감소
          </h3>
          <p
            className={`text-3xl font-bold ${
              (results.comparison.fpr_reduction_percentage || 0) > 0
                ? "text-green-600"
                : "text-red-600"
            }`}
          >
            {results.comparison.fpr_reduction_percentage
              ? `${results.comparison.fpr_reduction_percentage > 0 ? "+" : ""}${results.comparison.fpr_reduction_percentage.toFixed(2)}%`
              : "N/A"}
          </p>
        </div>
      </div>

      {/* 차트 영역 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* 성과 지표 비교 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            성과 지표 비교 (%)
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={metricsComparisonData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Legend />
              <Bar dataKey="그룹 A" fill="#3b82f6" />
              <Bar dataKey="그룹 B" fill="#10b981" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 평가 시간 비교 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            평균 평가 시간 (ms)
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={evaluationTimeData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="그룹 A" fill="#3b82f6" />
              <Bar dataKey="그룹 B" fill="#10b981" />
            </BarChart>
          </ResponsiveContainer>
          {results.comparison.evaluation_time_difference_ms && (
            <p className="text-sm text-gray-600 mt-2">
              차이:{" "}
              {results.comparison.evaluation_time_difference_ms > 0 ? "+" : ""}
              {results.comparison.evaluation_time_difference_ms.toFixed(2)}ms (
              {results.comparison.evaluation_time_change_percentage?.toFixed(1)}
              %)
            </p>
          )}
        </div>
      </div>

      {/* 상세 지표 테이블 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 그룹 A */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="bg-blue-600 text-white px-6 py-3">
            <h3 className="text-lg font-semibold">그룹 A (기존)</h3>
          </div>
          <div className="p-6">
            <table className="min-w-full">
              <tbody className="divide-y divide-gray-200">
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    총 거래 수
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_a.total_transactions.toLocaleString()}건
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    정탐 (TP)
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_a.true_positives.toLocaleString()}건
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    오탐 (FP)
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_a.false_positives.toLocaleString()}건
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    미탐 (FN)
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_a.false_negatives.toLocaleString()}건
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    정밀도 (Precision)
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_a.precision
                      ? `${(results.group_a.precision * 100).toFixed(2)}%`
                      : "N/A"}
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    재현율 (Recall)
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_a.recall
                      ? `${(results.group_a.recall * 100).toFixed(2)}%`
                      : "N/A"}
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    F1 스코어
                  </td>
                  <td className="py-3 text-sm font-bold text-gray-900 text-right">
                    {results.group_a.f1_score
                      ? `${(results.group_a.f1_score * 100).toFixed(2)}%`
                      : "N/A"}
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    오탐률 (FPR)
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_a.false_positive_rate
                      ? `${(results.group_a.false_positive_rate * 100).toFixed(2)}%`
                      : "N/A"}
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    평균 평가 시간
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_a.avg_evaluation_time_ms
                      ? `${results.group_a.avg_evaluation_time_ms.toFixed(2)}ms`
                      : "N/A"}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* 그룹 B */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="bg-green-600 text-white px-6 py-3">
            <h3 className="text-lg font-semibold">그룹 B (신규)</h3>
          </div>
          <div className="p-6">
            <table className="min-w-full">
              <tbody className="divide-y divide-gray-200">
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    총 거래 수
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_b.total_transactions.toLocaleString()}건
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    정탐 (TP)
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_b.true_positives.toLocaleString()}건
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    오탐 (FP)
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_b.false_positives.toLocaleString()}건
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    미탐 (FN)
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_b.false_negatives.toLocaleString()}건
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    정밀도 (Precision)
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_b.precision
                      ? `${(results.group_b.precision * 100).toFixed(2)}%`
                      : "N/A"}
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    재현율 (Recall)
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_b.recall
                      ? `${(results.group_b.recall * 100).toFixed(2)}%`
                      : "N/A"}
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    F1 스코어
                  </td>
                  <td className="py-3 text-sm font-bold text-gray-900 text-right">
                    {results.group_b.f1_score
                      ? `${(results.group_b.f1_score * 100).toFixed(2)}%`
                      : "N/A"}
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    오탐률 (FPR)
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_b.false_positive_rate
                      ? `${(results.group_b.false_positive_rate * 100).toFixed(2)}%`
                      : "N/A"}
                  </td>
                </tr>
                <tr>
                  <td className="py-3 text-sm font-medium text-gray-600">
                    평균 평가 시간
                  </td>
                  <td className="py-3 text-sm text-gray-900 text-right">
                    {results.group_b.avg_evaluation_time_ms
                      ? `${results.group_b.avg_evaluation_time_ms.toFixed(2)}ms`
                      : "N/A"}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ABTestResults;
