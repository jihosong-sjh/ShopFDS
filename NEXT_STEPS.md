# ShopFDS - 다음 작업 계획

**마지막 업데이트**: 2025-11-19

## 현재 상태 요약

### 구현 완료된 것
- [OK] Docker Compose 전체 인프라 구성 (PostgreSQL, Redis Cluster, RabbitMQ, ELK, Prometheus, Grafana)
- [OK] 데이터베이스 마이그레이션 (Alembic 4개 파일)
- [OK] 4개 백엔드 서비스 (Ecommerce, FDS, ML, Admin)
- [OK] 2개 프론트엔드 (Ecommerce, Admin) - React Router 구조 완성
- [OK] FDS 엔진 (룰, ML, CTI 통합)
- [OK] Celery 비동기 작업 처리

### 웹 브라우저 테스트 가능 여부
**답변: 지금 당장 가능! (단, 시드 데이터 필요)**

---

## 즉시 실행 가이드

### 최소 스택 실행 (테스트용)

```bash
# 1. 프로젝트 디렉토리로 이동
cd D:\side-project\ShopFDS

# 2. Docker 인프라 디렉토리로 이동
cd infrastructure\docker

# 3. 핵심 서비스만 실행 (PostgreSQL + Redis + 백엔드 + 프론트엔드)
docker-compose up -d postgres redis-node-1 redis-node-2 redis-node-3 redis-node-4 redis-node-5 redis-node-6 redis-cluster-init ecommerce-backend fds-service ecommerce-frontend

# 4. 로그 확인 (서비스 시작 확인)
docker-compose logs -f ecommerce-backend

# 5. 서비스 상태 확인
docker-compose ps
```

### 전체 스택 실행 (모니터링 포함)

```bash
cd D:\side-project\ShopFDS\infrastructure\docker
docker-compose up -d
```

### 서비스 중지

```bash
cd D:\side-project\ShopFDS\infrastructure\docker

# 모든 서비스 중지 (데이터는 유지)
docker-compose stop

# 모든 서비스 중지 및 컨테이너 삭제 (데이터는 유지)
docker-compose down

# 모든 서비스 중지 및 데이터 삭제 (완전 초기화)
docker-compose down -v
```

---

## 접속 URL (서비스 실행 후)

| 서비스 | URL | 로그인 정보 |
|--------|-----|-------------|
| **이커머스 프론트엔드** | http://localhost:3000 | 회원가입 필요 |
| **관리자 대시보드** | http://localhost:3001 | 회원가입 필요 |
| Ecommerce API 문서 | http://localhost:8000/docs | - |
| FDS API 문서 | http://localhost:8001/docs | - |
| ML Service API 문서 | http://localhost:8002/docs | - |
| Admin API 문서 | http://localhost:8003/docs | - |
| Grafana (모니터링) | http://localhost:3002 | admin / admin |
| Kibana (로그) | http://localhost:5601 | - |
| RabbitMQ 관리 | http://localhost:15672 | admin / admin |
| Flower (Celery) | http://localhost:5555 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| MLflow | http://localhost:5000 | - |

---

## 다음 작업: 시드 데이터 생성 (30분)

### 현재 문제
- 데이터베이스는 실행 중이지만 **상품 데이터가 없음**
- 회원가입은 되지만 **테스트용 계정이 없음**

### 해결 방법: 시드 데이터 스크립트 작성

```bash
# 1. 시드 데이터 스크립트 실행 (Claude에게 작성 요청)
cd services/ecommerce/backend
python scripts/seed_data.py

# 2. 생성될 데이터:
#    - 테스트 상품 20개 (전자제품, 의류, 식품 등)
#    - 테스트 사용자 3명 (일반, VIP, 의심계정)
#    - 카테고리 5개
#    - 초기 재고 설정
```

### 시드 데이터 생성 후 테스트 가능한 플로우

```
1. http://localhost:3000 접속
2. 회원가입 (이메일: test@example.com, 비밀번호: test1234)
3. 로그인
4. 상품 목록 확인 (20개 상품)
5. 상품 상세 페이지 → 장바구니 추가
6. 장바구니 확인
7. 체크아웃 (배송 정보 입력)
8. 결제 정보 입력 (Mock 결제, 카드번호: 4532-1234-5678-9010)
9. FDS 평가 결과 확인 (위험도 점수, 승인/거부/추가인증)
10. 주문 완료
11. 주문 내역 확인
```

---

## 고도화 계획 (우선순위 순)

### Phase 1: 시드 데이터 및 기본 테스트 (1일)
- [ ] 시드 데이터 스크립트 작성
- [ ] 웹 브라우저에서 전체 쇼핑 플로우 테스트
- [ ] FDS 평가 결과 확인
- [ ] 버그 수정

### Phase 2: 결제 게이트웨이 통합 (1주)
- [ ] Stripe Test Mode 연동
- [ ] 실제 카드 결제 테스트 (테스트 카드)
- [ ] 결제 실패 시나리오 처리
- [ ] 3D Secure 인증 플로우

### Phase 3: 프론트엔드 폴리싱 (1주)
- [ ] 로딩 스피너 추가
- [ ] 에러 처리 개선
- [ ] 상품 이미지 업로드 기능
- [ ] 상품 검색 및 필터링 개선
- [ ] 반응형 디자인 개선

### Phase 4: ML/FDS 고도화 (2주)
- [ ] Feature Engineering 파이프라인 개선
- [ ] 실전 탐지 룰 30개 추가
- [ ] 앙상블 모델 구축 (Random Forest + XGBoost + Neural Network)
- [ ] 설명 가능한 AI (SHAP/LIME)

### Phase 5: 소셜 로그인 및 고급 기능 (2주)
- [ ] Google OAuth 2.0 연동
- [ ] Facebook 로그인
- [ ] 위시리스트 기능
- [ ] 상품 리뷰 및 평점
- [ ] 추천 시스템

### Phase 6: 통합 테스트 및 성능 최적화 (1주)
- [ ] E2E 테스트 자동화 (Playwright)
- [ ] 부하 테스트 (Locust)
- [ ] FDS 성능 100ms 달성 검증
- [ ] 캐시 히트율 80% 달성 검증

### Phase 7: 프로덕션 배포 준비 (1주)
- [ ] Kubernetes 매니페스트 검증
- [ ] CI/CD 파이프라인 구축 (GitHub Actions)
- [ ] 보안 감사 (OWASP, PCI-DSS)
- [ ] 문서화 완성

---

## 빠른 참조

### 데이터베이스 마이그레이션

```bash
cd services/ecommerce/backend

# 마이그레이션 적용
alembic upgrade head

# 마이그레이션 롤백
alembic downgrade -1

# 새 마이그레이션 생성
alembic revision --autogenerate -m "description"
```

### 로그 확인

```bash
cd infrastructure/docker

# 특정 서비스 로그
docker-compose logs -f ecommerce-backend
docker-compose logs -f fds-service
docker-compose logs -f ecommerce-frontend

# 모든 서비스 로그
docker-compose logs -f

# 최근 100줄만 보기
docker-compose logs --tail=100 ecommerce-backend
```

### 데이터베이스 접속

```bash
# PostgreSQL 컨테이너 접속
docker exec -it shopfds-postgres-master psql -U shopfds_user -d shopfds

# 테이블 목록 확인
\dt

# 사용자 목록 확인
SELECT * FROM users LIMIT 10;

# 상품 목록 확인
SELECT * FROM products LIMIT 10;

# 주문 목록 확인
SELECT * FROM orders LIMIT 10;
```

### Redis 접속

```bash
# Redis 컨테이너 접속
docker exec -it shopfds-redis-node-1 redis-cli

# 키 목록 확인
KEYS *

# 특정 키 값 확인
GET key_name

# 전체 키 삭제 (주의!)
FLUSHALL
```

---

## 문제 해결

### 문제 1: 포트 충돌 (포트가 이미 사용 중)

```bash
# Windows에서 포트 사용 프로세스 확인
netstat -ano | findstr :8000
netstat -ano | findstr :5432

# 프로세스 종료 (PID 확인 후)
taskkill /PID <PID> /F
```

### 문제 2: Docker 디스크 공간 부족

```bash
# 사용하지 않는 Docker 리소스 정리
docker system prune -a --volumes

# 특정 볼륨만 삭제
docker volume ls
docker volume rm <volume_name>
```

### 문제 3: 컨테이너가 계속 재시작

```bash
# 컨테이너 로그 확인
docker-compose logs <service_name>

# 컨테이너 상태 확인
docker-compose ps

# 헬스체크 상태 확인
docker inspect <container_name> | grep -A 20 Health
```

### 문제 4: 데이터베이스 연결 실패

```bash
# 1. PostgreSQL 컨테이너 헬스체크
docker-compose ps postgres

# 2. 데이터베이스 접속 테스트
docker exec -it shopfds-postgres-master pg_isready -U shopfds_user

# 3. 환경 변수 확인
docker-compose config | grep DATABASE_URL
```

---

## 유용한 명령어 모음

### Docker Compose

```bash
# 서비스 재시작
docker-compose restart ecommerce-backend

# 특정 서비스만 빌드
docker-compose build ecommerce-backend

# 특정 서비스만 재시작 (빌드 포함)
docker-compose up -d --build ecommerce-backend

# 컨테이너 내부 접속
docker-compose exec ecommerce-backend bash

# 리소스 사용량 확인
docker stats
```

### Git

```bash
# 현재 상태 확인
git status

# 변경사항 확인
git diff

# 커밋
git add .
git commit -m "feat: add seed data script"
git push
```

### Python 테스트

```bash
cd services/ecommerce/backend

# 유닛 테스트
pytest tests/unit -v

# 통합 테스트
pytest tests/integration -v

# 커버리지 확인
pytest tests/unit -v --cov=src --cov-report=html
```

---

## 참고 문서

- 프로젝트 가이드: `CLAUDE.md`
- 빠른 시작: `specs/001-ecommerce-fds-platform/quickstart.md`
- API 문서: `docs/api/README.md`
- 아키텍처: `docs/architecture/README.md`
- 성능 최적화: `docs/performance-optimization.md`
- 보안 강화: `docs/security-hardening.md`

---

## 연락처

- GitHub Issues: https://github.com/anthropics/claude-code/issues
- 프로젝트 저장소: (GitHub URL 추가 예정)

---

**다음에 작업 시작할 때:**

1. 이 파일(`NEXT_STEPS.md`)을 열어서 현재 상태 확인
2. "즉시 실행 가이드" 섹션으로 Docker 서비스 실행
3. "다음 작업" 섹션에서 시드 데이터 생성 진행
4. 문제 발생 시 "문제 해결" 섹션 참조

**예상 시간: 30분 (시드 데이터 생성 + 첫 테스트)**
