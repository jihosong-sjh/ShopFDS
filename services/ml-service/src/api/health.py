"""
Enhanced Health Check API for ShopFDS Ecommerce Service
Checks: DB connection, Redis PING, disk space, replication lag
"""

import shutil
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.db.connection import get_write_db, get_read_db, get_redis

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any])
async def health_check():
    """
    Comprehensive health check endpoint

    Returns:
        200 OK: All systems operational
        503 Service Unavailable: One or more systems failing
    """
    health_status = {
        "service": "ml-service",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "checks": {},
    }

    all_healthy = True

    # Check 1: Database Write Connection
    try:
        async for db in get_write_db():
            await db.execute(text("SELECT 1"))
            health_status["checks"]["database_write"] = {
                "status": "healthy",
                "message": "Write database connection OK",
            }
            break
    except Exception as e:
        all_healthy = False
        health_status["checks"]["database_write"] = {
            "status": "unhealthy",
            "message": f"Write database connection failed: {str(e)}",
        }

    # Check 2: Database Read Connection (Read Replica)
    try:
        async for db in get_read_db():
            await db.execute(text("SELECT 1"))
            health_status["checks"]["database_read"] = {
                "status": "healthy",
                "message": "Read replica connection OK",
            }
            break
    except Exception as e:
        all_healthy = False
        health_status["checks"]["database_read"] = {
            "status": "unhealthy",
            "message": f"Read replica connection failed: {str(e)}",
        }

    # Check 3: Redis Connection
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection OK",
        }
    except Exception as e:
        all_healthy = False
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}",
        }

    # Check 4: Disk Space (must be < 90%)
    try:
        disk_usage = shutil.disk_usage("/")
        disk_percent = (disk_usage.used / disk_usage.total) * 100

        if disk_percent < 90:
            health_status["checks"]["disk_space"] = {
                "status": "healthy",
                "message": f"Disk usage: {disk_percent:.2f}%",
                "used_gb": disk_usage.used // (1024**3),
                "total_gb": disk_usage.total // (1024**3),
            }
        else:
            all_healthy = False
            health_status["checks"]["disk_space"] = {
                "status": "unhealthy",
                "message": f"Disk usage critical: {disk_percent:.2f}%",
                "used_gb": disk_usage.used // (1024**3),
                "total_gb": disk_usage.total // (1024**3),
            }
    except Exception as e:
        health_status["checks"]["disk_space"] = {
            "status": "unknown",
            "message": f"Disk space check failed: {str(e)}",
        }

    # Check 5: Replication Lag (if replication_monitor exists)
    try:
        from src.utils.replication_monitor import check_replication_lag

        async for db in get_write_db():
            lag = await check_replication_lag(db)

            if lag and lag > 10:  # > 10 seconds is unhealthy
                all_healthy = False
                health_status["checks"]["replication_lag"] = {
                    "status": "unhealthy",
                    "message": f"Replication lag too high: {lag}s",
                    "lag_seconds": lag,
                }
            else:
                health_status["checks"]["replication_lag"] = {
                    "status": "healthy",
                    "message": "Replication lag OK",
                    "lag_seconds": lag if lag else 0,
                }
            break
    except ImportError:
        health_status["checks"]["replication_lag"] = {
            "status": "skipped",
            "message": "Replication monitoring not configured",
        }
    except Exception as e:
        health_status["checks"]["replication_lag"] = {
            "status": "unknown",
            "message": f"Replication lag check failed: {str(e)}",
        }

    # Set overall status
    if all_healthy:
        health_status["status"] = "healthy"
        return JSONResponse(content=health_status, status_code=status.HTTP_200_OK)
    else:
        health_status["status"] = "unhealthy"
        return JSONResponse(
            content=health_status, status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@router.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes"""
    try:
        async for db in get_write_db():
            await db.execute(text("SELECT 1"))
            break
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(
            content={"status": "not ready", "error": str(e)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@router.get("/live")
async def liveness_check():
    """Liveness probe for Kubernetes"""
    return {"status": "alive", "service": "ml-service"}
