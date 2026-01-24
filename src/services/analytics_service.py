"""
Analytics Service

Module 5: Dashboard, Analytics & Monitoring
Service for calculating analytics, metrics, and generating reports.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from datetime import datetime, timedelta, date

from src.models.campaign import Campaign, CampaignStatus
from src.models.call_session import CallSession, CallStatus, CallOutcome
from src.models.scheduled_call import ScheduledCall, ScheduledCallStatus
from src.models.lead import Lead
from src.schemas.analytics import (
    CampaignMetrics,
    DailyStats,
    ConversationMetrics,
    SystemMetrics,
    LeadActivity
)
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class AnalyticsService:
    """
    Service for analytics and metrics calculations
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_campaign_metrics(self, campaign_id: int) -> Optional[CampaignMetrics]:
        """
        Get comprehensive metrics for a campaign
        """
        # Get campaign
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            return None

        # Get call statistics
        call_stats = await self.db.execute(
            select(
                func.count(CallSession.id).label('total_calls'),
                func.count(case((CallSession.status == CallStatus.COMPLETED, 1))).label('completed'),
                func.count(case((CallSession.status == CallStatus.IN_PROGRESS, 1))).label('in_progress'),
                func.count(case((CallSession.outcome == CallOutcome.QUALIFIED, 1))).label('qualified'),
                func.count(case((CallSession.outcome == CallOutcome.NOT_INTERESTED, 1))).label('not_interested'),
                func.count(case((CallSession.outcome == CallOutcome.NO_ANSWER, 1))).label('no_answer'),
                func.count(case((CallSession.status == CallStatus.FAILED, 1))).label('failed'),
                func.avg(CallSession.duration_seconds).label('avg_duration'),
                func.sum(CallSession.duration_seconds).label('total_duration')
            )
            .select_from(CallSession)
            .join(Lead)
            .where(Lead.campaign_id == campaign_id)
        )
        stats = call_stats.first()

        # Get scheduled call stats
        scheduled_stats = await self.db.execute(
            select(
                func.count(case((ScheduledCall.status == ScheduledCallStatus.PENDING, 1))).label('pending'),
                func.count(case((ScheduledCall.status == ScheduledCallStatus.CALLING, 1))).label('calling')
            )
            .where(ScheduledCall.campaign_id == campaign_id)
        )
        sched_stats = scheduled_stats.first()

        # Calculate rates
        total_calls = stats.total_calls or 0
        completed_calls = stats.completed or 0

        answer_rate = (completed_calls / total_calls * 100) if total_calls > 0 else 0
        qualification_rate = (stats.qualified / completed_calls * 100) if completed_calls > 0 else 0
        conversion_rate = (stats.qualified / campaign.valid_leads * 100) if campaign.valid_leads > 0 else 0

        # Calculate total call time in minutes
        total_duration = stats.total_duration or 0
        total_call_time_minutes = total_duration / 60 if total_duration else None

        return CampaignMetrics(
            campaign_id=campaign.id,
            campaign_name=campaign.name,
            total_leads=campaign.total_leads,
            valid_leads=campaign.valid_leads,
            dnc_filtered=campaign.dnc_filtered,
            calls_initiated=total_calls,
            calls_completed=completed_calls,
            calls_in_progress=stats.in_progress or 0,
            calls_pending=sched_stats.pending or 0,
            calls_qualified=stats.qualified or 0,
            calls_not_interested=stats.not_interested or 0,
            calls_no_answer=stats.no_answer or 0,
            calls_busy=0,  # Add if tracking busy status separately
            calls_failed=stats.failed or 0,
            answer_rate=round(answer_rate, 2),
            qualification_rate=round(qualification_rate, 2),
            conversion_rate=round(conversion_rate, 2),
            avg_call_duration_seconds=round(stats.avg_duration, 2) if stats.avg_duration else None,
            total_call_time_minutes=round(total_call_time_minutes, 2) if total_call_time_minutes else None,
            status=campaign.status.value,
            started_at=campaign.actual_start_time,
            completed_at=campaign.completed_time
        )

    async def get_daily_stats(
        self,
        campaign_id: Optional[int] = None,
        days: int = 7
    ) -> List[DailyStats]:
        """
        Get daily statistics for last N days
        """
        start_date = datetime.utcnow().date() - timedelta(days=days)

        # Base query
        query = select(
            func.date(CallSession.initiated_at).label('date'),
            func.count(CallSession.id).label('calls_made'),
            func.count(case((CallSession.status == CallStatus.COMPLETED, 1))).label('calls_answered'),
            func.count(case((CallSession.outcome == CallOutcome.QUALIFIED, 1))).label('calls_qualified'),
            func.sum(CallSession.duration_seconds).label('total_duration'),
            func.avg(CallSession.duration_seconds).label('avg_duration')
        ).where(
            CallSession.initiated_at >= start_date
        ).group_by(
            func.date(CallSession.initiated_at)
        ).order_by(
            func.date(CallSession.initiated_at)
        )

        # Filter by campaign if specified
        if campaign_id:
            query = query.join(Lead).where(Lead.campaign_id == campaign_id)

        result = await self.db.execute(query)
        rows = result.all()

        daily_stats = []
        for row in rows:
            total_duration_seconds = row.total_duration or 0
            daily_stats.append(DailyStats(
                date=row.date,
                calls_made=row.calls_made,
                calls_answered=row.calls_answered,
                calls_qualified=row.calls_qualified,
                total_duration_minutes=round(total_duration_seconds / 60, 2),
                avg_duration_seconds=round(row.avg_duration, 2) if row.avg_duration else 0
            ))

        return daily_stats

    async def get_conversation_metrics(self, call_sid: str) -> Optional[ConversationMetrics]:
        """
        Get detailed metrics for a single conversation
        """
        result = await self.db.execute(
            select(CallSession)
            .join(Lead)
            .where(CallSession.call_sid == call_sid)
        )
        call_session = result.scalar_one_or_none()

        if not call_session:
            return None

        # Parse transcript
        import json
        transcript = []
        collected_data = {}

        try:
            if call_session.full_transcript:
                transcript = json.loads(call_session.full_transcript)
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if call_session.collected_data:
                collected_data = json.loads(call_session.collected_data)
        except (json.JSONDecodeError, TypeError):
            pass

        # Calculate metrics
        total_exchanges = len([t for t in transcript if t.get("speaker") == "user"])

        # Extract stages (if tracked in collected_data)
        stages_reached = collected_data.get("stages_reached", [])

        # Extract objections
        objections = collected_data.get("objections_encountered", [])

        return ConversationMetrics(
            call_sid=call_session.call_sid,
            lead_name=call_session.lead.name,
            duration_seconds=call_session.duration_seconds or 0,
            total_exchanges=total_exchanges,
            stages_reached=stages_reached,
            objections_encountered=objections,
            objections_count=len(objections),
            outcome=call_session.outcome.value if call_session.outcome else "unknown",
            started_at=call_session.initiated_at,
            ended_at=call_session.ended_at or datetime.utcnow()
        )

    async def get_system_metrics(self) -> SystemMetrics:
        """
        Get system-wide metrics
        """
        # Campaign stats
        campaign_stats = await self.db.execute(
            select(
                func.count(Campaign.id).label('total'),
                func.count(case((Campaign.status == CampaignStatus.RUNNING, 1))).label('active')
            )
        )
        c_stats = campaign_stats.first()

        # Lead stats
        lead_count = await self.db.execute(select(func.count(Lead.id)))
        total_leads = lead_count.scalar()

        # Today's calls
        today = datetime.utcnow().date()
        today_calls = await self.db.execute(
            select(func.count(CallSession.id))
            .where(func.date(CallSession.initiated_at) == today)
        )
        calls_today = today_calls.scalar()

        # Current call status
        current_calls = await self.db.execute(
            select(
                func.count(case((ScheduledCall.status == ScheduledCallStatus.CALLING, 1))).label('in_progress'),
                func.count(case((ScheduledCall.status == ScheduledCallStatus.PENDING, 1))).label('queued')
            )
        )
        current = current_calls.first()

        # Overall rates (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        overall_stats = await self.db.execute(
            select(
                func.count(CallSession.id).label('total'),
                func.count(case((CallSession.status == CallStatus.COMPLETED, 1))).label('answered'),
                func.count(case((CallSession.outcome == CallOutcome.QUALIFIED, 1))).label('qualified')
            )
            .where(CallSession.initiated_at >= thirty_days_ago)
        )
        overall = overall_stats.first()

        answer_rate = (overall.answered / overall.total * 100) if overall.total > 0 else 0
        qualification_rate = (overall.qualified / overall.answered * 100) if overall.answered > 0 else 0

        # Check system health
        from src.database.connection import redis_client
        redis_healthy = False
        try:
            await redis_client.ping()
            redis_healthy = True
        except:
            pass

        return SystemMetrics(
            total_campaigns=c_stats.total,
            active_campaigns=c_stats.active,
            total_leads=total_leads,
            total_calls_today=calls_today,
            calls_in_progress=current.in_progress,
            calls_queued=current.queued,
            overall_answer_rate=round(answer_rate, 2),
            overall_qualification_rate=round(qualification_rate, 2),
            redis_connected=redis_healthy,
            database_connected=True,  # If we got here, DB is connected
            exotel_api_healthy=True  # TODO: Add actual health check
        )

    async def get_lead_activity(
        self,
        campaign_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[LeadActivity]:
        """
        Get recent lead activity
        """
        # Build query
        query = select(Lead).order_by(Lead.last_call_attempt.desc().nullslast()).limit(limit)

        if campaign_id:
            query = query.where(Lead.campaign_id == campaign_id)

        # Get leads
        result = await self.db.execute(query)
        leads = result.scalars().all()

        activities = []
        for lead in leads:
            # Get last call
            last_call_result = await self.db.execute(
                select(CallSession)
                .where(CallSession.lead_id == lead.id)
                .order_by(CallSession.initiated_at.desc())
                .limit(1)
            )
            last_call = last_call_result.scalar_one_or_none()

            # Get next scheduled call
            next_call_result = await self.db.execute(
                select(ScheduledCall)
                .where(
                    and_(
                        ScheduledCall.lead_id == lead.id,
                        ScheduledCall.status == ScheduledCallStatus.PENDING
                    )
                )
                .order_by(ScheduledCall.scheduled_time)
                .limit(1)
            )
            next_call = next_call_result.scalar_one_or_none()

            # Determine status
            if last_call and last_call.outcome:
                current_status = last_call.outcome.value
            elif next_call:
                current_status = "scheduled"
            else:
                current_status = "pending"

            activities.append(LeadActivity(
                lead_id=lead.id,
                lead_name=lead.name,
                phone=lead.phone,
                property_type=lead.property_type,
                location=lead.location,
                total_attempts=lead.call_attempts,
                last_attempt=lead.last_call_attempt,
                last_outcome=last_call.outcome.value if last_call and last_call.outcome else None,
                current_status=current_status,
                next_action="call" if next_call else None,
                next_scheduled_call=next_call.scheduled_time if next_call else None
            ))

        return activities
