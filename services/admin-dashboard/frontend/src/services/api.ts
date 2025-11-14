/**
 * API 서비스
 *
 * 관리자 대시보드 백엔드 API와 통신하는 클라이언트입니다.
 */

import axios, { AxiosInstance } from "axios";
import type {
  DashboardStats,
  ReviewQueueListResponse,
  ReviewQueueDetail,
  TransactionDetail,
  ReviewDecisionRequest,
  ReviewDecisionResponse,
  ReviewStatus,
} from "../types/dashboard";

// API 기본 URL (환경 변수에서 가져오거나 기본값 사용)
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8002";

// Axios 인스턴스 생성
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// 요청 인터셉터 (인증 토큰 추가 등)
apiClient.interceptors.request.use(
  (config) => {
    // 향후 JWT 토큰 추가
    // const token = localStorage.getItem('authToken');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터 (에러 처리)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // 서버 에러 응답
      console.error("API Error:", error.response.data);
    } else if (error.request) {
      // 요청은 보냈지만 응답을 받지 못함
      console.error("Network Error:", error.request);
    } else {
      // 요청 설정 중 에러 발생
      console.error("Request Setup Error:", error.message);
    }
    return Promise.reject(error);
  }
);

/**
 * 대시보드 API
 */
export const dashboardApi = {
  /**
   * 대시보드 통계 조회
   * @param timeRange 시간 범위 (1h, 24h, 7d, 30d)
   */
  getStats: async (
    timeRange: "1h" | "24h" | "7d" | "30d" = "24h"
  ): Promise<DashboardStats> => {
    const response = await apiClient.get<DashboardStats>(
      `/v1/dashboard/stats`,
      {
        params: { time_range: timeRange },
      }
    );
    return response.data;
  },
};

/**
 * 검토 큐 API
 */
export const reviewQueueApi = {
  /**
   * 검토 큐 목록 조회
   * @param status 검토 상태 필터
   * @param limit 최대 결과 수
   * @param offset 페이지 오프셋
   */
  getList: async (
    status?: ReviewStatus,
    limit: number = 50,
    offset: number = 0
  ): Promise<ReviewQueueListResponse> => {
    const response = await apiClient.get<ReviewQueueListResponse>(
      `/v1/review-queue`,
      {
        params: { status, limit, offset },
      }
    );
    return response.data;
  },

  /**
   * 검토 큐 항목 상세 조회
   * @param reviewQueueId 검토 큐 ID
   */
  getDetail: async (reviewQueueId: string): Promise<ReviewQueueDetail> => {
    const response = await apiClient.get<ReviewQueueDetail>(
      `/v1/review-queue/${reviewQueueId}`
    );
    return response.data;
  },

  /**
   * 검토 결정 제출
   * @param reviewQueueId 검토 큐 ID
   * @param request 검토 결정 요청
   */
  submitDecision: async (
    reviewQueueId: string,
    request: ReviewDecisionRequest
  ): Promise<ReviewDecisionResponse> => {
    const response = await apiClient.post<ReviewDecisionResponse>(
      `/v1/review-queue/${reviewQueueId}/approve`,
      request
    );
    return response.data;
  },
};

/**
 * 거래 API
 */
export const transactionApi = {
  /**
   * 거래 상세 정보 조회
   * @param transactionId 거래 ID
   */
  getDetail: async (transactionId: string): Promise<TransactionDetail> => {
    const response = await apiClient.get<TransactionDetail>(
      `/v1/transactions/${transactionId}`
    );
    return response.data;
  },
};

/**
 * 룰 관리 API
 */
export const rulesApi = {
  /**
   * 룰 목록 조회
   */
  getList: async (params?: {
    is_active?: boolean;
    rule_type?: string;
    skip?: number;
    limit?: number;
  }) => {
    const response = await apiClient.get(`/v1/rules`, { params });
    return response.data;
  },

  /**
   * 룰 상세 조회
   */
  getDetail: async (ruleId: string) => {
    const response = await apiClient.get(`/v1/rules/${ruleId}`);
    return response.data;
  },

  /**
   * 새 룰 생성
   */
  create: async (data: any) => {
    const response = await apiClient.post(`/v1/rules`, data);
    return response.data;
  },

  /**
   * 룰 수정
   */
  update: async (ruleId: string, data: any) => {
    const response = await apiClient.put(`/v1/rules/${ruleId}`, data);
    return response.data;
  },

  /**
   * 룰 삭제
   */
  delete: async (ruleId: string) => {
    const response = await apiClient.delete(`/v1/rules/${ruleId}`);
    return response.data;
  },

  /**
   * 룰 활성화/비활성화 토글
   */
  toggle: async (ruleId: string) => {
    const response = await apiClient.patch(`/v1/rules/${ruleId}/toggle`);
    return response.data;
  },
};

/**
 * A/B 테스트 API
 */
export const abTestsApi = {
  /**
   * A/B 테스트 목록 조회
   */
  getList: async (params?: {
    test_type?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }) => {
    const response = await apiClient.get(`/v1/ab-tests`, { params });
    return response.data;
  },

  /**
   * A/B 테스트 상세 조회
   */
  getDetail: async (testId: string) => {
    const response = await apiClient.get(`/v1/ab-tests/${testId}`);
    return response.data;
  },

  /**
   * 새 A/B 테스트 생성
   */
  create: async (data: any) => {
    const response = await apiClient.post(`/v1/ab-tests`, data);
    return response.data;
  },

  /**
   * A/B 테스트 수정
   */
  update: async (testId: string, data: any) => {
    const response = await apiClient.put(`/v1/ab-tests/${testId}`, data);
    return response.data;
  },

  /**
   * A/B 테스트 상태 변경
   */
  updateStatus: async (testId: string, data: {
    action: 'start' | 'pause' | 'resume' | 'complete' | 'cancel';
    winner?: string;
    confidence_level?: number;
  }) => {
    const response = await apiClient.patch(`/v1/ab-tests/${testId}/status`, data);
    return response.data;
  },

  /**
   * A/B 테스트 결과 조회
   */
  getResults: async (testId: string) => {
    const response = await apiClient.get(`/v1/ab-tests/${testId}/results`);
    return response.data;
  },

  /**
   * A/B 테스트 삭제
   */
  delete: async (testId: string) => {
    const response = await apiClient.delete(`/v1/ab-tests/${testId}`);
    return response.data;
  },
};

export default apiClient;
