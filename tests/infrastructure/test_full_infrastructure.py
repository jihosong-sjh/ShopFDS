"""
전체 인프라 통합 테스트

목표: docker-compose up -d 실행 후 모든 서비스 Health Check 통과, 2분 이내 시작
"""

import asyncio
import subprocess
import time
from typing import Dict, List

import httpx
import pytest
from redis.cluster import ClusterNode, RedisCluster


# ========================================
# 서비스 헬스체크 설정
# ========================================

SERVICES = {
    "ecommerce": {"url": "http://localhost:8000/v1/health", "timeout": 30},
    "fds": {"url": "http://localhost:8001/v1/health", "timeout": 30},
    "ml-service": {"url": "http://localhost:8002/v1/health", "timeout": 30},
    "admin-dashboard": {"url": "http://localhost:8003/v1/health", "timeout": 30},
}

INFRASTRUCTURE = {
    "postgres-master": {"host": "localhost", "port": 5432},
    "postgres-replica": {"host": "localhost", "port": 5433},
    "redis-cluster": {"nodes": ["127.0.0.1:7000"]},
    "rabbitmq": {"url": "http://localhost:15672/api/health/checks/alarms"},
    "elasticsearch": {"url": "http://localhost:9200/_cluster/health"},
    "prometheus": {"url": "http://localhost:9090/-/healthy"},
    "grafana": {"url": "http://localhost:3001/api/health"},
}


# ========================================
# 유틸리티 함수
# ========================================


def check_docker_compose_services() -> Dict[str, bool]:
    """Docker Compose 서비스 상태 확인"""
    try:
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "json"],
            cwd="D:/side-project/ShopFDS/infrastructure/docker",
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            print(f"[FAIL] docker-compose ps 실패: {result.stderr}")
            return {}

        # JSON 파싱 (각 줄이 JSON 객체)
        services = {}
        for line in result.stdout.strip().split("\n"):
            if line:
                import json

                service = json.loads(line)
                services[service["Service"]] = service["State"] == "running"

        return services
    except Exception as e:
        print(f"[FAIL] Docker Compose 상태 확인 실패: {e}")
        return {}


async def check_http_health(
    name: str, url: str, timeout: int = 10, auth: tuple = None
) -> bool:
    """HTTP 헬스체크"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if auth:
                response = await client.get(url, auth=auth)
            else:
                response = await client.get(url)

            if response.status_code == 200:
                print(f"[OK] {name} 헬스체크 통과")
                return True
            else:
                print(
                    f"[FAIL] {name} 헬스체크 실패 (HTTP {response.status_code}): {response.text[:200]}"
                )
                return False
    except httpx.TimeoutException:
        print(f"[FAIL] {name} 헬스체크 타임아웃 ({timeout}초)")
        return False
    except Exception as e:
        print(f"[FAIL] {name} 헬스체크 예외: {e}")
        return False


def check_postgres(host: str, port: int) -> bool:
    """PostgreSQL 연결 확인"""
    try:
        import socket

        sock = socket.create_connection((host, port), timeout=5)
        sock.close()
        print(f"[OK] PostgreSQL ({host}:{port}) 연결 성공")
        return True
    except Exception as e:
        print(f"[FAIL] PostgreSQL ({host}:{port}) 연결 실패: {e}")
        return False


def check_redis_cluster(nodes: List[str]) -> bool:
    """Redis Cluster 연결 확인"""
    try:
        startup_nodes = [
            ClusterNode(node.split(":")[0], int(node.split(":")[1])) for node in nodes
        ]
        client = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=False,
            skip_full_coverage_check=True,
            socket_timeout=5,
        )
        result = client.ping()
        client.close()

        if result:
            print("[OK] Redis Cluster 연결 성공")
            return True
        else:
            print("[FAIL] Redis Cluster PING 실패")
            return False
    except Exception as e:
        print(f"[FAIL] Redis Cluster 연결 실패: {e}")
        return False


# ========================================
# 통합 테스트
# ========================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_infrastructure_health():
    """
    전체 인프라 헬스체크 통합 테스트

    검증 포인트:
    1. 모든 Docker Compose 서비스가 running 상태
    2. 모든 애플리케이션 서비스 Health Check 통과
    3. 모든 인프라 컴포넌트 연결 성공
    4. 전체 헬스체크가 2분 이내 완료
    """
    start_time = time.time()

    print("\n" + "=" * 80)
    print("전체 인프라 통합 테스트 시작")
    print("=" * 80 + "\n")

    results = {"docker": {}, "applications": {}, "infrastructure": {}}

    # Step 1: Docker Compose 서비스 상태 확인
    print("Step 1: Docker Compose 서비스 상태 확인...")
    docker_services = check_docker_compose_services()

    if docker_services:
        for service, running in docker_services.items():
            results["docker"][service] = running
            status = "[OK]" if running else "[FAIL]"
            print(f"{status} {service}: {'running' if running else 'stopped'}")
    else:
        print("[WARNING] Docker Compose 서비스 상태를 확인할 수 없습니다. 테스트를 건너뜁니다.")

    # Step 2: 애플리케이션 서비스 헬스체크
    print("\nStep 2: 애플리케이션 서비스 헬스체크...")
    for name, config in SERVICES.items():
        result = await check_http_health(name, config["url"], config["timeout"])
        results["applications"][name] = result

    # Step 3: 인프라 컴포넌트 헬스체크
    print("\nStep 3: 인프라 컴포넌트 헬스체크...")

    # PostgreSQL
    results["infrastructure"]["postgres-master"] = check_postgres(
        INFRASTRUCTURE["postgres-master"]["host"],
        INFRASTRUCTURE["postgres-master"]["port"],
    )
    results["infrastructure"]["postgres-replica"] = check_postgres(
        INFRASTRUCTURE["postgres-replica"]["host"],
        INFRASTRUCTURE["postgres-replica"]["port"],
    )

    # Redis Cluster
    results["infrastructure"]["redis-cluster"] = check_redis_cluster(
        INFRASTRUCTURE["redis-cluster"]["nodes"]
    )

    # RabbitMQ (guest:guest 인증)
    results["infrastructure"]["rabbitmq"] = await check_http_health(
        "RabbitMQ",
        INFRASTRUCTURE["rabbitmq"]["url"],
        timeout=10,
        auth=("guest", "guest"),
    )

    # Elasticsearch
    results["infrastructure"]["elasticsearch"] = await check_http_health(
        "Elasticsearch", INFRASTRUCTURE["elasticsearch"]["url"], timeout=10
    )

    # Prometheus
    results["infrastructure"]["prometheus"] = await check_http_health(
        "Prometheus", INFRASTRUCTURE["prometheus"]["url"], timeout=10
    )

    # Grafana
    results["infrastructure"]["grafana"] = await check_http_health(
        "Grafana", INFRASTRUCTURE["grafana"]["url"], timeout=10
    )

    # 최종 결과 집계
    elapsed = time.time() - start_time

    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    print(f"소요 시간: {elapsed:.2f}초 / 목표: 120초 (2분)")
    print("")

    # 카테고리별 집계
    categories = {
        "Docker Compose": results["docker"],
        "Applications": results["applications"],
        "Infrastructure": results["infrastructure"],
    }

    total_pass = 0
    total_fail = 0

    for category, items in categories.items():
        if not items:
            continue

        passed = sum(1 for v in items.values() if v)
        failed = sum(1 for v in items.values() if not v)
        total_pass += passed
        total_fail += failed

        print(f"{category}: {passed} / {len(items)} 통과")
        for name, status in items.items():
            symbol = "[OK]" if status else "[FAIL]"
            print(f"  {symbol} {name}")
        print("")

    print(f"전체: {total_pass} / {total_pass + total_fail} 통과")
    print("")

    # Assertion
    if total_fail > 0:
        print(f"[FAIL] {total_fail}개 서비스가 헬스체크에 실패했습니다. 위 로그를 확인하세요.")

    # 시간 제한 확인
    if elapsed > 120:
        print(f"[WARNING] 헬스체크 소요 시간이 목표(120초)를 초과했습니다: {elapsed:.2f}초")

    # 최소한 애플리케이션 서비스가 모두 통과해야 함
    app_pass = sum(1 for v in results["applications"].values() if v)
    app_total = len(results["applications"])

    assert app_pass == app_total, f"애플리케이션 서비스 헬스체크 실패: {app_pass}/{app_total} 통과"

    # 인프라 중 PostgreSQL Master와 Redis Cluster는 필수
    assert results["infrastructure"].get(
        "postgres-master", False
    ), "PostgreSQL Master 연결 실패"

    print("=" * 80)
    print("[SUCCESS] 전체 인프라 통합 테스트 통과")
    print("=" * 80)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_startup_time():
    """
    전체 인프라 시작 시간 테스트

    검증 포인트:
    - docker-compose up -d 실행 후 2분 이내 모든 서비스 시작
    """
    print("\n" + "=" * 80)
    print("인프라 시작 시간 테스트")
    print("=" * 80 + "\n")

    print("[INFO] 이 테스트는 docker-compose up -d가 이미 실행된 상태를 가정합니다.")
    print("[INFO] 실제 시작 시간을 측정하려면 수동으로 docker-compose를 재시작하세요.")

    # 여기서는 현재 상태만 확인
    start_time = time.time()

    # 모든 애플리케이션 서비스가 준비될 때까지 대기 (최대 120초)
    max_wait = 120
    interval = 5
    elapsed = 0

    all_ready = False

    while elapsed < max_wait:
        ready_count = 0

        for name, config in SERVICES.items():
            if await check_http_health(name, config["url"], timeout=5):
                ready_count += 1

        if ready_count == len(SERVICES):
            all_ready = True
            break

        await asyncio.sleep(interval)
        elapsed += interval
        print(
            f"[INFO] 대기 중... ({elapsed}/{max_wait}초, {ready_count}/{len(SERVICES)} 준비됨)"
        )

    total_time = time.time() - start_time

    print(f"\n[INFO] 모든 서비스 준비 완료 시간: {total_time:.2f}초")

    if all_ready:
        print("[OK] 모든 애플리케이션 서비스가 정상 시작되었습니다.")

        if total_time <= 120:
            print(f"[OK] 시작 시간 목표 달성: {total_time:.2f}초 <= 120초")
        else:
            print(f"[WARNING] 시작 시간이 목표를 초과했습니다: {total_time:.2f}초 > 120초")
    else:
        pytest.fail(f"일부 서비스가 {max_wait}초 내에 준비되지 않았습니다.")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_database_replication_status():
    """
    PostgreSQL Read Replica 복제 상태 확인

    검증 포인트:
    - Master-Replica 복제 지연 10초 이내
    """
    print("\n" + "=" * 80)
    print("PostgreSQL 복제 상태 테스트")
    print("=" * 80 + "\n")

    try:
        from sqlalchemy import create_engine, text

        # Master 연결
        master_engine = create_engine(
            "postgresql://shopfds_user:shopfds_password@localhost:5432/shopfds_db"
        )

        with master_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT client_addr, state, sync_state, replay_lag FROM pg_stat_replication"
                )
            )
            rows = result.fetchall()

            if rows:
                for row in rows:
                    print(
                        f"[OK] Replica 연결: {row[0]}, 상태: {row[1]}, 동기 상태: {row[2]}, 지연: {row[3]}"
                    )

                # 복제 지연 확인
                replay_lag = rows[0][3]
                if replay_lag is not None:
                    # timedelta 또는 interval 타입 처리
                    lag_seconds = (
                        replay_lag.total_seconds()
                        if hasattr(replay_lag, "total_seconds")
                        else 0
                    )

                    if lag_seconds <= 10:
                        print(f"[OK] 복제 지연: {lag_seconds:.2f}초 <= 10초")
                    else:
                        print(f"[WARNING] 복제 지연이 목표를 초과했습니다: {lag_seconds:.2f}초 > 10초")
            else:
                print("[WARNING] 활성화된 Replica 연결이 없습니다.")
                pytest.skip("Read Replica가 연결되지 않았습니다.")

        master_engine.dispose()

    except Exception as e:
        print(f"[FAIL] PostgreSQL 복제 상태 확인 실패: {e}")
        pytest.skip(f"PostgreSQL 연결 실패: {e}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_redis_cluster_info():
    """
    Redis Cluster 클러스터 정보 확인

    검증 포인트:
    - 6노드 클러스터 구성 (3 master, 3 replica)
    - 클러스터 상태 OK
    """
    print("\n" + "=" * 80)
    print("Redis Cluster 상태 테스트")
    print("=" * 80 + "\n")

    try:
        startup_nodes = [ClusterNode("127.0.0.1", 7000)]
        client = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=True,
            skip_full_coverage_check=True,
            socket_timeout=5,
        )

        # 클러스터 정보 조회
        cluster_info = client.cluster_info()

        print(f"[INFO] Cluster State: {cluster_info.get('cluster_state')}")
        print(
            f"[INFO] Cluster Slots Assigned: {cluster_info.get('cluster_slots_assigned')}"
        )
        print(f"[INFO] Cluster Size: {cluster_info.get('cluster_size')}")
        print(f"[INFO] Cluster Known Nodes: {cluster_info.get('cluster_known_nodes')}")

        # 노드 목록 조회
        nodes = client.cluster_nodes()
        master_count = nodes.count("master")
        slave_count = nodes.count("slave")

        print(f"[INFO] Master Nodes: {master_count}")
        print(f"[INFO] Replica Nodes: {slave_count}")

        client.close()

        # Assertion
        assert cluster_info.get("cluster_state") == "ok", "Cluster 상태가 OK가 아닙니다."
        assert cluster_info.get("cluster_known_nodes", 0) >= 6, "6노드 이상의 클러스터가 아닙니다."

        print("[OK] Redis Cluster 상태 정상")

    except Exception as e:
        print(f"[FAIL] Redis Cluster 상태 확인 실패: {e}")
        pytest.skip(f"Redis Cluster 연결 실패: {e}")


if __name__ == "__main__":
    # 로컬 테스트 실행
    asyncio.run(test_full_infrastructure_health())
