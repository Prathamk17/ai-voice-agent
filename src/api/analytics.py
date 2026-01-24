"""
Analytics API Endpoints

Module 5: Dashboard, Analytics & Monitoring
FastAPI routes for analytics and metrics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from src.database.connection import get_db_session
from src.services.analytics_service import AnalyticsService
from src.schemas.analytics import (
    CampaignMetrics,
    DailyStats,
    ConversationMetrics,
    SystemMetrics,
    LeadActivity
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/campaigns/{campaign_id}/metrics", response_model=CampaignMetrics)
async def get_campaign_metrics(
    campaign_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get comprehensive metrics for a campaign

    Includes:
    - Lead statistics
    - Call statistics
    - Success rates
    - Duration metrics
    """
    service = AnalyticsService(db)
    metrics = await service.get_campaign_metrics(campaign_id)

    if not metrics:
        raise HTTPException(404, "Campaign not found")

    return metrics


@router.get("/daily-stats", response_model=List[DailyStats])
async def get_daily_stats(
    campaign_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get daily statistics

    Parameters:
    - campaign_id: Optional campaign filter
    - days: Number of days to include (1-90, default 7)
    """
    service = AnalyticsService(db)
    stats = await service.get_daily_stats(campaign_id, days)
    return stats


@router.get("/conversations/{call_sid}", response_model=ConversationMetrics)
async def get_conversation_metrics(
    call_sid: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed metrics for a single conversation

    Includes:
    - Conversation length and exchanges
    - Stages reached
    - Objections encountered
    - Outcome
    """
    service = AnalyticsService(db)
    metrics = await service.get_conversation_metrics(call_sid)

    if not metrics:
        raise HTTPException(404, "Call session not found")

    return metrics


@router.get("/system", response_model=SystemMetrics)
async def get_system_metrics(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get system-wide metrics

    Includes:
    - Total campaigns and active campaigns
    - Total leads
    - Current call status
    - Overall success rates
    - System health status
    """
    service = AnalyticsService(db)
    metrics = await service.get_system_metrics()
    return metrics


@router.get("/leads/activity", response_model=List[LeadActivity])
async def get_lead_activity(
    campaign_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get recent lead activity

    Parameters:
    - campaign_id: Optional campaign filter
    - status: Optional status filter
    - limit: Number of leads to return (1-1000, default 100)
    """
    service = AnalyticsService(db)
    activity = await service.get_lead_activity(campaign_id, status, limit)
    return activity
