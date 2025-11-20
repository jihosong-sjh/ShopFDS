# Tasks: 이커머스 프론트엔드 고도화

**Input**: Design documents from `/specs/004-frontend-ux-enhancement/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-endpoints.md

**Tests**: 테스트는 선택사항입니다. 이 기능에서는 E2E 테스트와 통합 테스트를 포함합니다.

**Organization**: 작업은 User Story별로 그룹화되어 각 스토리를 독립적으로 구현하고 테스트할 수 있습니다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (다른 파일, 의존성 없음)
- **[Story]**: 해당 작업이 속한 User Story (예: US1, US2, US3)
- 설명에 정확한 파일 경로 포함

## 경로 규칙

- **백엔드**: `services/ecommerce/backend/src/`
- **프론트엔드**: `services/ecommerce/frontend/src/`
- **테스트**: `services/ecommerce/backend/tests/`, `services/ecommerce/frontend/tests/`

---

## Phase 1: Setup (공유 인프라)

**목적**: 프로젝트 초기화 및 기본 구조 설정

- [X] T001 Git 브랜치 생성 및 전환 (004-frontend-ux-enhancement)
- [X] T002 [P] 백엔드 의존성 업데이트 (authlib, python-multipart 추가) in services/ecommerce/backend/requirements.txt
- [X] T003 [P] 프론트엔드 의존성 설치 (react-query, zustand, react-dropzone, vite-plugin-pwa, lodash.debounce) in services/ecommerce/frontend/package.json
- [X] T004 프론트엔드 Vite PWA 플러그인 설정 in services/ecommerce/frontend/vite.config.ts
- [X] T005 [P] 프론트엔드 React Query Provider 설정 in services/ecommerce/frontend/src/main.tsx
- [X] T006 [P] 프론트엔드 API 클라이언트 유틸리티 생성 in services/ecommerce/frontend/src/services/api.ts

---

## Phase 2: Foundational (필수 선행 작업)

**목적**: 모든 User Story 구현 전에 완료되어야 하는 핵심 인프라

**⚠️ CRITICAL**: 이 단계 완료 전까지 User Story 작업 시작 불가

- [ ] T007 데이터베이스 마이그레이션: Reviews 테이블 생성 in services/ecommerce/backend/alembic/versions/
- [ ] T008 [P] 데이터베이스 마이그레이션: ReviewVotes 테이블 생성 in services/ecommerce/backend/alembic/versions/
- [ ] T009 [P] 데이터베이스 마이그레이션: WishlistItems 테이블 생성 in services/ecommerce/backend/alembic/versions/
- [ ] T010 [P] 데이터베이스 마이그레이션: Addresses 테이블 생성 in services/ecommerce/backend/alembic/versions/
- [ ] T011 [P] 데이터베이스 마이그레이션: Coupons 테이블 생성 in services/ecommerce/backend/alembic/versions/
- [ ] T012 [P] 데이터베이스 마이그레이션: UserCoupons 테이블 생성 in services/ecommerce/backend/alembic/versions/
- [ ] T013 [P] 데이터베이스 마이그레이션: OAuthAccounts 테이블 생성 in services/ecommerce/backend/alembic/versions/
- [ ] T014 [P] 데이터베이스 마이그레이션: PushSubscriptions 테이블 생성 in services/ecommerce/backend/alembic/versions/
- [ ] T015 [P] 데이터베이스 마이그레이션: Products 테이블 images JSONB 컬럼 추가 in services/ecommerce/backend/alembic/versions/
- [ ] T016 [P] 데이터베이스 마이그레이션: Orders 테이블 coupon_id, discount_amount 컬럼 추가 in services/ecommerce/backend/alembic/versions/
- [ ] T017 Alembic 마이그레이션 실행 및 검증 (alembic upgrade head)
- [ ] T018 [P] 초기 데이터 시드: 쿠폰 샘플 데이터 생성 in services/ecommerce/backend/scripts/seed_data.py
- [ ] T019 [P] 프론트엔드 Tailwind CSS 다크모드 설정 in services/ecommerce/frontend/tailwind.config.js

**Checkpoint**: 기반 준비 완료 - User Story 구현 병렬 시작 가능

---

## Phase 3: User Story 1 - 효율적인 상품 검색 및 발견 (Priority: P1) 🎯 MVP

**Goal**: 사용자가 검색창 자동완성, 다양한 필터, 검색어 하이라이트를 통해 원하는 상품을 빠르게 찾을 수 있음

**Independent Test**: 사용자에게 "50만원 이하 삼성 스마트폰 찾기" 미션을 주고, 3번의 클릭 이내에 목표 상품을 찾을 수 있는지 측정

### Tests for User Story 1 ⚠️

> **NOTE: 테스트를 먼저 작성하고, 구현 전에 FAIL 확인**

- [X] T020 [P] [US1] 검색 자동완성 API 통합 테스트 in services/ecommerce/backend/tests/integration/test_search.py
- [X] T021 [P] [US1] 검색 필터링 E2E 테스트 (Playwright) in services/ecommerce/frontend/tests/e2e/search.spec.ts

### Backend Implementation for User Story 1

- [X] T022 [P] [US1] 검색 자동완성 API 엔드포인트 구현 (GET /v1/search/autocomplete) in services/ecommerce/backend/src/api/search.py
- [X] T023 [P] [US1] 상품 검색 API 엔드포인트 구현 (GET /v1/search/products) in services/ecommerce/backend/src/api/search.py
- [X] T024 [US1] PostgreSQL Trigram 유사도 검색 서비스 로직 구현 in services/ecommerce/backend/src/services/search_service.py
- [X] T025 [US1] 검색 히스토리 저장 API 엔드포인트 (POST /v1/search/history) in services/ecommerce/backend/src/api/search.py
- [X] T026 [US1] FastAPI 메인 앱에 검색 라우터 등록 in services/ecommerce/backend/src/main.py

### Frontend Implementation for User Story 1

- [X] T027 [P] [US1] useSearch Hook 구현 (디바운싱, React Query) in services/ecommerce/frontend/src/hooks/useSearch.ts
- [X] T028 [P] [US1] SearchBar 컴포넌트 구현 (자동완성 드롭다운) in services/ecommerce/frontend/src/components/SearchBar.tsx
- [X] T029 [US1] SearchPage 구현 (검색 결과 목록, 필터, 정렬) in services/ecommerce/frontend/src/pages/SearchPage.tsx
- [X] T030 [US1] 검색어 하이라이트 유틸리티 함수 구현 in services/ecommerce/frontend/src/utils/highlightText.ts
- [X] T031 [US1] 검색 필터 컴포넌트 구현 (가격 범위, 브랜드, 재고 여부) in services/ecommerce/frontend/src/components/SearchFilters.tsx
- [X] T032 [US1] URL 쿼리 파라미터 동기화 (React Router) in services/ecommerce/frontend/src/pages/SearchPage.tsx
- [X] T033 [US1] 최근 검색어 LocalStorage 관리 Hook in services/ecommerce/frontend/src/hooks/useSearchHistory.ts
- [ ] T034 [US1] 추천 상품 섹션 (홈 페이지) in services/ecommerce/frontend/src/pages/HomePage.tsx
- [X] T035 [US1] 최근 본 상품 섹션 (LocalStorage + 백엔드 동기화) in services/ecommerce/frontend/src/components/RecentlyViewed.tsx

**Checkpoint**: User Story 1 완전 기능, 독립 테스트 가능

---

## Phase 4: User Story 2 - 신뢰할 수 있는 상품 정보 확인 (Priority: P1)

**Goal**: 사용자가 상품 상세 이미지 확대, 실제 구매자 리뷰 읽기, 사진 리뷰 필터링을 통해 구매 결정을 내릴 수 있음

**Independent Test**: 사용자에게 "리뷰 평점 4.5점 이상인 노트북 중 실제 사용 사진이 있는 리뷰 읽기" 미션을 주고, 2분 이내에 해당 리뷰를 찾아 읽을 수 있는지 측정

### Tests for User Story 2 ⚠️

- [X] T036 [P] [US2] 리뷰 작성 API 통합 테스트 in services/ecommerce/backend/tests/integration/test_reviews.py
- [X] T037 [P] [US2] 리뷰 작성 E2E 테스트 (Playwright) in services/ecommerce/frontend/tests/e2e/review.spec.ts

### Backend Implementation for User Story 2

- [X] T038 [P] [US2] Review 모델 생성 in services/ecommerce/backend/src/models/review.py
- [X] T039 [P] [US2] ReviewVote 모델 생성 in services/ecommerce/backend/src/models/review_vote.py
- [X] T040 [US2] 리뷰 서비스 로직 구현 (작성 권한 검증, 이미지 업로드) in services/ecommerce/backend/src/services/review_service.py
- [X] T041 [US2] 리뷰 목록 조회 API (GET /v1/products/{id}/reviews) in services/ecommerce/backend/src/api/reviews.py
- [X] T042 [P] [US2] 리뷰 작성 API (POST /v1/reviews) in services/ecommerce/backend/src/api/reviews.py
- [X] T043 [P] [US2] 리뷰 수정 API (PUT /v1/reviews/{id}) in services/ecommerce/backend/src/api/reviews.py
- [X] T044 [P] [US2] 리뷰 삭제 API (DELETE /v1/reviews/{id}) in services/ecommerce/backend/src/api/reviews.py
- [X] T045 [P] [US2] 리뷰 도움돼요 투표 API (POST /v1/reviews/{id}/vote) in services/ecommerce/backend/src/api/reviews.py
- [X] T046 [P] [US2] 리뷰 도움돼요 취소 API (DELETE /v1/reviews/{id}/vote) in services/ecommerce/backend/src/api/reviews.py
- [X] T047 [US2] S3/R2 이미지 업로드 유틸리티 in services/ecommerce/backend/src/utils/image_upload.py
- [X] T048 [US2] FastAPI 메인 앱에 리뷰 라우터 등록 in services/ecommerce/backend/src/main.py

### Frontend Implementation for User Story 2

- [X] T049 [P] [US2] LazyImage 컴포넌트 구현 (Intersection Observer) in services/ecommerce/frontend/src/components/LazyImage.tsx
- [X] T050 [P] [US2] ImageGallery 컴포넌트 구현 (썸네일, 메인 이미지 전환) in services/ecommerce/frontend/src/components/ImageGallery.tsx
- [X] T051 [US2] ImageZoomModal 컴포넌트 구현 (확대 보기 2배) in services/ecommerce/frontend/src/components/ImageZoomModal.tsx
- [X] T052 [US2] ReviewForm 컴포넌트 구현 (별점, 텍스트, 사진 업로드) in services/ecommerce/frontend/src/components/ReviewForm.tsx
- [X] T053 [US2] ReviewList 컴포넌트 구현 (정렬, 필터) in services/ecommerce/frontend/src/components/ReviewList.tsx
- [X] T054 [US2] ReviewCard 컴포넌트 구현 (도움돼요 버튼, 사진 리뷰) in services/ecommerce/frontend/src/components/ReviewCard.tsx
- [X] T055 [US2] useReviews Hook 구현 (React Query) in services/ecommerce/frontend/src/hooks/useReviews.ts
- [X] T056 [US2] 상품 상세 페이지 업데이트 (이미지 갤러리, 리뷰 섹션) in services/ecommerce/frontend/src/pages/ProductDetailPage.tsx
- [X] T057 [US2] 상품 목록 카드에 평균 평점 및 리뷰 수 표시 in services/ecommerce/frontend/src/components/ProductCard.tsx

**Checkpoint**: User Story 1, 2 모두 독립적으로 동작

---

## Phase 5: User Story 3 - 간편한 결제 및 주문 프로세스 (Priority: P1)

**Goal**: 사용자가 할인 쿠폰 적용, 여러 결제 수단 선택, 주문 단계별 진행 상황 확인을 통해 빠르게 결제 완료

**Independent Test**: 사용자에게 "장바구니에 담긴 3개 상품 구매하기" 미션을 주고, 5분 이내에 주문 완료 페이지에 도달할 수 있는지 측정

### Tests for User Story 3 ⚠️

- [X] T058 [P] [US3] 쿠폰 적용 API 통합 테스트 in services/ecommerce/backend/tests/integration/test_coupons.py
- [X] T059 [P] [US3] 체크아웃 프로세스 E2E 테스트 (Playwright) in services/ecommerce/frontend/tests/e2e/checkout.spec.ts

### Backend Implementation for User Story 3

- [X] T060 [P] [US3] Coupon 모델 생성 in services/ecommerce/backend/src/models/coupon.py
- [X] T061 [P] [US3] UserCoupon 모델 생성 in services/ecommerce/backend/src/models/user_coupon.py
- [ ] T062 [US3] 쿠폰 서비스 로직 구현 (사용 가능 여부 검증, 할인 금액 계산) in services/ecommerce/backend/src/services/coupon_service.py
- [X] T063 [US3] 사용자 쿠폰 목록 조회 API (GET /v1/coupons/me) in services/ecommerce/backend/src/api/coupons.py
- [X] T064 [P] [US3] 쿠폰 발급 API (POST /v1/coupons/issue) in services/ecommerce/backend/src/api/coupons.py
- [X] T065 [P] [US3] 쿠폰 사용 가능 여부 확인 API (POST /v1/coupons/validate) in services/ecommerce/backend/src/api/coupons.py
- [X] T066 [US3] 주문 생성 서비스 업데이트 (쿠폰 적용) in services/ecommerce/backend/src/services/order_service.py
- [X] T067 [US3] FastAPI 메인 앱에 쿠폰 라우터 등록 in services/ecommerce/backend/src/main.py

### Frontend Implementation for User Story 3

- [X] T068 [US3] CheckoutPage 구현 (3단계 스텝 인디케이터) in services/ecommerce/frontend/src/pages/CheckoutPage.tsx
- [X] T069 [US3] CheckoutStep 컴포넌트 구현 (배송 정보 → 결제 → 주문 확인) in services/ecommerce/frontend/src/components/CheckoutStep.tsx
- [X] T070 [US3] CouponInput 컴포넌트 구현 (쿠폰 코드 입력, 적용) in services/ecommerce/frontend/src/components/CouponInput.tsx
- [X] T071 [US3] PaymentMethodSelector 컴포넌트 구현 (신용카드, 토스페이, 카카오페이) in services/ecommerce/frontend/src/components/PaymentMethodSelector.tsx
- [X] T072 [US3] OrderSummary 컴포넌트 구현 (총 금액, 할인 금액 표시) in services/ecommerce/frontend/src/components/OrderSummary.tsx
- [X] T073 [US3] OrderCompletePage 구현 (주문 번호, 배송 예정일 표시) in services/ecommerce/frontend/src/pages/OrderCompletePage.tsx
- [X] T074 [US3] useCoupons Hook 구현 (React Query) in services/ecommerce/frontend/src/hooks/useCoupons.ts
- [ ] T075 [US3] Toss Payments SDK 통합 in services/ecommerce/frontend/src/utils/tossPayments.ts

**Checkpoint**: User Story 1, 2, 3 모두 독립적으로 동작

---

## Phase 6: User Story 4 - 개인화된 쇼핑 경험 (Priority: P2)

**Goal**: 사용자가 소셜 로그인, 위시리스트, 추천 상품을 통해 개인화된 쇼핑 경험을 누림

**Independent Test**: 회원가입하지 않은 사용자가 Google 계정으로 로그인하여, 상품을 위시리스트에 추가하고, 다음날 재방문 시 위시리스트를 확인할 수 있는지 테스트

### Tests for User Story 4 ⚠️

- [X] T076 [P] [US4] OAuth 로그인 API 통합 테스트 in services/ecommerce/backend/tests/integration/test_oauth.py
- [X] T077 [P] [US4] 위시리스트 E2E 테스트 (Playwright) in services/ecommerce/frontend/tests/e2e/wishlist.spec.ts

### Backend Implementation for User Story 4

- [X] T078 [P] [US4] OAuthAccount 모델 생성 in services/ecommerce/backend/src/models/oauth_account.py
- [X] T079 [P] [US4] WishlistItem 모델 생성 in services/ecommerce/backend/src/models/wishlist_item.py
- [X] T080 [US4] OAuth 서비스 로직 구현 (Google, Kakao, Naver) in services/ecommerce/backend/src/services/oauth_service.py
- [X] T081 [US4] 위시리스트 서비스 로직 구현 in services/ecommerce/backend/src/services/wishlist_service.py
- [X] T082 [US4] Google OAuth 로그인 API (GET /v1/auth/oauth/google, callback) in services/ecommerce/backend/src/api/oauth.py
- [X] T083 [P] [US4] Kakao OAuth 로그인 API (GET /v1/auth/oauth/kakao, callback) in services/ecommerce/backend/src/api/oauth.py
- [X] T084 [P] [US4] Naver OAuth 로그인 API (GET /v1/auth/oauth/naver, callback) in services/ecommerce/backend/src/api/oauth.py
- [X] T085 [US4] 위시리스트 조회 API (GET /v1/wishlist) in services/ecommerce/backend/src/api/wishlist.py
- [X] T086 [P] [US4] 위시리스트 추가 API (POST /v1/wishlist) in services/ecommerce/backend/src/api/wishlist.py
- [X] T087 [P] [US4] 위시리스트 삭제 API (DELETE /v1/wishlist/{id}) in services/ecommerce/backend/src/api/wishlist.py
- [X] T088 [P] [US4] 위시리스트 일괄 장바구니 담기 API (POST /v1/wishlist/move-to-cart) in services/ecommerce/backend/src/api/wishlist.py
- [X] T089 [US4] 추천 상품 API (GET /v1/recommendations/for-you) in services/ecommerce/backend/src/api/recommendations.py
- [X] T090 [P] [US4] 최근 본 상품 조회 API (GET /v1/recommendations/recently-viewed) in services/ecommerce/backend/src/api/recommendations.py
- [X] T091 [P] [US4] 최근 본 상품 저장 API (POST /v1/recommendations/recently-viewed) in services/ecommerce/backend/src/api/recommendations.py
- [X] T092 [P] [US4] 연관 상품 조회 API (GET /v1/products/{id}/related) in services/ecommerce/backend/src/api/products.py
- [X] T093 [US4] FastAPI 메인 앱에 OAuth, 위시리스트, 추천 라우터 등록 in services/ecommerce/backend/src/main.py

### Frontend Implementation for User Story 4

- [X] T094 [P] [US4] GoogleLogin 컴포넌트 구현 (@react-oauth/google) in services/ecommerce/frontend/src/components/GoogleLogin.tsx
- [X] T095 [P] [US4] KakaoLogin 컴포넌트 구현 in services/ecommerce/frontend/src/components/KakaoLogin.tsx
- [X] T096 [P] [US4] NaverLogin 컴포넌트 구현 in services/ecommerce/frontend/src/components/NaverLogin.tsx
- [X] T097 [US4] 로그인 페이지 업데이트 (소셜 로그인 버튼 추가) in services/ecommerce/frontend/src/pages/LoginPage.tsx
- [X] T098 [US4] useAuth Hook 업데이트 (OAuth 로그인 처리) in services/ecommerce/frontend/src/hooks/useAuth.ts
- [X] T099 [US4] useWishlist Hook 구현 (React Query) in services/ecommerce/frontend/src/hooks/useWishlist.ts
- [X] T100 [US4] WishlistPage 구현 in services/ecommerce/frontend/src/pages/WishlistPage.tsx
- [X] T101 [US4] WishlistButton 컴포넌트 구현 (하트 아이콘 토글) in services/ecommerce/frontend/src/components/WishlistButton.tsx
- [X] T102 [US4] RecommendedProducts 컴포넌트 구현 (홈 페이지) in services/ecommerce/frontend/src/components/RecommendedProducts.tsx
- [X] T103 [US4] RelatedProducts 컴포넌트 구현 (상품 상세 페이지) in services/ecommerce/frontend/src/components/RelatedProducts.tsx

**Checkpoint**: User Story 1-4 모두 독립적으로 동작

---

## Phase 7: User Story 5 - 상품 비교 및 의사결정 지원 (Priority: P3)

**Goal**: 사용자가 여러 상품을 나란히 비교하여 최적의 선택을 할 수 있음

**Independent Test**: 사용자에게 "노트북 3개를 비교 목록에 추가하고, 비교 테이블에서 가장 저렴한 제품 선택하기" 미션을 주고, 성공 여부 측정

### Frontend Implementation for User Story 5 (LocalStorage 기반)

- [X] T104 [P] [US5] useComparison Hook 구현 (Zustand + LocalStorage) in services/ecommerce/frontend/src/hooks/useComparison.ts
- [X] T105 [US5] ComparisonFloatingButton 컴포넌트 구현 (화면 하단 플로팅) in services/ecommerce/frontend/src/components/ComparisonFloatingButton.tsx
- [X] T106 [US5] ComparisonPage 구현 (상품 비교 테이블) in services/ecommerce/frontend/src/pages/ComparisonPage.tsx
- [X] T107 [US5] CompareButton 컴포넌트 구현 (상품 카드에 추가) in services/ecommerce/frontend/src/components/CompareButton.tsx
- [X] T108 [US5] 비교 목록 상태 관리 (Zustand store) in services/ecommerce/frontend/src/stores/comparisonStore.ts

**Checkpoint**: User Story 1-5 모두 독립적으로 동작

---

## Phase 8: User Story 6 - 마이페이지 종합 관리 (Priority: P2)

**Goal**: 사용자가 배송지, 포인트, 쿠폰, 1:1 문의를 한 곳에서 관리할 수 있음

**Independent Test**: 재구매 고객이 마이페이지에서 새 배송지를 추가하고, 기본 배송지로 설정한 뒤, 체크아웃 시 자동으로 해당 주소가 선택되는지 확인

### Tests for User Story 6 ⚠️

- [X] T109 [P] [US6] 배송지 관리 API 통합 테스트 in services/ecommerce/backend/tests/integration/test_addresses.py

### Backend Implementation for User Story 6

- [X] T110 [P] [US6] Address 모델 생성 in services/ecommerce/backend/src/models/address.py
- [X] T111 [US6] 배송지 서비스 로직 구현 (기본 배송지 변경, 삭제 검증) in services/ecommerce/backend/src/services/address_service.py
- [X] T112 [US6] 배송지 목록 조회 API (GET /v1/addresses) in services/ecommerce/backend/src/api/addresses.py
- [X] T113 [P] [US6] 배송지 추가 API (POST /v1/addresses) in services/ecommerce/backend/src/api/addresses.py
- [X] T114 [P] [US6] 배송지 수정 API (PUT /v1/addresses/{id}) in services/ecommerce/backend/src/api/addresses.py
- [X] T115 [P] [US6] 배송지 삭제 API (DELETE /v1/addresses/{id}) in services/ecommerce/backend/src/api/addresses.py
- [X] T116 [P] [US6] 기본 배송지 설정 API (POST /v1/addresses/{id}/set-default) in services/ecommerce/backend/src/api/addresses.py
- [X] T117 [US6] FastAPI 메인 앱에 배송지 라우터 등록 in services/ecommerce/backend/src/main.py

### Frontend Implementation for User Story 6

- [X] T118 [US6] MyPage 레이아웃 구현 (사이드바, 메뉴) in services/ecommerce/frontend/src/pages/MyPage.tsx
- [X] T119 [US6] AddressManagementPage 구현 (배송지 목록, CRUD) in services/ecommerce/frontend/src/pages/AddressManagementPage.tsx
- [X] T120 [US6] AddressForm 컴포넌트 구현 (배송지 추가/수정 폼) in services/ecommerce/frontend/src/components/AddressForm.tsx
- [X] T121 [US6] AddressCard 컴포넌트 구현 (기본 배송지 뱃지, 수정/삭제 버튼) in services/ecommerce/frontend/src/components/AddressCard.tsx
- [X] T122 [US6] useAddresses Hook 구현 (React Query) in services/ecommerce/frontend/src/hooks/useAddresses.ts
- [X] T123 [US6] PointsCouponsPage 구현 (적립금, 쿠폰 목록) in services/ecommerce/frontend/src/pages/PointsCouponsPage.tsx
- [X] T124 [US6] 체크아웃 페이지 업데이트 (기본 배송지 자동 선택) in services/ecommerce/frontend/src/pages/CheckoutPage.tsx

**Checkpoint**: User Story 1-6 모두 독립적으로 동작

---

## Phase 9: User Story 7 - 모바일 최적화 및 PWA 경험 (Priority: P3)

**Goal**: 모바일 사용자가 PWA 설치, 푸시 알림, 오프라인 지원을 통해 네이티브 앱 수준의 경험을 누림

**Independent Test**: 모바일 사용자가 "홈 화면에 추가" 배너를 통해 PWA를 설치하고, 오프라인 상태에서 최근 본 상품을 조회할 수 있는지 확인

### Backend Implementation for User Story 7

- [X] T125 [P] [US7] PushSubscription 모델 생성 in services/ecommerce/backend/src/models/push_subscription.py
- [X] T126 [US7] 푸시 알림 서비스 로직 구현 (FCM) in services/ecommerce/backend/src/services/push_notification_service.py
- [X] T127 [US7] 푸시 구독 등록 API (POST /v1/push/subscribe) in services/ecommerce/backend/src/api/push.py
- [X] T128 [P] [US7] 푸시 구독 해지 API (DELETE /v1/push/unsubscribe) in services/ecommerce/backend/src/api/push.py
- [X] T129 [US7] 주문 상태 변경 시 푸시 알림 전송 in services/ecommerce/backend/src/services/order_service.py
- [X] T130 [US7] FastAPI 메인 앱에 푸시 라우터 등록 in services/ecommerce/backend/src/main.py

### Frontend Implementation for User Story 7

- [X] T131 [US7] Service Worker 등록 및 Workbox 설정 in services/ecommerce/frontend/src/sw.ts
- [X] T132 [US7] Manifest.json 설정 (아이콘, 테마 색상) in services/ecommerce/frontend/public/manifest.json
- [X] T133 [US7] usePWA Hook 구현 (설치 프롬프트, 알림 권한) in services/ecommerce/frontend/src/hooks/usePWA.ts
- [X] T134 [US7] PWAInstallPrompt 컴포넌트 구현 (설치 배너) in services/ecommerce/frontend/src/components/PWAInstallPrompt.tsx
- [X] T135 [US7] 푸시 알림 권한 요청 컴포넌트 in services/ecommerce/frontend/src/components/PushNotificationPrompt.tsx
- [X] T136 [US7] 오프라인 폴백 페이지 in services/ecommerce/frontend/src/pages/OfflinePage.tsx
- [X] T137 [US7] Service Worker 캐싱 전략 설정 (API, 정적 에셋) in services/ecommerce/frontend/vite.config.ts
- [X] T138 [US7] PWA 아이콘 및 스플래시 스크린 이미지 생성 in services/ecommerce/frontend/public/

**Checkpoint**: 모든 User Story 독립적으로 기능

---

## Phase 10: Polish & Cross-Cutting Concerns

**목적**: 여러 User Story에 영향을 미치는 개선 작업

- [X] T139 [P] 다크 모드 구현 (Tailwind CSS, Zustand) in services/ecommerce/frontend/src/stores/themeStore.ts
- [X] T140 [P] 다크 모드 토글 컴포넌트 in services/ecommerce/frontend/src/components/ThemeToggle.tsx
- [X] T141 [US7] 접근성 개선 (ARIA 속성, 시맨틱 HTML) 전체 컴포넌트 리뷰
- [X] T142 [US7] 키보드 네비게이션 지원 (Tab, Enter, Esc) 전체 인터랙티브 요소
- [X] T143 [P] 성능 최적화: 코드 스플리팅 (React.lazy) in services/ecommerce/frontend/src/App.tsx
- [X] T144 [P] 성능 최적화: 가상 스크롤 (react-window) 긴 상품 목록
- [X] T145 [P] 에러 바운더리 컴포넌트 구현 in services/ecommerce/frontend/src/components/ErrorBoundary.tsx
- [X] T146 [P] 스켈레톤 스크린 로더 구현 in services/ecommerce/frontend/src/components/SkeletonLoader.tsx
- [X] T147 [P] 토스트 알림 시스템 구현 in services/ecommerce/frontend/src/components/Toast.tsx
- [X] T148 [P] 모달 공통 컴포넌트 개선 (포커스 트랩, ESC 키) in services/ecommerce/frontend/src/components/Modal.tsx
- [X] T149 [P] API 에러 핸들링 인터셉터 in services/ecommerce/frontend/src/services/api.ts
- [X] T150 [P] 백엔드 로깅 개선 (구조화된 로그, 민감 정보 마스킹) in services/ecommerce/backend/src/utils/logger.py
- [X] T151 [P] 프론트엔드 Sentry 에러 트래킹 설정 in services/ecommerce/frontend/src/main.tsx
- [X] T152 [P] Web Vitals 측정 및 리포팅 in services/ecommerce/frontend/src/utils/webVitals.ts
- [X] T153 [P] API 문서 업데이트 (Swagger UI) in services/ecommerce/backend/src/main.py
- [X] T154 코드 리뷰 및 리팩토링 (중복 제거, 타입 안전성 개선)
- [X] T155 보안 강화 (CSRF 토큰, XSS 방지, Rate Limiting)
- [X] T156 quickstart.md 검증 및 업데이트 in specs/004-frontend-ux-enhancement/quickstart.md
- [X] T157 README.md 업데이트 (기능 목록, 스크린샷) in README.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존성 없음 - 즉시 시작 가능
- **Foundational (Phase 2)**: Setup 완료 필요 - 모든 User Story를 블록
- **User Stories (Phase 3-9)**: 모두 Foundational 완료 필요
  - User Story들은 병렬 진행 가능 (인력이 있는 경우)
  - 또는 우선순위순 순차 진행 (P1 → P2 → P3)
- **Polish (Phase 10)**: 원하는 User Story 모두 완료 필요

### User Story Dependencies

- **User Story 1 (P1)**: Foundational 완료 후 시작 - 다른 스토리 의존성 없음
- **User Story 2 (P1)**: Foundational 완료 후 시작 - 독립적으로 테스트 가능
- **User Story 3 (P1)**: Foundational 완료 후 시작 - 독립적으로 테스트 가능
- **User Story 4 (P2)**: Foundational 완료 후 시작 - 독립적으로 테스트 가능
- **User Story 5 (P3)**: Foundational 완료 후 시작 - 프론트엔드 전용, 백엔드 불필요
- **User Story 6 (P2)**: Foundational 완료 후 시작 - 독립적으로 테스트 가능
- **User Story 7 (P3)**: Foundational 완료 후 시작 - 독립적으로 테스트 가능

### User Story 내 순서

- 테스트 (포함 시) → 먼저 작성, 구현 전 FAIL 확인
- 모델 → 서비스
- 서비스 → API 엔드포인트
- 백엔드 API → 프론트엔드 Hook/컴포넌트
- 핵심 구현 → 통합
- 스토리 완료 → 다음 우선순위로 이동

### Parallel Opportunities

- Setup의 모든 [P] 작업 병렬 실행 가능
- Foundational의 모든 [P] 작업 병렬 실행 가능 (Phase 2 내)
- Foundational 완료 후, 모든 User Story 병렬 시작 가능 (팀 인력 허용 시)
- User Story 내 테스트 [P] 작업 병렬 실행 가능
- User Story 내 모델 [P] 작업 병렬 실행 가능
- 서로 다른 User Story는 다른 팀원이 병렬 작업 가능

---

## Parallel Example: User Story 1

```bash
# User Story 1의 모든 테스트를 병렬 실행:
Task: "검색 자동완성 API 통합 테스트 in services/ecommerce/backend/tests/integration/test_search.py"
Task: "검색 필터링 E2E 테스트 (Playwright) in services/ecommerce/frontend/tests/e2e/search.spec.ts"

# User Story 1의 병렬 가능한 백엔드 작업:
Task: "검색 자동완성 API 엔드포인트 구현 (GET /v1/search/autocomplete) in services/ecommerce/backend/src/api/search.py"
Task: "상품 검색 API 엔드포인트 구현 (GET /v1/search/products) in services/ecommerce/backend/src/api/search.py"

# User Story 1의 병렬 가능한 프론트엔드 작업:
Task: "useSearch Hook 구현 (디바운싱, React Query) in services/ecommerce/frontend/src/hooks/useSearch.ts"
Task: "SearchBar 컴포넌트 구현 (자동완성 드롭다운) in services/ecommerce/frontend/src/components/SearchBar.tsx"
```

---

## Parallel Example: User Story 2

```bash
# User Story 2의 백엔드 모델 병렬 생성:
Task: "Review 모델 생성 in services/ecommerce/backend/src/models/review.py"
Task: "ReviewVote 모델 생성 in services/ecommerce/backend/src/models/review_vote.py"

# User Story 2의 API 엔드포인트 병렬 구현:
Task: "리뷰 작성 API (POST /v1/reviews) in services/ecommerce/backend/src/api/reviews.py"
Task: "리뷰 수정 API (PUT /v1/reviews/{id}) in services/ecommerce/backend/src/api/reviews.py"
Task: "리뷰 삭제 API (DELETE /v1/reviews/{id}) in services/ecommerce/backend/src/api/reviews.py"
Task: "리뷰 도움돼요 투표 API (POST /v1/reviews/{id}/vote) in services/ecommerce/backend/src/api/reviews.py"

# User Story 2의 프론트엔드 컴포넌트 병렬 구현:
Task: "LazyImage 컴포넌트 구현 (Intersection Observer) in services/ecommerce/frontend/src/components/LazyImage.tsx"
Task: "ImageGallery 컴포넌트 구현 (썸네일, 메인 이미지 전환) in services/ecommerce/frontend/src/components/ImageGallery.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1만)

1. Phase 1: Setup 완료
2. Phase 2: Foundational 완료 (CRITICAL - 모든 스토리 블록)
3. Phase 3: User Story 1 완료
4. **STOP and VALIDATE**: User Story 1 독립 테스트
5. 준비 완료 시 배포/데모

### Incremental Delivery

1. Setup + Foundational 완료 → 기반 준비
2. User Story 1 추가 → 독립 테스트 → 배포/데모 (MVP!)
3. User Story 2 추가 → 독립 테스트 → 배포/데모
4. User Story 3 추가 → 독립 테스트 → 배포/데모
5. User Story 4 추가 → 독립 테스트 → 배포/데모
6. 각 스토리가 이전 스토리를 깨지 않고 가치 추가

### Parallel Team Strategy

여러 개발자가 있는 경우:

1. 팀이 Setup + Foundational을 함께 완료
2. Foundational 완료 후:
   - 개발자 A: User Story 1 (검색)
   - 개발자 B: User Story 2 (리뷰)
   - 개발자 C: User Story 3 (결제/쿠폰)
   - 개발자 D: User Story 4 (OAuth/위시리스트)
3. 스토리들이 독립적으로 완료되고 통합

---

## 총 작업 수 요약

- **총 작업 수**: 157개
- **Phase 1 (Setup)**: 6개 작업
- **Phase 2 (Foundational)**: 13개 작업
- **User Story 1 (검색)**: 16개 작업
- **User Story 2 (리뷰)**: 21개 작업
- **User Story 3 (결제/쿠폰)**: 18개 작업
- **User Story 4 (OAuth/위시리스트)**: 27개 작업
- **User Story 5 (비교)**: 5개 작업
- **User Story 6 (마이페이지)**: 16개 작업
- **User Story 7 (PWA)**: 14개 작업
- **Phase 10 (Polish)**: 19개 작업

**병렬 실행 가능 작업**: 89개 ([P] 마킹)

**독립 테스트 가능**: 각 User Story는 독립적으로 완성 및 테스트 가능

**제안 MVP 범위**: User Story 1 (검색) + User Story 2 (리뷰) + User Story 3 (결제/쿠폰) - 총 55개 작업

---

## Notes

- [P] 작업 = 다른 파일, 의존성 없음
- [Story] 라벨은 작업을 특정 User Story와 연결하여 추적성 제공
- 각 User Story는 독립적으로 완성 및 테스트 가능
- 테스트는 구현 전에 작성하고 FAIL 확인
- 각 작업 또는 논리적 그룹 후 커밋
- 각 Checkpoint에서 멈춰 스토리 독립 검증 가능
- 피해야 할 것: 모호한 작업, 동일 파일 충돌, 독립성을 깨는 스토리 간 의존성
