# 데이터 모델: 실시간 사기 탐지 시스템 실전 고도화

**작성**: 2025-11-18 | **상태**: Draft | **버전**: 1.0

## 개요

실시간 사기 탐지 시스템 고도화를 위한 PostgreSQL 데이터 모델. 디바이스 핑거프린팅, 행동 패턴, 네트워크 분석, 사기 탐지 룰, ML 모델, XAI 분석, 자동화된 학습 파이프라인 등 13개 주요 엔티티를 정의한다.

## 엔티티 정의

### 1. DeviceFingerprint (디바이스 핑거프린트)

브라우저 기반 디바이스 고유 식별 정보를 저장한다.

```sql
CREATE TABLE device_fingerprints (
    device_id VARCHAR(64) PRIMARY KEY,  -- SHA-256 해시
    canvas_hash VARCHAR(64) NOT NULL,   -- Canvas API 해시
    webgl_hash VARCHAR(64) NOT NULL,    -- WebGL API 해시
    audio_hash VARCHAR(64) NOT NULL,    -- Audio API 해시
    cpu_cores INT NOT NULL,             -- CPU 코어 수
    memory_size INT NOT NULL,           -- 메모리 크기 (MB)
    screen_resolution VARCHAR(20) NOT NULL,  -- 예: "1920x1080"
    timezone VARCHAR(50) NOT NULL,      -- 예: "Asia/Seoul"
    language VARCHAR(10) NOT NULL,      -- 예: "ko-KR"
    user_agent TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    blacklisted BOOLEAN DEFAULT FALSE,
    blacklist_reason TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_device_fingerprints_created_at ON device_fingerprints(created_at);
CREATE INDEX idx_device_fingerprints_blacklisted ON device_fingerprints(blacklisted);
```

### 2. BehaviorPattern (행동 패턴)

사용자의 마우스, 키보드, 클릭스트림 패턴을 저장한다.

```sql
CREATE TABLE behavior_patterns (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    mouse_movements JSONB,  -- [{timestamp, x, y, speed, acceleration, curvature}]
    keyboard_events JSONB,  -- [{timestamp, key, duration}]
    clickstream JSONB,      -- [{page, timestamp, duration}]
    bot_score INT DEFAULT 0,  -- 0-100 봇 확률
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_behavior_patterns_user_id ON behavior_patterns(user_id);
CREATE INDEX idx_behavior_patterns_created_at ON behavior_patterns(created_at);
```

### 3. NetworkAnalysis (네트워크 분석)

거래별 네트워크 분석 결과를 저장한다.

```sql
CREATE TABLE network_analysis (
    transaction_id UUID PRIMARY KEY,
    ip_address INET NOT NULL,
    geoip_country VARCHAR(2),
    geoip_city VARCHAR(50),
    asn INT,
    asn_organization VARCHAR(255),
    is_tor BOOLEAN DEFAULT FALSE,
    is_vpn BOOLEAN DEFAULT FALSE,
    is_proxy BOOLEAN DEFAULT FALSE,
    dns_ptr_record VARCHAR(255),
    country_mismatch BOOLEAN DEFAULT FALSE,
    risk_score INT DEFAULT 0,  -- 0-100
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
);

CREATE INDEX idx_network_analysis_ip_address ON network_analysis(ip_address);
CREATE INDEX idx_network_analysis_created_at ON network_analysis(created_at);
```

### 4. FraudRule (사기 탐지 룰)

실전 사기 탐지 룰 정의를 저장한다.

```sql
CREATE TYPE rule_category AS ENUM ('payment', 'account', 'shipping');

CREATE TABLE fraud_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name VARCHAR(255) NOT NULL,
    rule_category rule_category NOT NULL,
    rule_description TEXT,
    rule_logic JSONB,  -- 룰 실행 로직 저장
    risk_score INT NOT NULL,  -- 이 룰이 매칭되면 부여할 점수
    is_active BOOLEAN DEFAULT TRUE,
    priority INT DEFAULT 0,  -- 높을수록 먼저 실행
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID
);

CREATE INDEX idx_fraud_rules_category ON fraud_rules(rule_category);
CREATE INDEX idx_fraud_rules_is_active ON fraud_rules(is_active);
CREATE INDEX idx_fraud_rules_priority ON fraud_rules(priority DESC);
```

### 5. RuleExecution (룰 실행 결과)

거래별 룰 실행 결과를 저장한다.

```sql
CREATE TABLE rule_executions (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL,
    rule_id UUID NOT NULL,
    matched BOOLEAN NOT NULL,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,  -- 매칭 상세 정보
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    FOREIGN KEY (rule_id) REFERENCES fraud_rules(id) ON DELETE CASCADE
);

CREATE INDEX idx_rule_executions_transaction_id ON rule_executions(transaction_id);
CREATE INDEX idx_rule_executions_rule_id ON rule_executions(rule_id);
CREATE INDEX idx_rule_executions_triggered_at ON rule_executions(triggered_at);
```

### 6. MLModelVersion (ML 모델 버전)

ML 모델 버전 관리를 위한 엔티티.

```sql
CREATE TYPE model_name AS ENUM ('random_forest', 'xgboost', 'autoencoder', 'lstm');

CREATE TABLE ml_model_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name model_name NOT NULL,
    model_type VARCHAR(50),  -- 예: "ensemble"
    version_number VARCHAR(20) NOT NULL,  -- 예: "1.0.0"
    trained_at TIMESTAMP NOT NULL,
    accuracy FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    is_active BOOLEAN DEFAULT FALSE,
    model_path VARCHAR(255) NOT NULL,  -- S3 또는 로컬 경로
    hyperparameters JSONB,  -- 학습에 사용된 하이퍼파라미터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_name, version_number)
);

CREATE INDEX idx_ml_model_versions_is_active ON ml_model_versions(is_active);
CREATE INDEX idx_ml_model_versions_trained_at ON ml_model_versions(trained_at);
```

### 7. EnsemblePrediction (앙상블 예측)

앙상블 모델의 예측 결과를 저장한다.

```sql
CREATE TYPE prediction_decision AS ENUM ('allow', 'block', 'review');

CREATE TABLE ensemble_predictions (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL,
    rf_score FLOAT,        -- Random Forest 예측 (0-1)
    xgb_score FLOAT,       -- XGBoost 예측 (0-1)
    autoencoder_score FLOAT,  -- Autoencoder 예측 (0-1)
    lstm_score FLOAT,      -- LSTM 예측 (0-1)
    ensemble_score FLOAT NOT NULL,  -- 가중 평균 (0-1)
    final_decision prediction_decision NOT NULL,
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_version_id UUID,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    FOREIGN KEY (model_version_id) REFERENCES ml_model_versions(version_id)
);

CREATE INDEX idx_ensemble_predictions_transaction_id ON ensemble_predictions(transaction_id);
CREATE INDEX idx_ensemble_predictions_predicted_at ON ensemble_predictions(predicted_at);
```

### 8. FeatureImportance (Feature 중요도)

ML 모델의 Feature 중요도 분석 결과를 저장한다.

```sql
CREATE TABLE feature_importances (
    analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version_id UUID NOT NULL,
    feature_name VARCHAR(255) NOT NULL,
    importance_score FLOAT NOT NULL,  -- 0-1
    rank INT NOT NULL,  -- 1부터 시작
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_version_id) REFERENCES ml_model_versions(version_id) ON DELETE CASCADE
);

CREATE INDEX idx_feature_importances_model_version_id ON feature_importances(model_version_id);
CREATE INDEX idx_feature_importances_rank ON feature_importances(rank);
```

### 9. XAIExplanation (XAI 분석)

SHAP/LIME 기반 XAI 분석 결과를 저장한다.

```sql
CREATE TABLE xai_explanations (
    explanation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL,
    shap_values JSONB,  -- [{feature, shap_value, base_value}]
    lime_explanation JSONB,  -- 로컬 모델 근사 결과
    top_risk_factors JSONB,  -- [{factor, contribution, rank}]
    explanation_time_ms INT,  -- SHAP 계산 시간
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
);

CREATE INDEX idx_xai_explanations_transaction_id ON xai_explanations(transaction_id);
CREATE INDEX idx_xai_explanations_generated_at ON xai_explanations(generated_at);
```

### 10. DataDriftLog (데이터 드리프트 로그)

데이터 분포 변화를 추적한다.

```sql
CREATE TABLE data_drift_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metric_name VARCHAR(255) NOT NULL,  -- 예: "avg_order_amount", "transaction_frequency"
    baseline_value FLOAT NOT NULL,
    current_value FLOAT NOT NULL,
    drift_percentage FLOAT NOT NULL,  -- 변화율 (%)
    alert_triggered BOOLEAN DEFAULT FALSE,
    alert_message TEXT
);

CREATE INDEX idx_data_drift_logs_detected_at ON data_drift_logs(detected_at);
CREATE INDEX idx_data_drift_logs_alert_triggered ON data_drift_logs(alert_triggered);
```

### 11. RetrainingJob (재학습 작업)

모델 재학습 작업을 추적한다.

```sql
CREATE TYPE retrain_trigger_type AS ENUM ('auto', 'manual');
CREATE TYPE retrain_status AS ENUM ('pending', 'running', 'completed', 'failed');

CREATE TABLE retraining_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    triggered_by retrain_trigger_type NOT NULL,
    trigger_reason VARCHAR(255),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status retrain_status DEFAULT 'pending',
    new_model_version_id UUID,
    metrics JSONB,  -- {accuracy, precision, recall, f1_score}
    logs TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (new_model_version_id) REFERENCES ml_model_versions(version_id)
);

CREATE INDEX idx_retraining_jobs_status ON retraining_jobs(status);
CREATE INDEX idx_retraining_jobs_created_at ON retraining_jobs(created_at);
```

### 12. ExternalServiceLog (외부 서비스 호출 로그)

EmailRep, Numverify, BIN DB, HaveIBeenPwned 등 외부 API 호출을 기록한다.

```sql
CREATE TYPE service_name AS ENUM ('emailrep', 'numverify', 'bin_database', 'haveibeenpwned');

CREATE TABLE external_service_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name service_name NOT NULL,
    request_data JSONB,
    response_data JSONB,
    response_time_ms INT NOT NULL,
    status_code INT,
    error_message TEXT,
    called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transaction_id UUID
);

CREATE INDEX idx_external_service_logs_service_name ON external_service_logs(service_name);
CREATE INDEX idx_external_service_logs_called_at ON external_service_logs(called_at);
CREATE INDEX idx_external_service_logs_transaction_id ON external_service_logs(transaction_id);
```

### 13. BlacklistEntry (블랙리스트)

차단할 디바이스, IP, 이메일, 카드 BIN, 배송지를 저장한다.

```sql
CREATE TYPE blacklist_entry_type AS ENUM ('device_id', 'ip_address', 'email', 'card_bin', 'shipping_address');

CREATE TABLE blacklist_entries (
    entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_type blacklist_entry_type NOT NULL,
    entry_value VARCHAR(255) NOT NULL,
    reason TEXT NOT NULL,
    added_by UUID,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(entry_type, entry_value)
);

CREATE INDEX idx_blacklist_entries_entry_type ON blacklist_entries(entry_type);
CREATE INDEX idx_blacklist_entries_is_active ON blacklist_entries(is_active);
CREATE INDEX idx_blacklist_entries_expires_at ON blacklist_entries(expires_at);
```

## 데이터베이스 관계도 (ERD)

```mermaid
erDiagram
    USERS ||--o{ BEHAVIOR_PATTERNS : has
    USERS ||--o{ RETRAINING_JOBS : creates

    TRANSACTIONS ||--|| NETWORK_ANALYSIS : has
    TRANSACTIONS ||--o{ RULE_EXECUTIONS : triggers
    TRANSACTIONS ||--|| ENSEMBLE_PREDICTIONS : produces
    TRANSACTIONS ||--o{ XAI_EXPLANATIONS : generates
    TRANSACTIONS ||--o{ EXTERNAL_SERVICE_LOGS : involves

    FRAUD_RULES ||--o{ RULE_EXECUTIONS : "executes in"

    ML_MODEL_VERSIONS ||--o{ ENSEMBLE_PREDICTIONS : uses
    ML_MODEL_VERSIONS ||--o{ FEATURE_IMPORTANCES : "analyzed in"
    ML_MODEL_VERSIONS ||--o{ RETRAINING_JOBS : produces

    DEVICE_FINGERPRINTS ||--o{ TRANSACTIONS : identifies
    BLACKLIST_ENTRIES ||--o{ TRANSACTIONS : blocks

    DEVICE_FINGERPRINTS {
        string device_id PK "SHA-256"
        string canvas_hash
        string webgl_hash
        string audio_hash
        int cpu_cores
        int memory_size
        string screen_resolution
        string timezone
        string language
        text user_agent
        timestamp created_at
        timestamp last_seen_at
        boolean blacklisted
        text blacklist_reason
    }

    BEHAVIOR_PATTERNS {
        uuid session_id PK
        uuid user_id FK
        jsonb mouse_movements
        jsonb keyboard_events
        jsonb clickstream
        int bot_score
        timestamp created_at
    }

    NETWORK_ANALYSIS {
        uuid transaction_id PK FK
        inet ip_address
        string geoip_country
        string geoip_city
        int asn
        string asn_organization
        boolean is_tor
        boolean is_vpn
        boolean is_proxy
        string dns_ptr_record
        boolean country_mismatch
        int risk_score
        timestamp created_at
    }

    FRAUD_RULES {
        uuid rule_id PK
        string rule_name
        enum rule_category
        text rule_description
        jsonb rule_logic
        int risk_score
        boolean is_active
        int priority
        timestamp created_at
        timestamp updated_at
        uuid created_by
    }

    RULE_EXECUTIONS {
        uuid execution_id PK
        uuid transaction_id FK
        uuid rule_id FK
        boolean matched
        timestamp triggered_at
        jsonb metadata
    }

    ML_MODEL_VERSIONS {
        uuid version_id PK
        enum model_name
        string model_type
        string version_number
        timestamp trained_at
        float accuracy
        float precision
        float recall
        float f1_score
        boolean is_active
        string model_path
        jsonb hyperparameters
        timestamp created_at
    }

    ENSEMBLE_PREDICTIONS {
        uuid prediction_id PK
        uuid transaction_id FK
        float rf_score
        float xgb_score
        float autoencoder_score
        float lstm_score
        float ensemble_score
        enum final_decision
        timestamp predicted_at
        uuid model_version_id FK
    }

    FEATURE_IMPORTANCES {
        uuid analysis_id PK
        uuid model_version_id FK
        string feature_name
        float importance_score
        int rank
        timestamp analyzed_at
    }

    XAI_EXPLANATIONS {
        uuid explanation_id PK
        uuid transaction_id FK
        jsonb shap_values
        jsonb lime_explanation
        jsonb top_risk_factors
        int explanation_time_ms
        timestamp generated_at
    }

    DATA_DRIFT_LOGS {
        uuid log_id PK
        timestamp detected_at
        string metric_name
        float baseline_value
        float current_value
        float drift_percentage
        boolean alert_triggered
        text alert_message
    }

    RETRAINING_JOBS {
        uuid job_id PK
        enum triggered_by
        string trigger_reason
        timestamp started_at
        timestamp completed_at
        enum status
        uuid new_model_version_id FK
        jsonb metrics
        text logs
        timestamp created_at
    }

    EXTERNAL_SERVICE_LOGS {
        uuid log_id PK
        enum service_name
        jsonb request_data
        jsonb response_data
        int response_time_ms
        int status_code
        text error_message
        timestamp called_at
        uuid transaction_id FK
    }

    BLACKLIST_ENTRIES {
        uuid entry_id PK
        enum entry_type
        string entry_value
        text reason
        uuid added_by
        timestamp added_at
        timestamp expires_at
        boolean is_active
    }
```

## 인덱싱 전략

### 쓰기 성능 최적화

- 높은 write throughput을 위해 BRIN (Block Range Index) 고려:
  ```sql
  CREATE INDEX idx_rule_executions_triggered_at_brin
  ON rule_executions USING BRIN (triggered_at);
  ```

### 조회 성능 최적화

1. **Time-series 쿼리**: `created_at`, `triggered_at` 등 시간 기반 조회는 B-tree 인덱스
2. **필터링**: `is_active`, `blacklisted` 등 boolean 컬럼은 partial index
3. **조인**: `transaction_id`, `user_id` 외래키는 필수 인덱스
4. **JSONB 검색**: 복잡한 JSONB 조회 시 GIN 인덱스 고려

## 성능 고려사항

### 파티셔닝

높은 쓰기 부하를 처리하기 위해 시간 기반 파티셔닝 권장:

```sql
-- rule_executions 테이블 월별 파티셔닝
CREATE TABLE rule_executions_2025_11 PARTITION OF rule_executions
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

### 데이터 보관 정책

- **DeviceFingerprint**: 2년 보관 (블랙리스트 항목 제외)
- **NetworkAnalysis**: 1년 보관
- **RuleExecution**: 6개월 보관 (감사 목적)
- **EnsemblePrediction**: 1년 보관
- **ExternalServiceLog**: 3개월 보관

## 마이그레이션 지침

```bash
# 1. 마이그레이션 파일 생성
alembic revision --autogenerate -m "003-advanced-fds: 고도화 엔티티 추가"

# 2. 데이터베이스 업그레이드
alembic upgrade head

# 3. 인덱스 생성 (별도 스크립트)
python scripts/create_indices.py

# 4. 초기 데이터 로드 (있는 경우)
python scripts/seed_fraud_rules.py
```

## 보안 및 규정 준수

1. **PCI-DSS**: 결제 정보(카드 번호)는 저장하지 않음. BIN만 저장.
2. **GDPR**: 개인정보 삭제 요청 시 관련 행 자동 삭제
3. **감사 로깅**: 모든 룰 추가/수정/삭제는 `created_by` 및 타임스탬프 기록
4. **데이터 암호화**: 민감 데이터(user_agent 등)는 저장 시 암호화 고려

## 관련 문서

- [spec.md](./spec.md) - 기능 명세
- [plan.md](./plan.md) - 구현 계획
- [contracts/fds-advanced-api.yaml](./contracts/fds-advanced-api.yaml) - API 계약
- [contracts/ml-ensemble-api.yaml](./contracts/ml-ensemble-api.yaml) - ML API 계약
