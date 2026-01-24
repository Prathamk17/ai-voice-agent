"""
Health check endpoints for service monitoring and readiness probes.
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict

from src.database.connection import get_db_session, get_redis_client

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint.
    Returns 200 if service is running.

    Returns:
        dict: Status message
    """
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check(
    response: Response,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Readiness check endpoint.
    Verifies database and Redis connections are working.

    This endpoint is used by load balancers and orchestrators
    to determine if the service is ready to receive traffic.

    Args:
        response: FastAPI response object
        db: Database session

    Returns:
        dict: Status of all dependencies
    """
    try:
        # Check database connection
        await db.execute(text("SELECT 1"))

        # Check Redis connection
        redis = await get_redis_client()
        await redis.ping()

        return {
            "status": "ready",
            "database": "connected",
            "redis": "connected"
        }

    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "error": str(e)
        }


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check endpoint.
    Returns 200 if the service process is alive.

    Used by orchestrators to detect if service needs to be restarted.

    Returns:
        dict: Status message
    """
    return {"status": "alive"}


@router.get("/detailed")
async def detailed_health_check(response: Response):
    """
    Detailed health check of all components

    Module 5: Dashboard, Analytics & Monitoring
    Returns comprehensive health status of all system components.
    """
    from src.monitoring.health_checks import health_checker

    health_status = await health_checker.get_full_health_status()

    # Set appropriate status code
    if health_status["status"] == "healthy":
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return health_status


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint

    Module 5: Dashboard, Analytics & Monitoring
    Returns metrics in Prometheus format for monitoring.
    """
    from src.monitoring.metrics import metrics

    return metrics.get_metrics()
