"""
FastAPI Dependencies - Admin Dashboard
Feature: 002-production-infra
Task: T029

Provides common dependencies for FastAPI endpoints.
"""

import os
from redis.cluster import RedisCluster, ClusterNode
from typing import Optional


# --- Redis Cluster Dependency ---

_redis_cluster: Optional[RedisCluster] = None


def get_redis_cluster() -> RedisCluster:
    """
    FastAPI dependency for Redis Cluster client

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

        _redis_cluster = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=False,  # Keep binary for blacklist manager
            skip_full_coverage_check=True,  # Allow partial cluster
            max_connections=50,
            max_connections_per_node=10,
        )

    return _redis_cluster


# --- Authentication Dependency ---


class CurrentUser:
    """Mock current user for authentication"""

    def __init__(self, id: str, email: str, role: str = "admin"):
        self.id = id
        self.email = email
        self.role = role


def get_current_user() -> CurrentUser:
    """
    FastAPI dependency for current authenticated user

    TODO: Replace with actual JWT authentication in production

    Returns:
        CurrentUser: Current authenticated user
    """
    # Mock user for development
    # In production, this should validate JWT token and return actual user
    return CurrentUser(id="admin_user", email="admin@shopfds.com", role="admin")
