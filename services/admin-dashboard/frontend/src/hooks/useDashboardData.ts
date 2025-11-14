/**
 * 대시보드 데이터 Hooks
 *
 * React Query를 사용한 대시보드 데이터 fetching hooks입니다.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dashboardApi, reviewQueueApi, transactionApi } from "../services/api";
import type { ReviewDecisionRequest, ReviewStatus } from "../types/dashboard";

/**
 * 대시보드 통계 조회
 */
export const useDashboardStats = (
  timeRange: "1h" | "24h" | "7d" | "30d" = "24h"
) => {
  return useQuery({
    queryKey: ["dashboardStats", timeRange],
    queryFn: () => dashboardApi.getStats(timeRange),
    refetchInterval: 30000, // 30초마다 자동 갱신
    staleTime: 20000, // 20초 동안은 fresh 상태 유지
  });
};

/**
 * 검토 큐 목록 조회
 */
export const useReviewQueueList = (
  status?: ReviewStatus,
  limit: number = 50,
  offset: number = 0
) => {
  return useQuery({
    queryKey: ["reviewQueue", status, limit, offset],
    queryFn: () => reviewQueueApi.getList(status, limit, offset),
    refetchInterval: 60000, // 1분마다 자동 갱신
    staleTime: 30000, // 30초 동안은 fresh 상태 유지
  });
};

/**
 * 검토 큐 상세 조회
 */
export const useReviewQueueDetail = (reviewQueueId?: string) => {
  return useQuery({
    queryKey: ["reviewQueueDetail", reviewQueueId],
    queryFn: () => reviewQueueApi.getDetail(reviewQueueId!),
    enabled: !!reviewQueueId, // reviewQueueId가 있을 때만 실행
  });
};

/**
 * 거래 상세 조회
 */
export const useTransactionDetail = (transactionId?: string) => {
  return useQuery({
    queryKey: ["transactionDetail", transactionId],
    queryFn: () => transactionApi.getDetail(transactionId!),
    enabled: !!transactionId, // transactionId가 있을 때만 실행
  });
};

/**
 * 검토 결정 제출
 */
export const useSubmitReviewDecision = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      reviewQueueId,
      request,
    }: {
      reviewQueueId: string;
      request: ReviewDecisionRequest;
    }) => reviewQueueApi.submitDecision(reviewQueueId, request),
    onSuccess: () => {
      // 성공 시 관련 쿼리 무효화하여 데이터 재조회
      queryClient.invalidateQueries({ queryKey: ["reviewQueue"] });
      queryClient.invalidateQueries({ queryKey: ["dashboardStats"] });
    },
  });
};
