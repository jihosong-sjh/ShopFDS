/**
 * A/B 테스트 설정 페이지
 *
 * 보안팀이 FDS 룰이나 ML 모델의 A/B 테스트를 설정하고 관리하는 페이지입니다.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { abTestsApi } from "../services/api";

interface ABTest {
  id: string;
  name: string;
  description: string;
  test_type: string;
  status: string;
  group_a_config: Record<string, unknown>;
  group_b_config: Record<string, unknown>;
  traffic_split_percentage: number;
  start_time: string | null;
  end_time: string | null;
  planned_duration_hours: number | null;
  created_at: string;
}

const ABTestSetup = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterType, setFilterType] = useState<string>("");

  // A/B 테스트 목록 조회
  const {
    data: testsData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["abTests", filterStatus, filterType],
    queryFn: () =>
      abTestsApi.getList({
        status: filterStatus || undefined,
        test_type: filterType || undefined,
      }),
  });

  // 상태 변경 mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({
      testId,
      action,
    }: {
      testId: string;
      action: "start" | "pause" | "resume" | "complete" | "cancel";
    }) => abTestsApi.updateStatus(testId, { action }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["abTests"] });
    },
  });

  // 테스트 삭제 mutation
  const deleteMutation = useMutation({
    mutationFn: (testId: string) => abTestsApi.delete(testId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["abTests"] });
    },
  });

  // 상태 변경 핸들러
  const handleStatusChange = (
    testId: string,
    action: "start" | "pause" | "resume" | "complete" | "cancel"
  ) => {
    const actionText = {
      start: "시작",
      pause: "일시 중지",
      resume: "재개",
      complete: "완료",
      cancel: "취소",
    }[action];

    if (window.confirm(`이 테스트를 ${actionText}하시겠습니까?`)) {
      updateStatusMutation.mutate({ testId, action });
    }
  };

  // 테스트 삭제 핸들러
  const handleDelete = (testId: string) => {
    if (
      window.confirm(
        "정말로 이 테스트를 삭제하시겠습니까? 모든 결과 데이터가 영구적으로 삭제됩니다."
      )
    ) {
      deleteMutation.mutate(testId);
    }
  };

  // 결과 보기 핸들러
  const handleViewResults = (testId: string) => {
    navigate(`/ab-tests/${testId}/results`);
  };

  // 로딩 상태
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">테스트 목록을 불러오는 중...</p>
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
            테스트 목록을 불러오는 중 오류가 발생했습니다.
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

  const tests: ABTest[] = testsData?.tests || [];

  // 상태별 뱃지 색상
  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "draft":
        return "bg-gray-100 text-gray-800";
      case "running":
        return "bg-green-100 text-green-800";
      case "paused":
        return "bg-yellow-100 text-yellow-800";
      case "completed":
        return "bg-blue-100 text-blue-800";
      case "cancelled":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  // 상태 한글 변환
  const getStatusText = (status: string) => {
    switch (status) {
      case "draft":
        return "초안";
      case "running":
        return "진행중";
      case "paused":
        return "일시중지";
      case "completed":
        return "완료";
      case "cancelled":
        return "취소됨";
      default:
        return status;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* 헤더 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          A/B 테스트 관리
        </h1>
        <p className="text-gray-600">
          FDS 룰이나 ML 모델의 성능을 비교하기 위한 A/B 테스트를 관리합니다.
        </p>
      </div>

      {/* 필터 및 추가 버튼 */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          {/* 상태 필터 */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">상태:</label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm"
            >
              <option value="">전체</option>
              <option value="draft">초안</option>
              <option value="running">진행중</option>
              <option value="paused">일시중지</option>
              <option value="completed">완료</option>
              <option value="cancelled">취소됨</option>
            </select>
          </div>

          {/* 테스트 타입 필터 */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">타입:</label>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm"
            >
              <option value="">전체</option>
              <option value="rule">룰 비교</option>
              <option value="model">모델 비교</option>
              <option value="threshold">임계값 비교</option>
              <option value="hybrid">복합 테스트</option>
            </select>
          </div>

          {/* 추가 버튼 */}
          <button
            onClick={() => setShowCreateModal(true)}
            className="ml-auto bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 flex items-center gap-2"
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
                d="M12 6v6m0 0v6m0-6h6m-6 0H6"
              />
            </svg>
            새 테스트 추가
          </button>
        </div>
      </div>

      {/* 테스트 목록 */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {tests.length === 0 ? (
          <div className="text-center py-12">
            <svg
              className="w-16 h-16 text-gray-400 mx-auto mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
              />
            </svg>
            <p className="text-gray-500">등록된 테스트가 없습니다.</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-4 text-blue-600 hover:text-blue-700 font-medium"
            >
              첫 번째 테스트 추가하기
            </button>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  테스트 이름
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  타입
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  트래픽 분할
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  상태
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  생성일
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  작업
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {tests.map((test) => (
                <tr key={test.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">
                      {test.name}
                    </div>
                    <div className="text-sm text-gray-500">
                      {test.description || "설명 없음"}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                      {test.test_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    A: {100 - test.traffic_split_percentage}% / B:{" "}
                    {test.traffic_split_percentage}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${getStatusBadgeClass(
                        test.status
                      )}`}
                    >
                      {getStatusText(test.status)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(test.created_at).toLocaleDateString("ko-KR")}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end gap-2">
                      {/* 상태별 액션 버튼 */}
                      {test.status === "draft" && (
                        <button
                          onClick={() => handleStatusChange(test.id, "start")}
                          className="text-green-600 hover:text-green-900"
                        >
                          시작
                        </button>
                      )}
                      {test.status === "running" && (
                        <>
                          <button
                            onClick={() => handleStatusChange(test.id, "pause")}
                            className="text-yellow-600 hover:text-yellow-900"
                          >
                            일시중지
                          </button>
                          <button
                            onClick={() =>
                              handleStatusChange(test.id, "complete")
                            }
                            className="text-blue-600 hover:text-blue-900"
                          >
                            완료
                          </button>
                        </>
                      )}
                      {test.status === "paused" && (
                        <button
                          onClick={() => handleStatusChange(test.id, "resume")}
                          className="text-green-600 hover:text-green-900"
                        >
                          재개
                        </button>
                      )}
                      {test.status === "completed" && (
                        <button
                          onClick={() => handleViewResults(test.id)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          결과 보기
                        </button>
                      )}
                      {test.status !== "running" && (
                        <button
                          onClick={() => handleDelete(test.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          삭제
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

      {/* 테스트 생성 모달 (간단한 placeholder) */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">새 A/B 테스트 추가</h2>
            <p className="text-gray-600 mb-4">
              테스트 생성 폼은 실제 구현 시 추가됩니다. 현재는 API 연동 테스트를
              위한 placeholder입니다.
            </p>
            <p className="text-sm text-gray-500 mb-6">
              실제 구현에서는 룰 선택, 트래픽 분할 비율 설정, 계획된 기간 설정
              등의 입력 필드가 포함됩니다.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                취소
              </button>
              <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                생성
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ABTestSetup;
