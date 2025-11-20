"""
Monitoring API Endpoints

Provides endpoints for monitoring model performance and data drift.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.monitoring.drift_detector import DriftDetector
from src.monitoring.performance_monitor import PerformanceMonitor
from src.database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ml/monitoring", tags=["monitoring"])


@router.get("/drift")
async def get_drift_status(
    features: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get data drift status

    Args:
        features: Comma-separated list of features to check (optional)
        db: Database session

    Returns:
        Drift detection results
    """
    try:
        drift_detector = DriftDetector(db)

        # Parse features if provided
        feature_list = features.split(",") if features else None

        # Detect drift
        result = await drift_detector.detect_all_features_drift(feature_list)

        return {
            "status": "success",
            "data": result,
        }

    except Exception as e:
        logger.error(f"[MONITORING_API] Error getting drift status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drift/history")
async def get_drift_history(
    days: int = 30,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get drift detection history

    Args:
        days: Number of days to look back
        db: Database session

    Returns:
        Drift history
    """
    try:
        drift_detector = DriftDetector(db)
        history = await drift_detector.get_drift_history(days)

        return {
            "status": "success",
            "data": history,
        }

    except Exception as e:
        logger.error(f"[MONITORING_API] Error getting drift history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drift/summary")
async def get_drift_summary(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get drift summary

    Args:
        db: Database session

    Returns:
        Drift summary
    """
    try:
        drift_detector = DriftDetector(db)
        summary = await drift_detector.get_drift_summary()

        return {
            "status": "success",
            "data": summary,
        }

    except Exception as e:
        logger.error(f"[MONITORING_API] Error getting drift summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance_status(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get current performance status

    Args:
        db: Database session

    Returns:
        Performance status
    """
    try:
        performance_monitor = PerformanceMonitor(db)
        result = await performance_monitor.evaluate_current_performance()

        return {
            "status": "success",
            "data": result,
        }

    except Exception as e:
        logger.error(f"[MONITORING_API] Error getting performance status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/history")
async def get_performance_history(
    days: int = 30,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get performance monitoring history

    Args:
        days: Number of days to look back
        db: Database session

    Returns:
        Performance history
    """
    try:
        performance_monitor = PerformanceMonitor(db)
        history = await performance_monitor.get_performance_history(days)

        return {
            "status": "success",
            "data": history,
        }

    except Exception as e:
        logger.error(f"[MONITORING_API] Error getting performance history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/summary")
async def get_performance_summary(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get performance summary

    Args:
        db: Database session

    Returns:
        Performance summary
    """
    try:
        performance_monitor = PerformanceMonitor(db)
        summary = await performance_monitor.get_performance_summary()

        return {
            "status": "success",
            "data": summary,
        }

    except Exception as e:
        logger.error(f"[MONITORING_API] Error getting performance summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/trend")
async def get_performance_trend(
    days: int = 30,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get performance trend analysis

    Args:
        days: Number of days to analyze
        db: Database session

    Returns:
        Trend analysis
    """
    try:
        performance_monitor = PerformanceMonitor(db)
        trend = await performance_monitor.get_performance_trend(days)

        return {
            "status": "success",
            "data": trend,
        }

    except Exception as e:
        logger.error(f"[MONITORING_API] Error getting performance trend: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
