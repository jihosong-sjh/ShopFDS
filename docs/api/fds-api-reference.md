# FDS API Reference

## Overview

ShopFDS Fraud Detection System API는 실시간 사기 거래 탐지를 위한 REST API입니다.

**Base URL**: `http://localhost:8001`

**API Version**: `v1.0.0`

**Documentation**:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
- OpenAPI JSON: `http://localhost:8001/openapi.json`

## Authentication

현재 버전에서는 내부 서비스 간 통신만 지원하므로 인증이 필요하지 않습니다.
향후 JWT 기반 인증이 추가될 예정입니다.

## Rate Limiting

API Rate Limiting이 적용되어 있습니다:
- **일반 엔드포인트**: 100 requests/minute
- **평가 엔드포인트**: 1000 requests/minute
- **메트릭 엔드포인트**: 제한 없음

## API Endpoints

### 1. Health & Monitoring

#### GET /health

**Description**: 서비스 헬스 체크

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-18T12:00:00Z",
  "service": "fds",
  "version": "1.0.0"
}
```

#### GET /metrics

**Description**: Prometheus 메트릭 수집

**Response**: Prometheus 형식의 메트릭

```
# HELP fds_evaluation_duration_seconds FDS 평가 소요 시간 (초)
# TYPE fds_evaluation_duration_seconds histogram
fds_evaluation_duration_seconds_bucket{engine_type="total",le="0.01"} 1234
...
```

### 2. Integrated Evaluation (통합 평가)

#### POST /v1/fds/evaluate

**Description**: 통합 FDS 평가 (모든 엔진 조합)

**Request Body**:
```json
{
  "transaction_id": "txn_1234567890",
  "user_id": "usr_9876543210",
  "amount": 150000,
  "currency": "KRW",
  "payment_method": "credit_card",
  "card_bin": "123456",
  "card_last4": "7890",
  "shipping_address": {
    "country": "KR",
    "city": "Seoul",
    "postal_code": "06234"
  },
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0...",
  "device_fingerprint": "fp_abcd1234",
  "behavior_data": {
    "mouse_movements": 150,
    "keypress_count": 50,
    "page_views": 5,
    "session_duration": 300
  },
  "email": "user@example.com",
  "phone": "+821012345678"
}
```

**Response**:
```json
{
  "transaction_id": "txn_1234567890",
  "risk_score": 55,
  "risk_level": "medium",
  "decision": "additional_auth_required",
  "requires_verification": true,
  "risk_factors": [
    {
      "factor": "new_device",
      "severity": "medium",
      "contribution": 15
    },
    {
      "factor": "unusual_amount",
      "severity": "low",
      "contribution": 10
    }
  ],
  "engine_results": {
    "fingerprint": {
      "score": 20,
      "matched_blacklist": false
    },
    "behavior": {
      "score": 15,
      "bot_probability": 0.12
    },
    "network": {
      "score": 10,
      "is_tor": false,
      "is_vpn": false,
      "is_proxy": false
    },
    "rule": {
      "score": 30,
      "matched_rules": ["RULE_003"]
    },
    "ml": {
      "score": 25,
      "anomaly_probability": 0.45
    }
  },
  "evaluation_time_ms": 85,
  "timestamp": "2025-11-18T12:00:00Z"
}
```

**Performance**: P95 < 100ms

### 3. Device Fingerprinting

#### POST /v1/fds/device-fingerprint

**Description**: 디바이스 핑거프린트 수집 및 분석

**Request Body**:
```json
{
  "user_id": "usr_9876543210",
  "fingerprint_data": {
    "canvas_hash": "a1b2c3d4e5f6...",
    "webgl_hash": "f6e5d4c3b2a1...",
    "audio_hash": "1a2b3c4d5e6f...",
    "screen_resolution": "1920x1080",
    "timezone": "Asia/Seoul",
    "language": "ko-KR",
    "platform": "Win32",
    "plugins": ["PDF Viewer", "Chrome PDF Plugin"],
    "fonts": ["Arial", "Malgun Gothic", "Segoe UI"]
  },
  "ip_address": "203.0.113.42"
}
```

**Response**:
```json
{
  "device_id": "dev_a1b2c3d4e5f6",
  "is_blacklisted": false,
  "risk_score": 20,
  "anomalies": [],
  "first_seen": "2025-11-01T10:00:00Z",
  "last_seen": "2025-11-18T12:00:00Z",
  "seen_count": 42
}
```

#### GET /v1/fds/device-fingerprint/{device_id}

**Description**: 디바이스 핑거프린트 조회

**Response**:
```json
{
  "device_id": "dev_a1b2c3d4e5f6",
  "first_seen": "2025-11-01T10:00:00Z",
  "last_seen": "2025-11-18T12:00:00Z",
  "seen_count": 42,
  "associated_users": ["usr_9876543210"],
  "risk_score": 20,
  "is_blacklisted": false
}
```

### 4. Behavior Pattern Analysis

#### POST /v1/fds/behavior-pattern

**Description**: 행동 패턴 분석 (봇 탐지)

**Request Body**:
```json
{
  "session_id": "ses_1234567890",
  "user_id": "usr_9876543210",
  "behavior_data": {
    "mouse_movements": [
      {"x": 100, "y": 200, "timestamp": 1000},
      {"x": 150, "y": 250, "timestamp": 1100}
    ],
    "key_presses": [
      {"key": "a", "timestamp": 2000},
      {"key": "b", "timestamp": 2100}
    ],
    "clicks": [
      {"x": 300, "y": 400, "timestamp": 3000}
    ],
    "page_views": [
      {"page": "/product/123", "timestamp": 0, "duration": 5000},
      {"page": "/cart", "timestamp": 5000, "duration": 3000}
    ]
  }
}
```

**Response**:
```json
{
  "session_id": "ses_1234567890",
  "bot_probability": 0.12,
  "risk_score": 15,
  "is_bot": false,
  "anomalies": [
    {
      "type": "fast_typing",
      "severity": "low",
      "description": "Typing speed: 150 WPM (avg: 40 WPM)"
    }
  ],
  "behavior_metrics": {
    "mouse_speed_avg": 250.5,
    "mouse_curvature": 0.42,
    "typing_speed_wpm": 150,
    "page_stay_duration_avg": 4000
  }
}
```

### 5. Network Analysis

#### POST /v1/fds/network-analysis

**Description**: 네트워크 분석 (TOR/VPN/Proxy 탐지)

**Request Body**:
```json
{
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0...",
  "headers": {
    "X-Forwarded-For": "203.0.113.42",
    "Accept-Language": "ko-KR,ko;q=0.9"
  }
}
```

**Response**:
```json
{
  "ip_address": "203.0.113.42",
  "is_tor": false,
  "is_vpn": false,
  "is_proxy": false,
  "is_hosting": false,
  "risk_score": 10,
  "geo_info": {
    "country": "KR",
    "city": "Seoul",
    "latitude": 37.5665,
    "longitude": 126.9780
  },
  "asn_info": {
    "asn": 4766,
    "organization": "Korea Telecom",
    "reputation": "good"
  },
  "anomalies": []
}
```

### 6. Fraud Rules

#### GET /v1/fds/rules

**Description**: 사기 탐지 룰 목록 조회

**Query Parameters**:
- `category` (optional): `payment` | `account` | `shipping`
- `is_active` (optional): `true` | `false`
- `skip` (optional): 페이지네이션 오프셋 (기본: 0)
- `limit` (optional): 페이지네이션 리미트 (기본: 100)

**Response**:
```json
{
  "total": 30,
  "rules": [
    {
      "id": "rule_001",
      "name": "Test Card Detection",
      "category": "payment",
      "description": "Detects test credit card numbers",
      "priority": 100,
      "action": "block",
      "is_active": true,
      "created_at": "2025-11-01T00:00:00Z"
    }
  ]
}
```

#### POST /v1/fds/rules

**Description**: 새 사기 탐지 룰 생성

**Request Body**:
```json
{
  "name": "High Amount First Purchase",
  "category": "payment",
  "description": "Blocks first purchase over 500,000 KRW",
  "conditions": {
    "is_first_purchase": true,
    "amount_gte": 500000
  },
  "priority": 80,
  "action": "manual_review",
  "is_active": true
}
```

**Response**:
```json
{
  "id": "rule_031",
  "name": "High Amount First Purchase",
  "category": "payment",
  "priority": 80,
  "action": "manual_review",
  "is_active": true,
  "created_at": "2025-11-18T12:00:00Z"
}
```

#### PUT /v1/fds/rules/{rule_id}

**Description**: 기존 룰 업데이트

#### DELETE /v1/fds/rules/{rule_id}

**Description**: 룰 삭제

### 7. Blacklist Management

#### GET /v1/fds/blacklist/device/{device_id}

**Description**: 디바이스 블랙리스트 조회

**Response**:
```json
{
  "device_id": "dev_a1b2c3d4e5f6",
  "is_blacklisted": true,
  "reason": "Multiple fraud attempts",
  "added_at": "2025-11-10T15:30:00Z",
  "expires_at": null
}
```

#### POST /v1/fds/blacklist

**Description**: 블랙리스트 등록

**Request Body**:
```json
{
  "entry_type": "device",
  "entry_value": "dev_a1b2c3d4e5f6",
  "reason": "Confirmed fraud",
  "expires_at": null
}
```

**Response**:
```json
{
  "id": "bl_1234567890",
  "entry_type": "device",
  "entry_value": "dev_a1b2c3d4e5f6",
  "reason": "Confirmed fraud",
  "added_at": "2025-11-18T12:00:00Z",
  "expires_at": null
}
```

#### DELETE /v1/fds/blacklist/{blacklist_id}

**Description**: 블랙리스트 해제

### 8. XAI (Explainable AI)

#### GET /v1/fds/xai/{transaction_id}

**Description**: 거래 차단 사유 설명 (SHAP/LIME 분석)

**Response**:
```json
{
  "transaction_id": "txn_1234567890",
  "risk_score": 85,
  "decision": "block",
  "explanation": {
    "method": "shap",
    "base_value": 50,
    "feature_contributions": [
      {
        "feature": "new_device",
        "value": "true",
        "contribution": +15,
        "impact": "high"
      },
      {
        "feature": "unusual_amount",
        "value": 500000,
        "contribution": +10,
        "impact": "medium"
      },
      {
        "feature": "is_vpn",
        "value": "true",
        "contribution": +20,
        "impact": "high"
      }
    ],
    "top_risk_factors": [
      "is_vpn",
      "new_device",
      "unusual_amount"
    ]
  },
  "visualization_data": {
    "waterfall_chart": [...],
    "force_plot": [...]
  },
  "computation_time_ms": 450
}
```

### 9. External Verification

#### POST /v1/fds/verify/email

**Description**: 이메일 검증 (EmailRep + HaveIBeenPwned)

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Response**:
```json
{
  "email": "user@example.com",
  "is_disposable": false,
  "is_pwned": false,
  "reputation_score": 80,
  "risk_level": "low",
  "details": {
    "domain_age_days": 7300,
    "suspicious_tld": false,
    "breach_count": 0
  }
}
```

#### POST /v1/fds/verify/phone

**Description**: 전화번호 검증 (Numverify)

**Request Body**:
```json
{
  "phone": "+821012345678"
}
```

**Response**:
```json
{
  "phone": "+821012345678",
  "is_valid": true,
  "country_code": "KR",
  "carrier": "SK Telecom",
  "line_type": "mobile",
  "risk_level": "low"
}
```

#### POST /v1/fds/verify/card-bin

**Description**: 카드 BIN 검증 (BinList)

**Request Body**:
```json
{
  "bin": "123456"
}
```

**Response**:
```json
{
  "bin": "123456",
  "brand": "Visa",
  "type": "credit",
  "issuer": "KB Kookmin Bank",
  "country": "KR",
  "risk_level": "low"
}
```

## Error Responses

### Standard Error Format

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid transaction ID format",
    "details": {
      "field": "transaction_id",
      "reason": "Must start with 'txn_'"
    }
  },
  "timestamp": "2025-11-18T12:00:00Z",
  "path": "/v1/fds/evaluate"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | 잘못된 요청 파라미터 |
| `UNAUTHORIZED` | 401 | 인증 실패 |
| `FORBIDDEN` | 403 | 권한 없음 |
| `NOT_FOUND` | 404 | 리소스 없음 |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate Limit 초과 |
| `INTERNAL_ERROR` | 500 | 서버 내부 오류 |
| `SERVICE_UNAVAILABLE` | 503 | 서비스 일시 중단 |
| `TIMEOUT` | 504 | 요청 타임아웃 |

## Performance Guidelines

### Response Times

| Endpoint | Target P95 | Target P99 |
|----------|------------|------------|
| `/v1/fds/evaluate` | < 100ms | < 200ms |
| `/v1/fds/device-fingerprint` | < 50ms | < 100ms |
| `/v1/fds/behavior-pattern` | < 50ms | < 100ms |
| `/v1/fds/network-analysis` | < 100ms | < 200ms |
| `/v1/fds/xai/{id}` | < 5000ms | < 10000ms |
| `/v1/fds/verify/*` | < 2000ms | < 5000ms |

### Request Limits

- **Max Request Size**: 1 MB
- **Timeout**: 30 seconds (except XAI: 60 seconds)
- **Concurrent Requests**: 1000

## Best Practices

1. **Batch Processing**: For bulk evaluations, use multiple parallel requests instead of sequential calls
2. **Caching**: Client-side caching recommended for device fingerprints (24h TTL)
3. **Error Handling**: Implement exponential backoff for 5xx errors
4. **Monitoring**: Track response times and error rates
5. **Fail-Open**: In case of FDS service failure, allow transactions (with logging)

## Changelog

### v1.0.0 (2025-11-18)
- Initial release
- Integrated evaluation endpoint
- Device fingerprinting
- Behavior pattern analysis
- Network analysis
- Fraud rules engine
- XAI explanations
- External verification APIs
- Prometheus metrics

## Support

For issues or questions:
- **Documentation**: `/docs` or `/redoc`
- **OpenAPI Spec**: `/openapi.json`
- **Health Check**: `/health`
- **GitHub Issues**: https://github.com/your-org/shopfds/issues
