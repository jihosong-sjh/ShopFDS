/**
 * ML 모델 관리 페이지
 *
 * 기능:
 * - 모델 목록 조회 및 필터링 (배포 상태, 모델 유형)
 * - 모델 상세 정보 조회 (성능 지표, 학습 기간)
 * - 모델 학습 트리거 (학습 파라미터 설정)
 * - 모델 배포 (스테이징/프로덕션)
 * - 카나리 배포 관리 (시작/조정/완료/중단)
 * - 모델 롤백 (일반/긴급)
 * - 학습 상태 실시간 추적
 */

import React, { useState, useEffect } from "react";
import { mlModelsApi } from "../services/api";

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

interface TrainingStatus {
  model_id: string;
  status: string;
  progress_percentage: number;
  current_step: string;
  elapsed_time_seconds: number;
  estimated_remaining_seconds?: number;
  error_message?: string;
}

interface CanaryStatus {
  is_active: boolean;
  canary_model_id?: string;
  production_model_id?: string;
  traffic_percentage?: number;
  canary_metrics?: ModelMetrics;
  production_metrics?: ModelMetrics;
  recommendation?: string;
  started_at?: string;
}

const MLModelManagement: React.FC = () => {
  const [models, setModels] = useState<MLModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 필터 상태
  const [deploymentStatusFilter, setDeploymentStatusFilter] = useState<string>("");
  const [modelTypeFilter, setModelTypeFilter] = useState<string>("");

  // 모달 상태
  const [showTrainModal, setShowTrainModal] = useState(false);
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [showCanaryModal, setShowCanaryModal] = useState(false);
  const [showRollbackModal, setShowRollbackModal] = useState(false);
  const [selectedModel, setSelectedModel] = useState<MLModel | null>(null);

  // 학습 상태
  const [trainingStatus, setTrainingStatus] = useState<TrainingStatus | null>(null);
  const [trainingModelId, setTrainingModelId] = useState<string | null>(null);

  // 카나리 배포 상태
  const [canaryStatus, setCanaryStatus] = useState<CanaryStatus | null>(null);

  // 학습 폼 상태
  const [trainForm, setTrainForm] = useState({
    model_type: "isolation_forest",
    training_period_days: 30,
    auto_deploy_to_staging: false,
  });

  // 배포 폼 상태
  const [deployForm, setDeployForm] = useState<{
    target_environment: "staging" | "production";
  }>({
    target_environment: "staging",
  });

  // 카나리 배포 폼 상태
  const [canaryForm, setCanaryForm] = useState({
    initial_traffic_percentage: 10,
    success_threshold: 0.95,
    monitoring_window_minutes: 60,
  });

  // 롤백 폼 상태
  const [rollbackForm, setRollbackForm] = useState({
    reason: "",
    emergency: false,
  });

  // 모델 목록 조회
  const fetchModels = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await mlModelsApi.getList({
        deployment_status: deploymentStatusFilter || undefined,
        model_type: modelTypeFilter || undefined,
        limit: 50,
      });
      setModels(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "모델 목록 조회 실패");
      console.error("모델 목록 조회 오류:", err);
    } finally {
      setLoading(false);
    }
  };

  // 카나리 배포 상태 조회
  const fetchCanaryStatus = async () => {
    try {
      const data = await mlModelsApi.getCanaryStatus();
      setCanaryStatus(data);
    } catch (err: any) {
      console.error("카나리 상태 조회 오류:", err);
    }
  };

  // 학습 상태 조회 (폴링)
  useEffect(() => {
    if (trainingModelId) {
      const interval = setInterval(async () => {
        try {
          const status = await mlModelsApi.getTrainingStatus(trainingModelId);
          setTrainingStatus(status);

          // 학습 완료 시 폴링 중단
          if (status.status === "completed" || status.status === "failed") {
            setTrainingModelId(null);
            fetchModels(); // 모델 목록 새로고침
          }
        } catch (err: any) {
          console.error("학습 상태 조회 오류:", err);
        }
      }, 3000); // 3초마다 조회

      return () => clearInterval(interval);
    }
  }, [trainingModelId]);

  // 초기 로드 및 필터 변경 시 모델 목록 조회
  useEffect(() => {
    fetchModels();
    fetchCanaryStatus();
  }, [deploymentStatusFilter, modelTypeFilter]);

  // 모델 학습 트리거
  const handleTrain = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await mlModelsApi.train(trainForm);
      setTrainingModelId(response.model_id);
      setShowTrainModal(false);
      alert(`모델 학습이 시작되었습니다: ${response.model_name}`);
      fetchModels();
    } catch (err: any) {
      setError(err.response?.data?.detail || "모델 학습 트리거 실패");
      console.error("모델 학습 오류:", err);
    } finally {
      setLoading(false);
    }
  };

  // 모델 배포
  const handleDeploy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedModel) return;

    setLoading(true);
    setError(null);

    try {
      const response = await mlModelsApi.deploy({
        model_id: selectedModel.id,
        target_environment: deployForm.target_environment,
      });
      setShowDeployModal(false);
      alert(`모델이 ${deployForm.target_environment}에 배포되었습니다`);
      fetchModels();
    } catch (err: any) {
      setError(err.response?.data?.detail || "모델 배포 실패");
      console.error("모델 배포 오류:", err);
    } finally {
      setLoading(false);
    }
  };

  // 카나리 배포 시작
  const handleStartCanary = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedModel) return;

    setLoading(true);
    setError(null);

    try {
      await mlModelsApi.startCanary({
        model_id: selectedModel.id,
        ...canaryForm,
      });
      setShowCanaryModal(false);
      alert("카나리 배포가 시작되었습니다");
      fetchCanaryStatus();
      fetchModels();
    } catch (err: any) {
      setError(err.response?.data?.detail || "카나리 배포 시작 실패");
      console.error("카나리 배포 오류:", err);
    } finally {
      setLoading(false);
    }
  };

  // 카나리 배포 트래픽 조정
  const handleAdjustCanaryTraffic = async (newPercentage: number) => {
    setLoading(true);
    setError(null);

    try {
      await mlModelsApi.adjustCanaryTraffic(newPercentage);
      alert(`카나리 트래픽이 ${newPercentage}%로 조정되었습니다`);
      fetchCanaryStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || "트래픽 조정 실패");
      console.error("트래픽 조정 오류:", err);
    } finally {
      setLoading(false);
    }
  };

  // 카나리 배포 완료
  const handleCompleteCanary = async () => {
    if (!confirm("카나리 모델을 프로덕션으로 승격하시겠습니까?")) return;

    setLoading(true);
    setError(null);

    try {
      await mlModelsApi.completeCanary();
      alert("카나리 배포가 완료되었습니다");
      fetchCanaryStatus();
      fetchModels();
    } catch (err: any) {
      setError(err.response?.data?.detail || "카나리 배포 완료 실패");
      console.error("카나리 배포 완료 오류:", err);
    } finally {
      setLoading(false);
    }
  };

  // 카나리 배포 중단
  const handleAbortCanary = async () => {
    const reason = prompt("카나리 배포 중단 사유를 입력하세요:");
    if (!reason) return;

    setLoading(true);
    setError(null);

    try {
      await mlModelsApi.abortCanary(reason);
      alert("카나리 배포가 중단되었습니다");
      fetchCanaryStatus();
      fetchModels();
    } catch (err: any) {
      setError(err.response?.data?.detail || "카나리 배포 중단 실패");
      console.error("카나리 배포 중단 오류:", err);
    } finally {
      setLoading(false);
    }
  };

  // 모델 롤백
  const handleRollback = async (e: React.FormEvent) => {
    e.preventDefault();

    setLoading(true);
    setError(null);

    try {
      if (rollbackForm.emergency) {
        await mlModelsApi.emergencyRollback({
          reason: rollbackForm.reason,
          model_type: modelTypeFilter || undefined,
        });
      } else {
        await mlModelsApi.rollback({
          reason: rollbackForm.reason,
          target_model_id: selectedModel?.id,
          model_type: modelTypeFilter || undefined,
        });
      }
      setShowRollbackModal(false);
      alert("모델 롤백이 완료되었습니다");
      fetchModels();
    } catch (err: any) {
      setError(err.response?.data?.detail || "모델 롤백 실패");
      console.error("모델 롤백 오류:", err);
    } finally {
      setLoading(false);
    }
  };

  // 배포 상태별 배지 색상
  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case "production":
        return "bg-green-100 text-green-800";
      case "staging":
        return "bg-blue-100 text-blue-800";
      case "canary":
        return "bg-yellow-100 text-yellow-800";
      case "retired":
        return "bg-gray-100 text-gray-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  // 배포 상태 한글 변환
  const getStatusLabel = (status: string) => {
    const labels: { [key: string]: string } = {
      development: "개발",
      staging: "스테이징",
      production: "프로덕션",
      canary: "카나리",
      retired: "은퇴",
    };
    return labels[status] || status;
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 헤더 */}
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">ML 모델 관리</h1>
          <div className="flex gap-2">
            <button
              onClick={() => setShowTrainModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              새 모델 학습
            </button>
            <button
              onClick={() => setShowRollbackModal(true)}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
            >
              모델 롤백
            </button>
          </div>
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {/* 학습 상태 */}
        {trainingStatus && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-300 rounded-lg">
            <h3 className="text-lg font-semibold mb-2">
              모델 학습 진행 중: {trainingStatus.model_id}
            </h3>
            <div className="mb-2">
              <div className="flex justify-between text-sm mb-1">
                <span>{trainingStatus.current_step}</span>
                <span>{trainingStatus.progress_percentage}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${trainingStatus.progress_percentage}%` }}
                />
              </div>
            </div>
            <p className="text-sm text-gray-600">
              경과 시간: {Math.floor(trainingStatus.elapsed_time_seconds / 60)}분{" "}
              {trainingStatus.elapsed_time_seconds % 60}초
            </p>
            {trainingStatus.error_message && (
              <p className="text-sm text-red-600 mt-2">
                오류: {trainingStatus.error_message}
              </p>
            )}
          </div>
        )}

        {/* 카나리 배포 상태 */}
        {canaryStatus?.is_active && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-300 rounded-lg">
            <h3 className="text-lg font-semibold mb-2">카나리 배포 진행 중</h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-sm text-gray-600">카나리 모델</p>
                <p className="font-medium">{canaryStatus.canary_model_id}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">프로덕션 모델</p>
                <p className="font-medium">{canaryStatus.production_model_id}</p>
              </div>
            </div>
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-1">
                트래픽 분할: {canaryStatus.traffic_percentage}%
              </p>
              <div className="flex gap-2">
                {[10, 25, 50, 100].map((percentage) => (
                  <button
                    key={percentage}
                    onClick={() => handleAdjustCanaryTraffic(percentage)}
                    className="px-3 py-1 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700 transition"
                    disabled={loading}
                  >
                    {percentage}%
                  </button>
                ))}
              </div>
            </div>
            {canaryStatus.recommendation && (
              <p className="text-sm text-gray-700 mb-4">
                권장사항: {canaryStatus.recommendation}
              </p>
            )}
            <div className="flex gap-2">
              <button
                onClick={handleCompleteCanary}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition"
                disabled={loading}
              >
                배포 완료
              </button>
              <button
                onClick={handleAbortCanary}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition"
                disabled={loading}
              >
                배포 중단
              </button>
            </div>
          </div>
        )}

        {/* 필터 */}
        <div className="bg-white rounded-lg shadow-md p-4 mb-6">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                배포 상태
              </label>
              <select
                value={deploymentStatusFilter}
                onChange={(e) => setDeploymentStatusFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">전체</option>
                <option value="development">개발</option>
                <option value="staging">스테이징</option>
                <option value="production">프로덕션</option>
                <option value="canary">카나리</option>
                <option value="retired">은퇴</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                모델 유형
              </label>
              <select
                value={modelTypeFilter}
                onChange={(e) => setModelTypeFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">전체</option>
                <option value="isolation_forest">Isolation Forest</option>
                <option value="lightgbm">LightGBM</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={fetchModels}
                className="w-full px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition"
                disabled={loading}
              >
                새로고침
              </button>
            </div>
          </div>
        </div>

        {/* 모델 목록 */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-gray-500">로딩 중...</div>
          ) : models.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              모델이 없습니다. 새 모델을 학습하세요.
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    모델명
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    버전
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    유형
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    배포 상태
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    성능 지표
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    학습일
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    작업
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {models.map((model) => (
                  <tr key={model.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {model.name}
                      </div>
                      <div className="text-xs text-gray-500">{model.id}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {model.version}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {model.model_type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadgeColor(
                          model.deployment_status
                        )}`}
                      >
                        {getStatusLabel(model.deployment_status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {model.metrics.f1_score !== undefined ? (
                        <div>
                          <div>F1: {(model.metrics.f1_score * 100).toFixed(2)}%</div>
                          <div className="text-xs text-gray-500">
                            정확도: {((model.metrics.accuracy || 0) * 100).toFixed(2)}%
                          </div>
                        </div>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(model.trained_at).toLocaleString("ko-KR")}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex gap-2">
                        {model.deployment_status === "staging" && (
                          <>
                            <button
                              onClick={() => {
                                setSelectedModel(model);
                                setDeployForm({ target_environment: "production" });
                                setShowDeployModal(true);
                              }}
                              className="text-green-600 hover:text-green-900"
                            >
                              프로덕션 배포
                            </button>
                            <button
                              onClick={() => {
                                setSelectedModel(model);
                                setShowCanaryModal(true);
                              }}
                              className="text-yellow-600 hover:text-yellow-900"
                            >
                              카나리 배포
                            </button>
                          </>
                        )}
                        {model.deployment_status === "development" && (
                          <button
                            onClick={() => {
                              setSelectedModel(model);
                              setDeployForm({ target_environment: "staging" });
                              setShowDeployModal(true);
                            }}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            스테이징 배포
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* 모델 학습 모달 */}
        {showTrainModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h2 className="text-2xl font-bold mb-4">새 모델 학습</h2>
              <form onSubmit={handleTrain}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    모델 유형
                  </label>
                  <select
                    value={trainForm.model_type}
                    onChange={(e) =>
                      setTrainForm({ ...trainForm, model_type: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  >
                    <option value="isolation_forest">Isolation Forest</option>
                    <option value="lightgbm">LightGBM</option>
                  </select>
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    학습 데이터 기간 (일)
                  </label>
                  <input
                    type="number"
                    min="7"
                    max="365"
                    value={trainForm.training_period_days}
                    onChange={(e) =>
                      setTrainForm({
                        ...trainForm,
                        training_period_days: parseInt(e.target.value),
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div className="mb-6">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={trainForm.auto_deploy_to_staging}
                      onChange={(e) =>
                        setTrainForm({
                          ...trainForm,
                          auto_deploy_to_staging: e.target.checked,
                        })
                      }
                      className="mr-2"
                    />
                    <span className="text-sm text-gray-700">
                      학습 완료 후 자동으로 스테이징에 배포
                    </span>
                  </label>
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowTrainModal(false)}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    취소
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
                  >
                    학습 시작
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* 모델 배포 모달 */}
        {showDeployModal && selectedModel && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h2 className="text-2xl font-bold mb-4">모델 배포</h2>
              <p className="text-gray-600 mb-4">
                모델: {selectedModel.name} (v{selectedModel.version})
              </p>
              <form onSubmit={handleDeploy}>
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    배포 환경
                  </label>
                  <select
                    value={deployForm.target_environment}
                    onChange={(e) =>
                      setDeployForm({
                        target_environment: e.target.value as "staging" | "production",
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  >
                    <option value="staging">스테이징</option>
                    <option value="production">프로덕션</option>
                  </select>
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowDeployModal(false)}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    취소
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400"
                  >
                    배포
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* 카나리 배포 모달 */}
        {showCanaryModal && selectedModel && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h2 className="text-2xl font-bold mb-4">카나리 배포</h2>
              <p className="text-gray-600 mb-4">
                모델: {selectedModel.name} (v{selectedModel.version})
              </p>
              <form onSubmit={handleStartCanary}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    초기 트래픽 비율 (%)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={canaryForm.initial_traffic_percentage}
                    onChange={(e) =>
                      setCanaryForm({
                        ...canaryForm,
                        initial_traffic_percentage: parseInt(e.target.value),
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    성공률 임계값 (0-1)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={canaryForm.success_threshold}
                    onChange={(e) =>
                      setCanaryForm({
                        ...canaryForm,
                        success_threshold: parseFloat(e.target.value),
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    모니터링 시간 (분)
                  </label>
                  <input
                    type="number"
                    min="10"
                    max="1440"
                    value={canaryForm.monitoring_window_minutes}
                    onChange={(e) =>
                      setCanaryForm({
                        ...canaryForm,
                        monitoring_window_minutes: parseInt(e.target.value),
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowCanaryModal(false)}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    취소
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:bg-gray-400"
                  >
                    카나리 배포 시작
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* 롤백 모달 */}
        {showRollbackModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h2 className="text-2xl font-bold mb-4">모델 롤백</h2>
              <form onSubmit={handleRollback}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    롤백 사유
                  </label>
                  <textarea
                    value={rollbackForm.reason}
                    onChange={(e) =>
                      setRollbackForm({
                        ...rollbackForm,
                        reason: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={3}
                    required
                  />
                </div>
                <div className="mb-6">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={rollbackForm.emergency}
                      onChange={(e) =>
                        setRollbackForm({
                          ...rollbackForm,
                          emergency: e.target.checked,
                        })
                      }
                      className="mr-2"
                    />
                    <span className="text-sm text-gray-700">긴급 롤백 (즉시 실행)</span>
                  </label>
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowRollbackModal(false)}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    취소
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-400"
                  >
                    롤백 실행
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MLModelManagement;
