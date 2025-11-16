# ML 서비스 API 문서

**Base URL**: `http://localhost:8002` (개발)

**Version**: 1.0.0

**Swagger UI**: http://localhost:8002/docs

---

## 모델 학습 API (`/v1/ml/train`)

### 모델 학습 시작

Isolation Forest 또는 LightGBM 모델 학습을 시작합니다.

```http
POST /v1/ml/train
X-API-Key: <ml_api_key>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "model_type": "lightgbm",
  "data_period": {
    "start_date": "2025-10-01",
    "end_date": "2025-11-15"
  },
  "hyperparameters": {
    "max_depth": 7,
    "learning_rate": 0.1,
    "n_estimators": 100
  }
}
```

**모델 타입**:
- `isolation_forest`: Isolation Forest (이상 탐지)
- `lightgbm`: LightGBM (분류)

**응답** (202 Accepted):
```json
{
  "job_id": "job_abc123",
  "status": "started",
  "model_type": "lightgbm",
  "estimated_duration_minutes": 15,
  "started_at": "2025-11-16T12:00:00Z"
}
```

---

### 학습 상태 조회

```http
GET /v1/ml/train/status/{job_id}
X-API-Key: <ml_api_key>
```

**응답** (200 OK):
```json
{
  "job_id": "job_abc123",
  "status": "completed",
  "model_type": "lightgbm",
  "model_id": "model_v1.3.0",
  "progress": 100,
  "metrics": {
    "accuracy": 0.96,
    "precision": 0.94,
    "recall": 0.95,
    "f1_score": 0.945
  },
  "started_at": "2025-11-16T12:00:00Z",
  "completed_at": "2025-11-16T12:12:35Z",
  "duration_minutes": 12.58
}
```

**상태 값**:
- `started`: 학습 시작
- `running`: 학습 진행 중
- `completed`: 학습 완료
- `failed`: 학습 실패

---

### 학습 히스토리 조회

```http
GET /v1/ml/train/history?limit=10
X-API-Key: <ml_api_key>
```

**응답** (200 OK): 학습 작업 목록

---

## 모델 평가 API (`/v1/ml/models`)

### 모델 목록 조회

```http
GET /v1/ml/models?status=production&model_type=lightgbm
X-API-Key: <ml_api_key>
```

**응답** (200 OK):
```json
{
  "models": [
    {
      "model_id": "model_v1.3.0",
      "model_name": "LightGBM v1.3.0",
      "model_type": "lightgbm",
      "version": "1.3.0",
      "status": "production",
      "metrics": {
        "accuracy": 0.96,
        "precision": 0.94,
        "recall": 0.95,
        "f1_score": 0.945
      },
      "trained_at": "2025-11-16T12:00:00Z",
      "deployed_at": "2025-11-16T14:00:00Z"
    }
  ]
}
```

---

### 모델 비교

두 개 이상의 모델 성능을 비교합니다.

```http
POST /v1/ml/models/compare
X-API-Key: <ml_api_key>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "model_ids": ["model_v1.2.0", "model_v1.3.0"]
}
```

**응답** (200 OK):
```json
{
  "comparison": [
    {
      "model_id": "model_v1.2.0",
      "accuracy": 0.94,
      "precision": 0.92,
      "recall": 0.93,
      "f1_score": 0.925
    },
    {
      "model_id": "model_v1.3.0",
      "accuracy": 0.96,
      "precision": 0.94,
      "recall": 0.95,
      "f1_score": 0.945
    }
  ],
  "winner": "model_v1.3.0",
  "improvement": {
    "accuracy": 0.02,
    "f1_score": 0.02
  }
}
```

---

## 모델 배포 API (`/v1/ml/deploy`)

### 스테이징 환경 배포

```http
POST /v1/ml/deploy/staging
X-API-Key: <ml_api_key>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "model_id": "model_v1.3.0"
}
```

**응답** (200 OK):
```json
{
  "model_id": "model_v1.3.0",
  "environment": "staging",
  "deployed_at": "2025-11-16T14:00:00Z",
  "status": "active"
}
```

---

### 카나리 배포 시작

프로덕션 트래픽의 일부에만 새 모델을 적용합니다.

```http
POST /v1/ml/deploy/canary/start
X-API-Key: <ml_api_key>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "model_id": "model_v1.3.0",
  "initial_traffic_percentage": 10,
  "monitoring_duration_minutes": 30
}
```

**응답** (202 Accepted):
```json
{
  "canary_id": "canary_xyz789",
  "model_id": "model_v1.3.0",
  "current_traffic_percentage": 10,
  "status": "monitoring",
  "started_at": "2025-11-16T14:00:00Z"
}
```

---

### 카나리 배포 상태 조회

```http
GET /v1/ml/deploy/canary/{canary_id}/status
X-API-Key: <ml_api_key>
```

**응답** (200 OK):
```json
{
  "canary_id": "canary_xyz789",
  "model_id": "model_v1.3.0",
  "current_traffic_percentage": 10,
  "status": "monitoring",
  "metrics": {
    "new_model": {
      "accuracy": 0.96,
      "avg_response_time_ms": 42
    },
    "old_model": {
      "accuracy": 0.94,
      "avg_response_time_ms": 45
    }
  },
  "recommendation": "proceed",
  "reason": "새 모델이 성능 향상을 보임 (정확도 +2%, 응답 시간 -3ms)"
}
```

---

### 카나리 배포 트래픽 증가

```http
POST /v1/ml/deploy/canary/{canary_id}/increase-traffic
X-API-Key: <ml_api_key>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "target_percentage": 25
}
```

**점진적 롤아웃**: 10% → 25% → 50% → 100%

---

### 프로덕션 배포 (100%)

```http
POST /v1/ml/deploy/production
X-API-Key: <ml_api_key>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "model_id": "model_v1.3.0"
}
```

**응답** (200 OK):
```json
{
  "model_id": "model_v1.3.0",
  "environment": "production",
  "traffic_percentage": 100,
  "deployed_at": "2025-11-16T16:00:00Z"
}
```

---

### 긴급 롤백

성능 저하 시 이전 모델로 즉시 롤백합니다.

```http
POST /v1/ml/deploy/rollback/emergency
X-API-Key: <ml_api_key>
```

**응답** (200 OK):
```json
{
  "rolled_back_to": "model_v1.2.0",
  "reason": "긴급 롤백 - 현재 프로덕션 모델 문제 발생",
  "rolled_back_at": "2025-11-16T16:05:00Z"
}
```

---

### 특정 버전 롤백

```http
POST /v1/ml/deploy/rollback
X-API-Key: <ml_api_key>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "model_id": "model_v1.2.0",
  "reason": "v1.3.0의 오탐률이 높아 이전 버전으로 복귀"
}
```

**응답** (200 OK): 롤백된 모델 정보

---

## 변경 이력

### v1.0.0 (2025-11-16)
- 초기 ML 서비스 API 릴리스
- 모델 학습 (Isolation Forest, LightGBM)
- 모델 평가 및 비교
- 카나리 배포 (10% → 100%)
- 긴급 롤백 기능
