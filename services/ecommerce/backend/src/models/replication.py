"""
PostgreSQL Replication Monitoring Models
Feature: 002-production-infra
Task: T019

Tracks replication health and lag metrics for Master-Replica setup.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    String,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.models.base import Base, TimestampMixin


class ReplicationState(str, PyEnum):
    """Replication state enumeration"""

    STREAMING = "streaming"  # Normal streaming replication
    CATCHUP = "catchup"  # Replica catching up after restart
    UNKNOWN = "unknown"  # Connection lost or unknown state


class SyncState(str, PyEnum):
    """Synchronization state enumeration"""

    ASYNC = "async"  # Asynchronous replication (default)
    SYNC = "sync"  # Synchronous replication
    QUORUM = "quorum"  # Quorum-based synchronous replication


class ReplicationStatus(Base, TimestampMixin):
    """
    PostgreSQL Streaming Replication Status

    Tracks replication health metrics from pg_stat_replication view.
    Used for monitoring and alerting on replication lag.

    Reference:
    - specs/002-production-infra/data-model.md
    - https://www.postgresql.org/docs/15/monitoring-stats.html#MONITORING-PG-STAT-REPLICATION-VIEW
    """

    __tablename__ = "replication_status"

    # Primary key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Replication identity
    replica_name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="Application name from pg_stat_replication (e.g., replica-node-1)",
    )

    # Connection info
    client_addr: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Replica IP address",
    )

    # Replication state
    state: Mapped[ReplicationState] = mapped_column(
        Enum(ReplicationState, native_enum=False, length=20),
        nullable=False,
        default=ReplicationState.UNKNOWN,
        comment="Replication state: streaming, catchup, unknown",
    )

    # Lag metrics (in seconds)
    write_lag_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Master write to replica write lag (seconds)",
    )

    flush_lag_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Master write to replica flush lag (seconds)",
    )

    replay_lag_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Master write to replica replay lag (seconds) - most important metric",
    )

    # Lag in bytes (LSN difference)
    lag_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Bytes behind master (LSN diff)",
    )

    # Sync state
    sync_state: Mapped[SyncState] = mapped_column(
        Enum(SyncState, native_enum=False, length=20),
        nullable=False,
        default=SyncState.ASYNC,
        comment="Synchronization state: async, sync, quorum",
    )

    # Health status
    is_healthy: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if state=streaming and replay_lag < 10s",
    )

    # Last check timestamp
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp of last health check",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "replay_lag_seconds IS NULL OR replay_lag_seconds >= 0",
            name="ck_replication_status_replay_lag_nonnegative",
        ),
        CheckConstraint(
            "lag_bytes IS NULL OR lag_bytes >= 0",
            name="ck_replication_status_lag_bytes_nonnegative",
        ),
        Index("ix_replication_status_replica_name", "replica_name"),
        Index("ix_replication_status_checked_at", "checked_at"),
        Index("ix_replication_status_is_healthy", "is_healthy"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReplicationStatus(replica={self.replica_name}, "
            f"state={self.state}, replay_lag={self.replay_lag_seconds}s, "
            f"healthy={self.is_healthy})>"
        )

    @property
    def is_lagging(self) -> bool:
        """Check if replica is lagging (> 5 seconds)"""
        if self.replay_lag_seconds is None:
            return True  # Unknown lag is considered unhealthy
        return self.replay_lag_seconds > 5.0

    @property
    def is_critical_lag(self) -> bool:
        """Check if replica has critical lag (> 30 seconds)"""
        if self.replay_lag_seconds is None:
            return True  # Unknown lag is critical
        return self.replay_lag_seconds > 30.0
