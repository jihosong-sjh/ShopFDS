# FDS 내부 계약 명세

**Version**: 1.0.0
**Purpose**: 이커머스 서비스와 FDS 서비스 간 내부 통신 계약

## 1. 개요

FDS 서비스는 이커머스 플랫폼에서 발생하는 모든 거래를 실시간으로 평가하여 사기 여부를 판단합니다. 본 문서는 두 서비스 간의 통신 프로토콜, 데이터 형식, 응답 시간 SLA를 정의합니다.

---

## 2. 아키텍처 통신 흐름

```
[고객] → [이커머스 Frontend] → [이커머스 Backend]
                                        ↓
                                [주문 생성 API]
                                        ↓
                               [FDS 평가 요청] → [FDS Service]
                                        ↓              ↓
                                [Rule Engine] + [ML Engine] + [CTI Check]
                                        ↓              ↓
                               [위험 점수 산정]  ← [Redis Cache]
                                        ↓
                               [자동 대응 결정]
                                        ↓
                    [결과 반환: approve/additional_auth/blocked]
                                        ↓
                               [이커머스 Backend]
                                        ↓
                     [주문 완료 / 추가 인증 요청 / 차단 처리]
```

---

## 3. FDS 평가 요청 (Request)

### Endpoint

```
POST /internal/fds/evaluate
Content-Type: application/json
X-Service-Token: <서비스 간 인증 토큰>
```

### Request Body

```json
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "order_id": "789e0123-e45b-67c8-d901-234567890123",
  "amount": 249900.00,
  "currency": "KRW",
  "ip_address": "203.0.113.45",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "device_fingerprint": {
    "device_type": "desktop",
    "os": "Windows 10",
    "browser": "Chrome 120.0"
  },
  "shipping_info": {
    "name": "홍길동",
    "address": "서울특별시 강남구 테헤란로 123",
    "phone": "010-1234-5678"
  },
  "payment_info": {
    "method": "credit_card",
    "card_bin": "541234",
    "card_last_four": "5678"
  },
  "session_context": {
    "session_id": "abc123-session-xyz789",
    "session_duration_seconds": 320,
    "pages_visited": 8,
    "products_viewed": 3,
    "cart_additions": 2
  },
  "timestamp": "2025-11-13T14:30:00Z"
}
```

### 필수 필드 검증

| 필드 | 타입 | 제약 조건 |
|------|------|-----------|
| `transaction_id` | UUID | NOT NULL, 중복 방지 (멱등성) |
| `user_id` | UUID | NOT NULL |
| `order_id` | UUID | NOT NULL |
| `amount` | Decimal | > 0 |
| `ip_address` | String (IPv4/IPv6) | NOT NULL |
| `timestamp` | ISO 8601 | NOT NULL, 현재 시각 ±5분 이내 (시각 동기화 검증) |

---

## 4. FDS 평가 응답 (Response)

### 성공 응답 (200 OK)

```json
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "risk_score": 35,
  "risk_level": "low",
  "decision": "approve",
  "risk_factors": [
    {
      "factor_type": "velocity_check",
      "factor_score": 10,
      "description": "정상 범위 내 거래 빈도",
      "severity": "info"
    },
    {
      "factor_type": "ml_anomaly",
      "factor_score": 25,
      "description": "사용자 행동 패턴이 약간 다르지만 허용 범위",
      "severity": "low",
      "model_version": "IsolationForest-v1.2"
    }
  ],
  "evaluation_metadata": {
    "evaluation_time_ms": 87,
    "rule_engine_time_ms": 12,
    "ml_engine_time_ms": 45,
    "cti_check_time_ms": 30,
    "timestamp": "2025-11-13T14:30:00.087Z"
  },
  "recommended_action": {
    "action": "approve",
    "reason": "위험 점수가 낮은 정상 거래",
    "additional_auth_required": false
  }
}
```

### 중간 위험 응답 (추가 인증 필요)

```json
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "risk_score": 55,
  "risk_level": "medium",
  "decision": "additional_auth_required",
  "risk_factors": [
    {
      "factor_type": "location_mismatch",
      "factor_score": 40,
      "description": "등록된 주소(서울)와 IP 위치(부산) 불일치",
      "severity": "medium"
    },
    {
      "factor_type": "amount_threshold",
      "factor_score": 15,
      "description": "평소 구매 패턴 대비 1.8배 높은 금액",
      "severity": "low"
    }
  ],
  "evaluation_metadata": {
    "evaluation_time_ms": 92,
    "timestamp": "2025-11-13T14:30:00.092Z"
  },
  "recommended_action": {
    "action": "additional_auth_required",
    "reason": "지역 불일치 및 비정상 금액 패턴 감지",
    "additional_auth_required": true,
    "auth_methods": ["otp_sms", "biometric"],
    "auth_timeout_seconds": 300
  }
}
```

### 고위험 응답 (자동 차단)

```json
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "risk_score": 92,
  "risk_level": "high",
  "decision": "blocked",
  "risk_factors": [
    {
      "factor_type": "suspicious_ip",
      "factor_score": 50,
      "description": "AbuseIPDB에서 악성 IP로 등록됨 (신고 횟수: 127)",
      "severity": "high",
      "source": "AbuseIPDB"
    },
    {
      "factor_type": "velocity_check",
      "factor_score": 42,
      "description": "동일 IP에서 5분 내 5회 거래 시도 (임계값: 3회)",
      "severity": "high"
    }
  ],
  "evaluation_metadata": {
    "evaluation_time_ms": 78,
    "timestamp": "2025-11-13T14:30:00.078Z"
  },
  "recommended_action": {
    "action": "blocked",
    "reason": "악성 IP 및 비정상적인 거래 빈도 감지",
    "additional_auth_required": false,
    "manual_review_required": true,
    "review_queue_id": "queue-123e4567-e89b-12d3"
  }
}
```

### 에러 응답 (5xx)

```json
{
  "error_code": "FDS_SERVICE_UNAVAILABLE",
  "message": "FDS 서비스 일시 장애",
  "details": {
    "fallback_strategy": "fail_open",
    "action": "approve_with_review",
    "reason": "FDS 장애 시 거래 중단 방지, 사후 검토 큐에 추가"
  }
}
```

**Fail-Open 정책**: FDS 서비스 장애 시 거래를 승인하되, 모든 거래를 사후 검토 큐에 추가하여 안전성 유지.

---

## 5. 의사결정 (Decision) 타입

| Decision | Risk Score | 설명 | 이커머스 서비스 동작 |
|----------|------------|------|---------------------|
| `approve` | 0-30 | 위험도 낮음, 자동 승인 | 주문 즉시 완료 |
| `additional_auth_required` | 40-70 | 위험도 중간, 추가 인증 필요 | OTP/생체인증 요청, 인증 성공 시 주문 완료 |
| `blocked` | 80-100 | 위험도 높음, 자동 차단 | 주문 차단, 보안팀에 알림, 수동 검토 큐에 추가 |

---

## 6. 위험 요인 (Risk Factor) 타입

| factor_type | 설명 | 일반적인 점수 범위 |
|-------------|------|------------------|
| `velocity_check` | 단시간 내 반복 거래 | 0-50 |
| `amount_threshold` | 평소 대비 비정상 금액 | 0-40 |
| `location_mismatch` | 지역 불일치 | 0-40 |
| `suspicious_ip` | CTI 블랙리스트 IP | 0-50 |
| `suspicious_time` | 비정상 시간대 거래 (예: 새벽 3시) | 0-20 |
| `ml_anomaly` | ML 모델 이상 탐지 | 0-60 |
| `stolen_card` | 도난 카드 정보 | 0-50 |

**총 위험 점수 산정**:
```
risk_score = min(100, sum(factor_score * weight))
```
- `weight`: 각 요인의 중요도 가중치 (설정 가능)
- 최대값 100으로 정규화

---

## 7. 성능 SLA

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| **응답 시간 (P95)** | 100ms | `evaluation_metadata.evaluation_time_ms` |
| **응답 시간 (P99)** | 150ms | 동일 |
| **처리량** | 1,000 TPS | 초당 요청 수 |
| **가용성** | 99.9% | 월 최대 다운타임 43분 |

**타임아웃 설정**:
- 이커머스 서비스 → FDS 서비스: 200ms 타임아웃
- 타임아웃 시 Fail-Open 정책 적용

---

## 8. 캐싱 전략

### Redis 캐싱 대상

1. **CTI 결과** (IP, 카드 BIN):
   ```
   Key: threat:ip:{ip_address}
   TTL: 1시간
   Value: {threat_level: "high", source: "AbuseIPDB"}
   ```

2. **Velocity Check 카운터**:
   ```
   Key: velocity:ip:{ip_address}
   TTL: 5분
   Value: 3  (거래 횟수)
   ```

3. **ML 모델 예측 결과** (동일 패턴):
   ```
   Key: ml:prediction:{user_id}:{feature_hash}
   TTL: 10분
   Value: {score: 0.25, model_version: "v1.2"}
   ```

---

## 9. 보안

### 서비스 간 인증

```http
X-Service-Token: <HMAC-SHA256 서명된 JWT>
```

- 토큰 유효 기간: 1시간
- 이커머스 서비스와 FDS 서비스만 공유하는 Secret Key 사용
- 요청 시각 검증 (Replay Attack 방지)

### 데이터 보안

- **전송 중 암호화**: TLS 1.3 (내부 서비스 간에도 적용)
- **민감 정보 로그 금지**: 카드 번호, 비밀번호 등은 로그에 기록하지 않음
- **IP 주소 해싱**: 장기 저장 시 SHA-256 해싱 (GDPR 준수)

---

## 10. 모니터링 및 알림

### 메트릭 수집 (Prometheus)

```yaml
# FDS 평가 시간 히스토그램
fds_evaluation_duration_seconds{service="fds", decision="approve"}

# 위험 점수 분포
fds_risk_score_distribution{risk_level="low|medium|high"}

# 의사결정 분포
fds_decision_count{decision="approve|additional_auth|blocked"}

# 에러율
fds_error_rate{error_type="timeout|service_unavailable"}
```

### 알림 조건

| 조건 | 심각도 | 알림 채널 |
|------|--------|----------|
| P95 응답 시간 > 150ms (5분 이상) | Warning | Slack |
| 에러율 > 5% (1분 이상) | Critical | PagerDuty + Slack |
| 차단 건수 급증 (평소 대비 3배) | Warning | Slack |
| FDS 서비스 다운 | Critical | PagerDuty + SMS |

---

## 11. 테스트 시나리오

### 단위 테스트 (FDS 서비스)

```python
def test_low_risk_transaction():
    request = {
        "user_id": "normal-user-123",
        "amount": 50000,
        "ip_address": "211.234.56.78",
        "timestamp": datetime.utcnow().isoformat()
    }
    response = fds_service.evaluate(request)
    assert response["risk_score"] < 30
    assert response["decision"] == "approve"
    assert response["evaluation_metadata"]["evaluation_time_ms"] < 100
```

### 통합 테스트 (E2E)

```python
def test_high_risk_transaction_blocked():
    # 악성 IP로 거래 시도
    response = ecommerce_api.create_order(
        user_id="test-user",
        ip_address="203.0.113.1",  # 블랙리스트 IP
        amount=500000
    )
    assert response.status_code == 403
    assert response.json()["error_code"] == "TRANSACTION_BLOCKED"

    # FDS 검토 큐에 추가되었는지 확인
    review_queue = admin_api.get_review_queue()
    assert len(review_queue) > 0
```

### 성능 테스트

```bash
# Locust로 1,000 TPS 부하 테스트
locust -f fds_load_test.py --users 1000 --spawn-rate 100
```

**통과 기준**:
- P95 응답 시간 < 100ms
- 에러율 < 1%

---

## 12. 버전 관리

### API 버전 정책

- **Major Version**: 하위 호환성이 깨지는 변경 (예: 필수 필드 추가)
- **Minor Version**: 하위 호환성 유지 (예: 선택 필드 추가, 응답 필드 추가)

### Deprecation 정책

1. **공지**: 6개월 전 공지 (릴리스 노트, 이메일)
2. **병행 운영**: 3개월간 구버전과 신버전 동시 지원
3. **종료**: 구버전 종료 (에러 응답으로 전환)

**현재 버전**: v1.0.0 (2025-11-13)

---

## 다음 단계

✅ FDS 내부 계약 명세 완료
→ 다음: ML 모델 학습 파이프라인 계약 (ml-contract.md)
