"""
Call Scheduler Service for scheduling calls and managing retries.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta

from src.models.scheduled_call import ScheduledCall, ScheduledCallStatus
from src.models.lead import Lead
from src.models.campaign import Campaign
from src.utils.logger import get_logger
from src.config.settings import settings

logger = get_logger(__name__, settings.ENVIRONMENT)


class CallScheduler:
    """
    Service for scheduling calls to leads
    Handles call queuing, retry scheduling, and calling hours enforcement
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def schedule_campaign_calls(self, campaign_id: int) -> int:
        """
        Schedule calls for all leads in a campaign

        Returns number of calls scheduled
        """
        # Get all leads for campaign that haven't been scheduled yet
        result = await self.db.execute(
            select(Lead)
            .where(
                Lead.campaign_id == campaign_id,
                ~Lead.id.in_(
                    select(ScheduledCall.lead_id)
                    .where(ScheduledCall.campaign_id == campaign_id)
                )
            )
        )
        leads = result.scalars().all()

        if not leads:
            logger.info("No new leads to schedule", extra={"campaign_id": campaign_id})
            return 0

        # Get campaign settings
        campaign_result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = campaign_result.scalar_one()

        # Schedule calls
        scheduled_calls = []
        current_time = datetime.utcnow()

        for lead in leads:
            # Calculate initial scheduled time (respecting calling hours)
            scheduled_time = self._get_next_available_slot(
                current_time,
                calling_hours_start=campaign.calling_hours_start,
                calling_hours_end=campaign.calling_hours_end
            )

            scheduled_call = ScheduledCall(
                campaign_id=campaign_id,
                lead_id=lead.id,
                scheduled_time=scheduled_time,
                max_attempts=campaign.max_attempts_per_lead,
                status=ScheduledCallStatus.PENDING
            )
            scheduled_calls.append(scheduled_call)

        self.db.add_all(scheduled_calls)
        await self.db.commit()

        logger.info(
            "Campaign calls scheduled",
            extra={
                "campaign_id": campaign_id,
                "count": len(scheduled_calls)
            }
        )

        return len(scheduled_calls)

    def _get_next_available_slot(
        self,
        from_time: datetime,
        calling_hours_start: int = 10,
        calling_hours_end: int = 19
    ) -> datetime:
        """
        Get next available time slot respecting calling hours

        Rules:
        - Between calling_hours_start and calling_hours_end (default 10 AM - 7 PM)
        - Not on Sundays
        - If outside hours, schedule for next day at opening time
        """
        target_time = from_time

        # Check if current time is within calling hours
        if target_time.hour < calling_hours_start:
            # Before calling hours - schedule for today at opening
            target_time = target_time.replace(
                hour=calling_hours_start,
                minute=0,
                second=0,
                microsecond=0
            )
        elif target_time.hour >= calling_hours_end:
            # After calling hours - schedule for tomorrow at opening
            target_time = target_time + timedelta(days=1)
            target_time = target_time.replace(
                hour=calling_hours_start,
                minute=0,
                second=0,
                microsecond=0
            )

        # Skip Sunday (weekday() returns 6 for Sunday)
        while target_time.weekday() == 6:
            target_time = target_time + timedelta(days=1)

        return target_time

    async def get_pending_calls(
        self,
        limit: int = 100,
        max_concurrent: int = 10
    ) -> List[ScheduledCall]:
        """
        Get pending calls that are ready to be executed

        Criteria:
        - Status is PENDING
        - Scheduled time has passed
        - Within calling hours
        - Respects max concurrent limit
        """
        current_time = datetime.utcnow()
        current_hour = current_time.hour

        # Check if within calling hours
        if current_hour < settings.CALLING_HOURS_START or current_hour >= settings.CALLING_HOURS_END:
            logger.debug("Outside calling hours", extra={"current_hour": current_hour})
            return []

        # Check Sunday
        if current_time.weekday() == 6:
            logger.debug("Sunday - no calls")
            return []

        # Count currently active calls
        active_result = await self.db.execute(
            select(ScheduledCall)
            .where(ScheduledCall.status == ScheduledCallStatus.CALLING)
        )
        active_count = len(active_result.scalars().all())

        if active_count >= max_concurrent:
            logger.debug(
                "Max concurrent calls reached",
                extra={
                    "active": active_count,
                    "max": max_concurrent
                }
            )
            return []

        # Get available slots
        available_slots = max_concurrent - active_count
        fetch_limit = min(limit, available_slots)

        # Get pending calls
        result = await self.db.execute(
            select(ScheduledCall)
            .where(
                and_(
                    ScheduledCall.status == ScheduledCallStatus.PENDING,
                    ScheduledCall.scheduled_time <= current_time
                )
            )
            .order_by(ScheduledCall.scheduled_time)
            .limit(fetch_limit)
        )

        return result.scalars().all()

    async def schedule_retry(
        self,
        scheduled_call_id: int,
        failure_reason: str,
        delay_hours: int = 2
    ) -> Optional[ScheduledCall]:
        """
        Schedule a retry for a failed call
        """
        result = await self.db.execute(
            select(ScheduledCall).where(ScheduledCall.id == scheduled_call_id)
        )
        scheduled_call = result.scalar_one_or_none()

        if not scheduled_call:
            return None

        # Check if we've exhausted retries
        if scheduled_call.attempt_number >= scheduled_call.max_attempts:
            scheduled_call.status = ScheduledCallStatus.MAX_RETRIES_REACHED
            scheduled_call.failure_reason = f"Max retries reached. Last: {failure_reason}"
            await self.db.commit()

            logger.info(
                "Max retries reached",
                extra={
                    "scheduled_call_id": scheduled_call_id,
                    "attempts": scheduled_call.attempt_number
                }
            )

            return scheduled_call

        # Schedule retry
        retry_time = datetime.utcnow() + timedelta(hours=delay_hours)
        retry_time = self._get_next_available_slot(retry_time)

        scheduled_call.scheduled_time = retry_time
        scheduled_call.status = ScheduledCallStatus.PENDING
        scheduled_call.attempt_number += 1
        scheduled_call.failure_reason = failure_reason

        await self.db.commit()

        logger.info(
            "Call retry scheduled",
            extra={
                "scheduled_call_id": scheduled_call_id,
                "attempt": scheduled_call.attempt_number,
                "retry_time": retry_time.isoformat()
            }
        )

        return scheduled_call

    async def update_call_status(
        self,
        scheduled_call_id: int,
        status: ScheduledCallStatus,
        call_sid: str = None,
        exotel_status: str = None
    ):
        """
        Update scheduled call status
        """
        result = await self.db.execute(
            select(ScheduledCall).where(ScheduledCall.id == scheduled_call_id)
        )
        scheduled_call = result.scalar_one_or_none()

        if not scheduled_call:
            return

        scheduled_call.status = status
        scheduled_call.last_attempt_time = datetime.utcnow()

        if call_sid:
            scheduled_call.current_call_sid = call_sid

        if exotel_status:
            scheduled_call.last_call_status = exotel_status

        await self.db.commit()
