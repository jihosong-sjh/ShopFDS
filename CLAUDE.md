# ShopFDS Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-13

## 프로젝트 개요

AI/ML 기반 이커머스 FDS 플랫폼 - 실시간 사기 거래 탐지 시스템을 통합한 전자상거래 플랫폼

## Active Technologies

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15+ (SQLAlchemy, Alembic)
- **Cache**: Redis 7+ (aioredis)
- **ML**: scikit-learn, LightGBM
- **Testing**: pytest, pytest-asyncio

### Frontend
- **Framework**: React 18+ with TypeScript 5.3+
- **Build Tool**: Vite 5.0+
- **State Management**: Zustand (global), React Query (API)
- **HTTP Client**: Axios
- **Styling**: Tailwind CSS

### Infrastructure
- **Container**: Docker, Docker Compose
- **Orchestration**: Kubernetes (planned)
- **Gateway**: Nginx
- **Monitoring**: Prometheus, Grafana, Sentry

## Project Structure

```text
services/
├── ecommerce/                # 이커머스 플랫폼 서비스
│   ├── backend/             # FastAPI 백엔드
│   │   ├── src/
│   │   │   ├── models/      # SQLAlchemy 모델
│   │   │   ├── services/    # 비즈니스 로직
│   │   │   ├── api/         # REST API 엔드포인트
│   │   │   └── middleware/  # 인증, 로깅
│   │   └── tests/           # pytest 테스트
│   └── frontend/            # React + TypeScript
│       ├── src/
│       │   ├── components/
│       │   ├── pages/
│       │   └── services/
│       └── tests/
├── fds/                      # FDS 위험 평가 서비스
│   ├── src/
│   │   ├── engines/         # 룰/ML/CTI 엔진
│   │   ├── models/
│   │   └── api/
│   └── tests/
├── ml-service/               # ML 모델 학습/배포
│   ├── src/
│   │   ├── training/
│   │   ├── evaluation/
│   │   └── deployment/
│   └── notebooks/
├── admin-dashboard/          # 보안팀 대시보드
└── shared/                   # 공통 라이브러리

infrastructure/
├── docker/                   # Dockerfile, compose
├── k8s/                      # Kubernetes manifests
└── nginx/                    # API Gateway 설정

specs/001-ecommerce-fds-platform/
├── spec.md                   # 기능 명세서
├── plan.md                   # 구현 계획
├── research.md               # 기술 리서치
├── data-model.md             # 데이터베이스 스키마
├── quickstart.md             # 빠른 시작 가이드
└── contracts/                # API 계약
    ├── openapi.yaml
    └── fds-contract.md
```

## Commands

### 데이터베이스 마이그레이션
```bash
cd services/ecommerce/backend
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

### 개발 서버 실행
```bash
# 백엔드 (이커머스)
cd services/ecommerce/backend
python src/main.py  # http://localhost:8000

# 백엔드 (FDS)
cd services/fds
python src/main.py  # http://localhost:8001

# 프론트엔드
cd services/ecommerce/frontend
npm run dev  # http://localhost:3000
```

### 테스트
```bash
# Python 유닛 테스트
pytest tests/unit -v --cov=src

# Python 통합 테스트
pytest tests/integration -v

# FDS 성능 테스트 (목표: 100ms)
pytest tests/performance -v --benchmark

# TypeScript 테스트
npm test
```

### Docker Compose
```bash
# 전체 서비스 실행
docker-compose up -d

# 특정 서비스만 실행
docker-compose up -d postgres redis

# 로그 확인
docker-compose logs -f ecommerce-backend
```

## Code Style

### Python (Black + Ruff)
```bash
black src/
ruff check src/
```

### TypeScript (Prettier + ESLint)
```bash
npm run lint
npm run format
```

### 네이밍 컨벤션
- **Python**: `snake_case` (함수, 변수), `PascalCase` (클래스)
- **TypeScript**: `camelCase` (함수, 변수), `PascalCase` (컴포넌트, 인터페이스)
- **API 엔드포인트**: `/kebab-case`
- **데이터베이스**: `snake_case`

## 핵심 원칙

1. **보안 우선**: 결제 정보 토큰화, 비밀번호 bcrypt 해싱, 민감 데이터 로그 금지
2. **성능 목표**: FDS 평가 100ms 이내, API 응답 200ms 이내
3. **테스트 우선**: 유닛 테스트 커버리지 80% 이상, 통합 테스트 필수
4. **비동기 처리**: FastAPI async/await 활용, Redis 캐싱
5. **마이크로서비스**: 서비스별 독립 배포, API Gateway 통합

## Recent Changes

- 2025-11-13: 프로젝트 초기 설정 완료
  - Phase 0: 기술 스택 리서치 (research.md)
  - Phase 1: 데이터 모델 정의 (data-model.md)
  - Phase 1: API 계약 작성 (contracts/)
  - Phase 1: 빠른 시작 가이드 (quickstart.md)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
