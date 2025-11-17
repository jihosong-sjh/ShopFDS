"""
Redis Cluster Session Store - Ecommerce Backend
Feature: 002-production-infra
Task: T032

Provides session management using Redis Cluster for high availability.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from redis.cluster import RedisCluster


class SessionStore:
    """
    Redis Cluster \uae30\ubc18 \uc138\uc158 \uc2a4\ud1a0\uc5b4

    Features:
    - \uc138\uc158 \uc800\uc7a5 \ubc0f \uc870\ud68c
    - TTL 30\ubd84 \uc790\ub3d9 \ub9cc\ub8cc
    - Redis Cluster \ud328\uc77c\uc624\ubc84 \uc9c0\uc6d0
    """

    def __init__(self, redis_client: RedisCluster, ttl_minutes: int = 30):
        """
        Initialize SessionStore

        Args:
            redis_client: Redis Cluster client
            ttl_minutes: Session TTL in minutes (default: 30)
        """
        self.redis = redis_client
        self.ttl_seconds = ttl_minutes * 60
        self.prefix = "session"

    def _get_key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"{self.prefix}:{session_id}"

    def create_session(self, user_id: str, data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session

        Args:
            user_id: User ID
            data: Additional session data

        Returns:
            str: Session ID
        """
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed_at": datetime.utcnow().isoformat(),
            "data": data or {},
        }

        key = self._get_key(session_id)
        self.redis.setex(
            key,
            self.ttl_seconds,
            json.dumps(session_data)
        )

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data

        Args:
            session_id: Session ID

        Returns:
            dict: Session data or None if not found
        """
        key = self._get_key(session_id)
        data = self.redis.get(key)

        if not data:
            return None

        session = json.loads(data)

        # Update last accessed time
        session["last_accessed_at"] = datetime.utcnow().isoformat()
        self.redis.setex(key, self.ttl_seconds, json.dumps(session))

        return session

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update session data

        Args:
            session_id: Session ID
            data: Data to update

        Returns:
            bool: True if updated, False if not found
        """
        session = self.get_session(session_id)

        if not session:
            return False

        # Merge new data
        session["data"].update(data)
        session["last_accessed_at"] = datetime.utcnow().isoformat()

        key = self._get_key(session_id)
        self.redis.setex(key, self.ttl_seconds, json.dumps(session))

        return True

    def delete_session(self, session_id: str) -> bool:
        """
        Delete session

        Args:
            session_id: Session ID

        Returns:
            bool: True if deleted, False if not found
        """
        key = self._get_key(session_id)
        result = self.redis.delete(key)
        return result > 0

    def extend_session(self, session_id: str, ttl_minutes: Optional[int] = None) -> bool:
        """
        Extend session TTL

        Args:
            session_id: Session ID
            ttl_minutes: New TTL in minutes (default: use current TTL)

        Returns:
            bool: True if extended, False if not found
        """
        key = self._get_key(session_id)

        if not self.redis.exists(key):
            return False

        ttl_seconds = (ttl_minutes * 60) if ttl_minutes else self.ttl_seconds
        self.redis.expire(key, ttl_seconds)

        return True

    def get_active_sessions_count(self, user_id: Optional[str] = None) -> int:
        """
        Get count of active sessions

        Args:
            user_id: Filter by user ID (optional)

        Returns:
            int: Number of active sessions
        """
        # Note: This is an expensive operation in Redis Cluster
        # For production, consider maintaining a separate index
        if user_id:
            # Scan all sessions and filter by user_id
            # This is inefficient but works for now
            count = 0
            for key in self.redis.scan_iter(match=f"{self.prefix}:*"):
                data = self.redis.get(key)
                if data:
                    session = json.loads(data)
                    if session.get("user_id") == user_id:
                        count += 1
            return count
        else:
            # Count all sessions
            return sum(1 for _ in self.redis.scan_iter(match=f"{self.prefix}:*"))

    def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions (manual cleanup)

        Returns:
            int: Number of sessions cleaned up

        Note: Redis TTL handles this automatically, this is for manual cleanup
        """
        # Redis TTL handles expiration automatically
        # This method is kept for compatibility
        return 0


# --- FastAPI Middleware Integration ---

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable


class SessionMiddleware(BaseHTTPMiddleware):
    """
    FastAPI \uc138\uc158 \ubbf8\ub4e4\uc6e8\uc5b4

    Automatically manages user sessions using Redis Cluster.
    """

    def __init__(self, app, redis_client: RedisCluster, ttl_minutes: int = 30):
        """
        Initialize SessionMiddleware

        Args:
            app: FastAPI application
            redis_client: Redis Cluster client
            ttl_minutes: Session TTL in minutes
        """
        super().__init__(app)
        self.session_store = SessionStore(redis_client, ttl_minutes)

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with session management"""
        # Extract session ID from cookie or header
        session_id = request.cookies.get("session_id") or request.headers.get("X-Session-ID")

        if session_id:
            # Get session data
            session = self.session_store.get_session(session_id)
            if session:
                # Attach session to request state
                request.state.session = session
                request.state.user_id = session.get("user_id")
            else:
                # Session expired or not found
                request.state.session = None
                request.state.user_id = None
        else:
            # No session
            request.state.session = None
            request.state.user_id = None

        # Process request
        response = await call_next(request)

        return response


# --- Helper Functions ---

def require_session(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency for requiring active session

    Args:
        request: FastAPI request

    Returns:
        dict: Session data

    Raises:
        HTTPException: If no active session
    """
    if not hasattr(request.state, "session") or not request.state.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active session. Please login.",
        )
    return request.state.session


def get_current_user_id(request: Request) -> Optional[str]:
    """
    FastAPI dependency for getting current user ID from session

    Args:
        request: FastAPI request

    Returns:
        str: User ID or None
    """
    if hasattr(request.state, "user_id"):
        return request.state.user_id
    return None
