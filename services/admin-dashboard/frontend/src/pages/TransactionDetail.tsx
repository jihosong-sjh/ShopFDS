/**
 * 거래 상세 페이지
 *
 * 거래의 상세 정보와 위험 요인을 시각화하여 표시합니다.
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  useTransactionDetail,
  useSubmitReviewDecision,
} from "../hooks/useDashboardData";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { ReviewDecision } from "../types/dashboard";

const TransactionDetail = () => {
  const { transactionId } = useParams<{ transactionId: string }>();
  const navigate = useNavigate();
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [decision, setDecision] = useState<ReviewDecision>("approve");
  const [notes, setNotes] = useState("");

  const { data, isLoading, error, refetch } = useTransactionDetail(transactionId);
  const submitDecision = useSubmitReviewDecision();

  // 검토 결정 제출
  const handleSubmitReview = async () => {
    if (!data?.review_queue?.id) {
      alert("검토 큐 정보를 찾을 수 없습니다.");
      return;
    }

    try {
      await submitDecision.mutateAsync({
        reviewQueueId: data.review_queue.id,
        request: {
          decision,
          notes,
          reviewer_id: "00000000-0000-0000-0000-000000000001", // TODO: 실제 사용자 ID 사용
        },
      });
      alert("검토가 완료되었습니다.");
      setShowReviewModal(false);
      refetch();
    } catch (err) {
      console.error("검토 제출 실패:", err);
      alert("검토 제출 중 오류가 발생했습니다.");
    }
  };

  // 로딩 상태
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">거래 상세 정보를 불러오는 중...</p>
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
            거래 상세 정보를 불러오는 중 오류가 발생했습니다.
          </p>
          <button
            onClick={() => navigate(-1)}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            돌아가기
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { transaction, risk_factors, review_queue, user_history } = data;

  // 위험 요인 차트 데이터
  const riskFactorChartData = risk_factors.map((factor) => ({
    name: factor.factor_type,
    score: factor.factor_score,
  }));

  // 위험도에 따른 색상
  const getRiskColor = (score: number) => {
    if (score >= 30) return "#ef4444"; // red-500
    if (score >= 15) return "#f59e0b"; // amber-500
    return "#10b981"; // green-500
  };

  // 위험도 레이블
  const getRiskLevelLabel = (level: string) => {
    switch (level) {
      case "high":
        return "높음";
      case "medium":
        return "중간";
      case "low":
        return "낮음";
      default:
        return level;
    }
  };

  // 평가 상태 레이블
  const getEvaluationStatusLabel = (status: string) => {
    switch (status) {
      case "approved":
        return "승인됨";
      case "blocked":
        return "차단됨";
      case "manual_review":
        return "수동 검토";
      case "pending":
        return "대기중";
      case "additional_auth_required":
        return "추가 인증 필요";
      default:
        return status;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* 헤더 */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate(-1)}
            className="text-blue-600 hover:text-blue-800 mb-2 flex items-center"
          >
            <svg
              className="w-5 h-5 mr-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            돌아가기
          </button>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            거래 상세 정보
          </h1>
          <p className="text-gray-600">거래 ID: {transaction.id}</p>
        </div>
        {review_queue && review_queue.status !== "completed" && (
          <button
            onClick={() => setShowReviewModal(true)}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 font-medium"
          >
            검토 결정하기
          </button>
        )}
      </div>

      {/* 거래 기본 정보 */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          거래 기본 정보
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-gray-500 mb-1">주문 ID</p>
            <p className="text-base font-medium text-gray-900">
              {transaction.order_id}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">사용자 ID</p>
            <p className="text-base font-medium text-gray-900">
              {transaction.user_id}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">거래 금액</p>
            <p className="text-base font-medium text-gray-900">
              ₩{transaction.amount.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">위험 점수</p>
            <p className="text-base font-medium text-gray-900">
              {transaction.risk_score}점
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">위험 수준</p>
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                transaction.risk_level === "high"
                  ? "bg-red-100 text-red-800"
                  : transaction.risk_level === "medium"
                  ? "bg-amber-100 text-amber-800"
                  : "bg-green-100 text-green-800"
              }`}
            >
              {getRiskLevelLabel(transaction.risk_level)}
            </span>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">평가 상태</p>
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                transaction.evaluation_status === "blocked"
                  ? "bg-red-100 text-red-800"
                  : transaction.evaluation_status === "approved"
                  ? "bg-green-100 text-green-800"
                  : "bg-amber-100 text-amber-800"
              }`}
            >
              {getEvaluationStatusLabel(transaction.evaluation_status)}
            </span>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">IP 주소</p>
            <p className="text-base font-medium text-gray-900">
              {transaction.ip_address}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">디바이스 타입</p>
            <p className="text-base font-medium text-gray-900">
              {transaction.device_type}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">위치 정보</p>
            <p className="text-base font-medium text-gray-900">
              {transaction.geolocation || "N/A"}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">평가 시간</p>
            <p className="text-base font-medium text-gray-900">
              {transaction.evaluation_time_ms}ms
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">거래 시간</p>
            <p className="text-base font-medium text-gray-900">
              {new Date(transaction.created_at).toLocaleString("ko-KR")}
            </p>
          </div>
          {transaction.evaluated_at && (
            <div>
              <p className="text-sm text-gray-500 mb-1">평가 완료 시간</p>
              <p className="text-base font-medium text-gray-900">
                {new Date(transaction.evaluated_at).toLocaleString("ko-KR")}
              </p>
            </div>
          )}
        </div>
        {transaction.user_agent && (
          <div className="mt-4">
            <p className="text-sm text-gray-500 mb-1">User Agent</p>
            <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded">
              {transaction.user_agent}
            </p>
          </div>
        )}
      </div>

      {/* 위험 요인 시각화 */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          위험 요인 분석
        </h2>
        {risk_factors.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            위험 요인이 없습니다.
          </p>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={riskFactorChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="name"
                  angle={-45}
                  textAnchor="end"
                  height={100}
                />
                <YAxis />
                <Tooltip />
                <Bar dataKey="score" name="위험 점수">
                  {riskFactorChartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={getRiskColor(entry.score)}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>

            <div className="mt-6 space-y-4">
              {risk_factors.map((factor) => (
                <div
                  key={factor.id}
                  className="border border-gray-200 rounded-lg p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-base font-medium text-gray-900">
                      {factor.factor_type}
                    </h3>
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        factor.factor_score >= 30
                          ? "bg-red-100 text-red-800"
                          : factor.factor_score >= 15
                          ? "bg-amber-100 text-amber-800"
                          : "bg-green-100 text-green-800"
                      }`}
                    >
                      {factor.factor_score}점
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">
                    {factor.description}
                  </p>
                  {factor.metadata && Object.keys(factor.metadata).length > 0 && (
                    <div className="bg-gray-50 p-3 rounded">
                      <p className="text-xs text-gray-500 mb-1">추가 정보:</p>
                      <pre className="text-xs text-gray-700 overflow-x-auto">
                        {JSON.stringify(factor.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* 사용자 거래 이력 */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          사용자 거래 이력
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="text-center">
            <p className="text-3xl font-bold text-gray-900">
              {user_history.total_transactions}
            </p>
            <p className="text-sm text-gray-600 mt-1">총 거래 수</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-red-600">
              {user_history.high_risk_count}
            </p>
            <p className="text-sm text-gray-600 mt-1">고위험 거래</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-red-600">
              {user_history.blocked_count}
            </p>
            <p className="text-sm text-gray-600 mt-1">차단된 거래</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-amber-600">
              {user_history.avg_risk_score}
            </p>
            <p className="text-sm text-gray-600 mt-1">평균 위험 점수</p>
          </div>
        </div>
      </div>

      {/* 검토 큐 정보 */}
      {review_queue && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            검토 정보
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <p className="text-sm text-gray-500 mb-1">검토 상태</p>
              <span
                className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                  review_queue.status === "pending"
                    ? "bg-yellow-100 text-yellow-800"
                    : review_queue.status === "in_review"
                    ? "bg-blue-100 text-blue-800"
                    : "bg-green-100 text-green-800"
                }`}
              >
                {review_queue.status === "pending" && "대기중"}
                {review_queue.status === "in_review" && "검토중"}
                {review_queue.status === "completed" && "완료"}
              </span>
            </div>
            {review_queue.decision && (
              <div>
                <p className="text-sm text-gray-500 mb-1">검토 결정</p>
                <span
                  className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                    review_queue.decision === "approve"
                      ? "bg-green-100 text-green-800"
                      : review_queue.decision === "block"
                      ? "bg-red-100 text-red-800"
                      : "bg-amber-100 text-amber-800"
                  }`}
                >
                  {review_queue.decision === "approve" && "승인"}
                  {review_queue.decision === "block" && "차단"}
                  {review_queue.decision === "escalate" && "에스컬레이션"}
                </span>
              </div>
            )}
            <div>
              <p className="text-sm text-gray-500 mb-1">추가 시간</p>
              <p className="text-base font-medium text-gray-900">
                {new Date(review_queue.added_at).toLocaleString("ko-KR")}
              </p>
            </div>
            {review_queue.reviewed_at && (
              <div>
                <p className="text-sm text-gray-500 mb-1">검토 완료 시간</p>
                <p className="text-base font-medium text-gray-900">
                  {new Date(review_queue.reviewed_at).toLocaleString("ko-KR")}
                </p>
              </div>
            )}
          </div>
          {review_queue.review_notes && (
            <div className="mt-4">
              <p className="text-sm text-gray-500 mb-1">검토 메모</p>
              <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded">
                {review_queue.review_notes}
              </p>
            </div>
          )}
        </div>
      )}

      {/* 검토 결정 모달 */}
      {showReviewModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              검토 결정
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  결정
                </label>
                <select
                  value={decision}
                  onChange={(e) => setDecision(e.target.value as ReviewDecision)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="approve">승인 (오탐)</option>
                  <option value="block">차단 유지 (정탐)</option>
                  <option value="escalate">에스컬레이션 (추가 조사 필요)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  검토 메모
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={4}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="검토 사유를 입력하세요..."
                />
              </div>
            </div>
            <div className="mt-6 flex gap-3">
              <button
                onClick={handleSubmitReview}
                disabled={submitDecision.isPending}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitDecision.isPending ? "제출 중..." : "제출"}
              </button>
              <button
                onClick={() => setShowReviewModal(false)}
                disabled={submitDecision.isPending}
                className="flex-1 bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                취소
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TransactionDetail;
