# ML Service 통합 테스트

Phase 8: 사용자 스토리 6 - ML 모델 학습 및 성능 개선 - 통합 및 검증(T126-T127)

## 개요

본 통합 테스트는 ML 모델 재학습 파이프라인, 카나리 배포, 롤백 시나리오의 전체 워크플로우를 검증합니다.

## 테스트 파일

### 1. test_training_pipeline.py (T126: 모델 재학습 파이프라인 검증)

**검증 항목:**
- Isolation Forest 학습 파이프라인
- LightGBM 학습 파이프라인
- 데이터 로드 및 전처리
- Feature Engineering
- 모델 평가 및 저장
- 버전 관리 통합
- 엔드투엔드 학습 워크플로우

**테스트 클래스:**

#### TestIsolationForestPipeline
- `test_isolation_forest_training`: Isolation Forest 전체 학습 파이프라인
  - Feature Engineering
  - 데이터 전처리
  - 모델 학습
  - 예측 및 평가
  - 모델 저장 및 로드

#### TestLightGBMPipeline
- `test_lightgbm_training`: LightGBM 전체 학습 파이프라인
  - Feature Engineering
  - 데이터 전처리
  - Train/Val/Test 분할
  - 모델 학습 (Early Stopping)
  - 평가 및 Feature Importance
  - 모델 저장 및 로드

#### TestVersionManagementIntegration
- `test_model_registration_and_versioning`: 버전 관리 통합
  - 모델 등록
  - 스테이징 배포
  - 프로덕션 승격
  - 모델 비교

#### TestEndToEndTrainingPipeline
- `test_complete_training_workflow`: 전체 학습 워크플로우
  - Isolation Forest + LightGBM 학습
  - 모델 비교
  - 최적 모델 프로덕션 배포

### 2. test_canary_rollback.py (T127: 카나리 배포 및 롤백 시나리오 검증)

**검증 항목:**
- 카나리 배포 시작 (10% 트래픽)
- 트래픽 분할 로직 (해시 기반 일관된 라우팅)
- 성능 모니터링 및 통계 수집
- 트래픽 점진적 증가 (10% → 25% → 50% → 100%)
- 카나리 배포 완료 (프로덕션 승격)
- 카나리 배포 중단 (롤백)
- 긴급 롤백
- 특정 버전으로 롤백
- 롤백 히스토리 관리

**테스트 클래스:**

#### TestCanaryDeployment
- `test_start_canary_deployment`: 카나리 배포 시작
- `test_traffic_routing`: 트래픽 라우팅 (해시 기반 일관된 분할)
- `test_performance_monitoring`: 성능 모니터링 및 통계 수집
- `test_gradual_traffic_increase`: 트래픽 점진적 증가 (10% → 100%)
- `test_complete_canary_deployment`: 카나리 배포 완료 (프로덕션 승격)
- `test_abort_canary_deployment`: 카나리 배포 중단

#### TestModelRollback
- `test_emergency_rollback`: 긴급 롤백 (최근 은퇴 모델로 즉시 롤백)
- `test_rollback_to_specific_version`: 특정 버전으로 롤백
- `test_get_rollback_candidates`: 롤백 가능 모델 목록 조회
- `test_validate_rollback`: 롤백 가능 여부 검증
- `test_rollback_history`: 롤백 히스토리 관리

#### TestEndToEndCanaryRollback
- `test_complete_canary_rollback_workflow`: 전체 카나리 롤백 워크플로우
  - 프로덕션 모델 운영
  - 카나리 배포 (10% → 25% → 50%)
  - 성능 저하 감지
  - 카나리 배포 중단
  - 기존 모델 유지

## 실행 방법

### 전체 통합 테스트 실행

```bash
cd services/ml-service
pytest tests/integration -v -s
```

### 특정 테스트 파일 실행

```bash
# T126: 모델 재학습 파이프라인
pytest tests/integration/test_training_pipeline.py -v -s

# T127: 카나리 배포 및 롤백
pytest tests/integration/test_canary_rollback.py -v -s
```

### 특정 테스트 클래스 실행

```bash
# Isolation Forest 학습 파이프라인만
pytest tests/integration/test_training_pipeline.py::TestIsolationForestPipeline -v -s

# 카나리 배포 테스트만
pytest tests/integration/test_canary_rollback.py::TestCanaryDeployment -v -s

# 롤백 테스트만
pytest tests/integration/test_canary_rollback.py::TestModelRollback -v -s
```

### 특정 테스트 메서드 실행

```bash
# Isolation Forest 학습 파이프라인 테스트
pytest tests/integration/test_training_pipeline.py::TestIsolationForestPipeline::test_isolation_forest_training -v -s

# 카나리 배포 시작 테스트
pytest tests/integration/test_canary_rollback.py::TestCanaryDeployment::test_start_canary_deployment -v -s

# 긴급 롤백 테스트
pytest tests/integration/test_canary_rollback.py::TestModelRollback::test_emergency_rollback -v -s
```

### 마커 기반 실행

```bash
# 통합 테스트만
pytest -m integration -v -s

# 느린 테스트 제외
pytest -m "not slow" -v -s
```

### 커버리지와 함께 실행

```bash
pytest tests/integration --cov=src --cov-report=html -v -s
```

## 테스트 환경

### 데이터베이스
- SQLite In-Memory (비동기 및 동기 모드)
- 자동 스키마 생성 (MLModel, FraudCase)

### 샘플 데이터
- 1,000개 거래 데이터
- 정상 거래: 800개 (80%)
- 사기 거래: 200개 (20%)
- 특성: amount, velocity_1h, is_foreign_ip, failed_login_attempts 등

### Fixture

#### async_db_session
- 비동기 데이터베이스 세션
- 카나리 배포, 롤백, 버전 관리 테스트에 사용

#### sync_db_session
- 동기 데이터베이스 세션
- ML 모델 학습 테스트에 사용

#### sample_training_data
- 샘플 학습 데이터 (DataFrame)
- 1,000개 거래 + 특성

#### setup_models
- 테스트용 프로덕션 및 스테이징 모델 생성

## 검증 기준

### 모델 재학습 파이프라인 (T126)

1. **데이터 로드 및 전처리**
   - Feature Engineering 성공
   - 스케일링 및 인코딩 정상 작동
   - Train/Test 분할 비율 확인 (80:20)

2. **모델 학습**
   - Isolation Forest: 이상치 탐지율 > 10%
   - LightGBM: Early Stopping 작동
   - 평가 메트릭 범위: 0 ≤ accuracy, precision, recall, f1_score ≤ 1

3. **모델 저장 및 로드**
   - 모델 파일 생성 확인
   - 로드 후 예측 결과 일치

4. **버전 관리**
   - 모델 등록 성공
   - 스테이징 → 프로덕션 승격
   - 모델 비교 기능

### 카나리 배포 및 롤백 (T127)

1. **카나리 배포**
   - 카나리 설정 생성 (10% 트래픽)
   - 트래픽 분할 정확도: 목표 ± 3%
   - 성능 모니터링 통계 수집

2. **트래픽 증가**
   - 점진적 증가 (10% → 25% → 50% → 100%)
   - 통계 초기화 확인

3. **카나리 배포 완료**
   - 카나리 모델 → 프로덕션 승격
   - 기존 프로덕션 → 은퇴

4. **롤백**
   - 긴급 롤백: 최근 은퇴 모델 복원
   - 특정 버전 롤백: 지정 모델로 복원
   - 롤백 히스토리 기록

5. **성능 저하 감지**
   - 카나리 성공률 < 임계값 → 권장 사항 생성
   - 성능 비교 및 경고 메시지

## 의존성

### Python 패키지
```
pytest>=7.0
pytest-asyncio
sqlalchemy>=2.0
aiosqlite
numpy
pandas
scikit-learn
lightgbm
```

### 설치
```bash
pip install -r services/ml-service/requirements.txt
pip install pytest pytest-asyncio aiosqlite
```

## 트러블슈팅

### ImportError: No module named 'src'
- `pytest.ini`에서 `pythonpath = .` 확인
- 또는 `PYTHONPATH` 환경 변수 설정:
  ```bash
  export PYTHONPATH=D:\side-project\ShopFDS\services\ml-service:$PYTHONPATH
  ```

### SQLite 비동기 에러
- `aiosqlite` 설치 확인:
  ```bash
  pip install aiosqlite
  ```

### Windows 인코딩 에러
- 테스트 출력에 ASCII 문자만 사용
- 한글 출력은 `print()`로만

## 성공 기준

### T126: 모델 재학습 파이프라인 검증 ✓
- [X] Isolation Forest 학습 파이프라인 전체 통과
- [X] LightGBM 학습 파이프라인 전체 통과
- [X] 버전 관리 통합 (등록, 배포, 승격, 비교)
- [X] 엔드투엔드 워크플로우 (데이터 → 학습 → 평가 → 배포)

### T127: 카나리 배포 및 롤백 시나리오 검증 ✓
- [X] 카나리 배포 시작 및 트래픽 분할
- [X] 성능 모니터링 및 통계 수집
- [X] 트래픽 점진적 증가 (10% → 100%)
- [X] 카나리 배포 완료 (프로덕션 승격)
- [X] 카나리 배포 중단 (롤백)
- [X] 긴급 롤백 및 특정 버전 롤백
- [X] 롤백 히스토리 관리
- [X] 엔드투엔드 워크플로우 (배포 → 모니터링 → 중단)

## 다음 단계

Phase 8 완료! 모든 ML 모델 학습 및 배포 기능이 검증되었습니다.

다음 Phase:
- Phase 9: 마무리 및 교차 기능 (성능 최적화, 보안 강화, 모니터링, 배포, 문서화)

## 참고

- 프로젝트 구조: [CLAUDE.md](../../../../../CLAUDE.md)
- 기능 명세: [spec.md](../../../../../specs/001-ecommerce-fds-platform/spec.md)
- 구현 계획: [plan.md](../../../../../specs/001-ecommerce-fds-platform/plan.md)
- 태스크 목록: [tasks.md](../../../../../specs/001-ecommerce-fds-platform/tasks.md)
