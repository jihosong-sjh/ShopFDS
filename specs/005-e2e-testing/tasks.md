# Implementation Tasks: E2E 테스트 자동화 및 시스템 복원력 검증

**Feature Branch**: `005-e2e-testing`
**Created**: 2025-11-20
**Status**: Ready for Implementation

## Overview

E2E 테스트 자동화 및 시스템 복원력 검증 기능 구현 작업 목록입니다. Playwright를 활용한 20개 핵심 사용자 플로우 자동 검증, Istio 기반 카나리 배포(10% → 50% → 100% 점진적 전환), Litmus Chaos를 통한 5가지 장애 시나리오 복원력 테스트, Newman API 통합 테스트, k6 성능 테스트를 통합하여 CI/CD 파이프라인에서 자동 실행합니다.

**목표**:
- E2E 테스트 100% 통과율
- 카나리 배포 자동 롤백 30초 이내
- 시스템 장애 복구 30초 이내
- 배포 신뢰도 60% -> 95%+ 향상
- 프로덕션 장애 80% 감소

## Task Notation

- `[ ]` : 미완료 작업
- `[x]` : 완료된 작업
- `[P]` : 병렬 실행 가능 (서로 다른 파일, 의존성 없음)
- `[US1]` : User Story 1 (E2E 테스트 자동화)
- `[US2]` : User Story 2 (카나리 배포)
- `[US3]` : User Story 3 (Chaos Engineering)
- `[US4]` : User Story 4 (API 통합 테스트)
- `[US5]` : User Story 5 (성능 테스트)

## Dependencies

**User Story 완료 순서** (MVP 중심):
1. **Phase 0-1**: 프로젝트 초기화 및 인프라 구축 (필수)
2. **Phase 2**: Foundational 공통 인프라 (필수)
3. **Phase 3**: User Story 1 - E2E 테스트 자동화 (P1, MVP)
4. **Phase 4**: User Story 2 - 카나리 배포 (P1)
5. **Phase 5**: User Story 3 - Chaos Engineering (P2)
6. **Phase 6**: User Story 4 - API 통합 테스트 (P3)
7. **Phase 7**: User Story 5 - 성능 테스트 (P3)
8. **Phase 8**: 통합 및 최종 검증

**MVP (Minimum Viable Product)**: Phase 0-3까지 완료하면 핵심 E2E 테스트 자동화 기능이 작동합니다.

---

## Phase 0: 프로젝트 초기화 (Week 1, Day 1-2)

**목표**: 프로젝트 디렉토리 구조 생성, 의존성 설치, 기본 설정 파일 작성

### 디렉토리 구조 생성

- [ ] T001 Create E2E testing directory structure in tests/e2e/
- [ ] T002 Create API testing directory structure in tests/api/
- [ ] T003 Create performance testing directory structure in tests/performance/
- [ ] T004 Create canary deployment directory structure in infrastructure/k8s/canary/
- [ ] T005 Create chaos engineering directory structure in infrastructure/chaos/
- [ ] T006 Create documentation directory structure in docs/

### Playwright 설정

- [ ] T007 Initialize Playwright project in tests/e2e/package.json
- [ ] T008 Install Playwright dependencies (@playwright/test 1.40+)
- [ ] T009 Create Playwright configuration in tests/e2e/playwright.config.ts
- [ ] T010 Setup Playwright browsers (Chromium, Firefox, WebKit)
- [ ] T011 Create .gitignore for Playwright artifacts in tests/e2e/.gitignore

### API 테스트 설정

- [ ] T012 [P] Install Newman globally (npm install -g newman 6.0+)
- [ ] T013 [P] Install Supertest dependencies in tests/api/package.json
- [ ] T014 [P] Create Newman runner script in tests/api/run-newman.sh

### 성능 테스트 설정

- [ ] T015 [P] Install k6 CLI (0.48+) via package manager
- [ ] T016 [P] Create k6 configuration in tests/performance/config/

### 스크립트 및 문서

- [ ] T017 [P] Create setup script for Istio in scripts/setup-istio.sh
- [ ] T018 [P] Create setup script for Flagger in scripts/setup-flagger.sh
- [ ] T019 [P] Create setup script for Litmus Chaos in scripts/setup-litmus.sh
- [ ] T020 [P] Create README in docs/e2e-testing/README.md
- [ ] T021 [P] Create README in docs/canary-deployment/README.md
- [ ] T022 [P] Create README in docs/chaos-engineering/README.md
- [ ] T023 [P] Create README in docs/performance-testing/README.md

---

## Phase 1: 인프라 구축 (Week 1, Day 3-5)

**목표**: Kubernetes 클러스터 확인, Istio Service Mesh 설치, Prometheus/Grafana 통합

### Kubernetes 클러스터 확인

- [ ] T024 Verify Kubernetes cluster version (1.28+) and connectivity
- [ ] T025 Create namespaces for services (ecommerce, fds, ml-service, admin-dashboard)
- [ ] T026 Setup RBAC for testing tools (ServiceAccounts, Roles, RoleBindings)

### Istio Service Mesh 설치

- [ ] T027 Install Istio operator (1.20+) in infrastructure/k8s/istio/
- [ ] T028 Deploy Istio control plane (istiod) in istio-system namespace
- [ ] T029 Enable Istio sidecar injection for service namespaces
- [ ] T030 Create Istio Gateway for external traffic in infrastructure/k8s/istio/gateway.yaml
- [ ] T031 Verify Istio installation with istioctl verify-install

### Prometheus/Grafana 통합

- [ ] T032 Install Prometheus ServiceMonitor for Istio metrics
- [ ] T033 Configure Grafana Istio dashboards (Service Mesh, Traffic)
- [ ] T034 Setup Kiali for service mesh visualization
- [ ] T035 Test Prometheus scraping of Istio metrics

---

## Phase 2: Foundational 공통 인프라 (Week 2, Day 1-3)

**목표**: 테스트 데이터베이스, 공통 유틸리티, CI/CD 기본 워크플로우 구축

### 테스트 데이터베이스 스키마

- [ ] T036 Create Alembic migration for E2E Test Scenario table in services/ecommerce/backend/alembic/versions/
- [ ] T037 Create Alembic migration for E2E Test Run table
- [ ] T038 Create Alembic migration for Canary Deployment table
- [ ] T039 Create Alembic migration for Chaos Experiment table
- [ ] T040 Create Alembic migration for Performance Test table
- [ ] T041 Create Alembic migration for API Test Suite table
- [ ] T042 Run Alembic upgrade head to apply migrations
- [ ] T043 Verify database schema with psql or pgAdmin

### SQLAlchemy 모델

- [ ] T044 [P] Create E2ETestScenario model in services/ecommerce/backend/src/models/e2e_test_scenario.py
- [ ] T045 [P] Create E2ETestRun model in services/ecommerce/backend/src/models/e2e_test_run.py
- [ ] T046 [P] Create CanaryDeployment model in services/ecommerce/backend/src/models/canary_deployment.py
- [ ] T047 [P] Create ChaosExperiment model in services/ecommerce/backend/src/models/chaos_experiment.py
- [ ] T048 [P] Create PerformanceTest model in services/ecommerce/backend/src/models/performance_test.py
- [ ] T049 [P] Create APITestSuite model in services/ecommerce/backend/src/models/api_test_suite.py

### 공통 유틸리티

- [ ] T050 [P] Create test data generator in tests/e2e/fixtures/data-generator.ts
- [ ] T051 [P] Create authentication helper in tests/e2e/utils/auth-helper.ts
- [ ] T052 [P] Create environment config loader in tests/e2e/utils/config-loader.ts

### CI/CD 기본 워크플로우

- [ ] T053 Create GitHub Actions workflow skeleton in .github/workflows/e2e-tests.yml
- [ ] T054 [P] Create GitHub Actions workflow skeleton in .github/workflows/api-tests.yml
- [ ] T055 [P] Create GitHub Actions workflow skeleton in .github/workflows/performance-tests.yml
- [ ] T056 [P] Create GitHub Actions workflow skeleton in .github/workflows/canary-deployment.yml
- [ ] T057 [P] Create GitHub Actions workflow skeleton in .github/workflows/chaos-experiments.yml

---

## Phase 3: User Story 1 - E2E 테스트 자동화 (P1) (Week 2-3, Day 4-10)

**Story Goal**: 개발팀은 매 배포 전 핵심 사용자 플로우(회원가입, 로그인, 상품 검색, 장바구니, 결제)가 정상 작동함을 자동으로 검증하여 프로덕션 장애를 사전에 방지할 수 있어야 한다.

**Independent Test**: E2E 테스트 슈트를 실행하여 20개 핵심 시나리오가 모두 통과하는지 확인하면 독립적으로 검증 가능하다.

### Page Object Model 구현

- [ ] T058 [US1] Create LoginPage POM in tests/e2e/pages/LoginPage.ts
- [ ] T059 [US1] [P] Create RegisterPage POM in tests/e2e/pages/RegisterPage.ts
- [ ] T060 [US1] [P] Create ProductListPage POM in tests/e2e/pages/ProductListPage.ts
- [ ] T061 [US1] [P] Create ProductDetailPage POM in tests/e2e/pages/ProductDetailPage.ts
- [ ] T062 [US1] [P] Create CartPage POM in tests/e2e/pages/CartPage.ts
- [ ] T063 [US1] [P] Create CheckoutPage POM in tests/e2e/pages/CheckoutPage.ts
- [ ] T064 [US1] [P] Create OrderConfirmationPage POM in tests/e2e/pages/OrderConfirmationPage.ts
- [ ] T065 [US1] [P] Create DashboardPage POM in tests/e2e/pages/DashboardPage.ts

### E2E 테스트 시나리오 (20개)

**Authentication (인증)**

- [ ] T066 [US1] Implement user registration test in tests/e2e/scenarios/auth.spec.ts
- [ ] T067 [US1] Implement user login test in tests/e2e/scenarios/auth.spec.ts
- [ ] T068 [US1] Implement user logout test in tests/e2e/scenarios/auth.spec.ts
- [ ] T069 [US1] Implement password reset test in tests/e2e/scenarios/auth.spec.ts

**Product Browsing (상품 검색)**

- [ ] T070 [US1] [P] Implement product list display test in tests/e2e/scenarios/products.spec.ts
- [ ] T071 [US1] [P] Implement product search test in tests/e2e/scenarios/products.spec.ts
- [ ] T072 [US1] [P] Implement product filter test in tests/e2e/scenarios/products.spec.ts
- [ ] T073 [US1] [P] Implement product detail view test in tests/e2e/scenarios/products.spec.ts

**Shopping Cart (장바구니)**

- [ ] T074 [US1] [P] Implement add to cart test in tests/e2e/scenarios/cart.spec.ts
- [ ] T075 [US1] [P] Implement update cart quantity test in tests/e2e/scenarios/cart.spec.ts
- [ ] T076 [US1] [P] Implement remove from cart test in tests/e2e/scenarios/cart.spec.ts
- [ ] T077 [US1] [P] Implement cart total calculation test in tests/e2e/scenarios/cart.spec.ts

**Checkout & Payment (결제)**

- [ ] T078 [US1] [P] Implement checkout flow test in tests/e2e/scenarios/checkout.spec.ts
- [ ] T079 [US1] [P] Implement payment information entry test in tests/e2e/scenarios/checkout.spec.ts
- [ ] T080 [US1] [P] Implement low risk order completion test (10,000원) in tests/e2e/scenarios/checkout.spec.ts
- [ ] T081 [US1] [P] Implement high risk order with OTP test (5,000,000원) in tests/e2e/scenarios/checkout.spec.ts

**FDS Integration (사기 탐지)**

- [ ] T082 [US1] [P] Implement FDS low risk approval test in tests/e2e/scenarios/fds-integration.spec.ts
- [ ] T083 [US1] [P] Implement FDS high risk OTP verification test in tests/e2e/scenarios/fds-integration.spec.ts
- [ ] T084 [US1] [P] Implement FDS rejection test in tests/e2e/scenarios/fds-integration.spec.ts

**Order Management (주문 관리)**

- [ ] T085 [US1] [P] Implement order history view test in tests/e2e/scenarios/orders.spec.ts

### Cross-Browser & Responsive Testing

- [ ] T086 [US1] Configure Chromium browser tests in playwright.config.ts
- [ ] T087 [US1] Configure Firefox browser tests in playwright.config.ts
- [ ] T088 [US1] Configure WebKit (Safari) browser tests in playwright.config.ts
- [ ] T089 [US1] Configure desktop viewport (1920x1080) in playwright.config.ts
- [ ] T090 [US1] Configure mobile viewport (375x667) in playwright.config.ts

### Fixtures & Utilities

- [ ] T091 [US1] Create authenticated page fixture in tests/e2e/fixtures/authenticated-page.ts
- [ ] T092 [US1] [P] Create test user factory in tests/e2e/fixtures/user-factory.ts
- [ ] T093 [US1] [P] Create test product factory in tests/e2e/fixtures/product-factory.ts
- [ ] T094 [US1] [P] Create network mock helper in tests/e2e/utils/network-mock.ts

### CI/CD Integration

- [ ] T095 [US1] Implement E2E test workflow in .github/workflows/e2e-tests.yml
- [ ] T096 [US1] Configure Playwright Docker container for CI
- [ ] T097 [US1] Setup screenshot/video artifact upload on failure
- [ ] T098 [US1] Configure test retry (2회 재시도) in CI environment
- [ ] T099 [US1] Add E2E test status badge to README.md

### Testing & Validation

- [ ] T100 [US1] Run E2E test suite locally (npx playwright test)
- [ ] T101 [US1] Verify 20개 시나리오 100% 통과율
- [ ] T102 [US1] Verify 전체 실행 시간 10분 이내
- [ ] T103 [US1] Verify cross-browser compatibility (Chrome, Firefox, Safari)
- [ ] T104 [US1] Verify responsive design (desktop, mobile)

---

## Phase 4: User Story 2 - 카나리 배포 (P1) (Week 4-5, Day 11-17)

**Story Goal**: 운영팀은 새 버전을 배포할 때 전체 트래픽을 한 번에 전환하지 않고 10% → 50% → 100% 점진적으로 전환하여, 문제 발생 시 즉시 이전 버전으로 롤백할 수 있어야 한다.

**Independent Test**: 카나리 배포를 시작하고 트래픽 분할 비율을 확인하며, 에러율 모니터링을 통해 자동 롤백이 작동하는지 검증할 수 있다.

### Istio VirtualService & DestinationRule

- [ ] T105 [US2] Create VirtualService for ecommerce-backend in infrastructure/k8s/canary/istio/virtualservice-ecommerce.yaml
- [ ] T106 [US2] [P] Create VirtualService for fds in infrastructure/k8s/canary/istio/virtualservice-fds.yaml
- [ ] T107 [US2] [P] Create VirtualService for ml-service in infrastructure/k8s/canary/istio/virtualservice-ml-service.yaml
- [ ] T108 [US2] [P] Create VirtualService for admin-dashboard in infrastructure/k8s/canary/istio/virtualservice-admin-dashboard.yaml
- [ ] T109 [US2] Create DestinationRule for ecommerce-backend in infrastructure/k8s/canary/istio/destinationrule-ecommerce.yaml
- [ ] T110 [US2] [P] Create DestinationRule for fds in infrastructure/k8s/canary/istio/destinationrule-fds.yaml
- [ ] T111 [US2] [P] Create DestinationRule for ml-service in infrastructure/k8s/canary/istio/destinationrule-ml-service.yaml
- [ ] T112 [US2] [P] Create DestinationRule for admin-dashboard in infrastructure/k8s/canary/istio/destinationrule-admin-dashboard.yaml

### Flagger 설치 및 설정

- [ ] T113 [US2] Install Flagger (1.35+) via Helm in flagger-system namespace
- [ ] T114 [US2] Configure Flagger to use Istio provider
- [ ] T115 [US2] Create Prometheus MetricTemplate for error rate in infrastructure/k8s/canary/flagger/metric-error-rate.yaml
- [ ] T116 [US2] Create Prometheus MetricTemplate for latency P95 in infrastructure/k8s/canary/flagger/metric-latency-p95.yaml

### Canary CRD 정의 (4개 서비스)

- [ ] T117 [US2] Create Canary CRD for ecommerce-backend in infrastructure/k8s/canary/flagger/canary-ecommerce.yaml
- [ ] T118 [US2] [P] Create Canary CRD for fds in infrastructure/k8s/canary/flagger/canary-fds.yaml
- [ ] T119 [US2] [P] Create Canary CRD for ml-service in infrastructure/k8s/canary/flagger/canary-ml-service.yaml
- [ ] T120 [US2] [P] Create Canary CRD for admin-dashboard in infrastructure/k8s/canary/flagger/canary-admin-dashboard.yaml

### Load Testing Webhook

- [ ] T121 [US2] Deploy Flagger Load Tester in flagger-system namespace
- [ ] T122 [US2] Configure load testing webhook in Canary CRDs

### Prometheus 메트릭 통합

- [ ] T123 [US2] Verify Istio metrics available in Prometheus (istio_requests_total)
- [ ] T124 [US2] Create PromQL queries for error rate calculation
- [ ] T125 [US2] Create PromQL queries for P95 latency calculation
- [ ] T126 [US2] Test metric thresholds (error rate <5%, latency <200ms)

### Grafana 대시보드

- [ ] T127 [US2] Create Grafana dashboard for canary deployments in infrastructure/k8s/canary/monitoring/grafana-dashboard.json
- [ ] T128 [US2] Add traffic weight visualization panel
- [ ] T129 [US2] Add error rate comparison panel (stable vs canary)
- [ ] T130 [US2] Add latency comparison panel (stable vs canary)

### CI/CD 카나리 배포 자동화

- [ ] T131 [US2] Implement canary deployment workflow in .github/workflows/canary-deployment.yml
- [ ] T132 [US2] Add Docker image build and push step
- [ ] T133 [US2] Add kubectl set image command to trigger canary
- [ ] T134 [US2] Add kubectl wait for canary promotion step (timeout: 30m)
- [ ] T135 [US2] Add Slack notification on canary success/failure

### Testing & Validation

- [ ] T136 [US2] Deploy test version with intentional error to trigger rollback
- [ ] T137 [US2] Verify 10% -> 50% -> 100% 트래픽 점진적 전환
- [ ] T138 [US2] Verify 에러율 5% 초과 시 자동 롤백 (30초 이내)
- [ ] T139 [US2] Verify stable version remains untouched during rollback
- [ ] T140 [US2] Verify Grafana dashboard shows canary metrics correctly

---

## Phase 5: User Story 3 - Chaos Engineering (P2) (Week 6-7, Day 18-24)

**Story Goal**: SRE 팀은 프로덕션과 유사한 환경에서 의도적으로 장애를 주입(Pod 종료, 네트워크 지연, DB 연결 실패)하여 시스템이 30초 이내에 자동 복구되는지 검증할 수 있어야 한다.

**Independent Test**: 장애 시뮬레이션 도구를 사용하여 특정 장애 시나리오를 실행하고, 시스템이 30초 이내에 정상 상태로 복구되는지 모니터링으로 확인할 수 있다.

### Litmus Chaos 설치

- [ ] T141 [US3] Install Litmus Chaos Operator (3.8+) in litmus namespace
- [ ] T142 [US3] Create ChaosServiceAccount for experiments in infrastructure/chaos/rbac/chaos-service-account.yaml
- [ ] T143 [US3] Create ClusterRole for Litmus experiments in infrastructure/chaos/rbac/chaos-cluster-role.yaml
- [ ] T144 [US3] Create ClusterRoleBinding for Litmus experiments in infrastructure/chaos/rbac/chaos-cluster-role-binding.yaml

### Chaos Experiments (5가지)

**1. Pod Delete (Pod 종료)**

- [ ] T145 [US3] Create Pod Delete experiment for FDS in infrastructure/chaos/experiments/fds-pod-delete.yaml
- [ ] T146 [US3] Configure chaos duration 30초, interval 10초
- [ ] T147 [US3] Add cmdProbe to verify pod recovery (kubectl get pods)
- [ ] T148 [US3] Test FDS Pod Delete experiment (kubectl apply -f)

**2. Network Latency (네트워크 지연)**

- [ ] T149 [US3] [P] Create Network Latency experiment for FDS in infrastructure/chaos/experiments/fds-network-latency.yaml
- [ ] T150 [US3] [P] Configure network latency 500ms, jitter 50ms, duration 60초
- [ ] T151 [US3] [P] Add httpProbe to verify API health endpoint responds
- [ ] T152 [US3] [P] Test FDS Network Latency experiment

**3. Database Connection Loss (DB 연결 실패)**

- [ ] T153 [US3] [P] Create Network Loss experiment for Ecommerce in infrastructure/chaos/experiments/ecommerce-db-connection-loss.yaml
- [ ] T154 [US3] [P] Configure packet loss 100% to PostgreSQL port 5432, duration 30초
- [ ] T155 [US3] [P] Add cmdProbe to verify connection pool recovery
- [ ] T156 [US3] [P] Test Ecommerce DB Connection Loss experiment

**4. Redis Down (캐시 다운)**

- [ ] T157 [US3] [P] Create Pod Delete experiment for Redis in infrastructure/chaos/experiments/redis-pod-delete.yaml
- [ ] T158 [US3] [P] Configure chaos duration 30초 for Redis pod
- [ ] T159 [US3] [P] Add k8sProbe to verify Redis pod restart
- [ ] T160 [US3] [P] Test Redis Down experiment and cache fallback to DB

**5. Resource Stress (리소스 제한)**

- [ ] T161 [US3] [P] Create CPU Stress experiment for FDS in infrastructure/chaos/experiments/fds-cpu-stress.yaml
- [ ] T162 [US3] [P] Configure CPU cores 2, duration 120초
- [ ] T163 [US3] [P] Add k8sProbe to verify HPA scaling (replicas > 1)
- [ ] T164 [US3] [P] Test FDS CPU Stress experiment and HPA autoscaling

### Chaos Workflow (복합 시나리오)

- [ ] T165 [US3] Create Chaos Workflow for Black Friday scenario in infrastructure/chaos/workflows/black-friday-chaos.yaml
- [ ] T166 [US3] Add Pod Delete + Network Latency + CPU Stress sequential steps
- [ ] T167 [US3] Configure workflow to run all 3 experiments in sequence
- [ ] T168 [US3] Test Black Friday Chaos Workflow end-to-end

### Prometheus Probe Integration

- [ ] T169 [US3] Create PromQL probe for error rate <5% in chaos experiments
- [ ] T170 [US3] Create PromQL probe for P95 latency <200ms in chaos experiments
- [ ] T171 [US3] Add promProbe to all chaos experiments

### ChaosCenter UI Setup

- [ ] T172 [US3] Deploy ChaosCenter frontend (optional, if needed for visualization)
- [ ] T173 [US3] Access ChaosCenter UI at http://litmus-frontend:9091
- [ ] T174 [US3] Verify experiment history and metrics visualization

### CI/CD Chaos 실험 자동화

- [ ] T175 [US3] Implement chaos experiments workflow in .github/workflows/chaos-experiments.yml
- [ ] T176 [US3] Add kubectl apply for chaos experiments
- [ ] T177 [US3] Add kubectl wait for ChaosEngineCompleted condition (timeout: 5m)
- [ ] T178 [US3] Add Slack notification on chaos experiment completion

### Testing & Validation

- [ ] T179 [US3] Run all 5 chaos experiments in Staging environment
- [ ] T180 [US3] Verify 30초 이내 자동 복구 for all experiments
- [ ] T181 [US3] Verify error rate <5% during recovery
- [ ] T182 [US3] Verify Prometheus metrics show recovery timeline
- [ ] T183 [US3] Document recovery time for each experiment type

---

## Phase 6: User Story 4 - API 통합 테스트 (P3) (Week 8-9, Day 25-31)

**Story Goal**: QA 팀은 서비스 간 통신(Ecommerce ↔ FDS ↔ ML)이 엔드투엔드로 정상 작동하는지 자동화 테스트로 검증할 수 있어야 한다.

**Independent Test**: API 테스트 컬렉션을 실행하여 서비스 간 API 호출이 정상적으로 완료되는지 확인할 수 있다.

### Postman 컬렉션 작성 (Newman)

**Ecommerce API (15개 엔드포인트)**

- [ ] T184 [US4] Create Postman collection for Ecommerce API in tests/api/collections/ecommerce-api.postman_collection.json
- [ ] T185 [US4] Add Authentication endpoints (register, login, logout, refresh token)
- [ ] T186 [US4] Add Product endpoints (list, search, filter, detail)
- [ ] T187 [US4] Add Cart endpoints (add, update, remove, get)
- [ ] T188 [US4] Add Order endpoints (create, get, list, update status)

**FDS API (5개 엔드포인트)**

- [ ] T189 [US4] [P] Create Postman collection for FDS API in tests/api/collections/fds-api.postman_collection.json
- [ ] T190 [US4] [P] Add Transaction evaluation endpoint (POST /api/v1/fds/evaluate)
- [ ] T191 [US4] [P] Add Risk assessment endpoint (GET /api/v1/fds/risk/{transaction_id})
- [ ] T192 [US4] [P] Add CTI lookup endpoint (GET /api/v1/fds/cti/{ip_address})

**ML Service API (10개 엔드포인트)**

- [ ] T193 [US4] [P] Create Postman collection for ML Service API in tests/api/collections/ml-service-api.postman_collection.json
- [ ] T194 [US4] [P] Add Model training endpoints (POST /api/v1/ml/train)
- [ ] T195 [US4] [P] Add Model evaluation endpoints (GET /api/v1/ml/models/compare)
- [ ] T196 [US4] [P] Add Model deployment endpoints (POST /api/v1/ml/deploy/canary)

**Admin Dashboard API (20개 엔드포인트)**

- [ ] T197 [US4] [P] Create Postman collection for Admin Dashboard API in tests/api/collections/admin-dashboard-api.postman_collection.json
- [ ] T198 [US4] [P] Add Dashboard metrics endpoints (GET /api/v1/admin/dashboard/sales)
- [ ] T199 [US4] [P] Add Order management endpoints (GET, PATCH /api/v1/admin/orders)
- [ ] T200 [US4] [P] Add User management endpoints (GET, PATCH /api/v1/admin/users)
- [ ] T201 [US4] [P] Add Product management endpoints (POST, PUT, DELETE /api/v1/admin/products)

### Postman 환경 변수

- [ ] T202 [US4] Create local environment in tests/api/environments/local.postman_environment.json
- [ ] T203 [US4] [P] Create staging environment in tests/api/environments/staging.postman_environment.json
- [ ] T204 [US4] [P] Create production environment in tests/api/environments/production.postman_environment.json

### Newman 실행 스크립트

- [ ] T205 [US4] Implement Newman runner script in tests/api/run-newman.sh
- [ ] T206 [US4] Add CLI, HTML, JSON reporters
- [ ] T207 [US4] Configure --bail flag to stop on first failure

### Supertest 통합 테스트

**Service Integration Tests**

- [ ] T208 [US4] [P] Create Ecommerce ↔ FDS integration test in tests/api/integration/ecommerce-fds-integration.test.ts
- [ ] T209 [US4] [P] Create FDS ↔ ML integration test in tests/api/integration/fds-ml-integration.test.ts
- [ ] T210 [US4] [P] Create End-to-End flow test in tests/api/integration/end-to-end-flow.test.ts

**Test Scenarios**

- [ ] T211 [US4] Implement low risk transaction test (10,000원 -> approve)
- [ ] T212 [US4] Implement high risk transaction test (5,000,000원 -> OTP required)
- [ ] T213 [US4] Implement ML canary deployment test (새 모델 -> 카나리 응답)

### JSON Schema 검증

- [ ] T214 [US4] Create JSON schema for FDS evaluation response in tests/api/schemas/fds-evaluation-response.json
- [ ] T215 [US4] [P] Create JSON schema for order response in tests/api/schemas/order-response.json
- [ ] T216 [US4] [P] Create JSON schema for product response in tests/api/schemas/product-response.json
- [ ] T217 [US4] Add JSON schema validation to Postman tests (pm.response.to.have.jsonSchema)

### CI/CD API 테스트 자동화

- [ ] T218 [US4] Implement API tests workflow in .github/workflows/api-tests.yml
- [ ] T219 [US4] Add Newman CLI execution step
- [ ] T220 [US4] Add Supertest execution step (npm test)
- [ ] T221 [US4] Add HTML report artifact upload
- [ ] T222 [US4] Configure test to run on PR and main branch push

### Testing & Validation

- [ ] T223 [US4] Run Newman tests locally for all 4 services
- [ ] T224 [US4] Verify 50개 엔드포인트 100% 커버리지
- [ ] T225 [US4] Verify Ecommerce -> FDS -> OTP -> Order 플로우 성공
- [ ] T226 [US4] Verify Newman HTML report generation
- [ ] T227 [US4] Verify Supertest integration tests pass

---

## Phase 7: User Story 5 - 성능 테스트 (P3) (Week 10-11, Day 32-38)

**Story Goal**: 성능 테스트 엔지니어는 트래픽 급증 시나리오(Spike Test)와 장기간 안정성 테스트(Soak Test)를 통해 시스템이 블랙 프라이데이와 같은 극한 상황에서도 안정적으로 작동하는지 검증할 수 있어야 한다.

**Independent Test**: 부하 테스트 도구를 사용하여 Spike Test(트래픽 10배 증가)와 Soak Test(24시간 연속 부하)를 실행하고 시스템 안정성을 모니터링할 수 있다.

### k6 시나리오 작성

**Spike Test (트래픽 10배 급증)**

- [ ] T228 [US5] Create Spike Test script in tests/performance/scenarios/spike-test.js
- [ ] T229 [US5] Configure stages (1m: 100 VU -> 10s: 1000 VU -> 3m: 1000 VU -> 1m: 100 VU)
- [ ] T230 [US5] Add thresholds (http_req_duration p95<200ms, http_req_failed <5%)
- [ ] T231 [US5] Add product browsing scenario (GET /api/products)

**Soak Test (24시간 안정성)**

- [ ] T232 [US5] [P] Create Soak Test script in tests/performance/scenarios/soak-test.js
- [ ] T233 [US5] [P] Configure stages (5m: ramp to 200 VU -> 24h: 200 VU -> 5m: ramp down)
- [ ] T234 [US5] [P] Add thresholds (http_req_duration p95<200ms, http_req_failed <1%)
- [ ] T235 [US5] [P] Add realistic user behavior with random sleep (1-3초)

**Stress Test (한계 탐색)**

- [ ] T236 [US5] [P] Create Stress Test script in tests/performance/scenarios/stress-test.js
- [ ] T237 [US5] [P] Configure stages (2m -> 200 -> 5m -> 500 -> 5m -> 1000 -> 5m -> 2000 -> 5m -> 3000)
- [ ] T238 [US5] [P] Add thresholds (http_req_duration p95<500ms, http_req_failed <10%)

**FDS 평가 부하 테스트**

- [ ] T239 [US5] [P] Create FDS Evaluation Test script in tests/performance/scenarios/fds-evaluation.js
- [ ] T240 [US5] [P] Configure 100 VU, 10분 duration
- [ ] T241 [US5] [P] Add FDS evaluate endpoint (POST /api/v1/fds/evaluate)
- [ ] T242 [US5] [P] Add threshold (http_req_duration{endpoint:fds_evaluate} p95<100ms)

**블랙 프라이데이 시뮬레이션**

- [ ] T243 [US5] [P] Create Black Friday scenario in tests/performance/scenarios/black-friday.js
- [ ] T244 [US5] [P] Add product_browsing scenario (ramping to 10,000 VU)
- [ ] T245 [US5] [P] Add checkout_flow scenario (constant 500 VU)
- [ ] T246 [US5] [P] Add fds_evaluation scenario (1,000 TPS arrival rate)
- [ ] T247 [US5] [P] Add scenario-specific thresholds

### k6 유틸리티 및 설정

- [ ] T248 [US5] Create test data generator in tests/performance/utils/data-generator.js
- [ ] T249 [US5] [P] Create authentication helper in tests/performance/utils/auth-helper.js
- [ ] T250 [US5] [P] Create metrics collector in tests/performance/utils/metrics-collector.js
- [ ] T251 [US5] Create staging environment config in tests/performance/config/staging.json
- [ ] T252 [US5] [P] Create production environment config in tests/performance/config/production.json

### Prometheus 메트릭 통합

- [ ] T253 [US5] Configure k6 to export metrics to Prometheus (--out prometheus-rw)
- [ ] T254 [US5] Verify k6 metrics appear in Prometheus (k6_http_req_duration, k6_http_req_failed)
- [ ] T255 [US5] Create PromQL queries for k6 metrics aggregation

### Grafana 대시보드

- [ ] T256 [US5] Import k6 Load Testing Results dashboard (ID: 2587) to Grafana
- [ ] T257 [US5] Customize dashboard for ShopFDS metrics
- [ ] T258 [US5] Add panels for VU count, RPS, response time P95, error rate

### CI/CD 성능 테스트 자동화

- [ ] T259 [US5] Implement performance tests workflow in .github/workflows/performance-tests.yml
- [ ] T260 [US5] Add Spike Test execution on PR (k6 run spike-test.js)
- [ ] T261 [US5] Add Soak Test nightly execution (schedule: '0 0 * * *')
- [ ] T262 [US5] Add performance test failure threshold check
- [ ] T263 [US5] Add Slack notification on performance degradation

### Testing & Validation

- [ ] T264 [US5] Run Spike Test locally (k6 run spike-test.js)
- [ ] T265 [US5] Verify 1,000 TPS 트래픽 처리 성공
- [ ] T266 [US5] Verify P95 응답 시간 200ms 이내
- [ ] T267 [US5] Run FDS Evaluation Test
- [ ] T268 [US5] Verify FDS P95 100ms 이내 (목표 달성)
- [ ] T269 [US5] Run Soak Test for 1 hour (short test)
- [ ] T270 [US5] Verify 메모리 누수 없음, 성능 저하 없음
- [ ] T271 [US5] Verify Grafana dashboard shows k6 metrics correctly

---

## Phase 8: 통합 및 최종 검증 (Week 12, Day 39-42)

**목표**: 모든 User Story 통합, 문서화 완료, 최종 검증

### 통합 테스트

- [ ] T272 Run all E2E tests (20 scenarios) in CI
- [ ] T273 Run all API tests (50 endpoints) in CI
- [ ] T274 Trigger canary deployment for all 4 services
- [ ] T275 Run all 5 chaos experiments sequentially
- [ ] T276 Run performance tests (Spike, FDS Evaluation)
- [ ] T277 Verify all CI/CD workflows pass end-to-end

### Documentation

- [ ] T278 [P] Update E2E testing README in docs/e2e-testing/README.md
- [ ] T279 [P] Update Canary deployment README in docs/canary-deployment/README.md
- [ ] T280 [P] Update Chaos engineering README in docs/chaos-engineering/README.md
- [ ] T281 [P] Update Performance testing README in docs/performance-testing/README.md
- [ ] T282 [P] Update API testing README in tests/api/README.md
- [ ] T283 Create troubleshooting guide in docs/troubleshooting.md
- [ ] T284 Create architecture diagram (Mermaid) in docs/architecture-e2e-testing.md

### CI/CD 최종 통합

- [ ] T285 Create master CI workflow in .github/workflows/full-test-suite.yml
- [ ] T286 Add job dependencies (E2E -> API -> Performance -> Canary -> Chaos)
- [ ] T287 Add overall test suite success badge to README.md
- [ ] T288 Configure workflow to run on main branch push and release tags

### Monitoring & Alerting

- [ ] T289 [P] Create Prometheus alert rules for E2E test failures
- [ ] T290 [P] Create Prometheus alert rules for canary deployment failures
- [ ] T291 [P] Create Prometheus alert rules for chaos experiment failures
- [ ] T292 [P] Configure Alertmanager to send Slack notifications
- [ ] T293 Verify alerts trigger correctly in test scenarios

### Production Readiness

- [ ] T294 Review security settings (RBAC, ServiceAccounts, Secrets)
- [ ] T295 Review resource limits and requests for all testing tools
- [ ] T296 Configure production environment variables (BASE_URL, API_KEYS)
- [ ] T297 Test production chaos experiments with manual approval
- [ ] T298 Document production deployment checklist

### Final Validation

- [ ] T299 Verify E2E 테스트 100% 통과율 달성
- [ ] T300 Verify 카나리 배포 자동 롤백 30초 이내 달성
- [ ] T301 Verify 시스템 장애 복구 30초 이내 달성 (5가지 시나리오)
- [ ] T302 Verify API 테스트 50개 엔드포인트 100% 커버리지
- [ ] T303 Verify 성능 테스트 Spike 1,000 TPS, FDS P95 100ms 달성
- [ ] T304 Verify 배포 신뢰도 95%+ (이전 대비 58% 향상)
- [ ] T305 Verify CI/CD 전체 파이프라인 30분 이내 완료

### Cleanup & Optimization

- [ ] T306 [P] Remove unused test fixtures and mocks
- [ ] T307 [P] Optimize Playwright test execution time (병렬화, 재사용)
- [ ] T308 [P] Optimize k6 script performance (data generation, VU count)
- [ ] T309 Archive old test results (>90일) to object storage
- [ ] T310 Update CLAUDE.md with E2E testing guidelines

---

## Parallel Execution Examples

### Phase 3 (E2E 테스트) - Parallel POM 생성

Task T059-T065는 서로 다른 Page Object 파일을 생성하므로 병렬 실행 가능:

```bash
# Parallel execution
npm run create-pom:register &
npm run create-pom:product-list &
npm run create-pom:product-detail &
npm run create-pom:cart &
npm run create-pom:checkout &
npm run create-pom:order-confirmation &
npm run create-pom:dashboard &
wait
```

### Phase 4 (카나리 배포) - Parallel VirtualService 생성

Task T106-T108, T110-T112는 서로 다른 서비스의 Istio 리소스를 생성하므로 병렬 실행 가능:

```bash
# Parallel execution
kubectl apply -f infrastructure/k8s/canary/istio/virtualservice-fds.yaml &
kubectl apply -f infrastructure/k8s/canary/istio/virtualservice-ml-service.yaml &
kubectl apply -f infrastructure/k8s/canary/istio/virtualservice-admin-dashboard.yaml &
wait
```

### Phase 5 (Chaos Engineering) - Parallel Chaos Experiments

Task T149-T164는 서로 다른 장애 시나리오를 작성하므로 병렬 실행 가능:

```bash
# Parallel execution (Staging 환경에서만)
kubectl apply -f infrastructure/chaos/experiments/fds-network-latency.yaml &
kubectl apply -f infrastructure/chaos/experiments/ecommerce-db-connection-loss.yaml &
kubectl apply -f infrastructure/chaos/experiments/redis-pod-delete.yaml &
kubectl apply -f infrastructure/chaos/experiments/fds-cpu-stress.yaml &
wait
```

### Phase 6 (API 테스트) - Parallel Postman Collections

Task T189-T201은 서로 다른 Postman 컬렉션을 작성하므로 병렬 실행 가능:

```bash
# Parallel execution
newman run tests/api/collections/fds-api.postman_collection.json &
newman run tests/api/collections/ml-service-api.postman_collection.json &
newman run tests/api/collections/admin-dashboard-api.postman_collection.json &
wait
```

---

## Implementation Strategy

### MVP (Minimum Viable Product)

**Phase 0-3 완료 시 MVP 달성**:
- E2E 테스트 자동화 (20개 시나리오)
- CI/CD 통합
- 크로스 브라우저 테스트
- 배포 전 자동 검증

**추가 기능 (Phase 4-7)**:
- 카나리 배포 (안전한 배포)
- Chaos Engineering (복원력 검증)
- API 통합 테스트 (서비스 간 통합)
- 성능 테스트 (트래픽 급증 대응)

### Task Estimation

**총 작업 수**: 310개
- Phase 0: 23개 (1주)
- Phase 1: 12개 (3일)
- Phase 2: 22개 (3일)
- Phase 3: 47개 (7일, MVP)
- Phase 4: 36개 (7일)
- Phase 5: 43개 (7일)
- Phase 6: 44개 (7일)
- Phase 7: 44개 (7일)
- Phase 8: 39개 (4일)

**예상 소요 기간**: 12주 (3개월)

**병렬 실행 가능 작업**: 약 120개 (전체의 39%)

---

## Success Metrics

### E2E Testing (US1)

- [목표] 20개 시나리오 100% 통과율
- [목표] 전체 실행 시간 10분 이내
- [목표] 3개 브라우저 (Chrome, Firefox, Safari) 호환성
- [목표] 데스크톱/모바일 반응형 검증

### Canary Deployment (US2)

- [목표] 10% -> 50% -> 100% 점진적 전환
- [목표] 에러율 5% 초과 시 자동 롤백
- [목표] 롤백 시간 30초 이내
- [목표] 4개 서비스 카나리 배포 지원

### Chaos Engineering (US3)

- [목표] 5가지 장애 시나리오 자동화
- [목표] 시스템 복구 30초 이내
- [목표] 에러율 5% 미만 유지
- [목표] Prometheus 메트릭 기반 검증

### API Testing (US4)

- [목표] 50개 엔드포인트 100% 커버리지
- [목표] Ecommerce -> FDS -> OTP -> Order 플로우 성공
- [목표] JSON Schema 검증
- [목표] CI 자동 실행

### Performance Testing (US5)

- [목표] Spike Test 1,000 TPS, P95 200ms 이내
- [목표] Soak Test 24시간 메모리 누수 없음
- [목표] FDS P95 100ms 이내
- [목표] 블랙 프라이데이 시뮬레이션 성공

### Overall

- [목표] 배포 신뢰도 60% -> 95%+ (58% 향상)
- [목표] 프로덕션 장애 월 5회 -> 월 1회 이하 (80% 감소)
- [목표] CI/CD 파이프라인 30분 이내 완료
- [목표] 테스트 커버리지 70% -> 95%+ (36% 향상)

---

**Last Updated**: 2025-11-20
**Review Required**: After Phase 3 completion (MVP validation)
