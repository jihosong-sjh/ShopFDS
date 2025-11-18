# Tasks: Production Infrastructure

**Feature Branch**: `002-production-infra`
**Created**: 2025-11-17
**Status**: Ready for Implementation

---

## Summary

총 작업 수: 68개
- Phase 1 (Setup): 4개
- Phase 2 (Foundational): 6개
- Phase 3 (US1 - PostgreSQL Read Replica): 10개
- Phase 4 (US2 - Redis Cluster Blacklist): 12개
- Phase 5 (US3 - Celery + RabbitMQ): 13개
- Phase 6 (US4 - ELK Stack + Prometheus): 15개
- Phase 7 (US5 - Development Automation): 6개
- Phase 8 (Polish): 2개

병렬 실행 가능한 작업: 28개 (41%)

**MVP 범위 (US1~US2)**: Phase 1~4, 총 32개 작업 (예상 2주)
**Full 범위 (US1~US5)**: 전체 68개 작업 (예상 4주)

---

## Phase 1: Setup - 프로젝트 초기화 및 디렉토리 구조

**목표**: 인프라 코드 구조 생성 및 기본 설정 파일 배치

### 디렉토리 구조 생성

- [X] T001 [P] infrastructure/docker/postgres/ 디렉토리 생성
- [X] T002 [P] infrastructure/docker/redis/ 디렉토리 생성
- [X] T003 [P] infrastructure/monitoring/ 하위 디렉토리 생성 (prometheus/alerts/, alertmanager/, logstash/pipeline/, kibana/dashboards/)
- [X] T004 [P] infrastructure/scripts/ 및 tests/infrastructure/ 디렉토리 생성

---

## Phase 2: Foundational - 공통 인프라 확장

**목표**: 기존 Docker Compose 확장 및 네트워크 설정

### Docker Compose 기본 확장

- [X] T005 [P] infrastructure/docker/docker-compose.yml에 RabbitMQ 서비스 추가
- [X] T006 [P] infrastructure/docker/docker-compose.monitoring.yml 생성 (Prometheus, Grafana, Alertmanager)
- [X] T007 infrastructure/docker/docker-compose.yml에 Elasticsearch, Logstash, Kibana 서비스 추가 (T006 의존)
- [X] T008 [P] infrastructure/docker/.env.example 업데이트 (Redis Cluster, RabbitMQ, ELK 환경 변수)
- [X] T009 [P] infrastructure/docker/docker-compose.yml에 내부 네트워크 설정 추가 (shopfds-internal, shopfds-monitoring)
- [X] T010 모든 Docker Compose 파일 검증: docker-compose config (T005~T009 의존)

**검증 포인트**: docker-compose config 오류 없이 실행, 모든 서비스 네트워크 연결 가능

---

## Phase 3: User Story 1 - PostgreSQL Read Replica (Priority: P1)

**목표**: 고가용성 데이터베이스 운영 - Master-Replica 복제 구성

**독립 테스트**: PostgreSQL 마스터-슬레이브 복제가 구성된 상태에서 읽기 전용 쿼리가 Replica로 라우팅되고, 쓰기 쿼리는 Master로 라우팅되는지 확인합니다. Master 중단 시 Replica가 읽기 요청을 계속 처리하는지 검증합니다.

### PostgreSQL 복제 설정

- [X] T011 [P] [US1] infrastructure/docker/postgres/master.conf 생성 (스트리밍 복제 활성화, wal_level=replica, max_wal_senders=5)
- [X] T012 [P] [US1] infrastructure/docker/postgres/replica.conf 생성 (hot_standby=on, primary_conninfo)
- [X] T013 [US1] infrastructure/docker/docker-compose.yml에 postgres-replica 서비스 추가 (T011~T012 의존)
- [X] T014 [P] [US1] infrastructure/scripts/init-postgres-replication.sh 생성 (replicator 사용자 생성, pg_basebackup)

### 애플리케이션 연결 풀 수정

- [X] T015 [US1] services/ecommerce/backend/src/db/connection.py 수정: 읽기/쓰기 연결 풀 분리, get_read_db()/get_write_db() 함수 추가
- [X] T016 [US1] services/fds/src/db/connection.py 수정: 읽기/쓰기 연결 풀 분리 (T015와 동일 패턴)
- [X] T017 [US1] services/ml-service/src/db/connection.py 수정: 읽기/쓰기 연결 풀 분리 (T015와 동일 패턴)
- [X] T018 [US1] services/admin-dashboard/backend/src/db/connection.py 수정: 읽기/쓰기 연결 풀 분리 (T015와 동일 패턴)

### 복제 모니터링

- [X] T019 [US1] Alembic 마이그레이션 생성: ReplicationStatus 모델 추가 in services/ecommerce/backend/alembic/versions/ (T015 의존)
- [X] T020 [US1] services/ecommerce/backend/src/utils/replication_monitor.py 생성: check_replication_lag() 함수, pg_stat_replication 쿼리

### 통합 테스트

- [X] T021 [US1] tests/infrastructure/test_postgres_replication.py 생성: 읽기/쓰기 라우팅, 복제 지연, 폴백 테스트 (T015~T020 의존)

**검증 포인트**:
1. 읽기 전용 연결 풀을 통해 Replica에서 데이터 조회
2. Master에 새 주문 생성 후 10초 내 Replica에 복제 확인
3. 주문 생성 API 호출 시 Master에 쓰기 작업 수행
4. Read Replica 다운 시 Master로 자동 폴백

---

## Phase 4: User Story 2 - Redis Cluster 블랙리스트 관리 (Priority: P1)

**목표**: Redis Cluster 기반 캐싱 및 실시간 블랙리스트 관리

**독립 테스트**: 6노드 Redis Cluster가 구성된 상태에서 블랙리스트 IP를 추가하고, 해당 IP로 주문 요청 시 FDS가 자동으로 거부하는지 확인합니다. 클러스터 노드 하나가 다운되어도 서비스가 계속 작동하는지 검증합니다.

### Redis Cluster 구성

- [X] T022 [P] [US2] infrastructure/docker/redis/redis-cluster.conf 생성 (cluster-enabled yes, cluster-config-file, cluster-node-timeout 5000)
- [X] T023 [P] [US2] infrastructure/scripts/init-redis-cluster.sh 생성 (6노드 클러스터 생성, --cluster-replicas 1)
- [X] T024 [US2] infrastructure/docker/docker-compose.yml에 redis-node-1~6 서비스 추가 (포트 7000~7005) (T022 의존)
- [X] T025 [US2] infrastructure/docker/docker-compose.yml에서 기존 단일 Redis 서비스 제거, redis-cluster 네트워크 추가 (T024 의존)

### FDS 블랙리스트 관리

- [X] T026 [P] [US2] services/fds/src/cache/blacklist.py 생성: BlacklistManager 클래스 (add_entry, check_entry, remove_entry, list_entries)
- [X] T027 [US2] services/fds/src/engines/evaluation_engine.py 수정: 블랙리스트 체크 로직 추가 (check_ip, check_card_bin, check_email_domain) (T026 의존)
- [X] T028 [US2] services/fds/src/db/connection.py 수정: Redis Cluster 클라이언트 연결 (redis.cluster.RedisCluster) (T026 의존)

### Admin Dashboard 블랙리스트 API

- [X] T029 [P] [US2] services/admin-dashboard/backend/src/api/blacklist.py 생성: POST /v1/admin/blacklist (추가), GET /v1/admin/blacklist (목록), DELETE /v1/admin/blacklist/{entry_id} (삭제), PATCH /v1/admin/blacklist/{entry_id}/ttl (TTL 수정)
- [X] T030 [US2] services/admin-dashboard/backend/src/main.py 수정: 블랙리스트 라우터 등록 (T029 의존)
- [X] T031 [P] [US2] Alembic 마이그레이션 생성: BlacklistEntry 모델 추가 in services/fds/alembic/versions/ (로그용, Redis는 스키마 없음)

### 세션 스토어

- [X] T032 [US2] services/ecommerce/backend/src/middleware/session.py 수정: Redis Cluster 세션 스토어 통합 (TTL 30분) (T027 의존)

### 통합 테스트

- [X] T033 [US2] tests/infrastructure/test_redis_cluster.py 생성: 클러스터 생성, 샤딩, 페일오버, 블랙리스트 CRUD 테스트 (T026~T032 의존)

**검증 포인트**:
1. 블랙리스트 IP 추가 시 클러스터 전체에 자동 샤딩
2. 블랙리스트 IP로부터 주문 요청 시 FDS가 "high" 위험도로 평가
3. 블랙리스트 이메일 TTL 7일 후 자동 제거
4. Redis 노드 1개 다운 시 다른 노드로 자동 페일오버
5. 세션 30분 후 자동 만료

---

## Phase 5: User Story 3 - 비동기 작업 처리 (Priority: P2)

**목표**: Celery + RabbitMQ를 사용한 이메일, 배치 평가, 리포트 생성 비동기 처리

**독립 테스트**: 주문 생성 API 호출 후 즉시 응답을 받고, 백그라운드에서 Celery 워커가 이메일 발송 작업을 처리하는지 확인합니다. Flower 대시보드에서 작업 상태를 모니터링할 수 있는지 검증합니다.

### Celery 설정

- [X] T034 [P] [US3] services/ecommerce/backend/celeryconfig.py 생성 (broker_url=RabbitMQ, result_backend=Redis, task_routes)
- [X] T035 [P] [US3] services/fds/celeryconfig.py 생성 (T034와 동일 패턴)
- [X] T036 [P] [US3] infrastructure/docker/docker-compose.yml에 celery-worker, celery-beat, flower 서비스 추가 (T005 RabbitMQ 의존)

### Ecommerce 비동기 작업

- [X] T037 [P] [US3] services/ecommerce/backend/src/tasks/email.py 생성: send_order_confirmation_email(), send_password_reset_email() Celery 작업
- [X] T038 [P] [US3] services/ecommerce/backend/src/tasks/reports.py 생성: generate_sales_report() Celery 작업
- [X] T039 [P] [US3] services/ecommerce/backend/src/tasks/cleanup.py 생성: cleanup_old_sessions(), archive_old_logs() Celery Beat 스케줄 작업
- [X] T040 [US3] services/ecommerce/backend/src/services/order_service.py 수정: 주문 생성 시 send_order_confirmation_email.delay() 호출 (T037 의존)

### FDS 배치 평가

- [X] T041 [P] [US3] services/fds/src/tasks/batch_evaluation.py 생성: batch_evaluate_transactions() Celery Beat 작업 (매일 자정)
- [X] T042 [US3] services/fds/src/services/batch_service.py 생성: 지난 24시간 거래 재평가 로직 (T041 의존)

### Celery 작업 로깅

- [X] T043 [US3] Alembic 마이그레이션 생성: CeleryTaskLog 모델 추가 in services/ecommerce/backend/alembic/versions/
- [X] T044 [US3] services/ecommerce/backend/src/utils/celery_logger.py 생성: Celery 작업 시작/완료 시 CeleryTaskLog 기록 (T043 의존)
- [X] T045 [US3] celeryconfig.py 수정: task_prerun, task_postrun 시그널 핸들러 추가 (T044 의존)

### Flower 모니터링

- [X] T046 [US3] infrastructure/docker/docker-compose.yml Flower 서비스 환경 변수 설정 (basic auth, port 5555) (T036 의존)

### 통합 테스트

- [X] T047 [US3] tests/infrastructure/test_celery_tasks.py 생성: 이메일 발송, 배치 평가, 리포트 생성, 재시도, DLQ 테스트 (T037~T046 의존)

**검증 포인트**:
1. 주문 생성 시 이메일 발송 작업이 RabbitMQ 큐에 추가
2. Celery 워커가 작업 가져와 5초 이내 이메일 발송
3. 매일 자정 FDS 배치 평가 자동 실행
4. Flower 대시보드에서 실시간 작업 상태, 성공/실패 건수 확인
5. 주간 스케줄로 90일 이상 로그 자동 아카이빙

---

## Phase 6: User Story 4 - 통합 로그 모니터링 및 알림 (Priority: P2)

**목표**: ELK Stack 중앙 로그 관리 및 Prometheus + Alertmanager 메트릭 모니터링

**독립 테스트**: 애플리케이션 에러 로그가 Elasticsearch에 수집되고, Kibana 대시보드에서 실시간으로 조회되는지 확인합니다. CPU 사용률이 80%를 초과하면 Slack으로 알림이 발송되는지 검증합니다.

### Logstash 파이프라인

- [X] T048 [P] [US4] infrastructure/docker/elasticsearch/elasticsearch.yml 생성 (cluster.name, discovery.type=single-node, xpack.security.enabled=false)
- [X] T049 [P] [US4] infrastructure/monitoring/logstash/pipeline/app-logs.conf 생성 (input: beats, filter: json+grok, output: elasticsearch)
- [X] T050 [US4] infrastructure/docker/docker-compose.yml Logstash 서비스 볼륨 마운트 추가 (T049 의존)

### Elasticsearch 인덱스 템플릿

- [X] T051 [P] [US4] infrastructure/monitoring/elasticsearch/index-template.json 생성 (shopfds-{service}-{date} 패턴, 매핑, ILM 정책)
- [X] T052 [US4] infrastructure/scripts/init-elasticsearch.sh 생성 (인덱스 템플릿 적용, Curator 설정) (T051 의존)

### Kibana 대시보드

- [X] T053 [P] [US4] infrastructure/monitoring/kibana/dashboards/fds-monitoring.json 생성 (에러율, 응답 시간, 트래픽 패턴 시각화)

### 애플리케이션 로깅 강화

- [X] T054 [US4] services/ecommerce/backend/src/middleware/logging.py 수정: 구조화 로깅 (JSON 포맷, request_id, user_id, endpoint)
- [X] T055 [US4] services/fds/src/middleware/logging.py 수정: 구조화 로깅 (T054와 동일 패턴)
- [X] T056 [US4] services/ml-service/src/middleware/logging.py 수정: 구조화 로깅 (T054와 동일 패턴)
- [X] T057 [US4] services/admin-dashboard/backend/src/middleware/logging.py 수정: 구조화 로깅 (T054와 동일 패턴)

### Health Check 강화

- [X] T058 [US4] services/ecommerce/backend/src/api/health.py 수정: DB 연결, Redis PING, 디스크 공간(90% 미만), 복제 지연 체크 (T020 의존)
- [X] T059 [US4] services/fds/src/api/health.py 수정: Health Check 강화 (T058와 동일 패턴)
- [X] T060 [US4] services/ml-service/src/api/health.py 수정: Health Check 강화 (T058와 동일 패턴)
- [X] T061 [US4] services/admin-dashboard/backend/src/api/health.py 수정: Health Check 강화 (T058와 동일 패턴)

### Prometheus 알림 규칙

- [X] T062 [P] [US4] infrastructure/monitoring/prometheus/alerts/infrastructure.yml 생성 (CPU 80%, 메모리 85%, 디스크 85% 알림)
- [X] T063 [P] [US4] infrastructure/monitoring/prometheus/alerts/application.yml 생성 (API 에러율 5%, Health Check 실패 알림)
- [X] T064 [P] [US4] infrastructure/monitoring/alertmanager/alertmanager.yml 생성 (Slack webhook, Email SMTP, 라우팅 규칙)

### 통합 테스트

- [X] T065 [US4] tests/infrastructure/test_elk_logging.py 생성: 로그 인덱싱, Kibana 조회, 10초 이내 검색 테스트 (T048~T064 의존)

**검증 포인트**:
1. FastAPI 에러 발생 시 5초 이내 Elasticsearch 인덱싱
2. Kibana 대시보드에서 최근 1시간 에러율, 응답 시간, 트래픽 패턴 시각화
3. CPU 사용률 80% 초과 시 Alertmanager가 Slack 경고 메시지 발송
4. Sentry에 Python 예외 발생 시 스택 트레이스와 사용자 컨텍스트 기록
5. Health Check 엔드포인트가 DB 연결, Redis PING, 디스크 공간 실시간 체크

---

## Phase 7: User Story 5 - 개발 환경 자동화 (Priority: P3)

**목표**: Makefile 및 스크립트를 통한 로컬 개발 환경 빠른 설정 및 시드 데이터 생성

**독립 테스트**: 신규 개발자가 `make setup`을 실행하고, 5분 이내에 모든 서비스가 실행되며 시드 데이터가 로드되는지 확인합니다.

### Makefile 및 스크립트

- [X] T066 [P] [US5] infrastructure/Makefile 생성 (dev, test, migrate, seed, clean 타겟)
- [X] T067 [P] [US5] infrastructure/scripts/setup.sh 생성 (의존성 설치, Docker 이미지 빌드, 초기 마이그레이션)
- [X] T068 [P] [US5] infrastructure/scripts/reset-db.sh 생성 (모든 테이블 삭제, 최신 스키마 재생성)
- [X] T069 [P] [US5] infrastructure/scripts/seed-data.py 생성 (사용자 1000명, 주문 10000건, 상품 500개, 리뷰 5000개, 정상 거래 85%, 의심 거래 10%, 사기 거래 5%)
- [X] T070 [US5] infrastructure/scripts/seed-data.py 멱등성 보장 로직 추가: --append 플래그, 중복 제거 (T069 의존)
- [X] T071 [US5] README.md 업데이트: Quickstart 가이드, 개발 환경 설정 명령어 (T066~T070 의존)

**검증 포인트**:
1. `make setup` 실행 시 Docker Compose, 의존성 설치, DB 마이그레이션 자동 완료
2. `make seed` 실행 시 사용자 1000명, 주문 10000건, 상품 500개, 리뷰 5000개 생성
3. `make reset-db` 실행 시 모든 테이블 삭제 후 최신 스키마 재생성
4. `make test` 실행 시 전체 서비스 유닛 테스트 및 통합 테스트 순차 실행
5. CI/CD 파이프라인에서 Alembic 마이그레이션 자동 실행 및 롤백 스크립트 문서화

---

## Phase 8: Polish & Cross-Cutting Concerns

**목표**: 최종 검증, 문서 업데이트, CI/CD 통합

### 최종 통합 테스트

- [X] T072 전체 인프라 통합 테스트: docker-compose up -d 실행 후 모든 서비스 Health Check 통과, 2분 이내 시작 (T010, T021, T033, T047, T065 의존)

### 문서화

- [X] T073 specs/002-production-infra/quickstart.md 작성: 로컬 개발 환경 설정 가이드, 트러블슈팅 (T066~T072 의존)

**검증 포인트**:
- 전체 인프라가 `docker-compose up -d` 명령어로 2분 이내 시작
- 모든 Health Check 엔드포인트가 200 OK 응답
- Alembic 마이그레이션이 CI/CD 파이프라인에서 자동 실행, 실패 시 배포 중단

---

## Task Dependencies

### Critical Path (MVP - US1~US2)
```
T001~T004 (Setup)
  -> T005~T010 (Docker Compose)
    -> T011~T014 (PostgreSQL Replication)
      -> T015~T020 (Application Connection Pools)
        -> T021 (Replication Tests)
    -> T022~T025 (Redis Cluster)
      -> T026~T028 (Blacklist Manager)
        -> T029~T032 (Admin API + Session)
          -> T033 (Redis Tests)
```

### Extended Path (Full - US3~US5)
```
MVP (T001~T033)
  -> T034~T036 (Celery Setup)
    -> T037~T046 (Async Tasks)
      -> T047 (Celery Tests)
  -> T048~T053 (ELK Stack)
    -> T054~T064 (Logging + Prometheus)
      -> T065 (ELK Tests)
  -> T066~T071 (Dev Automation)
  -> T072~T073 (Final Integration)
```

---

## Acceptance Criteria

### US1 (PostgreSQL Read Replica)
- [SC-001] 데이터베이스 읽기 쿼리의 80% 이상이 Read Replica에서 처리
- Master 부하가 50% 이상 감소
- 복제 지연 10초 이내 유지
- Replica 다운 시 Master로 자동 폴백

### US2 (Redis Cluster Blacklist)
- [SC-002] 블랙리스트 차단 결정 100ms 이내
- [SC-003] Redis 노드 1개 장애 시 자동 페일오버 (서비스 중단 없음)
- 블랙리스트 IP/이메일/카드로부터 거래 자동 차단
- TTL 자동 만료 동작

### US3 (Celery + RabbitMQ)
- [SC-004] 주문 생성 API 응답 시간 평균 500ms 단축
- [SC-005] Celery 워커가 시간당 1000개 이상 작업 처리
- 이메일 발송 비동기 처리
- FDS 배치 평가 매일 자정 자동 실행

### US4 (ELK + Prometheus)
- [SC-006] 에러 발생 시 10초 이내 Elasticsearch 인덱싱
- [SC-007] CPU 사용률 80% 초과 시 30초 이내 Slack 알림
- [SC-010] Health Check 엔드포인트 100ms 이내 응답
- Kibana 대시보드에서 실시간 로그 조회

### US5 (Dev Automation)
- [SC-008] `make setup` 명령어로 5분 이내 전체 개발 환경 구축
- [SC-009] 시드 데이터 생성 10분 이내 완료 (사용자 1000명, 주문 10000건)
- [SC-011] Alembic 마이그레이션 CI/CD 자동 실행
- [SC-012] 전체 인프라 `docker-compose up -d` 명령어로 2분 이내 시작

---

## Notes

### Windows 환경 호환성
- 모든 스크립트는 ASCII 문자만 사용 (이모지 금지)
- 성공/실패 표시: [OK], [FAIL], [SUCCESS], [ERROR], [WARNING]
- Git 커밋 메시지: [feat], [fix], [docs], [test], [refactor]

### 병렬 실행 가능 작업 ([P] 마커)
- 서로 다른 파일/서비스 작업은 병렬 실행 가능
- 의존성 없는 설정 파일 생성 작업은 병렬 실행 가능
- 예: T001~T004 (디렉토리 생성), T011~T012 (PostgreSQL 설정 파일)

### User Story 레이블
- [US1]: PostgreSQL Read Replica 관련
- [US2]: Redis Cluster Blacklist 관련
- [US3]: Celery + RabbitMQ 관련
- [US4]: ELK Stack + Prometheus 관련
- [US5]: 개발 환경 자동화 관련

### MVP vs Full 구현
- **MVP (2주)**: US1~US2 (Phase 1~4, T001~T033)
  - PostgreSQL Read Replica: 읽기 부하 분산
  - Redis Cluster: 블랙리스트 관리, 세션 스토어
  - 핵심 인프라 안정성 확보
- **Full (4주)**: US1~US5 (Phase 1~8, T001~T073)
  - Celery: 비동기 작업 처리
  - ELK Stack: 중앙 로그 관리
  - Prometheus: 메트릭 모니터링 및 알림
  - 개발 환경 자동화

---

**Version**: 1.0
**Last Updated**: 2025-11-17
**Status**: Ready for Implementation
