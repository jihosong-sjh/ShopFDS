"""
PostgreSQL Replication Monitoring Utility
Feature: 002-production-infra
Task: T020

Monitors replication health by querying pg_stat_replication view.
Stores metrics in replication_status table for historical tracking.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.replication import ReplicationState, SyncState
from src.db.connection import get_write_session_maker

logger = logging.getLogger(__name__)


async def check_replication_lag(db: Optional[AsyncSession] = None) -> Dict:
    """
    Check PostgreSQL replication lag from pg_stat_replication view

    Queries the master database for replication status and calculates lag metrics.

    Args:
        db: Optional AsyncSession, if None creates a new session

    Returns:
        dict: Replication status summary
            {
                "status": "healthy" | "lagging" | "critical" | "not_configured",
                "replicas": [
                    {
                        "replica_name": "replica-node-1",
                        "client_addr": "10.0.1.10",
                        "state": "streaming",
                        "replay_lag_seconds": 0.12,
                        "is_healthy": True
                    }
                ],
                "max_lag_seconds": 0.12,
                "checked_at": "2025-11-17T18:00:00Z"
            }

    Example:
        ```python
        from src.utils.replication_monitor import check_replication_lag

        # Check replication status
        status = await check_replication_lag()
        if status["status"] == "critical":
            logger.error(f"Critical replication lag: {status['max_lag_seconds']}s")
        ```
    """
    should_close = False
    if db is None:
        session_maker = get_write_session_maker()
        db = session_maker()
        should_close = True

    try:
        # Query pg_stat_replication view on master
        query = text(
            """
            SELECT
                application_name,
                client_addr::text,
                state,
                sync_state,
                COALESCE(
                    EXTRACT(EPOCH FROM (pg_wal_lsn_diff(pg_current_wal_lsn(), write_lsn) / 1024.0 / 1024.0)),
                    0
                )::float AS write_lag_seconds,
                COALESCE(
                    EXTRACT(EPOCH FROM (pg_wal_lsn_diff(pg_current_wal_lsn(), flush_lsn) / 1024.0 / 1024.0)),
                    0
                )::float AS flush_lag_seconds,
                COALESCE(
                    EXTRACT(EPOCH FROM (pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) / 1024.0 / 1024.0)),
                    0
                )::float AS replay_lag_seconds,
                pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes
            FROM pg_stat_replication
            WHERE state IS NOT NULL
            ORDER BY application_name;
        """
        )

        result = await db.execute(query)
        rows = result.fetchall()

        if not rows:
            logger.info("[REPLICATION] No replicas found (pg_stat_replication empty)")
            return {
                "status": "not_configured",
                "replicas": [],
                "max_lag_seconds": None,
                "checked_at": datetime.utcnow().isoformat(),
            }

        # Process replica statuses
        replicas = []
        max_lag = 0.0

        for row in rows:
            replica_name = row[0]
            client_addr = row[1]
            state = row[2]
            sync_state = row[3]
            write_lag_seconds = float(row[4] or 0.0)
            flush_lag_seconds = float(row[5] or 0.0)
            replay_lag_seconds = float(row[6] or 0.0)
            lag_bytes = int(row[7] or 0)

            # Determine health status
            is_healthy = state == "streaming" and replay_lag_seconds < 10.0
            max_lag = max(max_lag, replay_lag_seconds)

            replica_info = {
                "replica_name": replica_name,
                "client_addr": client_addr,
                "state": state,
                "sync_state": sync_state,
                "write_lag_seconds": round(write_lag_seconds, 4),
                "flush_lag_seconds": round(flush_lag_seconds, 4),
                "replay_lag_seconds": round(replay_lag_seconds, 4),
                "lag_bytes": lag_bytes,
                "is_healthy": is_healthy,
            }
            replicas.append(replica_info)

            # Update or insert replication_status record
            await _update_replication_status(
                db=db,
                replica_name=replica_name,
                client_addr=client_addr,
                state=ReplicationState(state)
                if state in [s.value for s in ReplicationState]
                else ReplicationState.UNKNOWN,
                sync_state=SyncState(sync_state)
                if sync_state in [s.value for s in SyncState]
                else SyncState.ASYNC,
                write_lag_seconds=write_lag_seconds,
                flush_lag_seconds=flush_lag_seconds,
                replay_lag_seconds=replay_lag_seconds,
                lag_bytes=lag_bytes,
                is_healthy=is_healthy,
            )

        # Commit updates
        await db.commit()

        # Determine overall status
        if max_lag > 30.0:
            overall_status = "critical"
        elif max_lag > 10.0:
            overall_status = "lagging"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "replicas": replicas,
            "max_lag_seconds": round(max_lag, 4),
            "checked_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"[REPLICATION] Error checking replication lag: {str(e)}")
        raise
    finally:
        if should_close:
            await db.close()


async def _update_replication_status(
    db: AsyncSession,
    replica_name: str,
    client_addr: str,
    state: ReplicationState,
    sync_state: SyncState,
    write_lag_seconds: float,
    flush_lag_seconds: float,
    replay_lag_seconds: float,
    lag_bytes: int,
    is_healthy: bool,
) -> None:
    """
    Update or insert replication_status record

    Args:
        db: Database session
        replica_name: Replica application name
        client_addr: Replica IP address
        state: Replication state
        sync_state: Synchronization state
        write_lag_seconds: Write lag in seconds
        flush_lag_seconds: Flush lag in seconds
        replay_lag_seconds: Replay lag in seconds
        lag_bytes: Lag in bytes
        is_healthy: Health status
    """
    # Check if record exists
    query = text(
        """
        SELECT id FROM replication_status
        WHERE replica_name = :replica_name
        FOR UPDATE
    """
    )
    result = await db.execute(query, {"replica_name": replica_name})
    existing = result.fetchone()

    now = datetime.utcnow()

    if existing:
        # Update existing record
        update_query = text(
            """
            UPDATE replication_status
            SET
                client_addr = :client_addr,
                state = :state,
                write_lag_seconds = :write_lag_seconds,
                flush_lag_seconds = :flush_lag_seconds,
                replay_lag_seconds = :replay_lag_seconds,
                lag_bytes = :lag_bytes,
                sync_state = :sync_state,
                is_healthy = :is_healthy,
                checked_at = :checked_at,
                updated_at = :updated_at
            WHERE replica_name = :replica_name
        """
        )
        await db.execute(
            update_query,
            {
                "replica_name": replica_name,
                "client_addr": client_addr,
                "state": state.value,
                "write_lag_seconds": write_lag_seconds,
                "flush_lag_seconds": flush_lag_seconds,
                "replay_lag_seconds": replay_lag_seconds,
                "lag_bytes": lag_bytes,
                "sync_state": sync_state.value,
                "is_healthy": is_healthy,
                "checked_at": now,
                "updated_at": now,
            },
        )
    else:
        # Insert new record
        insert_query = text(
            """
            INSERT INTO replication_status (
                id, replica_name, client_addr, state, write_lag_seconds,
                flush_lag_seconds, replay_lag_seconds, lag_bytes, sync_state,
                is_healthy, checked_at, created_at, updated_at
            ) VALUES (
                :id, :replica_name, :client_addr, :state, :write_lag_seconds,
                :flush_lag_seconds, :replay_lag_seconds, :lag_bytes, :sync_state,
                :is_healthy, :checked_at, :created_at, :updated_at
            )
        """
        )
        await db.execute(
            insert_query,
            {
                "id": uuid4(),
                "replica_name": replica_name,
                "client_addr": client_addr,
                "state": state.value,
                "write_lag_seconds": write_lag_seconds,
                "flush_lag_seconds": flush_lag_seconds,
                "replay_lag_seconds": replay_lag_seconds,
                "lag_bytes": lag_bytes,
                "sync_state": sync_state.value,
                "is_healthy": is_healthy,
                "checked_at": now,
                "created_at": now,
                "updated_at": now,
            },
        )


async def get_replication_history(
    replica_name: Optional[str] = None,
    hours: int = 24,
    db: Optional[AsyncSession] = None,
) -> List[Dict]:
    """
    Get historical replication status

    Args:
        replica_name: Filter by specific replica (optional)
        hours: Number of hours to look back (default 24)
        db: Optional AsyncSession

    Returns:
        list: Historical replication statuses

    Example:
        ```python
        # Get last 24 hours of replication history
        history = await get_replication_history()
        for entry in history:
            print(f"{entry['checked_at']}: {entry['replay_lag_seconds']}s")
        ```
    """
    should_close = False
    if db is None:
        session_maker = get_write_session_maker()
        db = session_maker()
        should_close = True

    try:
        query_text = """
            SELECT
                replica_name,
                client_addr,
                state,
                replay_lag_seconds,
                lag_bytes,
                is_healthy,
                checked_at
            FROM replication_status
            WHERE checked_at >= NOW() - INTERVAL ':hours hours'
        """

        if replica_name:
            query_text += " AND replica_name = :replica_name"

        query_text += " ORDER BY checked_at DESC"

        params = {"hours": hours}
        if replica_name:
            params["replica_name"] = replica_name

        query = text(query_text)
        result = await db.execute(query, params)
        rows = result.fetchall()

        history = [
            {
                "replica_name": row[0],
                "client_addr": row[1],
                "state": row[2],
                "replay_lag_seconds": float(row[3]) if row[3] is not None else None,
                "lag_bytes": int(row[4]) if row[4] is not None else None,
                "is_healthy": bool(row[5]),
                "checked_at": row[6].isoformat() if row[6] else None,
            }
            for row in rows
        ]

        return history

    finally:
        if should_close:
            await db.close()
