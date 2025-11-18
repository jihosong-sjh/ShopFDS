"""
Blacklist Manager - Redis Cluster \uae30\ubc18 \ube14\ub799\ub9ac\uc2a4\ud2b8 \uad00\ub9ac
ShopFDS Production Infrastructure - User Story 2
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any
from redis.cluster import RedisCluster
import json


class BlacklistType(str, Enum):
    """Blacklist entry type"""

    IP = "ip"
    EMAIL_DOMAIN = "email_domain"
    CARD_BIN = "card_bin"
    USER_ID = "user_id"
    PHONE = "phone"


class BlacklistReason(str, Enum):
    """Reason for blacklisting"""

    FRAUD_DETECTED = "fraud_detected"
    CHARGEBACK = "chargeback"
    MULTIPLE_ACCOUNTS = "multiple_accounts"
    STOLEN_CARD = "stolen_card"
    MANUAL_REVIEW = "manual_review"
    ABUSE = "abuse"


class BlacklistEntry:
    """Blacklist entry model"""

    def __init__(
        self,
        id: str,
        entry_type: BlacklistType,
        value: str,
        reason: BlacklistReason,
        added_by: str,
        added_at: datetime,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.entry_type = entry_type
        self.value = value
        self.reason = reason
        self.added_by = added_by
        self.added_at = added_at
        self.expires_at = expires_at
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "entry_type": self.entry_type,
            "value": self.value,
            "reason": self.reason,
            "added_by": self.added_by,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlacklistEntry":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            entry_type=BlacklistType(data["entry_type"]),
            value=data["value"],
            reason=BlacklistReason(data["reason"]),
            added_by=data["added_by"],
            added_at=datetime.fromisoformat(data["added_at"])
            if data.get("added_at")
            else None,
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            metadata=data.get("metadata", {}),
        )


class BlacklistManager:
    """
    Redis Cluster \uae30\ubc18 \ube14\ub799\ub9ac\uc2a4\ud2b8 \uad00\ub9ac

    Features:
    - IP, \uc774\uba54\uc77c \ub3c4\uba54\uc778, \uce74\ub4dc BIN, \uc0ac\uc6a9\uc790 ID, \uc804\ud654\ubc88\ud638 \ube14\ub799\ub9ac\uc2a4\ud2b8
    - TTL \uae30\ubc18 \uc790\ub3d9 \ub9cc\ub8cc
    - Redis Cluster \uc0e4\ub529 \uc9c0\uc6d0
    - \uba54\ud0c0\ub370\uc774\ud130 \uc800\uc7a5
    """

    def __init__(self, redis_client: RedisCluster):
        """
        Initialize BlacklistManager

        Args:
            redis_client: Redis Cluster client
        """
        self.redis = redis_client
        self.prefix = "blacklist"

    def _get_key(self, entry_type: BlacklistType, value: str) -> str:
        """Generate Redis key for blacklist entry"""
        return f"{self.prefix}:{entry_type}:{value}"

    def _get_index_key(self, entry_type: BlacklistType) -> str:
        """Generate Redis key for type index"""
        return f"{self.prefix}:index:{entry_type}"

    async def add_entry(
        self,
        entry_type: BlacklistType,
        value: str,
        reason: BlacklistReason,
        added_by: str,
        ttl_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BlacklistEntry:
        """
        Add entry to blacklist

        Args:
            entry_type: Type of blacklist entry
            value: Value to blacklist (IP, email domain, etc.)
            reason: Reason for blacklisting
            added_by: User ID who added the entry
            ttl_days: TTL in days (None = no expiry)
            metadata: Additional metadata

        Returns:
            BlacklistEntry object
        """
        entry_id = str(uuid.uuid4())
        added_at = datetime.utcnow()
        expires_at = added_at + timedelta(days=ttl_days) if ttl_days else None

        entry = BlacklistEntry(
            id=entry_id,
            entry_type=entry_type,
            value=value,
            reason=reason,
            added_by=added_by,
            added_at=added_at,
            expires_at=expires_at,
            metadata=metadata,
        )

        # Store entry
        key = self._get_key(entry_type, value)
        self.redis.set(key, json.dumps(entry.to_dict()))

        # Set TTL if specified
        if ttl_days:
            self.redis.expire(key, ttl_days * 86400)  # Convert days to seconds

        # Add to type index
        index_key = self._get_index_key(entry_type)
        self.redis.sadd(index_key, value)

        return entry

    async def check_entry(
        self, entry_type: BlacklistType, value: str
    ) -> Optional[BlacklistEntry]:
        """
        Check if value is in blacklist

        Args:
            entry_type: Type of blacklist entry
            value: Value to check

        Returns:
            BlacklistEntry if found, None otherwise
        """
        key = self._get_key(entry_type, value)
        data = self.redis.get(key)

        if not data:
            return None

        return BlacklistEntry.from_dict(json.loads(data))

    async def remove_entry(self, entry_type: BlacklistType, value: str) -> bool:
        """
        Remove entry from blacklist

        Args:
            entry_type: Type of blacklist entry
            value: Value to remove

        Returns:
            True if removed, False if not found
        """
        key = self._get_key(entry_type, value)
        result = self.redis.delete(key)

        # Remove from type index
        index_key = self._get_index_key(entry_type)
        self.redis.srem(index_key, value)

        return result > 0

    async def list_entries(
        self,
        entry_type: Optional[BlacklistType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[BlacklistEntry]:
        """
        List blacklist entries

        Args:
            entry_type: Filter by type (None = all types)
            limit: Maximum number of entries to return
            offset: Offset for pagination

        Returns:
            List of BlacklistEntry objects
        """
        entries = []

        if entry_type:
            # Get entries for specific type
            index_key = self._get_index_key(entry_type)
            values = list(self.redis.smembers(index_key))

            # Apply pagination
            values = values[offset : offset + limit]

            for value in values:
                key = self._get_key(entry_type, value.decode("utf-8"))
                data = self.redis.get(key)
                if data:
                    entries.append(BlacklistEntry.from_dict(json.loads(data)))
        else:
            # Get all entries (scan all types)
            for bl_type in BlacklistType:
                index_key = self._get_index_key(bl_type)
                values = list(self.redis.smembers(index_key))

                for value in values:
                    key = self._get_key(bl_type, value.decode("utf-8"))
                    data = self.redis.get(key)
                    if data:
                        entries.append(BlacklistEntry.from_dict(json.loads(data)))

            # Apply pagination
            entries = entries[offset : offset + limit]

        return entries

    async def update_ttl(
        self, entry_type: BlacklistType, value: str, ttl_days: int
    ) -> bool:
        """
        Update TTL for blacklist entry

        Args:
            entry_type: Type of blacklist entry
            value: Value to update
            ttl_days: New TTL in days

        Returns:
            True if updated, False if not found
        """
        key = self._get_key(entry_type, value)

        # Check if entry exists
        if not self.redis.exists(key):
            return False

        # Update TTL
        self.redis.expire(key, ttl_days * 86400)

        # Update expires_at in entry data
        data = self.redis.get(key)
        if data:
            entry_dict = json.loads(data)
            entry_dict["expires_at"] = (
                datetime.utcnow() + timedelta(days=ttl_days)
            ).isoformat()
            self.redis.set(key, json.dumps(entry_dict))

        return True

    async def get_entry_count(self, entry_type: Optional[BlacklistType] = None) -> int:
        """
        Get total number of blacklist entries

        Args:
            entry_type: Filter by type (None = all types)

        Returns:
            Number of entries
        """
        if entry_type:
            index_key = self._get_index_key(entry_type)
            return self.redis.scard(index_key)
        else:
            total = 0
            for bl_type in BlacklistType:
                index_key = self._get_index_key(bl_type)
                total += self.redis.scard(index_key)
            return total

    async def is_blacklisted(
        self,
        ip: Optional[str] = None,
        email: Optional[str] = None,
        card_bin: Optional[str] = None,
        user_id: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Dict[str, Optional[BlacklistEntry]]:
        """
        Check multiple values against blacklist

        Args:
            ip: IP address
            email: Email address (will check domain)
            card_bin: Card BIN (first 6 digits)
            user_id: User ID
            phone: Phone number

        Returns:
            Dictionary of blacklist entries found
        """
        results = {}

        if ip:
            results["ip"] = await self.check_entry(BlacklistType.IP, ip)

        if email and "@" in email:
            domain = email.split("@")[1]
            results["email_domain"] = await self.check_entry(
                BlacklistType.EMAIL_DOMAIN, domain
            )

        if card_bin:
            results["card_bin"] = await self.check_entry(
                BlacklistType.CARD_BIN, card_bin
            )

        if user_id:
            results["user_id"] = await self.check_entry(BlacklistType.USER_ID, user_id)

        if phone:
            results["phone"] = await self.check_entry(BlacklistType.PHONE, phone)

        return results
