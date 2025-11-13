# Tasks: AI/ML 기반 이커머스 FDS 플랫폼

**입력**: `/specs/001-ecommerce-fds-platform/` 설계 문서
**전제조건**: plan.md (필수), spec.md (필수), research.md, data-model.md, contracts/

**테스트**: 본 명세서에서는 테스트를 명시적으로 요청하지 않았으므로 테스트 작업을 포함하지 않습니다. 필요 시 추후 추가 가능합니다.

**구조**: 사용자 스토리별로 태스크를 그룹화하여 각 스토리를 독립적으로 구현하고 테스트할 수 있도록 합니다.

## 형식: `[ID] [P?] [Story] 설명`

- **[P]**: 병렬 실행 가능 (서로 다른 파일, 의존성 없음)
- **[Story]**: 해당 태스크가 속한 사용자 스토리 (예: US1, US2, US3)
- 설명에 정확한 파일 경로 포함

## 경로 규칙

본 프로젝트는 마이크로서비스 아키텍처를 사용합니다:
- **이커머스 백엔드**: `services/ecommerce/backend/src/`, `services/ecommerce/backend/tests/`
- **이커머스 프론트엔드**: `services/ecommerce/frontend/src/`, `services/ecommerce/frontend/tests/`
- **FDS 서비스**: `services/fds/src/`, `services/fds/tests/`
- **ML 서비스**: `services/ml-service/src/`, `services/ml-service/tests/`
- **관리자 대시보드 백엔드**: `services/admin-dashboard/backend/src/`
- **관리자 대시보드 프론트엔드**: `services/admin-dashboard/frontend/src/`

---

## Phase 1: 프로젝트 초기 설정

**목적**: 프로젝트 구조 생성 및 기본 환경 구축

- [X] T001 프로젝트 디렉토리 구조 생성 (plan.md 구조에 따라)
- [X] T002 Git 저장소 초기화 및 .gitignore 설정
- [X] T003 [P] Docker Compose 개발 환경 구성 파일 작성 (infrastructure/docker/docker-compose.dev.yml)
- [X] T004 [P] PostgreSQL 15+ 데이터베이스 컨테이너 설정 및 TimescaleDB 확장 설치
- [X] T005 [P] Redis 7+ 캐시 서버 컨테이너 설정
- [X] T006 [P] 이커머스 백엔드 Python 가상환경 생성 및 FastAPI 의존성 설치 (services/ecommerce/backend/requirements.txt)
- [X] T007 [P] FDS 서비스 Python 가상환경 생성 및 의존성 설치 (services/fds/requirements.txt)
- [X] T008 [P] ML 서비스 Python 가상환경 생성 및 scikit-learn, LightGBM 설치 (services/ml-service/requirements.txt)
- [X] T009 [P] 이커머스 프론트엔드 React + TypeScript + Vite 프로젝트 초기화 (services/ecommerce/frontend)
- [X] T010 [P] 관리자 대시보드 프론트엔드 React + TypeScript 프로젝트 초기화 (services/admin-dashboard/frontend)

---

## Phase 2: 기반 인프라 (필수 선행 작업)

**목적**: 모든 사용자 스토리 구현 전에 반드시 완료되어야 하는 핵심 인프라

**⚠️ 중요**: 이 단계가 완료되기 전에는 사용자 스토리 작업을 시작할 수 없습니다

### 데이터베이스 및 마이그레이션

- [X] T011 Alembic 마이그레이션 도구 초기화 (services/ecommerce/backend/alembic)
- [X] T012 SQLAlchemy Base 모델 및 데이터베이스 연결 설정 (services/ecommerce/backend/src/models/base.py)
- [X] T013 데이터베이스 인덱스 전략 구현 (data-model.md 인덱스 섹션 참조)

### 인증 및 보안

- [X] T014 JWT 인증 미들웨어 구현 (services/ecommerce/backend/src/middleware/auth.py)
- [X] T015 [P] 비밀번호 해싱 유틸리티 구현 (bcrypt, services/ecommerce/backend/src/utils/security.py)
- [X] T016 [P] 역할 기반 접근 제어 (RBAC) 데코레이터 구현 (services/ecommerce/backend/src/middleware/authorization.py)

### API 및 에러 처리

- [X] T017 FastAPI 애플리케이션 기본 구조 및 라우터 설정 (services/ecommerce/backend/src/main.py)
- [X] T018 [P] 전역 에러 핸들러 및 커스텀 예외 클래스 구현 (services/ecommerce/backend/src/utils/exceptions.py)
- [X] T019 [P] 로깅 설정 및 민감 데이터 자동 마스킹 (services/ecommerce/backend/src/utils/logging.py)
- [X] T020 [P] CORS 미들웨어 설정 (프론트엔드 연동용)

### 환경 설정

- [X] T021 환경 변수 관리 (Pydantic Settings, services/ecommerce/backend/src/config.py)
- [X] T022 [P] Redis 연결 풀 설정 (services/ecommerce/backend/src/utils/redis_client.py)

**체크포인트**: 기반 인프라 완료 - 사용자 스토리 구현을 병렬로 시작할 수 있습니다

---

## Phase 3: 사용자 스토리 1 - 일반 고객의 정상 거래 플로우 (우선순위: P1) 🎯 MVP

**목표**: 일반 고객이 회원가입부터 상품 검색, 장바구니 담기, 결제 완료까지 전체 쇼핑 여정을 원활하게 완료할 수 있는 핵심 이커머스 기능 제공. FDS는 백그라운드에서 작동하되 정상 거래에 방해가 되지 않음.

**독립 테스트**: 새로운 사용자로 회원가입 → 상품 검색 → 장바구니 추가 → 결제 완료 → 주문 추적까지 전체 플로우를 실행하고, FDS 위험 점수가 낮게 산정되며(0-30점) 추가 인증 없이 결제가 완료되는지 확인.

### 데이터 모델 (User Story 1)

- [X] T023 [P] [US1] User 모델 생성 (services/ecommerce/backend/src/models/user.py)
- [X] T024 [P] [US1] Product 모델 생성 (services/ecommerce/backend/src/models/product.py)
- [X] T025 [P] [US1] Cart 및 CartItem 모델 생성 (services/ecommerce/backend/src/models/cart.py)
- [X] T026 [P] [US1] Order 및 OrderItem 모델 생성 (services/ecommerce/backend/src/models/order.py)
- [X] T027 [P] [US1] Payment 모델 생성 (services/ecommerce/backend/src/models/payment.py)
- [X] T028 [US1] 초기 마이그레이션 생성 및 적용 (alembic revision --autogenerate -m "Create ecommerce tables")

### 백엔드 서비스 (User Story 1)

- [X] T029 [P] [US1] UserService 구현: 회원가입, 로그인, 프로필 조회 (services/ecommerce/backend/src/services/user_service.py)
- [X] T030 [P] [US1] ProductService 구현: 상품 목록 조회, 검색, 상세 조회 (services/ecommerce/backend/src/services/product_service.py)
- [X] T031 [US1] CartService 구현: 장바구니 추가/수정/삭제 (services/ecommerce/backend/src/services/cart_service.py)
- [X] T032 [US1] OrderService 구현: 주문 생성, 주문 상태 관리 (services/ecommerce/backend/src/services/order_service.py)
- [X] T033 [US1] PaymentService 구현: 결제 처리 및 토큰화 (services/ecommerce/backend/src/services/payment_service.py)

### REST API 엔드포인트 (User Story 1)

- [X] T034 [P] [US1] 인증 API 구현: POST /v1/auth/register, POST /v1/auth/login (services/ecommerce/backend/src/api/auth.py)
- [X] T035 [P] [US1] 상품 API 구현: GET /v1/products, GET /v1/products/{id} (services/ecommerce/backend/src/api/products.py)
- [X] T036 [US1] 장바구니 API 구현: GET /v1/cart, POST /v1/cart/items, PUT /v1/cart/items/{id}, DELETE /v1/cart/items/{id} (services/ecommerce/backend/src/api/cart.py)
- [X] T037 [US1] 주문 API 구현: POST /v1/orders, GET /v1/orders, GET /v1/orders/{id} (services/ecommerce/backend/src/api/orders.py)

### 프론트엔드 (User Story 1)

- [X] T038 [P] [US1] 회원가입 페이지 구현 (services/ecommerce/frontend/src/pages/Register.tsx)
- [X] T039 [P] [US1] 로그인 페이지 구현 (services/ecommerce/frontend/src/pages/Login.tsx)
- [X] T040 [P] [US1] 상품 목록 페이지 및 검색 기능 구현 (services/ecommerce/frontend/src/pages/ProductList.tsx)
- [X] T041 [P] [US1] 상품 상세 페이지 구현 (services/ecommerce/frontend/src/pages/ProductDetail.tsx)
- [X] T042 [US1] 장바구니 페이지 구현 (services/ecommerce/frontend/src/pages/Cart.tsx)
- [X] T043 [US1] 주문/결제 페이지 구현 (services/ecommerce/frontend/src/pages/Checkout.tsx)
- [X] T044 [US1] 주문 추적 페이지 구현 (services/ecommerce/frontend/src/pages/OrderTracking.tsx)
- [X] T045 [US1] Zustand 전역 상태 관리 설정 (장바구니, 인증 상태)
- [X] T046 [US1] React Query API 통신 레이어 구현 (services/ecommerce/frontend/src/services/api.ts)

### 기본 FDS 통합 (User Story 1)

- [ ] T047 [US1] Transaction 모델 생성 (services/fds/src/models/transaction.py)
- [ ] T048 [US1] 기본 FDS 평가 엔드포인트 구현: POST /internal/fds/evaluate (services/fds/src/api/evaluation.py)
- [ ] T049 [US1] 이커머스 백엔드에서 FDS 서비스 비동기 호출 통합 (OrderService 내)
- [ ] T050 [US1] 정상 거래 시나리오 검증 (위험 점수 0-30점, 자동 승인)

**체크포인트**: 이 시점에서 사용자 스토리 1이 완전히 작동하며 독립적으로 테스트 가능해야 합니다. 고객이 회원가입부터 결제 완료까지 전체 플로우를 사용할 수 있습니다.

---

## Phase 4: 사용자 스토리 2 - 의심 거래 시 단계적 인증 (우선순위: P1)

**목표**: FDS가 중간 위험도 거래를 탐지했을 때 고객에게 추가 인증(OTP, 생체인증)을 요청하고, 인증 성공 시 거래를 완료하는 메커니즘 구현.

**독립 테스트**: 평소와 다른 IP 위치에서 로그인하거나 고액 결제를 시도하여 FDS가 중간 위험도(40-70점)를 산정하고 추가 인증을 요구하는지 확인. OTP 입력 성공 시 거래 완료, 3회 실패 시 거래 차단 확인.

### FDS 룰 엔진 (User Story 2)

- [X] T051 [P] [US2] RiskFactor 모델 생성 (services/fds/src/models/risk_factor.py)
- [X] T052 [P] [US2] DetectionRule 모델 생성 (services/fds/src/models/detection_rule.py)
- [X] T053 [US2] 룰 엔진 기본 구조 구현 (services/fds/src/engines/rule_engine.py)
- [X] T054 [P] [US2] Velocity Check 룰 구현 (단시간 내 반복 거래 탐지, Redis 활용)
- [X] T055 [P] [US2] 거래 금액 임계값 룰 구현 (평소 패턴 대비 고액 거래 탐지)
- [X] T056 [P] [US2] 지역 불일치 룰 구현 (등록 주소 vs IP 위치 비교)
- [X] T057 [US2] 위험 점수 산정 로직 구현 (여러 요인의 가중치 합산)

### 추가 인증 메커니즘 (User Story 2)

- [X] T058 [US2] OTP 생성 및 검증 유틸리티 구현 (services/ecommerce/backend/src/utils/otp.py)
- [X] T059 [US2] 추가 인증 요청 API 구현: POST /v1/auth/request-otp (services/ecommerce/backend/src/api/auth.py)
- [X] T060 [US2] OTP 검증 API 구현: POST /v1/auth/verify-otp (services/ecommerce/backend/src/api/auth.py)
- [X] T061 [US2] OrderService에 추가 인증 플로우 통합 (중간 위험도 시 OTP 요구)

### 프론트엔드 (User Story 2)

- [X] T062 [P] [US2] 추가 인증 모달 컴포넌트 구현 (OTP 입력 화면, services/ecommerce/frontend/src/components/OTPModal.tsx)
- [X] T063 [US2] 결제 페이지에 추가 인증 플로우 통합

### 통합 및 검증 (User Story 2)

- [ ] T064 [US2] FDS에서 중간 위험도 거래 시나리오 검증 (위험 점수 40-70점)
- [ ] T065 [US2] 추가 인증 성공 시나리오 검증 (거래 승인)
- [ ] T066 [US2] 추가 인증 3회 실패 시나리오 검증 (거래 차단)

**체크포인트**: 사용자 스토리 1과 2가 모두 독립적으로 작동해야 합니다. 정상 거래는 그대로 진행되며, 의심 거래는 추가 인증을 거칩니다.

---

## Phase 5: 사용자 스토리 3 - 고위험 거래 자동 차단 및 검토 (우선순위: P1)

**목표**: 고위험 거래를 자동으로 차단하고, 보안팀 대시보드에 실시간 알림을 전송하여 수동 검토를 가능하게 합니다.

**독립 테스트**: 알려진 악성 IP에서 접속하거나 단시간 내 여러 카드로 결제 시도 시 FDS가 고위험(80-100점)으로 판단하고 즉시 거래를 차단하며, 보안팀 대시보드에 알림이 표시되는지 확인.

### CTI 연동 (User Story 3)

- [ ] T067 [P] [US3] ThreatIntelligence 모델 생성 (services/fds/src/models/threat_intelligence.py)
- [ ] T068 [US3] CTI 커넥터 구현: AbuseIPDB API 연동 (services/fds/src/engines/cti_connector.py)
- [ ] T069 [US3] 악성 IP 검증 로직 구현 (타임아웃 50ms, Redis 캐싱)
- [ ] T070 [US3] 자체 블랙리스트 관리 API 구현: POST /internal/fds/blacklist (services/fds/src/api/threat.py)

### 자동 차단 로직 (User Story 3)

- [ ] T071 [US3] 고위험 거래 자동 차단 로직 구현 (위험 점수 80-100점)
- [ ] T072 [US3] ReviewQueue 모델 생성 (services/fds/src/models/review_queue.py)
- [ ] T073 [US3] 차단된 거래를 수동 검토 큐에 자동 추가하는 로직 구현

### 보안팀 대시보드 백엔드 (User Story 3)

- [ ] T074 [P] [US3] 관리자 대시보드 백엔드 FastAPI 기본 구조 생성 (services/admin-dashboard/backend/src/main.py)
- [ ] T075 [P] [US3] 실시간 거래 통계 API 구현: GET /v1/dashboard/stats (services/admin-dashboard/backend/src/api/dashboard.py)
- [ ] T076 [P] [US3] 검토 큐 목록 조회 API 구현: GET /v1/review-queue (services/admin-dashboard/backend/src/api/review.py)
- [ ] T077 [US3] 거래 상세 정보 조회 API 구현: GET /v1/transactions/{id} (services/admin-dashboard/backend/src/api/transactions.py)
- [ ] T078 [US3] 차단 해제/승인 API 구현: POST /v1/review-queue/{id}/approve (services/admin-dashboard/backend/src/api/review.py)

### 보안팀 대시보드 프론트엔드 (User Story 3)

- [ ] T079 [P] [US3] 대시보드 메인 페이지 구현 (실시간 지표 표시, services/admin-dashboard/frontend/src/pages/Dashboard.tsx)
- [ ] T080 [P] [US3] 검토 큐 페이지 구현 (차단된 거래 목록, services/admin-dashboard/frontend/src/pages/ReviewQueue.tsx)
- [ ] T081 [US3] 거래 상세 페이지 구현 (위험 요인 시각화, services/admin-dashboard/frontend/src/pages/TransactionDetail.tsx)
- [ ] T082 [US3] 실시간 알림 컴포넌트 구현 (WebSocket 기반, services/admin-dashboard/frontend/src/components/NotificationBell.tsx)

### 통합 및 검증 (User Story 3)

- [ ] T083 [US3] 악성 IP 접속 시 자동 차단 시나리오 검증
- [ ] T084 [US3] 보안팀 대시보드 알림 수신 검증
- [ ] T085 [US3] 수동 검토 및 차단 해제 플로우 검증

**체크포인트**: 모든 P1 사용자 스토리(US1, US2, US3)가 독립적으로 작동해야 합니다. 정상/의심/고위험 거래가 각각 올바르게 처리됩니다.

---

## Phase 6: 사용자 스토리 4 - 관리자의 상품 및 주문 관리 (우선순위: P2)

**목표**: 관리자가 상품을 등록/수정하고, 재고를 관리하며, 주문 상태를 업데이트할 수 있는 백오피스 기능 제공.

**독립 테스트**: 관리자 계정으로 로그인 → 새 상품 등록 → 재고 업데이트 → 주문 목록 조회 → 주문 상태를 "배송 중"으로 변경 → 고객에게 알림 전송 확인.

### 관리자 백엔드 API (User Story 4)

- [ ] T086 [P] [US4] 상품 관리 API 구현: POST /v1/admin/products, PUT /v1/admin/products/{id}, DELETE /v1/admin/products/{id} (services/ecommerce/backend/src/api/admin/products.py)
- [ ] T087 [P] [US4] 재고 관리 API 구현: PATCH /v1/admin/products/{id}/stock (services/ecommerce/backend/src/api/admin/products.py)
- [ ] T088 [P] [US4] 주문 관리 API 구현: GET /v1/admin/orders, PATCH /v1/admin/orders/{id}/status (services/ecommerce/backend/src/api/admin/orders.py)
- [ ] T089 [US4] 회원 관리 API 구현: GET /v1/admin/users, PATCH /v1/admin/users/{id}/status (services/ecommerce/backend/src/api/admin/users.py)
- [ ] T090 [US4] 매출 대시보드 API 구현: GET /v1/admin/dashboard/sales (services/ecommerce/backend/src/api/admin/dashboard.py)

### 관리자 프론트엔드 (User Story 4)

- [ ] T091 [P] [US4] 상품 등록/수정 페이지 구현 (services/ecommerce/frontend/src/pages/admin/ProductEditor.tsx)
- [ ] T092 [P] [US4] 재고 관리 페이지 구현 (services/ecommerce/frontend/src/pages/admin/StockManagement.tsx)
- [ ] T093 [P] [US4] 주문 관리 페이지 구현 (주문 목록, 상태 변경, services/ecommerce/frontend/src/pages/admin/OrderManagement.tsx)
- [ ] T094 [US4] 회원 관리 페이지 구현 (services/ecommerce/frontend/src/pages/admin/UserManagement.tsx)
- [ ] T095 [US4] 매출 대시보드 페이지 구현 (일/주/월별 통계, services/ecommerce/frontend/src/pages/admin/SalesDashboard.tsx)

### 통합 및 검증 (User Story 4)

- [ ] T096 [US4] 상품 CRUD 작업 검증
- [ ] T097 [US4] 주문 상태 변경 및 고객 알림 검증

**체크포인트**: 사용자 스토리 4가 독립적으로 작동하며, 기존 고객 플로우(US1-3)에 영향을 주지 않습니다.

---

## Phase 7: 사용자 스토리 5 - 보안팀의 실시간 모니터링 및 룰 관리 (우선순위: P2)

**목표**: 보안팀이 FDS 탐지 룰을 동적으로 추가/수정하고, A/B 테스트를 실행할 수 있는 운영 도구 제공.

**독립 테스트**: 보안팀 대시보드에서 새로운 탐지 룰 추가 → 코드 배포 없이 즉시 활성화 → 해당 패턴 거래 발생 시 룰 작동 확인 → A/B 테스트 설정 → 양측 성과 지표 비교.

### 룰 관리 백엔드 (User Story 5)

- [ ] T098 [P] [US5] 룰 관리 API 구현: GET /v1/rules, POST /v1/rules, PUT /v1/rules/{id}, DELETE /v1/rules/{id} (services/admin-dashboard/backend/src/api/rules.py)
- [ ] T099 [US5] 룰 활성화/비활성화 API 구현: PATCH /v1/rules/{id}/toggle (services/admin-dashboard/backend/src/api/rules.py)
- [ ] T100 [US5] 룰 엔진에서 동적 룰 로드 로직 구현 (데이터베이스에서 활성 룰 로드 및 적용)

### A/B 테스트 기능 (User Story 5)

- [ ] T101 [P] [US5] ABTest 모델 생성 (services/fds/src/models/ab_test.py)
- [ ] T102 [US5] A/B 테스트 설정 API 구현: POST /v1/ab-tests (services/admin-dashboard/backend/src/api/ab_tests.py)
- [ ] T103 [US5] A/B 테스트 결과 집계 API 구현: GET /v1/ab-tests/{id}/results (services/admin-dashboard/backend/src/api/ab_tests.py)
- [ ] T104 [US5] FDS 평가 시 A/B 테스트 그룹 분할 로직 구현

### 보안팀 프론트엔드 (User Story 5)

- [ ] T105 [P] [US5] 룰 관리 페이지 구현 (룰 목록, 추가/수정, services/admin-dashboard/frontend/src/pages/RuleManagement.tsx)
- [ ] T106 [US5] A/B 테스트 설정 페이지 구현 (services/admin-dashboard/frontend/src/pages/ABTestSetup.tsx)
- [ ] T107 [US5] A/B 테스트 결과 대시보드 구현 (정탐률, 오탐률 비교, services/admin-dashboard/frontend/src/pages/ABTestResults.tsx)

### 통합 및 검증 (User Story 5)

- [ ] T108 [US5] 새 룰 추가 및 즉시 적용 검증
- [ ] T109 [US5] A/B 테스트 실행 및 결과 집계 검증

**체크포인트**: 사용자 스토리 5가 독립적으로 작동하며, 보안팀이 룰을 동적으로 관리할 수 있습니다.

---

## Phase 8: 사용자 스토리 6 - ML 모델 학습 및 성능 개선 (우선순위: P3)

**목표**: 축적된 거래 데이터를 기반으로 ML 모델을 주기적으로 재학습하고, 새 모델을 점진적으로 배포하여 탐지 정확도를 지속적으로 개선.

**독립 테스트**: 일주일간의 거래 데이터 수집 → ML 재학습 트리거 → 새 모델 성능 비교 리포트 생성 → 카나리 배포 실행 → 성능 모니터링 → 롤백 기능 검증.

### ML 모델 학습 (User Story 6)

- [ ] T110 [P] [US6] MLModel 모델 생성 (services/ml-service/src/models/ml_model.py)
- [ ] T111 [P] [US6] FraudCase 모델 생성 (services/ml-service/src/models/fraud_case.py)
- [ ] T112 [US6] 학습 데이터 전처리 파이프라인 구현 (services/ml-service/src/data/preprocessing.py)
- [ ] T113 [US6] Feature Engineering 로직 구현 (services/ml-service/src/data/feature_engineering.py)
- [ ] T114 [US6] Isolation Forest 학습 스크립트 구현 (services/ml-service/src/training/train_isolation_forest.py)
- [ ] T115 [US6] LightGBM 학습 스크립트 구현 (services/ml-service/src/training/train_lightgbm.py)
- [ ] T116 [US6] 모델 평가 스크립트 구현 (정확도, 정밀도, 재현율, F1 스코어, services/ml-service/src/evaluation/evaluate.py)

### ML 모델 배포 (User Story 6)

- [ ] T117 [US6] 모델 버전 관리 시스템 구현 (MLflow 연동, services/ml-service/src/deployment/version_manager.py)
- [ ] T118 [US6] 카나리 배포 로직 구현 (트래픽 일부에만 새 모델 적용, services/ml-service/src/deployment/canary_deploy.py)
- [ ] T119 [US6] 모델 롤백 로직 구현 (services/ml-service/src/deployment/rollback.py)
- [ ] T120 [US6] FDS 엔진에 ML 모델 통합 (services/fds/src/engines/ml_engine.py)

### ML 서비스 API (User Story 6)

- [ ] T121 [P] [US6] 모델 학습 트리거 API 구현: POST /v1/ml/train (services/ml-service/src/api/training.py)
- [ ] T122 [P] [US6] 모델 배포 API 구현: POST /v1/ml/deploy (services/ml-service/src/api/deployment.py)
- [ ] T123 [US6] 모델 성능 비교 API 구현: GET /v1/ml/models/compare (services/ml-service/src/api/evaluation.py)

### 관리자 대시보드 통합 (User Story 6)

- [ ] T124 [US6] ML 모델 관리 페이지 구현 (모델 목록, 학습 트리거, services/admin-dashboard/frontend/src/pages/MLModelManagement.tsx)
- [ ] T125 [US6] 모델 성능 비교 대시보드 구현 (services/admin-dashboard/frontend/src/pages/ModelComparison.tsx)

### 통합 및 검증 (User Story 6)

- [ ] T126 [US6] 모델 재학습 파이프라인 검증
- [ ] T127 [US6] 카나리 배포 및 롤백 시나리오 검증

**체크포인트**: 모든 사용자 스토리가 독립적으로 작동합니다. ML 모델이 주기적으로 개선되며, FDS 정확도가 향상됩니다.

---

## Phase 9: 마무리 및 교차 기능

**목적**: 여러 사용자 스토리에 영향을 미치는 개선 사항

### 성능 최적화

- [ ] T128 [P] 데이터베이스 쿼리 최적화 (인덱스 활용, N+1 문제 해결)
- [ ] T129 [P] Redis 캐싱 전략 확대 (상품 목록, CTI 결과 등)
- [ ] T130 [P] FDS 평가 시간 모니터링 및 100ms 목표 달성 검증

### 보안 강화

- [ ] T131 [P] PCI-DSS 준수 검증 (결제 정보 토큰화, 민감 데이터 로그 금지)
- [ ] T132 [P] SQL Injection, XSS 등 OWASP Top 10 취약점 점검
- [ ] T133 Rate Limiting 구현 (Nginx 및 FastAPI 레벨)

### 모니터링 및 로깅

- [ ] T134 [P] Prometheus 메트릭 수집 설정 (services/ecommerce/backend, services/fds)
- [ ] T135 [P] Grafana 대시보드 구성 (FDS 평가 시간, 거래 처리량, 에러율)
- [ ] T136 Sentry 에러 트래킹 통합

### 배포 및 인프라

- [ ] T137 [P] 각 서비스별 Dockerfile 작성 (Multi-stage build)
- [ ] T138 [P] Kubernetes 매니페스트 작성 (Deployment, Service, Ingress)
- [ ] T139 Nginx API Gateway 설정 (라우팅, HTTPS 종료)
- [ ] T140 CI/CD 파이프라인 구성 (GitHub Actions: 테스트, 빌드, 배포)

### 문서화

- [ ] T141 [P] API 문서 자동 생성 (OpenAPI/Swagger UI)
- [ ] T142 [P] 아키텍처 다이어그램 업데이트 (docs/architecture/)
- [ ] T143 CLAUDE.md 최종 업데이트 (프로젝트 현황 반영)

### 최종 검증

- [ ] T144 quickstart.md 가이드 전체 실행 검증
- [ ] T145 전체 사용자 플로우 E2E 테스트 (Playwright)
- [ ] T146 성능 목표 달성 검증 (FDS 100ms, API 200ms, 1000 TPS)

---

## 의존성 및 실행 순서

### Phase 의존성

- **Phase 1 (프로젝트 초기 설정)**: 의존성 없음 - 즉시 시작 가능
- **Phase 2 (기반 인프라)**: Phase 1 완료 후 - **모든 사용자 스토리를 차단**
- **Phase 3-8 (사용자 스토리)**: 모두 Phase 2 완료 후 시작 가능
  - 사용자 스토리는 병렬로 진행 가능 (팀 인력이 있는 경우)
  - 또는 우선순위 순서대로 순차 진행 (P1 → P2 → P3)
- **Phase 9 (마무리)**: 원하는 사용자 스토리가 모두 완료된 후

### 사용자 스토리 의존성

- **사용자 스토리 1 (P1)**: Phase 2 완료 후 시작 가능 - 다른 스토리에 대한 의존성 없음
- **사용자 스토리 2 (P1)**: Phase 2 완료 후 시작 가능 - US1과 통합되지만 독립적으로 테스트 가능
- **사용자 스토리 3 (P1)**: Phase 2 완료 후 시작 가능 - US1, US2와 통합되지만 독립적으로 테스트 가능
- **사용자 스토리 4 (P2)**: Phase 2 완료 후 시작 가능 - US1의 모델을 사용하지만 독립적
- **사용자 스토리 5 (P2)**: Phase 2 완료 후 시작 가능 - US3의 FDS 인프라를 확장하지만 독립적
- **사용자 스토리 6 (P3)**: Phase 2 완료 후 시작 가능 - 데이터 축적 필요하지만 독립적으로 개발 가능

### 각 사용자 스토리 내부

- 모델 → 서비스 → API 엔드포인트 → 프론트엔드 순서
- 핵심 구현 → 통합 → 검증 순서
- 스토리 완료 후 다음 우선순위로 이동

### 병렬 실행 기회

- Phase 1의 모든 [P] 태스크는 병렬 실행 가능
- Phase 2의 모든 [P] 태스크는 병렬 실행 가능 (Phase 2 내에서)
- Phase 2 완료 후, 모든 사용자 스토리를 병렬로 시작 가능 (팀 인력이 있는 경우)
- 각 사용자 스토리 내 [P] 태스크는 병렬 실행 가능
- 서로 다른 사용자 스토리는 서로 다른 팀원이 병렬로 작업 가능

---

## 병렬 실행 예시: 사용자 스토리 1

```bash
# 모델 생성을 동시에 실행:
Task: "User 모델 생성 (services/ecommerce/backend/src/models/user.py)"
Task: "Product 모델 생성 (services/ecommerce/backend/src/models/product.py)"
Task: "Cart 및 CartItem 모델 생성 (services/ecommerce/backend/src/models/cart.py)"
Task: "Order 및 OrderItem 모델 생성 (services/ecommerce/backend/src/models/order.py)"
Task: "Payment 모델 생성 (services/ecommerce/backend/src/models/payment.py)"

# 백엔드 서비스를 동시에 실행:
Task: "UserService 구현 (services/ecommerce/backend/src/services/user_service.py)"
Task: "ProductService 구현 (services/ecommerce/backend/src/services/product_service.py)"

# API 엔드포인트를 동시에 실행:
Task: "인증 API 구현 (services/ecommerce/backend/src/api/auth.py)"
Task: "상품 API 구현 (services/ecommerce/backend/src/api/products.py)"

# 프론트엔드 페이지를 동시에 실행:
Task: "회원가입 페이지 구현 (services/ecommerce/frontend/src/pages/Register.tsx)"
Task: "로그인 페이지 구현 (services/ecommerce/frontend/src/pages/Login.tsx)"
Task: "상품 목록 페이지 구현 (services/ecommerce/frontend/src/pages/ProductList.tsx)"
Task: "상품 상세 페이지 구현 (services/ecommerce/frontend/src/pages/ProductDetail.tsx)"
```

---

## 구현 전략

### MVP 우선 (사용자 스토리 1만)

1. Phase 1 완료: 프로젝트 초기 설정
2. Phase 2 완료: 기반 인프라 (중요 - 모든 스토리를 차단)
3. Phase 3 완료: 사용자 스토리 1
4. **중단 및 검증**: 사용자 스토리 1을 독립적으로 테스트
5. 준비되면 배포/데모

### 점진적 제공

1. 프로젝트 초기 설정 + 기반 인프라 완료 → 기반 준비 완료
2. 사용자 스토리 1 추가 → 독립 테스트 → 배포/데모 (MVP!)
3. 사용자 스토리 2 추가 → 독립 테스트 → 배포/데모
4. 사용자 스토리 3 추가 → 독립 테스트 → 배포/데모
5. 사용자 스토리 4 추가 → 독립 테스트 → 배포/데모
6. 사용자 스토리 5 추가 → 독립 테스트 → 배포/데모
7. 사용자 스토리 6 추가 → 독립 테스트 → 배포/데모
8. 각 스토리는 이전 스토리를 손상시키지 않고 가치를 추가

### 병렬 팀 전략

여러 개발자가 있는 경우:

1. 팀이 프로젝트 초기 설정 + 기반 인프라를 함께 완료
2. 기반 인프라 완료 후:
   - 개발자 A: 사용자 스토리 1
   - 개발자 B: 사용자 스토리 2
   - 개발자 C: 사용자 스토리 3
3. 스토리가 독립적으로 완료되고 통합됨

---

## 참고사항

- [P] 태스크 = 서로 다른 파일, 의존성 없음
- [Story] 레이블은 태스크를 특정 사용자 스토리에 매핑하여 추적 가능
- 각 사용자 스토리는 독립적으로 완료 및 테스트 가능해야 함
- 각 태스크 또는 논리적 그룹 후 커밋
- 체크포인트에서 중단하여 스토리를 독립적으로 검증
- 피해야 할 사항: 모호한 태스크, 동일 파일 충돌, 독립성을 깨는 스토리 간 의존성

---

## 요약

- **총 태스크 수**: 146개
- **사용자 스토리별 태스크 수**:
  - 프로젝트 초기 설정 (Phase 1): 10개
  - 기반 인프라 (Phase 2): 11개
  - 사용자 스토리 1 (P1): 28개
  - 사용자 스토리 2 (P1): 16개
  - 사용자 스토리 3 (P1): 19개
  - 사용자 스토리 4 (P2): 12개
  - 사용자 스토리 5 (P2): 12개
  - 사용자 스토리 6 (P3): 18개
  - 마무리 및 교차 기능 (Phase 9): 19개

- **병렬 실행 기회**: 각 Phase 내 [P] 태스크, Phase 2 완료 후 모든 사용자 스토리
- **MVP 범위**: Phase 1 + Phase 2 + Phase 3 (사용자 스토리 1)
- **형식 검증**: 모든 태스크가 체크리스트 형식을 따릅니다 (체크박스, ID, 레이블, 파일 경로)
