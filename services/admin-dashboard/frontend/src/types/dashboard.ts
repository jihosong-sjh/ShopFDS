/**
 * 대시보드 타입 정의
 *
 * 보안팀 대시보드에서 사용하는 모든 타입을 정의합니다.
 */

// 위험 수준
export type RiskLevel = "low" | "medium" | "high";

// 평가 상태
export type EvaluationStatus = "pending" | "approved" | "blocked" | "manual_review" | "additional_auth_required";

// 디바이스 타입
export type DeviceType = "desktop" | "mobile" | "tablet" | "unknown";

// 검토 상태
export type ReviewStatus = "pending" | "in_review" | "completed";

// 검토 결정
export type ReviewDecision = "approve" | "block" | "escalate";

// 거래 요약 통계
export interface TransactionSummary {
  total: number;
  approved: number;
  blocked: number;
  manual_review: number;
}

// 위험도별 분포
export interface RiskDistribution {
  low: number;
  medium: number;
  high: number;
}

// 검토 큐 요약
export interface ReviewQueueSummary {
  total: number;
  pending: number;
  in_review: number;
  completed: number;
}

// 최근 알림
export interface RecentAlert {
  transaction_id: string;
  user_id: string;
  order_id: string;
  amount: number;
  risk_score: number;
  ip_address: string;
  created_at: string;
  evaluation_status: EvaluationStatus;
}

// 대시보드 통계
export interface DashboardStats {
  time_range: string;
  generated_at: string;
  transaction_summary: TransactionSummary;
  risk_distribution: RiskDistribution;
  review_queue_summary: ReviewQueueSummary;
  avg_evaluation_time_ms: number;
  performance_status: "good" | "degraded";
  recent_alerts: RecentAlert[];
}

// 거래 정보
export interface Transaction {
  id: string;
  order_id: string;
  user_id: string;
  amount: number;
  risk_score: number;
  risk_level: RiskLevel;
  evaluation_status: EvaluationStatus;
  ip_address: string;
  user_agent?: string;
  device_type: DeviceType;
  geolocation?: string;
  evaluation_time_ms?: number;
  created_at: string;
  evaluated_at?: string;
}

// 위험 요인
export interface RiskFactor {
  id: string;
  factor_type: string;
  factor_score: number;
  description: string;
  metadata?: Record<string, any>;
}

// 검토 큐 항목
export interface ReviewQueueItem {
  id: string;
  transaction_id: string;
  status: ReviewStatus;
  decision?: ReviewDecision;
  assigned_to?: string;
  review_notes?: string;
  added_at: string;
  reviewed_at?: string;
  transaction: {
    order_id: string;
    user_id: string;
    amount: number;
    risk_score: number;
    risk_level: RiskLevel;
    ip_address: string;
    device_type: DeviceType;
    created_at: string;
  };
}

// 검토 큐 목록 응답
export interface ReviewQueueListResponse {
  items: ReviewQueueItem[];
  total: number;
  limit: number;
  offset: number;
}

// 사용자 이력 요약
export interface UserHistory {
  total_transactions: number;
  high_risk_count: number;
  blocked_count: number;
  avg_risk_score: number;
}

// 검토 큐 상세
export interface ReviewQueueDetail {
  id: string;
  transaction_id: string;
  status: ReviewStatus;
  decision?: ReviewDecision;
  assigned_to?: string;
  review_notes?: string;
  added_at: string;
  reviewed_at?: string;
  transaction: Transaction;
  risk_factors: RiskFactor[];
}

// 거래 상세 정보
export interface TransactionDetail {
  transaction: Transaction;
  risk_factors: RiskFactor[];
  review_queue?: {
    id: string;
    status: ReviewStatus;
    decision?: ReviewDecision;
    assigned_to?: string;
    review_notes?: string;
    added_at: string;
    reviewed_at?: string;
  };
  user_history: UserHistory;
}

// 검토 결정 요청
export interface ReviewDecisionRequest {
  decision: ReviewDecision;
  notes?: string;
  reviewer_id: string;
}

// 검토 결정 응답
export interface ReviewDecisionResponse {
  review_queue_id: string;
  transaction_id: string;
  decision: ReviewDecision;
  status: ReviewStatus;
  reviewed_at: string;
  transaction_status: EvaluationStatus;
  message: string;
}
