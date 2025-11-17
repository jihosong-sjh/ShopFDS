# PostgreSQL Streaming Replication Best Practices

## 1. Master-Replica 복제 설정 방법

### Decision
PostgreSQL 스트리밍 복제를 다음 설정으로 구성:
```ini
# postgresql.conf (Master)
wal_level = replica
max_wal_senders = 5
wal_keep_size = 2048  # 2GB
hot_standby = on
max_replication_slots = 5
synchronous_commit = on  # 또는 remote_apply (강한 일관성 필요시)

# postgresql.conf (Replica)
hot_standby = on
hot_standby_feedback = on
max_standby_streaming_delay = 30s
```

### Rationale
- **wal_level = replica**: 스트림 복제를 위해 필수. WAL에 충분한 정보를 기록하여 Standby 서버가 복제 가능
- **max_wal_senders = 5**: Replica 2개 + 여유분(재연결, 백업용). 일반적으로 "Replica 수 * 2 + 1" 권장
- **wal_keep_size = 2GB**: Replica가 일시적으로 느려졌을 때 Master가 WAL 세그먼트를 충분히 보관하여 복제 중단 방지
- **hot_standby = on**: Replica에서 읽기 전용 쿼리 가능 (Read Scaling)
- **max_replication_slots = 5**: 물리적 슬롯 사용으로 WAL 자동 보관, Replica 연결 끊김 시 WAL 재전송 가능
- **synchronous_commit = on**: 비동기 복제 (성능 우선). 강한 데이터 일관성 필요시 `remote_apply` 사용

### Alternatives Considered
1. **Logical Replication**:
   - 장점: 테이블 단위 선택적 복제, 다른 PostgreSQL 버전 간 복제 가능
   - 단점: DDL 변경 자동 복제 안됨, Streaming Replication보다 복잡
   - 결론: 전체 데이터베이스 복제가 필요하므로 Streaming Replication 선택

2. **Cascading Replication** (Master -> Replica1 -> Replica2):
   - 장점: Master 부하 감소
   - 단점: 복제 지연 증가, 설정 복잡도 상승
   - 결론: 초기 단계에서는 Direct Replication(Master -> Replica 직접 연결)이 더 적합

3. **Synchronous Replication** (synchronous_commit = remote_apply):
   - 장점: 데이터 손실 0%, 강한 일관성
   - 단점: 쓰기 성능 저하 (Replica 응답 대기), 네트워크 지연 시 영향 큼
   - 결론: 이커머스 FDS는 성능 우선(100ms 목표)이므로 Asynchronous Replication 선택

### Implementation Notes
1. **Replication Slot 사용 권장**:
   ```sql
   -- Master에서 실행
   SELECT * FROM pg_create_physical_replication_slot('replica_slot_1');
   ```
   - WAL 자동 보관으로 Replica 다운 시에도 복제 재개 가능
   - `max_slot_wal_keep_size` 설정으로 WAL 무한 증가 방지 필요

2. **pg_hba.conf 설정** (Master):
   ```
   # TYPE  DATABASE        USER            ADDRESS                 METHOD
   host    replication     replicator      10.0.1.0/24             scram-sha-256
   ```

3. **Replica 초기 설정** (pg_basebackup 사용):
   ```bash
   pg_basebackup -h master_host -D /var/lib/postgresql/data -U replicator -P -v -R -S replica_slot_1
   ```
   - `-R` 옵션으로 `standby.signal` 및 `postgresql.auto.conf` 자동 생성

4. **주의사항**:
   - `wal_keep_size` 너무 작으면 Replica 일시 정지 시 복제 중단 위험
   - `max_wal_senders` 너무 크면 메모리 낭비 (각 sender당 ~10MB)
   - Replication Slot 사용 시 Replica 장기 다운되면 WAL 디스크 가득 찰 수 있음 → 모니터링 필수

---

## 2. SQLAlchemy 읽기/쓰기 연결 풀 분리 패턴

### Decision
**Django-Style Database Router 패턴** 구현:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# 엔진 생성
MASTER_URL = "postgresql+asyncpg://user:pass@master:5432/shopfds"
REPLICA_URL = "postgresql+asyncpg://user:pass@replica:5432/shopfds"

master_engine = create_engine(
    MASTER_URL,
    pool_size=20,          # 쓰기 연결 풀
    max_overflow=10,
    pool_pre_ping=True,    # 연결 상태 자동 체크
    echo=False,
)

replica_engine = create_engine(
    REPLICA_URL,
    pool_size=30,          # 읽기 연결 풀 (더 많이)
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,
)

# 세션 팩토리
SessionLocal = sessionmaker(bind=master_engine, expire_on_commit=False)
ReadOnlySession = sessionmaker(bind=replica_engine, expire_on_commit=False)

# 라우팅 로직
@contextmanager
def get_db_session(read_only: bool = False):
    """
    Context manager for database session with read/write routing.

    Args:
        read_only: True for replica, False for master (default)
    """
    session_factory = ReadOnlySession if read_only else SessionLocal
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# FastAPI Dependency
async def get_db():
    """Write session (Master)"""
    async with AsyncSession(master_engine) as session:
        yield session

async def get_read_db():
    """Read-only session (Replica)"""
    async with AsyncSession(replica_engine) as session:
        yield session
```

**사용 예시**:
```python
# FastAPI 엔드포인트
@router.get("/products")
async def list_products(db: AsyncSession = Depends(get_read_db)):
    # Replica에서 읽기
    result = await db.execute(select(Product).limit(100))
    return result.scalars().all()

@router.post("/products")
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    # Master에서 쓰기
    product = Product(**data.dict())
    db.add(product)
    await db.commit()
    return product
```

### Rationale
- **명시적 세션 선택**: `get_db()`(쓰기), `get_read_db()`(읽기)로 엔드포인트별 명확한 라우팅
- **Transaction-Level Routing**: SQLAlchemy 세션은 트랜잭션 내에서 엔진 변경 불가능하므로 트랜잭션 시작 전에 라우팅 결정
- **Connection Pool 분리**: Master(쓰기 20개), Replica(읽기 30개)로 워크로드에 맞게 최적화
- **pool_pre_ping=True**: 재사용 전 연결 상태 체크로 Replica 다운 시 즉시 감지

### Alternatives Considered
1. **Session.get_bind() Override** (RoutingSession):
   ```python
   class RoutingSession(Session):
       def get_bind(self, mapper=None, clause=None):
           if self._flushing:
               return master_engine
           else:
               return replica_engine
   ```
   - 장점: 자동 라우팅
   - 단점: 세션 내에서 엔진 전환 불가(트랜잭션 경계 문제), 예측 어려움
   - 결론: 명시적 세션 선택이 더 안전하고 디버깅 용이

2. **pgpool-II / PgBouncer Router**:
   - 장점: 애플리케이션 코드 변경 없이 SQL 쿼리 분석으로 자동 라우팅
   - 단점: 외부 의존성 추가, 설정 복잡도 증가, Latency 증가
   - 결론: 초기에는 애플리케이션 레벨 라우팅으로 시작, 규모 확장 시 pgpool-II 고려

3. **Query-Level Routing** (autocommit mode):
   ```python
   session.execute(select(...))  # Replica
   session.execute(insert(...))  # Master
   ```
   - 장점: 쿼리 단위 세밀한 제어
   - 단점: autocommit 모드 필수, 트랜잭션 경계 불명확, 성능 저하
   - 결론: Transaction-Level Routing이 안전하고 성능 우수

### Implementation Notes
1. **읽기 전용 트랜잭션 명시**:
   ```python
   # Replica에서 실수로 쓰기 방지
   replica_engine = create_engine(
       REPLICA_URL,
       connect_args={"options": "-c default_transaction_read_only=on"}
   )
   ```

2. **Connection Pool 크기 결정**:
   - Master Pool Size = 동시 쓰기 요청 수 + 여유분 (권장: 10-30)
   - Replica Pool Size = 동시 읽기 요청 수 + 여유분 (권장: 20-50)
   - 공식: `(2 * max_connections) + num_cpus` (PgBouncer 권장)

3. **PgBouncer 통합 권장** (프로덕션):
   ```python
   master_engine = create_engine(
       "postgresql+psycopg2://user:pass@pgbouncer:6432/shopfds",
       pool_size=10,  # PgBouncer 사용 시 더 작게
       poolclass=NullPool,  # PgBouncer가 pooling 담당
   )
   ```
   - 멀티 프로세스 환경에서 연결 공유 (Gunicorn, uWSGI)
   - Transaction Pooling Mode 권장 (Connection Pooling은 prepared statement 깨짐)

4. **주의사항**:
   - **읽기 전용 세션에서 쓰기 시도 시 에러 처리**:
     ```python
     try:
         db.execute(insert(...))
     except sqlalchemy.exc.InternalError as e:
         if "read-only transaction" in str(e):
             # Replica에서 쓰기 시도 → Master로 재시도
             pass
     ```
   - **Replica Lag로 인한 Read-After-Write 불일치**:
     ```python
     # 쓰기 직후 읽기는 Master 사용
     await db.commit()  # Master에 쓰기
     await asyncio.sleep(0.1)  # Replica 동기화 대기 (선택사항)
     result = await read_db.execute(select(...))  # Replica에서 읽기
     ```
   - **세션 공유 금지**: 동일 세션에서 Master/Replica 동시 사용 불가

---

## 3. 복제 지연 모니터링 방법

### Decision
**pg_stat_replication 뷰 기반 모니터링** + **Prometheus + Grafana 시각화**:

```python
# services/ecommerce/backend/src/utils/replication_monitor.py
from sqlalchemy import text
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

async def check_replication_lag(master_session) -> dict:
    """
    Check replication lag from master server.

    Returns:
        dict: {
            'replica_name': str,
            'state': str,
            'write_lag_seconds': float,
            'flush_lag_seconds': float,
            'replay_lag_seconds': float,
            'lag_bytes': int,
            'healthy': bool
        }
    """
    query = text("""
        SELECT
            application_name,
            state,
            client_addr,
            EXTRACT(EPOCH FROM write_lag) AS write_lag_seconds,
            EXTRACT(EPOCH FROM flush_lag) AS flush_lag_seconds,
            EXTRACT(EPOCH FROM replay_lag) AS replay_lag_seconds,
            pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes,
            sync_state,
            CASE
                WHEN state = 'streaming' AND replay_lag < INTERVAL '5 seconds'
                THEN TRUE
                ELSE FALSE
            END AS healthy
        FROM pg_stat_replication;
    """)

    result = await master_session.execute(query)
    rows = result.fetchall()

    replicas = []
    for row in rows:
        replica_info = {
            'replica_name': row.application_name,
            'state': row.state,
            'client_addr': str(row.client_addr),
            'write_lag_seconds': row.write_lag_seconds or 0,
            'flush_lag_seconds': row.flush_lag_seconds or 0,
            'replay_lag_seconds': row.replay_lag_seconds or 0,
            'lag_bytes': row.lag_bytes or 0,
            'sync_state': row.sync_state,
            'healthy': row.healthy
        }
        replicas.append(replica_info)

        # Alert on high lag
        if row.replay_lag_seconds and row.replay_lag_seconds > 10:
            logger.warning(
                f"[REPLICATION LAG] Replica {row.application_name} "
                f"is lagging by {row.replay_lag_seconds:.2f}s "
                f"({row.lag_bytes} bytes)"
            )

    return replicas

async def check_replica_status(replica_session) -> dict:
    """
    Check replication status from replica server.

    Returns:
        dict: {
            'is_in_recovery': bool,
            'last_wal_receive_lsn': str,
            'last_wal_replay_lsn': str,
            'lag_bytes': int
        }
    """
    query = text("""
        SELECT
            pg_is_in_recovery() AS is_in_recovery,
            pg_last_wal_receive_lsn() AS last_receive_lsn,
            pg_last_wal_replay_lsn() AS last_replay_lsn,
            pg_wal_lsn_diff(
                pg_last_wal_receive_lsn(),
                pg_last_wal_replay_lsn()
            ) AS lag_bytes;
    """)

    result = await replica_session.execute(query)
    row = result.fetchone()

    return {
        'is_in_recovery': row.is_in_recovery,
        'last_wal_receive_lsn': str(row.last_receive_lsn),
        'last_wal_replay_lsn': str(row.last_replay_lsn),
        'lag_bytes': row.lag_bytes or 0
    }
```

**Prometheus Exporter 설정**:
```yaml
# docker-compose.yml
services:
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    environment:
      DATA_SOURCE_NAME: "postgresql://exporter:password@master:5432/shopfds?sslmode=disable"
    ports:
      - "9187:9187"
    command:
      - '--collector.stat_replication'
```

**Grafana 대시보드 쿼리**:
```promql
# Replication Lag (seconds)
pg_stat_replication_replay_lag_seconds

# Replication Lag (bytes)
pg_stat_replication_lag_bytes

# Replica Health
up{job="postgres-exporter"}
```

### Rationale
- **pg_stat_replication**: Master에서 실행하여 모든 Replica의 상태 확인 가능
- **replay_lag**: 가장 중요한 지표. 사용자가 실제로 볼 수 있는 데이터의 지연 시간
- **write_lag vs flush_lag vs replay_lag**:
  - write_lag: Master가 WAL을 작성한 후 Replica가 OS 버퍼에 쓴 시간
  - flush_lag: Replica가 디스크에 fsync한 시간 (지속성 보장)
  - replay_lag: Replica가 WAL을 적용하여 쿼리 가능한 시간 (가장 중요)
- **pg_wal_lsn_diff**: 바이트 단위 지연 측정으로 네트워크 대역폭 병목 감지

### Alternatives Considered
1. **pg_stat_wal_receiver** (Replica에서 실행):
   - 장점: Replica 관점에서 수신 상태 확인
   - 단점: Master와의 상대적 지연 계산 불가능
   - 결론: pg_stat_replication과 함께 사용 (보조 지표)

2. **check_postgres.pl** (Nagios 플러그인):
   - 장점: 즉시 사용 가능한 알림 스크립트
   - 단점: 시각화 부족, 역사적 데이터 부족
   - 결론: Prometheus + Grafana가 더 강력

3. **Cloud Provider 모니터링** (AWS CloudWatch, GCP Monitoring):
   - 장점: 관리형 서비스, 설정 간단
   - 단점: 벤더 종속, 비용, 세밀한 제어 어려움
   - 결론: 온프레미스/멀티 클라우드 지원 위해 Prometheus 선택

### Implementation Notes
1. **알림 임계값 설정**:
   ```python
   LAG_WARNING_THRESHOLD = 5   # seconds
   LAG_CRITICAL_THRESHOLD = 30  # seconds
   LAG_BYTES_THRESHOLD = 100 * 1024 * 1024  # 100MB

   if replay_lag_seconds > LAG_CRITICAL_THRESHOLD:
       send_alert("CRITICAL: Replication lag > 30s")
   elif replay_lag_seconds > LAG_WARNING_THRESHOLD:
       send_alert("WARNING: Replication lag > 5s")
   ```

2. **정기적 모니터링 작업** (Celery Beat):
   ```python
   # services/ecommerce/backend/src/tasks/monitoring.py
   from celery import Celery
   from celery.schedules import crontab

   app = Celery('tasks')

   @app.task
   async def monitor_replication():
       async with get_master_session() as session:
           replicas = await check_replication_lag(session)
           for replica in replicas:
               if not replica['healthy']:
                   logger.error(f"Replica {replica['replica_name']} unhealthy!")

   app.conf.beat_schedule = {
       'monitor-replication': {
           'task': 'tasks.monitoring.monitor_replication',
           'schedule': crontab(minute='*/1'),  # 1분마다
       },
   }
   ```

3. **Replica 상태 확인 API** (Admin Dashboard):
   ```python
   @router.get("/v1/admin/replication/status")
   async def get_replication_status(db: AsyncSession = Depends(get_db)):
       replicas = await check_replication_lag(db)
       return {
           "replicas": replicas,
           "timestamp": datetime.utcnow().isoformat()
       }
   ```

4. **주의사항**:
   - **pg_stat_replication은 Master에서만 실행 가능**: Replica에서 실행 시 빈 결과
   - **state != 'streaming'**: Replica가 연결 끊김 또는 catchup 중 → 긴급 점검 필요
   - **replay_lag이 NULL**: Replica 초기 연결 시 WAL 데이터 부족 → 정상 (수 분 대기)
   - **lag_bytes 지속 증가**: Master 과부하 또는 네트워크 병목 → 인프라 스케일 업 필요

---

## 4. 자동 폴백 전략 (Replica 다운 시 Master로 읽기 쿼리 라우팅)

### Decision
**Circuit Breaker 패턴 기반 자동 폴백**:

```python
# services/ecommerce/backend/src/utils/db_router.py
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # 정상 작동
    OPEN = "open"          # Replica 다운, Master 사용
    HALF_OPEN = "half_open"  # 복구 확인 중

class ReplicaCircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,  # seconds
        half_open_timeout: int = 30,
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_timeout = half_open_timeout

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    async def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("[CIRCUIT BREAKER] Attempting to reset (HALF_OPEN)")
            else:
                logger.warning("[CIRCUIT BREAKER] Replica unavailable, using Master")
                raise ReplicaUnavailableError("Replica is down")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("[CIRCUIT BREAKER] Replica recovered, circuit CLOSED")
            self.state = CircuitState.CLOSED
        self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.error(
                    f"[CIRCUIT BREAKER] Replica failed {self.failure_count} times, "
                    f"circuit OPEN (fallback to Master)"
                )
                self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True

        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        timeout = self.half_open_timeout if self.state == CircuitState.HALF_OPEN else self.timeout
        return elapsed >= timeout

class ReplicaUnavailableError(Exception):
    pass

# Global circuit breaker instance
replica_circuit_breaker = ReplicaCircuitBreaker()

async def get_read_session():
    """
    Get read session with automatic fallback to master.
    """
    try:
        # Try replica first
        session = await replica_circuit_breaker.call(
            _create_replica_session
        )
        return session
    except ReplicaUnavailableError:
        # Fallback to master
        logger.warning("[DB ROUTER] Using Master for read query (Replica unavailable)")
        return await _create_master_session()
    except Exception as e:
        logger.error(f"[DB ROUTER] Failed to get read session: {e}")
        # Last resort: fallback to master
        return await _create_master_session()

async def _create_replica_session():
    """Create replica session with connection test."""
    session = AsyncSession(replica_engine)
    # Connection health check
    await session.execute(text("SELECT 1"))
    return session

async def _create_master_session():
    """Create master session."""
    return AsyncSession(master_engine)
```

**FastAPI Dependency 통합**:
```python
# services/ecommerce/backend/src/api/dependencies.py
from fastapi import Depends

async def get_db_read(fallback: bool = True):
    """
    Dependency for read operations with automatic fallback.

    Args:
        fallback: If True, fallback to master when replica is down
    """
    session = await get_read_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

# Usage
@router.get("/products")
async def list_products(db: AsyncSession = Depends(get_db_read)):
    # Automatically uses Master if Replica is down
    result = await db.execute(select(Product).limit(100))
    return result.scalars().all()
```

### Rationale
- **Circuit Breaker 패턴**: Netflix Hystrix, Resilience4j에서 검증된 패턴
- **3가지 상태 관리**:
  - CLOSED: 정상 (Replica 사용)
  - OPEN: Replica 다운 (즉시 Master 폴백, Replica 연결 시도 안함)
  - HALF_OPEN: 복구 확인 중 (1회 Replica 시도, 성공 시 CLOSED로 전환)
- **실패 임계값**: 5회 연속 실패 시 OPEN 전환 (ping 실패, 타임아웃 등)
- **타임아웃**: 60초 후 HALF_OPEN으로 자동 전환하여 복구 시도
- **Connection Health Check**: `SELECT 1` 쿼리로 연결 상태 사전 확인

### Alternatives Considered
1. **HAProxy / Pgpool-II Health Check**:
   - 장점: 애플리케이션 레벨 코드 불필요, 자동 라우팅
   - 단점: 외부 의존성, 설정 복잡도, 애플리케이션 레벨 세밀한 제어 어려움
   - 결론: 초기에는 애플리케이션 레벨 Circuit Breaker 사용, 규모 확장 시 HAProxy 추가 고려

2. **Retry with Exponential Backoff**:
   ```python
   for i in range(3):
       try:
           return await replica_session.execute(query)
       except Exception:
           await asyncio.sleep(2 ** i)  # 1s, 2s, 4s
   ```
   - 장점: 간단한 구현
   - 단점: Replica가 완전히 다운되면 모든 요청이 지연됨, Circuit Breaker 없음
   - 결론: Circuit Breaker가 더 안정적 (빠른 실패, 자동 복구)

3. **DNS Failover** (예: AWS Route 53 Health Check):
   - 장점: 인프라 레벨 자동화
   - 단점: DNS TTL로 인한 지연(수 분), 세밀한 제어 불가
   - 결론: 애플리케이션 레벨 폴백이 더 빠름 (수 초)

### Implementation Notes
1. **Connection Pool pre_ping 활용**:
   ```python
   replica_engine = create_engine(
       REPLICA_URL,
       pool_pre_ping=True,  # 연결 재사용 전 자동 체크
   )
   ```
   - 끊긴 연결 자동 제거, Circuit Breaker와 함께 사용

2. **Metrics 수집** (Prometheus):
   ```python
   from prometheus_client import Counter, Gauge

   replica_fallback_count = Counter('db_replica_fallback_total', 'Replica fallback to master count')
   circuit_breaker_state = Gauge('db_circuit_breaker_state', 'Circuit breaker state (0=closed, 1=open, 2=half_open)')

   # Circuit breaker 상태 변경 시
   if self.state == CircuitState.OPEN:
       replica_fallback_count.inc()
       circuit_breaker_state.set(1)
   ```

3. **알림 설정** (Slack, PagerDuty):
   ```python
   if self.state == CircuitState.OPEN:
       send_alert(
           level="CRITICAL",
           message=f"Replica database is down! All read queries routed to Master. "
                   f"Failure count: {self.failure_count}"
       )
   ```

4. **Config 환경 변수**:
   ```python
   # .env
   REPLICA_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
   REPLICA_CIRCUIT_BREAKER_TIMEOUT=60
   REPLICA_CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT=30
   ```

5. **주의사항**:
   - **Master 과부하 방지**: Replica 다운 시 Master가 읽기+쓰기 트래픽 모두 처리 → HPA로 Master 스케일 업 필요
   - **Read-After-Write 불일치 없음**: Replica 다운 시 Master에서 읽기이므로 일관성 보장
   - **복구 시 트래픽 급증 방지**: HALF_OPEN 상태에서 점진적으로 트래픽 증가 (Load Shedding)
   - **테스트**: Replica 강제 종료하여 폴백 로직 검증 필수

---

## 5. 권장 설정값

### Decision
**프로덕션 환경 권장 설정**:

```ini
# ===========================
# Master (Primary) 설정
# ===========================
[postgresql.conf - Master]

# --- Replication Settings ---
wal_level = replica
max_wal_senders = 5  # Replica 2개 + 백업/재연결 여유분
max_replication_slots = 5
wal_keep_size = 2048  # 2GB (Replica 일시 지연 대비)
max_slot_wal_keep_size = 4096  # 4GB (Slot WAL 최대 보관)

# --- Checkpoint Settings ---
checkpoint_timeout = 10min  # 기본 5min → 10min (I/O 분산)
max_wal_size = 2GB  # 기본 1GB → 2GB (체크포인트 빈도 감소)
min_wal_size = 1GB  # 기본 80MB → 1GB (WAL 재사용)
checkpoint_completion_target = 0.9  # 체크포인트를 timeout의 90%에 걸쳐 완료

# --- Write Performance ---
synchronous_commit = on  # 비동기 복제 (성능 우선)
# synchronous_commit = remote_apply  # 동기 복제 (일관성 우선, 성능 저하)
wal_compression = on  # WAL 압축 (네트워크 대역폭 절약)
wal_writer_delay = 200ms  # 기본값 (WAL writer 주기)

# --- Hot Standby Settings ---
hot_standby = on
hot_standby_feedback = on  # Replica의 쿼리 취소 방지
max_standby_streaming_delay = 30s  # Replica 쿼리 최대 대기 시간

# --- Connection Settings ---
max_connections = 200  # 동시 연결 수 (쓰기+읽기)
shared_buffers = 4GB  # 총 메모리의 25% (16GB 서버 기준)
effective_cache_size = 12GB  # 총 메모리의 75%

# --- Monitoring ---
log_replication_commands = on
log_checkpoints = on
log_connections = on
log_disconnections = on
log_duration = on
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '

# ===========================
# Replica (Standby) 설정
# ===========================
[postgresql.conf - Replica]

# --- Hot Standby Settings ---
hot_standby = on
hot_standby_feedback = on
max_standby_streaming_delay = 30s
max_standby_archive_delay = 30s

# --- Connection Settings ---
max_connections = 200  # Master와 동일
shared_buffers = 4GB  # Master와 동일

# --- Read-only enforced ---
default_transaction_read_only = on  # 실수로 쓰기 방지

# ===========================
# Replication Slot 설정
# ===========================
-- Master에서 실행
SELECT * FROM pg_create_physical_replication_slot('replica_slot_1');
SELECT * FROM pg_create_physical_replication_slot('replica_slot_2');

-- Slot 상태 모니터링
SELECT slot_name, slot_type, active, restart_lsn,
       pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) AS lag_bytes
FROM pg_replication_slots;

-- 비활성 Slot 제거 (60분 이상 사용 안됨)
SELECT pg_drop_replication_slot('replica_slot_1')
WHERE NOT active AND (now() - last_received_lsn) > INTERVAL '60 minutes';

# ===========================
# pg_hba.conf 설정
# ===========================
[pg_hba.conf - Master]
# TYPE  DATABASE        USER            ADDRESS                 METHOD
host    replication     replicator      10.0.1.10/32            scram-sha-256  # Replica 1
host    replication     replicator      10.0.1.11/32            scram-sha-256  # Replica 2
host    all             all             10.0.0.0/8              scram-sha-256  # Internal network

# ===========================
# Docker Compose 설정
# ===========================
version: '3.9'
services:
  postgres-master:
    image: postgres:15
    environment:
      POSTGRES_USER: shopfds
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: shopfds
    volumes:
      - master-data:/var/lib/postgresql/data
      - ./postgresql-master.conf:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shopfds"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres-replica:
    image: postgres:15
    environment:
      PGUSER: replicator
      PGPASSWORD: ${REPLICATOR_PASSWORD}
    volumes:
      - replica-data:/var/lib/postgresql/data
      - ./postgresql-replica.conf:/etc/postgresql/postgresql.conf
    command: |
      bash -c "
      if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
        pg_basebackup -h postgres-master -D /var/lib/postgresql/data -U replicator -P -v -R -S replica_slot_1
      fi
      postgres -c config_file=/etc/postgresql/postgresql.conf
      "
    ports:
      - "5433:5432"
    depends_on:
      postgres-master:
        condition: service_healthy

volumes:
  master-data:
  replica-data:
```

### Rationale

#### 복제 슬롯 (Replication Slot)
- **왜 필요한가?**: WAL 자동 보관으로 Replica 일시 다운 시에도 복제 재개 가능
- **max_slot_wal_keep_size = 4GB**: 무한 WAL 증가 방지 (디스크 가득 참 방지)
- **주의**: 슬롯 사용하지 않으면 주기적으로 제거 필요 (디스크 공간 확보)

#### 체크포인트 (Checkpoint)
- **checkpoint_timeout = 10min**: I/O 분산 (기본 5분은 너무 빈번)
- **max_wal_size = 2GB**: 체크포인트 빈도 감소로 쓰기 성능 향상
- **checkpoint_completion_target = 0.9**: 체크포인트를 90%에 걸쳐 완료하여 I/O 스파이크 방지

#### WAL 보관 주기 (wal_keep_size)
- **2GB 권장**: Replica가 5-10분 정도 지연되어도 복제 가능
- **계산식**: `쓰기 속도(MB/s) * 예상 지연 시간(s)`
  - 예: 10MB/s * 300s = 3GB → 2GB 설정 (여유 고려)
- **Replication Slot과 함께 사용**: Slot이 우선, wal_keep_size는 백업

#### 동기/비동기 복제 선택
- **synchronous_commit = on (비동기)**:
  - 장점: 쓰기 성능 우수 (Replica 대기 안함)
  - 단점: Master 장애 시 최대 수 초 데이터 손실 가능
  - 권장: 이커머스 FDS (성능 우선, 100ms 목표)
- **synchronous_commit = remote_apply (동기)**:
  - 장점: 데이터 손실 0%, 강한 일관성
  - 단점: 쓰기 성능 저하 (Replica 응답 대기), Latency 증가
  - 권장: 금융 거래, 결제 데이터 (일관성 우선)

#### Hot Standby 설정
- **hot_standby_feedback = on**: Replica의 읽기 쿼리가 Master의 VACUUM으로 취소되는 것 방지
- **max_standby_streaming_delay = 30s**: Replica 쿼리가 복제를 최대 30초 지연시킬 수 있음
  - 너무 크면: Replica Lag 증가
  - 너무 작으면: 긴 쿼리 취소됨

### Alternatives Considered
1. **Logical Replication 설정**:
   ```ini
   wal_level = logical
   max_replication_slots = 10
   max_logical_replication_workers = 4
   ```
   - 사용 사례: 테이블 단위 선택적 복제, 버전 업그레이드, 멀티 마스터
   - 단점: DDL 자동 복제 안됨, 설정 복잡도 높음
   - 결론: 초기에는 Physical Replication으로 충분

2. **Cascading Replication**:
   ```
   Master -> Replica1 -> Replica2
   ```
   - 장점: Master 부하 감소
   - 단점: Replica2 지연 증가 (2단계 복제)
   - 결론: Replica가 5개 이상일 때 고려

3. **Synchronous Replication with Multiple Replicas**:
   ```ini
   synchronous_standby_names = 'FIRST 1 (replica1, replica2)'
   ```
   - 장점: 1개 Replica만 동기 확인하면 커밋 (가용성 향상)
   - 단점: 여전히 성능 저하
   - 결론: 금융 서비스 수준의 일관성 필요 시만 사용

### Implementation Notes

#### 1. Replica 초기 설정 (pg_basebackup)
```bash
# Master에서 Replication Slot 생성
psql -U postgres -c "SELECT * FROM pg_create_physical_replication_slot('replica_slot_1');"

# Replica 서버에서 pg_basebackup 실행
pg_basebackup \
  -h master_host \
  -D /var/lib/postgresql/data \
  -U replicator \
  -P -v \
  -R \
  -S replica_slot_1 \
  --wal-method=stream

# -R: standby.signal 및 postgresql.auto.conf 자동 생성
# -S: Replication Slot 이름
# --wal-method=stream: WAL을 스트리밍으로 전송 (tar보다 안전)
```

#### 2. 복제 상태 모니터링 SQL
```sql
-- Master에서 실행: 모든 Replica 상태
SELECT
    application_name,
    state,
    sync_state,
    EXTRACT(EPOCH FROM (now() - pg_last_committed_xact())) AS master_lag_seconds,
    EXTRACT(EPOCH FROM write_lag) AS write_lag_seconds,
    EXTRACT(EPOCH FROM flush_lag) AS flush_lag_seconds,
    EXTRACT(EPOCH FROM replay_lag) AS replay_lag_seconds,
    pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) / 1024 / 1024 AS lag_mb
FROM pg_stat_replication;

-- Replica에서 실행: 자신의 지연 상태
SELECT
    pg_is_in_recovery() AS is_replica,
    pg_last_wal_receive_lsn() AS receive_lsn,
    pg_last_wal_replay_lsn() AS replay_lsn,
    pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn()) / 1024 / 1024 AS lag_mb;

-- Replication Slot 사용량
SELECT
    slot_name,
    slot_type,
    active,
    pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) / 1024 / 1024 AS retained_wal_mb
FROM pg_replication_slots;
```

#### 3. WAL 디스크 공간 관리
```bash
# WAL 디렉토리 크기 확인
du -sh /var/lib/postgresql/data/pg_wal

# WAL 파일 개수
ls -1 /var/lib/postgresql/data/pg_wal | wc -l

# 오래된 WAL 파일 수동 삭제 (주의: Replica 동기화 확인 후)
# pg_archivecleanup 사용
pg_archivecleanup /var/lib/postgresql/data/pg_wal 000000010000000000000010
```

#### 4. 성능 튜닝 팁
```ini
# SSD 사용 시
random_page_cost = 1.1  # 기본 4.0 → 1.1 (SSD는 랜덤 읽기 빠름)

# 대용량 메모리 서버
shared_buffers = 8GB  # 총 메모리의 25% (32GB 서버)
effective_cache_size = 24GB  # 총 메모리의 75%
work_mem = 64MB  # 정렬, 해시 조인용 (기본 4MB)
maintenance_work_mem = 1GB  # VACUUM, CREATE INDEX용 (기본 64MB)

# 고부하 쓰기 워크로드
wal_buffers = 16MB  # 기본 -1(자동) → 16MB (쓰기 버퍼)
max_wal_size = 4GB  # 쓰기 속도가 매우 빠른 경우
```

#### 5. 장애 복구 시나리오
**Scenario 1: Replica 다운**
```bash
# 1. Replica 재시작
systemctl restart postgresql

# 2. 복제 자동 재개 (Replication Slot 사용 시)
# 3. 복제 지연 확인
psql -h master -U postgres -c "SELECT * FROM pg_stat_replication;"
```

**Scenario 2: Master 다운 (Failover)**
```bash
# 1. Replica를 Master로 승격
pg_ctl promote -D /var/lib/postgresql/data

# 2. 애플리케이션 연결 문자열 변경 (DNS 또는 Load Balancer)
# 3. 기존 Master 복구 후 Replica로 전환 (pg_rewind)
pg_rewind --target-pgdata=/var/lib/postgresql/data --source-server="host=new_master port=5432 user=postgres"
```

**Scenario 3: 복제 슬롯 가득 참**
```bash
# 1. 사용하지 않는 슬롯 삭제
psql -U postgres -c "SELECT pg_drop_replication_slot('old_slot');"

# 2. max_slot_wal_keep_size 증가 (임시 조치)
# 3. Replica 복구 또는 재구축
```

#### 6. 보안 설정
```ini
# pg_hba.conf: 복제 연결 암호화
hostssl replication replicator 10.0.1.0/24 scram-sha-256

# postgresql.conf: SSL 인증서 설정
ssl = on
ssl_cert_file = '/etc/postgresql/server.crt'
ssl_key_file = '/etc/postgresql/server.key'
ssl_ca_file = '/etc/postgresql/root.crt'
```

#### 7. 테스트 체크리스트
- [ ] Replica 정상 연결 확인 (`pg_stat_replication`)
- [ ] 복제 지연 5초 이내 (`replay_lag < 5s`)
- [ ] Replica에서 읽기 쿼리 실행 가능
- [ ] Replica에서 쓰기 시도 시 에러 발생 (`default_transaction_read_only = on`)
- [ ] Replica 강제 종료 후 자동 복구 확인
- [ ] Master 장애 시 Replica 승격 (pg_ctl promote)
- [ ] WAL 디스크 사용량 모니터링 알림
- [ ] Circuit Breaker 폴백 동작 확인

---

## 결론

### 채택한 기술 스택
1. **PostgreSQL 15+ 스트리밍 복제** (Physical Replication)
2. **SQLAlchemy Django-Style Router** (명시적 세션 선택)
3. **pg_stat_replication + Prometheus + Grafana** (모니터링)
4. **Circuit Breaker 패턴** (자동 폴백)
5. **Replication Slot + 비동기 복제** (성능 + 안정성 균형)

### 핵심 설정 요약
| 파라미터 | Master | Replica | 설명 |
|---------|--------|---------|------|
| wal_level | replica | - | 복제 활성화 |
| max_wal_senders | 5 | - | 동시 Replica 수 |
| wal_keep_size | 2GB | - | WAL 최소 보관 |
| max_slot_wal_keep_size | 4GB | - | Slot WAL 최대 보관 |
| hot_standby | on | on | Replica 읽기 가능 |
| synchronous_commit | on | - | 비동기 복제 (성능 우선) |
| checkpoint_timeout | 10min | - | 체크포인트 간격 |
| max_wal_size | 2GB | - | 체크포인트 트리거 |

### 성능 목표
- **복제 지연**: P95 < 5초, P99 < 10초
- **폴백 시간**: Replica 다운 감지 후 1초 이내 Master 라우팅
- **읽기 확장**: Replica 추가로 읽기 TPS 2배 향상
- **쓰기 성능**: 비동기 복제로 Master 쓰기 Latency < 10ms

### 다음 단계
1. **프로덕션 배포**: Kubernetes StatefulSet으로 Master-Replica 배포
2. **자동화**: Patroni 또는 repmgr로 자동 Failover 설정
3. **Load Balancer**: HAProxy 또는 pgpool-II로 읽기 쿼리 자동 분산
4. **백업**: pg_basebackup 또는 WAL 아카이빙으로 PITR 구성
5. **성능 테스트**: Replica 읽기 분산으로 목표 TPS 달성 검증

---

## 참고 자료
- [PostgreSQL Official Documentation - Replication](https://www.postgresql.org/docs/current/runtime-config-replication.html)
- [PostgreSQL High Availability Cookbook (2nd Edition)](https://www.packtpub.com/product/postgresql-high-availability-cookbook-second-edition/9781787121843)
- [SQLAlchemy Database Routing](http://techspot.zzzeek.org/2012/01/11/django-style-database-routers-in-sqlalchemy/)
- [Circuit Breaker Pattern - Martin Fowler](https://martinfowler.com/bliki/CircuitBreaker.html)
- [PostgreSQL Replication Slots Best Practices](https://www.morling.dev/blog/mastering-postgres-replication-slots/)
