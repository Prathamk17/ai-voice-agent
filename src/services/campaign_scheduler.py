"""Campaign scheduler service for automated campaign management."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_async_session_maker
from src.database.repositories import CampaignRepository
from src.models.campaign import Campaign, CampaignStatus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CampaignScheduler:
    """
    Background service for campaign scheduling and monitoring.

    Responsibilities:
    - Check for campaigns scheduled to start
    - Monitor running campaigns
    - Auto-complete campaigns past their end time
    - Track campaign metrics
    """

    def __init__(self, check_interval_seconds: int = 60):
        """
        Initialize campaign scheduler.

        Args:
            check_interval_seconds: How often to check for campaign updates
        """
        self.check_interval = check_interval_seconds
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the campaign scheduler background task."""
        if self.running:
            logger.warning("Campaign scheduler is already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(
            "Campaign scheduler started",
            check_interval_seconds=self.check_interval
        )

    async def stop(self):
        """Stop the campaign scheduler background task."""
        if not self.running:
            return

        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Campaign scheduler stopped")

    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self.running:
            try:
                await self._check_scheduled_campaigns()
                await self._check_expired_campaigns()
                await self._update_campaign_metrics()
            except Exception as e:
                logger.error(f"Error in campaign scheduler: {str(e)}")

            # Wait before next check
            await asyncio.sleep(self.check_interval)

    async def _check_scheduled_campaigns(self):
        """Check for campaigns that should be started."""
        try:
            async_session_maker = get_async_session_maker()
            async with async_session_maker() as session:
                campaign_repo = CampaignRepository(session)
                current_time = datetime.utcnow()

                # Get campaigns scheduled to start
                scheduled_campaigns = await campaign_repo.get_scheduled_campaigns(
                    current_time
                )

                for campaign in scheduled_campaigns:
                    try:
                        # Validate campaign has leads
                        if campaign.total_leads == 0:
                            logger.warning(
                                "Skipping campaign start - no leads",
                                campaign_id=campaign.id,
                                campaign_name=campaign.name
                            )
                            # Update to draft status
                            await campaign_repo.update_status(
                                campaign.id,
                                CampaignStatus.DRAFT
                            )
                            continue

                        # Start the campaign
                        await campaign_repo.update_status(
                            campaign.id,
                            CampaignStatus.RUNNING
                        )

                        logger.info(
                            "Campaign auto-started by scheduler",
                            campaign_id=campaign.id,
                            campaign_name=campaign.name,
                            total_leads=campaign.total_leads
                        )

                    except Exception as e:
                        logger.error(
                            f"Failed to start campaign: {str(e)}",
                            campaign_id=campaign.id
                        )

                await session.commit()

        except Exception as e:
            logger.error(f"Error checking scheduled campaigns: {str(e)}")

    async def _check_expired_campaigns(self):
        """Check for campaigns that have passed their end time."""
        try:
            async_session_maker = get_async_session_maker()
            async with async_session_maker() as session:
                campaign_repo = CampaignRepository(session)
                current_time = datetime.utcnow()

                # Get active running campaigns
                active_campaigns = await campaign_repo.get_active_campaigns()

                for campaign in active_campaigns:
                    try:
                        # Check if campaign has exceeded scheduled end time
                        if (
                            campaign.scheduled_end_time and
                            current_time > campaign.scheduled_end_time
                        ):
                            await campaign_repo.update_status(
                                campaign.id,
                                CampaignStatus.COMPLETED
                            )

                            logger.info(
                                "Campaign auto-completed - end time reached",
                                campaign_id=campaign.id,
                                campaign_name=campaign.name,
                                scheduled_end_time=campaign.scheduled_end_time
                            )

                        # Check if all leads have been attempted
                        elif (
                            campaign.status == CampaignStatus.RUNNING and
                            campaign.total_leads > 0
                        ):
                            pending_leads = await campaign_repo.get_pending_leads(
                                campaign.id,
                                campaign.max_attempts_per_lead
                            )

                            if len(pending_leads) == 0:
                                await campaign_repo.update_status(
                                    campaign.id,
                                    CampaignStatus.COMPLETED
                                )

                                logger.info(
                                    "Campaign auto-completed - all leads processed",
                                    campaign_id=campaign.id,
                                    campaign_name=campaign.name,
                                    total_leads=campaign.total_leads
                                )

                    except Exception as e:
                        logger.error(
                            f"Error checking campaign expiry: {str(e)}",
                            campaign_id=campaign.id
                        )

                await session.commit()

        except Exception as e:
            logger.error(f"Error checking expired campaigns: {str(e)}")

    async def _update_campaign_metrics(self):
        """Update metrics for active campaigns."""
        try:
            async_session_maker = get_async_session_maker()
            async with async_session_maker() as session:
                campaign_repo = CampaignRepository(session)

                # Get running campaigns
                active_campaigns = await campaign_repo.get_active_campaigns()

                for campaign in active_campaigns:
                    try:
                        # Recalculate metrics
                        campaign.calculate_metrics()

                    except Exception as e:
                        logger.error(
                            f"Error updating campaign metrics: {str(e)}",
                            campaign_id=campaign.id
                        )

                await session.commit()

        except Exception as e:
            logger.error(f"Error updating campaign metrics: {str(e)}")

    async def get_next_campaign_to_call(
        self,
        session: AsyncSession
    ) -> Optional[tuple[Campaign, int]]:
        """
        Get the next campaign that should make a call and a lead ID.

        Args:
            session: Database session

        Returns:
            Tuple of (Campaign, lead_id) or None
        """
        try:
            campaign_repo = CampaignRepository(session)
            current_time = datetime.utcnow()
            current_hour = current_time.hour

            # Get running campaigns
            running_campaigns = await campaign_repo.get_active_campaigns()

            for campaign in running_campaigns:
                # Check if within calling hours
                if not (
                    campaign.calling_hours_start <= current_hour < campaign.calling_hours_end
                ):
                    continue

                # Get pending leads for this campaign
                pending_leads = await campaign_repo.get_pending_leads(
                    campaign.id,
                    campaign.max_attempts_per_lead
                )

                if pending_leads:
                    # Check retry delay for leads with previous attempts
                    for lead in pending_leads:
                        # If never called, can call immediately
                        if lead.call_attempts == 0:
                            return (campaign, lead.id)

                        # Check retry delay
                        if lead.last_call_attempt:
                            time_since_last_call = current_time - lead.last_call_attempt
                            retry_delay = timedelta(hours=campaign.retry_delay_hours)

                            if time_since_last_call >= retry_delay:
                                return (campaign, lead.id)

            return None

        except Exception as e:
            logger.error(f"Error getting next campaign to call: {str(e)}")
            return None


# Global scheduler instance
_scheduler: Optional[CampaignScheduler] = None


def get_campaign_scheduler() -> CampaignScheduler:
    """Get or create the global campaign scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = CampaignScheduler()
    return _scheduler


async def start_campaign_scheduler():
    """Start the global campaign scheduler."""
    scheduler = get_campaign_scheduler()
    await scheduler.start()


async def stop_campaign_scheduler():
    """Stop the global campaign scheduler."""
    scheduler = get_campaign_scheduler()
    await scheduler.stop()
