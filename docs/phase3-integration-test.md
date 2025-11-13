# Phase 3: 기본 FDS 통합 테스트 (T047-T050)

**날짜**: 2025-11-13
**목표**: 정상 거래 시나리오에서 FDS가 올바르게 작동하는지 검증

---

## 구현 완료 항목

### ✅ T047: Transaction 모델 생성
- **파일**: `services/fds/src/models/transaction.py`
- **내용**:
  - Transaction 모델 정의 (위험 점수, 위험 수준, 평가 상태)
  - DeviceType, RiskLevel, EvaluationStatus Enum
  - 위험 수준 자동 분류 로직

### ✅ T048: 기본 FDS 평가 엔드포인트 구현
- **파일**:
  - `services/fds/src/api/evaluation.py`
  - `services/fds/src/engines/evaluation_engine.py`
  - `services/fds/src/models/schemas.py`
- **내용**:
  - POST /internal/fds/evaluate 엔드포인트
  - 기본 평가 엔진 (룰 기반)
  - 위험 요인 평가 및 점수 산정
  - Pydantic 스키마 (요청/응답)

### ✅ T049: 이커머스 백엔드에서 FDS 서비스 비동기 호출 통합
- **파일**: `services/ecommerce/backend/src/services/order_service.py`
- **내용**:
  - OrderService에 FDS 평가 호출 통합
  - FDS 계약에 맞는 요청 데이터 구성
  - Fail-Open 정책 구현 (타임아웃/에러 시 자동 승인)
  - 디바이스 타입 자동 추출 (User-Agent 기반)

### ✅ T050: 정상 거래 시나리오 검증
- **파일**: `services/fds/tests/test_evaluation_api.py`
- **내용**:
  - 정상 거래 자동 승인 테스트
  - 고액 거래 자동 승인 테스트
  - 알 수 없는 디바이스 자동 승인 테스트

---

## 서비스 실행 방법

### 1. 데이터베이스 준비

```bash
# PostgreSQL 실행 확인
docker-compose up -d postgres

# Redis 실행 확인
docker-compose up -d redis
```

### 2. FDS 서비스 실행

```bash
cd services/fds

# 가상환경 활성화 (이미 생성된 경우)
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
# MINGW64
source venv/Scripts/activate

# 의존성 설치
pip install -r requirements.txt

# FDS 서비스 실행 (포트 8001)
python src/main.py
```

**확인**: http://localhost:8001/docs 에서 Swagger UI 확인

### 3. 이커머스 서비스 실행

```bash
cd services/ecommerce/backend

# 가상환경 활성화
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 이커머스 서비스 실행 (포트 8000)
python src/main.py
```

**확인**: http://localhost:8000/docs 에서 Swagger UI 확인

---

## 테스트 실행

### 1. FDS 단위 테스트

```bash
cd services/fds

# pytest로 FDS 평가 API 테스트
python tests/test_evaluation_api.py
```

**예상 출력**:
```
============================================================
FDS 정상 거래 시나리오 검증 (T050)
============================================================

✓ 정상 거래 자동 승인 테스트 통과
  - 위험 점수: 10
  - 평가 시간: 5ms

✓ 고액 거래 자동 승인 테스트 통과
  - 위험 점수: 25

✓ 알 수 없는 디바이스 자동 승인 테스트 통과
  - 위험 점수: 20

============================================================
✓ 모든 테스트 통과!
============================================================
```

### 2. 수동 테스트 (Swagger UI)

#### FDS 서비스 직접 호출

1. http://localhost:8001/docs 접속
2. `POST /internal/fds/evaluate` 엔드포인트 선택
3. "Try it out" 클릭
4. 요청 데이터 입력:

```json
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "order_id": "789e0123-e45b-67c8-d901-234567890123",
  "amount": 50000.00,
  "currency": "KRW",
  "ip_address": "211.234.56.78",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
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
  "session_context": null,
  "timestamp": "2025-11-13T14:30:00Z"
}
```

5. 헤더 추가:
   - `X-Service-Token`: `dev-service-token-12345`

6. "Execute" 클릭

**예상 응답**:
```json
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "risk_score": 10,
  "risk_level": "low",
  "decision": "approve",
  "risk_factors": [
    {
      "factor_type": "normal_transaction",
      "factor_score": 10,
      "description": "정상 범위 내 거래",
      "severity": "info"
    }
  ],
  "evaluation_metadata": {
    "evaluation_time_ms": 5,
    "rule_engine_time_ms": 5,
    "ml_engine_time_ms": null,
    "cti_check_time_ms": null,
    "timestamp": "2025-11-13T14:30:00.005Z"
  },
  "recommended_action": {
    "action": "approve",
    "reason": "위험 점수가 낮은 정상 거래 (점수: 10)",
    "additional_auth_required": false
  }
}
```

---

## 검증 기준

### 성공 기준

- [x] **위험 점수**: 정상 거래의 경우 0-30점
- [x] **위험 수준**: "low"
- [x] **의사결정**: "approve" (자동 승인)
- [x] **평가 시간**: 100ms 이내
- [x] **응답 형식**: FDS 계약(fds-contract.md)에 따름
- [x] **Fail-Open 정책**: FDS 에러 시 거래 승인

### 테스트 시나리오

| 시나리오 | 거래 금액 | 디바이스 | 예상 위험 점수 | 예상 결정 |
|---------|----------|---------|--------------|----------|
| 정상 거래 | 50,000원 | desktop | 10 | approve |
| 고액 거래 | 1,500,000원 | desktop | 25 | approve |
| 알 수 없는 디바이스 | 50,000원 | unknown | 20 | approve |

---

## 데이터베이스 확인

### Transaction 테이블 확인

```sql
-- FDS 서비스 DB 접속
psql -h localhost -U shopfds -d shopfds_dev

-- Transaction 테이블 조회
SELECT
    id,
    order_id,
    risk_score,
    risk_level,
    evaluation_status,
    evaluation_time_ms,
    created_at
FROM transactions
ORDER BY created_at DESC
LIMIT 10;
```

**예상 결과**:
```
                  id                  |               order_id               | risk_score | risk_level | evaluation_status | evaluation_time_ms |      created_at
--------------------------------------+--------------------------------------+------------+------------+-------------------+--------------------+---------------------
 550e8400-e29b-41d4-a716-446655440000 | 789e0123-e45b-67c8-d901-234567890123 |         10 | low        | approved          |                  5 | 2025-11-13 14:30:00
```

---

## 다음 단계 (Phase 4)

Phase 3 완료 후 다음 단계로 진행:

1. **Phase 4: 사용자 스토리 2 - 의심 거래 시 단계적 인증**
   - T051-T066: 룰 엔진 강화 (Velocity Check, 금액 임계값, 지역 불일치)
   - OTP 추가 인증 메커니즘 구현
   - 중간 위험도 거래 시나리오 검증

2. **Phase 5: 사용자 스토리 3 - 고위험 거래 자동 차단**
   - T067-T085: CTI 연동 (악성 IP 검증)
   - 보안팀 대시보드 구현
   - 수동 검토 큐 구현

---

## 문제 해결

### FDS 서비스 연결 실패

**증상**: 이커머스 서비스에서 주문 생성 시 FDS 연결 에러

**해결**:
1. FDS 서비스가 실행 중인지 확인 (http://localhost:8001/health)
2. config.py의 FDS_SERVICE_URL 확인
3. 서비스 토큰 확인 (X-Service-Token 헤더)

### 평가 시간 100ms 초과

**증상**: evaluation_time_ms > 100

**해결**:
- Phase 3에서는 기본 룰만 평가하므로 일반적으로 10ms 이내
- ML 엔진과 CTI 통합 후(Phase 5-6)에는 최적화 필요

---

## 요약

✅ **T047-T050 완료**: 기본 FDS 통합 구현 완료
✅ **정상 거래 시나리오**: 위험 점수 0-30점, 자동 승인
✅ **성능 목표**: 평가 시간 100ms 이내 달성
✅ **Fail-Open 정책**: FDS 장애 시 거래 승인

이제 Phase 4로 진행하여 룰 엔진을 강화하고 추가 인증 메커니즘을 구현할 수 있습니다.
