# E2E 테스트 자동화 및 시스템 복원력 검증 - API 계약 문서

**Feature Branch**: `005-e2e-testing`
**Created**: 2025-11-20
**Version**: 1.0.0

## 개요

이 디렉토리는 E2E 테스트 자동화 및 시스템 복원력 검증 기능을 위한 API 계약(Contract) 문서를 포함합니다. 모든 API는 OpenAPI 3.0 사양을 준수하며, REST 방식으로 설계되었습니다.

## API 목록

### 1. E2E 테스트 관리 API
- **파일**: `e2e-tests-api.yaml`
- **베이스 URL**: `/api/v1/e2e`
- **설명**: Playwright 기반 E2E 테스트 시나리오 생성, 실행, 결과 조회
- **주요 엔드포인트**:
  - `POST /scenarios` - E2E 테스트 시나리오 생성
  - `GET /scenarios` - 시나리오 목록 조회
  - `GET /scenarios/{id}` - 시나리오 상세 조회
  - `PUT /scenarios/{id}` - 시나리오 수정
  - `DELETE /scenarios/{id}` - 시나리오 삭제
  - `POST /runs` - 테스트 실행 트리거
  - `GET /runs` - 실행 기록 목록 조회
  - `GET /runs/{id}` - 실행 결과 상세 조회
  - `GET /runs/{id}/screenshots` - 스크린샷 조회
  - `GET /runs/{id}/videos` - 비디오 녹화 조회

### 2. 카나리 배포 관리 API
- **파일**: `canary-deployment-api.yaml`
- **베이스 URL**: `/api/v1/canary`
- **설명**: Flagger 기반 카나리 배포 관리 및 트래픽 분할 제어
- **주요 엔드포인트**:
  - `POST /deployments` - 카나리 배포 시작
  - `GET /deployments` - 배포 목록 조회
  - `GET /deployments/{id}` - 배포 상세 조회
  - `PATCH /deployments/{id}/traffic` - 트래픽 비율 수동 조정
  - `POST /deployments/{id}/rollback` - 배포 롤백
  - `GET /deployments/{id}/metrics` - 실시간 메트릭 조회

### 3. Chaos Engineering 실험 API
- **파일**: `chaos-experiments-api.yaml`
- **베이스 URL**: `/api/v1/chaos`
- **설명**: Litmus Chaos 기반 장애 시뮬레이션 실험 관리
- **주요 엔드포인트**:
  - `POST /experiments` - 장애 실험 생성
  - `GET /experiments` - 실험 목록 조회
  - `GET /experiments/{id}` - 실험 상세 조회
  - `POST /experiments/{id}/start` - 실험 시작 (승인 필요)
  - `POST /experiments/{id}/stop` - 실험 중단
  - `GET /experiments/{id}/observations` - 관찰 결과 조회

### 4. 성능 테스트 관리 API
- **파일**: `performance-tests-api.yaml`
- **베이스 URL**: `/api/v1/performance`
- **설명**: k6 기반 성능 테스트 실행 및 메트릭 조회
- **주요 엔드포인트**:
  - `POST /tests` - 성능 테스트 실행 트리거
  - `GET /tests` - 테스트 목록 조회
  - `GET /tests/{id}` - 테스트 결과 상세 조회
  - `GET /tests/{id}/metrics` - 상세 메트릭 조회
  - `GET /tests/{id}/report` - HTML 리포트 조회

### 5. API 테스트 관리 API
- **파일**: `api-tests-api.yaml`
- **베이스 URL**: `/api/v1/api-tests`
- **설명**: Newman (Postman CLI) 기반 API 통합 테스트 관리
- **주요 엔드포인트**:
  - `POST /suites` - API 테스트 슈트 생성
  - `GET /suites` - 슈트 목록 조회
  - `GET /suites/{id}` - 슈트 상세 조회
  - `POST /runs` - Newman 실행 트리거
  - `GET /runs/{id}` - 실행 결과 상세 조회
  - `GET /runs/{id}/report` - Newman HTML 리포트 조회

## 인증 (Authentication)

모든 API는 JWT Bearer 토큰 인증을 사용합니다.

### 인증 방법

```http
Authorization: Bearer {JWT_TOKEN}
```

### 토큰 획득

```bash
# 1. 로그인 API로 토큰 획득
curl -X POST https://api.shopfds.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "devops@shopfds.com",
    "password": "your-password"
  }'

# 응답 예시:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 인증된 요청 예시

```bash
curl -X GET https://api.shopfds.com/api/v1/e2e/scenarios \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## 공통 응답 형식

### 성공 응답

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "회원가입부터 결제까지 전체 플로우",
    "status": "active"
  }
}
```

### 에러 응답

모든 에러는 다음 형식으로 반환됩니다:

```json
{
  "error": "ERROR_CODE",
  "message": "사람이 읽을 수 있는 에러 메시지",
  "details": {
    "field": "필드명",
    "additional_info": "추가 정보"
  }
}
```

## 에러 코드

| HTTP 상태 코드 | 에러 코드 | 설명 |
|---------------|----------|------|
| 400 | BAD_REQUEST | 잘못된 요청 (유효성 검사 실패) |
| 401 | UNAUTHORIZED | 인증 실패 (토큰 없음 또는 만료) |
| 403 | FORBIDDEN | 권한 없음 (역할 기반 접근 제어) |
| 404 | NOT_FOUND | 리소스를 찾을 수 없음 |
| 409 | CONFLICT | 리소스 충돌 (이미 존재하는 리소스) |
| 422 | UNPROCESSABLE_ENTITY | 처리할 수 없는 요청 (비즈니스 로직 위반) |
| 429 | TOO_MANY_REQUESTS | 요청 제한 초과 (Rate Limiting) |
| 500 | INTERNAL_SERVER_ERROR | 서버 내부 오류 |
| 503 | SERVICE_UNAVAILABLE | 서비스 사용 불가 (유지보수 등) |

## Rate Limiting (요청 제한)

### 일반 API
- **제한**: 100 requests/minute per user
- **헤더**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### 테스트 실행 API (POST 요청)
- **제한**: 10 requests/minute per user
- **이유**: 리소스 집약적인 작업 방지

### 예시

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1700500000
```

### 제한 초과 시

```json
{
  "error": "TOO_MANY_REQUESTS",
  "message": "요청 제한을 초과했습니다. 60초 후 다시 시도하세요.",
  "details": {
    "retry_after": 60
  }
}
```

## 페이지네이션

목록 조회 API는 다음 파라미터를 지원합니다:

- `limit`: 조회 개수 (기본값: 20, 최대: 100)
- `offset`: 시작 위치 (기본값: 0)

### 요청 예시

```bash
curl -X GET "https://api.shopfds.com/api/v1/e2e/scenarios?limit=20&offset=0" \
  -H "Authorization: Bearer {TOKEN}"
```

### 응답 예시

```json
{
  "scenarios": [...],
  "total": 50,
  "limit": 20,
  "offset": 0
}
```

## API 테스트 방법

### 1. Swagger UI 사용

각 환경에서 Swagger UI를 통해 API를 직접 테스트할 수 있습니다:

- **로컬**: http://localhost:8000/docs
- **Staging**: https://staging.shopfds.com/docs
- **Production**: https://api.shopfds.com/docs

### 2. Postman 사용

Postman 컬렉션을 사용하여 API를 테스트할 수 있습니다:

```bash
# OpenAPI YAML → Postman 컬렉션 변환
npx openapi-to-postmanv2 -s e2e-tests-api.yaml -o e2e-tests.postman_collection.json
```

### 3. cURL 사용

#### E2E 테스트 시나리오 생성

```bash
curl -X POST https://api.shopfds.com/api/v1/e2e/scenarios \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "회원가입부터 결제까지 전체 플로우",
    "test_type": "functional",
    "browser": "chromium",
    "viewport": {"width": 1920, "height": 1080},
    "steps": [
      {"action": "goto", "url": "http://localhost:3000/login"},
      {"action": "fill", "selector": "[data-testid=\"email\"]", "value": "test@example.com"}
    ],
    "expected_results": [
      {"type": "url", "value": "/dashboard"}
    ],
    "priority": "high",
    "tags": ["checkout", "payment"]
  }'
```

#### 카나리 배포 시작

```bash
curl -X POST https://api.shopfds.com/api/v1/canary/deployments \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "ecommerce-backend",
    "old_version": "v1.0.0",
    "new_version": "v1.1.0",
    "initial_traffic_weight": 10,
    "threshold_max_error_rate": 5.0,
    "threshold_max_response_time": 200
  }'
```

#### 장애 실험 생성

```bash
curl -X POST https://api.shopfds.com/api/v1/chaos/experiments \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "FDS Pod 무작위 종료 복원력 테스트",
    "experiment_type": "pod_delete",
    "target_service": "fds-backend",
    "hypothesis": "FDS Pod 종료 시 30초 이내 자동 복구됨",
    "steady_state_hypothesis": {"error_rate": "<5%"},
    "method": {"total_chaos_duration": "60", "chaos_interval": "10"},
    "duration_sec": 60,
    "environment": "staging",
    "approval_required": false
  }'
```

#### 성능 테스트 실행

```bash
curl -X POST https://api.shopfds.com/api/v1/performance/tests \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "test_type": "spike",
    "scenario_name": "블랙 프라이데이 시뮬레이션",
    "target_tps": 1000,
    "duration_sec": 300,
    "virtual_users": 100,
    "environment": "staging",
    "k6_script_path": "tests/performance/scenarios/black-friday.js",
    "thresholds": {
      "p95_response_time": 200,
      "error_rate": 5.0
    }
  }'
```

#### Newman 실행 트리거

```bash
curl -X POST https://api.shopfds.com/api/v1/api-tests/runs \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "suite_id": "aa0e8400-e29b-41d4-a716-446655440000",
    "environment": "staging",
    "iterations": 1,
    "bail": false
  }'
```

## CI/CD 통합

### GitHub Actions 예시

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Login and get token
        id: auth
        run: |
          TOKEN=$(curl -X POST https://staging.shopfds.com/api/v1/auth/login \
            -H "Content-Type: application/json" \
            -d '{"email":"${{ secrets.CI_USER_EMAIL }}","password":"${{ secrets.CI_USER_PASSWORD }}"}' \
            | jq -r '.access_token')
          echo "::set-output name=token::$TOKEN"

      - name: Trigger E2E Tests
        run: |
          curl -X POST https://staging.shopfds.com/api/v1/e2e/runs \
            -H "Authorization: Bearer ${{ steps.auth.outputs.token }}" \
            -H "Content-Type: application/json" \
            -d '{
              "scenario_ids": ["550e8400-e29b-41d4-a716-446655440000"],
              "environment": "staging",
              "browser": "chromium"
            }'
```

## 권한 체계 (RBAC)

### 역할별 권한

| API | 개발자 | QA | DevOps | SRE | Admin |
|-----|-------|-----|--------|-----|-------|
| E2E 테스트 조회 | [OK] | [OK] | [OK] | [OK] | [OK] |
| E2E 테스트 생성/수정 | [OK] | [OK] | [OK] | [OK] | [OK] |
| E2E 테스트 삭제 | | [OK] | [OK] | [OK] | [OK] |
| 카나리 배포 조회 | [OK] | [OK] | [OK] | [OK] | [OK] |
| 카나리 배포 시작 | | | [OK] | [OK] | [OK] |
| 카나리 배포 롤백 | | | [OK] | [OK] | [OK] |
| 장애 실험 조회 | [OK] | [OK] | [OK] | [OK] | [OK] |
| 장애 실험 생성 (Staging) | | | [OK] | [OK] | [OK] |
| 장애 실험 실행 (Production) | | | | [OK] | [OK] |
| 성능 테스트 조회 | [OK] | [OK] | [OK] | [OK] | [OK] |
| 성능 테스트 실행 | | [OK] | [OK] | [OK] | [OK] |
| API 테스트 조회 | [OK] | [OK] | [OK] | [OK] | [OK] |
| API 테스트 실행 | [OK] | [OK] | [OK] | [OK] | [OK] |

## 환경별 엔드포인트

### 로컬 개발 환경
- **베이스 URL**: http://localhost:8000/api
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Staging 환경
- **베이스 URL**: https://staging.shopfds.com/api
- **Swagger UI**: https://staging.shopfds.com/docs
- **ReDoc**: https://staging.shopfds.com/redoc

### Production 환경
- **베이스 URL**: https://api.shopfds.com/api
- **Swagger UI**: https://api.shopfds.com/docs (인증 필요)
- **ReDoc**: https://api.shopfds.com/redoc (인증 필요)

## 모범 사례 (Best Practices)

### 1. 비동기 작업 패턴

테스트 실행과 같은 장시간 작업은 비동기로 처리됩니다:

```bash
# 1단계: 실행 트리거 (202 Accepted)
curl -X POST /api/v1/e2e/runs -d '{...}'
# 응답: {"run_id": "abc123", "status": "pending"}

# 2단계: 상태 폴링 (주기적으로 조회)
curl -X GET /api/v1/e2e/runs/abc123
# 응답: {"status": "running", "progress": 50}

# 3단계: 완료 확인
curl -X GET /api/v1/e2e/runs/abc123
# 응답: {"status": "passed", "duration_ms": 180000}
```

### 2. 필터링 및 정렬

```bash
# 실패한 E2E 테스트만 조회
curl -X GET "/api/v1/e2e/runs?status=failed&limit=10"

# 특정 서비스의 카나리 배포 조회
curl -X GET "/api/v1/canary/deployments?service_name=ecommerce-backend"

# 최근 30일 성능 테스트 조회
curl -X GET "/api/v1/performance/tests?started_after=2025-10-20"
```

### 3. 멱등성 (Idempotency)

POST 요청에 `Idempotency-Key` 헤더를 사용하여 중복 실행 방지:

```bash
curl -X POST /api/v1/e2e/runs \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{...}'
```

### 4. 에러 처리

```javascript
// JavaScript 예시
async function triggerE2ETest(scenarioId) {
  try {
    const response = await fetch('/api/v1/e2e/runs', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ scenario_ids: [scenarioId] }),
    });

    if (!response.ok) {
      const error = await response.json();
      console.error(`에러 (${error.error}): ${error.message}`);
      return;
    }

    const result = await response.json();
    console.log('테스트 시작:', result.run_id);
  } catch (error) {
    console.error('네트워크 오류:', error);
  }
}
```

## 버전 관리

API 버전은 URL 경로에 포함됩니다 (예: `/api/v1/`).

- **현재 버전**: v1
- **이전 버전 지원**: v1은 최소 6개월간 지원
- **Breaking Changes**: 메이저 버전 업그레이드 시 (v2, v3 등)
- **Non-breaking Changes**: 마이너 버전 업그레이드 시 (필드 추가 등)

## 문의 및 지원

- **개발팀**: devops@shopfds.com
- **QA팀**: qa@shopfds.com
- **SRE팀**: sre@shopfds.com
- **문서**: https://docs.shopfds.com/e2e-testing
- **이슈 트래커**: https://github.com/shopfds/shopfds/issues

---

**마지막 업데이트**: 2025-11-20
**문서 버전**: 1.0.0
