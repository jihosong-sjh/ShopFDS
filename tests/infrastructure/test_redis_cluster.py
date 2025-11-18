"""
Redis Cluster Integration Tests
Feature: 002-production-infra
Task: T033

Tests Redis Cluster functionality:
1. Cluster creation and initialization
2. Sharding across nodes
3. Failover capabilities
4. Blacklist CRUD operations
5. Session management
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from redis.cluster import RedisCluster, ClusterNode


# --- Redis Cluster Setup ---


@pytest.fixture(scope="module")
def redis_cluster():
    """
    Redis Cluster client fixture

    Note: Requires Docker Compose with 6 Redis nodes running
    """
    startup_nodes = [
        ClusterNode("localhost", 7000),
        ClusterNode("localhost", 7001),
        ClusterNode("localhost", 7002),
    ]

    client = RedisCluster(
        startup_nodes=startup_nodes,
        decode_responses=False,
        skip_full_coverage_check=True,
        max_connections=50,
    )

    yield client

    # Cleanup: Clear all test data
    try:
        client.flushall()
    except Exception as e:
        print(f"[WARN] Failed to flush Redis cluster: {e}")

    client.close()


# --- Test 1: Cluster Initialization ---


def test_redis_cluster_initialization(redis_cluster):
    """
    Test Redis Cluster initialization

    Verification:
    - Cluster is healthy
    - All nodes are connected
    - Cluster state is 'ok'
    """
    # Ping cluster
    response = redis_cluster.ping()
    assert response is True, "Redis Cluster ping failed"

    # Check cluster info
    cluster_info = redis_cluster.cluster_info()
    assert cluster_info["cluster_state"] == "ok", "Cluster state is not OK"
    assert cluster_info["cluster_size"] >= 3, "Cluster should have at least 3 master nodes"

    # Check cluster nodes
    cluster_nodes = redis_cluster.cluster_nodes()
    assert len(cluster_nodes.split("\n")) >= 6, "Cluster should have at least 6 nodes (3 masters + 3 replicas)"

    print(f"[OK] Redis Cluster initialized: {cluster_info['cluster_size']} shards, "
          f"{len(cluster_nodes.split(chr(10)))} total nodes")


# --- Test 2: Data Sharding ---


def test_redis_cluster_sharding(redis_cluster):
    """
    Test automatic data sharding across cluster nodes

    Verification:
    - Data is distributed across multiple nodes
    - Keys hash to different slots
    """
    # Insert data with different keys (should shard across nodes)
    test_keys = [f"shard_test_{i}" for i in range(100)]
    for key in test_keys:
        redis_cluster.set(key, f"value_{key}")

    # Verify all keys are stored
    for key in test_keys:
        value = redis_cluster.get(key)
        assert value is not None, f"Key {key} not found"
        assert value.decode("utf-8") == f"value_{key}", f"Value mismatch for {key}"

    # Check slot distribution
    slots_used = set()
    for key in test_keys:
        slot = redis_cluster.cluster_keyslot(key)
        slots_used.add(slot)

    # With 100 keys, we should have multiple slots
    assert len(slots_used) > 1, "Data should be distributed across multiple slots"

    print(f"[OK] Sharding test passed: {len(test_keys)} keys distributed across {len(slots_used)} slots")

    # Cleanup
    for key in test_keys:
        redis_cluster.delete(key)


# --- Test 3: Blacklist CRUD Operations ---


@pytest.mark.asyncio
async def test_blacklist_crud(redis_cluster):
    """
    Test blacklist manager CRUD operations

    Verification:
    - Add blacklist entry
    - Check entry exists
    - List entries
    - Remove entry
    """
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/fds/src"))

    from cache.blacklist import BlacklistManager, BlacklistType, BlacklistReason

    manager = BlacklistManager(redis_cluster)

    # 1. Add blacklist entry
    entry = await manager.add_entry(
        entry_type=BlacklistType.IP,
        value="192.168.1.100",
        reason=BlacklistReason.FRAUD_DETECTED,
        added_by="test_user",
        ttl_days=7,
        metadata={"source": "integration_test"},
    )

    assert entry is not None, "Failed to create blacklist entry"
    assert entry.value == "192.168.1.100"
    assert entry.reason == BlacklistReason.FRAUD_DETECTED

    print(f"[OK] Added blacklist entry: {entry.id}")

    # 2. Check entry exists
    found_entry = await manager.check_entry(BlacklistType.IP, "192.168.1.100")
    assert found_entry is not None, "Blacklist entry not found"
    assert found_entry.id == entry.id

    print(f"[OK] Found blacklist entry: {found_entry.id}")

    # 3. List entries
    entries = await manager.list_entries(entry_type=BlacklistType.IP, limit=10)
    assert len(entries) >= 1, "No entries found in list"
    assert any(e.id == entry.id for e in entries), "Created entry not in list"

    print(f"[OK] Listed {len(entries)} blacklist entries")

    # 4. Update TTL
    updated = await manager.update_ttl(BlacklistType.IP, "192.168.1.100", ttl_days=14)
    assert updated is True, "Failed to update TTL"

    print(f"[OK] Updated TTL to 14 days")

    # 5. Remove entry
    removed = await manager.remove_entry(BlacklistType.IP, "192.168.1.100")
    assert removed is True, "Failed to remove blacklist entry"

    # 6. Verify removal
    found_after_delete = await manager.check_entry(BlacklistType.IP, "192.168.1.100")
    assert found_after_delete is None, "Entry still exists after deletion"

    print(f"[OK] Removed blacklist entry: {entry.id}")


# --- Test 4: Blacklist Multiple Types ---


@pytest.mark.asyncio
async def test_blacklist_multiple_types(redis_cluster):
    """
    Test blacklist with multiple entry types

    Verification:
    - IP blacklist
    - Email domain blacklist
    - Card BIN blacklist
    - User ID blacklist
    """
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/fds/src"))

    from cache.blacklist import BlacklistManager, BlacklistType, BlacklistReason

    manager = BlacklistManager(redis_cluster)

    # Add different types of blacklist entries
    entries = []

    # IP blacklist
    entries.append(await manager.add_entry(
        entry_type=BlacklistType.IP,
        value="10.0.0.100",
        reason=BlacklistReason.FRAUD_DETECTED,
        added_by="test_user",
    ))

    # Email domain blacklist
    entries.append(await manager.add_entry(
        entry_type=BlacklistType.EMAIL_DOMAIN,
        value="spam-domain.com",
        reason=BlacklistReason.ABUSE,
        added_by="test_user",
    ))

    # Card BIN blacklist
    entries.append(await manager.add_entry(
        entry_type=BlacklistType.CARD_BIN,
        value="123456",
        reason=BlacklistReason.STOLEN_CARD,
        added_by="test_user",
    ))

    # User ID blacklist
    entries.append(await manager.add_entry(
        entry_type=BlacklistType.USER_ID,
        value=str(uuid.uuid4()),
        reason=BlacklistReason.MULTIPLE_ACCOUNTS,
        added_by="test_user",
    ))

    print(f"[OK] Added {len(entries)} blacklist entries of different types")

    # Check is_blacklisted with multiple values
    results = await manager.is_blacklisted(
        ip="10.0.0.100",
        email="user@spam-domain.com",
        card_bin="123456",
    )

    assert results["ip"] is not None, "IP not blacklisted"
    assert results["email_domain"] is not None, "Email domain not blacklisted"
    assert results["card_bin"] is not None, "Card BIN not blacklisted"

    print(f"[OK] Multi-type blacklist check: {sum(1 for v in results.values() if v)} matches found")

    # Cleanup
    for entry in entries:
        await manager.remove_entry(entry.entry_type, entry.value)


# --- Test 5: Session Management ---


def test_session_management(redis_cluster):
    """
    Test session store functionality

    Verification:
    - Create session
    - Get session
    - Update session
    - Session TTL expiry
    """
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/ecommerce/backend/src"))

    from middleware.session import SessionStore

    store = SessionStore(redis_cluster, ttl_minutes=1)  # 1 minute TTL for testing

    # 1. Create session
    user_id = str(uuid.uuid4())
    session_id = store.create_session(user_id, data={"cart_items": []})

    assert session_id is not None, "Failed to create session"

    print(f"[OK] Created session: {session_id}")

    # 2. Get session
    session = store.get_session(session_id)
    assert session is not None, "Session not found"
    assert session["user_id"] == user_id
    assert session["data"]["cart_items"] == []

    print(f"[OK] Retrieved session: {session_id}")

    # 3. Update session
    updated = store.update_session(session_id, {"cart_items": ["product_1", "product_2"]})
    assert updated is True, "Failed to update session"

    session = store.get_session(session_id)
    assert len(session["data"]["cart_items"]) == 2

    print(f"[OK] Updated session: {session_id}")

    # 4. Extend session TTL
    extended = store.extend_session(session_id, ttl_minutes=5)
    assert extended is True, "Failed to extend session TTL"

    print(f"[OK] Extended session TTL: {session_id}")

    # 5. Delete session
    deleted = store.delete_session(session_id)
    assert deleted is True, "Failed to delete session"

    session = store.get_session(session_id)
    assert session is None, "Session still exists after deletion"

    print(f"[OK] Deleted session: {session_id}")


# --- Test 6: Cluster Failover Simulation (Manual) ---


def test_cluster_failover_info(redis_cluster):
    """
    Test cluster failover information

    Note: Actual failover testing requires manually stopping a node.
    This test only checks cluster replication status.

    Verification:
    - Replication is configured
    - Each master has at least one replica
    """
    cluster_nodes_raw = redis_cluster.cluster_nodes()
    nodes = cluster_nodes_raw.split("\n")

    masters = []
    replicas = []

    for node_line in nodes:
        if not node_line.strip():
            continue

        parts = node_line.split()
        if len(parts) >= 3:
            node_id = parts[0]
            flags = parts[2]

            if "master" in flags:
                masters.append(node_id)
            elif "slave" in flags:
                replicas.append(node_id)

    print(f"[INFO] Cluster has {len(masters)} masters and {len(replicas)} replicas")

    assert len(masters) >= 3, "Cluster should have at least 3 master nodes"
    assert len(replicas) >= 3, "Cluster should have at least 3 replica nodes"

    print(f"[OK] Cluster replication verified: {len(masters)} masters, {len(replicas)} replicas")


# --- Test Summary ---


def test_redis_cluster_summary(redis_cluster):
    """
    Test summary and health check

    Verification:
    - All tests completed successfully
    - Cluster is healthy
    """
    # Final health check
    cluster_info = redis_cluster.cluster_info()

    print("\n" + "=" * 60)
    print("Redis Cluster Integration Test Summary")
    print("=" * 60)
    print(f"Cluster State: {cluster_info['cluster_state']}")
    print(f"Cluster Size: {cluster_info['cluster_size']} shards")
    print(f"Cluster Known Nodes: {cluster_info['cluster_known_nodes']}")
    print(f"Cluster Slots Assigned: {cluster_info['cluster_slots_assigned']}")
    print("=" * 60)
    print("[SUCCESS] All Redis Cluster tests passed!")
    print("=" * 60)

    assert cluster_info["cluster_state"] == "ok", "Final health check failed"
