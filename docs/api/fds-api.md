# FDS API 문서

**Base URL**: `http://localhost:8001` (개발), `https://api.your-domain.com/api/fds` (프로덕션)

**Version**: 1.0.0

**Swagger UI**: http://localhost:8001/docs

**성능 목표**: P95 응답 시간 100ms 이내, 1,000 TPS 처리

---

## 거래 평가 API (`/v1/fds/evaluate`)

### 실시간 거래 위험도 평가

이커머스 플랫폼에서 호출하여 거래의 위험도를 평가합니다.

```http
POST /v1/fds/evaluate
Content-Type: application/json
X-API-Key: <fds_api_key>  # 내부 서비스 간 인증
```

**요청 본문**:
```json
{
  "transaction_id": "txn_abc123",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "order_id": "order_def456",
  "amount": 178000,
  "payment_method": "credit_card",
  "ip_address": "192.168.1.100",
  "device_info": {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "device_type": "desktop",
    "screen_resolution": "1920x1080"
  },
  "geo_location": {
    "country": "KR",
    "city": "Seoul",
    "latitude": 37.5665,
    "longitude": 126.9780
  },
  "session_info": {
    "session_id": "sess_789",
    "login_time": "2025-11-16T12:00:00Z",
    "pages_viewed": 15,
    "time_on_site": 1200
  }
}
```

**응답** (200 OK):
```json
{
  "transaction_id": "txn_abc123",
  "risk_score": 55,
  "risk_level": "medium",
  "decision": "additional_auth_required",
  "requires_verification": true,
  "verification_methods": ["otp", "biometric"],
  "risk_factors": [
    {
      "type": "location_mismatch",
      "score": 20,
      "description": "등록된 주소와 IP 위치 불일치 (서울 vs 부산)"
    },
    {
      "type": "high_amount",
      "score": 15,
      "description": "평균 거래 금액(50,000원) 대비 3.5배 높음"
    },
    {
      "type": "ml_anomaly",
      "score": 20,
      "description": "ML 모델이 비정상 패턴 탐지 (신뢰도: 0.85)"
    }
  ],
  "engine_breakdown": {
    "rule_engine": {
      "score": 35,
      "triggered_rules": ["location_mismatch", "high_amount"]
    },
    "ml_engine": {
      "score": 20,
      "model_version": "v1.2.0",
      "confidence": 0.85
    },
    "cti_engine": {
      "score": 0,
      "threat_found": false
    }
  },
  "evaluation_time_ms": 85,
  "evaluated_at": "2025-11-16T12:00:00.085Z"
}
```

**위험 수준 (risk_level)과 결정 (decision)**:

| 위험 점수 | 위험 수준 | 결정 (decision) | 설명 |
|-----------|-----------|-----------------|------|
| 0-30 | `low` | `approved` | 자동 승인 |
| 40-70 | `medium` | `additional_auth_required` | 추가 인증 요구 (OTP, 생체인증) |
| 80-100 | `high` | `blocked` | 자동 차단 + 수동 검토 큐 추가 |

**성능 지표**:
```json
{
  "evaluation_time_ms": 85,
  "engine_breakdown": {
    "rule_engine_ms": 15,
    "ml_engine_ms": 45,
    "cti_engine_ms": 25
  }
}
```

**에러**:
- `400 Bad Request`: 필수 필드 누락
- `503 Service Unavailable`: FDS 일시 장애 (Fail-open 정책 적용)

---

## 위협 인텔리전스 API (`/v1/fds/threat`)

### 악성 IP 조회

```http
GET /v1/fds/threat/ip/{ip_address}
X-API-Key: <fds_api_key>
```

**응답** (200 OK):
```json
{
  "ip_address": "192.168.1.100",
  "is_malicious": false,
  "threat_level": "low",
  "last_checked": "2025-11-16T12:00:00Z"
}
```

**악성 IP 응답**:
```json
{
  "ip_address": "203.0.113.50",
  "is_malicious": true,
  "threat_level": "high",
  "sources": ["AbuseIPDB", "ThreatIntel DB"],
  "first_reported": "2025-11-10T08:00:00Z",
  "last_checked": "2025-11-16T12:00:00Z"
}
```

---

### 위협 정보 등록

```http
POST /v1/fds/threat/report
X-API-Key: <fds_api_key>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "type": "ip",
  "value": "203.0.113.50",
  "threat_level": "high",
  "source": "manual_review",
  "notes": "반복적인 사기 시도 탐지"
}
```

**응답** (201 Created): 등록된 위협 정보

---

## A/B 테스트 통합

FDS는 A/B 테스트를 지원하여 새로운 룰이나 ML 모델의 효과를 검증합니다.

**A/B 테스트 활성 시 응답**:
```json
{
  "transaction_id": "txn_abc123",
  "risk_score": 55,
  "ab_test_info": {
    "test_id": "ab_test_123",
    "group": "A",
    "test_name": "새로운 ML 모델 v2.0 테스트"
  }
}
```

- **Group A**: 기존 룰/모델 적용
- **Group B**: 새로운 룰/모델 적용

결과는 관리자 대시보드에서 집계되어 비교됩니다.

---

## 모니터링 및 성능 지표

FDS는 모든 평가에 대해 성능 지표를 수집합니다:

- **평균 응답 시간** (P50, P95, P99)
- **처리량** (TPS)
- **엔진별 기여도** (룰 기반, ML 기반, CTI)
- **위험 수준별 분포** (Low, Medium, High)

Prometheus 메트릭으로 노출되어 Grafana 대시보드에서 시각화됩니다.

---

## Fail-Open 정책

FDS 장애 시에도 이커머스 거래가 중단되지 않도록 Fail-Open 정책을 적용합니다:

1. FDS가 타임아웃(200ms)되면 기본 위험 점수 30점 (low) 반환
2. 모든 거래를 사후 검토 큐에 추가하여 나중에 분석
3. 장애 복구 후 자동으로 정상 평가 재개

**Fail-Open 응답 예시**:
```json
{
  "transaction_id": "txn_abc123",
  "risk_score": 30,
  "risk_level": "low",
  "decision": "approved",
  "fallback_mode": true,
  "reason": "FDS temporary unavailable - basic validation applied",
  "queued_for_review": true
}
```

---

## 변경 이력

### v1.0.0 (2025-11-16)
- 초기 FDS API 릴리스
- 실시간 거래 위험도 평가 (룰 + ML + CTI)
- A/B 테스트 지원
- Fail-Open 정책 구현
- 성능 목표 달성 (P95 85ms, 1,000 TPS)
