/**
 * 룰 관리 페이지
 *
 * 보안팀이 FDS 탐지 룰을 동적으로 관리할 수 있는 페이지입니다.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { rulesApi } from "../services/api";

interface Rule {
  id: string;
  name: string;
  description: string;
  rule_type: string;
  conditions: Record<string, unknown>;
  risk_score_addition: number;
  is_active: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

const RuleManagement = () => {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [filterActive, setFilterActive] = useState<boolean | undefined>(
    undefined
  );
  const [filterType, setFilterType] = useState<string>("");

  // 룰 목록 조회
  const {
    data: rulesData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["rules", filterActive, filterType],
    queryFn: () =>
      rulesApi.getList({
        is_active: filterActive,
        rule_type: filterType || undefined,
      }),
  });

  // 룰 토글 mutation
  const toggleMutation = useMutation({
    mutationFn: (ruleId: string) => rulesApi.toggle(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] });
    },
  });

  // 룰 삭제 mutation
  const deleteMutation = useMutation({
    mutationFn: (ruleId: string) => rulesApi.delete(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] });
    },
  });

  // 룰 토글 핸들러
  const handleToggle = (ruleId: string) => {
    if (
      window.confirm("이 룰의 활성화 상태를 변경하시겠습니까?")
    ) {
      toggleMutation.mutate(ruleId);
    }
  };

  // 룰 삭제 핸들러
  const handleDelete = (ruleId: string) => {
    if (
      window.confirm(
        "정말로 이 룰을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다."
      )
    ) {
      deleteMutation.mutate(ruleId);
    }
  };

  // 로딩 상태
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">룰 목록을 불러오는 중...</p>
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
            룰 목록을 불러오는 중 오류가 발생했습니다.
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

  const rules: Rule[] = rulesData?.rules || [];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* 헤더 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">룰 관리</h1>
        <p className="text-gray-600">
          FDS 탐지 룰을 동적으로 추가, 수정, 삭제할 수 있습니다.
        </p>
      </div>

      {/* 필터 및 추가 버튼 */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          {/* 활성 상태 필터 */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">상태:</label>
            <select
              value={filterActive === undefined ? "" : filterActive.toString()}
              onChange={(e) =>
                setFilterActive(
                  e.target.value === "" ? undefined : e.target.value === "true"
                )
              }
              className="border border-gray-300 rounded px-3 py-2 text-sm"
            >
              <option value="">전체</option>
              <option value="true">활성</option>
              <option value="false">비활성</option>
            </select>
          </div>

          {/* 룰 타입 필터 */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">타입:</label>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm"
            >
              <option value="">전체</option>
              <option value="velocity_check">Velocity Check</option>
              <option value="amount_threshold">금액 임계값</option>
              <option value="location_mismatch">지역 불일치</option>
              <option value="custom">커스텀</option>
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
            새 룰 추가
          </button>
        </div>
      </div>

      {/* 룰 목록 */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {rules.length === 0 ? (
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
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <p className="text-gray-500">등록된 룰이 없습니다.</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-4 text-blue-600 hover:text-blue-700 font-medium"
            >
              첫 번째 룰 추가하기
            </button>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  룰 이름
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  타입
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  위험 점수
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  우선순위
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
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">
                      {rule.name}
                    </div>
                    <div className="text-sm text-gray-500">
                      {rule.description}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {rule.rule_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    +{rule.risk_score_addition}점
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {rule.priority}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => handleToggle(rule.id)}
                      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                        rule.is_active
                          ? "bg-green-100 text-green-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {rule.is_active ? "활성" : "비활성"}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(rule.created_at).toLocaleDateString("ko-KR")}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => setEditingRule(rule)}
                      className="text-blue-600 hover:text-blue-900 mr-4"
                    >
                      수정
                    </button>
                    <button
                      onClick={() => handleDelete(rule.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 룰 생성/수정 모달 (간단한 placeholder - 실제 구현 시 확장 필요) */}
      {(showCreateModal || editingRule) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">
              {editingRule ? "룰 수정" : "새 룰 추가"}
            </h2>
            <p className="text-gray-600 mb-4">
              룰 생성/수정 폼은 실제 구현 시 추가됩니다. 현재는 API 연동 테스트를
              위한 placeholder입니다.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setEditingRule(null);
                }}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                취소
              </button>
              <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                저장
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RuleManagement;
