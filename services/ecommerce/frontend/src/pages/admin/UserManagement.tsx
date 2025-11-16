/**
 * 회원 관리 페이지
 *
 * T094: 회원 관리 페이지 구현
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi, adminQueryKeys } from '../../services/admin-api';
import type { User } from '../../services/api';

export const UserManagement: React.FC = () => {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);

  // 회원 목록 조회
  const { data: usersData, isLoading } = useQuery({
    queryKey: adminQueryKeys.users.list({
      status: statusFilter,
      role: roleFilter,
      search: searchQuery,
      page,
    }),
    queryFn: () =>
      adminApi.getAllUsers({
        status: statusFilter || undefined,
        role: roleFilter || undefined,
        search: searchQuery || undefined,
        page,
        page_size: 20,
      }),
  });

  // 회원 상태 업데이트 뮤테이션
  const updateUserStatusMutation = useMutation({
    mutationFn: ({ userId, status, notes }: { userId: string; status: string; notes?: string }) =>
      adminApi.updateUserStatus(userId, { status, admin_notes: notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.users.all });
      alert('회원 상태가 성공적으로 업데이트되었습니다.');
    },
    onError: (error) => {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      alert(`회원 상태 업데이트 실패: ${err.response?.data?.detail || err.message}`);
    },
  });

  // 상태 변경 핸들러
  const handleStatusChange = (userId: string, newStatus: string) => {
    const notes = prompt('관리자 메모를 입력하세요 (선택사항):');
    if (window.confirm(`회원 상태를 "${newStatus}"로 변경하시겠습니까?`)) {
      updateUserStatusMutation.mutate({
        userId,
        status: newStatus,
        notes: notes || undefined,
      });
    }
  };

  // 검색 핸들러
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  // 필터 초기화
  const handleResetFilters = () => {
    setStatusFilter('');
    setRoleFilter('');
    setSearchQuery('');
    setPage(1);
  };

  // 회원 상태 목록
  const userStatuses = [
    { value: 'active', label: '활성' },
    { value: 'inactive', label: '비활성' },
    { value: 'suspended', label: '정지' },
    { value: 'deleted', label: '삭제됨' },
  ];

  // 회원 역할 목록
  const userRoles = [
    { value: 'customer', label: '일반 회원' },
    { value: 'admin', label: '관리자' },
    { value: 'security', label: '보안팀' },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-4">회원 관리</h1>

        {/* 검색 및 필터 */}
        <div className="bg-white shadow-md rounded-lg p-4 mb-6">
          <form onSubmit={handleSearch} className="mb-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="이름 또는 이메일 검색..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                type="submit"
                className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                검색
              </button>
            </div>
          </form>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* 상태 필터 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">회원 상태</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">전체</option>
                {userStatuses.map((status) => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 역할 필터 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">회원 역할</label>
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">전체</option>
                {userRoles.map((role) => (
                  <option key={role.value} value={role.value}>
                    {role.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 필터 초기화 */}
            <div className="flex items-end">
              <button
                onClick={handleResetFilters}
                className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
              >
                필터 초기화
              </button>
            </div>
          </div>
        </div>

        {/* 통계 요약 */}
        {usersData && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white shadow-md rounded-lg p-4">
              <div className="text-sm text-gray-500">전체 회원</div>
              <div className="text-2xl font-bold">{usersData.total_count}</div>
            </div>
            <div className="bg-white shadow-md rounded-lg p-4">
              <div className="text-sm text-gray-500">활성 회원</div>
              <div className="text-2xl font-bold text-green-600">
                {usersData.users.filter((u) => u.status === 'active').length}
              </div>
            </div>
            <div className="bg-white shadow-md rounded-lg p-4">
              <div className="text-sm text-gray-500">정지된 회원</div>
              <div className="text-2xl font-bold text-red-600">
                {usersData.users.filter((u) => u.status === 'suspended').length}
              </div>
            </div>
            <div className="bg-white shadow-md rounded-lg p-4">
              <div className="text-sm text-gray-500">관리자</div>
              <div className="text-2xl font-bold text-blue-600">
                {usersData.users.filter((u) => u.role === 'admin').length}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 회원 목록 */}
      {isLoading ? (
        <div className="text-center py-8">로딩 중...</div>
      ) : usersData?.users.length === 0 ? (
        <div className="text-center py-8 text-gray-500">회원이 없습니다.</div>
      ) : (
        <div className="bg-white shadow-md rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  회원 정보
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  역할
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  상태
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  가입일
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  작업
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {usersData?.users.map((user) => (
                <UserRow
                  key={user.id}
                  user={user}
                  onStatusChange={handleStatusChange}
                  isUpdating={updateUserStatusMutation.isPending}
                  userStatuses={userStatuses}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 페이지네이션 */}
      {usersData && usersData.total_count > 0 && (
        <div className="mt-6 flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50"
          >
            이전
          </button>
          <span className="px-4 py-2">
            {page} / {Math.ceil(usersData.total_count / usersData.page_size)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(usersData.total_count / usersData.page_size)}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50"
          >
            다음
          </button>
        </div>
      )}
    </div>
  );
};

// 회원 행 컴포넌트
interface UserRowProps {
  user: User;
  onStatusChange: (userId: string, newStatus: string) => void;
  isUpdating: boolean;
  userStatuses: Array<{ value: string; label: string }>;
}

const UserRow: React.FC<UserRowProps> = ({ user, onStatusChange, isUpdating, userStatuses }) => {
  // 상태별 색상
  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      active: 'bg-green-100 text-green-800',
      inactive: 'bg-gray-100 text-gray-800',
      suspended: 'bg-red-100 text-red-800',
      deleted: 'bg-red-100 text-red-800',
    };
    return colorMap[status] || 'bg-gray-100 text-gray-800';
  };

  // 역할별 색상
  const getRoleColor = (role: string) => {
    const colorMap: Record<string, string> = {
      customer: 'bg-blue-100 text-blue-800',
      admin: 'bg-purple-100 text-purple-800',
      security: 'bg-indigo-100 text-indigo-800',
    };
    return colorMap[role] || 'bg-gray-100 text-gray-800';
  };

  const statusLabel = userStatuses.find((s) => s.value === user.status)?.label || user.status;

  return (
    <tr className={user.status === 'suspended' ? 'bg-red-50' : ''}>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <div>
            <div className="text-sm font-medium text-gray-900">{user.name}</div>
            <div className="text-xs text-gray-500">{user.email}</div>
            <div className="text-xs text-gray-400">ID: {user.id.slice(0, 8)}...</div>
          </div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className={`px-2 py-1 text-xs font-medium rounded ${getRoleColor(user.role)}`}>
          {user.role === 'customer' ? '일반 회원' : user.role === 'admin' ? '관리자' : '보안팀'}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(user.status)}`}>
          {statusLabel}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {user.created_at ? new Date(user.created_at).toLocaleDateString('ko-KR') : 'N/A'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm">
        <select
          onChange={(e) => onStatusChange(user.id, e.target.value)}
          disabled={isUpdating}
          className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
          defaultValue=""
        >
          <option value="" disabled>
            상태 변경
          </option>
          {userStatuses
            .filter((s) => s.value !== user.status)
            .map((status) => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
        </select>
      </td>
    </tr>
  );
};
