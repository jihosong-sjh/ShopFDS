/**
 * XAI Dashboard Page
 *
 * T084: 설명 가능한 AI (XAI) 대시보드
 *
 * SHAP/LIME 분석 결과를 시각화하여 ML 모델의 예측 근거를 설명합니다.
 *
 * 주요 기능:
 * 1. 거래 ID로 XAI 분석 결과 조회
 * 2. SHAP Waterfall Chart (Feature 기여도)
 * 3. Top 5 Risk Factors (상위 위험 요인)
 * 4. LIME Local Explanation
 * 5. 검증 결과 표시
 *
 * 목표:
 * - 3클릭 이내로 거래 차단 사유 확인 가능
 * - SHAP 분석 95%가 5초 이내 완료
 */

import React, { useState } from "react";
import { WaterfallChart, SHAPValue } from "../components/WaterfallChart";
import { TopRiskFactors, RiskFactor } from "../components/TopRiskFactors";

// FDS API 기본 URL
const FDS_API_BASE_URL = import.meta.env.VITE_FDS_API_URL || "http://localhost:8001";

interface LIMEExplanation {
  prediction: number;
  local_prediction: number;
  score: number;
  intercept: number;
  explanations: Array<{
    feature: string;
    weight: number;
  }>;
}

interface ValidationResult {
  valid: boolean;
  mismatches: Array<{
    feature: string;
    shap_value?: number;
    original_value?: number;
    error?: string;
  }>;
  total_features: number;
}

interface XAIResponse {
  transaction_id: string;
  shap_values: SHAPValue[] | null;
  lime_explanation: LIMEExplanation | null;
  top_risk_factors: RiskFactor[];
  explanation_time_ms: number;
  generated_at: string;
  validation?: ValidationResult;
}

export const XAIDashboard: React.FC = () => {
  const [transactionId, setTransactionId] = useState<string>("");
  const [xaiData, setXaiData] = useState<XAIResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * XAI 분석 결과 조회
   */
  const handleFetchXAI = async () => {
    if (!transactionId.trim()) {
      setError("Please enter a transaction ID");
      return;
    }

    setLoading(true);
    setError(null);
    setXaiData(null);

    try {
      const response = await fetch(
        `${FDS_API_BASE_URL}/v1/fds/xai/${transactionId.trim()}`
      );

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("XAI explanation not found for this transaction");
        }
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const data: XAIResponse = await response.json();
      setXaiData(data);
    } catch (err) {
      console.error("Failed to fetch XAI data:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch XAI explanation");
    } finally {
      setLoading(false);
    }
  };

  /**
   * Enter 키 입력 핸들러
   */
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleFetchXAI();
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          XAI Dashboard - Explainable AI
        </h1>
        <p className="mt-2 text-gray-600">
          Understand ML model predictions with SHAP and LIME explanations
        </p>
      </div>

      {/* Search Section */}
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label
              htmlFor="transactionId"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Transaction ID
            </label>
            <input
              id="transactionId"
              type="text"
              value={transactionId}
              onChange={(e) => setTransactionId(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter transaction ID (UUID)"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={handleFetchXAI}
            disabled={loading}
            className={`px-6 py-2 rounded-md font-medium text-white transition-colors ${
              loading
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            {loading ? "Loading..." : "Fetch Explanation"}
          </button>
        </div>

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">[ERROR] {error}</p>
          </div>
        )}
      </div>

      {/* XAI Results */}
      {xaiData && (
        <div className="space-y-8">
          {/* Metadata */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Analysis Metadata
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-500">Transaction ID</p>
                <p className="font-mono text-sm text-gray-900 break-all">
                  {xaiData.transaction_id}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Analysis Time</p>
                <p
                  className={`font-semibold ${
                    xaiData.explanation_time_ms < 5000
                      ? "text-green-600"
                      : "text-red-600"
                  }`}
                >
                  {xaiData.explanation_time_ms}ms
                  {xaiData.explanation_time_ms < 5000 ? " [OK]" : " [TIMEOUT]"}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Generated At</p>
                <p className="text-sm text-gray-900">
                  {new Date(xaiData.generated_at).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Validation Status</p>
                <p
                  className={`font-semibold ${
                    xaiData.validation?.valid ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {xaiData.validation?.valid ? "[PASS] Valid" : "[FAIL] Invalid"}
                </p>
              </div>
            </div>
          </div>

          {/* Top Risk Factors */}
          {xaiData.top_risk_factors && xaiData.top_risk_factors.length > 0 && (
            <TopRiskFactors
              riskFactors={xaiData.top_risk_factors}
              showChart={true}
              showTable={true}
            />
          )}

          {/* SHAP Waterfall Chart */}
          {xaiData.shap_values && xaiData.shap_values.length > 0 && (
            <WaterfallChart
              shapValues={xaiData.shap_values}
              height={500}
            />
          )}

          {/* LIME Explanation */}
          {xaiData.lime_explanation && (
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                LIME Local Explanation
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="p-4 bg-gray-50 rounded">
                  <p className="text-sm text-gray-500">Global Prediction</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {(xaiData.lime_explanation.prediction * 100).toFixed(2)}%
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded">
                  <p className="text-sm text-gray-500">Local Prediction</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {(xaiData.lime_explanation.local_prediction * 100).toFixed(2)}%
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded">
                  <p className="text-sm text-gray-500">R² Score</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {xaiData.lime_explanation.score.toFixed(4)}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded">
                  <p className="text-sm text-gray-500">Intercept</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {xaiData.lime_explanation.intercept.toFixed(4)}
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Feature
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Weight
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Impact
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {xaiData.lime_explanation.explanations.map((exp, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {exp.feature}
                        </td>
                        <td
                          className={`px-4 py-3 text-sm font-semibold ${
                            exp.weight > 0 ? "text-red-600" : "text-green-600"
                          }`}
                        >
                          {exp.weight > 0 ? "+" : ""}
                          {exp.weight.toFixed(4)}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-1 text-xs font-medium rounded-full ${
                              exp.weight > 0
                                ? "bg-red-100 text-red-800"
                                : "bg-green-100 text-green-800"
                            }`}
                          >
                            {exp.weight > 0 ? "Increases Risk" : "Decreases Risk"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Validation Details */}
          {xaiData.validation && !xaiData.validation.valid && (
            <div className="bg-red-50 border border-red-200 p-6 rounded-lg shadow">
              <h2 className="text-xl font-semibold text-red-900 mb-4">
                [WARNING] Validation Issues Detected
              </h2>
              <p className="text-sm text-red-700 mb-4">
                SHAP values do not match original feature values. This may indicate
                a data mismatch.
              </p>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-red-200">
                  <thead className="bg-red-100">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-red-700 uppercase">
                        Feature
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-red-700 uppercase">
                        SHAP Value
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-red-700 uppercase">
                        Original Value
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-red-700 uppercase">
                        Error
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-red-100">
                    {xaiData.validation.mismatches.map((mismatch, idx) => (
                      <tr key={idx}>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {mismatch.feature}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700">
                          {mismatch.shap_value?.toFixed(4) || "N/A"}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700">
                          {mismatch.original_value?.toFixed(4) || "N/A"}
                        </td>
                        <td className="px-4 py-3 text-sm text-red-600">
                          {mismatch.error || "Value mismatch"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* No Data Message */}
          {!xaiData.shap_values &&
            !xaiData.lime_explanation &&
            xaiData.top_risk_factors.length === 0 && (
              <div className="bg-yellow-50 border border-yellow-200 p-6 rounded-lg text-center">
                <p className="text-yellow-700">
                  No XAI analysis data available for this transaction.
                </p>
                <p className="text-sm text-yellow-600 mt-2">
                  The analysis may have timed out or failed. Please try again later.
                </p>
              </div>
            )}
        </div>
      )}

      {/* Empty State */}
      {!xaiData && !loading && !error && (
        <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">
            No XAI data loaded
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            Enter a transaction ID above to view its XAI explanation
          </p>
        </div>
      )}
    </div>
  );
};

export default XAIDashboard;
