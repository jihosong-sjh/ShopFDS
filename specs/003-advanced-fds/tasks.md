# Tasks: 실시간 사기 탐지 시스템 실전 고도화

**Input**: `/specs/003-advanced-fds/` 설계 문서
**Prerequisites**: plan.md (필수), spec.md (사용자 스토리), research.md, data-model.md, contracts/

**Tests**: 이 tasks.md는 테스트 작성을 포함하지 않습니다. 각 User Story의 Acceptance Scenarios를 기반으로 구현 완료 후 테스트할 수 있습니다.

**Organization**: 태스크는 사용자 스토리별로 그룹화되어 각 스토리를 독립적으로 구현하고 테스트할 수 있습니다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (다른 파일, 의존성 없음)
- **[Story]**: 어느 사용자 스토리에 속하는지 (예: US1, US2, US3)
- 설명에 정확한 파일 경로 포함

## 프로젝트 경로 규칙

- **FDS 서비스**: `services/fds/src/`, `services/fds/tests/`
- **ML 서비스**: `services/ml-service/src/`, `services/ml-service/tests/`
- **이커머스 프론트엔드**: `services/ecommerce/frontend/src/`
- **Admin 대시보드**: `services/admin-dashboard/frontend/src/`

---

## Phase 1: Setup (프로젝트 초기화)

**목적**: 프로젝트 구조 및 기본 설정

- [X] T001 고도화 브랜치 생성 및 프로젝트 구조 확인
- [X] T002 [P] FDS 서비스에 신규 디렉토리 생성 (engines/, models/, services/)
- [X] T003 [P] ML 서비스에 신규 디렉토리 생성 (models/, training/, deployment/, monitoring/)
- [X] T004 [P] 이커머스 프론트엔드에 utils/ 디렉토리 생성
- [X] T005 [P] Admin 대시보드 프론트엔드에 pages/ 디렉토리 생성
- [X] T006 외부 API 키 환경 변수 설정 (.env 파일)

---

## Phase 2: Foundational (공통 인프라)

**목적**: 모든 사용자 스토리가 의존하는 핵심 인프라 구축

**⚠️ CRITICAL**: 이 Phase가 완료되어야 사용자 스토리 작업을 시작할 수 있습니다

- [X] T007 데이터베이스 마이그레이션 생성 (13개 신규 엔티티) in services/fds/alembic/versions/
- [X] T008 DeviceFingerprint 모델 생성 in services/fds/src/models/device_fingerprint.py
- [X] T009 [P] BehaviorPattern 모델 생성 in services/fds/src/models/behavior_pattern.py
- [X] T010 [P] NetworkAnalysis 모델 생성 in services/fds/src/models/network_analysis.py
- [X] T011 [P] FraudRule 모델 생성 in services/fds/src/models/fraud_rule.py
- [X] T012 [P] RuleExecution 모델 생성 in services/fds/src/models/rule_execution.py
- [X] T013 [P] MLModelVersion 모델 생성 in services/ml-service/src/models/ml_model_version.py
- [X] T014 [P] EnsemblePrediction 모델 생성 in services/ml-service/src/models/ensemble_prediction.py
- [X] T015 [P] FeatureImportance 모델 생성 in services/ml-service/src/models/feature_importance.py
- [X] T016 [P] XAIExplanation 모델 생성 in services/fds/src/models/xai_explanation.py
- [X] T017 [P] DataDriftLog 모델 생성 in services/ml-service/src/models/data_drift_log.py
- [X] T018 [P] RetrainingJob 모델 생성 in services/ml-service/src/models/retraining_job.py
- [X] T019 [P] ExternalServiceLog 모델 생성 in services/fds/src/models/external_service_log.py
- [X] T020 [P] BlacklistEntry 모델 생성 in services/fds/src/models/blacklist_entry.py
- [X] T021 데이터베이스 마이그레이션 적용 (alembic upgrade head)
- [X] T022 Redis 캐시 유틸리티 생성 in services/fds/src/utils/cache_utils.py
- [X] T023 외부 API 공통 클라이언트 생성 in services/fds/src/services/external_api_client.py

**Checkpoint**: 인프라 준비 완료 - 사용자 스토리 구현을 병렬로 시작할 수 있습니다

---

## Phase 3: User Story 1 - 디바이스 핑거프린팅 기반 사기 탐지 (Priority: P1) 🎯 MVP

**Goal**: 브라우저 기반 디바이스 고유 지문을 수집하고 블랙리스트와 대조하여 사기를 탐지

**Independent Test**: 동일 브라우저에서 쿠키 삭제 후 재접속 시 동일 디바이스 ID 생성 확인, VPN 변경 후에도 디바이스 식별 검증

### Implementation for User Story 1

- [X] T024 [P] [US1] 클라이언트 사이드 핑거프린팅 유틸리티 생성 (Canvas/WebGL/Audio 해싱) in services/ecommerce/frontend/src/utils/deviceFingerprint.ts
- [X] T025 [P] [US1] 디바이스 핑거프린팅 수집 API 구현 (POST /v1/fds/device-fingerprint) in services/fds/src/api/device_fingerprint.py
- [X] T026 [US1] 디바이스 ID 생성 엔진 구현 (SHA-256 해싱) in services/fds/src/engines/fingerprint_engine.py
- [X] T027 [US1] 타임존/언어 불일치 검사 로직 구현 in services/fds/src/engines/fingerprint_engine.py
- [X] T028 [US1] 블랙리스트 조회 API 구현 (GET /v1/fds/blacklist/device/{device_id}) in services/fds/src/api/blacklist.py
- [X] T029 [US1] 블랙리스트 등록/해제 API 구현 (POST/DELETE /v1/fds/blacklist) in services/fds/src/api/blacklist.py
- [X] T030 [US1] Redis 캐싱 적용 (디바이스 ID 조회 TTL 24시간)
- [X] T031 [US1] 프론트엔드 통합 (사용자 접속 시 자동 핑거프린팅 수집) in services/ecommerce/frontend/src/App.tsx

**Checkpoint**: US1 완료 - 디바이스 핑거프린팅 시스템이 독립적으로 작동하며 95% 정확도로 디바이스 재식별

---

## Phase 4: User Story 2 - 행동 패턴 분석 기반 봇 탐지 (Priority: P1)

**Goal**: 마우스 움직임, 키보드 타이핑, 클릭스트림 분석으로 자동화된 봇과 정상 사용자 구별

**Independent Test**: Selenium 스크립트로 자동 주문 시 봇으로 분류되는지 확인, 정상 사용자와 행동 패턴 점수 비교

### Implementation for User Story 2

- [X] T032 [P] [US2] 클라이언트 사이드 행동 패턴 추적 유틸리티 생성 (mousemove/keydown/click 이벤트) in services/ecommerce/frontend/src/utils/behaviorTracking.ts
- [X] T033 [P] [US2] 행동 패턴 분석 엔진 구현 (마우스 속도/가속도/곡률 계산) in services/fds/src/engines/behavior_analysis_engine.py
- [X] T034 [US2] 키보드 타이핑 패턴 분석 로직 구현 (입력 속도, 백스페이스 빈도) in services/fds/src/engines/behavior_analysis_engine.py
- [X] T035 [US2] 클릭스트림 분석 로직 구현 (페이지 체류 시간 이상치 탐지) in services/fds/src/engines/behavior_analysis_engine.py
- [X] T036 [US2] 봇 확률 점수 계산 알고리즘 구현 (곡률 < 0.1 → 85점) in services/fds/src/engines/behavior_analysis_engine.py
- [X] T037 [US2] 행동 패턴 데이터 수집 API 구현 (POST /v1/fds/behavior-pattern) in services/fds/src/api/behavior_pattern.py
- [X] T038 [US2] 봇 탐지 시 추가 인증 트리거 로직 구현 (OTP/CAPTCHA 요구)
- [X] T039 [US2] 프론트엔드 통합 (결제 페이지에서 행동 패턴 수집) in services/ecommerce/frontend/src/pages/CheckoutPage.tsx

**Checkpoint**: US2 완료 - 행동 패턴 분석이 봇을 90% 정확도로 탐지하고 추가 인증 자동 요청

---

## Phase 5: User Story 3 - 네트워크 분석 기반 프록시/VPN 탐지 (Priority: P2)

**Goal**: TOR/VPN/Proxy 사용 탐지 및 GeoIP 불일치 검사로 의심스러운 접속 식별

**Independent Test**: TOR 브라우저로 접속 시 "TOR 사용" 플래그 확인, 상용 VPN 사용 시 탐지 여부 검증

### Implementation for User Story 3

- [X] T040 [P] [US3] TOR Exit Node 리스트 데이터 로더 구현 (https://check.torproject.org/torbulkexitlist) in services/fds/src/engines/network_analysis_engine.py
- [X] T041 [P] [US3] GeoIP 데이터베이스 통합 (MaxMind GeoIP2) in services/fds/src/engines/network_analysis_engine.py
- [X] T042 [US3] ASN 평판 조회 로직 구현 (WHOIS 데이터베이스) in services/fds/src/engines/network_analysis_engine.py
- [X] T043 [US3] DNS PTR 역방향 조회 로직 구현 (프록시 키워드 탐지) in services/fds/src/engines/network_analysis_engine.py
- [X] T044 [US3] 네트워크 분석 종합 엔진 구현 (TOR/VPN/Proxy 판정) in services/fds/src/engines/network_analysis_engine.py
- [X] T045 [US3] 국가 불일치 검사 로직 구현 (GeoIP vs 결제 카드 발급국) in services/fds/src/engines/network_analysis_engine.py
- [X] T046 [US3] 네트워크 분석 API 구현 (POST /v1/fds/network-analysis) in services/fds/src/api/network_analysis.py
- [X] T047 [US3] Redis 캐싱 적용 (IP 주소별 TTL 1시간)

**Checkpoint**: US3 완료 - 네트워크 분석이 TOR 95%, VPN/Proxy 85% 정확도로 탐지

---

## Phase 6: User Story 4 - 실전 사기 탐지 룰 30개 적용 (Priority: P1)

**Goal**: 결제/계정/배송지 사기 유형별 30개 룰 적용으로 명백한 사기 패턴 자동 차단

**Independent Test**: 테스트 카드(4111111111111111)로 결제 시 즉시 차단, 1분 내 5회 비밀번호 실패 시 계정 잠금 확인

### Implementation for User Story 4

- [X] T048 [P] [US4] 결제 관련 룰 10개 구현 (테스트 카드, BIN 불일치 등) in services/fds/src/engines/fraud_rule_engine.py
- [X] T049 [P] [US4] 계정 탈취 관련 룰 10개 구현 (비밀번호 실패, 세션 하이재킹 등) in services/fds/src/engines/fraud_rule_engine.py
- [X] T050 [P] [US4] 배송지 사기 관련 룰 10개 구현 (화물 전달 주소, 일회용 이메일 등) in services/fds/src/engines/fraud_rule_engine.py
- [X] T051 [US4] 룰 우선순위 실행 엔진 구현 (차단 > 수동 검토 > 위험 점수) in services/fds/src/engines/fraud_rule_engine.py
- [X] T052 [US4] 테스트 카드 리스트 데이터 로더 구현 (4111111111111111 등) in services/fds/src/data/test_cards.json
- [X] T053 [US4] 화물 전달 주소 DB 로더 구현 in services/fds/src/data/freight_forwarders.json
- [X] T054 [US4] 일회용 이메일 도메인 리스트 로더 구현 in services/fds/src/data/disposable_emails.json
- [X] T055 [US4] 룰 관리 API 구현 (POST/PUT/DELETE /v1/fds/rules) in services/fds/src/api/rules.py
- [X] T056 [US4] 룰 실행 결과 저장 로직 구현 (RuleExecution 엔티티)
- [X] T057 [US4] 룰 DB 초기 데이터 시드 스크립트 생성 in services/fds/scripts/seed_fraud_rules.py

**Checkpoint**: US4 완료 - 30개 룰이 테스트 카드 등 명백한 사기 패턴을 100% 정확도로 차단

---

## Phase 7: User Story 5 - 앙상블 ML 모델 기반 정밀 예측 (Priority: P2)

**Goal**: Random Forest, XGBoost, Autoencoder, LSTM 조합으로 사기 예측 정확도 95% 이상 달성

**Independent Test**: 과거 6개월 사기 데이터로 학습 후 테스트 데이터셋에서 F1 Score 0.95 이상 검증

### Implementation for User Story 5

- [X] T058 [P] [US5] Random Forest 모델 학습 코드 구현 in services/ml-service/src/models/random_forest_model.py
- [X] T059 [P] [US5] XGBoost 모델 학습 코드 구현 (GPU 가속) in services/ml-service/src/models/xgboost_model.py
- [X] T060 [P] [US5] Autoencoder 모델 학습 코드 구현 (PyTorch) in services/ml-service/src/models/autoencoder_model.py
- [X] T061 [P] [US5] LSTM 모델 학습 코드 구현 (시계열 패턴) in services/ml-service/src/models/lstm_model.py
- [X] T062 [US5] SMOTE 데이터 불균형 처리 로직 구현 (사기 5% → 40%) in services/ml-service/src/training/data_resampler.py
- [X] T063 [US5] Feature Engineering 파이프라인 구현 in services/ml-service/src/training/feature_engineering.py
- [X] T064 [US5] 앙상블 가중 투표 로직 구현 (RF 30%, XGB 35%, AE 25%, LSTM 10%) in services/ml-service/src/models/ensemble_model.py
- [X] T065 [US5] Feature Importance 분석 코드 구현 (Random Forest) in services/ml-service/src/training/feature_importance_analyzer.py
- [X] T066 [US5] MLflow 실험 추적 통합 in services/ml-service/src/training/mlflow_tracker.py
- [X] T067 [US5] 모델 학습 API 구현 (POST /v1/ml/ensemble/train) in services/ml-service/src/api/training.py
- [X] T068 [US5] 학습 진행 상황 모니터링 API 구현 (GET /v1/ml/ensemble/status/{job_id}) in services/ml-service/src/api/training.py
- [X] T069 [US5] 모델 평가 메트릭 계산 로직 구현 (Precision, Recall, F1 Score) in services/ml-service/src/training/evaluator.py

**Checkpoint**: US5 완료 - 앙상블 모델이 F1 Score 0.95, 오탐률 6%, 미탐률 12.6% 달성

---

## Phase 8: User Story 6 - 실시간 추론 최적화 및 Edge 배포 (Priority: P3)

**Goal**: 모델 양자화, 배치 추론, WebAssembly 배포로 FDS 평가 시간 50ms 달성

**Independent Test**: TorchServe 1,000 TPS 부하 시 P95 응답 50ms 이내 측정, WebAssembly 모델 브라우저 작동 검증

### Implementation for User Story 6

- [X] T070 [P] [US6] PyTorch 모델 INT8 양자화 코드 구현 in services/ml-service/src/deployment/quantizer.py
- [X] T071 [P] [US6] ONNX Runtime 통합 (추론 가속) in services/ml-service/src/deployment/onnx_converter.py
- [X] T072 [US6] TorchServe 배포 설정 구현 (배치 크기 50) in services/ml-service/src/deployment/torchserve_deploy.py
- [X] T073 [US6] 배치 추론 파이프라인 구현 (동시 요청 50개 이상 시 활성화) in services/ml-service/src/deployment/batch_inference.py
- [X] T074 [US6] WebAssembly 모델 컴파일 코드 구현 (Emscripten) in services/ml-service/src/deployment/wasm_compiler.py
- [X] T075 [US6] 클라이언트 사이드 모델 로더 구현 (브라우저) in services/ecommerce/frontend/src/utils/wasmModelLoader.ts
- [X] T076 [US6] 클라이언트 사이드 봇 차단 로직 구현 (점수 90+ 서버 요청 전 차단) in services/ecommerce/frontend/src/utils/clientSideBotBlocker.ts
- [X] T077 [US6] 모델 배포 API 구현 (POST /v1/ml/deployment/deploy) in services/ml-service/src/api/optimization.py
- [X] T078 [US6] 추론 시간 모니터링 로직 구현 (P95 50ms 목표) in services/ml-service/src/deployment/performance_monitor.py

**Checkpoint**: US6 완료 - 추론 시간 P95 50ms 달성, 서버 부하 20% 감소

---

## Phase 9: User Story 7 - 설명 가능한 AI (XAI) 대시보드 (Priority: P2)

**Goal**: SHAP/LIME 분석으로 거래 차단 사유 구체적 근거를 실시간 시각화

**Independent Test**: 특정 거래 "high risk" 판정 후 XAI 대시보드에서 위험 요인 상위 5개 확인, SHAP 값 일치 검증

### Implementation for User Story 7

- [X] T079 [P] [US7] SHAP 분석 엔진 구현 (TreeExplainer, DeepExplainer) in services/fds/src/services/xai_service.py
- [X] T080 [P] [US7] LIME 로컬 모델 근사 코드 구현 in services/fds/src/services/xai_service.py
- [X] T081 [US7] Feature 기여도 계산 로직 구현 (워터폴 차트 데이터) in services/fds/src/services/xai_service.py
- [X] T082 [US7] SHAP 계산 타임아웃 처리 로직 구현 (5초 제한) in services/fds/src/services/xai_service.py
- [X] T083 [US7] XAI 분석 API 구현 (GET /v1/fds/xai/{transaction_id}) in services/fds/src/api/xai.py
- [X] T084 [US7] XAI 대시보드 프론트엔드 페이지 생성 in services/admin-dashboard/frontend/src/pages/XAIDashboard.tsx
- [X] T085 [US7] 워터폴 차트 컴포넌트 구현 (Recharts) in services/admin-dashboard/frontend/src/components/WaterfallChart.tsx
- [X] T086 [US7] 위험 요인 상위 5개 시각화 컴포넌트 구현 in services/admin-dashboard/frontend/src/components/TopRiskFactors.tsx
- [X] T087 [US7] SHAP 값 검증 로직 구현 (feature 값과 일치 확인)

**Checkpoint**: US7 완료 - XAI 대시보드에서 거래 차단 사유를 3클릭 이내로 확인 가능, SHAP 분석 95%가 5초 이내

---

## Phase 10: User Story 8 - 자동화된 학습 파이프라인 및 데이터 드리프트 감지 (Priority: P3)

**Goal**: 차지백/신고 데이터 자동 수집, 데이터 드리프트 감지, 자동 재학습으로 모델 최신성 유지

**Independent Test**: 차지백 100건 수집 시 자동 라벨링 트리거 확인, 모델 정확도 3% 하락 시 재학습 알림 검증

### Implementation for User Story 8

- [X] T088 [P] [US8] 차지백 데이터 자동 라벨링 시스템 구현 in services/ml-service/src/training/auto_labeler.py
- [X] T089 [P] [US8] 사용자 신고 데이터 수집 로직 구현 in services/ml-service/src/training/feedback_collector.py
- [X] T090 [US8] 데이터 드리프트 감지 로직 구현 (KS 테스트) in services/ml-service/src/monitoring/drift_detector.py
- [X] T091 [US8] 모델 성능 모니터링 로직 구현 (F1 Score 추적) in services/ml-service/src/monitoring/performance_monitor.py
- [X] T092 [US8] 자동 재학습 트리거 로직 구현 (성능 저하/드리프트 감지 시) in services/ml-service/src/training/auto_retrainer.py
- [X] T093 [US8] Celery 비동기 작업 큐 통합 (재학습 작업) in services/ml-service/src/training/celery_tasks.py
- [X] T094 [US8] Slack 알림 통합 (성능 저하, 재학습 완료) in services/ml-service/src/utils/slack_notifier.py
- [X] T095 [US8] A/B 테스트 자동화 로직 구현 (신규 모델 카나리 배포) in services/ml-service/src/deployment/ab_test_manager.py
- [X] T096 [US8] 데이터 드리프트 모니터링 API 구현 (GET /v1/ml/monitoring/drift) in services/ml-service/src/api/monitoring.py
- [X] T097 [US8] 재학습 작업 상태 API 구현 (GET /v1/ml/training/jobs/{job_id}) in services/ml-service/src/api/training.py

**Checkpoint**: US8 완료 - 자동 학습 파이프라인이 데이터 드리프트 감지 후 24시간 이내 재학습 완료

---

## Phase 11: User Story 9 - 외부 서비스 통합 검증 강화 (Priority: P2)

**Goal**: EmailRep, Numverify, BIN DB, HaveIBeenPwned API 통합으로 사용자 신원 다층 검증

**Independent Test**: 유출 이메일(leaked@example.com)로 가입 시 경고 표시, 허위 전화번호 사용 시 거부 확인

### Implementation for User Story 9

- [X] T098 [P] [US9] EmailRep API 통합 (이메일 평판 조회) in services/fds/src/services/emailrep_service.py
- [X] T099 [P] [US9] Numverify API 통합 (전화번호 검증) in services/fds/src/services/numverify_service.py
- [X] T100 [P] [US9] BIN Database API 통합 (카드 발급국 조회) in services/fds/src/services/bin_service.py
- [X] T101 [P] [US9] HaveIBeenPwned API 통합 (유출 이메일 확인) in services/fds/src/services/hibp_service.py
- [X] T102 [US9] 외부 API 통합 서비스 구현 (Fallback 로직, 5초 타임아웃) in services/fds/src/services/external_verification_service.py
- [X] T103 [US9] 외부 서비스 호출 로그 저장 로직 구현 (ExternalServiceLog 엔티티)
- [X] T104 [US9] 이메일 검증 API 구현 (POST /v1/fds/verify/email) in services/fds/src/api/verification.py
- [X] T105 [US9] 전화번호 검증 API 구현 (POST /v1/fds/verify/phone) in services/fds/src/api/verification.py
- [X] T106 [US9] 카드 BIN 검증 API 구현 (POST /v1/fds/verify/card-bin) in services/fds/src/api/verification.py
- [X] T107 [US9] 외부 API 재시도 로직 구현 (3회 재시도, 지수 백오프)

**Checkpoint**: US9 완료 - 외부 서비스 통합으로 계정 탈취 사기 80% 감소, API 실패 시 Fallback 자동 실행

---

## Phase 12: Polish & Cross-Cutting Concerns (마무리 및 교차 기능)

**목적**: 여러 사용자 스토리에 영향을 주는 개선 사항

- [ ] T108 [P] 통합 FDS 평가 엔진 구현 (모든 엔진 조합) in services/fds/src/engines/evaluation_engine.py
- [ ] T109 통합 FDS 평가 API 구현 (POST /v1/fds/evaluate) in services/fds/src/api/evaluation.py
- [ ] T110 [P] 성능 최적화 (Redis 캐싱 확장, 쿼리 최적화)
- [ ] T111 [P] 보안 강화 (API Rate Limiting, JWT 검증)
- [ ] T112 [P] Prometheus 메트릭 추가 (FDS 평가 시간, 모델 추론 시간)
- [ ] T113 [P] Grafana 대시보드 생성 (성능 지표, 사기 탐지율)
- [ ] T114 [P] API 문서 업데이트 (Swagger/OpenAPI)
- [ ] T115 통합 테스트 작성 (전체 FDS 평가 플로우)
- [ ] T116 성능 테스트 실행 (1,000 TPS 부하, P95 50ms 검증)
- [ ] T117 quickstart.md 검증 및 업데이트
- [ ] T118 보안 감사 (GDPR/CCPA/PCI-DSS 준수 확인)
- [ ] T119 코드 리뷰 및 리팩토링
- [ ] T120 최종 배포 준비 (Docker 이미지 빌드, Kubernetes 매니페스트)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존성 없음 - 즉시 시작 가능
- **Foundational (Phase 2)**: Setup 완료 후 - 모든 사용자 스토리 차단
- **User Stories (Phase 3-11)**: Foundational 완료 후 병렬 실행 가능
  - 우선순위 순서: P1 (US1, US2, US4) → P2 (US3, US5, US7, US9) → P3 (US6, US8)
- **Polish (Phase 12)**: 모든 원하는 사용자 스토리 완료 후

### User Story Dependencies

- **US1 (디바이스 핑거프린팅, P1)**: Foundational 완료 후 - 다른 스토리 의존성 없음
- **US2 (행동 패턴 분석, P1)**: Foundational 완료 후 - 다른 스토리 의존성 없음
- **US3 (네트워크 분석, P2)**: Foundational 완료 후 - 다른 스토리 의존성 없음
- **US4 (사기 탐지 룰, P1)**: Foundational 완료 후 - 다른 스토리 의존성 없음
- **US5 (앙상블 ML, P2)**: Foundational 완료 후 - 다른 스토리 의존성 없음
- **US6 (추론 최적화, P3)**: US5 완료 후 (모델 학습 필요)
- **US7 (XAI 대시보드, P2)**: US5 완료 후 (ML 모델 필요)
- **US8 (자동 학습, P3)**: US5 완료 후 (ML 모델 필요)
- **US9 (외부 서비스, P2)**: Foundational 완료 후 - 다른 스토리 의존성 없음

### Within Each User Story

- 모델(Models) → 서비스(Services) → API → 프론트엔드 통합
- 핵심 구현 → 통합 → 검증
- 각 스토리 완료 후 다음 우선순위로 이동

### Parallel Opportunities

- Phase 1 모든 [P] 태스크 병렬 실행 가능
- Phase 2 모든 [P] 태스크(T009-T020) 병렬 실행 가능
- Foundational 완료 후 모든 사용자 스토리 병렬 시작 가능 (팀 역량 허용 시)
- 각 User Story 내 [P] 태스크 병렬 실행 가능
- 다른 사용자 스토리는 다른 팀원이 병렬 작업 가능

---

## Parallel Example: User Story 1

```bash
# User Story 1 모든 [P] 태스크 함께 실행:
Task: "클라이언트 사이드 핑거프린팅 유틸리티 생성 (Canvas/WebGL/Audio 해싱) in services/ecommerce/frontend/src/utils/deviceFingerprint.ts"
Task: "디바이스 핑거프린팅 수집 API 구현 (POST /v1/fds/device-fingerprint) in services/fds/src/api/device_fingerprint.py"
```

---

## Implementation Strategy

### MVP First (User Story 1, 2, 4만 구현 - P1 우선순위)

1. Phase 1: Setup 완료
2. Phase 2: Foundational 완료 (CRITICAL - 모든 스토리 차단)
3. Phase 3: User Story 1 완료 (디바이스 핑거프린팅)
4. Phase 4: User Story 2 완료 (행동 패턴 분석)
5. Phase 6: User Story 4 완료 (사기 탐지 룰 30개)
6. **STOP and VALIDATE**: P1 스토리 독립 테스트
7. 배포/데모 준비 완료

### Incremental Delivery

1. Setup + Foundational → 인프라 준비 완료
2. US1 추가 → 독립 테스트 → 배포/데모 (디바이스 핑거프린팅)
3. US2 추가 → 독립 테스트 → 배포/데모 (봇 탐지)
4. US4 추가 → 독립 테스트 → 배포/데모 (30개 룰) - MVP 완료!
5. US3, US5, US7, US9 추가 → P2 기능 (고급 분석, ML, XAI, 외부 서비스)
6. US6, US8 추가 → P3 기능 (최적화, 자동화)
7. 각 스토리가 이전 스토리를 깨지 않고 가치 추가

### Parallel Team Strategy

다수 개발자가 있는 경우:

1. 팀이 Setup + Foundational 함께 완료
2. Foundational 완료 후:
   - Developer A: User Story 1 (디바이스 핑거프린팅)
   - Developer B: User Story 2 (행동 패턴 분석)
   - Developer C: User Story 4 (사기 탐지 룰)
   - ML Engineer: User Story 5 (앙상블 ML)
3. 스토리별로 완료 및 독립적으로 통합

---

## Notes

- [P] 태스크 = 다른 파일, 의존성 없음
- [Story] 라벨은 추적을 위해 특정 사용자 스토리에 태스크 매핑
- 각 사용자 스토리는 독립적으로 완료 및 테스트 가능해야 함
- 각 태스크 또는 논리적 그룹 후 커밋
- 모든 체크포인트에서 중지하여 스토리를 독립적으로 검증
- 회피 사항: 모호한 태스크, 동일 파일 충돌, 독립성을 깨는 교차 스토리 의존성

---

## 총 태스크 수: 120개

- Phase 1 (Setup): 6개
- Phase 2 (Foundational): 17개
- Phase 3 (US1): 8개
- Phase 4 (US2): 8개
- Phase 5 (US3): 8개
- Phase 6 (US4): 10개
- Phase 7 (US5): 12개
- Phase 8 (US6): 9개
- Phase 9 (US7): 9개
- Phase 10 (US8): 10개
- Phase 11 (US9): 10개
- Phase 12 (Polish): 13개

### User Story별 태스크 수

- US1 (디바이스 핑거프린팅): 8개
- US2 (행동 패턴 분석): 8개
- US3 (네트워크 분석): 8개
- US4 (사기 탐지 룰): 10개
- US5 (앙상블 ML): 12개
- US6 (추론 최적화): 9개
- US7 (XAI 대시보드): 9개
- US8 (자동 학습): 10개
- US9 (외부 서비스): 10개

### MVP 범위 (P1 우선순위만)

- Setup (6개) + Foundational (17개) + US1 (8개) + US2 (8개) + US4 (10개) = **49개 태스크**
- 예상 완료 시간: 2-3주 (개발자 2-3명 기준)

### 전체 범위 (P1 + P2 + P3)

- 전체 120개 태스크
- 예상 완료 시간: 6-8주 (개발자 3-4명 + ML 엔지니어 1명 기준)

---

**마지막 업데이트**: 2025-11-18
**검증 상태**: [OK] 모든 태스크가 체크리스트 형식 준수, 파일 경로 포함, 사용자 스토리별 그룹화 완료
