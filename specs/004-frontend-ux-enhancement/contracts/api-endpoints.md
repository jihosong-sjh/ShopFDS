# API 엔드포인트: 프론트엔드 UX 고도화

**Feature**: 004-frontend-ux-enhancement
**작성일**: 2025-11-19
**Base URL**: `https://api.shopfds.com`
**API Version**: v1

## 개요

프론트엔드 UX 고도화를 위한 REST API 엔드포인트 명세입니다.

**신규 API 그룹**:
1. **검색 API** (`/v1/search`): 자동완성, 검색 결과, 필터링
2. **리뷰 API** (`/v1/reviews`): 리뷰 CRUD, 투표, 정렬/필터
3. **위시리스트 API** (`/v1/wishlist`): 찜 목록 관리
4. **배송지 API** (`/v1/addresses`): 배송지 CRUD, 기본 배송지 설정
5. **쿠폰 API** (`/v1/coupons`): 쿠폰 조회, 발급, 사용
6. **OAuth API** (`/v1/auth/oauth`): 소셜 로그인 (Google, Kakao, Naver)
7. **추천 API** (`/v1/recommendations`): 추천 상품, 최근 본 상품

---

## 1. 검색 API

### 1.1 자동완성

**GET** `/v1/search/autocomplete`

**설명**: 검색어 2글자 이상 입력 시 상품명, 브랜드, 카테고리 자동완성 제안

**쿼리 파라미터**:
- `q` (required): 검색어 (2글자 이상)
- `limit` (optional): 결과 개수 (기본값: 10, 최대: 20)

**응답 예시**:
```json
{
  "suggestions": [
    {
      "type": "product",
      "text": "아이폰 15 Pro",
      "product_id": "uuid",
      "image_url": "https://..."
    },
    {
      "type": "brand",
      "text": "Apple"
    },
    {
      "type": "category",
      "text": "스마트폰"
    }
  ]
}
```

---

### 1.2 상품 검색

**GET** `/v1/search/products`

**설명**: 검색어 + 필터로 상품 검색

**쿼리 파라미터**:
- `q` (required): 검색어
- `category` (optional): 카테고리 ID
- `brand` (optional): 브랜드 이름
- `min_price` (optional): 최소 가격
- `max_price` (optional): 최대 가격
- `in_stock` (optional): 재고 있는 상품만 (`true`/`false`)
- `sort` (optional): 정렬 (`popular`, `price_asc`, `price_desc`, `newest`, `rating`)
- `page` (optional): 페이지 번호 (기본값: 1)
- `limit` (optional): 페이지당 개수 (기본값: 20)

**응답 예시**:
```json
{
  "products": [
    {
      "id": "uuid",
      "name": "아이폰 15 Pro 256GB",
      "price": 1490000,
      "discounted_price": 1390000,
      "images": ["https://...", "https://..."],
      "brand": "Apple",
      "category": "스마트폰",
      "rating": 4.8,
      "review_count": 1284,
      "in_stock": true
    }
  ],
  "total_count": 142,
  "page": 1,
  "total_pages": 8,
  "filters_applied": {
    "query": "아이폰",
    "brand": "Apple",
    "min_price": 1000000,
    "max_price": 2000000
  }
}
```

---

### 1.3 최근 검색어 저장

**POST** `/v1/search/history`

**설명**: 사용자 검색어 기록 저장 (로그인 사용자만)

**요청 Body**:
```json
{
  "query": "아이폰 15"
}
```

**응답**:
```json
{
  "message": "검색어가 저장되었습니다"
}
```

---

## 2. 리뷰 API

### 2.1 상품 리뷰 목록 조회

**GET** `/v1/products/{product_id}/reviews`

**설명**: 특정 상품의 리뷰 목록

**쿼리 파라미터**:
- `rating` (optional): 별점 필터 (1-5)
- `has_photos` (optional): 사진 리뷰만 (`true`/`false`)
- `sort` (optional): 정렬 (`recent`, `rating_desc`, `rating_asc`, `helpful`)
- `page` (optional): 페이지 번호
- `limit` (optional): 페이지당 개수 (기본값: 10)

**응답 예시**:
```json
{
  "reviews": [
    {
      "id": "uuid",
      "user": {
        "id": "uuid",
        "name": "홍길동",
        "masked_name": "홍**"
      },
      "rating": 5,
      "title": "정말 만족합니다",
      "content": "배송도 빠르고 상품도 좋아요...",
      "images": ["https://...", "https://..."],
      "helpful_count": 42,
      "is_verified_purchase": true,
      "is_helpful_by_me": false,
      "created_at": "2025-11-15T10:30:00Z"
    }
  ],
  "total_count": 1284,
  "average_rating": 4.8,
  "rating_distribution": {
    "5": 856,
    "4": 312,
    "3": 85,
    "2": 21,
    "1": 10
  },
  "page": 1,
  "total_pages": 129
}
```

---

### 2.2 리뷰 작성

**POST** `/v1/reviews`

**설명**: 리뷰 작성 (구매 확정 고객만)

**요청 Body**:
```json
{
  "product_id": "uuid",
  "order_id": "uuid",
  "rating": 5,
  "title": "정말 만족합니다",
  "content": "배송도 빠르고 상품도 좋아요",
  "images": ["https://...", "https://..."]  // 최대 3장
}
```

**응답**:
```json
{
  "id": "uuid",
  "message": "리뷰가 작성되었습니다"
}
```

**오류**:
- `400 Bad Request`: 이미 리뷰 작성함, 구매하지 않은 상품
- `401 Unauthorized`: 로그인 필요

---

### 2.3 리뷰 수정

**PUT** `/v1/reviews/{review_id}`

**설명**: 본인이 작성한 리뷰 수정

**요청 Body**:
```json
{
  "rating": 4,
  "title": "수정된 제목",
  "content": "수정된 내용",
  "images": ["https://..."]
}
```

---

### 2.4 리뷰 삭제

**DELETE** `/v1/reviews/{review_id}`

**설명**: 본인이 작성한 리뷰 삭제

**응답**:
```json
{
  "message": "리뷰가 삭제되었습니다"
}
```

---

### 2.5 리뷰 "도움돼요" 투표

**POST** `/v1/reviews/{review_id}/vote`

**설명**: 리뷰에 "도움돼요" 투표 (중복 투표 불가)

**응답**:
```json
{
  "message": "투표가 완료되었습니다",
  "helpful_count": 43
}
```

**오류**:
- `400 Bad Request`: 이미 투표함
- `401 Unauthorized`: 로그인 필요

---

### 2.6 리뷰 "도움돼요" 취소

**DELETE** `/v1/reviews/{review_id}/vote`

**설명**: "도움돼요" 투표 취소

**응답**:
```json
{
  "message": "투표가 취소되었습니다",
  "helpful_count": 42
}
```

---

## 3. 위시리스트 API

### 3.1 위시리스트 조회

**GET** `/v1/wishlist`

**설명**: 사용자 위시리스트 목록

**쿼리 파라미터**:
- `page` (optional): 페이지 번호
- `limit` (optional): 페이지당 개수 (기본값: 20)

**응답 예시**:
```json
{
  "items": [
    {
      "id": "uuid",
      "product": {
        "id": "uuid",
        "name": "갤럭시 S24 Ultra",
        "price": 1690000,
        "discounted_price": 1590000,
        "image_url": "https://...",
        "in_stock": true,
        "rating": 4.7,
        "review_count": 856
      },
      "added_at": "2025-11-10T14:20:00Z"
    }
  ],
  "total_count": 12
}
```

---

### 3.2 위시리스트에 추가

**POST** `/v1/wishlist`

**요청 Body**:
```json
{
  "product_id": "uuid"
}
```

**응답**:
```json
{
  "id": "uuid",
  "message": "위시리스트에 추가되었습니다"
}
```

**오류**:
- `400 Bad Request`: 이미 위시리스트에 있음
- `404 Not Found`: 상품 없음

---

### 3.3 위시리스트에서 삭제

**DELETE** `/v1/wishlist/{item_id}`

**응답**:
```json
{
  "message": "위시리스트에서 삭제되었습니다"
}
```

---

### 3.4 여러 상품 한 번에 장바구니 담기

**POST** `/v1/wishlist/move-to-cart`

**요청 Body**:
```json
{
  "item_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**응답**:
```json
{
  "message": "3개 상품이 장바구니에 추가되었습니다",
  "success_count": 3,
  "failed_items": []
}
```

---

## 4. 배송지 API

### 4.1 배송지 목록 조회

**GET** `/v1/addresses`

**응답 예시**:
```json
{
  "addresses": [
    {
      "id": "uuid",
      "address_name": "집",
      "recipient_name": "홍길동",
      "phone": "010-1234-5678",
      "zipcode": "12345",
      "address": "서울특별시 강남구 테헤란로 123",
      "address_detail": "아파트 101동 1001호",
      "is_default": true,
      "created_at": "2025-01-01T00:00:00Z"
    },
    {
      "id": "uuid",
      "address_name": "회사",
      "recipient_name": "홍길동",
      "phone": "010-1234-5678",
      "zipcode": "54321",
      "address": "서울특별시 중구 세종대로 110",
      "address_detail": "빌딩 5층",
      "is_default": false,
      "created_at": "2025-01-05T00:00:00Z"
    }
  ]
}
```

---

### 4.2 배송지 추가

**POST** `/v1/addresses`

**요청 Body**:
```json
{
  "address_name": "새 배송지",
  "recipient_name": "홍길동",
  "phone": "010-1234-5678",
  "zipcode": "12345",
  "address": "서울특별시 강남구 테헤란로 123",
  "address_detail": "아파트 101동 1001호",
  "is_default": false
}
```

**응답**:
```json
{
  "id": "uuid",
  "message": "배송지가 추가되었습니다"
}
```

---

### 4.3 배송지 수정

**PUT** `/v1/addresses/{address_id}`

**요청 Body**: (추가와 동일)

---

### 4.4 배송지 삭제

**DELETE** `/v1/addresses/{address_id}`

**응답**:
```json
{
  "message": "배송지가 삭제되었습니다"
}
```

**오류**:
- `400 Bad Request`: 기본 배송지는 삭제 불가 (다른 배송지를 기본으로 설정 후 삭제)

---

### 4.5 기본 배송지 설정

**POST** `/v1/addresses/{address_id}/set-default`

**응답**:
```json
{
  "message": "기본 배송지로 설정되었습니다"
}
```

---

## 5. 쿠폰 API

### 5.1 사용자 쿠폰 목록 조회

**GET** `/v1/coupons/me`

**쿼리 파라미터**:
- `status` (optional): `available` (사용 가능), `used` (사용 완료), `expired` (만료)

**응답 예시**:
```json
{
  "coupons": [
    {
      "id": "uuid",
      "coupon_code": "WELCOME2025",
      "coupon_name": "신규 회원 환영 쿠폰",
      "description": "첫 구매 시 사용 가능",
      "discount_type": "PERCENT",
      "discount_value": 10,
      "max_discount_amount": 10000,
      "min_purchase_amount": 50000,
      "valid_from": "2025-01-01T00:00:00Z",
      "valid_until": "2025-12-31T23:59:59Z",
      "issued_at": "2025-01-10T10:00:00Z",
      "used_at": null,
      "is_usable": true,
      "reason": ""
    },
    {
      "id": "uuid",
      "coupon_code": "SPRING5000",
      "coupon_name": "봄맞이 5천원 할인",
      "discount_type": "FIXED",
      "discount_value": 5000,
      "min_purchase_amount": 30000,
      "valid_until": "2025-05-31T23:59:59Z",
      "issued_at": "2025-03-01T00:00:00Z",
      "used_at": null,
      "is_usable": true,
      "reason": ""
    }
  ]
}
```

---

### 5.2 쿠폰 코드로 발급받기

**POST** `/v1/coupons/issue`

**요청 Body**:
```json
{
  "coupon_code": "WELCOME2025"
}
```

**응답**:
```json
{
  "id": "uuid",
  "message": "쿠폰이 발급되었습니다"
}
```

**오류**:
- `400 Bad Request`: 존재하지 않는 쿠폰, 이미 발급받음, 사용 횟수 초과
- `401 Unauthorized`: 로그인 필요

---

### 5.3 쿠폰 사용 가능 여부 확인

**POST** `/v1/coupons/validate`

**요청 Body**:
```json
{
  "coupon_code": "WELCOME2025",
  "order_amount": 80000
}
```

**응답**:
```json
{
  "is_valid": true,
  "discount_amount": 8000,
  "final_amount": 72000,
  "message": ""
}
```

**오류 응답**:
```json
{
  "is_valid": false,
  "discount_amount": 0,
  "final_amount": 80000,
  "message": "최소 구매 금액 50,000원 이상이어야 합니다"
}
```

---

## 6. OAuth API

### 6.1 Google 로그인 시작

**GET** `/v1/auth/oauth/google`

**설명**: Google OAuth 인증 URL로 리다이렉트

**응답**: HTTP 302 Redirect to Google

---

### 6.2 Google 로그인 콜백

**GET** `/v1/auth/oauth/google/callback`

**쿼리 파라미터**:
- `code`: Google Authorization Code
- `state`: CSRF 방지 토큰

**응답**:
```json
{
  "access_token": "jwt_token",
  "refresh_token": "jwt_refresh_token",
  "user": {
    "id": "uuid",
    "email": "user@gmail.com",
    "name": "홍길동",
    "avatar_url": "https://..."
  }
}
```

---

### 6.3 Kakao 로그인

**GET** `/v1/auth/oauth/kakao`
**GET** `/v1/auth/oauth/kakao/callback`

(Google과 동일한 플로우)

---

### 6.4 Naver 로그인

**GET** `/v1/auth/oauth/naver`
**GET** `/v1/auth/oauth/naver/callback`

(Google과 동일한 플로우)

---

## 7. 추천 API

### 7.1 추천 상품 조회

**GET** `/v1/recommendations/for-you`

**설명**: 사용자 맞춤 추천 상품 (로그인 사용자: 협업 필터링, 비로그인: 인기 상품)

**쿼리 파라미터**:
- `limit` (optional): 추천 개수 (기본값: 10)

**응답 예시**:
```json
{
  "products": [
    {
      "id": "uuid",
      "name": "에어팟 프로 2세대",
      "price": 359000,
      "discounted_price": 329000,
      "image_url": "https://...",
      "rating": 4.9,
      "review_count": 2341
    }
  ],
  "algorithm": "collaborative_filtering"  // 또는 "popular"
}
```

---

### 7.2 최근 본 상품 조회

**GET** `/v1/recommendations/recently-viewed`

**설명**: 최근 본 상품 (프론트엔드 LocalStorage + 백엔드 동기화)

**응답 예시**:
```json
{
  "products": [
    {
      "id": "uuid",
      "name": "아이폰 15 Pro",
      "price": 1490000,
      "image_url": "https://...",
      "viewed_at": "2025-11-18T15:30:00Z"
    }
  ]
}
```

---

### 7.3 최근 본 상품 저장

**POST** `/v1/recommendations/recently-viewed`

**요청 Body**:
```json
{
  "product_id": "uuid"
}
```

**응답**:
```json
{
  "message": "최근 본 상품에 추가되었습니다"
}
```

---

### 7.4 연관 상품 조회

**GET** `/v1/products/{product_id}/related`

**설명**: 같은 카테고리의 유사 상품

**쿼리 파라미터**:
- `limit` (optional): 추천 개수 (기본값: 8)

**응답 예시**:
```json
{
  "products": [
    {
      "id": "uuid",
      "name": "갤럭시 S24 Ultra",
      "price": 1690000,
      "image_url": "https://...",
      "rating": 4.7,
      "review_count": 856
    }
  ]
}
```

---

## 인증 및 오류 처리

### 인증

모든 보호된 엔드포인트는 JWT Bearer Token 필요:

```
Authorization: Bearer {access_token}
```

### 공통 오류 응답

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "로그인이 필요합니다",
    "details": {}
  }
}
```

**HTTP 상태 코드**:
- `200 OK`: 성공
- `201 Created`: 생성 성공
- `400 Bad Request`: 잘못된 요청
- `401 Unauthorized`: 인증 필요
- `403 Forbidden`: 권한 없음
- `404 Not Found`: 리소스 없음
- `409 Conflict`: 중복 (이미 존재)
- `422 Unprocessable Entity`: 검증 실패
- `500 Internal Server Error`: 서버 오류

---

## Rate Limiting

**제한**:
- 인증된 사용자: 1000 req/hour
- 비인증 사용자: 100 req/hour

**헤더**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 842
X-RateLimit-Reset: 1700000000
```

초과 시 `429 Too Many Requests` 응답

---

## 다음 단계

API 계약 정의 완료. Phase 1 마지막:
1. **빠른 시작 가이드**: 로컬 개발 환경 설정 문서
