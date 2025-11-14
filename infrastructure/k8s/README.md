# Kubernetes 배포 가이드

ShopFDS 플랫폼의 Kubernetes 배포 매니페스트입니다.

## 사전 요구사항

- Kubernetes 클러스터 (v1.24+)
- kubectl CLI 도구
- Nginx Ingress Controller 설치
- cert-manager (TLS 인증서 자동 발급용, 선택사항)
- 이미지 레지스트리 (Docker Hub, ECR, GCR 등)

## 배포 순서

### 1. 네임스페이스 생성

```bash
kubectl apply -f namespace.yaml
```

### 2. ConfigMap 및 Secrets 설정

**중요**: `secrets.yaml` 파일의 비밀번호를 실제 프로덕션 값으로 변경하세요!

```bash
# Secrets 파일 편집
vi secrets.yaml

# ConfigMap 및 Secrets 적용
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
```

### 3. Persistent Volumes 생성

```bash
kubectl apply -f persistent-volumes.yaml
```

### 4. 데이터베이스 및 캐시 배포

```bash
kubectl apply -f postgres.yaml
kubectl apply -f redis.yaml

# 준비 상태 확인
kubectl get pods -n shopfds -l tier=database
kubectl get pods -n shopfds -l tier=cache
```

### 5. 백엔드 서비스 배포

```bash
kubectl apply -f ecommerce-backend.yaml
kubectl apply -f fds-service.yaml
kubectl apply -f ml-service.yaml
kubectl apply -f admin-dashboard-backend.yaml

# 서비스 상태 확인
kubectl get pods -n shopfds -l tier=backend
kubectl get svc -n shopfds
```

### 6. 프론트엔드 서비스 배포

```bash
kubectl apply -f ecommerce-frontend.yaml
kubectl apply -f admin-dashboard-frontend.yaml

# 프론트엔드 상태 확인
kubectl get pods -n shopfds -l tier=frontend
```

### 7. Ingress 설정

**중요**: `ingress.yaml` 파일에서 도메인 이름을 실제 도메인으로 변경하세요!

```bash
# Ingress 파일 편집
vi ingress.yaml

# Ingress 적용
kubectl apply -f ingress.yaml

# Ingress 상태 확인
kubectl get ingress -n shopfds
kubectl describe ingress shopfds-ingress -n shopfds
```

### 8. Kustomize로 한 번에 배포 (권장)

```bash
# 모든 리소스를 한 번에 배포
kubectl apply -k .

# 또는 특정 환경별로 배포
kubectl apply -k overlays/production
```

## 배포 확인

### 모든 리소스 상태 확인

```bash
# 모든 Pod 확인
kubectl get pods -n shopfds

# 모든 Service 확인
kubectl get svc -n shopfds

# Ingress 확인
kubectl get ingress -n shopfds

# HPA (Horizontal Pod Autoscaler) 확인
kubectl get hpa -n shopfds
```

### 로그 확인

```bash
# 특정 서비스 로그 확인
kubectl logs -n shopfds -l app=ecommerce-backend --tail=100 -f
kubectl logs -n shopfds -l app=fds-service --tail=100 -f

# 이전 컨테이너 로그 확인 (재시작된 경우)
kubectl logs -n shopfds <pod-name> --previous
```

### Health Check

```bash
# 서비스별 Health Check
kubectl exec -n shopfds -it <ecommerce-backend-pod> -- curl http://localhost:8000/health
kubectl exec -n shopfds -it <fds-service-pod> -- curl http://localhost:8001/health
```

## 데이터베이스 마이그레이션

```bash
# 마이그레이션 Job 실행
kubectl apply -f jobs/db-migration.yaml

# Job 상태 확인
kubectl get jobs -n shopfds
kubectl logs -n shopfds job/db-migration
```

## 스케일링

### 수동 스케일링

```bash
# Deployment 스케일링
kubectl scale deployment ecommerce-backend -n shopfds --replicas=5
kubectl scale deployment fds-service -n shopfds --replicas=10
```

### 자동 스케일링 (HPA)

HPA는 이미 다음 서비스에 적용되어 있습니다:
- `ecommerce-backend`: 3-10 replicas
- `fds-service`: 5-20 replicas

```bash
# HPA 상태 확인
kubectl get hpa -n shopfds

# HPA 상세 정보
kubectl describe hpa ecommerce-backend-hpa -n shopfds
```

## 업데이트 및 롤백

### 이미지 업데이트

```bash
# 새 이미지로 업데이트
kubectl set image deployment/ecommerce-backend -n shopfds \
  ecommerce-backend=shopfds/ecommerce-backend:v1.2.0

# 롤아웃 상태 확인
kubectl rollout status deployment/ecommerce-backend -n shopfds
```

### 롤백

```bash
# 이전 버전으로 롤백
kubectl rollout undo deployment/ecommerce-backend -n shopfds

# 특정 revision으로 롤백
kubectl rollout undo deployment/ecommerce-backend -n shopfds --to-revision=2

# 롤아웃 히스토리 확인
kubectl rollout history deployment/ecommerce-backend -n shopfds
```

## 모니터링

### Prometheus 및 Grafana 설치 (선택사항)

```bash
# Helm으로 Prometheus Stack 설치
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n shopfds

# Grafana 접속
kubectl port-forward -n shopfds svc/prometheus-grafana 3000:80
```

## 삭제

### 전체 삭제

```bash
# Kustomize로 삭제
kubectl delete -k .

# 또는 네임스페이스 전체 삭제
kubectl delete namespace shopfds
```

### 특정 리소스만 삭제

```bash
kubectl delete deployment ecommerce-backend -n shopfds
kubectl delete service ecommerce-backend-service -n shopfds
```

## 트러블슈팅

### Pod가 시작되지 않는 경우

```bash
# Pod 상태 확인
kubectl describe pod <pod-name> -n shopfds

# 이벤트 확인
kubectl get events -n shopfds --sort-by='.lastTimestamp'

# 로그 확인
kubectl logs <pod-name> -n shopfds
```

### 데이터베이스 연결 실패

```bash
# PostgreSQL 서비스 확인
kubectl get svc postgres-service -n shopfds

# PostgreSQL Pod 로그 확인
kubectl logs -n shopfds -l app=postgres

# 연결 테스트
kubectl exec -n shopfds -it <backend-pod> -- nc -zv postgres-service 5432
```

### Ingress 접속 불가

```bash
# Ingress Controller 확인
kubectl get pods -n ingress-nginx

# Ingress 설정 확인
kubectl describe ingress shopfds-ingress -n shopfds

# DNS 확인
nslookup shopfds.example.com
```

## 보안 권장사항

1. **Secrets 관리**: Git에 secrets.yaml 커밋 금지, Sealed Secrets 사용 권장
2. **RBAC**: 최소 권한 원칙 적용
3. **Network Policies**: Pod 간 통신 제한
4. **이미지 스캔**: 취약점 스캔 후 배포
5. **TLS/SSL**: cert-manager로 자동 인증서 발급

## 참고 자료

- [Kubernetes 공식 문서](https://kubernetes.io/docs/)
- [Nginx Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager](https://cert-manager.io/docs/)
- [Kustomize](https://kustomize.io/)
