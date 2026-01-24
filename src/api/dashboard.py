"""
Dashboard API Endpoints

Module 5: Dashboard, Analytics & Monitoring
FastAPI routes for dashboard data and real-time updates.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from datetime import datetime

from src.database.connection import get_db_session
from src.database.repositories import CampaignRepository
from src.services.analytics_service import AnalyticsService
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get dashboard overview with key metrics

    Returns:
    - System-wide metrics
    - Recent campaigns summary
    - Daily statistics for the last 7 days
    """
    analytics = AnalyticsService(db)
    campaign_repo = CampaignRepository(db)

    # System metrics
    system_metrics = await analytics.get_system_metrics()

    # Recent campaigns
    campaigns = await campaign_repo.get_all(skip=0, limit=10, include_deleted=False)

    # Get metrics for each recent campaign
    campaign_summaries = []
    for campaign in campaigns:
        metrics = await analytics.get_campaign_metrics(campaign.id)
        if metrics:
            campaign_summaries.append({
                "id": campaign.id,
                "name": campaign.name,
                "status": campaign.status.value,
                "calls_completed": metrics.calls_completed,
                "calls_qualified": metrics.calls_qualified,
                "answer_rate": metrics.answer_rate,
                "qualification_rate": metrics.qualification_rate
            })

    # Daily stats for last 7 days
    daily_stats = await analytics.get_daily_stats(days=7)

    return {
        "system": system_metrics,
        "recent_campaigns": campaign_summaries,
        "daily_stats": daily_stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/realtime")
async def get_realtime_data(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get real-time data for dashboard
    Should be polled every few seconds for live updates

    Returns:
    - Number of calls in progress
    - Active call details
    - Calls queued
    - Latest system metrics
    """
    analytics = AnalyticsService(db)
    system_metrics = await analytics.get_system_metrics()

    # Active calls info
    active_calls = []
    try:
        from src.websocket.server import websocket_server
        from src.websocket.session_manager import SessionManager

        session_mgr = SessionManager()

        for call_sid in list(websocket_server.active_connections.keys()):
            try:
                session = await session_mgr.get_session(call_sid)

                if session:
                    duration = (datetime.utcnow() - session.session_start_time).total_seconds()
                    active_calls.append({
                        "call_sid": call_sid,
                        "lead_name": session.lead_name,
                        "stage": session.conversation_stage,
                        "duration_seconds": int(duration)
                    })
            except Exception as e:
                logger.error(f"Error getting session for {call_sid}", error=str(e))
                continue

    except Exception as e:
        logger.error("Error getting active calls", error=str(e))

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "calls_in_progress": len(active_calls),
        "active_calls": active_calls,
        "calls_queued": system_metrics.calls_queued,
        "total_calls_today": system_metrics.total_calls_today
    }


@router.get("/campaigns/{campaign_id}/summary")
async def get_campaign_summary(
    campaign_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed summary for a specific campaign

    Includes:
    - Campaign metrics
    - Daily stats for the campaign
    - Recent lead activity
    """
    analytics = AnalyticsService(db)

    # Get campaign metrics
    metrics = await analytics.get_campaign_metrics(campaign_id)
    if not metrics:
        from fastapi import HTTPException
        raise HTTPException(404, "Campaign not found")

    # Get daily stats for this campaign (last 30 days)
    daily_stats = await analytics.get_daily_stats(campaign_id=campaign_id, days=30)

    # Get recent lead activity
    lead_activity = await analytics.get_lead_activity(campaign_id=campaign_id, limit=50)

    return {
        "metrics": metrics,
        "daily_stats": daily_stats,
        "recent_activity": lead_activity,
        "timestamp": datetime.utcnow().isoformat()
    }
