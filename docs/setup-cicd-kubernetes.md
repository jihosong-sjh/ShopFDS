# GitHub Actions CI/CD 및 Kubernetes 배포 설정 가이드

## 목차

1. [GitHub Actions CI 설정](#1-github-actions-ci-설정)
2. [Kubernetes 클러스터 준비](#2-kubernetes-클러스터-준비)
3. [GitHub과 Kubernetes 연동](#3-github과-kubernetes-연동)
4. [첫 배포 실행](#4-첫-배포-실행)
5. [트러블슈팅](#5-트러블슈팅)

---

## 1. GitHub Actions CI 설정

### 1.1 GitHub Repository 설정

#### Step 1: Repository를 GitHub에 푸시

```bash
# 현재 디렉토리에서
git init  # 이미 초기화되어 있으면 생략
git add .
git commit -m "feat: Add CI/CD and Kubernetes infrastructure"

# GitHub에 리포지토리 생성 후
git remote add origin https://github.com/YOUR_USERNAME/ShopFDS.git
git branch -M main
git push -u origin main
```

#### Step 2: GitHub Repository Settings 확인

1. GitHub 웹사이트에서 리포지토리로 이동
2. **Settings** 탭 클릭
3. 왼쪽 메뉴에서 **Actions** > **General** 선택
4. "Workflow permissions" 확인:
   - ✅ "Read and write permissions" 선택
   - ✅ "Allow GitHub Actions to create and approve pull requests" 체크

### 1.2 GitHub Container Registry 설정

#### Step 1: Personal Access Token (PAT) 생성 (선택사항)

> **참고**: `GITHUB_TOKEN`은 자동으로 제공되지만, 외부에서 이미지를 Pull하려면 PAT이 필요할 수 있습니다.

1. GitHub 프로필 → **Settings** → **Developer settings**
2. **Personal access tokens** → **Tokens (classic)**
3. **Generate new token (classic)** 클릭
4. 권한 선택:
   - ✅ `write:packages`
   - ✅ `read:packages`
   - ✅ `delete:packages`
   - ✅ `repo` (private repository인 경우)
5. **Generate token** 클릭
6. 생성된 토큰 복사 (다시 볼 수 없음!)

#### Step 2: Package Visibility 설정

1. 첫 이미지가 푸시되면 GitHub Packages에 표시됨
2. **Packages** 탭에서 이미지 선택
3. **Package settings** → **Change visibility** → **Public** (또는 Private)

### 1.3 GitHub Secrets 설정

#### Step 1: Repository Secrets 추가

1. Repository → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭
3. 다음 Secrets 추가:

```
# 필수 Secrets

1. KUBECONFIG_STAGING
   - Staging Kubernetes 클러스터 설정
   - 값: base64로 인코딩된 kubeconfig 파일

2. KUBECONFIG_PRODUCTION
   - Production Kubernetes 클러스터 설정
   - 값: base64로 인코딩된 kubeconfig 파일

# 선택사항 Secrets

3. SLACK_WEBHOOK
   - Slack 알림용
   - 값: https://hooks.slack.com/services/YOUR/WEBHOOK/URL

4. CODECOV_TOKEN
   - 코드 커버리지 리포팅
   - 값: Codecov 토큰 (https://codecov.io)
```

### 1.4 Environments 설정

#### Step 1: Environment 생성

1. Repository → **Settings** → **Environments**
2. **New environment** 클릭

**Staging Environment**:
- Name: `staging`
- Protection rules: (선택사항)
  - ✅ Required reviewers (리뷰어 추가)
  - ✅ Wait timer (대기 시간)

**Production Environment**:
- Name: `production`
- Protection rules: (권장)
  - ✅ **Required reviewers** (1-6명 추가) ⭐ 중요!
  - ✅ Wait timer: 5분 (선택사항)
  - ✅ Deployment branches: `main` only

### 1.5 GitHub Actions 워크플로우 활성화 확인

```bash
# 워크플로우 파일 확인
ls -la .github/workflows/

# 다음 파일들이 있어야 함:
# - ci-backend.yml
# - ci-frontend.yml
# - build-and-push.yml
# - deploy.yml
```

첫 푸시 후 GitHub Actions 탭에서 워크플로우가 실행되는지 확인하세요.

---

## 2. Kubernetes 클러스터 준비

### 옵션 A: 로컬 Kubernetes (개발/테스트용)

#### Option 1: Minikube (가장 쉬움)

```bash
# 1. Minikube 설치 (Windows)
choco install minikube

# 2. 클러스터 시작
minikube start --cpus=4 --memory=8192 --driver=docker

# 3. Nginx Ingress Controller 설치
minikube addons enable ingress

# 4. kubeconfig 확인
kubectl cluster-info

# 5. 상태 확인
kubectl get nodes
```

#### Option 2: Docker Desktop Kubernetes

```bash
# 1. Docker Desktop 설정 열기
# 2. Settings → Kubernetes → Enable Kubernetes 체크
# 3. Apply & Restart

# 4. 확인
kubectl cluster-info
kubectl get nodes
```

#### Option 3: Kind (Kubernetes in Docker)

```bash
# 1. Kind 설치
choco install kind

# 2. 클러스터 생성
kind create cluster --name shopfds

# 3. Nginx Ingress 설치
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# 4. 확인
kubectl cluster-info --context kind-shopfds
```

### 옵션 B: 클라우드 Kubernetes (프로덕션용)

#### AWS EKS

```bash
# 1. AWS CLI 설치 및 설정
aws configure

# 2. eksctl 설치
choco install eksctl

# 3. 클러스터 생성 (약 15분 소요)
eksctl create cluster \
  --name shopfds-production \
  --region ap-northeast-2 \
  --nodegroup-name standard-workers \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 5 \
  --managed

# 4. kubeconfig 설정
aws eks update-kubeconfig --name shopfds-production --region ap-northeast-2

# 5. Nginx Ingress Controller 설치
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/aws/deploy.yaml
```

#### Google GKE

```bash
# 1. gcloud CLI 설치 및 설정
gcloud init

# 2. 클러스터 생성
gcloud container clusters create shopfds-production \
  --num-nodes=3 \
  --machine-type=n1-standard-2 \
  --region=asia-northeast3

# 3. kubeconfig 설정
gcloud container clusters get-credentials shopfds-production --region=asia-northeast3

# 4. Nginx Ingress Controller 설치
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
```

#### Azure AKS

```bash
# 1. Azure CLI 설치 및 로그인
az login

# 2. 리소스 그룹 생성
az group create --name shopfds-rg --location koreacentral

# 3. 클러스터 생성
az aks create \
  --resource-group shopfds-rg \
  --name shopfds-production \
  --node-count 3 \
  --node-vm-size Standard_D2s_v3 \
  --enable-addons monitoring \
  --generate-ssh-keys

# 4. kubeconfig 설정
az aks get-credentials --resource-group shopfds-rg --name shopfds-production

# 5. Nginx Ingress Controller 설치
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
```

### 2.2 Kubernetes 클러스터 검증

```bash
# 1. 노드 확인
kubectl get nodes

# 출력 예시:
# NAME                      STATUS   ROLES    AGE   VERSION
# node1                     Ready    <none>   5m    v1.28.0
# node2                     Ready    <none>   5m    v1.28.0
# node3                     Ready    <none>   5m    v1.28.0

# 2. Ingress Controller 확인
kubectl get pods -n ingress-nginx

# 3. 네임스페이스 생성 (아직 안했다면)
kubectl create namespace shopfds

# 4. 현재 컨텍스트 확인
kubectl config current-context
```

---

## 3. GitHub과 Kubernetes 연동

### 3.1 kubeconfig 파일 준비

#### Step 1: kubeconfig 파일 위치 확인

```bash
# Windows
echo %USERPROFILE%\.kube\config

# Linux/Mac
echo ~/.kube/config

# 파일 내용 확인
cat ~/.kube/config
```

#### Step 2: 별도 kubeconfig 생성 (권장)

**보안상 이유로 전체 kubeconfig를 GitHub에 올리지 말고, 특정 클러스터용만 추출하세요.**

```bash
# 1. 현재 컨텍스트 확인
kubectl config current-context

# 2. Staging용 kubeconfig 추출
kubectl config view --minify --flatten --context=minikube > kubeconfig-staging.yaml

# 3. Production용 kubeconfig 추출
kubectl config view --minify --flatten --context=shopfds-production > kubeconfig-production.yaml

# 4. 파일 확인
cat kubeconfig-staging.yaml
```

#### Step 3: ServiceAccount 생성 (더 안전한 방법 - 권장)

**GitHub Actions 전용 ServiceAccount를 만들어 제한된 권한만 부여**

```bash
# 1. ServiceAccount 생성
kubectl create serviceaccount github-actions -n shopfds

# 2. ClusterRole 생성 (deploy-role.yaml)
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: github-actions-deployer
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "patch", "update"]
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get"]
EOF

# 3. ClusterRoleBinding 생성
kubectl create clusterrolebinding github-actions-deployer-binding \
  --clusterrole=github-actions-deployer \
  --serviceaccount=shopfds:github-actions

# 4. Token 생성 (Kubernetes 1.24+)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: github-actions-token
  namespace: shopfds
  annotations:
    kubernetes.io/service-account.name: github-actions
type: kubernetes.io/service-account-token
EOF

# 5. Token 추출
TOKEN=$(kubectl get secret github-actions-token -n shopfds -o jsonpath='{.data.token}' | base64 --decode)

# 6. CA 인증서 추출
CA_CERT=$(kubectl get secret github-actions-token -n shopfds -o jsonpath='{.data.ca\.crt}')

# 7. Server URL 확인
SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')

# 8. kubeconfig 생성
cat <<EOF > kubeconfig-github-actions.yaml
apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: ${CA_CERT}
    server: ${SERVER}
  name: github-actions-cluster
contexts:
- context:
    cluster: github-actions-cluster
    namespace: shopfds
    user: github-actions-user
  name: github-actions-context
current-context: github-actions-context
users:
- name: github-actions-user
  user:
    token: ${TOKEN}
EOF

# 9. 확인
kubectl --kubeconfig=kubeconfig-github-actions.yaml get pods -n shopfds
```

### 3.2 kubeconfig Base64 인코딩

```bash
# Windows (PowerShell)
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Content kubeconfig-staging.yaml -Raw)))

# Linux/Mac
cat kubeconfig-staging.yaml | base64 -w 0

# 또는 간단하게 (Linux/Mac)
base64 < kubeconfig-staging.yaml > kubeconfig-staging-base64.txt

# 출력된 base64 문자열 전체를 복사
```

### 3.3 GitHub Secrets에 kubeconfig 추가

#### Step 1: Staging kubeconfig 추가

1. GitHub Repository → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭
3. Secret 추가:
   - **Name**: `KUBECONFIG_STAGING`
   - **Value**: (위에서 생성한 base64 문자열 전체 붙여넣기)
4. **Add secret** 클릭

#### Step 2: Production kubeconfig 추가

1. 동일한 방법으로 **KUBECONFIG_PRODUCTION** 추가
2. **Value**: Production 클러스터의 base64 kubeconfig

### 3.4 Slack 알림 설정 (선택사항)

#### Step 1: Slack Webhook URL 생성

1. Slack 워크스페이스 → **Apps** → **Incoming Webhooks** 검색
2. **Add to Slack** 클릭
3. 채널 선택 (예: `#deployments`)
4. **Add Incoming WebHooks integration** 클릭
5. **Webhook URL** 복사 (예: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX`)

#### Step 2: GitHub Secret 추가

1. Repository → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭
3. Secret 추가:
   - **Name**: `SLACK_WEBHOOK`
   - **Value**: (복사한 Webhook URL)

### 3.5 Codecov 설정 (선택사항)

#### Step 1: Codecov 계정 연동

1. https://codecov.io 방문
2. GitHub 계정으로 로그인
3. Repository 선택 (ShopFDS)
4. **Upload Token** 복사

#### Step 2: GitHub Secret 추가

1. Repository → **Settings** → **Secrets and variables** → **Actions**
2. Secret 추가:
   - **Name**: `CODECOV_TOKEN`
   - **Value**: (복사한 Upload Token)

---

## 4. 첫 배포 실행

### 4.1 수동으로 Kubernetes 리소스 생성

**GitHub Actions가 실행되기 전에 기본 인프라를 먼저 배포해야 합니다.**

```bash
# 1. 현재 디렉토리 확인
cd D:/side-project/ShopFDS

# 2. Namespace 생성 (이미 있으면 생략)
kubectl apply -f infrastructure/k8s/namespace.yaml

# 3. ConfigMap 및 Secrets 수정
# ⚠️ 중요: secrets.yaml의 비밀번호를 실제 값으로 변경!
notepad infrastructure/k8s/secrets.yaml

# 변경할 항목:
# - POSTGRES_PASSWORD
# - REDIS_PASSWORD
# - JWT_SECRET
# - ENCRYPTION_KEY
# - ABUSEIPDB_API_KEY
# - SENTRY_DSN

# 4. ConfigMap과 Secrets 적용
kubectl apply -f infrastructure/k8s/configmap.yaml
kubectl apply -f infrastructure/k8s/secrets.yaml

# 5. Persistent Volumes 생성
kubectl apply -f infrastructure/k8s/persistent-volumes.yaml

# 6. PostgreSQL 및 Redis 배포
kubectl apply -f infrastructure/k8s/postgres.yaml
kubectl apply -f infrastructure/k8s/redis.yaml

# 7. 데이터베이스 준비 대기 (약 1-2분)
kubectl get pods -n shopfds -w
# Ctrl+C로 중단

# 8. 데이터베이스 확인
kubectl exec -it -n shopfds $(kubectl get pod -n shopfds -l app=postgres -o jsonpath='{.items[0].metadata.name}') -- psql -U shopfds_user -d shopfds -c "SELECT version();"
```

### 4.2 Docker 이미지 수동 빌드 (선택사항)

**GitHub Actions가 자동으로 빌드하지만, 로컬 테스트를 위해 수동 빌드 가능**

```bash
# 1. Docker 로그인
docker login ghcr.io -u YOUR_GITHUB_USERNAME

# 2. 이미지 빌드 (예: Ecommerce Backend)
cd services/ecommerce/backend
docker build -t ghcr.io/YOUR_USERNAME/shopfds-ecommerce-backend:latest .

# 3. 이미지 푸시
docker push ghcr.io/YOUR_USERNAME/shopfds-ecommerce-backend:latest

# 4. 모든 서비스 반복...
```

### 4.3 GitHub Actions 워크플로우

#### 워크플로우 트리거 구조

**중요: PR과 Main merge 시 실행되는 워크플로우가 다릅니다!**

| 시점 | 실행되는 워크플로우 | 목적 |
|------|---------------------|------|
| **PR 생성/업데이트** | CI - Backend<br>CI - Frontend | 코드 품질 검증<br>(테스트, 린트, 빌드) |
| **Main 브랜치 merge** | CI - Backend<br>CI - Frontend<br>**Build and Push**<br>**Deploy to K8s** | 검증 + 배포<br>(이미지 빌드, 배포) |

#### Step 1: Feature 브랜치에서 개발 (일반 워크플로우)

```bash
# 1. Feature 브랜치 생성
git checkout -b feature/my-new-feature

# 2. 개발 및 커밋
git add .
git commit -m "feat: Add new feature"

# 3. Feature 브랜치에 푸시
git push origin feature/my-new-feature
```

#### Step 2: Pull Request 생성

```bash
# GitHub에서 Pull Request 생성
# Base: main ← Compare: feature/my-new-feature
```

**이 시점에 실행되는 워크플로우:**
- ✅ **CI - Backend Services** (테스트, 린트)
- ✅ **CI - Frontend Services** (테스트, 린트, 빌드 검증)
- ❌ **Build and Push** (실행 안 됨)
- ❌ **Deploy** (실행 안 됨)

#### Step 3: 코드 리뷰 및 PR Merge

1. GitHub Repository → **Pull requests** 탭
2. 생성한 PR 확인
3. CI 통과 확인 (녹색 체크)
4. 리뷰어 승인 받기
5. **Merge pull request** 클릭

#### Step 4: Main Merge 후 자동 배포

**PR이 main에 merge되면 자동으로 실행:**

1. GitHub Repository → **Actions** 탭
2. 실행 중인 워크플로우 확인:
   - ✅ **CI - Backend Services**
   - ✅ **CI - Frontend Services**
   - ✅ **Build and Push Docker Images** ← main merge 후 실행!
   - ✅ **Deploy to Kubernetes** ← Build 완료 후 실행!

#### Step 5: 배포 진행 상황 모니터링

```bash
# 터미널에서 실시간 모니터링
kubectl get pods -n shopfds -w

# 배포 상태 확인
kubectl rollout status deployment/ecommerce-backend -n shopfds
kubectl rollout status deployment/fds-service -n shopfds

# 로그 확인
kubectl logs -n shopfds -l app=ecommerce-backend --tail=100 -f
```

#### (선택) 직접 Main에 푸시 (비권장)

**긴급 핫픽스가 아니면 PR 워크플로우를 사용하세요!**

```bash
# 1. main 브랜치로 전환
git checkout main
git pull origin main

# 2. 변경사항 커밋
git add .
git commit -m "feat: Setup CI/CD and Kubernetes deployment"

# 3. main 브랜치에 직접 푸시
git push origin main

# 이 경우 CI + Build + Deploy가 모두 실행됨
```

### 4.4 Ingress 설정 (로컬 테스트)

#### Minikube의 경우

```bash
# 1. Minikube IP 확인
minikube ip
# 예: 192.168.49.2

# 2. hosts 파일 수정 (관리자 권한 필요)
# Windows: C:\Windows\System32\drivers\etc\hosts
# Linux/Mac: /etc/hosts

# 다음 줄 추가:
192.168.49.2 shopfds.example.com
192.168.49.2 admin.shopfds.example.com
192.168.49.2 api.shopfds.example.com

# 3. Ingress 적용 (SSL 인증서 없이)
# ingress.yaml에서 TLS 섹션 주석 처리
kubectl apply -f infrastructure/k8s/ingress.yaml

# 4. 브라우저에서 접속
http://shopfds.example.com
http://api.shopfds.example.com/v1/products
```

#### 클라우드의 경우

```bash
# 1. Ingress External IP 확인
kubectl get ingress -n shopfds

# 출력 예시:
# NAME              CLASS   HOSTS                    ADDRESS         PORTS     AGE
# shopfds-ingress   nginx   shopfds.example.com,...  34.123.45.67   80, 443   5m

# 2. DNS 설정
# 도메인 레지스트라에서 A 레코드 추가:
# shopfds.example.com → 34.123.45.67
# admin.shopfds.example.com → 34.123.45.67
# api.shopfds.example.com → 34.123.45.67

# 3. SSL 인증서 설정 (Let's Encrypt)
# cert-manager 설치
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# ClusterIssuer 생성
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# 4. Ingress 적용 (TLS 자동 발급)
kubectl apply -f infrastructure/k8s/ingress.yaml

# 5. 인증서 발급 확인 (약 1-2분)
kubectl get certificate -n shopfds
```

### 4.5 배포 확인

```bash
# 1. 모든 Pod 실행 확인
kubectl get pods -n shopfds

# 모든 Pod가 Running 상태여야 함

# 2. Services 확인
kubectl get svc -n shopfds

# 3. Ingress 확인
kubectl get ingress -n shopfds

# 4. Health Check
curl http://api.shopfds.example.com/v1/products
# 또는
kubectl exec -n shopfds deployment/ecommerce-backend -- curl http://localhost:8000/health

# 5. 로그 확인
kubectl logs -n shopfds -l app=ecommerce-backend --tail=50
kubectl logs -n shopfds -l app=fds-service --tail=50
```

---

## 5. 트러블슈팅

### 5.1 GitHub Actions 실패

#### 문제: CI 테스트 실패

```bash
# 로컬에서 테스트 실행
cd services/ecommerce/backend
pytest tests/ -v

# 테스트 통과 확인 후 다시 푸시
```

#### 문제: Docker 이미지 빌드 실패

```bash
# 로컬에서 빌드 테스트
cd services/ecommerce/backend
docker build -t test .

# 에러 확인 및 수정
```

#### 문제: KUBECONFIG_STAGING Secret 인식 안 됨

1. Secret 이름 정확히 확인 (`KUBECONFIG_STAGING`)
2. base64 인코딩 확인
3. GitHub Actions 로그에서 에러 메시지 확인

### 5.2 Kubernetes 배포 실패

#### 문제: ImagePullBackOff

```bash
# Pod 상태 확인
kubectl describe pod <pod-name> -n shopfds

# 원인:
# 1. 이미지가 GitHub Container Registry에 없음
# 2. 이미지 이름 오타
# 3. Private 이미지인데 ImagePullSecret 없음

# 해결: ImagePullSecret 생성
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_TOKEN \
  -n shopfds

# Deployment에 imagePullSecrets 추가
kubectl edit deployment ecommerce-backend -n shopfds

# spec.template.spec에 추가:
# imagePullSecrets:
# - name: ghcr-secret
```

#### 문제: CrashLoopBackOff

```bash
# 로그 확인
kubectl logs <pod-name> -n shopfds
kubectl logs <pod-name> -n shopfds --previous

# 일반적인 원인:
# 1. 환경변수 누락 (DB 연결 정보 등)
# 2. 데이터베이스 연결 실패
# 3. 포트 충돌
# 4. 의존성 누락

# ConfigMap/Secrets 확인
kubectl get configmap shopfds-config -n shopfds -o yaml
kubectl get secret shopfds-secrets -n shopfds -o yaml
```

#### 문제: Pending 상태

```bash
# 이벤트 확인
kubectl describe pod <pod-name> -n shopfds

# 일반적인 원인:
# 1. 리소스 부족 (CPU/Memory)
# 2. PersistentVolume 생성 실패
# 3. NodeSelector/Affinity 미스매치

# 노드 리소스 확인
kubectl top nodes

# PVC 확인
kubectl get pvc -n shopfds
```

### 5.3 Ingress 접속 불가

#### 문제: 502 Bad Gateway

```bash
# 백엔드 서비스 확인
kubectl get svc -n shopfds
kubectl get endpoints -n shopfds

# 백엔드 Pod 확인
kubectl get pods -n shopfds -l app=ecommerce-backend

# 직접 연결 테스트
kubectl port-forward -n shopfds svc/ecommerce-backend-service 8000:8000
# 브라우저: http://localhost:8000/health
```

#### 문제: 도메인 접속 안 됨

```bash
# DNS 확인
nslookup shopfds.example.com

# Ingress Controller 확인
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx <ingress-controller-pod>

# Ingress 리소스 확인
kubectl describe ingress shopfds-ingress -n shopfds
```

### 5.4 데이터베이스 연결 실패

```bash
# PostgreSQL Pod 확인
kubectl get pods -n shopfds -l app=postgres

# PostgreSQL 로그 확인
kubectl logs -n shopfds <postgres-pod>

# 연결 테스트
kubectl exec -it -n shopfds <postgres-pod> -- psql -U shopfds_user -d shopfds

# 백엔드에서 연결 테스트
kubectl exec -it -n shopfds <backend-pod> -- nc -zv postgres-service 5432
```

---

## 6. 체크리스트

### GitHub Actions CI 설정 완료 ✅

- [ ] GitHub Repository 생성 및 코드 푸시
- [ ] Actions 권한 설정 (Read and write permissions)
- [ ] GitHub Container Registry 활성화
- [ ] GitHub Secrets 추가:
  - [ ] KUBECONFIG_STAGING
  - [ ] KUBECONFIG_PRODUCTION
  - [ ] SLACK_WEBHOOK (선택)
  - [ ] CODECOV_TOKEN (선택)
- [ ] Environments 생성 (staging, production)
- [ ] Production environment에 승인자 추가

### Kubernetes 클러스터 준비 완료 ✅

- [ ] Kubernetes 클러스터 생성 (Minikube/EKS/GKE/AKS)
- [ ] kubectl 설치 및 설정
- [ ] Nginx Ingress Controller 설치
- [ ] 클러스터 연결 확인 (`kubectl get nodes`)
- [ ] Namespace 생성 (`kubectl create namespace shopfds`)

### GitHub-Kubernetes 연동 완료 ✅

- [ ] kubeconfig 파일 추출
- [ ] ServiceAccount 생성 (선택, 권장)
- [ ] kubeconfig base64 인코딩
- [ ] GitHub Secrets에 kubeconfig 추가
- [ ] Slack Webhook 설정 (선택)
- [ ] Codecov 설정 (선택)

### 첫 배포 완료 ✅

- [ ] secrets.yaml 비밀번호 변경
- [ ] ConfigMap/Secrets 적용
- [ ] PostgreSQL/Redis 배포
- [ ] 데이터베이스 준비 확인
- [ ] GitHub Actions 워크플로우 실행
- [ ] 모든 Pod Running 상태 확인
- [ ] Ingress 설정 및 DNS/hosts 파일 수정
- [ ] 애플리케이션 접속 확인

---

## 7. 다음 단계

배포가 완료되면:

1. **모니터링 설정**
   - Prometheus + Grafana 설치
   - Sentry 연동
   - 로그 집계 (ELK Stack)

2. **보안 강화**
   - Network Policies 적용
   - Pod Security Standards
   - Secrets 관리 개선 (Sealed Secrets, Vault)

3. **백업 설정**
   - PostgreSQL 자동 백업
   - Velero 설치 (클러스터 백업)

4. **성능 최적화**
   - HPA 튜닝
   - 리소스 Requests/Limits 조정
   - 캐시 전략 최적화

---

## 참고 자료

- [GitHub Actions 공식 문서](https://docs.github.com/en/actions)
- [Kubernetes 공식 문서](https://kubernetes.io/docs/)
- [Nginx Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager](https://cert-manager.io/docs/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

---

**준비 완료!** 이제 GitHub에 코드를 푸시하면 자동으로 CI/CD가 실행되고 Kubernetes에 배포됩니다! 🚀
