# 🚀 빠른 시작: 5분 안에 배포하기

**목표**: 최소한의 설정으로 ShopFDS를 로컬 Kubernetes에 배포하기

## 사전 요구사항

- Docker Desktop 설치 및 실행 중
- Git 설치
- 기본적인 명령줄 사용 지식

---

## Step 1: Kubernetes 활성화 (1분)

### Windows/Mac - Docker Desktop

1. Docker Desktop 실행
2. **Settings (⚙️)** → **Kubernetes**
3. ☑️ **Enable Kubernetes** 체크
4. **Apply & Restart** 클릭
5. 상태가 "Kubernetes is running" 될 때까지 대기 (약 1-2분)

### 확인

```bash
kubectl version --short
kubectl get nodes
```

---

## Step 2: Ingress Controller 설치 (1분)

```bash
# Nginx Ingress Controller 설치
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

# 설치 확인 (약 30초 소요)
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
```

---

## Step 3: ShopFDS 배포 (2분)

### 3.1 코드 복제

```bash
# 리포지토리 클론 (이미 있으면 생략)
cd D:/side-project
git clone https://github.com/YOUR_USERNAME/ShopFDS.git
cd ShopFDS
```

### 3.2 Secrets 설정

```bash
# secrets.yaml 파일 열기
notepad infrastructure/k8s/secrets.yaml

# 다음 항목만 변경 (나머지는 기본값 사용 가능):
# POSTGRES_PASSWORD: your_strong_password_123
# JWT_SECRET: your_jwt_secret_key_change_me_in_production
```

### 3.3 배포 실행

```bash
# 모든 리소스 배포
kubectl apply -k infrastructure/k8s/

# 배포 진행 상황 확인
kubectl get pods -n shopfds -w
# 모든 Pod가 Running 상태가 될 때까지 대기 (Ctrl+C로 중단)
```

---

## Step 4: 접속 설정 (1분)

### 4.1 hosts 파일 수정

**Windows** (관리자 권한으로 메모장 실행):
```bash
# 메모장을 관리자 권한으로 실행
notepad C:\Windows\System32\drivers\etc\hosts

# 맨 아래에 다음 줄 추가:
127.0.0.1 shopfds.example.com
127.0.0.1 admin.shopfds.example.com
127.0.0.1 api.shopfds.example.com
```

**Mac/Linux**:
```bash
sudo nano /etc/hosts

# 다음 줄 추가:
127.0.0.1 shopfds.example.com
127.0.0.1 admin.shopfds.example.com
127.0.0.1 api.shopfds.example.com
```

### 4.2 Ingress TLS 비활성화 (로컬 테스트용)

```bash
# ingress.yaml 편집
notepad infrastructure/k8s/ingress.yaml

# 다음 섹션을 주석 처리 (앞에 # 추가):
# spec:
#   tls:
#   - hosts:
#     - shopfds.example.com
#     ...

# 저장 후 다시 적용
kubectl apply -f infrastructure/k8s/ingress.yaml
```

---

## Step 5: 접속 확인 ✅

### 브라우저에서 접속

```
http://shopfds.example.com
http://admin.shopfds.example.com
http://api.shopfds.example.com/health
```

### API 테스트

```bash
# Health Check
curl http://api.shopfds.example.com/health

# 또는 kubectl을 통해
kubectl exec -n shopfds deployment/ecommerce-backend -- curl http://localhost:8000/health
```

---

## 문제 해결

### Pod가 시작되지 않음

```bash
# Pod 상태 확인
kubectl get pods -n shopfds

# 에러 확인
kubectl describe pod <pod-name> -n shopfds

# 로그 확인
kubectl logs <pod-name> -n shopfds
```

### 일반적인 문제

**1. ImagePullBackOff**
```bash
# 이미지를 로컬에서 빌드
cd services/ecommerce/backend
docker build -t shopfds/ecommerce-backend:latest .

# Deployment 수정 (imagePullPolicy: Never)
kubectl edit deployment ecommerce-backend -n shopfds
```

**2. CrashLoopBackOff**
```bash
# PostgreSQL이 준비될 때까지 대기
kubectl wait --for=condition=ready pod -l app=postgres -n shopfds --timeout=300s

# Pod 재시작
kubectl rollout restart deployment/ecommerce-backend -n shopfds
```

**3. 502 Bad Gateway**
```bash
# 백엔드 서비스 확인
kubectl get svc -n shopfds
kubectl get endpoints ecommerce-backend-service -n shopfds

# Port-forward로 직접 접속
kubectl port-forward -n shopfds svc/ecommerce-backend-service 8000:8000
# http://localhost:8000/health
```

---

## 다음 단계

### GitHub Actions CI/CD 설정

완전한 가이드: [setup-cicd-kubernetes.md](./setup-cicd-kubernetes.md)

**간단 요약**:

1. **GitHub Repository 생성**
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/ShopFDS.git
   git push -u origin main
   ```

2. **GitHub Secrets 추가**
   - Repository → Settings → Secrets and variables → Actions
   - `KUBECONFIG_STAGING` 추가:
     ```bash
     kubectl config view --minify --flatten | base64 -w 0
     ```

3. **코드 푸시**
   ```bash
   git push origin main
   ```
   → GitHub Actions가 자동으로 테스트, 빌드, 배포 실행!

---

## 정리 (삭제)

```bash
# ShopFDS 네임스페이스 전체 삭제
kubectl delete namespace shopfds

# Ingress Controller 삭제
kubectl delete namespace ingress-nginx

# Kubernetes 비활성화 (Docker Desktop)
# Settings → Kubernetes → Uncheck "Enable Kubernetes"
```

---

## 요약

```bash
# 1. Kubernetes 활성화
kubectl version

# 2. Ingress 설치
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

# 3. ShopFDS 배포
kubectl apply -k infrastructure/k8s/

# 4. hosts 파일 수정
# 127.0.0.1 shopfds.example.com

# 5. 접속 확인
curl http://api.shopfds.example.com/health
```

**🎉 완료! 이제 ShopFDS가 로컬 Kubernetes에서 실행 중입니다!**

---

## 추가 명령어

### 상태 모니터링

```bash
# 모든 리소스 확인
kubectl get all -n shopfds

# 로그 실시간 확인
kubectl logs -n shopfds -l app=ecommerce-backend -f

# 특정 Pod 로그
kubectl logs -n shopfds <pod-name> -f

# Pod 내부 접속
kubectl exec -it -n shopfds <pod-name> -- /bin/sh
```

### 서비스 스케일링

```bash
# Replica 수 조정
kubectl scale deployment ecommerce-backend -n shopfds --replicas=5

# HPA 상태 확인
kubectl get hpa -n shopfds
```

### 업데이트

```bash
# 이미지 업데이트
kubectl set image deployment/ecommerce-backend -n shopfds \
  ecommerce-backend=shopfds/ecommerce-backend:v2

# 롤아웃 상태 확인
kubectl rollout status deployment/ecommerce-backend -n shopfds

# 롤백
kubectl rollout undo deployment/ecommerce-backend -n shopfds
```

---

## 참고 자료

- 📖 [상세 배포 가이드](./setup-cicd-kubernetes.md)
- 📖 [Kubernetes 매니페스트](../infrastructure/k8s/README.md)
- 📖 [CI/CD 워크플로우](.github/workflows/README.md)
- 📖 [프로젝트 개요](../README.md)
