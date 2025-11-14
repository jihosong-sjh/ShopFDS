# CI/CD 파이프라인

ShopFDS 플랫폼의 GitHub Actions 기반 CI/CD 파이프라인입니다.

## 워크플로우 구성

### 1. CI - Backend Services (`ci-backend.yml`)

**트리거**:
- Push to `main`, `develop` branches (백엔드 코드 변경 시)
- Pull Request to `main`, `develop` branches

**작업**:
1. **Ecommerce Backend 테스트**
   - Python 3.11 환경 설정
   - PostgreSQL, Redis 서비스 컨테이너 실행
   - 의존성 설치
   - 코드 품질 검사 (Black, Ruff)
   - 유닛 테스트 (pytest)
   - 통합 테스트
   - 커버리지 리포트 (Codecov)

2. **FDS Service 테스트**
   - 유닛 테스트
   - **성능 테스트** (100ms 목표)
   - 커버리지 리포트

3. **ML Service 테스트**
   - 유닛 테스트
   - 커버리지 리포트

4. **Admin Dashboard Backend 테스트**
   - 유닛 테스트
   - 커버리지 리포트

### 2. CI - Frontend Services (`ci-frontend.yml`)

**트리거**:
- Push to `main`, `develop` branches (프론트엔드 코드 변경 시)
- Pull Request to `main`, `develop` branches

**작업**:
1. **Ecommerce Frontend 테스트**
   - Node.js 18 환경 설정
   - 의존성 설치 (npm ci)
   - ESLint 검사
   - TypeScript 타입 체크
   - 유닛 테스트 (Jest)
   - 프로덕션 빌드
   - 커버리지 리포트

2. **Admin Dashboard Frontend 테스트**
   - 동일한 프로세스

### 3. Build and Push Docker Images (`build-and-push.yml`)

**트리거**:
- Push to `main` branch
- Git tags (v*.*.*)
- Manual trigger (workflow_dispatch)

**작업**:
1. **Backend Services 빌드**
   - Docker Buildx 설정
   - GitHub Container Registry 로그인
   - 각 서비스별 이미지 빌드 및 푸시
   - Multi-platform 지원 (linux/amd64, linux/arm64)
   - 캐시 최적화

2. **Frontend Services 빌드**
   - 동일한 프로세스
   - 빌드 시 환경변수 주입

3. **Nginx Gateway 빌드**
   - API Gateway 이미지 빌드 및 푸시

**이미지 태그**:
- `latest`: main 브랜치의 최신 커밋
- `v1.2.3`: Semantic versioning
- `main-abc1234`: 브랜치명-커밋SHA
- `pr-123`: Pull Request 번호

### 4. Deploy to Kubernetes (`deploy.yml`)

**트리거**:
- Build and Push 워크플로우 성공 후 자동 실행 (Staging)
- Manual trigger (Production 배포 시)

**작업**:
1. **Staging 배포**
   - kubectl 설정
   - Kubernetes 이미지 업데이트
   - Rollout 상태 확인
   - Smoke 테스트
   - Slack 알림

2. **Production 배포**
   - 배포 전 백업
   - Blue-Green 배포
   - Rollout 상태 확인
   - Smoke 테스트 + 성능 테스트
   - 실패 시 자동 롤백
   - Slack 알림

## 설정 방법

### 1. GitHub Secrets 설정

리포지토리 Settings > Secrets and variables > Actions에서 다음 Secrets 추가:

#### 필수 Secrets

```bash
# Kubernetes 설정
KUBECONFIG_STAGING        # Staging 클러스터 kubeconfig (base64 인코딩)
KUBECONFIG_PRODUCTION     # Production 클러스터 kubeconfig (base64 인코딩)

# Slack 알림 (선택사항)
SLACK_WEBHOOK             # Slack Webhook URL

# Codecov (선택사항)
CODECOV_TOKEN             # Codecov 업로드 토큰
```

#### Kubeconfig 인코딩 방법

```bash
# Staging
cat ~/.kube/config-staging | base64 -w 0 > kubeconfig-staging.txt

# Production
cat ~/.kube/config-production | base64 -w 0 > kubeconfig-production.txt
```

### 2. GitHub Container Registry 권한 설정

1. GitHub Settings > Developer settings > Personal access tokens
2. `write:packages` 권한 추가
3. 리포지토리에 Secret으로 등록 (또는 GITHUB_TOKEN 사용)

### 3. 환경 설정 (Environments)

리포지토리 Settings > Environments에서 환경 추가:

- **staging**: 자동 배포
- **production**: 승인 필요 (Protection rules)

## 사용 방법

### 자동 배포 (Staging)

```bash
# main 브랜치에 푸시
git push origin main

# 자동으로 다음 순서로 실행:
# 1. CI 테스트 (ci-backend.yml, ci-frontend.yml)
# 2. Docker 이미지 빌드 (build-and-push.yml)
# 3. Staging 배포 (deploy.yml)
```

### 수동 배포 (Production)

1. GitHub Actions 탭으로 이동
2. "Deploy to Kubernetes" 워크플로우 선택
3. "Run workflow" 클릭
4. Environment: `production` 선택
5. "Run workflow" 버튼 클릭

### 태그 릴리스

```bash
# Semantic versioning 태그 생성
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3

# 자동으로 v1.2.3 태그로 이미지 빌드
```

## 브랜치 전략

### GitFlow 기반

```
main          # 프로덕션 브랜치
  └── develop # 개발 브랜치
       └── feature/xxx  # 기능 브랜치
```

### 배포 흐름

1. **개발**: `feature/xxx` → `develop` (Pull Request)
2. **테스트**: `develop` 브랜치에서 CI 실행
3. **스테이징**: `develop` → `main` (Pull Request) → Staging 자동 배포
4. **프로덕션**: `main` 브랜치에서 수동 배포

## 테스트 커버리지

### 목표

- **Backend**: 80% 이상
- **Frontend**: 70% 이상

### 확인 방법

```bash
# 로컬에서 커버리지 확인
cd services/ecommerce/backend
pytest tests/ --cov=src --cov-report=html

# HTML 리포트 열기
open htmlcov/index.html
```

## 롤백

### GitHub Actions에서 롤백

1. GitHub Actions 탭
2. "Deploy to Kubernetes" 워크플로우
3. 이전 성공한 실행 선택
4. "Re-run all jobs" 클릭

### Kubectl로 직접 롤백

```bash
# 이전 버전으로 롤백
kubectl rollout undo deployment/ecommerce-backend -n shopfds

# 특정 revision으로 롤백
kubectl rollout undo deployment/ecommerce-backend -n shopfds --to-revision=2

# 롤백 히스토리 확인
kubectl rollout history deployment/ecommerce-backend -n shopfds
```

## 모니터링

### 배포 상태 확인

```bash
# 실시간 롤아웃 상태
kubectl rollout status deployment/ecommerce-backend -n shopfds

# Pod 상태
kubectl get pods -n shopfds -l app=ecommerce-backend

# 이벤트 확인
kubectl get events -n shopfds --sort-by='.lastTimestamp'
```

### 로그 확인

```bash
# 배포 중 로그
kubectl logs -n shopfds -l app=ecommerce-backend --tail=100 -f

# 이전 컨테이너 로그 (재시작된 경우)
kubectl logs -n shopfds <pod-name> --previous
```

## 성능 테스트

### FDS 100ms 목표

CI 파이프라인에서 자동으로 FDS 성능 테스트 실행:

```bash
# 로컬에서 실행
cd services/fds
pytest tests/performance -v --benchmark-only
```

### 부하 테스트 (선택사항)

```bash
# Apache Bench
ab -n 1000 -c 10 https://api.shopfds.example.com/v1/products

# K6 load testing
k6 run load-test.js
```

## 트러블슈팅

### 이미지 빌드 실패

```bash
# 로컬에서 빌드 테스트
cd services/ecommerce/backend
docker build -t test .

# 빌드 로그 확인
docker build --progress=plain -t test .
```

### 배포 실패

```bash
# Pod 상태 확인
kubectl describe pod <pod-name> -n shopfds

# 이미지 Pull 실패 확인
kubectl get events -n shopfds | grep "Failed to pull image"

# ImagePullBackOff 해결
kubectl delete pod <pod-name> -n shopfds
```

### 테스트 실패

```bash
# 로컬에서 테스트 실행
pytest tests/integration -v

# 특정 테스트만 실행
pytest tests/integration/test_order_service.py::test_create_order -v
```

## 보안

### Docker 이미지 스캔

```yaml
# .github/workflows/security-scan.yml (별도 추가 권장)
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'ghcr.io/shopfds/ecommerce-backend:latest'
    format: 'sarif'
    output: 'trivy-results.sarif'
```

### Secrets 관리

- GitHub Secrets 사용 (암호화 저장)
- Kubernetes Secrets는 Git에 커밋 금지
- Sealed Secrets 또는 External Secrets Operator 사용 권장

## 비용 최적화

### GitHub Actions 무료 플랜

- Public 리포지토리: 무제한
- Private 리포지토리: 월 2,000분

### 최적화 팁

1. **캐시 활용**: pip, npm 캐시 사용
2. **병렬 실행**: Matrix 전략 활용
3. **조건부 실행**: 경로 필터 사용
4. **Self-hosted Runners**: 대규모 프로젝트는 자체 러너 사용

## 참고 자료

- [GitHub Actions 공식 문서](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Kubectl Setup Action](https://github.com/azure/setup-kubectl)
- [Codecov Action](https://github.com/codecov/codecov-action)
