"""
Email Lead Campaign Service for managing the default auto-calling campaign.
All email leads are automatically associated with this campaign.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from src.models.campaign import Campaign, CampaignStatus
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__, settings.ENVIRONMENT)


class EmailLeadCampaignService:
    """
    Service for managing the default email leads campaign.

    This campaign is auto-created and always running.
    All leads from email notifications are associated with it.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_or_create_default_campaign(self) -> Campaign:
        """
        Get or create the default email leads campaign.

        The campaign is created with:
        - Name: "Email Leads - Auto" (from settings)
        - Status: RUNNING (always active)
        - Max attempts: From EMAIL_LEADS_MAX_RETRY_ATTEMPTS
        - Retry delay: From EMAIL_LEADS_RETRY_DELAY_HOURS

        Returns:
            Campaign: The default email leads campaign
        """
        campaign_name = settings.EMAIL_LEADS_DEFAULT_CAMPAIGN_NAME

        # Try to find existing campaign
        result = await self.db.execute(
            select(Campaign).where(
                Campaign.name == campaign_name,
                Campaign.is_deleted == False
            )
        )
        existing_campaign = result.scalar_one_or_none()

        if existing_campaign:
            # Ensure it's running
            if existing_campaign.status != CampaignStatus.RUNNING:
                logger.info(
                    "Reactivating email leads campaign",
                    campaign_id=existing_campaign.id,
                    previous_status=existing_campaign.status
                )
                existing_campaign.status = CampaignStatus.RUNNING
                existing_campaign.actual_start_time = datetime.utcnow()
                await self.db.commit()
                await self.db.refresh(existing_campaign)

            logger.debug(
                "Using existing email leads campaign",
                campaign_id=existing_campaign.id
            )
            return existing_campaign

        # Create new default campaign
        new_campaign = Campaign(
            name=campaign_name,
            description="Auto-generated campaign for email lead notifications. "
                       "Leads from MagicBricks, 99Acres, and other sources are automatically "
                       "added to this campaign and called.",
            status=CampaignStatus.RUNNING,
            actual_start_time=datetime.utcnow(),
            max_attempts_per_lead=settings.EMAIL_LEADS_MAX_RETRY_ATTEMPTS,
            retry_delay_hours=settings.EMAIL_LEADS_RETRY_DELAY_HOURS,
            calling_hours_start=settings.CALLING_HOURS_START,
            calling_hours_end=settings.CALLING_HOURS_END,
            max_concurrent_calls=settings.MAX_CONCURRENT_CALLS,
            script_template=None,  # Will use default conversation script
            qualification_criteria=None,
            is_active=True,
            total_leads=0,
            leads_called=0,
            leads_completed=0,
            leads_qualified=0
        )

        self.db.add(new_campaign)
        await self.db.commit()
        await self.db.refresh(new_campaign)

        logger.info(
            "Created default email leads campaign",
            campaign_id=new_campaign.id,
            campaign_name=new_campaign.name
        )

        return new_campaign

    async def increment_lead_count(self, campaign: Campaign) -> None:
        """
        Increment the total_leads count for the campaign.

        Args:
            campaign: Campaign to update
        """
        campaign.total_leads += 1
        await self.db.commit()

        logger.debug(
            "Incremented email campaign lead count",
            campaign_id=campaign.id,
            total_leads=campaign.total_leads
        )


async def get_email_leads_campaign(db_session: AsyncSession) -> Campaign:
    """
    Helper function to get or create the default email leads campaign.

    Args:
        db_session: Database session

    Returns:
        Campaign: The default email leads campaign
    """
    service = EmailLeadCampaignService(db_session)
    return await service.get_or_create_default_campaign()
