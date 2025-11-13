# 빠른 시작 가이드: 이커머스 FDS 플랫폼

**Version**: 1.0.0
**Last Updated**: 2025-11-13

본 가이드는 개발자가 로컬 환경에서 이커머스 FDS 플랫폼을 빠르게 구축하고 실행할 수 있도록 단계별 지침을 제공합니다.

---

## 목차

1. [사전 요구사항](#1-사전-요구사항)
2. [프로젝트 구조 생성](#2-프로젝트-구조-생성)
3. [데이터베이스 설정](#3-데이터베이스-설정)
4. [백엔드 서비스 설정](#4-백엔드-서비스-설정)
5. [프론트엔드 설정](#5-프론트엔드-설정)
6. [Docker Compose로 전체 실행](#6-docker-compose로-전체-실행)
7. [API 테스트](#7-api-테스트)
8. [개발 워크플로우](#8-개발-워크플로우)

---

## 1. 사전 요구사항

### 필수 소프트웨어

| 소프트웨어 | 최소 버전 | 설치 확인 |
|-----------|----------|----------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| PostgreSQL | 15+ | `psql --version` |
| Redis | 7+ | `redis-server --version` |
| Docker | 24+ | `docker --version` |
| Docker Compose | 2.20+ | `docker-compose --version` |

### 권장 도구

- **IDE**: VS Code (Python, TypeScript 확장 설치)
- **API 테스트**: Postman 또는 HTTPie
- **데이터베이스 클라이언트**: DBeaver 또는 pgAdmin

---

## 2. 프로젝트 구조 생성

### 2.1 리포지토리 클론 (또는 초기화)

```bash
# Git 리포지토리 초기화
git init ShopFDS
cd ShopFDS

# 프로젝트 구조 생성
mkdir -p services/{ecommerce/backend,ecommerce/frontend,fds,ml-service,admin-dashboard/backend,admin-dashboard/frontend,shared}
mkdir -p infrastructure/{docker,k8s,nginx,scripts}
mkdir -p docs/{api,architecture,deployment}
```

### 2.2 .gitignore 설정

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
.venv/
venv/
.env
*.db

# Node.js
node_modules/
dist/
build/
.env.local

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Docker
docker-compose.override.yml
EOF
```

---

## 3. 데이터베이스 설정

### 3.1 PostgreSQL 설치 및 실행 (Docker 사용)

```bash
# docker-compose.yml 생성
cat > infrastructure/docker/docker-compose.dev.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: shopfds-postgres
    environment:
      POSTGRES_USER: shopfds
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: shopfds_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shopfds"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: shopfds-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
  redis_data:
EOF

# 데이터베이스 실행
cd infrastructure/docker
docker-compose -f docker-compose.dev.yml up -d

# 연결 확인
psql -h localhost -U shopfds -d shopfds_dev -c "SELECT version();"
```

### 3.2 TimescaleDB 확장 설치 (선택)

```bash
# PostgreSQL 컨테이너 접속
docker exec -it shopfds-postgres psql -U shopfds -d shopfds_dev

# TimescaleDB 확장 생성
CREATE EXTENSION IF NOT EXISTS timescaledb;
\dx  -- 확장 목록 확인
```

---

## 4. 백엔드 서비스 설정

### 4.1 이커머스 백엔드 (FastAPI)

```bash
cd services/ecommerce/backend

# Python 가상 환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
aioredis==2.0.1
httpx==0.25.2
psycopg2-binary==2.9.9
asyncpg==0.29.0
python-multipart==0.0.6
EOF

pip install -r requirements.txt

# 프로젝트 구조 생성
mkdir -p src/{models,services,api,middleware,utils}
mkdir -p tests/{unit,integration,e2e}

# 환경 변수 설정
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://shopfds:dev_password@localhost:5432/shopfds_dev
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
FDS_SERVICE_URL=http://localhost:8001
EOF

# 메인 애플리케이션 생성
cat > src/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="이커머스 플랫폼 API",
    description="FDS 통합 이커머스 플랫폼",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "이커머스 플랫폼 API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
EOF

# 실행
python src/main.py
```

**접속 확인**: http://localhost:8000/docs (Swagger UI)

### 4.2 FDS 서비스 (FastAPI)

```bash
cd services/fds

# Python 가상 환경 생성
python -m venv .venv
source .venv/bin/activate

# 의존성 설치
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
aioredis==2.0.1
httpx==0.25.2
scikit-learn==1.3.2
lightgbm==4.1.0
pandas==2.1.4
numpy==1.26.2
joblib==1.3.2
EOF

pip install -r requirements.txt

# 프로젝트 구조 생성
mkdir -p src/{models,engines,api,services,utils}
mkdir -p tests/{unit,integration,performance}

# 환경 변수 설정
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://shopfds:dev_password@localhost:5432/shopfds_dev
REDIS_URL=redis://localhost:6379/1
ML_MODEL_PATH=./models/isolation_forest_v1.pkl
ABUSEIPDB_API_KEY=your-api-key
CTI_TIMEOUT_MS=50
TARGET_EVALUATION_TIME_MS=100
EOF

# 메인 애플리케이션 생성
cat > src/main.py << 'EOF'
from fastapi import FastAPI

app = FastAPI(
    title="FDS API",
    description="사기 탐지 시스템",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "FDS 서비스", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "target_latency_ms": 100}

@app.post("/internal/fds/evaluate")
async def evaluate_transaction(request: dict):
    # TODO: 실제 FDS 로직 구현
    return {
        "transaction_id": request.get("transaction_id"),
        "risk_score": 25,
        "risk_level": "low",
        "decision": "approve",
        "evaluation_metadata": {
            "evaluation_time_ms": 87
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
EOF

# 실행
python src/main.py
```

**접속 확인**: http://localhost:8001/docs

---

## 5. 프론트엔드 설정

### 5.1 이커머스 프론트엔드 (React + Vite)

```bash
cd services/ecommerce/frontend

# Vite 프로젝트 생성
npm create vite@latest . -- --template react-ts

# 의존성 설치
npm install

# 추가 패키지 설치
npm install axios @tanstack/react-query zustand react-router-dom zod

# 환경 변수 설정
cat > .env.local << 'EOF'
VITE_API_BASE_URL=http://localhost:8000/v1
EOF

# 개발 서버 실행
npm run dev
```

**접속 확인**: http://localhost:3000

---

## 6. Docker Compose로 전체 실행

### 6.1 전체 서비스 Docker Compose

```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # 데이터베이스
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: shopfds
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: shopfds_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # 이커머스 백엔드
  ecommerce-backend:
    build:
      context: ./services/ecommerce/backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://shopfds:dev_password@postgres:5432/shopfds_dev
      REDIS_URL: redis://redis:6379/0
      FDS_SERVICE_URL: http://fds:8001
    depends_on:
      - postgres
      - redis

  # FDS 서비스
  fds:
    build:
      context: ./services/fds
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: postgresql+asyncpg://shopfds:dev_password@postgres:5432/shopfds_dev
      REDIS_URL: redis://redis:6379/1
    depends_on:
      - postgres
      - redis

  # 이커머스 프론트엔드
  ecommerce-frontend:
    build:
      context: ./services/ecommerce/frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      VITE_API_BASE_URL: http://localhost:8000/v1
    depends_on:
      - ecommerce-backend

volumes:
  postgres_data:
EOF

# 전체 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

---

## 7. API 테스트

### 7.1 회원가입 & 로그인

```bash
# 회원가입
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "name": "홍길동"
  }'

# 응답 예시
# {
#   "user": {...},
#   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "refresh_token": "..."
# }

# 로그인
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'
```

### 7.2 상품 조회

```bash
# 상품 목록
curl http://localhost:8000/v1/products

# 상품 상세
curl http://localhost:8000/v1/products/{product_id}
```

### 7.3 주문 생성 (FDS 통합 테스트)

```bash
# Access Token을 환경 변수에 저장
export TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."

# 장바구니에 상품 추가
curl -X POST http://localhost:8000/v1/cart/items \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "550e8400-e29b-41d4-a716-446655440000",
    "quantity": 2
  }'

# 주문 생성
curl -X POST http://localhost:8000/v1/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_name": "홍길동",
    "shipping_address": "서울특별시 강남구 테헤란로 123",
    "shipping_phone": "010-1234-5678",
    "payment_info": {
      "card_number": "1234567890123456",
      "card_expiry": "12/25",
      "card_cvv": "123"
    }
  }'

# 응답에서 FDS 결과 확인
# {
#   "order": {...},
#   "fds_result": {
#     "action": "approve",
#     "risk_score": 35,
#     "message": "정상 거래"
#   }
# }
```

---

## 8. 개발 워크플로우

### 8.1 데이터베이스 마이그레이션

```bash
cd services/ecommerce/backend

# Alembic 초기화
alembic init alembic

# 마이그레이션 생성
alembic revision --autogenerate -m "Create users table"

# 마이그레이션 적용
alembic upgrade head

# 롤백
alembic downgrade -1
```

### 8.2 테스트 실행

```bash
# 백엔드 유닛 테스트
cd services/ecommerce/backend
pytest tests/unit -v --cov=src

# 통합 테스트
pytest tests/integration -v

# FDS 성능 테스트 (목표: 100ms 이내)
cd services/fds
pytest tests/performance -v --benchmark
```

### 8.3 코드 포매팅 & 린팅

```bash
# Python (Black + Ruff)
pip install black ruff
black src/
ruff check src/

# TypeScript (Prettier + ESLint)
npm install -D prettier eslint
npm run lint
npm run format
```

### 8.4 Git 워크플로우

```bash
# Feature 브랜치 생성
git checkout -b feature/user-authentication

# 커밋
git add .
git commit -m "feat: Implement JWT authentication"

# Push
git push origin feature/user-authentication

# Pull Request 생성 (GitHub/GitLab)
```

---

## 9. 다음 단계

✅ 로컬 환경 구축 완료

**추천 학습 경로**:
1. [data-model.md](./data-model.md) - 데이터베이스 스키마 이해
2. [contracts/openapi.yaml](./contracts/openapi.yaml) - API 명세 확인
3. [contracts/fds-contract.md](./contracts/fds-contract.md) - FDS 통합 이해
4. [research.md](./research.md) - 기술 스택 상세 설명

**구현 시작**:
- Phase 1: 이커머스 플랫폼 (FR-001 ~ FR-026)
- Phase 2: FDS 통합 (FR-027 ~ FR-055)

---

## 10. 트러블슈팅

### PostgreSQL 연결 실패

```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs postgres

# 포트 충돌 시 변경
# docker-compose.yml에서 ports를 "15432:5432"로 변경
```

### Redis 연결 실패

```bash
# Redis 핑 테스트
docker exec -it shopfds-redis redis-cli ping

# 응답: PONG (정상)
```

### Python 패키지 설치 오류

```bash
# pip 업그레이드
pip install --upgrade pip setuptools wheel

# 캐시 삭제
pip cache purge
pip install -r requirements.txt --no-cache-dir
```

---

## 문의 및 지원

- **이슈 트래커**: [GitHub Issues](https://github.com/your-org/ShopFDS/issues)
- **문서**: [docs/](../../../docs/)
- **API 문서**: http://localhost:8000/docs (개발 서버 실행 후)
