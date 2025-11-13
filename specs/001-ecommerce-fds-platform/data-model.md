# 데이터 모델: AI/ML 기반 이커머스 FDS 플랫폼

**Date**: 2025-11-13
**Database**: PostgreSQL 15+ (Primary) + Redis 7+ (Cache)

## 개요

본 문서는 이커머스 플랫폼과 FDS 시스템의 모든 엔티티, 관계, 검증 규칙, 상태 전이를 정의합니다.

---

## 1. 이커머스 플랫폼 엔티티

### 1.1 User (사용자)

**목적**: 플랫폼에 가입한 고객 및 관리자 계정

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 이메일 (로그인 ID) |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 해시된 비밀번호 |
| name | VARCHAR(100) | NOT NULL | 사용자 이름 |
| role | ENUM('customer', 'admin', 'security_team') | NOT NULL, DEFAULT 'customer' | 사용자 역할 |
| status | ENUM('active', 'suspended', 'deleted') | NOT NULL, DEFAULT 'active' | 계정 상태 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 가입 일시 |
| last_login_at | TIMESTAMP | NULLABLE | 마지막 로그인 일시 |
| failed_login_attempts | INTEGER | NOT NULL, DEFAULT 0 | 연속 로그인 실패 횟수 (3회 초과 시 일시 잠금) |

**검증 규칙**:
- `email`: RFC 5322 형식, 중복 불가
- `password`: 최소 8자, 대소문자 + 숫자 + 특수문자 포함
- `failed_login_attempts`: 3회 초과 시 계정 일시 잠금 (15분)

**관계**:
- User 1 ↔ N Orders
- User 1 ↔ 1 Cart
- User 1 ↔ N UserBehaviorLogs

---

### 1.2 Product (상품)

**목적**: 판매 중인 상품 정보

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| name | VARCHAR(255) | NOT NULL | 상품명 |
| description | TEXT | NULLABLE | 상품 설명 |
| price | DECIMAL(10, 2) | NOT NULL, CHECK (price >= 0) | 가격 (단위: 원) |
| stock_quantity | INTEGER | NOT NULL, CHECK (stock_quantity >= 0) | 재고 수량 |
| category | VARCHAR(100) | NOT NULL, INDEX | 카테고리 (예: 전자제품, 의류, 식품) |
| image_url | VARCHAR(500) | NULLABLE | 상품 이미지 URL |
| status | ENUM('available', 'out_of_stock', 'discontinued') | NOT NULL, DEFAULT 'available' | 상품 상태 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 등록 일시 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 수정 일시 |

**검증 규칙**:
- `price`: 0 이상
- `stock_quantity`: 0 이상
- `status`: `stock_quantity == 0`일 때 자동으로 'out_of_stock'으로 변경

**상태 전이**:
```
available ↔ out_of_stock  (재고 수량에 따라 자동 전환)
   ↓
discontinued  (관리자가 판매 중단 시)
```

---

### 1.3 Cart (장바구니)

**목적**: 사용자별 구매 예정 상품 목록

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| user_id | UUID | FOREIGN KEY (users.id), UNIQUE | 사용자 ID (1:1 관계) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 생성 일시 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 수정 일시 |

**관계**:
- Cart 1 ↔ N CartItems

---

### 1.4 CartItem (장바구니 항목)

**목적**: 장바구니에 담긴 개별 상품

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| cart_id | UUID | FOREIGN KEY (carts.id), NOT NULL | 장바구니 ID |
| product_id | UUID | FOREIGN KEY (products.id), NOT NULL | 상품 ID |
| quantity | INTEGER | NOT NULL, CHECK (quantity > 0) | 수량 |
| added_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 추가 일시 |

**검증 규칙**:
- `quantity`: 1 이상, `product.stock_quantity` 이하
- 동일 `cart_id` + `product_id` 조합은 중복 불가 (UNIQUE 제약)

**계산 필드**:
- `subtotal = product.price * quantity` (실시간 계산)

---

### 1.5 Order (주문)

**목적**: 고객의 구매 주문

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| order_number | VARCHAR(20) | UNIQUE, NOT NULL | 주문 번호 (예: ORD-20251113-001) |
| user_id | UUID | FOREIGN KEY (users.id), NOT NULL | 사용자 ID |
| total_amount | DECIMAL(10, 2) | NOT NULL, CHECK (total_amount > 0) | 총 금액 |
| status | ENUM | NOT NULL, DEFAULT 'pending' | 주문 상태 (아래 참조) |
| shipping_name | VARCHAR(100) | NOT NULL | 수령인 이름 |
| shipping_address | TEXT | NOT NULL | 배송 주소 |
| shipping_phone | VARCHAR(20) | NOT NULL | 수령인 연락처 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 주문 생성 일시 |
| paid_at | TIMESTAMP | NULLABLE | 결제 완료 일시 |
| shipped_at | TIMESTAMP | NULLABLE | 배송 시작 일시 |
| delivered_at | TIMESTAMP | NULLABLE | 배송 완료 일시 |
| cancelled_at | TIMESTAMP | NULLABLE | 취소 일시 |

**주문 상태 (status ENUM)**:
- `pending`: 주문 접수 (결제 대기)
- `paid`: 결제 완료 (배송 준비)
- `preparing`: 배송 준비 중
- `shipped`: 배송 중
- `delivered`: 배송 완료
- `cancelled`: 취소됨
- `refunded`: 환불 완료

**상태 전이**:
```
pending → paid → preparing → shipped → delivered
   ↓         ↓
cancelled  refunded
```

**검증 규칙**:
- `order_number`: 형식 `ORD-YYYYMMDD-###` (일련번호)
- `shipping_phone`: 한국 전화번호 형식 (010-####-####)

**관계**:
- Order 1 ↔ N OrderItems
- Order 1 ↔ 1 Payment
- Order 1 ↔ 1 Transaction (FDS)

---

### 1.6 OrderItem (주문 항목)

**목적**: 주문에 포함된 개별 상품 (주문 시점의 가격 기록)

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| order_id | UUID | FOREIGN KEY (orders.id), NOT NULL | 주문 ID |
| product_id | UUID | FOREIGN KEY (products.id), NOT NULL | 상품 ID |
| quantity | INTEGER | NOT NULL, CHECK (quantity > 0) | 수량 |
| unit_price | DECIMAL(10, 2) | NOT NULL | 주문 시점 단가 (상품 가격 변동 대비) |

**계산 필드**:
- `subtotal = unit_price * quantity`

---

### 1.7 Payment (결제)

**목적**: 주문에 대한 결제 정보

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| order_id | UUID | FOREIGN KEY (orders.id), UNIQUE | 주문 ID (1:1 관계) |
| payment_method | ENUM('credit_card') | NOT NULL | 결제 수단 (초기에는 신용카드만) |
| amount | DECIMAL(10, 2) | NOT NULL | 결제 금액 |
| status | ENUM('pending', 'completed', 'failed', 'refunded') | NOT NULL, DEFAULT 'pending' | 결제 상태 |
| card_token | VARCHAR(255) | NOT NULL | 토큰화된 카드 정보 (PCI-DSS 준수) |
| card_last_four | CHAR(4) | NOT NULL | 카드 마지막 4자리 (표시용) |
| transaction_id | VARCHAR(100) | NULLABLE | 결제 게이트웨이 거래 ID |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 결제 시도 일시 |
| completed_at | TIMESTAMP | NULLABLE | 결제 완료 일시 |
| failed_reason | TEXT | NULLABLE | 결제 실패 사유 |

**검증 규칙**:
- `amount`: `order.total_amount`와 일치해야 함
- `card_token`: 실제 카드 번호는 저장 금지 (토큰만 저장)

**상태 전이**:
```
pending → completed
   ↓         ↓
failed    refunded
```

---

## 2. FDS 엔티티

### 2.1 Transaction (거래)

**목적**: FDS가 평가하는 개별 거래 이벤트

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| user_id | UUID | FOREIGN KEY (users.id), NOT NULL | 사용자 ID |
| order_id | UUID | FOREIGN KEY (orders.id), UNIQUE | 주문 ID |
| amount | DECIMAL(10, 2) | NOT NULL | 거래 금액 |
| ip_address | INET | NOT NULL, INDEX | 접속 IP 주소 |
| user_agent | TEXT | NOT NULL | User-Agent 헤더 (디바이스 정보) |
| device_type | ENUM('desktop', 'mobile', 'tablet', 'unknown') | NOT NULL | 디바이스 유형 |
| geolocation | JSONB | NULLABLE | IP 기반 지리적 위치 (country, city, lat, lon) |
| risk_score | INTEGER | NOT NULL, CHECK (risk_score BETWEEN 0 AND 100) | 위험 점수 (0-100) |
| risk_level | ENUM('low', 'medium', 'high') | NOT NULL | 위험 수준 |
| evaluation_status | ENUM('evaluating', 'approved', 'blocked', 'manual_review') | NOT NULL, DEFAULT 'evaluating' | 평가 상태 |
| evaluation_time_ms | INTEGER | NOT NULL | FDS 평가 소요 시간 (ms) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 거래 발생 일시 |
| evaluated_at | TIMESTAMP | NULLABLE | 평가 완료 일시 |

**위험 수준 (risk_level) 자동 분류**:
- `low`: risk_score 0-30 → 자동 승인
- `medium`: risk_score 40-70 → 추가 인증 요구
- `high`: risk_score 80-100 → 자동 차단

**검증 규칙**:
- `evaluation_time_ms`: 목표 100ms 이내 (성능 모니터링 지표)
- `geolocation`: PostGIS 확장 사용 시 GEOGRAPHY 타입으로 변경 가능

**관계**:
- Transaction 1 ↔ N RiskFactors
- Transaction 1 ↔ 0..1 ReviewQueue

---

### 2.2 RiskFactor (위험 요인)

**목적**: 거래의 위험 점수 산정에 기여한 개별 요인

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| transaction_id | UUID | FOREIGN KEY (transactions.id), NOT NULL | 거래 ID |
| factor_type | VARCHAR(50) | NOT NULL | 요인 유형 (아래 참조) |
| factor_score | INTEGER | NOT NULL, CHECK (factor_score BETWEEN 0 AND 100) | 요인별 위험 점수 |
| description | TEXT | NOT NULL | 요인 설명 (예: "동일 IP에서 5분 내 3회 거래") |
| metadata | JSONB | NULLABLE | 추가 메타데이터 (룰 ID, ML 모델 feature importance 등) |

**요인 유형 (factor_type)**:
- `velocity_check`: 단시간 내 반복 거래
- `amount_threshold`: 비정상적 고액 거래
- `location_mismatch`: 지역 불일치 (등록 주소 vs IP 위치)
- `suspicious_ip`: 악성 IP (CTI 블랙리스트)
- `suspicious_time`: 비정상 시간대 거래
- `ml_anomaly`: ML 모델이 탐지한 이상 패턴
- `stolen_card`: 도난 카드 정보 (CTI)

---

### 2.3 DetectionRule (탐지 룰)

**목적**: FDS가 사용하는 룰 기반 탐지 규칙

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| name | VARCHAR(255) | NOT NULL | 룰 이름 (예: "5분 내 3회 거래 차단") |
| rule_type | VARCHAR(50) | NOT NULL | 룰 유형 (velocity, threshold, blacklist 등) |
| condition | JSONB | NOT NULL | 룰 조건 (JSON 형식) |
| risk_score_weight | INTEGER | NOT NULL, CHECK (risk_score_weight BETWEEN 0 AND 100) | 위험 점수 가중치 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 활성화 여부 |
| priority | INTEGER | NOT NULL, DEFAULT 0 | 우선순위 (높을수록 먼저 평가) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 생성 일시 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 수정 일시 |
| created_by | UUID | FOREIGN KEY (users.id), NULLABLE | 생성자 (보안팀 사용자 ID) |

**조건 예시 (condition JSONB)**:
```json
{
  "type": "velocity",
  "window_seconds": 300,
  "max_transactions": 3,
  "scope": "ip_address"
}
```

**검증 규칙**:
- `condition`: JSON Schema 검증 필수
- 보안팀만 생성/수정 가능 (role='security_team')

---

### 2.4 FraudCase (사기 케이스)

**목적**: 확정된 사기 거래 사례 (ML 학습 데이터)

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| transaction_id | UUID | FOREIGN KEY (transactions.id), UNIQUE | 거래 ID |
| user_id | UUID | FOREIGN KEY (users.id), NOT NULL | 사용자 ID |
| fraud_type | ENUM | NOT NULL | 사기 유형 (아래 참조) |
| detected_at | TIMESTAMP | NOT NULL | 탐지 일시 |
| confirmed_at | TIMESTAMP | NULLABLE | 확정 일시 (수동 검토 완료 후) |
| loss_amount | DECIMAL(10, 2) | NOT NULL | 손실 금액 |
| status | ENUM('suspected', 'confirmed', 'false_positive') | NOT NULL, DEFAULT 'suspected' | 케이스 상태 |
| notes | TEXT | NULLABLE | 보안팀 메모 |

**사기 유형 (fraud_type)**:
- `card_theft`: 카드 도용
- `account_takeover`: 계정 탈취
- `refund_fraud`: 환불 사기
- `identity_theft`: 신원 도용
- `promo_abuse`: 프로모션 악용

**상태 전이**:
```
suspected → confirmed  (보안팀 검토 후 확정)
   ↓
false_positive  (오탐으로 판단)
```

---

### 2.5 ReviewQueue (검토 큐)

**목적**: 수동 검토가 필요한 차단된 거래

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| transaction_id | UUID | FOREIGN KEY (transactions.id), UNIQUE | 거래 ID |
| assigned_to | UUID | FOREIGN KEY (users.id), NULLABLE | 검토 담당자 ID |
| status | ENUM('pending', 'in_review', 'completed') | NOT NULL, DEFAULT 'pending' | 검토 상태 |
| decision | ENUM('approve', 'block', 'escalate') | NULLABLE | 검토 결과 |
| review_notes | TEXT | NULLABLE | 검토 메모 |
| added_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 큐 추가 일시 |
| reviewed_at | TIMESTAMP | NULLABLE | 검토 완료 일시 |

**검증 규칙**:
- `assigned_to`: role='security_team'인 사용자만 할당 가능
- `reviewed_at - added_at`: 평균 10분 이내 목표

---

### 2.6 MLModel (ML 모델)

**목적**: FDS에서 사용하는 기계학습 모델 메타데이터

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| name | VARCHAR(255) | NOT NULL | 모델 이름 (예: "IsolationForest-v1.2") |
| version | VARCHAR(50) | NOT NULL | 버전 (예: "1.2.0") |
| model_type | VARCHAR(50) | NOT NULL | 모델 유형 (isolation_forest, random_forest, lightgbm) |
| training_data_start | DATE | NOT NULL | 학습 데이터 시작일 |
| training_data_end | DATE | NOT NULL | 학습 데이터 종료일 |
| trained_at | TIMESTAMP | NOT NULL | 학습 완료 일시 |
| accuracy | DECIMAL(5, 4) | NULLABLE | 정확도 (0-1) |
| precision | DECIMAL(5, 4) | NULLABLE | 정밀도 (0-1) |
| recall | DECIMAL(5, 4) | NULLABLE | 재현율 (0-1) |
| f1_score | DECIMAL(5, 4) | NULLABLE | F1 스코어 (0-1) |
| deployment_status | ENUM('development', 'staging', 'production', 'retired') | NOT NULL | 배포 상태 |
| deployed_at | TIMESTAMP | NULLABLE | 프로덕션 배포 일시 |
| model_path | VARCHAR(500) | NOT NULL | 모델 파일 경로 (S3, 로컬 등) |

**검증 규칙**:
- `version`: Semantic Versioning (MAJOR.MINOR.PATCH)
- `deployment_status='production'`인 모델은 1개만 존재 가능

---

### 2.7 UserBehaviorLog (사용자 행동 로그)

**목적**: FDS 학습을 위한 사용자 행동 데이터 (TimescaleDB 활용)

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | BIGSERIAL | PRIMARY KEY | 고유 식별자 (자동 증가) |
| user_id | UUID | FOREIGN KEY (users.id), NOT NULL, INDEX | 사용자 ID |
| session_id | UUID | NOT NULL, INDEX | 세션 ID |
| action_type | VARCHAR(50) | NOT NULL | 액션 유형 (login, view_product, add_to_cart, checkout 등) |
| action_timestamp | TIMESTAMP | NOT NULL, INDEX | 액션 발생 일시 |
| ip_address | INET | NOT NULL | 접속 IP |
| user_agent | TEXT | NOT NULL | User-Agent |
| context | JSONB | NULLABLE | 추가 컨텍스트 (상품 ID, 금액 등) |

**인덱싱**:
- `(user_id, action_timestamp DESC)`: 사용자별 최근 행동 조회
- `(action_type, action_timestamp DESC)`: 액션별 시계열 분석
- `session_id`: 세션별 행동 패턴 분석

**TimescaleDB 하이퍼테이블**:
```sql
SELECT create_hypertable('user_behavior_logs', 'action_timestamp');
```

---

### 2.8 ThreatIntelligence (위협 인텔리전스)

**목적**: 외부 CTI 및 자체 블랙리스트

| 필드명 | 타입 | 제약 조건 | 설명 |
|--------|------|-----------|------|
| id | UUID | PRIMARY KEY | 고유 식별자 |
| threat_type | ENUM('ip', 'email_domain', 'card_bin') | NOT NULL | 위협 유형 |
| value | VARCHAR(255) | NOT NULL, INDEX | 위협 값 (IP 주소, 이메일 도메인, 카드 BIN) |
| threat_level | ENUM('low', 'medium', 'high') | NOT NULL | 위협 수준 |
| source | VARCHAR(100) | NOT NULL | 출처 (AbuseIPDB, internal 등) |
| description | TEXT | NULLABLE | 설명 |
| registered_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 등록 일시 |
| expires_at | TIMESTAMP | NULLABLE | 만료 일시 (NULL이면 영구) |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 활성화 여부 |

**인덱싱**:
- `(threat_type, value)`: UNIQUE 제약 + HASH 인덱스로 O(1) 조회
- `(expires_at)`: 만료된 항목 자동 삭제용

**Redis 캐싱**:
```python
# Redis Key: threat:{type}:{value}
# TTL: 1시간 (AbuseIPDB API 호출 최소화)
redis.setex(f"threat:ip:{ip_address}", 3600, threat_level)
```

---

## 3. 데이터베이스 인덱스 전략

### 성능 최적화를 위한 주요 인덱스

```sql
-- Users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);

-- Products
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_status ON products(status);

-- Orders
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

-- Transactions
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_ip_address ON transactions(ip_address);
CREATE INDEX idx_transactions_risk_level ON transactions(risk_level);
CREATE INDEX idx_transactions_created_at ON transactions(created_at DESC);

-- RiskFactors
CREATE INDEX idx_risk_factors_transaction_id ON risk_factors(transaction_id);
CREATE INDEX idx_risk_factors_factor_type ON risk_factors(factor_type);

-- ThreatIntelligence
CREATE UNIQUE INDEX idx_threat_intel_type_value ON threat_intelligence(threat_type, value);
CREATE INDEX idx_threat_intel_expires_at ON threat_intelligence(expires_at);

-- UserBehaviorLogs (TimescaleDB)
CREATE INDEX idx_user_behavior_user_action_time ON user_behavior_logs(user_id, action_timestamp DESC);
CREATE INDEX idx_user_behavior_session ON user_behavior_logs(session_id);
```

---

## 4. 데이터 보존 정책

| 테이블 | 보존 기간 | 정책 |
|--------|----------|------|
| `orders`, `payments` | 3년 | 법적 요구사항 (전자상거래법) |
| `transactions`, `risk_factors` | 3년 | 사기 패턴 분석용 |
| `user_behavior_logs` | 1년 | ML 학습용, 이후 집계 데이터만 보존 |
| `fraud_cases` | 영구 | 사기 사례 학습 데이터 |
| `threat_intelligence` | `expires_at` 기준 | 만료된 항목 자동 삭제 (일 1회 배치) |
| `review_queue` | 6개월 | 검토 완료 후 아카이브 |

---

## 5. 데이터 마이그레이션 전략

**도구**: Alembic (SQLAlchemy)

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "Add risk_score column to transactions"

# 마이그레이션 적용
alembic upgrade head

# 롤백
alembic downgrade -1
```

**마이그레이션 원칙**:
1. **하위 호환성**: 기존 데이터를 손실하지 않음
2. **점진적 배포**: 컬럼 추가 → 데이터 마이그레이션 → 구 컬럼 삭제
3. **백업 필수**: 프로덕션 배포 전 전체 백업

---

## 다음 단계

✅ 데이터 모델 정의 완료
→ 다음: contracts/ 디렉토리에 API 계약 (OpenAPI) 생성
