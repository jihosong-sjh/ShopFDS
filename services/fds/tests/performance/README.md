# FDS 성능 테스트 가이드

T116: FDS 평가 엔진의 성능을 검증하는 테스트 모음입니다.

## 성능 목표

- **평균 응답 시간**: 50ms 이내
- **P95 응답 시간**: 100ms 이내 (이상적: 50ms)
- **처리량**: 1,000 TPS 이상
- **실패율**: 0%

## 테스트 종류

### 1. pytest-benchmark 성능 테스트

단위 성능 측정 및 회귀 방지 테스트입니다.

#### 실행 방법

```bash
# 기본 실행
cd services/fds
pytest tests/performance/test_fds_performance.py -v

# 벤치마크 통계 포함
pytest tests/performance/test_fds_performance.py -v --benchmark-only

# 상세 출력
pytest tests/performance/test_fds_performance.py -v -s
```

#### 포함된 테스트

1. **단일 평가 성능**: 100회 반복 측정, P95 계산
2. **동시 평가 성능**: 100개 동시 요청 처리 능력
3. **고부하 시나리오**: 1,000개 요청 순차 처리, 일관성 검증
4. **CTI 체크 성능**: CTI 체크 시간 및 비중 측정
5. **성능 종합 요약**: 목표 달성 여부 확인

#### 예상 결과

```
[성능 테스트 1] 단일 평가 성능
  - 평균: 25.34ms
  - P95: 45.67ms
  - 최소: 15ms
  - 최대: 78ms
  - 목표: P95 < 100ms (이상적: 50ms)
  [PASS] 단일 평가 성능 목표 달성

[성능 테스트 2] 동시 평가 성능 (100개 동시 요청)
  - 총 요청 수: 100
  - 총 처리 시간: 543.21ms
  - 처리량: 184.12 TPS
  - 평균 응답 시간: 28.45ms
  - P95 응답 시간: 52.34ms
  [PASS] 동시 평가 성능 검증 완료
```

### 2. Locust 부하 테스트

실제 운영 환경 시뮬레이션 및 고부하 테스트입니다.

#### 사전 준비

```bash
# Locust 설치
pip install locust

# FDS 서비스 실행
cd services/fds
python src/main.py
```

#### 실행 방법

**웹 UI 모드** (권장):

```bash
cd services/fds
locust -f tests/performance/locustfile.py --host=http://localhost:8001
```

1. 브라우저에서 http://localhost:8089 접속
2. Number of users: 100 (동시 사용자 수)
3. Spawn rate: 10 (초당 증가 사용자 수)
4. Host: http://localhost:8001
5. "Start swarming" 클릭

**헤드리스 모드** (CI/CD):

```bash
cd services/fds
locust -f tests/performance/locustfile.py \
    --host=http://localhost:8001 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --headless \
    --html reports/locust_report.html \
    --csv reports/locust_stats
```

#### 테스트 시나리오

1. **정상 거래** (가중치 10): 50,000원, 정상 IP
2. **고액 거래** (가중치 5): 1,000,000원, 중간 위험
3. **의심스러운 거래** (가중치 2): 5,000,000원, TOR IP
4. **연속 거래** (가중치 1): Velocity Check 테스트

#### 예상 결과

```
[부하 테스트 성능 요약]
================================================================================
총 요청 수: 50000
성공: 49950 (99.9%)
실패: 50 (0.1%)

[응답 시간]
평균: 32.45ms
P95: 67.89ms
최소: 12.34ms
최대: 145.67ms

[목표 달성 여부]
1. 평균 응답 시간 < 50ms: [OK] (32.45ms)
2. P95 응답 시간 < 100ms: [OK] (67.89ms)
3. 실패율 < 1%: [OK] (0.10%)
================================================================================
```

#### Locust 웹 UI 주요 지표

- **RPS (Requests Per Second)**: 초당 요청 수
- **Response Time**: 응답 시간 분포 차트
- **Number of Users**: 현재 동시 사용자 수
- **Failures**: 실패한 요청 수 및 이유

## 성능 최적화 팁

### 현재 성능이 목표에 미달할 경우

#### 1. Redis 캐싱 활용도 증가

```python
# CTI 체크 결과 캐싱 (TTL: 1시간)
await redis.setex(f"cti:ip:{ip_address}", 3600, json.dumps(cti_result))

# 블랙리스트 캐싱 (TTL: 24시간)
await redis.setex(f"blacklist:device:{device_id}", 86400, "true")
```

#### 2. CTI 체크 타임아웃 조정

```python
# src/engines/cti_connector.py
TIMEOUT = 3.0  # 5초 -> 3초로 단축
```

#### 3. 불필요한 DB 쿼리 제거

```python
# Lazy loading 대신 Eager loading 사용
transaction = await db.execute(
    select(Transaction)
    .options(selectinload(Transaction.risk_factors))
    .where(Transaction.id == transaction_id)
)
```

#### 4. 비동기 처리 확장

```python
# 여러 CTI 소스 병렬 조회
results = await asyncio.gather(
    cti_connector.check_abuseipdb(ip),
    cti_connector.check_virustotal(ip),
    return_exceptions=True,
)
```

## 성능 회귀 방지

### CI/CD 파이프라인 통합

```yaml
# .github/workflows/performance-test.yml
- name: Run Performance Tests
  run: |
    cd services/fds
    pytest tests/performance/test_fds_performance.py --benchmark-only

    # 성능 기준 검증
    if [ $P95_TIME -gt 100 ]; then
      echo "Performance regression detected!"
      exit 1
    fi
```

### 성능 모니터링 대시보드

Grafana 대시보드에서 실시간 성능 지표를 모니터링합니다:

- **FDS 평가 시간**: P50, P95, P99
- **CTI 체크 시간**: 평균, 최대
- **처리량**: TPS (Transactions Per Second)
- **에러율**: 실패한 평가 비율

## 문제 해결

### 1. 평균 응답 시간 > 100ms

**원인**:
- CTI 체크 타임아웃 너무 김
- DB 쿼리 N+1 문제
- Redis 캐시 미스율 높음

**해결**:
- CTI 타임아웃 3초로 단축
- Eager loading 적용
- 캐시 TTL 증가

### 2. P95 응답 시간 > 100ms

**원인**:
- 외부 API (CTI) 응답 지연
- DB 연결 풀 부족
- 동시 요청 처리 병목

**해결**:
- CTI 체크 비동기 병렬 처리
- DB 연결 풀 크기 증가 (10 -> 20)
- 비동기 작업 최적화

### 3. 처리량 < 1,000 TPS

**원인**:
- 단일 서버 CPU 제약
- DB 쿼리 느림
- 동기 처리 병목

**해결**:
- 수평 확장 (여러 인스턴스)
- DB 인덱스 추가
- 비동기 처리 확장

## 참고 자료

- [pytest-benchmark 문서](https://pytest-benchmark.readthedocs.io/)
- [Locust 문서](https://docs.locust.io/)
- [성능 최적화 가이드](../../../docs/performance-optimization.md)
- [Prometheus 메트릭](../../../infrastructure/monitoring/prometheus.yml)
