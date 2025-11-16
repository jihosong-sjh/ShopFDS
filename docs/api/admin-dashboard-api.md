# 관리자 대시보드 API 문서

**Base URL**: `http://localhost:8003` (개발)

**Version**: 1.0.0

**Swagger UI**: http://localhost:8003/docs

**권한**: `SECURITY_ANALYST` 또는 `SECURITY_MANAGER` 역할 필요

---

## 대시보드 API (`/v1/dashboard`)

### 실시간 통계 조회

```http
GET /v1/dashboard/stats?period=today
Authorization: Bearer <access_token>
```

**응답** (200 OK):
```json
{
  "total_transactions": 1523,
  "avg_risk_score": 32.5,
  "blocked_transactions": 45,
  "pending_reviews": 12,
  "risk_distribution": {
    "low": 1350,
    "medium": 128,
    "high": 45
  },
  "hourly_trend": [
    {
      "hour": "00:00",
      "transactions": 50,
      "avg_risk_score": 28
    }
  ]
}
```

---

## 검토 큐 API (`/v1/review`)

### 검토 대기 거래 조회

```http
GET /v1/review/queue?status=pending&priority=high
Authorization: Bearer <access_token>
```

**응답** (200 OK):
```json
{
  "data": [
    {
      "review_id": "review_123",
      "transaction_id": "txn_abc456",
      "risk_score": 95,
      "risk_level": "high",
      "user_info": {
        "user_id": "user_789",
        "email": "suspect@example.com",
        "account_age_days": 2
      },
      "transaction_info": {
        "amount": 500000,
        "items": ["고가 전자제품 x5"],
        "shipping_address": "서울시 강남구..."
      },
      "risk_factors": [...],
      "created_at": "2025-11-16T12:00:00Z",
      "priority": "high"
    }
  ],
  "pagination": {...}
}
```

---

### 거래 승인

```http
POST /v1/review/{review_id}/approve
Authorization: Bearer <access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "notes": "고객 확인 완료 - 정당한 거래로 판단",
  "notify_customer": true
}
```

**응답** (200 OK):
```json
{
  "review_id": "review_123",
  "status": "approved",
  "reviewed_by": "analyst_john",
  "reviewed_at": "2025-11-16T12:30:00Z"
}
```

---

### 거래 차단

```http
POST /v1/review/{review_id}/reject
Authorization: Bearer <access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "reason": "stolen_card",
  "notes": "카드 도용 확인 - 카드사 신고 완료",
  "block_user": true
}
```

**응답** (200 OK): 차단 결과

---

## 거래 내역 API (`/v1/transactions`)

### 전체 거래 조회

```http
GET /v1/transactions?risk_level=high&date_from=2025-11-01&date_to=2025-11-16
Authorization: Bearer <access_token>
```

**응답** (200 OK): 거래 목록 (페이지네이션 포함)

---

### 거래 상세 조회

```http
GET /v1/transactions/{transaction_id}
Authorization: Bearer <access_token>
```

**응답** (200 OK):
```json
{
  "transaction_id": "txn_abc456",
  "user_id": "user_789",
  "amount": 500000,
  "risk_score": 95,
  "risk_level": "high",
  "risk_factors": [...],
  "user_behavior_log": [
    {
      "timestamp": "2025-11-16T11:50:00Z",
      "action": "login",
      "ip": "203.0.113.50",
      "location": "Seoul"
    }
  ],
  "device_info": {...},
  "ml_prediction": {
    "model_version": "v1.3.0",
    "fraud_probability": 0.92,
    "confidence": 0.88
  }
}
```

---

## 탐지 룰 API (`/v1/rules`)

### 룰 목록 조회

```http
GET /v1/rules?status=active&type=velocity
Authorization: Bearer <access_token>
```

**응답** (200 OK):
```json
{
  "data": [
    {
      "rule_id": "rule_123",
      "name": "Velocity Check - 동일 카드 반복 결제",
      "type": "velocity",
      "description": "5분 내 동일 카드로 3회 이상 결제 시도",
      "conditions": {
        "time_window_minutes": 5,
        "max_attempts": 3,
        "match_field": "card_number"
      },
      "risk_score": 40,
      "status": "active",
      "created_at": "2025-11-10T10:00:00Z"
    }
  ]
}
```

---

### 룰 생성

**권한**: `SECURITY_MANAGER`

```http
POST /v1/rules
Authorization: Bearer <access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "name": "고액 거래 탐지",
  "type": "threshold",
  "description": "100만원 이상 거래 시 추가 인증",
  "conditions": {
    "amount_threshold": 1000000
  },
  "risk_score": 50,
  "status": "active"
}
```

**응답** (201 Created): 생성된 룰 정보

---

### 룰 활성화/비활성화

```http
PATCH /v1/rules/{rule_id}/status
Authorization: Bearer <access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "status": "inactive",
  "reason": "오탐률 높아 일시 비활성화"
}
```

**응답** (200 OK): 업데이트된 룰 정보

---

## A/B 테스트 API (`/v1/ab-tests`)

### A/B 테스트 목록 조회

```http
GET /v1/ab-tests?status=running
Authorization: Bearer <access_token>
```

**응답** (200 OK):
```json
{
  "data": [
    {
      "test_id": "ab_test_123",
      "name": "새 ML 모델 v2.0 테스트",
      "description": "LightGBM v2.0 vs v1.3.0 성능 비교",
      "status": "running",
      "group_a": {
        "description": "기존 모델 v1.3.0",
        "traffic_percentage": 80
      },
      "group_b": {
        "description": "새 모델 v2.0",
        "traffic_percentage": 20
      },
      "start_date": "2025-11-15T00:00:00Z",
      "end_date": "2025-11-22T23:59:59Z"
    }
  ]
}
```

---

### A/B 테스트 생성

**권한**: `SECURITY_MANAGER`

```http
POST /v1/ab-tests
Authorization: Bearer <access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "name": "새 Velocity 룰 테스트",
  "description": "3회 → 2회 임계값 변경 효과 검증",
  "group_a": {
    "description": "기존 룰 (3회)",
    "traffic_percentage": 80,
    "config": {"max_attempts": 3}
  },
  "group_b": {
    "description": "새 룰 (2회)",
    "traffic_percentage": 20,
    "config": {"max_attempts": 2}
  },
  "duration_days": 7
}
```

**응답** (201 Created): 생성된 A/B 테스트 정보

---

### A/B 테스트 결과 조회

```http
GET /v1/ab-tests/{test_id}/results
Authorization: Bearer <access_token>
```

**응답** (200 OK):
```json
{
  "test_id": "ab_test_123",
  "name": "새 ML 모델 v2.0 테스트",
  "status": "completed",
  "results": {
    "group_a": {
      "total_transactions": 4000,
      "blocked_transactions": 180,
      "true_positives": 165,
      "false_positives": 15,
      "precision": 0.92,
      "recall": 0.95,
      "f1_score": 0.935,
      "avg_evaluation_time_ms": 88
    },
    "group_b": {
      "total_transactions": 1000,
      "blocked_transactions": 50,
      "true_positives": 48,
      "false_positives": 2,
      "precision": 0.96,
      "recall": 0.96,
      "f1_score": 0.96,
      "avg_evaluation_time_ms": 82
    }
  },
  "recommendation": "deploy_group_b",
  "reason": "Group B가 정밀도(+4%), 평가 시간(-6ms) 모두 개선"
}
```

---

### A/B 테스트 상태 변경

```http
PATCH /v1/ab-tests/{test_id}/status
Authorization: Bearer <access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "status": "paused",
  "reason": "예상치 못한 오탐률 증가로 일시 중단"
}
```

**가능한 상태**: `draft`, `running`, `paused`, `completed`, `cancelled`

**응답** (200 OK): 업데이트된 A/B 테스트 정보

---

## 변경 이력

### v1.0.0 (2025-11-16)
- 초기 관리자 대시보드 API 릴리스
- 실시간 통계 대시보드
- 검토 큐 관리 (승인/차단)
- 탐지 룰 동적 관리
- A/B 테스트 설정 및 결과 분석
