"""Campaign repository for database operations."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.campaign import Campaign, CampaignStatus
from src.models.lead import Lead


class CampaignRepository:
    """Repository for Campaign database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(self, campaign: Campaign) -> Campaign:
        """
        Create a new campaign.

        Args:
            campaign: Campaign instance to create

        Returns:
            Created campaign with populated ID
        """
        self.session.add(campaign)
        await self.session.flush()
        await self.session.refresh(campaign)
        return campaign

    async def get_by_id(
        self,
        campaign_id: int,
        include_leads: bool = False
    ) -> Optional[Campaign]:
        """
        Get campaign by ID.

        Args:
            campaign_id: Campaign ID
            include_leads: Whether to load related leads

        Returns:
            Campaign if found, None otherwise
        """
        query = select(Campaign).where(Campaign.id == campaign_id)

        if include_leads:
            query = query.options(selectinload(Campaign.leads))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[CampaignStatus] = None,
        include_deleted: bool = False
    ) -> List[Campaign]:
        """
        Get all campaigns with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by campaign status
            include_deleted: Whether to include deleted campaigns

        Returns:
            List of campaigns
        """
        query = select(Campaign)

        # Apply filters
        filters = []
        if status:
            filters.append(Campaign.status == status)
        if not include_deleted:
            filters.append(Campaign.is_deleted == False)

        if filters:
            query = query.where(and_(*filters))

        # Apply pagination
        query = query.offset(skip).limit(limit).order_by(Campaign.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_campaigns(self) -> List[Campaign]:
        """
        Get all active campaigns that should be running.

        Returns:
            List of active campaigns
        """
        query = select(Campaign).where(
            and_(
                Campaign.is_active == True,
                Campaign.is_deleted == False,
                or_(
                    Campaign.status == CampaignStatus.RUNNING,
                    Campaign.status == CampaignStatus.SCHEDULED
                )
            )
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_scheduled_campaigns(self, current_time: datetime) -> List[Campaign]:
        """
        Get campaigns scheduled to start at or before the given time.

        Args:
            current_time: Time to check against

        Returns:
            List of scheduled campaigns ready to start
        """
        query = select(Campaign).where(
            and_(
                Campaign.status == CampaignStatus.SCHEDULED,
                Campaign.scheduled_start_time <= current_time,
                Campaign.is_active == True,
                Campaign.is_deleted == False
            )
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, campaign_id: int, **kwargs) -> Optional[Campaign]:
        """
        Update campaign fields.

        Args:
            campaign_id: Campaign ID
            **kwargs: Fields to update

        Returns:
            Updated campaign if found, None otherwise
        """
        # Add updated_at timestamp
        kwargs['updated_at'] = datetime.utcnow()

        query = (
            update(Campaign)
            .where(Campaign.id == campaign_id)
            .values(**kwargs)
            .returning(Campaign)
        )

        result = await self.session.execute(query)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def update_status(
        self,
        campaign_id: int,
        new_status: CampaignStatus
    ) -> Optional[Campaign]:
        """
        Update campaign status.

        Args:
            campaign_id: Campaign ID
            new_status: New status to set

        Returns:
            Updated campaign if found, None otherwise
        """
        update_data = {
            'status': new_status,
            'updated_at': datetime.utcnow()
        }

        # Set actual start/end times based on status
        if new_status == CampaignStatus.RUNNING:
            update_data['actual_start_time'] = datetime.utcnow()
        elif new_status in [CampaignStatus.COMPLETED, CampaignStatus.CANCELLED]:
            update_data['actual_end_time'] = datetime.utcnow()

        return await self.update(campaign_id, **update_data)

    async def update_metrics(
        self,
        campaign_id: int,
        leads_called: Optional[int] = None,
        leads_completed: Optional[int] = None,
        leads_qualified: Optional[int] = None,
        call_duration: Optional[int] = None
    ) -> Optional[Campaign]:
        """
        Update campaign performance metrics.

        Args:
            campaign_id: Campaign ID
            leads_called: Number of leads called (incremental)
            leads_completed: Number of leads completed (incremental)
            leads_qualified: Number of leads qualified (incremental)
            call_duration: Call duration in seconds (incremental)

        Returns:
            Updated campaign if found, None otherwise
        """
        campaign = await self.get_by_id(campaign_id)
        if not campaign:
            return None

        # Update metrics
        if leads_called is not None:
            campaign.leads_called += leads_called
        if leads_completed is not None:
            campaign.leads_completed += leads_completed
        if leads_qualified is not None:
            campaign.leads_qualified += leads_qualified
        if call_duration is not None:
            campaign.total_call_duration_seconds += call_duration

        # Recalculate derived metrics
        campaign.calculate_metrics()
        campaign.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(campaign)
        return campaign

    async def soft_delete(self, campaign_id: int) -> bool:
        """
        Soft delete a campaign.

        Args:
            campaign_id: Campaign ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.update(campaign_id, is_deleted=True, is_active=False)
        return result is not None

    async def hard_delete(self, campaign_id: int) -> bool:
        """
        Permanently delete a campaign.

        Args:
            campaign_id: Campaign ID

        Returns:
            True if deleted, False if not found
        """
        query = delete(Campaign).where(Campaign.id == campaign_id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0

    async def get_campaign_leads(
        self,
        campaign_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Lead]:
        """
        Get all leads for a campaign.

        Args:
            campaign_id: Campaign ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of leads
        """
        query = (
            select(Lead)
            .where(Lead.campaign_id == campaign_id)
            .offset(skip)
            .limit(limit)
            .order_by(Lead.created_at.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_pending_leads(
        self,
        campaign_id: int,
        max_attempts: int = 3
    ) -> List[Lead]:
        """
        Get leads that haven't been called or haven't reached max attempts.

        Args:
            campaign_id: Campaign ID
            max_attempts: Maximum call attempts per lead

        Returns:
            List of pending leads
        """
        query = (
            select(Lead)
            .where(
                and_(
                    Lead.campaign_id == campaign_id,
                    Lead.call_attempts < max_attempts
                )
            )
            .order_by(Lead.created_at.asc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_campaign_leads(self, campaign_id: int) -> int:
        """
        Count total leads in a campaign.

        Args:
            campaign_id: Campaign ID

        Returns:
            Number of leads
        """
        from sqlalchemy import func

        query = select(func.count(Lead.id)).where(Lead.campaign_id == campaign_id)
        result = await self.session.execute(query)
        return result.scalar_one()
