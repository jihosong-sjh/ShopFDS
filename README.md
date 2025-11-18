# ShopFDS - AI/ML 기반 이커머스 사기 탐지 플랫폼

## [OVERVIEW] 프로젝트 개요

ShopFDS는 실시간 사기 거래 탐지 시스템(Fraud Detection System)을 통합한 차세대 전자상거래 플랫폼입니다. 머신러닝 기반의 지능형 위험 평가와 룰 기반 탐지를 결합하여 안전하고 신뢰할 수 있는 이커머스 환경을 제공합니다.

### 핵심 가치
- **실시간 사기 탐지**: 100ms 이내 트랜잭션 평가로 즉각적인 위험 감지
- **지능형 위험 평가**: ML 모델과 룰 엔진의 하이브리드 접근
- **확장 가능한 아키텍처**: 마이크로서비스 기반으로 유연한 확장성
- **엔터프라이즈 보안**: PCI-DSS 준수 및 OWASP Top 10 대응

## [FEATURES] 주요 기능

### 1. 이커머스 플랫폼
- **사용자 관리**: JWT 기반 인증/인가, 소셜 로그인 지원
- **상품 관리**: 카테고리별 상품 관리, 실시간 재고 추적
- **장바구니**: 세션 기반 장바구니, 게스트 체크아웃 지원
- **주문 처리**: 실시간 주문 상태 추적, 다단계 결제 검증

### 2. FDS (Fraud Detection System)
- **실시간 위험 평가**: 트랜잭션 당 100ms 이내 평가
- **하이브리드 탐지**: 룰 엔진 + ML 모델 + CTI 통합
- **적응형 학습**: 실시간 피드백 기반 모델 개선
- **위협 인텔리전스**: 외부 CTI 피드 통합

### 3. 머신러닝 서비스
- **모델 학습**: Isolation Forest, LightGBM 기반 이상 탐지
- **A/B 테스트**: 모델 성능 비교 및 점진적 배포
- **카나리 배포**: 안전한 모델 업데이트 및 롤백

### 4. 관리자 대시보드
- **실시간 모니터링**: 거래 현황 및 위험 지표 시각화
- **수동 검토**: 의심 거래 큐 관리 및 레이블링
- **룰 관리**: 동적 탐지 룰 생성/수정/삭제
- **성과 분석**: 정탐률, 오탐률, F1 스코어 추적

## [TECH STACK] 기술 스택

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15+ (SQLAlchemy ORM)
- **Cache**: Redis 7+ (비동기 캐싱)
- **ML**: scikit-learn, LightGBM, MLflow
- **Message Queue**: Celery + Redis

### Frontend
- **Framework**: React 18+ with TypeScript 5.3+
- **Build Tool**: Vite 5.0+
- **State Management**: Zustand + React Query
- **UI Components**: Tailwind CSS
- **Charts**: Recharts

### Infrastructure
- **Container**: Docker, Docker Compose
- **Orchestration**: Kubernetes (production)
- **API Gateway**: Nginx
- **Monitoring**: Prometheus + Grafana
- **APM**: Sentry

## [ARCHITECTURE] 시스템 아키텍처

```
[Client Apps]
     |
[Nginx Gateway]
     |
+----+----+----+----+
|    |    |    |    |
v    v    v    v    v
[Services]
- Ecommerce API (8000)
- FDS Service (8001)
- ML Service (8002)
- Admin Dashboard (8003)
     |
[Data Layer]
- PostgreSQL (Primary DB)
- Redis (Cache & Queue)
- MLflow (Model Registry)
```

## [PROJECT STRUCTURE] 프로젝트 구조

```
ShopFDS/
|-- services/                 # 마이크로서비스
|   |-- ecommerce/           # 이커머스 플랫폼
|   |   |-- backend/         # FastAPI 백엔드
|   |   |-- frontend/        # React 프론트엔드
|   |-- fds/                 # FDS 위험 평가 서비스
|   |-- ml-service/          # ML 모델 관리
|   |-- admin-dashboard/     # 관리자 대시보드
|
|-- infrastructure/          # 인프라 설정
|   |-- docker/             # Docker 설정
|   |-- k8s/                # Kubernetes 매니페스트
|   |-- nginx/              # API Gateway 설정
|
|-- specs/                   # 프로젝트 명세
|   |-- 001-ecommerce-fds-platform/
|       |-- spec.md         # 기능 명세서
|       |-- plan.md         # 구현 계획
|       |-- data-model.md   # 데이터 모델
|
|-- docs/                    # 문서
    |-- api/                # API 문서
    |-- architecture/       # 아키텍처 다이어그램
```

## [GETTING STARTED] 시작하기

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+ (로컬 개발용)
- Redis 7+ (로컬 개발용)

### Quick Start
> [RECOMMENDED] For automated setup with Makefile, see [infrastructure/QUICKSTART.md](infrastructure/QUICKSTART.md)


#### 1. 저장소 클론
```bash
git clone https://github.com/yourusername/ShopFDS.git
cd ShopFDS
```

#### 2. Docker Compose로 전체 서비스 실행
```bash
# 모든 서비스 한 번에 실행
docker-compose up -d

# 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f
```

#### 3. 서비스 접속
- **이커머스 프론트엔드**: http://localhost:3000
- **관리자 대시보드**: http://localhost:3001
- **API 문서 (Swagger)**:
  - Ecommerce: http://localhost:8000/docs
  - FDS: http://localhost:8001/docs
  - ML Service: http://localhost:8002/docs
  - Admin: http://localhost:8003/docs

### Local Development

#### Backend 서비스 개발
```bash
# 이커머스 백엔드
cd services/ecommerce/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python src/main.py
```

#### Frontend 개발
```bash
# 이커머스 프론트엔드
cd services/ecommerce/frontend
npm install
npm run dev
```

## [API DOCUMENTATION] API 문서

### 주요 API 엔드포인트

#### 인증
- `POST /v1/auth/register` - 회원가입
- `POST /v1/auth/login` - 로그인
- `POST /v1/auth/logout` - 로그아웃

#### 상품
- `GET /v1/products` - 상품 목록
- `GET /v1/products/{id}` - 상품 상세
- `GET /v1/products/search` - 상품 검색

#### 주문
- `POST /v1/orders` - 주문 생성
- `GET /v1/orders/{id}` - 주문 조회
- `POST /v1/orders/{id}/verify` - OTP 검증

#### FDS
- `POST /v1/fds/evaluate` - 실시간 거래 평가
- `POST /v1/fds/feedback` - 탐지 결과 피드백
- `GET /v1/fds/cti/{entity_type}/{entity_value}` - CTI 조회

상세 API 문서는 `/docs/api/` 디렉토리 참조

## [TESTING] 테스트

### Python 테스트
```bash
# 유닛 테스트
cd services/ecommerce/backend
pytest tests/unit -v

# 통합 테스트
pytest tests/integration -v

# 성능 테스트
cd services/fds
pytest tests/performance -v --benchmark
```

### TypeScript 테스트
```bash
cd services/ecommerce/frontend
npm test
npm run test:coverage
```

### 테스트 커버리지 목표
- 유닛 테스트: 80% 이상
- 통합 테스트: 주요 플로우 100% 커버
- 성능 테스트: FDS 평가 100ms 이내

## [PERFORMANCE] 성능 지표

### 목표 성능
- **FDS 평가 시간**: P95 < 100ms, P99 < 150ms
- **API 응답 시간**: P95 < 200ms
- **동시 처리량**: 1,000+ TPS
- **캐시 히트율**: 85% 이상
- **가용성**: 99.9% SLA

### 모니터링
- **Prometheus**: 메트릭 수집
- **Grafana**: 시각화 대시보드
- **Sentry**: 에러 추적
- **ELK Stack**: 로그 분석

## [SECURITY] 보안

### 보안 준수사항
- **PCI-DSS 3.2.1**: 결제 카드 산업 데이터 보안 표준
- **OWASP Top 10**: 웹 애플리케이션 보안 취약점 대응
- **GDPR**: 개인정보 보호 규정 준수

### 보안 기능
- JWT 기반 인증/인가
- 결제 정보 토큰화
- Rate Limiting
- SQL Injection 방어
- XSS/CSRF 보호
- 민감 데이터 암호화

## [DEPLOYMENT] 배포

### Production 배포
```bash
# Kubernetes 클러스터 배포
cd infrastructure/k8s
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f deployments/
kubectl apply -f services/
kubectl apply -f ingress.yaml
```

### CI/CD Pipeline
- **GitHub Actions**: 자동화된 테스트 및 배포
- **Blue-Green Deployment**: 무중단 배포
- **Canary Release**: 점진적 롤아웃
- **Automatic Rollback**: 실패 시 자동 롤백

## [CONTRIBUTING] 기여 가이드

### 개발 규칙
1. **브랜치 전략**: Git Flow
2. **커밋 메시지**: Conventional Commits
3. **코드 스타일**:
   - Python: Black + Ruff
   - TypeScript: Prettier + ESLint
4. **테스트 작성**: 모든 새 기능에 테스트 필수

### Pull Request 프로세스
1. Feature 브랜치 생성
2. 코드 작성 및 테스트
3. 로컬에서 린팅 및 포맷팅
4. PR 생성 및 리뷰 요청
5. CI 통과 확인
6. 코드 리뷰 및 수정
7. Merge

## [TROUBLESHOOTING] 문제 해결

### 자주 발생하는 문제

#### Docker Compose 실행 실패
```bash
# 포트 충돌 확인
netstat -an | grep 8000

# 컨테이너 정리
docker-compose down -v
docker system prune -f
```

#### 데이터베이스 연결 실패
```bash
# PostgreSQL 상태 확인
docker-compose ps postgres

# 데이터베이스 초기화
docker-compose exec postgres psql -U shopfds
```

#### Redis 연결 실패
```bash
# Redis 상태 확인
docker-compose ps redis

# Redis CLI 접속
docker-compose exec redis redis-cli
```

## [ROADMAP] 로드맵

### Phase 1 (완료)
- [x] 핵심 이커머스 기능
- [x] 기본 FDS 룰 엔진
- [x] 관리자 대시보드

### Phase 2 (진행중)
- [x] ML 모델 통합
- [x] A/B 테스트 기능
- [ ] 실시간 알림 시스템

### Phase 3 (계획)
- [ ] GraphQL API 지원
- [ ] 다국어 지원
- [ ] 모바일 앱

## [LICENSE] 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## [CONTACT] 문의

- **이메일**: contact@shopfds.com
- **이슈 트래커**: [GitHub Issues](https://github.com/yourusername/ShopFDS/issues)
- **문서**: [프로젝트 위키](https://github.com/yourusername/ShopFDS/wiki)

---

[SUCCESS] ShopFDS - Building Safer E-commerce with AI