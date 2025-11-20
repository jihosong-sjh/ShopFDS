# E2E 테스트 자동화 및 시스템 복원력 검증 - 빠른 시작 가이드

**Feature Branch**: `005-e2e-testing`
**작성일**: 2025-11-20
**버전**: 1.0.0

## 목차

1. [사전 요구사항](#사전-요구사항)
2. [5분 빠른 시작](#5분-빠른-시작)
3. [E2E Testing 빠른 시작](#e2e-testing-빠른-시작)
4. [Canary Deployment 빠른 시작](#canary-deployment-빠른-시작)
5. [Chaos Engineering 빠른 시작](#chaos-engineering-빠른-시작)
6. [Performance Testing 빠른 시작](#performance-testing-빠른-시작)
7. [API Testing 빠른 시작](#api-testing-빠른-시작)
8. [문제 해결 (Troubleshooting)](#문제-해결-troubleshooting)
9. [다음 단계](#다음-단계)

---

## 사전 요구사항

### 필수 도구

#### 1. Docker Desktop (Windows)
- **버전**: Docker Desktop 4.25+ for Windows
- **다운로드**: https://www.docker.com/products/docker-desktop
- **설치 후 확인**:
  ```powershell
  docker --version
  # Docker version 24.0.6, build...

  docker-compose --version
  # Docker Compose version v2.23.0
  ```

#### 2. Kubernetes 클러스터
Windows 환경에서는 다음 옵션 중 하나를 선택:

**옵션 A: Docker Desktop Kubernetes (권장 - 가장 간단)**
- Docker Desktop 설정에서 Kubernetes 활성화
- 설정 > Kubernetes > Enable Kubernetes 체크
- 확인:
  ```powershell
  kubectl version --client
  kubectl cluster-info
  ```

**옵션 B: Minikube**
- 다운로드: https://minikube.sigs.k8s.io/docs/start/
- 설치 후 시작:
  ```powershell
  minikube start --cpus=4 --memory=8192 --disk-size=40g
  minikube status
  ```

**옵션 C: k3s (경량 Kubernetes)**
- Windows용 WSL2 필요
- 설치:
  ```powershell
  wsl --install
  # WSL2에서:
  curl -sfL https://get.k3s.io | sh -
  ```

#### 3. Node.js 및 npm
- **버전**: Node.js 18+ LTS
- **다운로드**: https://nodejs.org/
- **확인**:
  ```powershell
  node --version
  # v18.18.0

  npm --version
  # 10.2.0
  ```

#### 4. Python
- **버전**: Python 3.11+
- **다운로드**: https://www.python.org/downloads/
- **확인**:
  ```powershell
  python --version
  # Python 3.11.5
  ```

#### 5. kubectl
- **설치** (Docker Desktop Kubernetes 사용 시 자동 설치됨):
  ```powershell
  # 또는 수동 설치:
  choco install kubernetes-cli

  # 확인:
  kubectl version --client
  ```

#### 6. Helm
- **버전**: Helm 3.12+
- **설치**:
  ```powershell
  choco install kubernetes-helm

  # 또는 스크립트로 설치:
  $scriptUrl = "https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3"
  Invoke-WebRequest -Uri $scriptUrl -OutFile get_helm.ps1
  .\get_helm.ps1

  # 확인:
  helm version
  ```

### 시스템 요구사항

#### 최소 사양
- **CPU**: 4 코어
- **RAM**: 8GB
- **디스크**: 40GB 여유 공간
- **OS**: Windows 10/11 Pro (Hyper-V 지원)

#### 권장 사양 (로컬 전체 환경 실행)
- **CPU**: 8 코어
- **RAM**: 16GB
- **디스크**: 80GB SSD
- **OS**: Windows 11 Pro

#### Kubernetes 클러스터 리소스 (프로덕션)
- **Control Plane**: 4 CPU, 8Gi 메모리
- **Worker Nodes**: 3대 x (8 CPU, 16Gi 메모리)
- **총 리소스**: 28 CPU, 56Gi 메모리

### 네트워크 포트

다음 포트들이 열려 있어야 합니다:

| 서비스 | 포트 | 용도 |
|--------|------|------|
| Ecommerce Backend | 8000 | FastAPI 서버 |
| FDS | 8001 | FDS 평가 API |
| ML Service | 8002 | ML 모델 API |
| Admin Dashboard | 8003 | 관리자 백엔드 |
| Frontend | 3000 | React 프론트엔드 |
| Playwright | 9323 | 테스트 디버깅 |
| Prometheus | 9090 | 메트릭 수집 |
| Grafana | 3001 | 대시보드 |
| Istio Ingress | 80, 443 | 외부 트래픽 |

---

## 5분 빠른 시작

### Step 1: 클러스터 준비 (2분)

#### Docker Desktop Kubernetes 사용 시

```powershell
# 1. Docker Desktop에서 Kubernetes 활성화 확인
kubectl cluster-info

# 2. 네임스페이스 생성
kubectl create namespace ecommerce
kubectl create namespace fds
kubectl create namespace ml-service
kubectl create namespace admin-dashboard
kubectl create namespace istio-system
kubectl create namespace litmus

# 3. 확인
kubectl get namespaces
```

#### Minikube 사용 시

```powershell
# 1. Minikube 시작 (약 2분 소요)
minikube start --cpus=4 --memory=8192 --disk-size=40g

# 2. 애드온 활성화
minikube addons enable metrics-server
minikube addons enable ingress

# 3. 네임스페이스 생성
kubectl create namespace ecommerce
kubectl create namespace fds
kubectl create namespace istio-system
kubectl create namespace litmus
```

### Step 2: Istio 설치 (1분)

```powershell
# 1. Istio 다운로드 (Windows)
cd D:\side-project\ShopFDS
curl -L https://istio.io/downloadIstio | sh -
cd istio-1.20.0

# 2. Istio 설치
.\bin\istioctl install --set profile=demo -y

# 3. 설치 확인
kubectl get pods -n istio-system
# NAME                                    READY   STATUS    RESTARTS   AGE
# istiod-xxx                              1/1     Running   0          1m
# istio-ingressgateway-xxx                1/1     Running   0          1m
```

### Step 3: Litmus Chaos 설치 (1분)

```powershell
# 1. Litmus Operator 설치
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v3.8.0.yaml

# 2. 설치 확인
kubectl get pods -n litmus
# NAME                                    READY   STATUS    RUNNING
# chaos-operator-ce-xxx                   1/1     Running   0

# 3. Chaos Experiments 설치
kubectl apply -f https://hub.litmuschaos.io/api/chaos/3.8.0?file=charts/generic/experiments.yaml -n litmus
```

### Step 4: Playwright 설치 (30초)

```powershell
# 1. 프로젝트 루트로 이동
cd D:\side-project\ShopFDS\tests\e2e

# 2. 의존성 설치
npm install

# 3. Playwright 브라우저 설치
npx playwright install

# 4. 확인
npx playwright --version
# Version 1.40.0
```

### Step 5: 첫 E2E 테스트 실행 (30초)

```powershell
# 1. 백엔드 서비스 시작 (Docker Compose)
cd D:\side-project\ShopFDS
docker-compose up -d

# 2. 서비스 준비 대기 (약 30초)
timeout /t 30

# 3. E2E 테스트 실행
cd tests\e2e
npx playwright test scenarios/login.spec.ts

# 출력 예시:
# Running 1 test using 1 worker
# [chromium] › scenarios/login.spec.ts:3:1 › 사용자 로그인 플로우
# [OK] scenarios/login.spec.ts:3:1 › 사용자 로그인 플로우 (2.5s)
# 1 passed (3s)
```

**축하합니다!** 기본 환경이 준비되었습니다.

---

## E2E Testing 빠른 시작

### 1. Playwright 프로젝트 초기화

#### 프로젝트 구조 생성

```powershell
cd D:\side-project\ShopFDS

# E2E 테스트 디렉토리 생성
mkdir tests\e2e
cd tests\e2e

# package.json 생성
npm init -y

# Playwright 및 의존성 설치
npm install --save-dev @playwright/test @types/node
npm install --save-dev dotenv
```

#### playwright.config.ts 생성

`tests/e2e/playwright.config.ts` 파일 생성:

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './scenarios',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 4 : 2,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
});
```

### 2. 첫 번째 테스트 시나리오 작성

#### 로그인 테스트 (`tests/e2e/scenarios/login.spec.ts`)

```typescript
import { test, expect } from '@playwright/test';

test.describe('사용자 인증', () => {
  test('로그인 성공 플로우', async ({ page }) => {
    // 1. 로그인 페이지 이동
    await page.goto('/login');

    // 2. 페이지 로드 확인
    await expect(page).toHaveTitle(/ShopFDS/);

    // 3. 이메일 입력
    await page.fill('[data-testid="email"]', 'test@example.com');

    // 4. 비밀번호 입력
    await page.fill('[data-testid="password"]', 'password123');

    // 5. 로그인 버튼 클릭
    await page.click('[data-testid="login-button"]');

    // 6. 대시보드로 리다이렉트 확인
    await expect(page).toHaveURL(/\/dashboard/);

    // 7. 사용자 메뉴 표시 확인
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('로그인 실패 - 잘못된 비밀번호', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'wrongpassword');
    await page.click('[data-testid="login-button"]');

    // 에러 메시지 표시 확인
    await expect(page.locator('[data-testid="error-message"]'))
      .toHaveText(/이메일 또는 비밀번호가 올바르지 않습니다/);
  });
});
```

#### 전체 결제 플로우 테스트 (`tests/e2e/scenarios/checkout.spec.ts`)

```typescript
import { test, expect } from '@playwright/test';

test.describe('주문 결제 플로우', () => {
  test.beforeEach(async ({ page }) => {
    // 모든 테스트 전에 로그인
    await page.goto('/login');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('저위험 거래 - 즉시 승인', async ({ page }) => {
    // 1. 상품 검색
    await page.goto('/products');
    await page.fill('[data-testid="search-input"]', '노트북');
    await page.click('[data-testid="search-button"]');

    // 2. 첫 번째 상품 선택
    await page.click('[data-testid="product-card"]:first-child');

    // 3. 장바구니 추가
    await page.click('[data-testid="add-to-cart"]');
    await expect(page.locator('[data-testid="cart-count"]')).toHaveText('1');

    // 4. 장바구니로 이동
    await page.click('[data-testid="cart-icon"]');
    await expect(page).toHaveURL(/\/cart/);

    // 5. 결제 진행
    await page.click('[data-testid="checkout-button"]');

    // 6. 배송 정보 입력
    await page.fill('[data-testid="shipping-name"]', '홍길동');
    await page.fill('[data-testid="shipping-address"]', '서울특별시 강남구');
    await page.fill('[data-testid="shipping-phone"]', '010-1234-5678');

    // 7. 결제 정보 입력
    await page.fill('[data-testid="card-number"]', '1234567890123456');
    await page.fill('[data-testid="card-expiry"]', '12/25');
    await page.fill('[data-testid="card-cvv"]', '123');

    // 8. 주문 완료
    await page.click('[data-testid="complete-order"]');

    // 9. 주문 완료 확인 (저위험 거래 - 즉시 승인)
    await expect(page).toHaveURL(/\/orders\/\w+/);
    await expect(page.locator('[data-testid="order-status"]'))
      .toHaveText(/결제 완료/);
  });

  test('고위험 거래 - OTP 추가 인증', async ({ page }) => {
    // 1-7단계는 위와 동일하지만 고액 상품 선택
    await page.goto('/products');
    await page.fill('[data-testid="search-input"]', '명품시계');
    await page.click('[data-testid="search-button"]');
    await page.click('[data-testid="product-card"]:first-child');
    await page.click('[data-testid="add-to-cart"]');
    await page.click('[data-testid="cart-icon"]');
    await page.click('[data-testid="checkout-button"]');

    await page.fill('[data-testid="shipping-name"]', '홍길동');
    await page.fill('[data-testid="shipping-address"]', '서울특별시 강남구');
    await page.fill('[data-testid="shipping-phone"]', '010-1234-5678');
    await page.fill('[data-testid="card-number"]', '1234567890123456');
    await page.fill('[data-testid="card-expiry"]', '12/25');
    await page.fill('[data-testid="card-cvv"]', '123');

    // 8. 주문 시도
    await page.click('[data-testid="complete-order"]');

    // 9. FDS 추가 인증 요구 확인
    await expect(page.locator('[data-testid="otp-modal"]')).toBeVisible();
    await expect(page.locator('[data-testid="otp-message"]'))
      .toHaveText(/추가 인증이 필요합니다/);

    // 10. OTP 입력
    await page.fill('[data-testid="otp-input"]', '123456');
    await page.click('[data-testid="verify-otp"]');

    // 11. 주문 완료 확인
    await expect(page).toHaveURL(/\/orders\/\w+/);
    await expect(page.locator('[data-testid="order-status"]'))
      .toHaveText(/결제 완료/);
  });
});
```

### 3. 로컬 실행

#### 단일 테스트 실행

```powershell
# 로그인 테스트만 실행
npx playwright test scenarios/login.spec.ts

# 특정 브라우저에서 실행
npx playwright test scenarios/login.spec.ts --project=chromium
```

#### 전체 테스트 실행

```powershell
# 모든 시나리오 실행 (3개 브라우저 병렬)
npx playwright test

# UI 모드로 실행 (디버깅 용이)
npx playwright test --ui

# 헤드풀 모드 (브라우저 UI 보이기)
npx playwright test --headed
```

#### HTML 리포트 확인

```powershell
# 리포트 생성 및 자동 열기
npx playwright show-report

# 브라우저에서 자동으로 열림:
# http://localhost:9323/
```

### 4. CI에서 실행

#### GitHub Actions 워크플로우 (`tests/e2e/.github/workflows/e2e-tests.yml`)

```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop, 005-e2e-testing]
  pull_request:
    branches: [main]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        browser: [chromium, firefox, webkit]

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd tests/e2e
          npm ci

      - name: Install Playwright browsers
        run: |
          cd tests/e2e
          npx playwright install --with-deps ${{ matrix.browser }}

      - name: Start services
        run: docker-compose up -d

      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'
          timeout 60 bash -c 'until curl -f http://localhost:3000; do sleep 2; done'

      - name: Run E2E tests
        run: |
          cd tests/e2e
          npx playwright test --project=${{ matrix.browser }}

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report-${{ matrix.browser }}
          path: tests/e2e/playwright-report

      - name: Stop services
        if: always()
        run: docker-compose down
```

---

## Canary Deployment 빠른 시작

### 1. Flagger 설치

```powershell
# 1. Flagger Helm 저장소 추가
helm repo add flagger https://flagger.app
helm repo update

# 2. Flagger 설치 (Istio 연동)
helm upgrade --install flagger flagger/flagger `
  --namespace istio-system `
  --set meshProvider=istio `
  --set metricsServer=http://prometheus:9090

# 3. Flagger Load Tester 설치 (선택사항)
helm upgrade --install flagger-loadtester flagger/loadtester `
  --namespace istio-system

# 4. 설치 확인
kubectl get pods -n istio-system | findstr flagger
# flagger-xxx                             1/1     Running   0
# flagger-loadtester-xxx                  1/1     Running   0
```

### 2. 첫 카나리 배포 생성

#### Canary CRD 작성 (`infrastructure/k8s/canary/flagger/canary-ecommerce.yaml`)

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: ecommerce-backend
  namespace: ecommerce
spec:
  # 대상 Deployment
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ecommerce-backend

  # 프로그레스 타임아웃 (30분)
  progressDeadlineSeconds: 1800

  # 서비스 포트
  service:
    port: 8000
    targetPort: 8000
    portName: http

  # 카나리 분석 설정
  analysis:
    interval: 1m           # 1분마다 분석
    threshold: 5           # 5회 연속 실패 시 롤백
    maxWeight: 100         # 최대 100% 트래픽
    stepWeight: 10         # 10%씩 증가

    # 메트릭 기반 자동 판단
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 95            # 95% 이상 성공률 유지
      interval: 1m

    - name: request-duration
      thresholdRange:
        max: 200           # 200ms 이하 응답 시간
      interval: 1m

    # Load Testing (선택사항)
    webhooks:
    - name: load-test
      url: http://flagger-loadtester.istio-system/
      timeout: 5s
      metadata:
        type: cmd
        cmd: "hey -z 1m -q 10 -c 2 http://ecommerce-backend-canary.ecommerce:8000/health"
```

#### Canary 배포

```powershell
# 1. Canary CRD 적용
kubectl apply -f infrastructure\k8s\canary\flagger\canary-ecommerce.yaml

# 2. Canary 상태 확인
kubectl get canary -n ecommerce
# NAME                 STATUS        WEIGHT   LASTTRANSITIONTIME
# ecommerce-backend    Initialized   0        2025-11-20T10:00:00Z

# 3. 새 버전 배포 (이미지 태그 변경으로 카나리 트리거)
kubectl set image deployment/ecommerce-backend `
  ecommerce-backend=ecommerce-backend:v1.1.0 `
  -n ecommerce

# 4. Flagger가 자동으로 카나리 배포 시작
kubectl get canary -n ecommerce -w
# NAME                 STATUS        WEIGHT   LASTTRANSITIONTIME
# ecommerce-backend    Progressing   10       2025-11-20T10:01:00Z
# ecommerce-backend    Progressing   20       2025-11-20T10:02:00Z
# ecommerce-backend    Progressing   30       2025-11-20T10:03:00Z
# ...
# ecommerce-backend    Succeeded     100      2025-11-20T10:10:00Z
```

### 3. 트래픽 모니터링

#### Prometheus 쿼리

```promql
# 카나리 트래픽 비율
sum(rate(istio_requests_total{destination_workload="ecommerce-backend-canary"}[1m])) /
sum(rate(istio_requests_total{destination_workload=~"ecommerce-backend.*"}[1m])) * 100

# 에러율
100 - sum(rate(istio_requests_total{
  destination_workload="ecommerce-backend-canary",
  response_code!~"5.*"
}[1m])) /
sum(rate(istio_requests_total{
  destination_workload="ecommerce-backend-canary"
}[1m])) * 100

# P95 응답 시간
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{
    destination_workload="ecommerce-backend-canary"
  }[1m])) by (le)
)
```

#### Grafana 대시보드

```powershell
# 1. Grafana 접속 (포트 포워딩)
kubectl port-forward -n istio-system svc/grafana 3001:3000

# 2. 브라우저에서 접속
# http://localhost:3001
# Username: admin
# Password: admin (기본값)

# 3. Flagger 대시보드 임포트
# Dashboards > Import > ID: 15474 (Flagger Canary Dashboard)
```

### 4. 수동 트래픽 조정

```powershell
# 현재 트래픽 비율 확인
kubectl get canary ecommerce-backend -n ecommerce -o jsonpath='{.status.canaryWeight}'

# 수동으로 트래픽 50%로 조정
kubectl patch canary ecommerce-backend -n ecommerce --type merge `
  -p '{\"spec\":{\"analysis\":{\"stepWeight\":50}}}'

# Canary 일시 중지
kubectl patch canary ecommerce-backend -n ecommerce --type merge `
  -p '{\"spec\":{\"skipAnalysis\":true}}'
```

### 5. 롤백 테스트

#### 자동 롤백 (에러율 초과 시)

```powershell
# 1. 의도적으로 에러 발생시키기 (예: 잘못된 설정 배포)
kubectl set image deployment/ecommerce-backend `
  ecommerce-backend=ecommerce-backend:broken-version `
  -n ecommerce

# 2. Flagger 자동 감지 및 롤백 확인
kubectl get canary ecommerce-backend -n ecommerce -w
# NAME                 STATUS    WEIGHT   LASTTRANSITIONTIME
# ecommerce-backend    Failed    0        2025-11-20T10:15:00Z

# 3. 이벤트 확인
kubectl describe canary ecommerce-backend -n ecommerce
# Events:
#   Type     Reason  Message
#   ----     ------  -------
#   Warning  Synced  Canary analysis failed, rolling back
```

#### 수동 롤백

```powershell
# Canary 삭제로 즉시 롤백
kubectl delete canary ecommerce-backend -n ecommerce

# 이전 버전으로 수동 롤백
kubectl set image deployment/ecommerce-backend `
  ecommerce-backend=ecommerce-backend:v1.0.0 `
  -n ecommerce
```

---

## Chaos Engineering 빠른 시작

### 1. 첫 장애 실험 정의 (Pod Delete)

#### ChaosEngine CRD 작성 (`infrastructure/chaos/experiments/pod-delete-fds.yaml`)

```yaml
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

  # 실험 상태
  engineState: 'active'

  # 서비스 어카운트
  chaosServiceAccount: litmus-admin

  # 장애 실험 목록
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        # 총 장애 지속 시간 (30초)
        - name: TOTAL_CHAOS_DURATION
          value: '30'

        # Pod 삭제 간격 (10초마다)
        - name: CHAOS_INTERVAL
          value: '10'

        # Graceful shutdown
        - name: FORCE
          value: 'false'

      # 복구 검증 Probe
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
            criteria: ">="
            value: "1"  # 최소 1개 Pod는 Running 상태
```

### 2. 실험 실행

#### RBAC 설정 (ServiceAccount 생성)

```powershell
# 1. ServiceAccount 및 권한 생성
kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: litmus-admin
  namespace: fds
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: litmus-admin
  namespace: fds
rules:
- apiGroups: [""]
  resources: ["pods", "events"]
  verbs: ["create", "delete", "get", "list", "patch", "update", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: litmus-admin
  namespace: fds
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: litmus-admin
subjects:
- kind: ServiceAccount
  name: litmus-admin
  namespace: fds
EOF
```

#### 실험 실행

```powershell
# 1. 실험 적용
kubectl apply -f infrastructure\chaos\experiments\pod-delete-fds.yaml

# 2. 실험 상태 실시간 모니터링
kubectl get chaosengine fds-pod-delete -n fds -w
# NAME              AGE   CHAOSENGINE   STATUS
# fds-pod-delete    5s    running       running

# 3. 실험 로그 확인
kubectl logs -f -n fds -l name=pod-delete

# 4. 실험 결과 확인 (완료 후)
kubectl get chaosresult fds-pod-delete-pod-delete -n fds -o yaml
```

### 3. 복구 시간 측정

#### Prometheus 메트릭

```promql
# 평균 복구 시간 (초)
avg(chaos_experiment_recovery_time_seconds{
  experiment="pod-delete",
  target_service="fds-backend"
})

# 최대 복구 시간
max(chaos_experiment_recovery_time_seconds{
  experiment="pod-delete",
  target_service="fds-backend"
})
```

#### kubectl로 수동 측정

```powershell
# 1. Pod 삭제 전 시간 기록
$startTime = Get-Date

# 2. Pod 수동 삭제 (테스트용)
kubectl delete pod -n fds -l app=fds-backend --force --grace-period=0

# 3. 새 Pod가 Ready 상태가 될 때까지 대기
kubectl wait --for=condition=Ready pod -n fds -l app=fds-backend --timeout=60s

# 4. 복구 시간 계산
$endTime = Get-Date
$recoveryTime = ($endTime - $startTime).TotalSeconds
Write-Host "복구 시간: $recoveryTime 초"
```

### 4. 결과 분석

#### ChaosResult 조회

```powershell
# 실험 결과 상세 조회
kubectl get chaosresult -n fds -o yaml

# 예시 출력:
# apiVersion: litmuschaos.io/v1alpha1
# kind: ChaosResult
# metadata:
#   name: fds-pod-delete-pod-delete
# spec:
#   experimentstatus:
#     verdict: Pass
#     failStep: N/A
#   probeSuccessPercentage: "100"
# status:
#   history:
#     passedRuns: 1
#     failedRuns: 0
```

#### ChaosCenter UI (선택사항)

```powershell
# 1. ChaosCenter 설치
helm install chaos litmuschaos/litmus `
  --namespace litmus `
  --set portal.frontend.service.type=LoadBalancer

# 2. 포트 포워딩
kubectl port-forward -n litmus svc/chaos-litmus-frontend-service 9091:9091

# 3. 브라우저에서 접속
# http://localhost:9091
# Username: admin
# Password: litmus
```

---

## Performance Testing 빠른 시작

### 1. k6 설치

#### Windows 설치

```powershell
# Chocolatey 사용
choco install k6

# 또는 직접 다운로드
# https://dl.k6.io/msi/k6-latest-amd64.msi
# MSI 파일 실행 후 설치

# 확인
k6 version
# k6 v0.48.0
```

### 2. 첫 부하 테스트 스크립트

#### Spike Test (`tests/performance/scenarios/spike-test.js`)

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

// 테스트 시나리오 설정
export const options = {
  stages: [
    { duration: '1m', target: 100 },   // 1분: 100 VU (정상 부하)
    { duration: '10s', target: 1000 }, // 10초: 1000 VU (10배 급증)
    { duration: '3m', target: 1000 },  // 3분: 1000 VU 유지
    { duration: '1m', target: 100 },   // 1분: 100 VU (복구)
    { duration: '1m', target: 0 },     // 1분: 종료
  ],
  thresholds: {
    'http_req_duration': ['p(95)<200'],  // P95 200ms 이내
    'http_req_failed': ['rate<0.05'],    // 에러율 5% 미만
  },
};

// VU 시나리오 (각 가상 사용자가 실행)
export default function () {
  // 1. 상품 목록 조회
  const productsRes = http.get('http://localhost:8000/api/products');
  check(productsRes, {
    'products status is 200': (r) => r.status === 200,
    'products response time < 200ms': (r) => r.timings.duration < 200,
  });

  sleep(1);

  // 2. 상품 상세 조회
  const productRes = http.get('http://localhost:8000/api/products/1');
  check(productRes, {
    'product status is 200': (r) => r.status === 200,
  });

  sleep(1);
}
```

### 3. Spike Test 실행

#### 로컬 실행

```powershell
# 1. 백엔드 서비스 시작 (아직 안 했다면)
cd D:\side-project\ShopFDS
docker-compose up -d

# 2. 서비스 준비 대기
timeout /t 10

# 3. k6 실행
cd tests\performance\scenarios
k6 run spike-test.js

# 출력 예시:
#   execution: local
#      script: spike-test.js
#      output: -
#
#   scenarios: (100.00%) 1 scenario, 1000 max VUs, 6m30s max duration
#              default: Up to 1000 looping VUs for 6m0s over 5 stages
#
#   [OK] http_req_duration..........: avg=85ms  min=45ms med=78ms max=195ms p(95)=165ms p(99)=185ms
#   [OK] http_req_failed............: 2.15% (215 of 10000)
#   http_reqs...................: 10000 166.67/s
```

#### HTML 리포트 생성

```powershell
# 1. k6 실행 with JSON 출력
k6 run --out json=test-results.json spike-test.js

# 2. HTML 리포트 변환 (k6-reporter 사용)
npm install -g k6-html-reporter
k6-html-reporter test-results.json --output report.html

# 3. 리포트 열기
start report.html
```

### 4. Grafana 대시보드 확인

#### Prometheus Remote Write 설정

```powershell
# 1. k6 Prometheus Remote Write로 메트릭 전송
k6 run --out experimental-prometheus-rw spike-test.js

# 2. Grafana k6 대시보드 임포트
# Dashboards > Import > ID: 2587 (k6 Load Testing Results)

# 3. 실시간 메트릭 확인
# http://localhost:3001
```

#### 주요 메트릭

```promql
# VU (Virtual Users) 수
k6_vus

# RPS (Requests Per Second)
rate(k6_http_reqs_total[1m])

# P95 응답 시간
histogram_quantile(0.95, rate(k6_http_req_duration_bucket[1m]))

# 에러율
rate(k6_http_req_failed[1m])
```

---

## API Testing 빠른 시작

### 1. Postman 컬렉션 생성

#### Newman 설치

```powershell
# 전역 설치
npm install -g newman newman-reporter-htmlextra

# 확인
newman --version
# 6.0.0
```

#### 샘플 컬렉션 생성 (`tests/api/collections/ecommerce-api.postman_collection.json`)

```json
{
  "info": {
    "name": "ShopFDS Ecommerce API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000",
      "type": "string"
    }
  ],
  "item": [
    {
      "name": "1. 회원가입",
      "event": [
        {
          "listen": "test",
          "script": {
            "exec": [
              "pm.test('상태 코드는 201', function() {",
              "  pm.response.to.have.status(201);",
              "});",
              "",
              "pm.test('사용자 ID 존재', function() {",
              "  const jsonData = pm.response.json();",
              "  pm.expect(jsonData.id).to.exist;",
              "  pm.environment.set('user_id', jsonData.id);",
              "});"
            ]
          }
        }
      ],
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"email\": \"test@example.com\",\n  \"password\": \"password123\",\n  \"name\": \"홍길동\"\n}"
        },
        "url": {
          "raw": "{{base_url}}/api/auth/register",
          "host": ["{{base_url}}"],
          "path": ["api", "auth", "register"]
        }
      }
    },
    {
      "name": "2. 로그인",
      "event": [
        {
          "listen": "test",
          "script": {
            "exec": [
              "pm.test('상태 코드는 200', function() {",
              "  pm.response.to.have.status(200);",
              "});",
              "",
              "pm.test('토큰 존재', function() {",
              "  const jsonData = pm.response.json();",
              "  pm.expect(jsonData.access_token).to.exist;",
              "  pm.environment.set('auth_token', jsonData.access_token);",
              "});"
            ]
          }
        }
      ],
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"email\": \"test@example.com\",\n  \"password\": \"password123\"\n}"
        },
        "url": {
          "raw": "{{base_url}}/api/auth/login",
          "host": ["{{base_url}}"],
          "path": ["api", "auth", "login"]
        }
      }
    },
    {
      "name": "3. 상품 목록 조회",
      "event": [
        {
          "listen": "test",
          "script": {
            "exec": [
              "pm.test('상태 코드는 200', function() {",
              "  pm.response.to.have.status(200);",
              "});",
              "",
              "pm.test('응답 시간 < 200ms', function() {",
              "  pm.expect(pm.response.responseTime).to.be.below(200);",
              "});",
              "",
              "pm.test('상품 배열 존재', function() {",
              "  const jsonData = pm.response.json();",
              "  pm.expect(jsonData).to.be.an('array');",
              "  pm.expect(jsonData.length).to.be.above(0);",
              "});"
            ]
          }
        }
      ],
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{auth_token}}"
          }
        ],
        "url": {
          "raw": "{{base_url}}/api/products",
          "host": ["{{base_url}}"],
          "path": ["api", "products"]
        }
      }
    }
  ]
}
```

### 2. Newman으로 실행

#### 기본 실행

```powershell
# 1. 디렉토리 이동
cd D:\side-project\ShopFDS\tests\api

# 2. 컬렉션 실행
newman run collections\ecommerce-api.postman_collection.json

# 출력:
# ShopFDS Ecommerce API
#
# [->] 1. 회원가입
#   [OK] POST http://localhost:8000/api/auth/register [201 Created, 500B, 125ms]
#   [OK] 상태 코드는 201
#   [OK] 사용자 ID 존재
#
# [->] 2. 로그인
#   [OK] POST http://localhost:8000/api/auth/login [200 OK, 450B, 85ms]
#   [OK] 상태 코드는 200
#   [OK] 토큰 존재
#
# [->] 3. 상품 목록 조회
#   [OK] GET http://localhost:8000/api/products [200 OK, 2.5KB, 65ms]
#   [OK] 상태 코드는 200
#   [OK] 응답 시간 < 200ms
#   [OK] 상품 배열 존재
#
# Summary:
#   Total: 3 requests
#   Passed: 7 tests
#   Failed: 0 tests
```

#### HTML 리포트 생성

```powershell
# HTMLExtra 리포터로 상세 리포트 생성
newman run collections\ecommerce-api.postman_collection.json `
  --reporters cli,htmlextra `
  --reporter-htmlextra-export reports\newman-report.html

# 리포트 열기
start reports\newman-report.html
```

### 3. CI 통합

#### GitHub Actions 워크플로우 (`.github/workflows/api-tests.yml`)

```yaml
name: API Tests

on:
  push:
    branches: [main, develop, 005-e2e-testing]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * *'  # 매일 자정 실행

jobs:
  api-tests:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install Newman
        run: npm install -g newman newman-reporter-htmlextra

      - name: Start services
        run: docker-compose up -d

      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'

      - name: Run API tests
        run: |
          cd tests/api
          newman run collections/ecommerce-api.postman_collection.json \
            --reporters cli,htmlextra,json \
            --reporter-htmlextra-export newman-report.html \
            --reporter-json-export newman-report.json

      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: newman-report
          path: tests/api/newman-report.html

      - name: Check test results
        run: |
          FAILED=$(jq '.run.stats.assertions.failed' tests/api/newman-report.json)
          if [ "$FAILED" -gt 0 ]; then
            echo "[FAIL] $FAILED tests failed"
            exit 1
          fi

      - name: Stop services
        if: always()
        run: docker-compose down
```

---

## 문제 해결 (Troubleshooting)

### 일반적인 문제

#### 1. Docker Kubernetes가 시작되지 않음

**증상**:
```powershell
kubectl cluster-info
# The connection to the server localhost:8080 was refused
```

**해결**:
```powershell
# 1. Docker Desktop 재시작
# 작업 표시줄에서 Docker Desktop 우클릭 > Restart

# 2. Kubernetes 재설정
# Docker Desktop > Settings > Kubernetes > Reset Kubernetes Cluster

# 3. WSL2 업데이트 (필요시)
wsl --update
```

#### 2. Istio 설치 실패

**증상**:
```powershell
.\bin\istioctl install
# Error: unable to connect to Kubernetes
```

**해결**:
```powershell
# 1. kubectl 연결 확인
kubectl get nodes

# 2. Istio 버전 확인 (호환성)
# Kubernetes 1.28+ -> Istio 1.20+

# 3. 권한으로 재시도 (PowerShell 관리자 모드)
.\bin\istioctl install --set profile=demo -y --skip-confirmation
```

#### 3. Playwright 브라우저 다운로드 실패

**증상**:
```powershell
npx playwright install
# Error: Failed to download Chromium
```

**해결**:
```powershell
# 1. 프록시 환경변수 설정 (회사 환경)
$env:HTTPS_PROXY="http://proxy.company.com:8080"

# 2. 수동 다운로드 및 설치
npx playwright install --force

# 3. 특정 브라우저만 설치
npx playwright install chromium
```

#### 4. Port 충돌

**증상**:
```powershell
docker-compose up
# Error: bind: address already in use
```

**해결**:
```powershell
# 1. 사용 중인 포트 확인
netstat -ano | findstr :8000

# 2. 프로세스 종료
taskkill /PID <PID> /F

# 3. 또는 docker-compose.yml에서 포트 변경
# ports:
#   - "8080:8000"  # 호스트 포트 8080으로 변경
```

#### 5. Flagger 카나리 배포가 진행되지 않음

**증상**:
```powershell
kubectl get canary -n ecommerce
# NAME                 STATUS        WEIGHT
# ecommerce-backend    Initialized   0
```

**해결**:
```powershell
# 1. Flagger 로그 확인
kubectl logs -n istio-system deployment/flagger

# 2. Deployment 이미지 태그 변경 확인
kubectl describe deployment ecommerce-backend -n ecommerce

# 3. VirtualService 생성 확인
kubectl get virtualservice -n ecommerce

# 4. Prometheus 연결 확인
kubectl logs -n istio-system deployment/flagger | grep prometheus
```

### 로그 확인 방법

#### Kubernetes Pod 로그

```powershell
# 특정 Pod 로그 확인
kubectl logs -n ecommerce <pod-name>

# 실시간 로그 스트리밍
kubectl logs -n ecommerce <pod-name> -f

# 이전 컨테이너 로그 (재시작 시)
kubectl logs -n ecommerce <pod-name> --previous

# Label로 필터링
kubectl logs -n ecommerce -l app=ecommerce-backend --tail=100
```

#### Docker Compose 로그

```powershell
# 전체 서비스 로그
docker-compose logs

# 특정 서비스 로그
docker-compose logs ecommerce-backend

# 실시간 로그
docker-compose logs -f fds
```

#### Playwright 디버깅

```powershell
# 디버그 모드로 실행
$env:DEBUG="pw:api"
npx playwright test

# 헤드풀 모드 (브라우저 UI 보이기)
npx playwright test --headed --debug

# 특정 테스트만 디버그
npx playwright test scenarios/login.spec.ts --debug
```

#### k6 디버깅

```powershell
# 상세 로그 출력
k6 run --verbose spike-test.js

# HTTP 요청/응답 상세
k6 run --http-debug spike-test.js

# 특정 VU만 실행 (디버깅)
k6 run --vus=1 --iterations=1 spike-test.js
```

### 디버깅 팁

#### 1. Kubernetes 리소스 상태 확인

```powershell
# Pod 상태 및 재시작 횟수
kubectl get pods -A -o wide

# 이벤트 확인
kubectl get events -n ecommerce --sort-by='.lastTimestamp'

# 리소스 사용량
kubectl top nodes
kubectl top pods -n ecommerce
```

#### 2. 네트워크 연결 테스트

```powershell
# Pod 내부에서 네트워크 테스트
kubectl exec -it -n ecommerce <pod-name> -- curl http://fds-backend:8001/health

# DNS 확인
kubectl exec -it -n ecommerce <pod-name> -- nslookup fds-backend

# Istio Sidecar 상태
kubectl exec -it -n ecommerce <pod-name> -c istio-proxy -- curl localhost:15000/stats
```

#### 3. Prometheus 메트릭 확인

```powershell
# Prometheus UI 포트 포워딩
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# 브라우저에서 접속: http://localhost:9090

# 쿼리 예시:
# - 전체 요청 수: sum(istio_requests_total)
# - 에러율: sum(rate(istio_requests_total{response_code=~"5.*"}[1m]))
```

---

## 다음 단계

### 고급 시나리오 작성

#### 1. E2E 테스트 확장
- Page Object Model 패턴 적용
- 재사용 가능한 Fixture 작성
- Visual Regression Testing (스크린샷 비교)
- Accessibility Testing (WCAG 준수)

**참고 문서**:
- `docs/e2e-testing/page-object-model.md`
- `docs/e2e-testing/visual-testing.md`

#### 2. 카나리 배포 고급 전략
- A/B 테스트 (Header 기반 라우팅)
- Blue-Green 배포
- 멀티 서비스 동시 배포
- 커스텀 메트릭 분석

**참고 문서**:
- `docs/canary-deployment/advanced-strategies.md`
- `docs/canary-deployment/custom-metrics.md`

#### 3. Chaos Engineering 복잡한 시나리오
- 네트워크 지연 + 리소스 부족 조합
- 데이터베이스 연결 실패 시뮬레이션
- 의존 서비스 다운 시나리오
- Chaos Workflow (여러 실험 조합)

**참고 문서**:
- `docs/chaos-engineering/advanced-scenarios.md`
- `docs/chaos-engineering/chaos-workflows.md`

### 프로덕션 배포 가이드

#### 1. 프로덕션 환경 준비
- Kubernetes 클러스터 구성 (AWS EKS, GCP GKE, Azure AKS)
- Istio 프로덕션 프로필 설정
- 모니터링 스택 구축 (Prometheus, Grafana, Jaeger)
- 로그 수집 (ELK Stack 또는 Loki)

**참고 문서**:
- `docs/deployment/production-setup.md`
- `infrastructure/k8s/production/README.md`

#### 2. CI/CD 파이프라인 확장
- GitHub Actions Self-hosted Runners
- Multi-stage 배포 (Dev → Staging → Production)
- 자동 롤백 조건 정의
- Slack/Teams 알림 통합

**참고 문서**:
- `docs/ci-cd/pipeline-guide.md`
- `.github/workflows/README.md`

### 모니터링 설정

#### 1. Grafana 대시보드 구성
- Flagger Canary Dashboard
- k6 Load Testing Results
- Istio Service Mesh Dashboard
- Litmus Chaos Dashboard

**대시보드 ID**:
- Flagger: 15474
- k6: 2587
- Istio: 7639, 7645
- Litmus: (커스텀 생성)

**참고 문서**:
- `docs/monitoring/grafana-dashboards.md`

#### 2. 알림 설정
- Prometheus Alertmanager 구성
- 카나리 배포 실패 알림
- 장애 실험 결과 알림
- 성능 테스트 임계값 초과 알림

**참고 문서**:
- `docs/monitoring/alerting.md`
- `infrastructure/k8s/monitoring/alertmanager.yaml`

### 학습 리소스

#### 공식 문서
- **Playwright**: https://playwright.dev/
- **Istio**: https://istio.io/latest/docs/
- **Flagger**: https://docs.flagger.app/
- **Litmus Chaos**: https://docs.litmuschaos.io/
- **k6**: https://k6.io/docs/
- **Newman**: https://learning.postman.com/docs/collections/using-newman-cli/

#### 튜토리얼
- Playwright E2E Testing: https://playwright.dev/docs/intro
- Istio Traffic Management: https://istio.io/latest/docs/tasks/traffic-management/
- Chaos Engineering Principles: https://principlesofchaos.org/
- k6 Load Testing: https://k6.io/docs/get-started/

#### 커뮤니티
- Playwright Discord: https://discord.com/invite/playwright
- Istio Slack: https://slack.istio.io/
- CNCF Slack (#litmus, #flagger): https://slack.cncf.io/
- k6 Community Forum: https://community.k6.io/

---

**문의**:
- DevOps 팀: devops@shopfds.com
- QA 팀: qa@shopfds.com
- SRE 팀: sre@shopfds.com
- 문서 이슈: https://github.com/shopfds/shopfds/issues

**마지막 업데이트**: 2025-11-20
**문서 버전**: 1.0.0
