/**
 * 모델 성능 비교 대시보드
 *
 * 기능:
 * - 두 모델 선택 및 성능 지표 비교
 * - 정확도, 정밀도, 재현율, F1 스코어 시각화 (차트)
 * - 학습 기간, 배포 상태 비교
 * - 권장 사항 표시
 * - 프로덕션 모델과 다른 모델 비교 기능
 */

import React, { useState, useEffect } from "react";
import { mlModelsApi } from "../services/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";

interface ModelMetrics {
  accuracy?: number;
  precision?: number;
  recall?: number;
  f1_score?: number;
}

interface MLModel {
  id: string;
  name: string;
  version: string;
  model_type: string;
  deployment_status: string;
  trained_at: string;
  deployed_at?: string;
  training_period: string;
  metrics: ModelMetrics;
}

interface ComparisonResult {
  model_1: {
    id: string;
    name: string;
    version: string;
    model_type: string;
    deployment_status: string;
    metrics: ModelMetrics;
    trained_at: string;
    training_period: string;
  };
  model_2: {
    id: string;
    name: string;
    version: string;
    model_type: string;
    deployment_status: string;
    metrics: ModelMetrics;
    trained_at: string;
    training_period: string;
  };
  comparison: {
    accuracy_diff?: number;
    precision_diff?: number;
    recall_diff?: number;
    f1_score_diff?: number;
  };
  recommendation: string;
}

const ModelComparison: React.FC = () => {
  const [models, setModels] = useState<MLModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedModel1, setSelectedModel1] = useState<string>("");
  const [selectedModel2, setSelectedModel2] = useState<string>("");
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(
    null
  );

  const [productionModel, setProductionModel] = useState<MLModel | null>(null);

  // 모델 목록 조회
  const fetchModels = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await mlModelsApi.getList({ limit: 100 });
      setModels(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "모델 목록 조회 실패");
      console.error("모델 목록 조회 오류:", err);
    } finally {
      setLoading(false);
    }
  };

  // 현재 프로덕션 모델 조회
  const fetchProductionModel = async () => {
    try {
      const data = await mlModelsApi.getCurrentProduction();
      if (data) {
        setProductionModel(data);
      }
    } catch (err: any) {
      console.error("프로덕션 모델 조회 오류:", err);
    }
  };

  // 초기 로드
  useEffect(() => {
    fetchModels();
    fetchProductionModel();
  }, []);

  // 모델 비교 실행
  const handleCompare = async () => {
    if (!selectedModel1 || !selectedModel2) {
      alert("두 개의 모델을 선택하세요");
      return;
    }

    if (selectedModel1 === selectedModel2) {
      alert("다른 모델을 선택하세요");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await mlModelsApi.compare(selectedModel1, selectedModel2);
      setComparisonResult(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || "모델 비교 실패");
      console.error("모델 비교 오류:", err);
    } finally {
      setLoading(false);
    }
  };

  // 프로덕션 모델과 비교
  const handleCompareWithProduction = (modelId: string) => {
    if (!productionModel) {
      alert("프로덕션 모델이 없습니다");
      return;
    }

    setSelectedModel1(productionModel.id);
    setSelectedModel2(modelId);

    // 비교 실행
    setTimeout(() => {
      mlModelsApi
        .compare(productionModel.id, modelId)
        .then((result) => {
          setComparisonResult(result);
        })
        .catch((err) => {
          setError(err.response?.data?.detail || "모델 비교 실패");
          console.error("모델 비교 오류:", err);
        });
    }, 100);
  };

  // 차트 데이터 준비
  const getBarChartData = () => {
    if (!comparisonResult) return [];

    const { model_1, model_2 } = comparisonResult;

    return [
      {
        metric: "정확도",
        [model_1.name]: (model_1.metrics.accuracy || 0) * 100,
        [model_2.name]: (model_2.metrics.accuracy || 0) * 100,
      },
      {
        metric: "정밀도",
        [model_1.name]: (model_1.metrics.precision || 0) * 100,
        [model_2.name]: (model_2.metrics.precision || 0) * 100,
      },
      {
        metric: "재현율",
        [model_1.name]: (model_1.metrics.recall || 0) * 100,
        [model_2.name]: (model_2.metrics.recall || 0) * 100,
      },
      {
        metric: "F1 스코어",
        [model_1.name]: (model_1.metrics.f1_score || 0) * 100,
        [model_2.name]: (model_2.metrics.f1_score || 0) * 100,
      },
    ];
  };

  // 레이더 차트 데이터 준비
  const getRadarChartData = () => {
    if (!comparisonResult) return [];

    const { model_1, model_2 } = comparisonResult;

    return [
      {
        metric: "정확도",
        [model_1.name]: (model_1.metrics.accuracy || 0) * 100,
        [model_2.name]: (model_2.metrics.accuracy || 0) * 100,
      },
      {
        metric: "정밀도",
        [model_1.name]: (model_1.metrics.precision || 0) * 100,
        [model_2.name]: (model_2.metrics.precision || 0) * 100,
      },
      {
        metric: "재현율",
        [model_1.name]: (model_1.metrics.recall || 0) * 100,
        [model_2.name]: (model_2.metrics.recall || 0) * 100,
      },
      {
        metric: "F1",
        [model_1.name]: (model_1.metrics.f1_score || 0) * 100,
        [model_2.name]: (model_2.metrics.f1_score || 0) * 100,
      },
    ];
  };

  // 차이값 포맷팅
  const formatDiff = (diff?: number) => {
    if (diff === undefined || diff === null) return "-";
    const sign = diff > 0 ? "+" : "";
    return `${sign}${(diff * 100).toFixed(2)}%`;
  };

  // 차이값 색상
  const getDiffColor = (diff?: number) => {
    if (diff === undefined || diff === null) return "text-gray-500";
    if (diff > 0) return "text-green-600";
    if (diff < 0) return "text-red-600";
    return "text-gray-500";
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 헤더 */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">모델 성능 비교</h1>
          <p className="text-gray-600 mt-2">
            두 모델의 성능 지표를 비교하여 최적의 모델을 선택하세요
          </p>
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {/* 프로덕션 모델 정보 */}
        {productionModel && (
          <div className="mb-6 p-4 bg-green-50 border border-green-300 rounded-lg">
            <h3 className="text-lg font-semibold mb-2">현재 프로덕션 모델</h3>
            <p className="text-gray-700">
              {productionModel.name} (v{productionModel.version}) - F1 스코어:{" "}
              {((productionModel.metrics.f1_score || 0) * 100).toFixed(2)}%
            </p>
          </div>
        )}

        {/* 모델 선택 */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">모델 선택</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                모델 1
              </label>
              <select
                value={selectedModel1}
                onChange={(e) => setSelectedModel1(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              >
                <option value="">선택하세요</option>
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} (v{model.version}) - {model.deployment_status}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                모델 2
              </label>
              <select
                value={selectedModel2}
                onChange={(e) => setSelectedModel2(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              >
                <option value="">선택하세요</option>
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} (v{model.version}) - {model.deployment_status}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={handleCompare}
                disabled={loading || !selectedModel1 || !selectedModel2}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition"
              >
                비교하기
              </button>
            </div>
          </div>
        </div>

        {/* 비교 결과 */}
        {comparisonResult && (
          <div className="space-y-6">
            {/* 권장사항 */}
            <div className="bg-blue-50 border border-blue-300 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-2">권장사항</h3>
              <p className="text-gray-700">{comparisonResult.recommendation}</p>
            </div>

            {/* 기본 정보 비교 */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold mb-4">기본 정보</h2>
              <div className="grid grid-cols-2 gap-6">
                {/* 모델 1 */}
                <div>
                  <h3 className="text-lg font-semibold mb-3 text-blue-600">
                    {comparisonResult.model_1.name}
                  </h3>
                  <dl className="space-y-2">
                    <div>
                      <dt className="text-sm text-gray-600">버전</dt>
                      <dd className="text-sm font-medium">
                        {comparisonResult.model_1.version}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-gray-600">모델 유형</dt>
                      <dd className="text-sm font-medium">
                        {comparisonResult.model_1.model_type}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-gray-600">배포 상태</dt>
                      <dd className="text-sm font-medium">
                        {comparisonResult.model_1.deployment_status}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-gray-600">학습일</dt>
                      <dd className="text-sm font-medium">
                        {new Date(comparisonResult.model_1.trained_at).toLocaleString(
                          "ko-KR"
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-gray-600">학습 기간</dt>
                      <dd className="text-sm font-medium">
                        {comparisonResult.model_1.training_period}
                      </dd>
                    </div>
                  </dl>
                </div>

                {/* 모델 2 */}
                <div>
                  <h3 className="text-lg font-semibold mb-3 text-green-600">
                    {comparisonResult.model_2.name}
                  </h3>
                  <dl className="space-y-2">
                    <div>
                      <dt className="text-sm text-gray-600">버전</dt>
                      <dd className="text-sm font-medium">
                        {comparisonResult.model_2.version}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-gray-600">모델 유형</dt>
                      <dd className="text-sm font-medium">
                        {comparisonResult.model_2.model_type}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-gray-600">배포 상태</dt>
                      <dd className="text-sm font-medium">
                        {comparisonResult.model_2.deployment_status}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-gray-600">학습일</dt>
                      <dd className="text-sm font-medium">
                        {new Date(comparisonResult.model_2.trained_at).toLocaleString(
                          "ko-KR"
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-gray-600">학습 기간</dt>
                      <dd className="text-sm font-medium">
                        {comparisonResult.model_2.training_period}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>
            </div>

            {/* 성능 지표 테이블 */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold mb-4">성능 지표</h2>
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      지표
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      {comparisonResult.model_1.name}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      {comparisonResult.model_2.name}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      차이
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      정확도 (Accuracy)
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {((comparisonResult.model_1.metrics.accuracy || 0) * 100).toFixed(
                        2
                      )}
                      %
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {((comparisonResult.model_2.metrics.accuracy || 0) * 100).toFixed(
                        2
                      )}
                      %
                    </td>
                    <td
                      className={`px-6 py-4 whitespace-nowrap text-sm font-semibold ${getDiffColor(
                        comparisonResult.comparison.accuracy_diff
                      )}`}
                    >
                      {formatDiff(comparisonResult.comparison.accuracy_diff)}
                    </td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      정밀도 (Precision)
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {(
                        (comparisonResult.model_1.metrics.precision || 0) * 100
                      ).toFixed(2)}
                      %
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {(
                        (comparisonResult.model_2.metrics.precision || 0) * 100
                      ).toFixed(2)}
                      %
                    </td>
                    <td
                      className={`px-6 py-4 whitespace-nowrap text-sm font-semibold ${getDiffColor(
                        comparisonResult.comparison.precision_diff
                      )}`}
                    >
                      {formatDiff(comparisonResult.comparison.precision_diff)}
                    </td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      재현율 (Recall)
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {((comparisonResult.model_1.metrics.recall || 0) * 100).toFixed(
                        2
                      )}
                      %
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {((comparisonResult.model_2.metrics.recall || 0) * 100).toFixed(
                        2
                      )}
                      %
                    </td>
                    <td
                      className={`px-6 py-4 whitespace-nowrap text-sm font-semibold ${getDiffColor(
                        comparisonResult.comparison.recall_diff
                      )}`}
                    >
                      {formatDiff(comparisonResult.comparison.recall_diff)}
                    </td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      F1 스코어
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {(
                        (comparisonResult.model_1.metrics.f1_score || 0) * 100
                      ).toFixed(2)}
                      %
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {(
                        (comparisonResult.model_2.metrics.f1_score || 0) * 100
                      ).toFixed(2)}
                      %
                    </td>
                    <td
                      className={`px-6 py-4 whitespace-nowrap text-sm font-semibold ${getDiffColor(
                        comparisonResult.comparison.f1_score_diff
                      )}`}
                    >
                      {formatDiff(comparisonResult.comparison.f1_score_diff)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* 막대 차트 */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold mb-4">성능 지표 비교 (막대 차트)</h2>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={getBarChartData()}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="metric" />
                  <YAxis domain={[0, 100]} label={{ value: "%", angle: -90 }} />
                  <Tooltip />
                  <Legend />
                  <Bar
                    dataKey={comparisonResult.model_1.name}
                    fill="#3b82f6"
                    name={comparisonResult.model_1.name}
                  />
                  <Bar
                    dataKey={comparisonResult.model_2.name}
                    fill="#10b981"
                    name={comparisonResult.model_2.name}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* 레이더 차트 */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold mb-4">성능 지표 비교 (레이더 차트)</h2>
              <ResponsiveContainer width="100%" height={400}>
                <RadarChart data={getRadarChartData()}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="metric" />
                  <PolarRadiusAxis domain={[0, 100]} />
                  <Radar
                    name={comparisonResult.model_1.name}
                    dataKey={comparisonResult.model_1.name}
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.6}
                  />
                  <Radar
                    name={comparisonResult.model_2.name}
                    dataKey={comparisonResult.model_2.name}
                    stroke="#10b981"
                    fill="#10b981"
                    fillOpacity={0.6}
                  />
                  <Legend />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* 모델이 없을 때 */}
        {!loading && models.length === 0 && (
          <div className="bg-white rounded-lg shadow-md p-8 text-center text-gray-500">
            모델이 없습니다. 먼저 모델을 학습하세요.
          </div>
        )}

        {/* 빠른 비교: 프로덕션 모델과 비교 */}
        {productionModel && models.length > 1 && !comparisonResult && (
          <div className="bg-white rounded-lg shadow-md p-6 mt-6">
            <h2 className="text-xl font-bold mb-4">
              빠른 비교: 프로덕션 모델과 비교하기
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {models
                .filter((model) => model.id !== productionModel.id)
                .map((model) => (
                  <button
                    key={model.id}
                    onClick={() => handleCompareWithProduction(model.id)}
                    className="p-4 border border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition text-left"
                  >
                    <h3 className="font-semibold text-sm mb-1">{model.name}</h3>
                    <p className="text-xs text-gray-600 mb-2">v{model.version}</p>
                    <p className="text-xs text-gray-500">
                      F1: {((model.metrics.f1_score || 0) * 100).toFixed(2)}%
                    </p>
                  </button>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ModelComparison;
