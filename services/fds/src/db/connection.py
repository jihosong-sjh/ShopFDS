"""
Read/Write Database Connection Pool Manager - FDS Service
Feature: 002-production-infra
Task: T016

Provides separate connection pools for:
- Write operations: Master database
- Read operations: Read Replica database (with fallback to Master)
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)

# Simple logger (FDS service may have different logging setup)
import logging

logger = logging.getLogger(__name__)


# Database URLs from environment variables
MASTER_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://shopfds:dev_password@localhost:5432/shopfds_dev",
)

REPLICA_DATABASE_URL = os.getenv(
    "READ_REPLICA_URL",
    # Fallback to master if replica URL not configured
    MASTER_DATABASE_URL.replace(":5432", ":5433")
    if "5432" in MASTER_DATABASE_URL
    else MASTER_DATABASE_URL,
)

# SQL Echo setting
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"


# --- Write Database Engine (Master) ---
_write_engine: AsyncEngine | None = None
_WriteSessionLocal: async_sessionmaker[AsyncSession] | None = None


def get_write_engine() -> AsyncEngine:
    """
    Get or create write (master) database engine

    Returns:
        AsyncEngine: Master database engine
    """
    global _write_engine
    if _write_engine is None:
        logger.info(
            f"[WRITE] Creating master database engine: {MASTER_DATABASE_URL.split('@')[1] if '@' in MASTER_DATABASE_URL else 'localhost'}"
        )
        _write_engine = create_async_engine(
            MASTER_DATABASE_URL,
            echo=SQL_ECHO,
            pool_size=10,  # Connection pool size
            max_overflow=20,  # Additional connections allowed
            pool_pre_ping=True,  # Test connection before using
            pool_recycle=3600,  # Recycle connections every 1 hour
        )
    return _write_engine


def get_write_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Get or create write session maker

    Returns:
        async_sessionmaker: Session factory for write operations
    """
    global _WriteSessionLocal
    if _WriteSessionLocal is None:
        _WriteSessionLocal = async_sessionmaker(
            get_write_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _WriteSessionLocal


async def get_write_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for write database session (Master)

    Use this for INSERT, UPDATE, DELETE operations.

    Example:
        ```python
        @app.post("/fds/evaluation")
        async def create_evaluation(db: AsyncSession = Depends(get_write_db)):
            # Write to master database
            new_eval = TransactionEvaluation(...)
            db.add(new_eval)
            await db.commit()
            return new_eval
        ```

    Yields:
        AsyncSession: Write database session
    """
    session_maker = get_write_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"[WRITE] Transaction error: {str(e)}")
            raise
        finally:
            await session.close()


# --- Read Database Engine (Replica) ---
_read_engine: AsyncEngine | None = None
_ReadSessionLocal: async_sessionmaker[AsyncSession] | None = None
_use_replica = MASTER_DATABASE_URL != REPLICA_DATABASE_URL


def get_read_engine() -> AsyncEngine:
    """
    Get or create read (replica) database engine

    Returns:
        AsyncEngine: Read replica database engine (or master if replica unavailable)
    """
    global _read_engine, _use_replica

    if _read_engine is None:
        if _use_replica:
            logger.info(
                f"[READ] Creating read replica engine: {REPLICA_DATABASE_URL.split('@')[1] if '@' in REPLICA_DATABASE_URL else 'localhost'}"
            )
            try:
                _read_engine = create_async_engine(
                    REPLICA_DATABASE_URL,
                    echo=SQL_ECHO,
                    pool_size=15,  # Larger pool for read-heavy workloads
                    max_overflow=30,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                )
            except Exception as e:
                logger.warning(
                    f"[READ] Failed to create replica engine, falling back to master: {str(e)}"
                )
                _read_engine = get_write_engine()
                _use_replica = False
        else:
            logger.info(
                "[READ] No separate read replica configured, using master for reads"
            )
            _read_engine = get_write_engine()

    return _read_engine


def get_read_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Get or create read session maker

    Returns:
        async_sessionmaker: Session factory for read operations
    """
    global _ReadSessionLocal
    if _ReadSessionLocal is None:
        _ReadSessionLocal = async_sessionmaker(
            get_read_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _ReadSessionLocal


async def get_read_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for read database session (Replica)

    Use this for SELECT operations to reduce load on master.
    Automatically falls back to master if replica is unavailable.

    Example:
        ```python
        @app.get("/fds/history")
        async def get_evaluation_history(db: AsyncSession = Depends(get_read_db)):
            # Read from replica database
            result = await db.execute(select(TransactionEvaluation))
            return result.scalars().all()
        ```

    Yields:
        AsyncSession: Read database session
    """
    session_maker = get_read_session_maker()
    async with session_maker() as session:
        try:
            yield session
            # Read-only sessions don't need commit
        except Exception as e:
            logger.error(f"[READ] Query error: {str(e)}")
            # Try to fallback to master on replica failure
            if _use_replica:
                logger.warning("[READ] Attempting fallback to master database")
                try:
                    async with get_write_session_maker()() as fallback_session:
                        yield fallback_session
                except Exception as fallback_error:
                    logger.error(
                        f"[READ] Fallback to master also failed: {str(fallback_error)}"
                    )
                    raise
            else:
                raise
        finally:
            await session.close()


async def close_all_connections() -> None:
    """
    Close all database connection pools

    Call this on application shutdown to properly cleanup resources.
    """
    global _write_engine, _read_engine, _WriteSessionLocal, _ReadSessionLocal

    if _write_engine is not None:
        logger.info("[WRITE] Closing master database engine")
        await _write_engine.dispose()
        _write_engine = None
        _WriteSessionLocal = None

    if _read_engine is not None and _read_engine != _write_engine:
        logger.info("[READ] Closing read replica engine")
        await _read_engine.dispose()
        _read_engine = None
        _ReadSessionLocal = None


# --- Legacy Compatibility ---
# For backward compatibility with existing code using get_db()
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Legacy database session provider (uses write database)

    DEPRECATED: Use get_write_db() or get_read_db() explicitly instead.
    This function is kept for backward compatibility with existing code.

    Yields:
        AsyncSession: Write database session
    """
    async for session in get_write_db():
        yield session


# --- Health Check ---
async def check_database_health() -> dict:
    """
    Check health of both master and replica databases

    Returns:
        dict: Health status of databases

    Example:
        {
            "master": {"status": "healthy", "latency_ms": 5.2},
            "replica": {"status": "healthy", "latency_ms": 6.1}
        }
    """
    import time
    from sqlalchemy import text

    health = {}

    # Check master
    try:
        start = time.time()
        async with get_write_session_maker()() as session:
            await session.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        health["master"] = {"status": "healthy", "latency_ms": round(latency, 2)}
    except Exception as e:
        health["master"] = {"status": "unhealthy", "error": str(e)}

    # Check replica
    if _use_replica:
        try:
            start = time.time()
            async with get_read_session_maker()() as session:
                await session.execute(text("SELECT 1"))
            latency = (time.time() - start) * 1000
            health["replica"] = {"status": "healthy", "latency_ms": round(latency, 2)}
        except Exception as e:
            health["replica"] = {"status": "unhealthy", "error": str(e)}
    else:
        health["replica"] = {"status": "not_configured", "fallback": "using_master"}

    return health


# --- Redis Cluster Connection ---
from redis.cluster import RedisCluster
from redis.cluster import ClusterNode

_redis_cluster: RedisCluster | None = None


def get_redis_cluster() -> RedisCluster:
    """
    Get or create Redis Cluster client

    Returns:
        RedisCluster: Redis Cluster client
    """
    global _redis_cluster

    if _redis_cluster is None:
        # Get Redis Cluster nodes from environment
        redis_nodes_str = os.getenv(
            "REDIS_CLUSTER_NODES",
            "redis-node-1:6379,redis-node-2:6379,redis-node-3:6379",
        )

        # Parse nodes
        startup_nodes = []
        for node_str in redis_nodes_str.split(","):
            host, port = node_str.strip().split(":")
            startup_nodes.append(ClusterNode(host=host, port=int(port)))

        logger.info(
            f"[REDIS] Creating Redis Cluster client with nodes: {redis_nodes_str}"
        )

        _redis_cluster = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=False,  # Keep binary for blacklist manager
            skip_full_coverage_check=True,  # Allow partial cluster
            max_connections=50,
            max_connections_per_node=10,
        )

    return _redis_cluster


async def check_redis_cluster_health() -> dict:
    """
    Check health of Redis Cluster

    Returns:
        dict: Health status of Redis Cluster
    """
    import time

    try:
        start = time.time()
        redis = get_redis_cluster()
        redis.ping()
        latency = (time.time() - start) * 1000

        # Get cluster info
        cluster_info = redis.cluster_info()
        cluster_nodes = redis.cluster_nodes()

        return {
            "status": "healthy",
            "latency_ms": round(latency, 2),
            "cluster_state": cluster_info.get("cluster_state", "unknown"),
            "cluster_size": cluster_info.get("cluster_size", 0),
            "total_nodes": len(cluster_nodes.split("\n")) - 1,
        }
    except Exception as e:
        logger.error(f"[REDIS] Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}


async def close_redis_cluster() -> None:
    """
    Close Redis Cluster connection

    Call this on application shutdown.
    """
    global _redis_cluster

    if _redis_cluster is not None:
        logger.info("[REDIS] Closing Redis Cluster connection")
        _redis_cluster.close()
        _redis_cluster = None
