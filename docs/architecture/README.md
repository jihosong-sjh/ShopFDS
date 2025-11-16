# ShopFDS 아키텍처 문서

AI/ML 기반 이커머스 FDS 플랫폼의 시스템 아키텍처 문서입니다.

---

## 목차

1. [마이크로서비스 아키텍처 개요](#1-마이크로서비스-아키텍처-개요)
2. [FDS 평가 플로우](#2-fds-평가-플로우)
3. [데이터 흐름 다이어그램](#3-데이터-흐름-다이어그램)
4. [배포 아키텍처](#4-배포-아키텍처)
5. [데이터베이스 스키마](#5-데이터베이스-스키마)
6. [보안 아키텍처](#6-보안-아키텍처)

---

## 1. 마이크로서비스 아키텍처 개요

ShopFDS는 4개의 독립적인 마이크로서비스로 구성됩니다.

```mermaid
graph TB
    Client[웹 브라우저 / 모바일 앱]
    Gateway[Nginx API Gateway<br/>포트: 80/443]

    Ecommerce[이커머스 플랫폼<br/>포트: 8000]
    FDS[FDS 서비스<br/>포트: 8001]
    ML[ML 서비스<br/>포트: 8002]
    Admin[관리자 대시보드<br/>포트: 8003]

    PostgreSQL[(PostgreSQL<br/>관계형 DB)]
    Redis[(Redis<br/>캐시 / 세션)]
    MLflow[MLflow<br/>모델 레지스트리]

    Client -->|HTTPS| Gateway
    Gateway -->|/api/ecommerce/*| Ecommerce
    Gateway -->|/api/fds/*| FDS
    Gateway -->|/api/ml/*| ML
    Gateway -->|/api/admin/*| Admin

    Ecommerce -->|거래 평가 요청| FDS
    FDS -->|ML 예측 요청| ML
    Admin -->|통계 조회| Ecommerce
    Admin -->|거래 검토| FDS
    Admin -->|모델 관리| ML

    Ecommerce --> PostgreSQL
    FDS --> PostgreSQL
    ML --> PostgreSQL
    Admin --> PostgreSQL

    Ecommerce --> Redis
    FDS --> Redis
    ML --> MLflow

    style Gateway fill:#f9f,stroke:#333,stroke-width:4px
    style FDS fill:#ff9,stroke:#333,stroke-width:2px
    style ML fill:#9f9,stroke:#333,stroke-width:2px
```

### 서비스별 역할

| 서비스 | 포트 | 주요 기능 | 데이터베이스 |
|--------|------|-----------|--------------|
| **이커머스 플랫폼** | 8000 | 회원가입/로그인, 상품 조회, 장바구니, 주문/결제 | PostgreSQL + Redis |
| **FDS 서비스** | 8001 | 실시간 거래 위험도 평가 (룰 + ML + CTI) | PostgreSQL + Redis |
| **ML 서비스** | 8002 | 모델 학습, 평가, 배포 (카나리, 롤백) | PostgreSQL + MLflow |
| **관리자 대시보드** | 8003 | 실시간 모니터링, 검토 큐, 룰 관리, A/B 테스트 | PostgreSQL |

---

## 2. FDS 평가 플로우

주문 생성 시 FDS가 거래를 평가하고, 위험도에 따라 자동으로 대응합니다.

```mermaid
sequenceDiagram
    participant User as 고객
    participant Frontend as 프론트엔드
    participant Ecommerce as 이커머스 API
    participant FDS as FDS API
    participant ML as ML 서비스
    participant CTI as CTI DB
    participant Admin as 관리자 대시보드

    User->>Frontend: 주문 생성 요청
    Frontend->>Ecommerce: POST /v1/orders

    Note over Ecommerce: 주문 데이터 생성<br/>(Order, Payment)

    Ecommerce->>FDS: POST /v1/fds/evaluate<br/>(거래 위험도 평가)

    par 병렬 평가 (목표: 100ms 이내)
        FDS->>FDS: 룰 기반 탐지<br/>(Velocity, Threshold, Location)
        FDS->>ML: ML 모델 예측<br/>(Isolation Forest, LightGBM)
        FDS->>CTI: 악성 IP/카드 조회
    end

    Note over FDS: 위험 점수 산정<br/>(0-100점)

    alt 위험 점수 0-30 (Low)
        FDS-->>Ecommerce: decision: "approved"
        Ecommerce-->>Frontend: 주문 승인
        Frontend-->>User: 주문 완료
    else 위험 점수 40-70 (Medium)
        FDS-->>Ecommerce: decision: "additional_auth_required"
        Ecommerce-->>Frontend: OTP 요청
        Frontend-->>User: OTP 입력 요청
        User->>Frontend: OTP 입력
        Frontend->>Ecommerce: POST /v1/orders/{id}/verify-otp
        Ecommerce-->>Frontend: OTP 검증 성공
        Frontend-->>User: 주문 완료
    else 위험 점수 80-100 (High)
        FDS->>FDS: 수동 검토 큐 추가
        FDS->>Admin: 실시간 알림 전송
        FDS-->>Ecommerce: decision: "blocked"
        Ecommerce-->>Frontend: 거래 차단
        Frontend-->>User: 거래 차단 안내<br/>(고객센터 문의)
        Admin->>FDS: 수동 검토 후 승인/차단
    end
```

### 성능 목표

- **FDS 평가 시간**: P95 100ms 이내 (실제 달성: P95 85ms)
- **처리량**: 1,000 TPS 이상
- **엔진별 처리 시간**:
  - 룰 엔진: 15ms
  - ML 엔진: 45ms
  - CTI 엔진: 25ms (타임아웃: 50ms)

---

## 3. 데이터 흐름 다이어그램

사용자 행동 데이터가 수집되어 ML 학습에 활용되는 전체 데이터 파이프라인입니다.

```mermaid
graph LR
    User[고객 행동]
    Ecommerce[이커머스 플랫폼]
    BehaviorLog[(UserBehaviorLog<br/>TimescaleDB)]
    Transaction[(Transaction<br/>PostgreSQL)]
    FraudCase[(FraudCase<br/>ML 학습 데이터)]

    ML[ML 서비스]
    MLflow[(MLflow<br/>모델 저장소)]
    FDS[FDS 서비스]
    Admin[보안팀 검토]

    User -->|로그인, 상품 조회, 결제| Ecommerce
    Ecommerce -->|행동 로그 기록| BehaviorLog
    Ecommerce -->|거래 평가 요청| FDS
    FDS -->|거래 저장| Transaction
    FDS -->|차단 거래| Admin
    Admin -->|수동 검토<br/>(오탐/정탐)| FraudCase

    BehaviorLog -->|Feature Engineering| ML
    Transaction -->|Feature Engineering| ML
    FraudCase -->|Label 데이터| ML

    ML -->|모델 학습| ML
    ML -->|모델 저장| MLflow
    MLflow -->|모델 로드| FDS
    FDS -->|실시간 예측| Ecommerce

    style FraudCase fill:#f99,stroke:#333,stroke-width:2px
    style MLflow fill:#9f9,stroke:#333,stroke-width:2px
```

### 데이터 생명주기

1. **수집 단계**: 모든 사용자 행동과 거래 데이터 로깅
2. **저장 단계**: PostgreSQL (거래), TimescaleDB (행동 로그)
3. **특징 추출**: Feature Engineering (시계열 집계, 통계)
4. **학습 단계**: Isolation Forest, LightGBM 모델 학습 (주 1회)
5. **배포 단계**: 카나리 배포 (10% → 100%)
6. **예측 단계**: 실시간 사기 거래 예측

---

## 4. 배포 아키텍처

Kubernetes 기반 프로덕션 배포 아키텍처입니다.

```mermaid
graph TB
    subgraph "외부 사용자"
        Browser[웹 브라우저]
        Mobile[모바일 앱]
    end

    subgraph "클라우드 인프라 (AWS/GCP/Azure)"
        LB[로드 밸런서<br/>HTTPS 종료]

        subgraph "Kubernetes 클러스터"
            Ingress[Nginx Ingress Controller]

            subgraph "이커머스 Namespace"
                EcommercePod1[이커머스 Pod 1]
                EcommercePod2[이커머스 Pod 2]
                EcommercePod3[이커머스 Pod 3]
            end

            subgraph "FDS Namespace"
                FDSPod1[FDS Pod 1]
                FDSPod2[FDS Pod 2]
                FDSPod3[FDS Pod 3]
            end

            subgraph "ML Namespace"
                MLPod1[ML Pod 1]
            end

            subgraph "Admin Namespace"
                AdminPod1[Admin Pod 1]
            end

            subgraph "데이터 계층"
                PostgreSQL[(PostgreSQL<br/>StatefulSet)]
                Redis[(Redis<br/>StatefulSet)]
            end
        end

        subgraph "모니터링"
            Prometheus[Prometheus]
            Grafana[Grafana]
        end
    end

    Browser --> LB
    Mobile --> LB
    LB --> Ingress

    Ingress --> EcommercePod1
    Ingress --> EcommercePod2
    Ingress --> EcommercePod3
    Ingress --> FDSPod1
    Ingress --> FDSPod2
    Ingress --> FDSPod3
    Ingress --> MLPod1
    Ingress --> AdminPod1

    EcommercePod1 --> PostgreSQL
    EcommercePod1 --> Redis
    FDSPod1 --> PostgreSQL
    FDSPod1 --> Redis

    EcommercePod1 -.->|메트릭| Prometheus
    FDSPod1 -.->|메트릭| Prometheus
    Prometheus --> Grafana

    style LB fill:#f9f,stroke:#333,stroke-width:4px
    style PostgreSQL fill:#99f,stroke:#333,stroke-width:2px
    style Redis fill:#f99,stroke:#333,stroke-width:2px
```

### 인프라 구성

| 컴포넌트 | 수량 | 리소스 | 스케일링 |
|----------|------|--------|----------|
| **이커머스 Pod** | 3 | CPU 2코어, 메모리 4GB | HPA (최대 10개) |
| **FDS Pod** | 3 | CPU 2코어, 메모리 4GB | HPA (최대 10개) |
| **ML Pod** | 1 | CPU 4코어, 메모리 8GB | 수동 (학습 시 증가) |
| **Admin Pod** | 1 | CPU 1코어, 메모리 2GB | 고정 |
| **PostgreSQL** | 1 (Primary) + 2 (Replica) | CPU 4코어, 메모리 16GB | 읽기 복제본 |
| **Redis** | 1 (Master) + 2 (Replica) | CPU 2코어, 메모리 8GB | Sentinel 모드 |

### CI/CD 파이프라인

```mermaid
graph LR
    Dev[개발자 커밋]
    GitHub[GitHub Actions]
    Test[테스트<br/>Black, Ruff, pytest]
    Build[Docker 빌드]
    Registry[Container Registry]
    Deploy[Kubernetes 배포]
    Smoke[Smoke 테스트]
    Rollback[롤백]

    Dev --> GitHub
    GitHub --> Test
    Test -->|성공| Build
    Test -->|실패| Dev
    Build --> Registry
    Registry --> Deploy
    Deploy --> Smoke
    Smoke -->|성공| Deploy
    Smoke -->|실패| Rollback

    style Test fill:#9f9,stroke:#333,stroke-width:2px
    style Rollback fill:#f99,stroke:#333,stroke-width:2px
```

**배포 전략**: Blue-Green 배포 (무중단 배포)

---

## 5. 데이터베이스 스키마

### 주요 엔티티 관계도 (ERD)

```mermaid
erDiagram
    User ||--o{ Order : "주문"
    User ||--|| Cart : "장바구니"
    Cart ||--o{ CartItem : "포함"
    Order ||--o{ OrderItem : "포함"
    Order ||--|| Payment : "결제"
    Product ||--o{ CartItem : "참조"
    Product ||--o{ OrderItem : "참조"

    Order ||--|| Transaction : "FDS 평가"
    Transaction ||--o{ RiskFactor : "위험 요인"
    Transaction ||--o| FraudCase : "사기 케이스"
    Transaction ||--o| ReviewQueue : "검토 큐"

    User {
        uuid id PK
        string email UK
        string name
        string password_hash
        string role
        datetime created_at
    }

    Product {
        uuid id PK
        string name
        decimal price
        int stock
        string category
        datetime created_at
    }

    Order {
        uuid id PK
        uuid user_id FK
        string order_number UK
        decimal total_amount
        string status
        datetime created_at
    }

    Transaction {
        uuid id PK
        uuid order_id FK
        int risk_score
        string risk_level
        string decision
        datetime created_at
    }
```

상세한 데이터 모델은 [data-model.md](../../specs/001-ecommerce-fds-platform/data-model.md)를 참조하세요.

---

## 6. 보안 아키텍처

### 인증 및 권한 관리 (RBAC)

```mermaid
graph TB
    User[사용자]
    Login[로그인]
    JWT[JWT 토큰 발급]

    API[API 요청]
    AuthMiddleware[인증 미들웨어]
    RBACMiddleware[권한 체크 미들웨어]

    Resource[보호된 리소스]

    User --> Login
    Login --> JWT
    User --> API
    API --> AuthMiddleware
    AuthMiddleware -->|토큰 검증| RBACMiddleware
    RBACMiddleware -->|권한 있음| Resource
    RBACMiddleware -->|권한 없음| Forbidden[403 Forbidden]

    style AuthMiddleware fill:#9f9,stroke:#333,stroke-width:2px
    style RBACMiddleware fill:#ff9,stroke:#333,stroke-width:2px
```

### 역할 및 권한

| 역할 | 권한 |
|------|------|
| `CUSTOMER` | 주문 생성, 본인 주문 조회, 장바구니 관리 |
| `ADMIN` | 상품 관리, 전체 주문 조회, 회원 관리 |
| `SECURITY_ANALYST` | 거래 조회, 대시보드 조회 |
| `SECURITY_MANAGER` | 검토 승인/차단, 룰 관리, A/B 테스트 |

### 데이터 보안

- **결제 정보**: PCI-DSS 준수, 카드 번호 토큰화
- **비밀번호**: bcrypt 해싱 (cost factor: 12)
- **개인정보**: AES-256 암호화 저장
- **통신**: HTTPS/TLS 1.3 암호화
- **로깅**: 민감 데이터 자동 마스킹 (SecureLogger)

### Rate Limiting

Nginx + Redis 기반 API Rate Limiting:

| API 타입 | 제한 |
|----------|------|
| 인증 API | 10 req/min |
| 일반 API | 60 req/min |
| 관리자 API | 100 req/min |

---

## 참고 문서

- [API 문서](../api/)
- [배포 가이드](../deployment-infrastructure-summary.md)
- [성능 최적화](../performance-optimization.md)
- [보안 강화](../security-hardening.md)

---

Copyright © 2025 ShopFDS Team.
