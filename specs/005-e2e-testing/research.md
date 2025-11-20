# E2E 테스트 자동화 및 시스템 복원력 검증 - 기술 리서치

**Feature Branch**: `005-e2e-testing`
**Created**: 2025-11-20
**Status**: Research

## 목차

1. [E2E 테스트 프레임워크](#1-e2e-테스트-프레임워크)
2. [Service Mesh (서비스 메시)](#2-service-mesh-서비스-메시)
3. [카나리 배포 자동화](#3-카나리-배포-자동화)
4. [Chaos Engineering 도구](#4-chaos-engineering-도구)
5. [성능 테스트 도구](#5-성능-테스트-도구)
6. [API 테스트 도구](#6-api-테스트-도구)
7. [통합 아키텍처 결정](#7-통합-아키텍처-결정)

---

## 1. E2E 테스트 프레임워크

### Decision

**Playwright** 채택

### Rationale

1. **최신 브라우저 자동화 API**: Chromium, Firefox, WebKit(Safari) 3대 브라우저 엔진을 단일 API로 제어
2. **안정적인 자동 대기 메커니즘**: 요소가 준비될 때까지 자동으로 대기하여 Flaky 테스트 최소화
3. **강력한 선택자 엔진**: CSS, XPath, 텍스트, ARIA 역할 등 다양한 선택자 지원
4. **네트워크 및 API Mocking**: 테스트 격리를 위한 네트워크 인터셉션 기능 내장
5. **병렬 실행 및 격리**: 브라우저 컨텍스트 격리로 안전한 병렬 테스트
6. **TypeScript 완벽 지원**: 기존 프론트엔드 TypeScript 5.3+ 스택과 일관성
7. **CI 통합 용이**: Docker 이미지 제공, Headless 모드, 스크린샷/비디오 녹화
8. **Microsoft 공식 지원**: 활발한 커뮤니티, 빠른 업데이트

**기술적 적합성**:
- React 18+ 프론트엔드와 완벽 호환
- GitHub Actions CI/CD와 즉시 통합 가능
- Page Object Model 패턴으로 유지보수성 향상
- 10분 이내 E2E 테스트 실행 목표 달성 가능

### Alternatives Considered

| Tool | Pros | Cons | Verdict |
|------|------|------|---------|
| **Playwright** | - 3대 브라우저 엔진 지원<br>- 자동 대기 메커니즘<br>- TypeScript 완벽 지원<br>- 빠른 실행 속도<br>- 강력한 디버깅 도구 | - 상대적으로 신규 도구<br>- 커뮤니티 규모 (Cypress 대비) | **선택** |
| **Cypress** | - 인기 있는 도구<br>- 풍부한 플러그인 생태계<br>- 실시간 Time-travel 디버깅<br>- 직관적인 UI | - WebKit(Safari) 공식 미지원<br>- iframe, 다중 탭 제한<br>- 네트워크 레이어 접근 제한<br>- 느린 실행 속도 (Playwright 대비) | 제외 |
| **Selenium** | - 업계 표준 도구<br>- 다양한 언어 바인딩<br>- 방대한 커뮤니티<br>- 레거시 브라우저 지원 | - Flaky 테스트 문제<br>- 수동 대기 로직 필요<br>- 느린 실행 속도<br>- 현대적인 API 부족<br>- 복잡한 설정 | 제외 |
| **Puppeteer** | - Chrome DevTools Protocol<br>- 빠른 실행 속도<br>- Google 공식 지원 | - Chromium만 지원<br>- 크로스 브라우저 불가<br>- Firefox, Safari 미지원 | 제외 |
| **TestCafe** | - 브라우저 플러그인 불필요<br>- JavaScript/TypeScript 지원<br>- 자동 대기 메커니즘 | - 느린 실행 속도<br>- 제한적인 API<br>- 커뮤니티 규모 작음<br>- 고급 기능 부족 | 제외 |

### Best Practices

1. **Page Object Model (POM) 패턴**
   ```typescript
   // tests/e2e/pages/LoginPage.ts
   export class LoginPage {
     constructor(private page: Page) {}

     async login(email: string, password: string) {
       await this.page.fill('[data-testid="email"]', email);
       await this.page.fill('[data-testid="password"]', password);
       await this.page.click('[data-testid="login-button"]');
     }

     async expectLoggedIn() {
       await expect(this.page.locator('[data-testid="user-menu"]')).toBeVisible();
     }
   }
   ```

2. **테스트 격리 및 재사용**
   ```typescript
   // tests/e2e/fixtures/index.ts
   import { test as base } from '@playwright/test';

   export const test = base.extend({
     authenticatedPage: async ({ page }, use) => {
       await page.goto('/login');
       await page.fill('[data-testid="email"]', 'test@example.com');
       await page.fill('[data-testid="password"]', 'password123');
       await page.click('[data-testid="login-button"]');
       await use(page);
     },
   });
   ```

3. **자동 대기 및 재시도**
   ```typescript
   // 명시적 대기 불필요 - Playwright가 자동 처리
   await page.click('button.submit'); // 버튼이 클릭 가능할 때까지 자동 대기

   // 커스텀 조건 대기
   await page.waitForFunction(() => window.analytics !== undefined);
   ```

4. **네트워크 모킹으로 테스트 안정성 향상**
   ```typescript
   // FDS API 모킹
   await page.route('**/api/fds/evaluate', route => {
     route.fulfill({
       status: 200,
       body: JSON.stringify({ risk_score: 25, decision: 'approve' }),
     });
   });
   ```

5. **병렬 실행 최적화**
   ```typescript
   // playwright.config.ts
   export default defineConfig({
     workers: process.env.CI ? 4 : 2, // CI에서 4개 워커 병렬 실행
     fullyParallel: true,
     retries: process.env.CI ? 2 : 0, // CI에서 2회 재시도
   });
   ```

6. **실패 시 디버깅 정보 자동 수집**
   ```typescript
   // playwright.config.ts
   use: {
     screenshot: 'only-on-failure', // 실패 시 스크린샷
     video: 'retain-on-failure',   // 실패 시 비디오 녹화
     trace: 'retain-on-failure',   // 실패 시 trace 파일
   },
   ```

### Integration Notes

**ShopFDS 아키텍처 통합**:

1. **프론트엔드 통합** (`services/ecommerce/frontend`, `services/admin-dashboard/frontend`):
   - React 컴포넌트에 `data-testid` 속성 추가로 안정적인 선택자 제공
   - Zustand 스토어 상태 검증
   - React Query 캐시 상태 확인

2. **백엔드 통합** (FastAPI 서비스):
   - E2E 테스트용 테스트 데이터베이스 격리 (PostgreSQL 독립 스키마)
   - 테스트 사용자 자동 생성/정리 (Fixture)
   - FDS API 모킹으로 외부 의존성 제거

3. **CI/CD 통합** (GitHub Actions):
   ```yaml
   # .github/workflows/e2e-tests.yml
   - name: Run E2E Tests
     run: |
       docker-compose -f docker-compose.test.yml up -d
       npx playwright test
       docker-compose down
   ```

4. **테스트 데이터 관리**:
   - 각 테스트는 독립적인 사용자/상품/주문 데이터 생성
   - 테스트 완료 후 자동 정리 (teardown)
   - 결제 정보는 테스트 토큰 사용 (실제 결제 방지)

5. **성능 목표**:
   - 20개 E2E 시나리오를 4개 워커로 병렬 실행
   - 목표: 전체 실행 시간 10분 이내
   - Headless 모드로 30% 속도 향상

---

## 2. Service Mesh (서비스 메시)

### Decision

**Istio** 채택

### Rationale

1. **업계 표준**: CNCF 졸업 프로젝트, 가장 널리 사용되는 Service Mesh
2. **강력한 트래픽 관리**: VirtualService, DestinationRule로 세밀한 라우팅 제어
3. **카나리 배포 지원**: 가중치 기반 트래픽 분할 (10%, 50%, 100%)
4. **Observability**: Prometheus, Grafana, Jaeger, Kiali 통합
5. **보안 기능**: mTLS 자동 암호화, 인증/인가 정책
6. **Kubernetes 네이티브**: CRD 기반 선언적 설정
7. **Flagger 완벽 지원**: 자동 카나리 배포 컨트롤러와 즉시 통합
8. **풍부한 생태계**: Istio Operator, istioctl CLI, 방대한 문서

**기술적 적합성**:
- Kubernetes 1.28+ 환경에 최적화
- Prometheus/Grafana 기존 모니터링 스택과 원활히 통합
- 4개 마이크로서비스(Ecommerce, FDS, ML-Service, Admin-Dashboard) 독립 배포 가능
- Nginx API Gateway와 공존 가능

### Alternatives Considered

| Tool | Pros | Cons | Verdict |
|------|------|------|---------|
| **Istio** | - 업계 표준 및 CNCF 졸업<br>- 강력한 트래픽 관리<br>- Flagger 완벽 지원<br>- 풍부한 Observability<br>- mTLS 자동 암호화<br>- 대규모 엔터프라이즈 검증 | - 상대적으로 높은 리소스 사용<br>- 학습 곡선<br>- 복잡한 설정 (초기) | **선택** |
| **Linkerd** | - 경량화 (낮은 리소스 사용)<br>- 간단한 설정<br>- 빠른 성능<br>- CNCF 졸업<br>- Rust 기반 고성능 | - 제한적인 기능<br>- Istio 대비 커뮤니티 작음<br>- Flagger 지원 제한적<br>- 고급 트래픽 관리 부족 | 제외 |
| **Consul Connect** | - HashiCorp 생태계 통합<br>- Multi-cloud 지원<br>- Service Discovery 내장<br>- Non-Kubernetes 환경 지원 | - Kubernetes 네이티브 아님<br>- 복잡한 설정<br>- Observability 약함<br>- Flagger 미지원 | 제외 |
| **Kuma** | - Kong 제공<br>- Multi-zone 지원<br>- 간단한 UI<br>- Envoy 기반 | - 커뮤니티 작음<br>- 엔터프라이즈 검증 부족<br>- Flagger 미지원<br>- 기능 제한적 | 제외 |
| **AWS App Mesh** | - AWS 완전 관리형<br>- ECS, EKS 통합<br>- AWS 서비스 통합 | - AWS 종속성<br>- Kubernetes 전용 아님<br>- 오픈소스 아님<br>- Flagger 제한적 지원 | 제외 |

### Best Practices

1. **점진적 도입 전략**
   ```yaml
   # 1단계: Sidecar Injection만 활성화 (트래픽 관리 없이 Observability만)
   apiVersion: v1
   kind: Namespace
   metadata:
     name: ecommerce
     labels:
       istio-injection: enabled
   ```

2. **카나리 배포용 VirtualService**
   ```yaml
   # infrastructure/k8s/canary/istio/virtualservice-ecommerce.yaml
   apiVersion: networking.istio.io/v1beta1
   kind: VirtualService
   metadata:
     name: ecommerce-backend
   spec:
     hosts:
     - ecommerce-backend
     http:
     - match:
       - headers:
           x-canary:
             exact: "true"
       route:
       - destination:
           host: ecommerce-backend
           subset: canary
         weight: 100
     - route:
       - destination:
           host: ecommerce-backend
           subset: stable
         weight: 90
       - destination:
           host: ecommerce-backend
           subset: canary
         weight: 10 # 초기 10% 트래픽
   ```

3. **DestinationRule로 서브셋 정의**
   ```yaml
   apiVersion: networking.istio.io/v1beta1
   kind: DestinationRule
   metadata:
     name: ecommerce-backend
   spec:
     host: ecommerce-backend
     trafficPolicy:
       connectionPool:
         tcp:
           maxConnections: 100
         http:
           http1MaxPendingRequests: 50
           http2MaxRequests: 100
       outlierDetection:
         consecutiveErrors: 5
         interval: 30s
         baseEjectionTime: 30s
     subsets:
     - name: stable
       labels:
         version: v1.0.0
     - name: canary
       labels:
         version: v1.1.0
   ```

4. **Observability 통합**
   ```yaml
   # Prometheus 메트릭 자동 수집
   apiVersion: v1
   kind: Service
   metadata:
     name: ecommerce-backend
     annotations:
       prometheus.io/scrape: "true"
       prometheus.io/port: "15020"
       prometheus.io/path: "/stats/prometheus"
   ```

5. **Circuit Breaking 및 Retry 정책**
   ```yaml
   trafficPolicy:
     connectionPool:
       tcp:
         maxConnections: 100
       http:
         http1MaxPendingRequests: 50
         maxRequestsPerConnection: 2
     outlierDetection:
       consecutiveErrors: 5
       interval: 30s
       baseEjectionTime: 30s
       maxEjectionPercent: 50
   ```

6. **mTLS 자동 암호화**
   ```yaml
   apiVersion: security.istio.io/v1beta1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: ecommerce
   spec:
     mtls:
       mode: STRICT # 모든 서비스 간 통신 mTLS 강제
   ```

### Integration Notes

**ShopFDS 아키텍처 통합**:

1. **마이크로서비스 통합**:
   - 4개 백엔드 서비스에 Envoy Sidecar 자동 주입
   - 서비스 간 통신 mTLS 암호화 (Ecommerce ↔ FDS ↔ ML-Service)
   - Nginx API Gateway를 통한 외부 트래픽 수신 유지

2. **기존 모니터링 통합**:
   - Istio 메트릭을 기존 Prometheus로 수집
   - Grafana에 Istio 대시보드 추가
   - Kiali로 서비스 메시 시각화

3. **점진적 배포 전략**:
   ```
   1. Istio Control Plane 설치 (istiod)
   2. Namespace에 Sidecar Injection 활성화
   3. 기존 서비스 재배포 (Sidecar 주입)
   4. VirtualService/DestinationRule 생성
   5. Flagger 설치 및 카나리 배포 자동화
   ```

4. **리소스 요구사항**:
   - istiod: 500m CPU, 2Gi 메모리 (Control Plane)
   - Envoy Sidecar: 100m CPU, 128Mi 메모리 (각 Pod)
   - 총 추가 리소스: ~2 CPU, ~4Gi 메모리 (4개 서비스 기준)

5. **트래픽 흐름**:
   ```
   User → Nginx Ingress → Istio Gateway → VirtualService
        → Envoy Sidecar (ecommerce-backend) → Service
        → Envoy Sidecar (fds) → Service
        → Envoy Sidecar (ml-service) → Service
   ```

---

## 3. 카나리 배포 자동화

### Decision

**Flagger** 채택

### Rationale

1. **Kubernetes 네이티브**: CRD 기반 선언적 카나리 배포 정의
2. **Istio 완벽 통합**: VirtualService/DestinationRule 자동 관리
3. **자동 카나리 분석**: Prometheus 메트릭 기반 자동 롤백 결정
4. **점진적 트래픽 전환**: 10% → 25% → 50% → 100% 자동 증가
5. **A/B 테스트 지원**: Header 기반 트래픽 라우팅
6. **Load Testing 통합**: Webhook으로 외부 테스트 도구 실행
7. **알림 통합**: Slack, MS Teams, Discord 알림
8. **CNCF Sandbox**: 활발한 커뮤니티, Weaveworks 공식 지원

**기술적 적합성**:
- Istio와 즉시 통합 가능
- Prometheus 기존 모니터링 스택 활용
- 30초 이내 자동 롤백 목표 달성 가능
- 선언적 설정으로 GitOps 패턴 적용 가능

### Alternatives Considered

| Tool | Pros | Cons | Verdict |
|------|------|------|---------|
| **Flagger** | - Kubernetes 네이티브<br>- Istio 완벽 통합<br>- 자동 메트릭 분석<br>- A/B 테스트 지원<br>- CNCF Sandbox<br>- 선언적 설정 | - Istio 의존성<br>- 학습 곡선<br>- 초기 설정 복잡도 | **선택** |
| **Argo Rollouts** | - ArgoCD 통합<br>- Blue-Green, Canary 지원<br>- 다양한 메트릭 프로바이더<br>- Service Mesh 독립적 | - Istio 통합 수동 설정<br>- Flagger 대비 복잡<br>- 트래픽 분할 제한적 | 제외 |
| **Custom Solution** | - 완전한 제어<br>- 특정 요구사항 맞춤<br>- 외부 의존성 없음 | - 개발/유지보수 부담<br>- 검증되지 않은 안정성<br>- 재발명의 바퀴 | 제외 |
| **Spinnaker** | - 엔터프라이즈급 CD 플랫폼<br>- 다양한 배포 전략<br>- Multi-cloud 지원 | - 과도한 복잡도<br>- 높은 리소스 요구<br>- Kubernetes 전용 아님<br>- 설정 복잡 | 제외 |
| **Jenkins X** | - GitOps 패턴<br>- Tekton 기반<br>- Preview 환경 자동 생성 | - 학습 곡선 높음<br>- 복잡한 설정<br>- Istio 통합 제한적 | 제외 |

### Best Practices

1. **Canary CRD 정의**
   ```yaml
   # infrastructure/k8s/canary/flagger/canary-ecommerce.yaml
   apiVersion: flagger.app/v1beta1
   kind: Canary
   metadata:
     name: ecommerce-backend
     namespace: ecommerce
   spec:
     targetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: ecommerce-backend
     progressDeadlineSeconds: 1800 # 30분 타임아웃
     service:
       port: 8000
     analysis:
       interval: 1m # 1분마다 분석
       threshold: 5 # 5회 연속 실패 시 롤백
       maxWeight: 100
       stepWeight: 10 # 10%씩 증가
       metrics:
       - name: request-success-rate
         thresholdRange:
           min: 95 # 95% 이상 성공률 유지
         interval: 1m
       - name: request-duration
         thresholdRange:
           max: 500 # 500ms 이하 응답 시간
         interval: 1m
       webhooks:
       - name: load-test
         url: http://flagger-loadtester/
         timeout: 5s
         metadata:
           type: cmd
           cmd: "hey -z 1m -q 10 -c 2 http://ecommerce-backend-canary:8000/"
   ```

2. **메트릭 기반 자동 롤백**
   ```yaml
   analysis:
     metrics:
     - name: error-rate
       templateRef:
         name: error-rate
         namespace: istio-system
       thresholdRange:
         max: 5 # 에러율 5% 초과 시 롤백
       interval: 1m
     - name: latency-p95
       templateRef:
         name: latency
         namespace: istio-system
       thresholdRange:
         max: 200 # P95 200ms 초과 시 롤백
       interval: 1m
   ```

3. **Slack 알림 통합**
   ```yaml
   webhooks:
   - name: slack-notification
     url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
     metadata:
       type: post-rollout
       text: "Canary deployment completed for ecommerce-backend"
   ```

4. **A/B 테스트 시나리오**
   ```yaml
   # Header 기반 카나리 라우팅
   analysis:
     match:
     - headers:
         x-canary:
           exact: "insider" # insider 헤더 사용자만 카나리 버전
   ```

5. **Blue-Green 배포 모드**
   ```yaml
   # 카나리 대신 Blue-Green 배포
   spec:
     analysis:
       iterations: 10
       threshold: 2
       maxWeight: 100
       stepWeight: 100 # 한 번에 100% 전환 (Blue-Green)
   ```

6. **Load Testing Webhook**
   ```yaml
   webhooks:
   - name: load-test
     url: http://flagger-loadtester/
     timeout: 5s
     metadata:
       type: cmd
       cmd: "k6 run /scripts/load-test.js"
   ```

### Integration Notes

**ShopFDS 아키텍처 통합**:

1. **4개 서비스 카나리 배포**:
   - `canary-ecommerce.yaml`: Ecommerce Backend
   - `canary-fds.yaml`: FDS 서비스
   - `canary-ml-service.yaml`: ML 서비스
   - `canary-admin-dashboard.yaml`: Admin Dashboard Backend

2. **Prometheus 메트릭 연동**:
   ```yaml
   # Istio 메트릭 템플릿
   apiVersion: flagger.app/v1beta1
   kind: MetricTemplate
   metadata:
     name: error-rate
     namespace: istio-system
   spec:
     provider:
       type: prometheus
       address: http://prometheus:9090
     query: |
       100 - sum(
         rate(
           istio_requests_total{
             reporter="destination",
             destination_workload_namespace="{{ namespace }}",
             destination_workload=~"{{ target }}",
             response_code!~"5.*"
           }[{{ interval }}]
         )
       ) / sum(
         rate(
           istio_requests_total{
             reporter="destination",
             destination_workload_namespace="{{ namespace }}",
             destination_workload=~"{{ target }}"
           }[{{ interval }}]
         )
       ) * 100
   ```

3. **카나리 배포 플로우**:
   ```
   1. 새 버전 Deployment 생성 (예: v1.1.0)
   2. Flagger가 VirtualService 자동 생성
   3. 초기 10% 트래픽 라우팅
   4. 1분마다 Prometheus 메트릭 분석
   5. 성공률 95% 이상 → 10%씩 증가 (10% → 20% → ... → 100%)
   6. 실패 시 → 자동 롤백 (30초 이내)
   7. 100% 완료 시 → 이전 버전 Pod 스케일다운
   ```

4. **CI/CD 통합** (GitHub Actions):
   ```yaml
   # .github/workflows/canary-deployment.yml
   - name: Deploy Canary
     run: |
       kubectl set image deployment/ecommerce-backend \
         ecommerce-backend=ecommerce-backend:${{ github.sha }}
       # Flagger가 자동으로 카나리 배포 시작

   - name: Monitor Canary
     run: |
       kubectl wait --for=condition=Promoted \
         canary/ecommerce-backend \
         --timeout=30m
   ```

5. **롤백 시나리오**:
   - 자동 롤백: 에러율 5% 초과 또는 P95 200ms 초과
   - 수동 롤백: `kubectl delete canary ecommerce-backend` → Flagger가 자동 복원

---

## 4. Chaos Engineering 도구

### Decision

**Litmus Chaos** 채택

### Rationale

1. **Kubernetes 네이티브**: CRD 기반 장애 주입 실험 정의
2. **CNCF Sandbox**: 활발한 커뮤니티, 엔터프라이즈 검증
3. **풍부한 실험 라이브러리**: Pod Kill, Network Latency, Resource Stress 등 30+ 실험
4. **Chaos Workflow**: 여러 실험을 조합한 복잡한 시나리오 지원
5. **Hypothesis 검증**: 실험 전후 상태 비교 (Steady State Hypothesis)
6. **Observability 통합**: Prometheus 메트릭 기반 실험 결과 검증
7. **RBAC 및 안전 장치**: Namespace 격리, 승인 워크플로우
8. **ChaosCenter UI**: 웹 기반 실험 관리 대시보드

**기술적 적합성**:
- Kubernetes 1.28+ 환경에 최적화
- Prometheus/Grafana 기존 모니터링 스택 활용
- 30초 이내 자동 복구 목표 검증 가능
- GitOps 패턴으로 실험 버전 관리

### Alternatives Considered

| Tool | Pros | Cons | Verdict |
|------|------|------|---------|
| **Litmus Chaos** | - Kubernetes 네이티브<br>- CNCF Sandbox<br>- 풍부한 실험 라이브러리<br>- Chaos Workflow 지원<br>- ChaosCenter UI<br>- 오픈소스 무료 | - 상대적으로 신규 도구<br>- 엔터프라이즈 지원 제한적 | **선택** |
| **Chaos Mesh** | - CNCF Sandbox<br>- 강력한 UI<br>- 다양한 장애 유형<br>- Time Travel 기능<br>- PingCAP 검증 | - 커뮤니티 작음<br>- 문서 부족<br>- Observability 약함 | 제외 |
| **Gremlin** | - 엔터프라이즈급 기능<br>- 강력한 UI/UX<br>- 팀 협업 기능<br>- 상세한 리포트<br>- 24/7 지원 | - 상용 라이선스 (비용)<br>- 오픈소스 아님<br>- Vendor Lock-in | 제외 |
| **Chaos Toolkit** | - 오픈소스<br>- Python 기반 확장성<br>- 다양한 플랫폼 지원<br>- Hypothesis 검증 | - Kubernetes 네이티브 아님<br>- UI 없음<br>- 수동 설정 많음 | 제외 |
| **Pumba** | - Docker 컨테이너 장애 주입<br>- 간단한 CLI<br>- 경량화 | - Kubernetes 지원 제한적<br>- 복잡한 시나리오 불가<br>- 커뮤니티 작음 | 제외 |

### Best Practices

1. **Pod Kill 실험**
   ```yaml
   # infrastructure/chaos/experiments/pod-delete.yaml
   apiVersion: litmuschaos.io/v1alpha1
   kind: ChaosEngine
   metadata:
     name: fds-pod-delete
     namespace: fds
   spec:
     appinfo:
       appns: fds
       applabel: 'app=fds-backend'
       appkind: deployment
     engineState: 'active'
     chaosServiceAccount: litmus-admin
     experiments:
     - name: pod-delete
       spec:
         components:
           env:
           - name: TOTAL_CHAOS_DURATION
             value: '30' # 30초 동안 장애 유지
           - name: CHAOS_INTERVAL
             value: '10' # 10초마다 Pod 삭제
           - name: FORCE
             value: 'false' # Graceful shutdown
         probe:
         - name: check-pod-recovery
           type: cmdProbe
           mode: Continuous
           runProperties:
             probeTimeout: 5
             interval: 2
             retry: 3
           cmdProbe/inputs:
             command: kubectl get pods -n fds -l app=fds-backend --field-selector=status.phase=Running
             comparator:
               type: int
               criteria: ">=" # 최소 1개 Pod는 Running 상태
               value: "1"
   ```

2. **네트워크 지연 주입**
   ```yaml
   # infrastructure/chaos/experiments/network-latency.yaml
   apiVersion: litmuschaos.io/v1alpha1
   kind: ChaosEngine
   metadata:
     name: fds-network-latency
   spec:
     experiments:
     - name: pod-network-latency
       spec:
         components:
           env:
           - name: TARGET_CONTAINER
             value: 'fds-backend'
           - name: NETWORK_INTERFACE
             value: 'eth0'
           - name: NETWORK_LATENCY
             value: '500' # 500ms 지연
           - name: TOTAL_CHAOS_DURATION
             value: '60' # 1분 동안 지연
           - name: JITTER
             value: '50' # ±50ms 변동
         probe:
         - name: check-api-response-time
           type: httpProbe
           mode: Continuous
           httpProbe/inputs:
             url: http://fds-backend:8001/health
             method:
               get:
                 criteria: "==" # 200 OK 응답
                 responseCode: "200"
             insecureSkipVerify: true
   ```

3. **리소스 Stress 테스트**
   ```yaml
   # infrastructure/chaos/experiments/resource-stress.yaml
   - name: pod-cpu-hog
     spec:
       components:
         env:
         - name: CPU_CORES
           value: '2' # 2개 CPU 코어 점유
         - name: TOTAL_CHAOS_DURATION
           value: '120' # 2분 동안 부하
         - name: CHAOS_KILL_COMMAND
           value: "kill -9 $(pidof md5sum)"
       probe:
       - name: check-hpa-scaling
         type: k8sProbe
         mode: EOT # End of Test
         k8sProbe/inputs:
           group: apps
           version: v1
           resource: deployments
           namespace: fds
           fieldSelector: metadata.name=fds-backend
           operation: present
           criteria: ".spec.replicas > 1" # HPA가 작동하여 Pod 증가
   ```

4. **데이터베이스 연결 실패**
   ```yaml
   # infrastructure/chaos/experiments/db-connection-loss.yaml
   - name: pod-network-loss
     spec:
       components:
         env:
         - name: TARGET_CONTAINER
           value: 'ecommerce-backend'
         - name: NETWORK_PACKET_LOSS_PERCENTAGE
           value: '100' # PostgreSQL 포트 완전 차단
         - name: DESTINATION_IPS
           value: 'postgres-service.default.svc.cluster.local'
         - name: DESTINATION_PORTS
           value: '5432'
         - name: TOTAL_CHAOS_DURATION
           value: '30' # 30초 동안 연결 차단
       probe:
       - name: check-connection-pool-recovery
         type: cmdProbe
         mode: Edge
         cmdProbe/inputs:
           command: |
             kubectl exec -n ecommerce deployment/ecommerce-backend -- \
             python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://...'); engine.connect()"
           comparator:
             type: string
             criteria: "contains"
             value: "successfully connected" # 연결 복구 확인
   ```

5. **Chaos Workflow (복합 시나리오)**
   ```yaml
   # infrastructure/chaos/workflows/black-friday-chaos.yaml
   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     name: black-friday-chaos
   spec:
     entrypoint: chaos-workflow
     templates:
     - name: chaos-workflow
       steps:
       - - name: pod-delete-fds
           template: run-chaos
           arguments:
             parameters:
             - name: experiment
               value: pod-delete
       - - name: network-latency-ecommerce
           template: run-chaos
           arguments:
             parameters:
             - name: experiment
               value: network-latency
       - - name: cpu-stress-ml-service
           template: run-chaos
           arguments:
             parameters:
             - name: experiment
               value: cpu-stress
   ```

6. **안전 장치 및 승인 워크플로우**
   ```yaml
   # Staging 환경: 자동 실행
   engineState: 'active'

   # Production 환경: 수동 승인 필요
   engineState: 'stop' # 기본값: 중지
   # 실행 시: kubectl annotate chaosengine fds-pod-delete litmuschaos.io/chaos="true"
   ```

### Integration Notes

**ShopFDS 아키텍처 통합**:

1. **5가지 장애 시나리오 자동화**:
   - `pod-delete.yaml`: FDS Pod 무작위 종료 → Kubernetes 자동 복구 검증
   - `network-latency.yaml`: FDS API 500ms 지연 → Timeout/Retry 로직 검증
   - `db-connection-loss.yaml`: PostgreSQL 연결 차단 → Connection Pool 복구 검증
   - `redis-down.yaml`: Redis 다운 → 캐시 미스 처리 검증
   - `resource-stress.yaml`: CPU/메모리 제한 → HPA 작동 검증

2. **Prometheus 메트릭 기반 검증**:
   ```yaml
   probe:
   - name: check-error-rate
     type: promProbe
     mode: Continuous
     promProbe/inputs:
       endpoint: http://prometheus:9090
       query: |
         sum(rate(http_requests_total{job="fds-backend",status=~"5.."}[1m])) /
         sum(rate(http_requests_total{job="fds-backend"}[1m])) * 100
       comparator:
         type: float
         criteria: "<" # 에러율 5% 미만 유지
         value: "5.0"
   ```

3. **CI/CD 통합** (GitHub Actions):
   ```yaml
   # .github/workflows/chaos-experiments.yml
   - name: Run Chaos Experiments
     run: |
       kubectl apply -f infrastructure/chaos/experiments/
       kubectl wait --for=condition=ChaosEngineCompleted \
         chaosengine/fds-pod-delete \
         --timeout=5m
   ```

4. **ChaosCenter UI 통합**:
   - 웹 대시보드: http://litmus-frontend:9091
   - 실험 히스토리, 성공/실패율, 복구 시간 시각화
   - 팀 협업: 실험 스케줄링, 승인 워크플로우

5. **안전 가드레일**:
   - Staging 환경: 자동 실행 (주간 근무 시간)
   - Production 환경: SRE 팀 수동 승인 후 실행
   - RBAC: `litmus-admin` ServiceAccount만 실험 실행 권한
   - Namespace 격리: 각 서비스별 독립 실험

---

## 5. 성능 테스트 도구

### Decision

**k6** 채택

### Rationale

1. **현대적인 부하 테스트 도구**: JavaScript/TypeScript로 시나리오 작성
2. **CLI 친화적**: CI/CD 파이프라인 통합 용이
3. **높은 성능**: Go 언어 기반으로 수천 RPS 생성 가능
4. **풍부한 메트릭**: HTTP 요청, 응답 시간, 처리량, 에러율 등
5. **Grafana Cloud 통합**: k6 Cloud로 결과 시각화 (옵션)
6. **Prometheus 내보내기**: 기존 모니터링 스택 활용
7. **다양한 테스트 유형**: Spike, Soak, Stress, Load 테스트 지원
8. **오픈소스**: Grafana Labs 공식 지원

**기술적 적합성**:
- JavaScript 기반 시나리오로 프론트엔드 팀도 작성 가능
- Prometheus/Grafana 기존 모니터링 스택 통합
- 1,000 TPS Spike Test 목표 달성 가능
- Docker 컨테이너로 CI 통합 간편

### Alternatives Considered

| Tool | Pros | Cons | Verdict |
|------|------|------|---------|
| **k6** | - 현대적인 API<br>- JavaScript 시나리오<br>- 높은 성능<br>- CI/CD 친화적<br>- Prometheus 통합<br>- Grafana Cloud 지원 | - 상대적으로 신규 도구<br>- GUI 없음 (CLI만) | **선택** |
| **JMeter** | - 업계 표준<br>- GUI 제공<br>- 풍부한 플러그인<br>- 대규모 커뮤니티 | - Java 기반 무거움<br>- 느린 실행 속도<br>- CI 통합 복잡<br>- 스크립트 작성 어려움 | 제외 |
| **Gatling** | - Scala 기반 성능<br>- 상세한 리포트<br>- CI/CD 통합 가능<br>- 오픈소스 | - 학습 곡선 높음<br>- Scala 언어 장벽<br>- 설정 복잡 | 제외 |
| **Locust** | - Python 기반<br>- 간단한 스크립트<br>- 분산 부하 테스트<br>- 오픈소스 | - 성능 제한 (Python)<br>- 메트릭 부족<br>- Prometheus 통합 약함 | 제외 |
| **Artillery** | - Node.js 기반<br>- YAML 시나리오<br>- CI 통합 간편<br>- 오픈소스 | - 성능 제한<br>- 커뮤니티 작음<br>- 고급 기능 부족 | 제외 |

### Best Practices

1. **Spike Test (트래픽 10배 급증)**
   ```javascript
   // tests/performance/scenarios/spike-test.js
   import http from 'k6/http';
   import { check, sleep } from 'k6';

   export const options = {
     stages: [
       { duration: '1m', target: 100 },   // 1분: 100 VU (정상 부하)
       { duration: '10s', target: 1000 }, // 10초: 1000 VU (10배 급증)
       { duration: '3m', target: 1000 },  // 3분: 1000 VU 유지
       { duration: '1m', target: 100 },   // 1분: 100 VU (복구)
       { duration: '1m', target: 0 },     // 1분: 종료
     ],
     thresholds: {
       'http_req_duration': ['p(95)<200'], // P95 200ms 이내
       'http_req_failed': ['rate<0.05'],   // 에러율 5% 미만
     },
   };

   export default function () {
     const res = http.get('http://ecommerce-backend:8000/api/products');
     check(res, {
       'status is 200': (r) => r.status === 200,
       'response time < 200ms': (r) => r.timings.duration < 200,
     });
     sleep(1);
   }
   ```

2. **Soak Test (24시간 안정성)**
   ```javascript
   // tests/performance/scenarios/soak-test.js
   export const options = {
     stages: [
       { duration: '5m', target: 200 },    // 5분: 램프 업
       { duration: '24h', target: 200 },   // 24시간: 200 VU 유지
       { duration: '5m', target: 0 },      // 5분: 램프 다운
     ],
     thresholds: {
       'http_req_duration': ['p(95)<200'],
       'http_req_failed': ['rate<0.01'],   // 장기 안정성: 에러율 1% 미만
       'http_reqs': ['rate>100'],          // 최소 100 RPS 유지
     },
   };

   export default function () {
     const res = http.get('http://ecommerce-backend:8000/api/products');
     check(res, {
       'status is 200': (r) => r.status === 200,
     });
     sleep(Math.random() * 2 + 1); // 1-3초 랜덤 슬립 (현실적인 사용자 패턴)
   }
   ```

3. **Stress Test (한계 탐색)**
   ```javascript
   // tests/performance/scenarios/stress-test.js
   export const options = {
     stages: [
       { duration: '2m', target: 200 },
       { duration: '5m', target: 500 },
       { duration: '5m', target: 1000 },
       { duration: '5m', target: 2000 },
       { duration: '5m', target: 3000 }, // 한계 탐색
       { duration: '2m', target: 0 },
     ],
     thresholds: {
       'http_req_duration': ['p(95)<500'], // 스트레스 상황: P95 500ms
       'http_req_failed': ['rate<0.10'],   // 에러율 10% 미만
     },
   };
   ```

4. **FDS 평가 API 부하 테스트**
   ```javascript
   // tests/performance/scenarios/fds-evaluation.js
   import http from 'k6/http';
   import { check } from 'k6';

   export const options = {
     vus: 100,
     duration: '10m',
     thresholds: {
       'http_req_duration{endpoint:fds_evaluate}': ['p(95)<100'], // FDS P95 100ms
     },
   };

   export default function () {
     const payload = JSON.stringify({
       transaction_id: `txn_${__VU}_${__ITER}`,
       amount: Math.random() * 1000000 + 10000,
       user_id: `user_${__VU}`,
       ip_address: `192.168.1.${Math.floor(Math.random() * 255)}`,
     });

     const res = http.post('http://fds:8001/api/v1/fds/evaluate', payload, {
       headers: { 'Content-Type': 'application/json' },
       tags: { endpoint: 'fds_evaluate' },
     });

     check(res, {
       'status is 200': (r) => r.status === 200,
       'response time < 100ms': (r) => r.timings.duration < 100,
       'risk_score exists': (r) => JSON.parse(r.body).risk_score !== undefined,
     });
   }
   ```

5. **Prometheus 메트릭 내보내기**
   ```javascript
   // tests/performance/config/prometheus-output.js
   export const options = {
     ext: {
       loadimpact: {
         projectID: 123456,
         name: 'ShopFDS Performance Test',
       },
     },
     // 또는 k6 run --out prometheus-rw=http://prometheus:9090/api/v1/write
   };
   ```

6. **복합 시나리오 (블랙 프라이데이)**
   ```javascript
   // tests/performance/scenarios/black-friday.js
   export const options = {
     scenarios: {
       product_browsing: {
         executor: 'ramping-vus',
         startVUs: 0,
         stages: [
           { duration: '5m', target: 5000 },
           { duration: '30m', target: 10000 },
         ],
         exec: 'browseProducts',
       },
       checkout_flow: {
         executor: 'constant-vus',
         vus: 500,
         duration: '35m',
         exec: 'checkoutFlow',
       },
       fds_evaluation: {
         executor: 'constant-arrival-rate',
         rate: 1000, // 1000 TPS
         timeUnit: '1s',
         duration: '35m',
         preAllocatedVUs: 100,
         exec: 'evaluateFds',
       },
     },
     thresholds: {
       'http_req_duration{scenario:product_browsing}': ['p(95)<200'],
       'http_req_duration{scenario:checkout_flow}': ['p(95)<500'],
       'http_req_duration{scenario:fds_evaluation}': ['p(95)<100'],
     },
   };

   export function browseProducts() {
     http.get('http://ecommerce-backend:8000/api/products');
   }

   export function checkoutFlow() {
     // 로그인 → 장바구니 → 결제
   }

   export function evaluateFds() {
     // FDS 평가 API 호출
   }
   ```

### Integration Notes

**ShopFDS 아키텍처 통합**:

1. **테스트 시나리오 구조**:
   ```
   tests/performance/
   ├── scenarios/
   │   ├── spike-test.js         # 트래픽 급증 시나리오
   │   ├── soak-test.js          # 24시간 안정성 테스트
   │   ├── stress-test.js        # 한계 탐색 테스트
   │   ├── fds-evaluation.js     # FDS 평가 부하 테스트
   │   ├── black-friday.js       # 블랙 프라이데이 시뮬레이션
   │   └── api-integration.js    # 서비스 간 통합 부하 테스트
   ├── utils/
   │   ├── data-generator.js     # 테스트 데이터 생성
   │   ├── auth-helper.js        # 인증 토큰 관리
   │   └── metrics-collector.js  # 커스텀 메트릭 수집
   ├── config/
   │   ├── staging.json          # Staging 환경 설정
   │   └── production.json       # Production 환경 설정
   └── README.md
   ```

2. **CI/CD 통합** (GitHub Actions):
   ```yaml
   # .github/workflows/performance-tests.yml
   - name: Run Spike Test
     run: |
       docker run --rm -i grafana/k6 run \
         -e BASE_URL=http://staging.shopfds.com \
         - <tests/performance/scenarios/spike-test.js

   - name: Run Soak Test (Nightly)
     if: github.event.schedule == '0 0 * * *' # 매일 자정
     run: |
       k6 run --out prometheus-rw=http://prometheus:9090/api/v1/write \
         tests/performance/scenarios/soak-test.js
   ```

3. **Grafana 대시보드 통합**:
   - k6 메트릭을 Prometheus로 내보내기
   - Grafana에서 실시간 시각화
   - 대시보드: k6 Load Testing Results (ID: 2587)

4. **성능 목표 검증**:
   - Spike Test: 1,000 TPS → P95 200ms 이내
   - Soak Test: 24시간 → 메모리 누수 없음
   - FDS 평가: P95 100ms 이내 (목표 달성)

5. **로컬 실행**:
   ```bash
   # scripts/run-performance-test.sh
   #!/bin/bash
   docker-compose -f docker-compose.test.yml up -d
   k6 run tests/performance/scenarios/spike-test.js
   docker-compose down
   ```

---

## 6. API 테스트 도구

### Decision

**Newman (Postman CLI)** 주 도구, **Supertest** 보조 도구

### Rationale

1. **Newman (Postman CLI)**:
   - Postman 컬렉션을 CI/CD에서 자동 실행
   - 팀 협업: QA 팀이 Postman UI로 작성, CI에서 Newman 실행
   - 풍부한 Assertion: JSON Schema 검증, 응답 시간, 상태 코드
   - Newman Reporter: HTML, JSON, JUnit 리포트 생성
   - 환경 변수 지원: Staging, Production 환경 분리

2. **Supertest (보조)**:
   - Node.js/TypeScript 통합 테스트
   - Express/FastAPI 엔드포인트 직접 테스트
   - Jest와 통합으로 유닛 테스트와 일관성
   - 프로그래밍 방식으로 복잡한 시나리오 작성

**기술적 적합성**:
- QA 팀: Postman UI로 API 테스트 작성
- 개발팀: Supertest로 통합 테스트 작성
- CI/CD: Newman으로 자동 실행
- 50개 API 엔드포인트 커버리지 달성 가능

### Alternatives Considered

| Tool | Pros | Cons | Verdict |
|------|------|------|---------|
| **Newman (Postman CLI)** | - Postman 컬렉션 재사용<br>- QA 팀 협업 용이<br>- CI/CD 통합 간편<br>- 풍부한 Assertion<br>- 환경 변수 지원 | - GUI 없음 (CLI만)<br>- Postman 의존성 | **주 도구 선택** |
| **Supertest** | - Node.js 통합 테스트<br>- TypeScript 지원<br>- Jest 통합<br>- 프로그래밍 방식 | - Postman 컬렉션 미지원<br>- 팀 협업 제한 | **보조 도구 선택** |
| **REST Assured** | - Java 기반<br>- BDD 스타일<br>- 강력한 Assertion | - Java 언어 장벽<br>- Python/TypeScript 스택 불일치 | 제외 |
| **Tavern** | - Python YAML 기반<br>- pytest 통합<br>- 간단한 시나리오 | - 복잡한 시나리오 제한<br>- 커뮤니티 작음 | 제외 |
| **Karate** | - BDD 스타일<br>- 통합 테스트 프레임워크<br>- UI 테스트 지원 | - Java 기반<br>- 학습 곡선 높음<br>- 과도한 기능 | 제외 |

### Best Practices

1. **Newman Postman 컬렉션 구조**
   ```json
   // tests/api/collections/ecommerce-api.postman_collection.json
   {
     "info": {
       "name": "ShopFDS Ecommerce API",
       "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
     },
     "item": [
       {
         "name": "Authentication",
         "item": [
           {
             "name": "Register User",
             "request": {
               "method": "POST",
               "url": "{{base_url}}/api/auth/register",
               "body": {
                 "mode": "raw",
                 "raw": "{\"email\":\"test@example.com\",\"password\":\"password123\"}"
               }
             },
             "event": [
               {
                 "listen": "test",
                 "script": {
                   "exec": [
                     "pm.test('Status is 201', function() {",
                     "  pm.response.to.have.status(201);",
                     "});",
                     "pm.test('User ID exists', function() {",
                     "  const jsonData = pm.response.json();",
                     "  pm.expect(jsonData.id).to.exist;",
                     "  pm.environment.set('user_id', jsonData.id);",
                     "});"
                   ]
                 }
               }
             ]
           }
         ]
       },
       {
         "name": "Products",
         "item": [
           {
             "name": "Get Products",
             "request": {
               "method": "GET",
               "url": "{{base_url}}/api/products"
             },
             "event": [
               {
                 "listen": "test",
                 "script": {
                   "exec": [
                     "pm.test('Status is 200', function() {",
                     "  pm.response.to.have.status(200);",
                     "});",
                     "pm.test('Response time < 200ms', function() {",
                     "  pm.expect(pm.response.responseTime).to.be.below(200);",
                     "});",
                     "pm.test('Products array exists', function() {",
                     "  const jsonData = pm.response.json();",
                     "  pm.expect(jsonData).to.be.an('array');",
                     "});"
                   ]
                 }
               }
             ]
           }
         ]
       },
       {
         "name": "FDS Integration",
         "item": [
           {
             "name": "Evaluate High Risk Transaction",
             "request": {
               "method": "POST",
               "url": "{{base_url}}/api/orders",
               "body": {
                 "mode": "raw",
                 "raw": "{\"amount\":5000000,\"user_id\":\"{{user_id}}\"}"
               }
             },
             "event": [
               {
                 "listen": "test",
                 "script": {
                   "exec": [
                     "pm.test('FDS requires additional auth', function() {",
                     "  const jsonData = pm.response.json();",
                     "  pm.expect(jsonData.requires_verification).to.be.true;",
                     "  pm.expect(jsonData.risk_level).to.eql('high');",
                     "});"
                   ]
                 }
               }
             ]
           }
         ]
       }
     ]
   }
   ```

2. **Newman 환경 변수**
   ```json
   // tests/api/environments/staging.postman_environment.json
   {
     "name": "Staging",
     "values": [
       {
         "key": "base_url",
         "value": "http://staging.shopfds.com",
         "enabled": true
       },
       {
         "key": "auth_token",
         "value": "",
         "enabled": true
       }
     ]
   }
   ```

3. **Newman CLI 실행**
   ```bash
   # tests/api/run-newman.sh
   #!/bin/bash

   newman run tests/api/collections/ecommerce-api.postman_collection.json \
     --environment tests/api/environments/staging.postman_environment.json \
     --reporters cli,html,json \
     --reporter-html-export newman-report.html \
     --reporter-json-export newman-report.json \
     --bail # 첫 실패 시 중단
   ```

4. **Supertest 통합 테스트**
   ```typescript
   // tests/api/integration/ecommerce-fds-integration.test.ts
   import request from 'supertest';
   import { app } from '../../../services/ecommerce/backend/src/main';

   describe('Ecommerce → FDS Integration', () => {
     let authToken: string;
     let userId: string;

     beforeAll(async () => {
       // 테스트 사용자 등록
       const res = await request(app)
         .post('/api/auth/register')
         .send({ email: 'test@example.com', password: 'password123' });

       expect(res.status).toBe(201);
       userId = res.body.id;
       authToken = res.body.token;
     });

     it('should approve low risk transaction', async () => {
       const res = await request(app)
         .post('/api/orders')
         .set('Authorization', `Bearer ${authToken}`)
         .send({
           amount: 10000,
           user_id: userId,
           items: [{ product_id: 'prod_1', quantity: 1 }],
         });

       expect(res.status).toBe(201);
       expect(res.body.fds_result.decision).toBe('approve');
       expect(res.body.fds_result.risk_level).toBe('low');
     });

     it('should require OTP for high risk transaction', async () => {
       const res = await request(app)
         .post('/api/orders')
         .set('Authorization', `Bearer ${authToken}`)
         .send({
           amount: 5000000, // 고위험 거래
           user_id: userId,
         });

       expect(res.status).toBe(202); // Accepted, pending verification
       expect(res.body.requires_verification).toBe(true);
       expect(res.body.fds_result.risk_level).toBe('high');
     });

     afterAll(async () => {
       // 테스트 데이터 정리
       await request(app)
         .delete(`/api/users/${userId}`)
         .set('Authorization', `Bearer ${authToken}`);
     });
   });
   ```

5. **JSON Schema 검증**
   ```javascript
   // Postman 테스트 스크립트
   const schema = {
     type: 'object',
     properties: {
       id: { type: 'string' },
       amount: { type: 'number' },
       fds_result: {
         type: 'object',
         properties: {
           risk_score: { type: 'number', minimum: 0, maximum: 100 },
           decision: { type: 'string', enum: ['approve', 'reject', 'manual_review'] },
         },
         required: ['risk_score', 'decision'],
       },
     },
     required: ['id', 'amount', 'fds_result'],
   };

   pm.test('Schema is valid', function() {
     pm.response.to.have.jsonSchema(schema);
   });
   ```

6. **CI/CD 통합**
   ```yaml
   # .github/workflows/api-tests.yml
   - name: Run Newman Tests
     run: |
       npm install -g newman newman-reporter-htmlextra
       newman run tests/api/collections/ecommerce-api.postman_collection.json \
         --environment tests/api/environments/staging.postman_environment.json \
         --reporters cli,htmlextra \
         --reporter-htmlextra-export newman-report.html

   - name: Upload Test Report
     uses: actions/upload-artifact@v3
     if: always()
     with:
       name: newman-report
       path: newman-report.html
   ```

### Integration Notes

**ShopFDS 아키텍처 통합**:

1. **API 테스트 컬렉션 구조**:
   ```
   tests/api/
   ├── collections/
   │   ├── ecommerce-api.postman_collection.json
   │   ├── fds-api.postman_collection.json
   │   ├── ml-service-api.postman_collection.json
   │   └── admin-dashboard-api.postman_collection.json
   ├── environments/
   │   ├── local.postman_environment.json
   │   ├── staging.postman_environment.json
   │   └── production.postman_environment.json
   ├── integration/
   │   ├── ecommerce-fds-integration.test.ts     # Supertest
   │   ├── fds-ml-integration.test.ts
   │   └── end-to-end-flow.test.ts
   ├── run-newman.sh
   └── README.md
   ```

2. **서비스 간 통합 테스트 시나리오**:
   - **Ecommerce → FDS**: 주문 생성 → FDS 평가 → 결정 (approve/reject/manual_review)
   - **FDS → ML**: 거래 평가 → ML 예측 → 위험 점수 반환
   - **Ecommerce → FDS → OTP**: 고위험 거래 → 추가 인증 요구 → OTP 검증 → 주문 완료

3. **Newman 실행 모드**:
   - 로컬: `newman run --environment local.json`
   - CI: `newman run --environment staging.json --bail`
   - Production: `newman run --environment production.json --delay-request 1000` (Rate Limiting 고려)

4. **커버리지 목표**:
   - Ecommerce API: 15개 엔드포인트
   - FDS API: 5개 엔드포인트
   - ML Service API: 10개 엔드포인트
   - Admin Dashboard API: 20개 엔드포인트
   - **총 50개 엔드포인트 100% 커버리지**

5. **실패 시 디버깅**:
   - Newman HTML 리포트: 상세한 요청/응답, 실패 이유
   - Supertest: Jest 스냅샷으로 응답 변화 추적
   - CI 아티팩트: Newman 리포트 자동 업로드

---

## 7. 통합 아키텍처 결정

### 전체 아키텍처 다이어그램

```
+------------------+
|  GitHub Actions  | ← CI/CD 파이프라인
+------------------+
        |
        v
+------------------+     +------------------+     +------------------+
|   E2E Testing    |     |   API Testing    |     | Performance Test |
|   (Playwright)   |     | (Newman/Supertest|     |      (k6)        |
+------------------+     +------------------+     +------------------+
        |                        |                        |
        v                        v                        v
+------------------------------------------------------------------------+
|                         Kubernetes Cluster                             |
|  +------------------+     +------------------+     +------------------+|
|  | Ecommerce (v1.0) | ←→ |   FDS (v1.0)     | ←→ | ML-Service (v1.0)||
|  | Ecommerce (v1.1) |     |   FDS (v1.1)     |     | ML-Service (v1.1)||
|  +------------------+     +------------------+     +------------------+|
|         ↑ ↓                      ↑ ↓                      ↑ ↓         |
|  +------------------+     +------------------+     +------------------+|
|  |  Istio Gateway   |     | Istio VirtualSvc |     | DestinationRule  ||
|  +------------------+     +------------------+     +------------------+|
|         ↑                        ↑                        ↑            |
|  +------------------+     +------------------+     +------------------+|
|  |     Flagger      |     |   Litmus Chaos   |     | Prometheus/Grafana|
|  | (카나리 컨트롤러)  |     | (장애 주입)        |     | (모니터링)        |
|  +------------------+     +------------------+     +------------------+|
+------------------------------------------------------------------------+
```

### 배포 플로우

```
1. 코드 커밋 (GitHub)
   ↓
2. GitHub Actions CI 시작
   ↓
3. [Stage 1] 단위 테스트 (pytest, jest)
   ↓
4. [Stage 2] API 테스트 (Newman, Supertest)
   ↓
5. [Stage 3] E2E 테스트 (Playwright)
   ↓
6. [Stage 4] Docker 이미지 빌드 & 푸시
   ↓
7. [Stage 5] Staging 환경 배포
   ↓
8. [Stage 6] 성능 테스트 (k6 Spike Test)
   ↓
9. [Stage 7] Chaos Engineering (Litmus)
   ↓
10. [Stage 8] 카나리 배포 시작 (Flagger)
    ↓
11. 10% 트래픽 라우팅 → 메트릭 분석 (1분)
    ↓
12. 성공 → 50% 트래픽 → 메트릭 분석 (1분)
    ↓
13. 성공 → 100% 트래픽 → 배포 완료
    ↓
14. 실패 시 → 자동 롤백 (30초 이내)
```

### 기술 스택 매핑

| 계층 | 기술 | 목적 |
|-----|------|------|
| **E2E Testing** | Playwright | 브라우저 자동화, 20개 핵심 플로우 검증 |
| **API Testing** | Newman, Supertest | 서비스 간 통합, 50개 엔드포인트 검증 |
| **Performance** | k6 | Spike/Soak/Stress 테스트, 1,000 TPS |
| **Service Mesh** | Istio | 트래픽 분할, mTLS, Observability |
| **Canary Deployment** | Flagger | 자동 카나리 배포, 30초 롤백 |
| **Chaos Engineering** | Litmus Chaos | 5가지 장애 시나리오, 30초 복구 검증 |
| **Monitoring** | Prometheus, Grafana | 메트릭 수집, 대시보드 시각화 |
| **CI/CD** | GitHub Actions | 자동화 파이프라인, 30분 이내 완료 |

### 예상 성과

| 지표 | 현재 | 목표 | 예상 개선 |
|-----|------|------|----------|
| **배포 신뢰도** | 60% | 95%+ | +58% |
| **배포 실패율** | 40% | 5% | -88% |
| **장애 복구 시간** | 5분+ | 30초 | -90% |
| **프로덕션 장애** | 월 5회 | 월 1회 이하 | -80% |
| **테스트 커버리지** | 70% | 95%+ | +36% |
| **E2E 테스트 자동화** | 없음 | 20개 시나리오 | 신규 |
| **성능 테스트 자동화** | 수동 | 자동 (CI 통합) | 신규 |
| **카나리 배포** | 없음 | 4개 서비스 | 신규 |

### 리소스 요구사항

**Kubernetes 클러스터**:
- Control Plane: 4 CPU, 8Gi 메모리
- Worker Nodes: 3대 x (8 CPU, 16Gi 메모리)
- Istio: 2 CPU, 4Gi 메모리
- Flagger: 500m CPU, 1Gi 메모리
- Litmus: 1 CPU, 2Gi 메모리
- 총 추가 리소스: ~6 CPU, ~12Gi 메모리

**CI/CD 런타임**:
- Playwright E2E: 4 CPU, 8Gi 메모리, 10분
- Newman API: 2 CPU, 4Gi 메모리, 5분
- k6 Performance: 4 CPU, 8Gi 메모리, 10분 (Spike), 24시간 (Soak)
- 총 CI 실행 시간: 30분 이내 (병렬 실행)

### 단계별 도입 계획

**Phase 1: 기초 구축 (주 1-2)**
- Kubernetes 클러스터 확인
- Istio Service Mesh 설치
- Prometheus/Grafana 통합

**Phase 2: E2E 테스트 (주 3-4)**
- Playwright 설정
- 20개 핵심 시나리오 작성
- CI/CD 통합

**Phase 3: 카나리 배포 (주 5-6)**
- Flagger 설치
- 4개 서비스 Canary CRD 작성
- 자동 롤백 검증

**Phase 4: Chaos Engineering (주 7-8)**
- Litmus Chaos 설치
- 5가지 장애 시나리오 작성
- 복원력 검증

**Phase 5: 성능 및 API 테스트 (주 9-10)**
- k6 시나리오 작성
- Newman 컬렉션 작성
- CI/CD 통합

**Phase 6: 프로덕션 배포 (주 11-12)**
- Staging 검증 완료
- Production 점진적 도입
- 모니터링 및 최적화

---

## 결론

ShopFDS 프로젝트의 E2E 테스트 자동화 및 시스템 복원력 검증 기능은 다음 기술 스택으로 구현됩니다:

1. **E2E Testing**: Playwright (브라우저 자동화, TypeScript)
2. **Service Mesh**: Istio (트래픽 관리, mTLS)
3. **Canary Deployment**: Flagger (자동 카나리 배포)
4. **Chaos Engineering**: Litmus Chaos (Kubernetes 네이티브 장애 주입)
5. **Performance Testing**: k6 (JavaScript 부하 테스트)
6. **API Testing**: Newman + Supertest (Postman CLI + Node.js)

이 기술 스택은 기존 ShopFDS 아키텍처(Python 3.11+, TypeScript 5.3+, Kubernetes, Prometheus/Grafana)와 완벽히 통합되며, 배포 신뢰도를 95% 이상으로 향상시키고, 프로덕션 장애를 80% 감소시킬 것으로 예상됩니다.

모든 도구는 오픈소스이며 CNCF 생태계 또는 업계 표준 도구로, 장기적인 유지보수성과 커뮤니티 지원이 보장됩니다.
