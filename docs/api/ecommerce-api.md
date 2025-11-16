# 이커머스 플랫폼 API 문서

**Base URL**: `http://localhost:8000` (개발), `https://api.your-domain.com/api/ecommerce` (프로덕션)

**Version**: 1.0.0

**Swagger UI**: http://localhost:8000/docs

---

## 인증 API (`/v1/auth`)

### 회원가입

사용자 계정을 생성합니다.

```http
POST /v1/auth/signup
Content-Type: application/json
```

**요청 본문**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "name": "홍길동",
  "phone": "010-1234-5678"
}
```

**응답** (201 Created):
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "name": "홍길동",
  "created_at": "2025-11-16T12:00:00Z"
}
```

**에러**:
- `409 Conflict`: 이메일 중복
- `400 Bad Request`: 비밀번호 강도 불충분

---

### 로그인

JWT 액세스 토큰을 발급받습니다.

```http
POST /v1/auth/login
Content-Type: application/json
```

**요청 본문**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**응답** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "홍길동",
    "role": "customer"
  }
}
```

**에러**:
- `401 Unauthorized`: 이메일 또는 비밀번호 불일치

---

### 현재 사용자 조회

JWT 토큰으로 현재 로그인한 사용자 정보를 조회합니다.

```http
GET /v1/auth/me
Authorization: Bearer <access_token>
```

**응답** (200 OK):
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "name": "홍길동",
  "phone": "010-1234-5678",
  "role": "customer",
  "created_at": "2025-11-16T12:00:00Z"
}
```

---

## 상품 API (`/v1/products`)

### 상품 목록 조회

카테고리별 상품을 조회합니다. 페이지네이션 지원.

```http
GET /v1/products?category={category}&page={page}&page_size={size}
Authorization: Bearer <access_token>
```

**쿼리 파라미터**:
- `category` (선택): 카테고리 필터 (예: `electronics`, `fashion`)
- `page` (기본값: 1): 페이지 번호
- `page_size` (기본값: 20): 페이지당 항목 수

**응답** (200 OK):
```json
{
  "data": [
    {
      "product_id": "prod_123",
      "name": "무선 이어폰",
      "description": "노이즈 캔슬링 지원",
      "price": 89000,
      "category": "electronics",
      "stock": 150,
      "image_url": "https://cdn.example.com/images/prod_123.jpg",
      "created_at": "2025-11-10T10:00:00Z"
    }
  ],
  "pagination": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

---

### 상품 상세 조회

특정 상품의 상세 정보를 조회합니다.

```http
GET /v1/products/{product_id}
Authorization: Bearer <access_token>
```

**응답** (200 OK):
```json
{
  "product_id": "prod_123",
  "name": "무선 이어폰",
  "description": "노이즈 캔슬링 지원, Bluetooth 5.0, 배터리 24시간",
  "price": 89000,
  "category": "electronics",
  "stock": 150,
  "image_url": "https://cdn.example.com/images/prod_123.jpg",
  "created_at": "2025-11-10T10:00:00Z",
  "updated_at": "2025-11-15T14:00:00Z"
}
```

**에러**:
- `404 Not Found`: 상품 없음

---

### 상품 검색

상품명 또는 설명으로 검색합니다.

```http
GET /v1/products/search?q={query}&min_price={min}&max_price={max}
Authorization: Bearer <access_token>
```

**쿼리 파라미터**:
- `q` (필수): 검색 키워드
- `min_price` (선택): 최소 가격
- `max_price` (선택): 최대 가격

**응답**: 상품 목록과 동일

---

## 장바구니 API (`/v1/cart`)

### 장바구니 조회

현재 사용자의 장바구니를 조회합니다.

```http
GET /v1/cart
Authorization: Bearer <access_token>
```

**응답** (200 OK):
```json
{
  "cart_id": "cart_456",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "items": [
    {
      "cart_item_id": "item_789",
      "product_id": "prod_123",
      "product_name": "무선 이어폰",
      "price": 89000,
      "quantity": 2,
      "subtotal": 178000,
      "added_at": "2025-11-16T10:00:00Z"
    }
  ],
  "total_amount": 178000,
  "total_items": 2
}
```

---

### 장바구니에 상품 추가

```http
POST /v1/cart/items
Authorization: Bearer <access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "product_id": "prod_123",
  "quantity": 2
}
```

**응답** (201 Created):
```json
{
  "cart_item_id": "item_789",
  "product_id": "prod_123",
  "quantity": 2,
  "added_at": "2025-11-16T10:00:00Z"
}
```

**에러**:
- `400 Bad Request`: 재고 부족
- `404 Not Found`: 상품 없음

---

### 장바구니 항목 수량 변경

```http
PATCH /v1/cart/items/{cart_item_id}
Authorization: Bearer <access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "quantity": 3
}
```

**응답** (200 OK): 업데이트된 장바구니 조회 결과

---

### 장바구니 항목 삭제

```http
DELETE /v1/cart/items/{cart_item_id}
Authorization: Bearer <access_token>
```

**응답** (204 No Content)

---

## 주문 API (`/v1/orders`)

### 주문 생성 (장바구니에서 체크아웃)

장바구니의 모든 상품으로 주문을 생성하고, FDS 위험 평가를 수행합니다.

```http
POST /v1/orders
Authorization: Bearer <access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "shipping_name": "홍길동",
  "shipping_address": "서울특별시 강남구 테헤란로 123",
  "shipping_phone": "010-1234-5678",
  "payment_info": {
    "card_number": "1234567890123456",
    "card_expiry": "12/25",
    "card_cvv": "123"
  }
}
```

**응답** (201 Created):
```json
{
  "order_id": "order_abc123",
  "order_number": "ORD-20251116-0001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_amount": 178000,
  "status": "pending_payment",
  "fds_result": {
    "risk_score": 25,
    "risk_level": "low",
    "decision": "approved",
    "requires_verification": false
  },
  "shipping_info": {
    "name": "홍길동",
    "address": "서울특별시 강남구 테헤란로 123",
    "phone": "010-1234-5678"
  },
  "items": [
    {
      "product_id": "prod_123",
      "product_name": "무선 이어폰",
      "quantity": 2,
      "unit_price": 89000,
      "subtotal": 178000
    }
  ],
  "created_at": "2025-11-16T12:00:00Z"
}
```

**FDS 위험 수준별 응답**:

**Low Risk (0-30점)**: 자동 승인
```json
{
  "fds_result": {
    "risk_score": 25,
    "risk_level": "low",
    "decision": "approved",
    "requires_verification": false
  }
}
```

**Medium Risk (40-70점)**: 추가 인증 요구
```json
{
  "fds_result": {
    "risk_score": 55,
    "risk_level": "medium",
    "decision": "additional_auth_required",
    "requires_verification": true,
    "verification_methods": ["otp", "biometric"]
  }
}
```

**High Risk (80-100점)**: 자동 차단
```json
{
  "fds_result": {
    "risk_score": 95,
    "risk_level": "high",
    "decision": "blocked",
    "reason": "악성 IP 주소 탐지"
  }
}
```

**에러**:
- `400 Bad Request`: 장바구니 비어있음, 재고 부족
- `403 Forbidden`: 거래 차단

---

### OTP 검증 (추가 인증)

FDS가 추가 인증을 요구한 경우, OTP를 입력하여 주문을 완료합니다.

```http
POST /v1/orders/{order_id}/verify-otp
Authorization: Bearer <access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "otp_code": "123456"
}
```

**응답** (200 OK):
```json
{
  "verified": true,
  "order_status": "payment_approved",
  "message": "OTP 검증 성공. 주문이 승인되었습니다."
}
```

**에러**:
- `400 Bad Request`: OTP 불일치, 시도 횟수 초과
- `404 Not Found`: 주문 없음

---

### 주문 내역 조회

현재 사용자의 모든 주문을 조회합니다.

```http
GET /v1/orders?status={status}&page={page}&page_size={size}
Authorization: Bearer <access_token>
```

**쿼리 파라미터**:
- `status` (선택): 주문 상태 필터 (`pending`, `completed`, `cancelled`)
- `page`, `page_size`: 페이지네이션

**응답** (200 OK): 주문 목록 (페이지네이션 포함)

---

### 주문 상세 조회

```http
GET /v1/orders/{order_id}
Authorization: Bearer <access_token>
```

**응답** (200 OK): 주문 생성 응답과 동일 (추가로 배송 추적 정보 포함)

---

## 관리자 API

### 상품 관리 (`/v1/admin/products`)

**권한 필요**: `ADMIN` 역할

#### 상품 등록
```http
POST /v1/admin/products
Authorization: Bearer <admin_access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "name": "무선 이어폰",
  "description": "노이즈 캔슬링 지원",
  "price": 89000,
  "category": "electronics",
  "stock": 150,
  "image_url": "https://cdn.example.com/images/prod.jpg"
}
```

**응답** (201 Created): 생성된 상품 정보

---

#### 상품 수정
```http
PUT /v1/admin/products/{product_id}
Authorization: Bearer <admin_access_token>
Content-Type: application/json
```

**요청 본문**: 상품 등록과 동일 (모든 필드 필수)

**응답** (200 OK): 수정된 상품 정보

---

#### 상품 삭제
```http
DELETE /v1/admin/products/{product_id}
Authorization: Bearer <admin_access_token>
```

**응답** (204 No Content)

---

#### 재고 업데이트
```http
PATCH /v1/admin/products/{product_id}/stock
Authorization: Bearer <admin_access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "stock": 200
}
```

**응답** (200 OK): 업데이트된 상품 정보

---

### 주문 관리 (`/v1/admin/orders`)

**권한 필요**: `ADMIN` 역할

#### 전체 주문 조회
```http
GET /v1/admin/orders?status={status}&date_from={from}&date_to={to}
Authorization: Bearer <admin_access_token>
```

**쿼리 파라미터**:
- `status` (선택): 주문 상태 필터
- `date_from`, `date_to` (선택): 날짜 범위 필터

**응답** (200 OK): 주문 목록 (페이지네이션 포함)

---

#### 주문 상태 변경
```http
PATCH /v1/admin/orders/{order_id}/status
Authorization: Bearer <admin_access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "status": "shipping",
  "tracking_number": "1234567890"
}
```

**가능한 상태**:
- `pending` → `payment_approved` → `preparing` → `shipping` → `delivered` → `completed`
- 취소: `cancelled`

**응답** (200 OK): 업데이트된 주문 정보

---

### 회원 관리 (`/v1/admin/users`)

**권한 필요**: `ADMIN` 역할

#### 회원 목록 조회
```http
GET /v1/admin/users?status={status}&page={page}
Authorization: Bearer <admin_access_token>
```

**응답** (200 OK):
```json
{
  "data": [
    {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "name": "홍길동",
      "role": "customer",
      "status": "active",
      "created_at": "2025-11-16T12:00:00Z",
      "last_login": "2025-11-16T13:00:00Z"
    }
  ],
  "pagination": {...}
}
```

---

#### 회원 상태 변경
```http
PATCH /v1/admin/users/{user_id}/status
Authorization: Bearer <admin_access_token>
Content-Type: application/json
```

**요청 본문**:
```json
{
  "status": "suspended",
  "reason": "사기 의심 계정"
}
```

**가능한 상태**: `active`, `suspended`, `banned`

**응답** (200 OK): 업데이트된 회원 정보

---

### 대시보드 (`/v1/admin/dashboard`)

**권한 필요**: `ADMIN` 역할

#### 매출 통계 조회
```http
GET /v1/admin/dashboard/sales?period={period}&date_from={from}&date_to={to}
Authorization: Bearer <admin_access_token>
```

**쿼리 파라미터**:
- `period`: `daily`, `weekly`, `monthly`
- `date_from`, `date_to`: 날짜 범위

**응답** (200 OK):
```json
{
  "total_sales": 15000000,
  "total_orders": 250,
  "average_order_value": 60000,
  "daily_breakdown": [
    {
      "date": "2025-11-16",
      "sales": 500000,
      "orders": 10,
      "average_order_value": 50000
    }
  ]
}
```

---

## 에러 코드

| 코드 | 설명 |
|------|------|
| `validation_error` | 입력 데이터 검증 실패 |
| `authentication_failed` | 인증 실패 |
| `permission_denied` | 권한 없음 |
| `resource_not_found` | 리소스 없음 |
| `duplicate_email` | 이메일 중복 |
| `insufficient_stock` | 재고 부족 |
| `cart_empty` | 장바구니 비어있음 |
| `transaction_blocked` | 거래 차단 (FDS) |
| `otp_verification_failed` | OTP 검증 실패 |
| `internal_server_error` | 서버 내부 오류 |

---

## Rate Limiting

API 남용을 방지하기 위해 Rate Limiting이 적용됩니다:

- **인증 API**: 분당 10회
- **일반 API**: 분당 60회
- **관리자 API**: 분당 100회

초과 시 `429 Too Many Requests` 응답.

---

## 변경 이력

### v1.0.0 (2025-11-16)
- 초기 API 릴리스
- 인증, 상품, 장바구니, 주문 API 구현
- 관리자 API (상품, 주문, 회원, 대시보드) 구현
- FDS 통합 (주문 생성 시 실시간 위험 평가)
- OTP 추가 인증 기능 구현
