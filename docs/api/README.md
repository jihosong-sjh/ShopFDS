# API 문서

ShopFDS 플랫폼의 모든 API 엔드포인트 문서입니다.

## 서비스별 API 문서

ShopFDS는 마이크로서비스 아키텍처를 기반으로 4개의 독립적인 서비스로 구성되어 있습니다.

### 1. 이커머스 플랫폼 API (포트: 8000)

**Swagger UI**: http://localhost:8000/docs
**ReDoc**: http://localhost:8000/redoc
**OpenAPI Spec**: http://localhost:8000/openapi.json

**주요 엔드포인트**:
- **인증** (`/v1/auth`): 회원가입, 로그인, 토큰 관리
- **상품** (`/v1/products`): 상품 조회, 검색, 카테고리별 필터링
- **장바구니** (`/v1/cart`): 장바구니 관리 (추가, 수정, 삭제)
- **주문** (`/v1/orders`): 주문 생성, 조회, 추적
- **관리자 상품** (`/v1/admin/products`): 상품 등록, 수정, 삭제, 재고 관리
- **관리자 주문** (`/v1/admin/orders`): 주문 관리, 상태 변경
- **관리자 회원** (`/v1/admin/users`): 회원 조회, 상태 관리
- **관리자 대시보드** (`/v1/admin/dashboard`): 매출 통계, 주문 현황

**상세 문서**: [ecommerce-api.md](./ecommerce-api.md)

---

### 2. FDS (Fraud Detection System) API (포트: 8001)

**Swagger UI**: http://localhost:8001/docs
**ReDoc**: http://localhost:8001/redoc
**OpenAPI Spec**: http://localhost:8001/openapi.json

**주요 엔드포인트**:
- **거래 평가** (`/v1/fds/evaluate`): 실시간 거래 위험도 평가 (목표: 100ms)
- **위협 인텔리전스** (`/v1/fds/threat`): CTI 데이터 조회 및 관리

**위험 수준 분류**:
- **Low (0-30점)**: 자동 승인
- **Medium (40-70점)**: 추가 인증 요구 (OTP, 생체인증)
- **High (80-100점)**: 자동 차단 + 수동 검토 큐 추가

**성능 목표**:
- P95 응답 시간: 100ms 이내
- 처리량: 1,000 TPS 이상

**상세 문서**: [fds-api.md](./fds-api.md)

---

### 3. ML 서비스 API (포트: 8002)

**Swagger UI**: http://localhost:8002/docs
**ReDoc**: http://localhost:8002/redoc
**OpenAPI Spec**: http://localhost:8002/openapi.json

**주요 엔드포인트**:
- **모델 학습** (`/v1/ml/train`): Isolation Forest, LightGBM 학습 시작
- **모델 평가** (`/v1/ml/models`): 모델 성능 비교, 조회
- **모델 배포** (`/v1/ml/deploy`): 스테이징/프로덕션 배포, 카나리 배포, 롤백

**ML 워크플로우**:
1. 데이터 전처리 및 특징 추출
2. 모델 학습 (비동기 백그라운드 작업)
3. 모델 평가 (Accuracy, Precision, Recall, F1 Score)
4. 카나리 배포 (10% → 25% → 50% → 100%)
5. 프로덕션 배포 또는 긴급 롤백

**상세 문서**: [ml-service-api.md](./ml-service-api.md)

---

### 4. 관리자 대시보드 API (포트: 8003)

**Swagger UI**: http://localhost:8003/docs
**ReDoc**: http://localhost:8003/redoc
**OpenAPI Spec**: http://localhost:8003/openapi.json

**주요 엔드포인트**:
- **대시보드** (`/v1/dashboard`): 실시간 거래 통계, 위험 점수 추이
- **검토 큐** (`/v1/review`): 수동 검토 대기 중인 거래 조회 및 승인/차단
- **거래 내역** (`/v1/transactions`): 전체 거래 조회, 필터링
- **탐지 룰** (`/v1/rules`): 룰 조회, 생성, 수정, 활성화/비활성화
- **A/B 테스트** (`/v1/ab-tests`): A/B 테스트 설정, 결과 조회

**보안팀 기능**:
- 실시간 알림 수신
- 고위험 거래 상세 분석
- 동적 룰 관리 (코드 배포 없이 즉시 적용)
- A/B 테스트를 통한 룰 효과 검증

**상세 문서**: [admin-dashboard-api.md](./admin-dashboard-api.md)

---

## API 게이트웨이 (Nginx)

모든 서비스는 Nginx API Gateway를 통해 통합되어 외부에 노출됩니다.

**게이트웨이 URL**: http://localhost (또는 https://your-domain.com)

**라우팅 규칙**:
- `/api/ecommerce/*` → 이커머스 플랫폼 (8000)
- `/api/fds/*` → FDS 서비스 (8001)
- `/api/ml/*` → ML 서비스 (8002)
- `/api/admin/*` → 관리자 대시보드 (8003)

**보안 기능**:
- HTTPS 종료 (SSL/TLS)
- Rate Limiting (API 남용 방지)
- 보안 헤더 추가
- CORS 정책 관리

**상세 설정**: [infrastructure/nginx/nginx.conf](../../infrastructure/nginx/nginx.conf)

---

## 인증 및 권한

### JWT 기반 인증

모든 API는 JWT(JSON Web Token) 기반 인증을 사용합니다.

**토큰 획득**:
```http
POST /v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}
```

**응답**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**API 호출 시 토큰 사용**:
```http
GET /v1/orders
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### RBAC (역할 기반 접근 제어)

**역할 (Role)**:
- `CUSTOMER`: 일반 고객 (주문, 장바구니 관리)
- `ADMIN`: 관리자 (상품 관리, 주문 관리, 회원 관리)
- `SECURITY_ANALYST`: 보안 분석가 (거래 검토, 대시보드 조회)
- `SECURITY_MANAGER`: 보안 매니저 (룰 관리, A/B 테스트, 검토 승인/차단)

**권한 (Permission)** 예시:
- `PRODUCT_CREATE`, `PRODUCT_READ`, `PRODUCT_UPDATE`, `PRODUCT_DELETE`
- `ORDER_CREATE`, `ORDER_READ`, `ORDER_READ_ALL`, `ORDER_UPDATE`
- `REVIEW_READ`, `REVIEW_APPROVE`, `REVIEW_REJECT`
- `RULE_CREATE`, `RULE_UPDATE`, `AB_TEST_MANAGE`

---

## API 공통 사양

### 요청 헤더

모든 API 요청은 다음 헤더를 포함해야 합니다:

```http
Content-Type: application/json
Authorization: Bearer <access_token>
X-Request-ID: <unique-request-id>  # 선택사항, 로그 추적용
```

### 응답 형식

#### 성공 응답 (200 OK)

```json
{
  "data": {
    // 응답 데이터
  },
  "meta": {
    "request_id": "req_1234567890",
    "timestamp": "2025-11-16T12:00:00Z"
  }
}
```

#### 페이지네이션 응답

```json
{
  "data": [...],
  "pagination": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  },
  "meta": {
    "request_id": "req_1234567890",
    "timestamp": "2025-11-16T12:00:00Z"
  }
}
```

#### 에러 응답 (4xx, 5xx)

```json
{
  "error": "validation_error",
  "message": "입력 데이터가 유효하지 않습니다.",
  "details": {
    "field": "email",
    "issue": "이메일 형식이 올바르지 않습니다."
  }
}
```

### HTTP 상태 코드

- `200 OK`: 요청 성공
- `201 Created`: 리소스 생성 성공
- `204 No Content`: 요청 성공, 응답 본문 없음
- `400 Bad Request`: 잘못된 요청 (입력 검증 실패)
- `401 Unauthorized`: 인증 실패 (토큰 없음 또는 만료)
- `403 Forbidden`: 권한 없음
- `404 Not Found`: 리소스 없음
- `409 Conflict`: 충돌 (예: 중복된 이메일)
- `429 Too Many Requests`: Rate Limit 초과
- `500 Internal Server Error`: 서버 내부 오류
- `503 Service Unavailable`: 서비스 일시 중단

---

## API 테스트

### Postman 컬렉션

각 서비스의 Postman 컬렉션을 제공합니다:

- [Ecommerce API.postman_collection.json](./postman/Ecommerce-API.postman_collection.json)
- [FDS API.postman_collection.json](./postman/FDS-API.postman_collection.json)
- [ML Service API.postman_collection.json](./postman/ML-Service-API.postman_collection.json)
- [Admin Dashboard API.postman_collection.json](./postman/Admin-Dashboard-API.postman_collection.json)

### cURL 예시

#### 회원가입
```bash
curl -X POST http://localhost:8000/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "name": "홍길동"
  }'
```

#### 상품 조회
```bash
curl -X GET http://localhost:8000/v1/products \
  -H "Authorization: Bearer <access_token>"
```

#### 거래 위험 평가 (FDS)
```bash
curl -X POST http://localhost:8001/v1/fds/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_123",
    "user_id": "user_456",
    "amount": 150000,
    "payment_method": "credit_card",
    "ip_address": "192.168.1.100",
    "device_info": {
      "user_agent": "Mozilla/5.0...",
      "device_type": "desktop"
    }
  }'
```

---

## API 변경 이력

### v1.0.0 (2025-11-16)
- 초기 API 릴리스
- 이커머스 플랫폼 API 구현
- FDS 실시간 평가 API 구현
- ML 모델 학습/배포 API 구현
- 관리자 대시보드 API 구현

---

## 지원 및 문의

API 사용 중 문제가 발생하거나 문의사항이 있으시면:

- **GitHub Issues**: [ShopFDS Issues](https://github.com/your-org/ShopFDS/issues)
- **개발자 문서**: [docs/](../../docs/)
- **아키텍처 문서**: [docs/architecture/](../architecture/)

---

## 라이선스

Copyright © 2025 ShopFDS Team. All rights reserved.
