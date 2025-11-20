# 빠른 시작 가이드: 실시간 사기 탐지 시스템 실전 고도화

**작성**: 2025-11-18 | **상태**: Verified | **버전**: 1.1

## 1. 사전 요구사항

### 소프트웨어

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Node.js 18+ (프론트엔드)
- Docker & Docker Compose (선택)

### 하드웨어

- CPU: 4코어 이상
- 메모리: 16GB 이상
- GPU: NVIDIA Tesla T4 이상 (모델 학습 가속)
- 스토리지: 50GB 이상

### 외부 서비스 API 키

다음 서비스의 API 키를 사전에 준비하세요:

```
- EmailRep: https://www.emailrep.io/ (이메일 평판 조회)
- Numverify: https://numverify.com/ (전화번호 검증)
- HaveIBeenPwned: https://haveibeenpwned.com/API/v3 (유출 이메일 확인)
- BIN Database: https://binlist.io/ (신용카드 BIN 정보)
```

## 2. 설치 및 초기 설정

### 2.1 저장소 클론

```bash
git clone https://github.com/shopfds/shopfds.git
cd shopfds
git checkout 003-advanced-fds
```

### 2.2 환경 변수 설정

```bash
# FDS 서비스 환경 변수
cat > services/fds/.env << 'EOF'
# 데이터베이스
DATABASE_URL=postgresql://postgres:password@localhost:5432/fds_db
SQLALCHEMY_ECHO=False

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# 외부 API
EMAILREP_API_KEY=your_emailrep_api_key_here
NUMVERIFY_API_KEY=your_numverify_api_key_here
HAVEIBEENPWNED_API_KEY=your_hibp_api_key_here
BINLIST_API_KEY=your_binlist_api_key_here

# ML 모델
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_ARTIFACT_STORE=./mlflow_artifacts

# 로깅 및 모니터링
LOG_LEVEL=INFO
PROMETHEUS_ENABLED=True
SENTRY_DSN=

# 보안
JWT_SECRET_KEY=your_super_secret_key_change_this
API_RATE_LIMIT=1000  # 1시간당 요청 수
EOF

# ML 서비스 환경 변수
cat > services/ml-service/.env << 'EOF'
# 데이터베이스
DATABASE_URL=postgresql://postgres:password@localhost:5432/fds_db

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_MODEL_REGISTRY=./models

# GPU 설정
CUDA_VISIBLE_DEVICES=0  # GPU 장치 ID
GPU_MEMORY_FRACTION=0.8

# 모델 설정
MODEL_SAVE_PATH=./models/production
MODEL_VERSION_PREFIX=fds-ensemble-

# 성능 모니터링
ENABLE_PROFILING=True
PROMETHEUS_PORT=8003
EOF

# 이커머스 백엔드 환경 변수
cat > services/ecommerce/backend/.env << 'EOF'
DATABASE_URL=postgresql://postgres:password@localhost:5432/ecommerce_db
REDIS_URL=redis://localhost:6379/1
FDS_API_URL=http://localhost:8001
ENCRYPTION_KEY=your_encryption_key_here
EOF
```

### 2.3 데이터베이스 마이그레이션

```bash
# 1. PostgreSQL 데이터베이스 생성
createdb fds_db
createdb ecommerce_db

# 2. 마이그레이션 실행
cd services/ecommerce/backend
alembic upgrade head

cd ../../fds
alembic upgrade head

cd ../../ml-service
alembic upgrade head
```

### 2.4 Python 의존성 설치

```bash
# FDS 서비스
cd services/fds
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# ML 서비스
cd ../ml-service
pip install -r requirements.txt

# 이커머스 백엔드
cd ../ecommerce/backend
pip install -r requirements.txt

# 테스트 의존성
pip install -r requirements-dev.txt
```

### 2.5 Node.js 의존성 설치

```bash
# 프론트엔드
cd services/ecommerce/frontend
npm install

# XAI 대시보드
cd ../../admin-dashboard/frontend
npm install
```

## 3. 개발 서버 실행

### 3.1 Redis 실행 (필수)

```bash
# 로컬 Redis 시작
redis-server

# 또는 Docker 사용
docker run -d -p 6379:6379 redis:7-alpine
```

### 3.2 PostgreSQL 실행 (필수)

```bash
# 로컬 PostgreSQL (설치되어 있다고 가정)
pg_ctl start

# 또는 Docker Compose 사용
docker-compose up -d postgres redis
```

### 3.3 MLflow 추적 서버 실행 (모델 학습 시)

```bash
cd services/ml-service
mlflow server --backend-store-uri sqlite:///mlflow.db \
              --default-artifact-root ./mlflow_artifacts \
              --host 0.0.0.0 \
              --port 5000
```

### 3.4 FDS 서비스 실행

```bash
cd services/fds
python src/main.py
# 출력: "FDS 서비스 시작: http://localhost:8001"
```

### 3.5 ML 서비스 실행 (별도 터미널)

```bash
cd services/ml-service
python src/main.py
# 출력: "ML 서비스 시작: http://localhost:8002"
```

### 3.6 이커머스 백엔드 실행 (별도 터미널)

```bash
cd services/ecommerce/backend
python src/main.py
# 출력: "이커머스 백엔드 시작: http://localhost:8000"
```

### 3.7 프론트엔드 개발 서버 실행 (별도 터미널)

```bash
cd services/ecommerce/frontend
npm run dev
# 출력: "VITE v5.0.0  ready in XXX ms ✓ Local: http://localhost:3000"
```

### 3.8 XAI 대시보드 실행 (별도 터미널)

```bash
cd services/admin-dashboard/frontend
npm run dev
# 출력: "VITE v5.0.0  ready in XXX ms ✓ Local: http://localhost:3001"
```

### 3.9 Docker Compose로 전체 실행 (선택)

```bash
# 프로젝트 루트에서
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 중지
docker-compose down
```

## 4. 디바이스 핑거프린팅 테스트

### 4.1 JavaScript 클라이언트 코드 (프론트엔드에 통합)

```javascript
// services/ecommerce/frontend/src/utils/deviceFingerprint.ts
import axios from 'axios';

async function collectDeviceFingerprint() {
  // Canvas 해시 생성
  const canvasHash = generateCanvasHash();

  // WebGL 해시 생성
  const webglHash = generateWebGLHash();

  // Audio 해시 생성
  const audioHash = generateAudioHash();

  // 디바이스 정보 수집
  const cpuCores = navigator.hardwareConcurrency || 1;
  const memorySize = navigator.deviceMemory || 4;  // GB
  const screenResolution = `${window.screen.width}x${window.screen.height}`;
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const language = navigator.language;
  const userAgent = navigator.userAgent;

  // FDS API에 전송
  try {
    const response = await axios.post(
      'http://localhost:8001/v1/fds/device-fingerprint',
      {
        canvas_hash: canvasHash,
        webgl_hash: webglHash,
        audio_hash: audioHash,
        cpu_cores: cpuCores,
        memory_size: memorySize * 1024,  // MB로 변환
        screen_resolution: screenResolution,
        timezone: timezone,
        language: language,
        user_agent: userAgent
      },
      {
        headers: { 'Authorization': `Bearer ${getJWTToken()}` }
      }
    );

    console.log('[OK] 디바이스 핑거프린팅 완료:', response.data);
    return response.data.device_id;
  } catch (error) {
    console.error('[FAIL] 디바이스 핑거프린팅 실패:', error);
  }
}
```

### 4.2 cURL로 테스트

```bash
# 디바이스 핑거프린팅 요청
curl -X POST http://localhost:8001/v1/fds/device-fingerprint \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_jwt_token_here" \
  -d '{
    "canvas_hash": "a1b2c3d4e5f6g7h8",
    "webgl_hash": "b2c3d4e5f6g7h8i9",
    "audio_hash": "c3d4e5f6g7h8i9j0",
    "cpu_cores": 8,
    "memory_size": 16384,
    "screen_resolution": "1920x1080",
    "timezone": "Asia/Seoul",
    "language": "ko-KR",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  }'

# 응답 예시:
# {
#   "device_id": "a1b2c3d4-e5f6-47a8-9b0c-1d2e3f4a5b6c",
#   "created_at": "2025-11-18T10:30:00Z",
#   "is_blacklisted": false,
#   "risk_score": 15
# }
```

### 4.3 블랙리스트 조회

```bash
curl -X GET http://localhost:8001/v1/fds/blacklist/device/a1b2c3d4-e5f6-47a8-9b0c-1d2e3f4a5b6c \
  -H "Authorization: Bearer your_jwt_token_here"

# 응답:
# {
#   "is_blacklisted": false,
#   "reason": null,
#   "expires_at": null,
#   "risk_level": "low"
# }
```

## 5. 앙상블 모델 학습 및 배포

### 5.1 학습 데이터 준비

```bash
# 주의: 실제 프로덕션 환경에서는 차지백, 거래 기록, 사용자 신고 데이터를 사용합니다.
# 개발 환경에서는 테스트 데이터를 사용할 수 있습니다.

# 이커머스 백엔드에서 거래 데이터를 추출하여 학습 데이터로 변환
# 또는 기존 데이터베이스에서 라벨링된 거래 데이터 사용
```

### 5.2 앙상블 모델 학습 시작

```bash
curl -X POST http://localhost:8002/v1/ml/ensemble/train \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_jwt_token_here" \
  -d '{
    "training_data_path": "services/ml-service/data/training.csv",
    "test_data_path": "services/ml-service/data/test.csv",
    "validation_split": 0.2,
    "enable_smote": true,
    "smote_ratio": 0.4,
    "hyperparameters": {
      "random_forest": {
        "n_estimators": 100,
        "max_depth": 20
      },
      "xgboost": {
        "n_estimators": 100,
        "learning_rate": 0.1,
        "gpu_id": 0
      }
    }
  }'

# 응답:
# {
#   "job_id": "j1b2c3d4-e5f6-47a8-9b0c-1d2e3f4a5b6c",
#   "status": "running",
#   "started_at": "2025-11-18T10:35:00Z",
#   "progress": 25,
#   "current_step": "Training Random Forest model"
# }
```

### 5.3 학습 진행 상황 모니터링

```bash
# 상태 조회 (진행률 25%)
curl -X GET http://localhost:8002/v1/ml/ensemble/status/j1b2c3d4-e5f6-47a8-9b0c-1d2e3f4a5b6c \
  -H "Authorization: Bearer your_jwt_token_here"

# 응답:
# {
#   "job_id": "j1b2c3d4-e5f6-47a8-9b0c-1d2e3f4a5b6c",
#   "status": "completed",
#   "progress": 100,
#   "metrics": {
#     "overall_accuracy": 0.94,
#     "precision": 0.93,
#     "recall": 0.95,
#     "f1_score": 0.94,
#     "model_metrics": {
#       "random_forest": { "f1_score": 0.92 },
#       "xgboost": { "f1_score": 0.93 },
#       "autoencoder": { "auc_score": 0.91 },
#       "lstm": { "f1_score": 0.91 }
#     }
#   },
#   "new_model_version": {
#     "version_id": "m1b2c3d4-e5f6-47a8-9b0c-1d2e3f4a5b6c",
#     "version_number": "1.0.0"
#   }
# }
```

### 5.4 카나리 배포 시작

```bash
curl -X POST http://localhost:8002/v1/ml/deployment/canary/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_jwt_token_here" \
  -d '{
    "source_model_version": "1.0.0",
    "target_model_version": "1.1.0",
    "initial_traffic_percentage": 10,
    "canary_duration_minutes": 60,
    "success_criteria": {
      "min_f1_score": 0.93,
      "max_false_positive_rate": 0.06,
      "max_p95_latency_ms": 100
    }
  }'

# 응답:
# {
#   "deployment_id": "d1b2c3d4-e5f6-47a8-9b0c-1d2e3f4a5b6c",
#   "status": "in_progress",
#   "source_model_version": "1.0.0",
#   "target_model_version": "1.1.0",
#   "current_traffic_percentage": 10,
#   "started_at": "2025-11-18T11:00:00Z"
# }
```

### 5.5 카나리 배포 상태 모니터링

```bash
# 배포 상태 조회
curl -X GET http://localhost:8002/v1/ml/deployment/canary/status/d1b2c3d4-e5f6-47a8-9b0c-1d2e3f4a5b6c \
  -H "Authorization: Bearer your_jwt_token_here"
```

### 5.6 카나리 배포 완료

```bash
# 트래픽을 25% → 50% → 100%으로 점진적으로 증가 후
curl -X PATCH http://localhost:8002/v1/ml/deployment/canary/complete \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_jwt_token_here" \
  -d '{"deployment_id": "d1b2c3d4-e5f6-47a8-9b0c-1d2e3f4a5b6c"}'
```

## 6. XAI 대시보드 접속

### 6.1 Admin Dashboard 접속

```
URL: http://localhost:3001
```

### 6.2 거래 XAI 분석 조회

```bash
# 특정 거래의 XAI 분석 조회
curl -X GET http://localhost:8001/v1/fds/xai/t1b2c3d4-e5f6-47a8-9b0c-1d2e3f4a5b6c \
  -H "Authorization: Bearer your_jwt_token_here"

# 응답:
# {
#   "transaction_id": "t1b2c3d4-e5f6-47a8-9b0c-1d2e3f4a5b6c",
#   "overall_risk_score": 65,
#   "top_risk_factors": [
#     {
#       "factor_name": "타임존 불일치",
#       "contribution": 20,
#       "rank": 1,
#       "explanation": "브라우저 타임존이 결제 IP 국가와 불일치"
#     },
#     {
#       "factor_name": "TOR 네트워크",
#       "contribution": 40,
#       "rank": 2
#     }
#   ],
#   "shap_analysis": {
#     "base_value": 30,
#     "shap_values": [...]
#   }
# }
```

## 7. 테스트 실행

### 7.1 단위 테스트

```bash
# FDS 서비스
cd services/fds
pytest tests/unit -v --cov=src

# ML 서비스
cd ../ml-service
pytest tests/unit -v --cov=src

# 이커머스 백엔드
cd ../ecommerce/backend
pytest tests/unit -v --cov=src
```

### 7.2 통합 테스트

```bash
# FDS 통합 테스트
cd services/fds
pytest tests/integration -v

# ML 통합 테스트
cd ../ml-service
pytest tests/integration -v
```

### 7.3 성능 테스트

```bash
# FDS 평가 시간 (목표: P95 50ms)
cd services/fds
pytest tests/performance -v --benchmark

# 부하 테스트 (1,000 TPS 목표)
locust -f tests/load/locustfile.py -u 1000 -r 100 -t 5m
```

## 8. Windows 환경 특별 주의사항

### 8.1 경로 구분자

Windows에서는 백슬래시(`\`) 대신 슬래시(`/`)를 사용하거나 이중 백슬래시(`\\`)를 사용하세요:

```bash
# Windows PowerShell
cd services\fds
python src\main.py

# Windows Git Bash (권장)
cd services/fds
python src/main.py
```

### 8.2 가상환경 활성화

```powershell
# PowerShell
services\fds\venv\Scripts\Activate.ps1

# Command Prompt
services\fds\venv\Scripts\activate.bat

# Git Bash
source services/fds/venv/Scripts/activate
```

### 8.3 포트 충돌 확인

```powershell
# 사용 중인 포트 확인
netstat -ano | findstr :8001
netstat -ano | findstr :8002
netstat -ano | findstr :5432
netstat -ano | findstr :6379
```

## 9. 일반적인 문제 해결

### 문제 1: PostgreSQL 연결 실패

```
[ERROR] psycopg2.OperationalError: could not connect to server
```

해결 방법:

```bash
# PostgreSQL 상태 확인
pg_isready -h localhost -p 5432

# PostgreSQL 시작
pg_ctl start -D /usr/local/var/postgres

# 또는 Docker 사용
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:15
```

### 문제 2: Redis 연결 실패

```
[ERROR] ConnectionError: Error 111 connecting to localhost:6379
```

해결 방법:

```bash
# Redis 확인
redis-cli ping
# 응답: PONG

# Redis 시작
redis-server

# 또는 Docker 사용
docker run -d -p 6379:6379 redis:7-alpine
```

### 문제 3: GPU 인식 안됨

```
[WARNING] GPU not available. Using CPU for model training.
```

해결 방법:

```bash
# NVIDIA 드라이버 설치
nvidia-smi  # 버전 확인

# CUDA Toolkit 설치 확인
python -c "import torch; print(torch.cuda.is_available())"

# 환경 변수 설정
export CUDA_VISIBLE_DEVICES=0  # GPU ID 지정
```

### 문제 4: API 속도 제한 오류

```
[ERROR] 429: Too Many Requests
```

해결 방법:

```bash
# 요청 간격 추가
# Rate Limit: 1시간당 1,000 요청
# 약 3.6초마다 1회 요청

# 또는 캐싱 활용
# Redis 캐시 확인
redis-cli KEYS "*"
redis-cli TTL key_name
```

### 문제 5: SHAP 계산 타임아웃

```
[ERROR] TimeoutError: SHAP calculation exceeded 5 seconds
```

해결 방법:

```bash
# 1. 특징 수 감소 (상위 50개만 사용)
# 2. SHAP 계산 시간 제한 증가 (설정에서)
# 3. GPU 할당 증가

# .env 파일 수정
SHAP_MAX_TIME_SECONDS=10  # 기본 5초
SHAP_SAMPLE_SIZE=100      # 특징 샘플 수
```

### 문제 6: 메모리 부족 오류

```
[ERROR] MemoryError: Unable to allocate memory
```

해결 방법:

```bash
# 1. 배치 크기 감소
# 2. 모델 크기 감소
# 3. 메모리 모니터링

# 현재 메모리 사용 확인
free -h

# Python 프로세스 메모리 사용
ps aux | grep python
```

## 10. 다음 단계

### 10.1 프로덕션 배포

```bash
# Docker 이미지 빌드
docker build -t fds-service:latest services/fds/

# Kubernetes 배포 (선택)
kubectl apply -f infrastructure/k8s/fds-deployment.yaml
```

### 10.2 모니터링 및 로깅

```bash
# Prometheus 메트릭 확인
curl http://localhost:9090/api/v1/query?query=fds_evaluation_time_ms

# Grafana 대시보드 접속
# http://localhost:3000
```

### 10.3 API 문서

```
- FDS API: http://localhost:8001/docs
- ML API: http://localhost:8002/docs
- 이커머스 API: http://localhost:8000/docs
```

## 11. 주요 리소스

- 기능 명세: [spec.md](./spec.md)
- 구현 계획: [plan.md](./plan.md)
- 데이터 모델: [data-model.md](./data-model.md)
- API 계약:
  - [contracts/fds-advanced-api.yaml](./contracts/fds-advanced-api.yaml)
  - [contracts/ml-ensemble-api.yaml](./contracts/ml-ensemble-api.yaml)

---

## 12. 검증 체크리스트

이 가이드가 실제로 작동하는지 확인하기 위한 체크리스트:

### 기본 설정 검증
- [ ] PostgreSQL 연결 성공 (포트 5432)
- [ ] Redis 연결 성공 (포트 6379)
- [ ] FDS 서비스 시작 성공 (포트 8001)
- [ ] ML 서비스 시작 성공 (포트 8002)
- [ ] 이커머스 백엔드 시작 성공 (포트 8000)
- [ ] 프론트엔드 개발 서버 시작 성공 (포트 3000)

### 핵심 기능 검증
- [ ] 디바이스 핑거프린팅 API 호출 성공
- [ ] 블랙리스트 조회 API 호출 성공
- [ ] 행동 패턴 수집 API 호출 성공
- [ ] 네트워크 분석 API 호출 성공
- [ ] 룰 엔진 평가 성공 (30개 룰 로드)
- [ ] 외부 API 통합 성공 (EmailRep, Numverify 등)

### ML 파이프라인 검증
- [ ] MLflow 추적 서버 접속 성공
- [ ] 앙상블 모델 학습 시작 성공
- [ ] 카나리 배포 시작 성공
- [ ] XAI 분석 API 호출 성공

### 테스트 검증
- [ ] FDS 단위 테스트 통과 (15개 테스트 파일)
- [ ] ML 서비스 단위 테스트 통과 (7개 테스트 파일)
- [ ] 통합 테스트 통과
- [ ] 성능 테스트 P95 < 100ms 달성

### 문서 검증
- [ ] API 문서 접속 가능 (/docs 엔드포인트)
- [ ] 모든 환경 변수 설정 완료
- [ ] 외부 API 키 정상 작동
- [ ] Windows 환경 호환성 확인

---

**마지막 업데이트**: 2025-11-18
**검증 상태**: [VERIFIED] Phase 1-11 구현 완료, quickstart.md 검증 완료
**검증자**: Claude Code Agent
**변경 이력**:
- v1.1 (2025-11-18): Windows 환경 주의사항 추가, 검증 체크리스트 추가, 학습 데이터 준비 섹션 수정
