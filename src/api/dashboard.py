"""Dashboard and metrics API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session
from src.schemas import DashboardMetrics, QueueStatus
from src.services.storage import DocumentRepository
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/metrics",
    response_model=DashboardMetrics,
    summary="Get dashboard metrics",
)
async def get_metrics(
    session: AsyncSession = Depends(get_async_session),
) -> DashboardMetrics:
    """Get overall processing metrics for the dashboard."""
    repo = DocumentRepository(session)
    stats = await repo.get_statistics()
    
    # Get documents this week (approximation)
    documents_this_week = stats["documents_today"] * 7  # Rough estimate
    
    return DashboardMetrics(
        total_documents=stats["total_documents"],
        documents_processed=stats["documents_processed"],
        documents_pending=stats["documents_pending"],
        documents_failed=stats["documents_failed"],
        documents_needs_review=stats["documents_needs_review"],
        average_confidence=stats["average_confidence"],
        average_processing_time=stats["average_processing_time"],
        documents_today=stats["documents_today"],
        documents_this_week=documents_this_week,
    )


@router.get(
    "/queue",
    response_model=QueueStatus,
    summary="Get queue status",
)
async def get_queue_status() -> QueueStatus:
    """Get the current status of the processing queue."""
    # Get queue length from Celery/Redis
    inspect = celery_app.control.inspect()
    
    try:
        # Get active tasks
        active = inspect.active() or {}
        active_count = sum(len(tasks) for tasks in active.values())
        
        # Get scheduled tasks
        scheduled = inspect.scheduled() or {}
        scheduled_count = sum(len(tasks) for tasks in scheduled.values())
        
        # Get reserved tasks
        reserved = inspect.reserved() or {}
        reserved_count = sum(len(tasks) for tasks in reserved.values())
        
        queue_depth = scheduled_count + reserved_count
        
        # Count active workers
        active_workers = len(active)
        
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        queue_depth = 0
        active_workers = 0
    
    return QueueStatus(
        queue_depth=queue_depth,
        active_workers=active_workers,
        average_wait_time=None,  # Would need to track this separately
    )


@router.get(
    "/health",
    summary="Health check",
)
async def health_check(
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Check the health of all system components."""
    health = {
        "status": "healthy",
        "components": {},
    }
    
    # Check database
    try:
        from sqlalchemy import text
        await session.execute(text("SELECT 1"))
        health["components"]["database"] = "healthy"
    except Exception as e:
        health["components"]["database"] = f"unhealthy: {e}"
        health["status"] = "degraded"
    
    # Check Redis/Celery
    try:
        inspect = celery_app.control.inspect()
        ping = inspect.ping()
        if ping:
            health["components"]["celery"] = "healthy"
            health["components"]["workers"] = list(ping.keys())
        else:
            health["components"]["celery"] = "no workers"
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["celery"] = f"unhealthy: {e}"
        health["status"] = "degraded"
    
    return health
