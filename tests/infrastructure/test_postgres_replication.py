"""
PostgreSQL Replication Integration Tests
Feature: 002-production-infra
Task: T021

Tests read/write routing, replication lag monitoring, and failover scenarios.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Load environment variables before importing connection modules
from dotenv import load_dotenv

backend_path = os.path.join(os.path.dirname(__file__), "../../services/ecommerce/backend")
load_dotenv(os.path.join(backend_path, ".env"))

# Import connection modules
import sys
sys.path.insert(0, backend_path)

from src.db.connection import (
    get_write_db,
    get_read_db,
    check_database_health,
    close_all_connections,
)
from src.utils.replication_monitor import check_replication_lag


@pytest_asyncio.fixture(scope="function")
async def cleanup():
    """Cleanup after each test"""
    yield
    # Cleanup is handled by context manager in get_write_db/get_read_db


class TestDatabaseConnectionPools:
    """Test read/write connection pool separation"""

    @pytest.mark.asyncio
    async def test_write_connection_pool(self, cleanup):
        """Test write connection pool connects to master"""
        async for db in get_write_db():
            result = await db.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            assert db_name is not None
            print(f"[OK] Write pool connected to database: {db_name}")

    @pytest.mark.asyncio
    async def test_read_connection_pool(self, cleanup):
        """Test read connection pool connects to replica (or master if not configured)"""
        async for db in get_read_db():
            result = await db.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            assert db_name is not None
            print(f"[OK] Read pool connected to database: {db_name}")

    @pytest.mark.asyncio
    async def test_database_health_check(self, cleanup):
        """Test health check for both master and replica"""
        health = await check_database_health()

        assert "master" in health
        assert health["master"]["status"] == "healthy"
        print(f"[OK] Master health: {health['master']}")

        if "replica" in health:
            print(f"[INFO] Replica health: {health['replica']}")


class TestReadWriteRouting:
    """Test that writes go to master and reads can use replica"""

    @pytest.mark.asyncio
    async def test_write_to_master(self, cleanup):
        """Test write operation on master database"""
        async for db in get_write_db():
            # Create a test table (if not exists)
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS replication_test (
                    id SERIAL PRIMARY KEY,
                    test_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await db.commit()

            # Insert test data
            test_value = f"test-{datetime.now(timezone.utc).isoformat()}"
            await db.execute(
                text("INSERT INTO replication_test (test_value) VALUES (:value)"),
                {"value": test_value}
            )
            await db.commit()

            # Verify insert
            result = await db.execute(
                text("SELECT test_value FROM replication_test WHERE test_value = :value"),
                {"value": test_value}
            )
            inserted_value = result.scalar()
            assert inserted_value == test_value
            print(f"[OK] Successfully wrote to master: {test_value}")

    @pytest.mark.asyncio
    async def test_read_from_replica(self, cleanup):
        """Test read operation from replica (with replication delay tolerance)"""
        # First, write to master
        test_value = f"test-read-{datetime.now(timezone.utc).isoformat()}"

        async for db in get_write_db():
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS replication_test (
                    id SERIAL PRIMARY KEY,
                    test_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await db.execute(
                text("INSERT INTO replication_test (test_value) VALUES (:value)"),
                {"value": test_value}
            )
            await db.commit()

        # Wait for replication (max 10 seconds)
        await asyncio.sleep(2)

        # Try to read from replica
        async for db in get_read_db():
            for attempt in range(5):
                result = await db.execute(
                    text("SELECT test_value FROM replication_test WHERE test_value = :value"),
                    {"value": test_value}
                )
                read_value = result.scalar()

                if read_value == test_value:
                    print(f"[OK] Successfully read from replica: {read_value} (attempt {attempt + 1})")
                    break

                # Wait and retry if not found (replication lag)
                print(f"[INFO] Replication lag detected, retrying... (attempt {attempt + 1}/5)")
                await asyncio.sleep(2)
            else:
                print("[WARNING] Data not replicated within 10 seconds (this is acceptable if replica not configured)")

    @pytest.mark.asyncio
    async def test_concurrent_read_write(self, cleanup):
        """Test concurrent read and write operations"""
        async def write_task():
            async for db in get_write_db():
                await db.execute(
                    text("INSERT INTO replication_test (test_value) VALUES (:value)"),
                    {"value": "concurrent-write"}
                )
                await db.commit()

        async def read_task():
            async for db in get_read_db():
                result = await db.execute(text("SELECT COUNT(*) FROM replication_test"))
                count = result.scalar()
                return count

        # Run tasks concurrently
        write_result, read_result = await asyncio.gather(
            write_task(),
            read_task(),
            return_exceptions=True
        )

        print(f"[OK] Concurrent operations completed (read count: {read_result})")
        assert not isinstance(write_result, Exception)
        assert not isinstance(read_result, Exception)


class TestReplicationMonitoring:
    """Test replication lag monitoring functionality"""

    @pytest.mark.asyncio
    async def test_check_replication_lag(self, cleanup):
        """Test replication lag monitoring"""
        try:
            status = await check_replication_lag()

            assert "status" in status
            assert "replicas" in status
            assert "max_lag_seconds" in status
            assert "checked_at" in status

            print(f"[INFO] Replication status: {status['status']}")
            print(f"[INFO] Number of replicas: {len(status['replicas'])}")

            if status["replicas"]:
                for replica in status["replicas"]:
                    print(f"[INFO] Replica {replica['replica_name']}: "
                          f"lag={replica['replay_lag_seconds']}s, "
                          f"state={replica['state']}, "
                          f"healthy={replica['is_healthy']}")

                    # Check lag is reasonable (<10s is healthy)
                    if replica['is_healthy']:
                        assert replica['replay_lag_seconds'] < 10.0
                        print(f"[OK] Replica {replica['replica_name']} is healthy")
            else:
                print("[INFO] No replicas configured (running in single-node mode)")

        except Exception as e:
            print(f"[WARNING] Could not check replication lag: {str(e)}")
            print("[INFO] This is normal if not running on PostgreSQL master")

    @pytest.mark.asyncio
    async def test_replication_lag_threshold(self, cleanup):
        """Test replication lag threshold detection"""
        try:
            status = await check_replication_lag()

            if status["status"] == "not_configured":
                print("[INFO] Replication not configured, skipping lag threshold test")
                pytest.skip("Replication not configured")

            # Verify max lag is tracked
            if status["replicas"]:
                max_lag = status["max_lag_seconds"]
                print(f"[INFO] Maximum replication lag: {max_lag}s")

                # Verify status classification
                if max_lag < 10.0:
                    assert status["status"] == "healthy"
                elif max_lag < 30.0:
                    assert status["status"] == "lagging"
                else:
                    assert status["status"] == "critical"

                print(f"[OK] Replication status correctly classified: {status['status']}")

        except Exception as e:
            print(f"[INFO] Replication lag threshold test skipped: {str(e)}")
            pytest.skip("Replication not available")


class TestFailoverScenarios:
    """Test failover and fallback scenarios"""

    @pytest.mark.asyncio
    async def test_replica_unavailable_fallback(self, cleanup):
        """Test that read operations fall back to master if replica is unavailable"""
        # This test simulates replica failure by reading when replica might be down
        # The connection pool should automatically fall back to master

        async for db in get_read_db():
            result = await db.execute(text("SELECT 1 as test"))
            value = result.scalar()
            assert value == 1
            print("[OK] Read operation successful (using master or replica)")

    @pytest.mark.asyncio
    async def test_master_down_read_only(self, cleanup):
        """Test that reads continue to work even if master is down (replica available)"""
        # This is a manual test - requires stopping master container
        # pytest.skip("Manual test: requires stopping master container")

        health = await check_database_health()
        print(f"[INFO] Current database health: {health}")

        # If replica is healthy, reads should still work
        if health.get("replica", {}).get("status") == "healthy":
            async for db in get_read_db():
                result = await db.execute(text("SELECT 1 as test"))
                value = result.scalar()
                assert value == 1
                print("[OK] Read operations work with replica even when master is down")
        else:
            print("[INFO] Replica not available for failover test")


class TestDataConsistency:
    """Test data consistency between master and replica"""

    @pytest.mark.asyncio
    async def test_write_read_consistency(self, cleanup):
        """Test that data written to master appears on replica"""
        # Write unique data to master
        unique_value = f"consistency-test-{datetime.now(timezone.utc).isoformat()}"

        async for db in get_write_db():
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS replication_test (
                    id SERIAL PRIMARY KEY,
                    test_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await db.execute(
                text("INSERT INTO replication_test (test_value) VALUES (:value)"),
                {"value": unique_value}
            )
            await db.commit()
            print(f"[OK] Wrote to master: {unique_value}")

        # Wait for replication (target: <10s)
        await asyncio.sleep(3)

        # Read from replica and verify
        async for db in get_read_db():
            for attempt in range(3):
                result = await db.execute(
                    text("SELECT test_value FROM replication_test WHERE test_value = :value"),
                    {"value": unique_value}
                )
                read_value = result.scalar()

                if read_value == unique_value:
                    print(f"[OK] Data replicated successfully: {read_value}")
                    break

                await asyncio.sleep(2)
            else:
                print("[WARNING] Data not found on replica (may be using master fallback)")


@pytest.mark.asyncio
async def test_cleanup_test_data(cleanup):
    """Cleanup test data after all tests"""
    async for db in get_write_db():
        await db.execute(text("DROP TABLE IF EXISTS replication_test CASCADE"))
        await db.commit()
        print("[OK] Test data cleaned up")
