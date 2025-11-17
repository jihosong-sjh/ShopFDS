# Redis Cluster 운영 가이드 리서치

**Date**: 2025-11-17
**Purpose**: 프로덕션 환경 Redis Cluster 아키텍처 설계 및 운영 전략 수립

---

## 1. Redis Cluster 아키텍처 개요

### Decision: Redis Cluster (6 Nodes: 3 Masters + 3 Replicas)

### Rationale

1. **고가용성 (High Availability)**:
   - 마스터 노드 장애 시 레플리카가 자동으로 승격 (Automatic Failover)
   - 단일 장애 지점(Single Point of Failure) 제거
   - 다운타임 최소화 (< 1초)

2. **수평 확장성 (Horizontal Scalability)**:
   - 데이터가 16,384개 해시 슬롯에 자동 분산 (Sharding)
   - 노드 추가만으로 확장 가능 (최대 ~1,000 노드 권장)
   - 읽기/쓰기 부하를 여러 마스터에 분산

3. **성능 목표 달성**:
   - FDS 평가 100ms 목표를 위해 초고속 캐싱 필수
   - 인메모리 저장으로 <1ms 응답 속도
   - Velocity Check (단시간 내 반복 거래 탐지)에 최적화

4. **데이터 안정성**:
   - 각 마스터마다 레플리카 1개 보장 (최소 데이터 복제본 2개)
   - 비동기 복제로 성능 저하 없이 데이터 보호

### Alternatives Considered

| 구성 | 장점 | 단점 | 선택 이유 |
|------|------|------|-----------|
| **단일 Redis 인스턴스** | 간단한 설정, 낮은 복잡도 | SPOF, 확장 불가, 장애 시 서비스 중단 | [REJECTED] 프로덕션 부적합 |
| **Redis Sentinel** | 자동 페일오버, 설정 간단 | 샤딩 미지원, 쓰기 확장 불가 | [REJECTED] 데이터 증가 시 확장 한계 |
| **Redis Cluster** | 샤딩 + 페일오버, 수평 확장 | 복잡한 설정, 클러스터 모드 필요 | [SELECTED] 프로덕션 요구사항 충족 |

---

## 2. 6노드 클러스터 초기화

### Cluster Topology

```
[Master 1]         [Master 2]         [Master 3]
Port: 7000         Port: 7001         Port: 7002
Slots: 0-5460      Slots: 5461-10922  Slots: 10923-16383
    |                  |                  |
    v                  v                  v
[Replica 1]        [Replica 2]        [Replica 3]
Port: 7003         Port: 7004         Port: 7005
```

### 초기화 명령어

#### 1. Redis 노드 시작 (각 노드별 설정 파일)

```bash
# redis-7000.conf (Master 1)
port 7000
cluster-enabled yes
cluster-config-file nodes-7000.conf
cluster-node-timeout 5000
appendonly yes
appendfilename "appendonly-7000.aof"
dir ./cluster-data/7000
logfile "./cluster-data/7000/redis.log"

# redis-7003.conf (Replica 1)
port 7003
cluster-enabled yes
cluster-config-file nodes-7003.conf
cluster-node-timeout 5000
appendonly yes
appendfilename "appendonly-7003.aof"
dir ./cluster-data/7003
logfile "./cluster-data/7003/redis.log"

# 나머지 노드도 동일한 패턴으로 설정...
```

#### 2. 노드 프로세스 시작

```bash
# 각 노드 시작
redis-server ./redis-7000.conf &
redis-server ./redis-7001.conf &
redis-server ./redis-7002.conf &
redis-server ./redis-7003.conf &
redis-server ./redis-7004.conf &
redis-server ./redis-7005.conf &
```

#### 3. 클러스터 생성 (한 줄 명령어)

```bash
redis-cli --cluster create \
  127.0.0.1:7000 \
  127.0.0.1:7001 \
  127.0.0.1:7002 \
  127.0.0.1:7003 \
  127.0.0.1:7004 \
  127.0.0.1:7005 \
  --cluster-replicas 1
```

**주요 옵션 설명**:
- `--cluster create`: 새 클러스터 생성
- `--cluster-replicas 1`: 각 마스터마다 레플리카 1개 할당
- 처음 3개 노드(7000~7002)가 마스터, 나머지(7003~7005)가 레플리카로 자동 배정

#### 4. 클러스터 상태 확인

```bash
# 클러스터 정보 조회
redis-cli -c -p 7000 cluster info

# Expected Output:
# cluster_state:ok
# cluster_slots_assigned:16384
# cluster_slots_ok:16384
# cluster_slots_pfail:0
# cluster_slots_fail:0
# cluster_known_nodes:6
# cluster_size:3

# 노드 목록 조회
redis-cli -c -p 7000 cluster nodes

# Expected Output (예시):
# a1b2c3... 127.0.0.1:7000@17000 myself,master - 0 1700000000 1 connected 0-5460
# d4e5f6... 127.0.0.1:7003@17003 slave a1b2c3... 0 1700000000 1 connected
# ...
```

### Implementation Notes

1. **포트 범위**: 각 노드는 2개 포트 사용
   - Client Port: 7000~7005 (클라이언트 연결용)
   - Cluster Bus Port: 17000~17005 (노드 간 통신, Client Port + 10000)

2. **디렉토리 구조**:
   ```
   /data/redis-cluster/
   ├── 7000/
   │   ├── appendonly-7000.aof
   │   ├── nodes-7000.conf (클러스터 자동 생성)
   │   └── redis.log
   ├── 7001/
   ├── 7002/
   ├── 7003/
   ├── 7004/
   └── 7005/
   ```

3. **보안 설정** (프로덕션 필수):
   ```bash
   # redis.conf 추가 설정
   requirepass YOUR_STRONG_PASSWORD
   masterauth YOUR_STRONG_PASSWORD   # 레플리카가 마스터 인증용
   protected-mode yes
   bind 0.0.0.0  # 외부 접근 허용 (방화벽 필수)
   ```

---

## 3. 해시 슬롯 16384개 자동 분배 방식

### Why 16,384 Slots?

1. **메모리 효율성**:
   - 16K 슬롯: 클러스터 설정에 **2KB** 메모리 필요
   - 65K 슬롯: 클러스터 설정에 **8KB** 메모리 필요 (비효율적)
   - 비트맵으로 슬롯 상태 관리 시 16K가 최적

2. **충분한 샤딩 단위**:
   - 최대 1,000개 마스터 노드 지원
   - 각 노드당 평균 16개 슬롯 할당
   - 데이터 균등 분산 보장

3. **빠른 리샤딩**:
   - 슬롯 단위로 데이터 이동 가능
   - 노드 추가/제거 시 슬롯만 재분배

### 해시 슬롯 계산 방식

```python
import zlib

def get_hash_slot(key: str) -> int:
    """
    Redis Cluster 해시 슬롯 계산 (CRC16 mod 16384)

    Args:
        key: Redis 키

    Returns:
        int: 0~16383 범위의 슬롯 번호
    """
    # 해시 태그 처리: {user123}:cart -> "user123"만 해싱
    if '{' in key:
        start = key.index('{')
        end = key.index('}', start)
        if end > start + 1:
            key = key[start+1:end]

    # CRC16 계산
    crc = zlib.crc32(key.encode('utf-8')) & 0xFFFF
    return crc % 16384

# 예시
print(get_hash_slot("user:123:cart"))      # 예: 7892
print(get_hash_slot("user:456:cart"))      # 예: 13451
print(get_hash_slot("{user123}:cart"))     # 해시 태그: "user123"만 해싱
print(get_hash_slot("{user123}:profile"))  # 동일 슬롯 (같은 노드에 저장)
```

### 3-Master Cluster 슬롯 분배

| Master Node | Port | Slot Range | Slot Count | Percentage |
|-------------|------|------------|------------|------------|
| Master 1 | 7000 | 0 ~ 5460 | 5,461 | 33.3% |
| Master 2 | 7001 | 5461 ~ 10922 | 5,462 | 33.4% |
| Master 3 | 7002 | 10923 ~ 16383 | 5,461 | 33.3% |

### Hash Tag를 이용한 Multi-Key 작업

Redis Cluster에서는 여러 키가 동일 슬롯에 있어야 MGET, MSET 등 Multi-Key 명령어 사용 가능:

```python
# WRONG: 에러 발생 (키들이 다른 노드에 분산)
redis.mget("user:123:cart", "user:456:cart")
# Error: CROSSSLOT Keys in request don't hash to the same slot

# CORRECT: 해시 태그로 동일 슬롯 보장
redis.mget("{user123}:cart", "{user123}:profile", "{user123}:orders")
# Success: 모두 "user123"으로 해싱 -> 동일 슬롯
```

### Implementation Notes

1. **키 네이밍 전략**:
   ```python
   # 사용자별 데이터 그룹핑 (권장)
   "{user:123}:cart"
   "{user:123}:session"
   "{user:123}:velocity"

   # FDS 블랙리스트 (분산 저장)
   "blacklist:ip:192.168.1.1"
   "blacklist:email:test@example.com"
   "blacklist:card_bin:123456"
   ```

2. **슬롯 이동 시나리오**:
   - 노드 추가: 기존 마스터들이 슬롯 일부를 새 노드에 이동
   - 노드 제거: 제거할 노드의 슬롯을 기존 마스터들에게 분배
   - 리밸런싱: `redis-cli --cluster rebalance` 명령어로 자동 조정

---

## 4. Python redis-py Cluster 사용법

### Decision: redis-py 5.0.1+ (Native Cluster Support)

### Rationale

1. **통합 라이브러리**: redis-py 4.1.0+부터 클러스터 모드 네이티브 지원
2. **redis-py-cluster 불필요**: 별도 라이브러리 아카이브됨 (2021년 이후)
3. **비동기 지원**: `redis.asyncio.cluster.RedisCluster`로 FastAPI와 완벽 통합
4. **자동 리다이렉션**: MOVED/ASK 응답 자동 처리

### 설치

```bash
# requirements.txt (이미 설치됨)
redis==5.0.1
```

### 동기 클라이언트 사용 예시

```python
from redis.cluster import RedisCluster

# 클러스터 연결 (시작 노드 1개만 명시하면 자동 탐색)
cluster = RedisCluster(
    host='localhost',
    port=7000,
    password='YOUR_PASSWORD',  # 프로덕션 환경
    decode_responses=True,     # 문자열 자동 디코딩
    skip_full_coverage_check=False,  # 전체 슬롯 커버리지 확인 (권장)
)

# 기본 작업 (단일 노드 Redis와 동일)
cluster.set("user:123:cart", '{"items": [1, 2, 3]}', ex=3600)
cart = cluster.get("user:123:cart")

# 해시 태그 활용 Multi-Key 작업
cluster.mset({
    "{user:123}:cart": '{"items": [1, 2, 3]}',
    "{user:123}:profile": '{"name": "홍길동"}',
})
cart, profile = cluster.mget("{user:123}:cart", "{user:123}:profile")

# 연결 종료
cluster.close()
```

### 비동기 클라이언트 사용 (FastAPI 통합)

#### 1. Redis Cluster 클라이언트 초기화 (utils/redis_cluster.py)

```python
"""
Redis Cluster 연결 풀 관리

비동기 Redis Cluster 클라이언트를 제공합니다.
FDS Velocity Check, 블랙리스트 캐싱에 사용됩니다.
"""

from typing import Optional, Any
import json
from redis.asyncio.cluster import RedisCluster
from redis.asyncio import ConnectionPool
from src.config import get_settings

settings = get_settings()

# 전역 Redis Cluster 클라이언트
_cluster_client: Optional[RedisCluster] = None


async def init_redis_cluster() -> RedisCluster:
    """
    Redis Cluster 클라이언트 초기화

    Returns:
        RedisCluster: Redis Cluster 클라이언트 인스턴스
    """
    global _cluster_client

    if _cluster_client is not None:
        return _cluster_client

    try:
        # 시작 노드 (클러스터 토폴로지 자동 탐색)
        startup_nodes = [
            {"host": "redis-node-1", "port": 7000},
            {"host": "redis-node-2", "port": 7001},
            {"host": "redis-node-3", "port": 7002},
        ]

        # Redis Cluster 클라이언트 생성
        _cluster_client = RedisCluster(
            startup_nodes=startup_nodes,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            skip_full_coverage_check=False,  # 전체 슬롯 커버리지 확인
            max_connections=50,              # 연결 풀 크기
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )

        # 연결 테스트
        await _cluster_client.ping()
        print("[OK] Redis Cluster 연결 성공")

        return _cluster_client

    except Exception as e:
        print(f"[FAIL] Redis Cluster 연결 실패: {e}")
        raise


async def close_redis_cluster() -> None:
    """
    Redis Cluster 연결 종료

    애플리케이션 종료 시 호출하여 리소스를 정리합니다.
    """
    global _cluster_client

    if _cluster_client:
        await _cluster_client.close()
        _cluster_client = None
        print("Redis Cluster 클라이언트 종료")


async def get_redis_cluster() -> RedisCluster:
    """
    Redis Cluster 클라이언트 가져오기 (FastAPI 의존성 주입용)

    Returns:
        RedisCluster: Redis Cluster 클라이언트
    """
    if _cluster_client is None:
        await init_redis_cluster()

    return _cluster_client


class RedisClusterCache:
    """
    Redis Cluster 캐싱 헬퍼 클래스

    JSON 직렬화/역직렬화를 자동으로 처리합니다.
    """

    def __init__(self, cluster: RedisCluster):
        self.cluster = cluster

    async def get(self, key: str, default: Any = None) -> Any:
        """캐시에서 값 가져오기"""
        try:
            value = await self.cluster.get(key)
            if value is None:
                return default

            # JSON 역직렬화 시도
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            print(f"Redis Cluster GET 실패: {key}, {e}")
            return default

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 저장"""
        try:
            # JSON 직렬화 시도
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)

            if ttl:
                await self.cluster.setex(key, ttl, value)
            else:
                await self.cluster.set(key, value)

            return True

        except Exception as e:
            print(f"Redis Cluster SET 실패: {key}, {e}")
            return False

    async def delete(self, key: str) -> bool:
        """캐시에서 키 삭제"""
        try:
            await self.cluster.delete(key)
            return True
        except Exception as e:
            print(f"Redis Cluster DELETE 실패: {key}, {e}")
            return False
```

#### 2. FastAPI 애플리케이션 통합 (main.py)

```python
from fastapi import FastAPI, Depends
from src.utils.redis_cluster import (
    init_redis_cluster,
    close_redis_cluster,
    get_redis_cluster,
    RedisClusterCache,
)

app = FastAPI()


@app.on_event("startup")
async def startup():
    """애플리케이션 시작 시 Redis Cluster 초기화"""
    await init_redis_cluster()


@app.on_event("shutdown")
async def shutdown():
    """애플리케이션 종료 시 Redis Cluster 연결 종료"""
    await close_redis_cluster()


@app.get("/velocity-check/{user_id}")
async def velocity_check(
    user_id: str,
    cluster: RedisCluster = Depends(get_redis_cluster)
):
    """
    Velocity Check: 사용자의 최근 1분간 거래 횟수 확인
    """
    key = f"velocity:user:{user_id}:1min"

    # 카운터 증가 (TTL 60초)
    count = await cluster.incr(key)

    # 첫 요청이면 만료 시간 설정
    if count == 1:
        await cluster.expire(key, 60)

    # 임계값 초과 시 고위험 판정
    is_suspicious = count > 5

    return {
        "user_id": user_id,
        "transaction_count": count,
        "is_suspicious": is_suspicious,
        "threshold": 5,
    }
```

### Implementation Notes

1. **startup_nodes**: 최소 1개 노드만 명시하면 클러스터 토폴로지 자동 탐색
   - 권장: 3개 마스터 모두 명시 (고가용성)

2. **skip_full_coverage_check**:
   - `False` (기본값): 전체 16,384 슬롯이 커버되지 않으면 에러 발생 (안전)
   - `True`: 일부 슬롯 누락 허용 (클러스터 재구성 중 사용)

3. **자동 리다이렉션**:
   - 클라이언트가 잘못된 노드에 요청 시 MOVED/ASK 응답 자동 처리
   - 애플리케이션 코드는 단일 Redis와 동일하게 작성 가능

---

## 5. 블랙리스트 TTL 전략

### Decision: SETEX 기반 자동 만료 + 계층별 TTL

### Rationale

1. **메모리 효율성**: 자동 만료로 오래된 블랙리스트 제거
2. **보안 유연성**: 위협 수준에 따라 차등 TTL 적용
3. **운영 자동화**: 수동 삭제 불필요

### TTL 전략 (위협 수준별)

| 블랙리스트 유형 | TTL | 사용 명령어 | 이유 |
|-----------------|-----|------------|------|
| **임시 IP 차단** | 1시간 (3,600초) | SETEX | 일시적 의심 IP (VPN, 공용 WiFi) |
| **사기 IP** | 7일 (604,800초) | SETEX | 과거 사기 거래 IP (재발 방지) |
| **영구 차단 IP** | 없음 (영구) | SET | APT 공격, 반복 사기범 |
| **도난 카드 BIN** | 30일 (2,592,000초) | SETEX | 카드사 신고 기간 (통상 30일) |
| **의심 이메일 도메인** | 90일 (7,776,000초) | SETEX | 임시 이메일 서비스 (guerrillamail 등) |

### SETEX vs SET + EXPIRE 비교

```python
# SETEX (권장): 원자적 저장 + TTL 설정
await cluster.setex("blacklist:ip:192.168.1.1", 3600, "fraud_detected")

# SET + EXPIRE (비권장): 경쟁 조건(race condition) 가능
await cluster.set("blacklist:ip:192.168.1.1", "fraud_detected")
await cluster.expire("blacklist:ip:192.168.1.1", 3600)
# 문제: SET과 EXPIRE 사이에 프로세스 종료 시 TTL 미설정 -> 메모리 누수
```

### 블랙리스트 서비스 구현 예시

```python
from enum import IntEnum
from redis.asyncio.cluster import RedisCluster
from typing import Optional


class ThreatLevel(IntEnum):
    """위협 수준 (TTL 결정용)"""
    TEMPORARY = 3600          # 1시간
    FRAUD = 604800            # 7일
    PERMANENT = 0             # 영구
    STOLEN_CARD = 2592000     # 30일
    SUSPICIOUS_EMAIL = 7776000  # 90일


class BlacklistService:
    """
    Redis Cluster 기반 블랙리스트 관리 서비스
    """

    def __init__(self, cluster: RedisCluster):
        self.cluster = cluster

    async def add_ip_blacklist(
        self,
        ip: str,
        threat_level: ThreatLevel,
        reason: str
    ) -> bool:
        """
        IP를 블랙리스트에 추가

        Args:
            ip: 차단할 IP 주소
            threat_level: 위협 수준 (TTL 결정)
            reason: 차단 이유 (로그용)

        Returns:
            bool: 성공 여부
        """
        key = f"blacklist:ip:{ip}"
        value = {
            "reason": reason,
            "threat_level": threat_level.name,
            "added_at": "2025-11-17T12:00:00Z",  # 실제로는 datetime.utcnow()
        }

        try:
            if threat_level == ThreatLevel.PERMANENT:
                # 영구 차단 (TTL 없음)
                await self.cluster.set(key, json.dumps(value, ensure_ascii=False))
            else:
                # 자동 만료 (SETEX)
                await self.cluster.setex(
                    key,
                    threat_level.value,
                    json.dumps(value, ensure_ascii=False)
                )

            print(f"[OK] IP 블랙리스트 추가: {ip} (TTL: {threat_level.value}s)")
            return True

        except Exception as e:
            print(f"[FAIL] IP 블랙리스트 추가 실패: {ip}, {e}")
            return False

    async def is_ip_blacklisted(self, ip: str) -> tuple[bool, Optional[dict]]:
        """
        IP가 블랙리스트에 있는지 확인

        Args:
            ip: 확인할 IP 주소

        Returns:
            tuple: (블랙리스트 여부, 상세 정보)
        """
        key = f"blacklist:ip:{ip}"

        try:
            value = await self.cluster.get(key)
            if value is None:
                return False, None

            # JSON 역직렬화
            detail = json.loads(value)

            # 남은 TTL 확인 (선택사항)
            ttl = await self.cluster.ttl(key)
            detail["ttl_remaining"] = ttl

            return True, detail

        except Exception as e:
            print(f"[FAIL] IP 블랙리스트 조회 실패: {ip}, {e}")
            # Fail Open: Redis 오류 시 요청 허용 (보안 < 가용성)
            return False, None

    async def remove_ip_blacklist(self, ip: str) -> bool:
        """
        IP를 블랙리스트에서 제거 (오탐 처리용)

        Args:
            ip: 제거할 IP 주소

        Returns:
            bool: 성공 여부
        """
        key = f"blacklist:ip:{ip}"

        try:
            await self.cluster.delete(key)
            print(f"[OK] IP 블랙리스트 제거: {ip}")
            return True

        except Exception as e:
            print(f"[FAIL] IP 블랙리스트 제거 실패: {ip}, {e}")
            return False

    async def extend_ip_blacklist_ttl(self, ip: str, additional_seconds: int) -> bool:
        """
        IP 블랙리스트 TTL 연장 (재범 시)

        Args:
            ip: IP 주소
            additional_seconds: 추가 TTL (초)

        Returns:
            bool: 성공 여부
        """
        key = f"blacklist:ip:{ip}"

        try:
            # 현재 TTL 조회
            current_ttl = await self.cluster.ttl(key)
            if current_ttl < 0:
                # TTL 없음 (영구 차단) 또는 키 없음
                return False

            # 새 TTL 설정
            new_ttl = current_ttl + additional_seconds
            await self.cluster.expire(key, new_ttl)

            print(f"[OK] IP 블랙리스트 TTL 연장: {ip} (+{additional_seconds}s)")
            return True

        except Exception as e:
            print(f"[FAIL] IP 블랙리스트 TTL 연장 실패: {ip}, {e}")
            return False
```

### 사용 예시 (FDS 엔진 통합)

```python
from fastapi import Depends
from src.services.blacklist_service import BlacklistService, ThreatLevel

@app.post("/fds/evaluate")
async def evaluate_transaction(
    transaction: TransactionRequest,
    blacklist: BlacklistService = Depends(get_blacklist_service)
):
    """
    거래 위험도 평가 (블랙리스트 체크 포함)
    """
    # 1. IP 블랙리스트 확인
    is_blacklisted, detail = await blacklist.is_ip_blacklisted(transaction.ip)

    if is_blacklisted:
        return {
            "decision": "block",
            "risk_score": 100,
            "reason": f"IP 블랙리스트: {detail['reason']}",
            "ttl_remaining": detail["ttl_remaining"],
        }

    # 2. 정상 FDS 평가 진행...
    risk_score = await evaluate_risk(transaction)

    # 3. 고위험 판정 시 블랙리스트 추가
    if risk_score >= 90:
        await blacklist.add_ip_blacklist(
            ip=transaction.ip,
            threat_level=ThreatLevel.FRAUD,
            reason="High risk score detected"
        )

    return {
        "decision": "approve" if risk_score < 50 else "review",
        "risk_score": risk_score,
    }
```

### Implementation Notes

1. **SETEX vs PSETEX**:
   - SETEX: 초 단위 TTL (충분한 정밀도)
   - PSETEX: 밀리초 단위 TTL (OTP, 세션 등 짧은 TTL용)

2. **TTL 확인 명령어**:
   ```python
   ttl = await cluster.ttl("blacklist:ip:192.168.1.1")
   # -2: 키 없음
   # -1: TTL 없음 (영구)
   # >0: 남은 시간 (초)
   ```

3. **메모리 정책 설정** (redis.conf):
   ```bash
   maxmemory 2gb
   maxmemory-policy volatile-lru  # TTL 설정된 키 중 LRU 제거 (권장)
   # 또는
   maxmemory-policy allkeys-lru   # 모든 키 중 LRU 제거
   ```

4. **배치 삭제** (만료 전 수동 정리):
   ```python
   # SCAN으로 패턴 매칭 키 조회 (KEYS는 프로덕션 금지, 블로킹)
   async for key in cluster.scan_iter(match="blacklist:ip:*", count=100):
       ttl = await cluster.ttl(key)
       if 0 < ttl < 3600:  # 1시간 미만 남은 키 삭제
           await cluster.delete(key)
   ```

---

## 6. 페일오버 시나리오

### Automatic Failover Process

Redis Cluster는 **자동 페일오버**를 통해 마스터 장애 시 레플리카를 자동으로 승격합니다.

### 페일오버 발생 조건

1. **노드 장애 감지**:
   - 마스터 노드가 `cluster-node-timeout` (기본 5초) 동안 응답 없음
   - 과반수 마스터 노드가 장애를 확인 (Gossip Protocol)

2. **레플리카 승격 투표**:
   - 장애 마스터의 레플리카들이 승격 후보로 등록
   - 다른 마스터 노드들이 투표 (과반수 동의 필요)
   - 가장 최신 데이터를 가진 레플리카가 승격

3. **클라이언트 리다이렉션**:
   - 새 마스터가 슬롯 소유권 획득
   - 클라이언트는 MOVED 응답으로 새 마스터 주소 인지
   - redis-py는 자동으로 새 마스터에 재연결

### 페일오버 타임라인

```
[T+0s] 마스터 노드 7000 장애 발생
[T+1s] 다른 노드들이 7000에 PING 전송 (응답 없음)
[T+5s] cluster-node-timeout 초과 -> 장애 감지
[T+6s] 레플리카 7003이 승격 요청 (FAILOVER_AUTH_REQUEST)
[T+6.5s] 마스터 7001, 7002가 7003에 투표
[T+7s] 7003이 과반수 득표 -> 새 마스터로 승격
[T+7.5s] 7003이 슬롯 0~5460 소유권 선언 (CLUSTER NODES 업데이트)
[T+8s] 클라이언트가 슬롯 1234 요청 시 7003으로 리다이렉션
```

**총 다운타임**: 약 **5~10초** (cluster-node-timeout 설정에 따라 조정 가능)

### 페일오버 시나리오 상세

#### 시나리오 1: 마스터 1대 다운 (정상 페일오버)

**초기 상태**:
```
Master 1 (7000) -> Replica 1 (7003)  [Slots: 0-5460]
Master 2 (7001) -> Replica 2 (7004)  [Slots: 5461-10922]
Master 3 (7002) -> Replica 3 (7005)  [Slots: 10923-16383]
```

**Master 1 (7000) 장애 발생**:
```bash
# 장애 시뮬레이션
redis-cli -p 7000 DEBUG SLEEP 30  # 30초 동안 응답 중지
# 또는
kill -9 $(pgrep -f redis-7000)    # 프로세스 강제 종료
```

**페일오버 후 상태**:
```
Replica 1 (7003) -> [NEW MASTER]    [Slots: 0-5460]
Master 2 (7001) -> Replica 2 (7004) [Slots: 5461-10922]
Master 3 (7002) -> Replica 3 (7005) [Slots: 10923-16383]

Master 1 (7000) -> [FAIL, DISCONNECTED]
```

**클러스터 상태 확인**:
```bash
redis-cli -c -p 7003 cluster nodes

# Expected Output:
# a1b2c3... 127.0.0.1:7003@17003 myself,master - 0 0 7 connected 0-5460
# a1b2c3... 127.0.0.1:7000@17000 master,fail - 1700000000 1700000000 1 disconnected
```

#### 시나리오 2: 마스터 복구 (자동 레플리카 재구성)

**Master 1 (7000) 재시작**:
```bash
redis-server ./redis-7000.conf &
```

**복구 후 상태**:
```
Master 1 (7003) -> Replica 1 (7000) [Slots: 0-5460]  <- 역할 변경!
Master 2 (7001) -> Replica 2 (7004) [Slots: 5461-10922]
Master 3 (7002) -> Replica 3 (7005) [Slots: 10923-16383]
```

**주의**:
- 7000은 레플리카로 복귀 (마스터가 아님!)
- 원래 마스터로 되돌리려면 **수동 페일오버** 필요:
  ```bash
  redis-cli -c -p 7000 CLUSTER FAILOVER TAKEOVER
  ```

#### 시나리오 3: 마스터 + 레플리카 동시 다운 (슬롯 커버리지 손실)

**Master 1 (7000) + Replica 1 (7003) 동시 장애**:
```bash
kill -9 $(pgrep -f redis-7000)
kill -9 $(pgrep -f redis-7003)
```

**결과**:
```
[CRITICAL] 슬롯 0-5460 커버리지 손실!
cluster_state: fail
cluster_slots_fail: 5461
```

**클라이언트 동작**:
- `cluster-require-full-coverage yes` (기본값):
  - **모든 요청 거부** (CLUSTERDOWN 에러)
  - "Not all 16384 slots are covered" 에러 메시지

- `cluster-require-full-coverage no`:
  - 슬롯 5461~16383만 정상 서비스 (부분 가용성)
  - 슬롯 0~5460 요청 시에만 에러

### Failover 설정 최적화

```bash
# redis.conf (프로덕션 권장 설정)

# 노드 장애 감지 시간 (기본 5초)
cluster-node-timeout 5000  # 5초 (빠른 페일오버)
# 주의: 너무 짧으면 네트워크 지연 시 오탐 발생

# 레플리카 유효성 검증 (마스터와 동기화 시간)
cluster-replica-validity-factor 10
# 계산식: (node-timeout * validity-factor) + repl-ping-period
# 예: (5000ms * 10) + 1000ms = 51초
# 의미: 마스터와 51초 이상 동기화 안 되면 승격 불가

# 레플리카 우선순위 (낮을수록 우선 승격)
cluster-replica-priority 100
# 0: 승격 불가 (읽기 전용 레플리카)
# 100: 기본값

# 전체 슬롯 커버리지 요구 (권장: yes)
cluster-require-full-coverage yes
```

### Manual Failover (계획된 유지보수)

마스터 노드를 안전하게 재시작하려면 **수동 페일오버**를 먼저 실행:

```bash
# 1. 레플리카에서 수동 페일오버 실행
redis-cli -c -p 7003 CLUSTER FAILOVER

# 2. 7003이 마스터로 승격된 후 7000 재시작
redis-cli -p 7000 SHUTDOWN NOSAVE
# 서버 업데이트, 설정 변경 등...
redis-server ./redis-7000.conf &

# 3. 7000이 레플리카로 복귀 확인
redis-cli -c -p 7000 CLUSTER NODES
```

### Implementation Notes

1. **Gossip Protocol**:
   - 노드들이 Cluster Bus Port (17000~17005)로 상태 정보 교환
   - 방화벽에서 Client Port + Cluster Bus Port 모두 허용 필수

2. **Split Brain 방지**:
   - 과반수 마스터 동의 필요 (최소 3개 마스터 권장)
   - 네트워크 파티션 시 소수 그룹은 쓰기 거부

3. **데이터 손실 가능성**:
   - 비동기 복제: 마스터 장애 직전 쓰기는 레플리카에 미도달 가능
   - 최소화 방법: `min-replicas-to-write 1` 설정 (레플리카 1개 이상 확인 후 쓰기)

---

## 7. cluster-require-full-coverage 설정

### Decision: `cluster-require-full-coverage no` (프로덕션)

### Rationale

1. **부분 가용성 보장**:
   - 일부 슬롯 손실 시에도 나머지 슬롯은 정상 서비스
   - 예: 슬롯 0~5460 손실 시, 슬롯 5461~16383은 정상 동작

2. **점진적 복구**:
   - 장애 노드 복구 중에도 서비스 지속 가능
   - 사용자 영향 최소화

3. **운영 유연성**:
   - 클러스터 재구성(리샤딩) 중에도 서비스 가능
   - 노드 추가/제거 작업 시 다운타임 없음

### Trade-offs

| 설정 | 장점 | 단점 | 권장 사용 |
|------|------|------|-----------|
| **yes (기본값)** | Fail-Fast 철학, 문제 조기 발견, 일관된 에러 응답 | 일부 슬롯 손실 시 전체 서비스 중단 | 개발/테스트 환경 |
| **no** | 부분 가용성, 점진적 복구, 사용자 영향 최소화 | 슬롯 누락 시 일부 키 접근 불가 (에러 발생) | 프로덕션 환경 (권장) |

### 설정 방법

```bash
# redis.conf 수정
cluster-require-full-coverage no

# 또는 런타임 설정 변경 (모든 노드에 적용)
redis-cli -c -p 7000 CONFIG SET cluster-require-full-coverage no
redis-cli -c -p 7001 CONFIG SET cluster-require-full-coverage no
redis-cli -c -p 7002 CONFIG SET cluster-require-full-coverage no
redis-cli -c -p 7003 CONFIG SET cluster-require-full-coverage no
redis-cli -c -p 7004 CONFIG SET cluster-require-full-coverage no
redis-cli -c -p 7005 CONFIG SET cluster-require-full-coverage no

# 설정 영구 저장
redis-cli -c -p 7000 CONFIG REWRITE
```

### 부분 슬롯 손실 시 클라이언트 동작

#### cluster-require-full-coverage yes (기본값)

```python
cluster = RedisCluster(host='localhost', port=7000)

# 슬롯 0~5460 손실 상황
try:
    # 슬롯 1234 (손실된 슬롯)
    cluster.get("user:123:cart")  # 슬롯 1234
except Exception as e:
    print(e)
    # ClusterDownError: CLUSTERDOWN Hash slot not served
    # 전체 클러스터 다운으로 간주!

try:
    # 슬롯 8000 (정상 슬롯)
    cluster.get("user:456:profile")  # 슬롯 8000
except Exception as e:
    print(e)
    # ClusterDownError: CLUSTERDOWN Hash slot not served
    # 정상 슬롯도 접근 불가!
```

#### cluster-require-full-coverage no (권장)

```python
cluster = RedisCluster(host='localhost', port=7000)

# 슬롯 0~5460 손실 상황
try:
    # 슬롯 1234 (손실된 슬롯)
    cluster.get("user:123:cart")  # 슬롯 1234
except Exception as e:
    print(e)
    # ClusterError: No node available for slot 1234
    # 해당 슬롯만 에러!

# 슬롯 8000 (정상 슬롯)
profile = cluster.get("user:456:profile")  # 슬롯 8000
print(profile)
# 정상 응답: {"name": "김철수"}
```

### Graceful Degradation 구현

```python
from redis.asyncio.cluster import RedisCluster
from redis.exceptions import ClusterError

async def get_user_cart(user_id: str, cluster: RedisCluster):
    """
    사용자 장바구니 조회 (Graceful Degradation)
    """
    key = f"user:{user_id}:cart"

    try:
        cart = await cluster.get(key)
        return cart

    except ClusterError as e:
        # 슬롯 커버리지 손실 (부분 장애)
        if "No node available for slot" in str(e):
            print(f"[WARNING] 슬롯 손실로 인한 캐시 미스: {user_id}")
            # Fallback: 데이터베이스에서 직접 조회
            cart = await db.get_cart(user_id)
            return cart
        else:
            # 전체 클러스터 다운 (cluster-require-full-coverage yes)
            print(f"[CRITICAL] Redis Cluster 전체 다운")
            raise

    except Exception as e:
        # 기타 네트워크 오류
        print(f"[ERROR] Redis Cluster 접근 실패: {e}")
        # Fail Open: Redis 오류 시 DB로 폴백
        return await db.get_cart(user_id)
```

### Monitoring (슬롯 커버리지 감시)

```python
async def check_cluster_health(cluster: RedisCluster):
    """
    클러스터 건강 상태 확인 (Prometheus 메트릭)
    """
    try:
        info = await cluster.cluster_info()

        # 슬롯 커버리지 확인
        slots_assigned = int(info.get("cluster_slots_assigned", 0))
        slots_ok = int(info.get("cluster_slots_ok", 0))
        slots_fail = int(info.get("cluster_slots_fail", 0))

        if slots_fail > 0:
            # 슬롯 손실 알림 (Slack, PagerDuty 등)
            alert_ops(
                severity="critical",
                message=f"Redis Cluster 슬롯 손실: {slots_fail}/16384"
            )

        return {
            "cluster_state": info.get("cluster_state"),
            "slots_assigned": slots_assigned,
            "slots_ok": slots_ok,
            "slots_fail": slots_fail,
            "coverage_percentage": (slots_ok / 16384) * 100,
        }

    except Exception as e:
        print(f"[FAIL] 클러스터 상태 확인 실패: {e}")
        return None
```

### Implementation Notes

1. **리샤딩 중 설정**:
   ```bash
   # 리샤딩 전 임시로 no 설정
   redis-cli -c -p 7000 CONFIG SET cluster-require-full-coverage no

   # 리샤딩 실행
   redis-cli --cluster reshard 127.0.0.1:7000

   # 리샤딩 완료 후 yes 복원 (선택사항)
   redis-cli -c -p 7000 CONFIG SET cluster-require-full-coverage yes
   ```

2. **클라이언트 설정**:
   ```python
   # redis-py에서는 skip_full_coverage_check 파라미터로 제어
   cluster = RedisCluster(
       host='localhost',
       port=7000,
       skip_full_coverage_check=True,  # cluster-require-full-coverage no와 동일
   )
   ```

3. **알림 전략**:
   - `cluster_slots_fail > 0`: Critical 알림 (즉시 대응)
   - `cluster_state: fail`: 전체 클러스터 다운 (최우선 대응)
   - `coverage_percentage < 100%`: Warning 알림 (모니터링)

---

## 8. 프로덕션 배포 아키텍처

### Kubernetes StatefulSet 배포

```yaml
# infrastructure/k8s/redis-cluster.yaml

apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cluster
  namespace: shopfds
spec:
  serviceName: redis-cluster
  replicas: 6
  selector:
    matchLabels:
      app: redis-cluster
  template:
    metadata:
      labels:
        app: redis-cluster
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
          name: client
        - containerPort: 16379
          name: cluster-bus
        command:
        - redis-server
        args:
        - /conf/redis.conf
        - --cluster-enabled
        - "yes"
        - --cluster-config-file
        - /data/nodes.conf
        - --cluster-node-timeout
        - "5000"
        - --cluster-require-full-coverage
        - "no"
        - --appendonly
        - "yes"
        - --maxmemory
        - "2gb"
        - --maxmemory-policy
        - "volatile-lru"
        volumeMounts:
        - name: redis-data
          mountPath: /data
        - name: redis-config
          mountPath: /conf
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          tcpSocket:
            port: 6379
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "fast-ssd"
      resources:
        requests:
          storage: 10Gi

---
apiVersion: v1
kind: Service
metadata:
  name: redis-cluster
  namespace: shopfds
spec:
  type: ClusterIP
  clusterIP: None  # Headless Service (StatefulSet DNS)
  ports:
  - port: 6379
    targetPort: 6379
    name: client
  - port: 16379
    targetPort: 16379
    name: cluster-bus
  selector:
    app: redis-cluster
```

### 클러스터 초기화 Job

```yaml
# infrastructure/k8s/redis-cluster-init.yaml

apiVersion: batch/v1
kind: Job
metadata:
  name: redis-cluster-init
  namespace: shopfds
spec:
  template:
    spec:
      containers:
      - name: redis-cli
        image: redis:7-alpine
        command:
        - /bin/sh
        - -c
        - |
          redis-cli --cluster create \
            redis-cluster-0.redis-cluster.shopfds.svc.cluster.local:6379 \
            redis-cluster-1.redis-cluster.shopfds.svc.cluster.local:6379 \
            redis-cluster-2.redis-cluster.shopfds.svc.cluster.local:6379 \
            redis-cluster-3.redis-cluster.shopfds.svc.cluster.local:6379 \
            redis-cluster-4.redis-cluster.shopfds.svc.cluster.local:6379 \
            redis-cluster-5.redis-cluster.shopfds.svc.cluster.local:6379 \
            --cluster-replicas 1 \
            --cluster-yes
      restartPolicy: OnFailure
```

---

## 9. 운영 가이드

### 클러스터 상태 확인

```bash
# 클러스터 정보
redis-cli -c -p 7000 CLUSTER INFO

# 노드 목록 및 역할
redis-cli -c -p 7000 CLUSTER NODES

# 슬롯 분배 확인
redis-cli -c -p 7000 CLUSTER SLOTS
```

### 노드 추가 (스케일 아웃)

```bash
# 1. 새 노드 시작 (7006, 7007)
redis-server ./redis-7006.conf &
redis-server ./redis-7007.conf &

# 2. 클러스터에 마스터 추가
redis-cli --cluster add-node 127.0.0.1:7006 127.0.0.1:7000

# 3. 슬롯 재분배 (기존 마스터들에서 슬롯 이동)
redis-cli --cluster reshard 127.0.0.1:7000
# 대화형 프롬프트:
# How many slots do you want to move? 2730  # (16384 / 6 마스터 = 약 2730)
# What is the receiving node ID? <7006의 Node ID>
# Source node #1: all  # 모든 마스터에서 균등하게 가져옴

# 4. 레플리카 추가
redis-cli --cluster add-node 127.0.0.1:7007 127.0.0.1:7000 --cluster-slave --cluster-master-id <7006의 Node ID>

# 5. 재분배 확인
redis-cli --cluster check 127.0.0.1:7000
```

### 노드 제거 (스케일 인)

```bash
# 1. 슬롯 이동 (제거할 노드의 슬롯을 다른 노드로)
redis-cli --cluster reshard 127.0.0.1:7000
# 대화형 프롬프트:
# How many slots do you want to move? 2730  # 제거할 노드의 슬롯 개수
# What is the receiving node ID? <받을 마스터 Node ID>
# Source node #1: <제거할 노드 ID>
# Source node #2: done

# 2. 레플리카 제거
redis-cli --cluster del-node 127.0.0.1:7000 <레플리카 Node ID>

# 3. 마스터 제거 (슬롯 0개 확인 후)
redis-cli --cluster del-node 127.0.0.1:7000 <마스터 Node ID>
```

### 클러스터 재조정

```bash
# 슬롯 균등 분배 (자동)
redis-cli --cluster rebalance 127.0.0.1:7000
```

---

## 10. 모니터링 및 알림

### Prometheus 메트릭

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'redis-cluster'
    static_configs:
      - targets:
        - 'redis-node-1:6379'
        - 'redis-node-2:6379'
        - 'redis-node-3:6379'
        - 'redis-node-4:6379'
        - 'redis-node-5:6379'
        - 'redis-node-6:6379'
    metrics_path: '/metrics'
    scheme: 'http'
```

### 주요 메트릭

| 메트릭 | 설명 | 임계값 | 알림 |
|--------|------|--------|------|
| `cluster_state` | 클러스터 상태 (ok/fail) | fail | Critical |
| `cluster_slots_fail` | 실패한 슬롯 수 | > 0 | Critical |
| `cluster_known_nodes` | 알려진 노드 수 | < 6 | Warning |
| `used_memory` | 사용 메모리 | > 80% | Warning |
| `connected_clients` | 연결된 클라이언트 수 | > 10,000 | Warning |
| `keyspace_hits_rate` | 캐시 히트율 | < 80% | Info |

### Grafana 대시보드

- Redis Cluster Overview: 노드 상태, 슬롯 분배, 메모리 사용량
- Performance Metrics: 초당 명령어 수, 응답 시간, 네트워크 I/O
- Failover History: 페일오버 발생 이력, 복구 시간

---

## 11. 보안 강화

### 1. 인증 설정

```bash
# redis.conf
requirepass YOUR_STRONG_PASSWORD_HERE
masterauth YOUR_STRONG_PASSWORD_HERE
```

### 2. 네트워크 격리

```bash
# redis.conf
bind 10.0.1.0/24  # 내부 네트워크만 허용
protected-mode yes

# 방화벽 설정 (iptables)
iptables -A INPUT -p tcp --dport 6379 -s 10.0.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 6379 -j DROP
```

### 3. TLS 암호화 (Redis 6.0+)

```bash
# redis.conf
tls-port 6380
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt
tls-cluster yes
```

### 4. 위험 명령어 비활성화

```bash
# redis.conf
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG "CONFIG_SECRET_NAME"
rename-command SHUTDOWN "SHUTDOWN_SECRET_NAME"
```

---

## 12. 성능 최적화

### 1. 메모리 최적화

```bash
# redis.conf
maxmemory 2gb
maxmemory-policy volatile-lru  # TTL 있는 키만 제거
activedefrag yes               # 메모리 단편화 방지 (Redis 4.0+)
```

### 2. Persistence 전략

```bash
# AOF + RDB 하이브리드 (권장)
appendonly yes
appendfsync everysec           # 1초마다 fsync (성능 vs 안정성 균형)
save 900 1                     # 900초 동안 1개 이상 변경 시 스냅샷
save 300 10
save 60 10000
```

### 3. Connection Pool 최적화

```python
cluster = RedisCluster(
    host='localhost',
    port=7000,
    max_connections=50,        # 연결 풀 크기 (애플리케이션당)
    socket_timeout=5.0,        # 읽기/쓰기 타임아웃
    socket_connect_timeout=5.0,  # 연결 타임아웃
)
```

---

## 13. 참고 자료

- [Redis Cluster Specification](https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/)
- [Redis Cluster Tutorial](https://redis.io/docs/latest/operate/oss_and_stack/management/scaling/)
- [redis-py Clustering Documentation](https://redis.readthedocs.io/en/stable/clustering.html)
- [Redis Cluster Best Practices](https://www.dragonflydb.io/guides/redis-best-practices)
- [Handling Redis Failover](https://binaryscripts.com/redis/2025/05/25/handling-redis-failover-and-recovery-strategies-for-minimizing-downtime.html)

---

## 14. 다음 단계

- [x] Redis Cluster 아키텍처 리서치 완료
- [ ] Kubernetes StatefulSet 배포 구현
- [ ] Prometheus + Grafana 모니터링 구성
- [ ] Python 애플리케이션에 RedisCluster 통합
- [ ] 블랙리스트 서비스 구현 (TTL 전략 적용)
- [ ] Failover 시나리오 테스트 (Chaos Engineering)
