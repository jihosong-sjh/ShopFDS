"""
Blacklist Management API - Admin Dashboard
Feature: 002-production-infra
Task: T029

Provides REST API for managing blacklist entries in Redis Cluster.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from datetime import datetime

from ..dependencies import get_redis_cluster, get_current_user
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../../fds/src"))

from cache.blacklist import (
    BlacklistManager,
    BlacklistType,
    BlacklistReason,
    BlacklistEntry,
)

router = APIRouter(prefix="/v1/admin/blacklist", tags=["Blacklist Management"])


# --- Request/Response Models ---


class BlacklistAddRequest(BaseModel):
    """Request model for adding blacklist entry"""

    entry_type: BlacklistType = Field(..., description="Type of blacklist entry")
    value: str = Field(..., description="Value to blacklist (IP, email domain, card BIN, etc.)")
    reason: BlacklistReason = Field(..., description="Reason for blacklisting")
    ttl_days: Optional[int] = Field(
        None, description="TTL in days (None = no expiry)", ge=1, le=365
    )
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata")


class BlacklistUpdateTTLRequest(BaseModel):
    """Request model for updating TTL"""

    ttl_days: int = Field(..., description="New TTL in days", ge=1, le=365)


class BlacklistEntryResponse(BaseModel):
    """Response model for blacklist entry"""

    id: str
    entry_type: str
    value: str
    reason: str
    added_by: str
    added_at: Optional[datetime]
    expires_at: Optional[datetime]
    metadata: dict

    @classmethod
    def from_entry(cls, entry: BlacklistEntry) -> "BlacklistEntryResponse":
        """Convert BlacklistEntry to response model"""
        return cls(
            id=entry.id,
            entry_type=entry.entry_type,
            value=entry.value,
            reason=entry.reason,
            added_by=entry.added_by,
            added_at=entry.added_at,
            expires_at=entry.expires_at,
            metadata=entry.metadata,
        )


class BlacklistListResponse(BaseModel):
    """Response model for blacklist listing"""

    total: int
    entries: List[BlacklistEntryResponse]
    offset: int
    limit: int


# --- API Endpoints ---


@router.post(
    "",
    response_model=BlacklistEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add blacklist entry",
    description="Add a new entry to the blacklist (IP, email domain, card BIN, user ID, phone)",
)
async def add_blacklist_entry(
    request: BlacklistAddRequest,
    redis_cluster=Depends(get_redis_cluster),
    current_user=Depends(get_current_user),
):
    """
    Add a new blacklist entry

    - **entry_type**: Type of entry (ip, email_domain, card_bin, user_id, phone)
    - **value**: Value to blacklist
    - **reason**: Reason for blacklisting (fraud_detected, chargeback, etc.)
    - **ttl_days**: TTL in days (optional, None = permanent)
    - **metadata**: Additional metadata (optional)
    """
    try:
        blacklist_manager = BlacklistManager(redis_cluster)

        entry = await blacklist_manager.add_entry(
            entry_type=request.entry_type,
            value=request.value,
            reason=request.reason,
            added_by=current_user.id,  # Use authenticated user ID
            ttl_days=request.ttl_days,
            metadata=request.metadata,
        )

        return BlacklistEntryResponse.from_entry(entry)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add blacklist entry: {str(e)}",
        )


@router.get(
    "",
    response_model=BlacklistListResponse,
    summary="List blacklist entries",
    description="Get list of blacklist entries with pagination and optional type filter",
)
async def list_blacklist_entries(
    entry_type: Optional[BlacklistType] = Query(None, description="Filter by entry type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    redis_cluster=Depends(get_redis_cluster),
    current_user=Depends(get_current_user),
):
    """
    List blacklist entries with pagination

    - **entry_type**: Filter by type (optional)
    - **limit**: Maximum number of entries (default: 100, max: 1000)
    - **offset**: Offset for pagination (default: 0)
    """
    try:
        blacklist_manager = BlacklistManager(redis_cluster)

        entries = await blacklist_manager.list_entries(
            entry_type=entry_type,
            limit=limit,
            offset=offset,
        )

        total = await blacklist_manager.get_entry_count(entry_type=entry_type)

        return BlacklistListResponse(
            total=total,
            entries=[BlacklistEntryResponse.from_entry(entry) for entry in entries],
            offset=offset,
            limit=limit,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list blacklist entries: {str(e)}",
        )


@router.get(
    "/{entry_type}/{value}",
    response_model=BlacklistEntryResponse,
    summary="Get blacklist entry",
    description="Get a specific blacklist entry by type and value",
)
async def get_blacklist_entry(
    entry_type: BlacklistType,
    value: str,
    redis_cluster=Depends(get_redis_cluster),
    current_user=Depends(get_current_user),
):
    """
    Get a specific blacklist entry

    - **entry_type**: Type of entry
    - **value**: Value to check
    """
    try:
        blacklist_manager = BlacklistManager(redis_cluster)

        entry = await blacklist_manager.check_entry(entry_type=entry_type, value=value)

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blacklist entry not found: {entry_type}:{value}",
            )

        return BlacklistEntryResponse.from_entry(entry)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get blacklist entry: {str(e)}",
        )


@router.delete(
    "/{entry_type}/{value}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove blacklist entry",
    description="Remove a blacklist entry",
)
async def remove_blacklist_entry(
    entry_type: BlacklistType,
    value: str,
    redis_cluster=Depends(get_redis_cluster),
    current_user=Depends(get_current_user),
):
    """
    Remove a blacklist entry

    - **entry_type**: Type of entry
    - **value**: Value to remove
    """
    try:
        blacklist_manager = BlacklistManager(redis_cluster)

        removed = await blacklist_manager.remove_entry(entry_type=entry_type, value=value)

        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blacklist entry not found: {entry_type}:{value}",
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove blacklist entry: {str(e)}",
        )


@router.patch(
    "/{entry_type}/{value}/ttl",
    response_model=BlacklistEntryResponse,
    summary="Update blacklist entry TTL",
    description="Update the TTL (time-to-live) for a blacklist entry",
)
async def update_blacklist_ttl(
    entry_type: BlacklistType,
    value: str,
    request: BlacklistUpdateTTLRequest,
    redis_cluster=Depends(get_redis_cluster),
    current_user=Depends(get_current_user),
):
    """
    Update TTL for a blacklist entry

    - **entry_type**: Type of entry
    - **value**: Value to update
    - **ttl_days**: New TTL in days
    """
    try:
        blacklist_manager = BlacklistManager(redis_cluster)

        updated = await blacklist_manager.update_ttl(
            entry_type=entry_type,
            value=value,
            ttl_days=request.ttl_days,
        )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blacklist entry not found: {entry_type}:{value}",
            )

        # Fetch updated entry
        entry = await blacklist_manager.check_entry(entry_type=entry_type, value=value)

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Entry updated but failed to fetch updated data",
            )

        return BlacklistEntryResponse.from_entry(entry)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update blacklist TTL: {str(e)}",
        )
