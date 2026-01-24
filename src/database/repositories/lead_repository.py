"""Lead repository for database operations."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.lead import Lead, LeadSource


class LeadRepository:
    """Repository for Lead database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(self, lead: Lead) -> Lead:
        """
        Create a new lead.

        Args:
            lead: Lead instance to create

        Returns:
            Created lead with populated ID
        """
        self.session.add(lead)
        await self.session.flush()
        await self.session.refresh(lead)
        return lead

    async def create_bulk(self, leads: List[Lead]) -> List[Lead]:
        """
        Create multiple leads in bulk.

        Args:
            leads: List of Lead instances to create

        Returns:
            List of created leads
        """
        self.session.add_all(leads)
        await self.session.flush()
        for lead in leads:
            await self.session.refresh(lead)
        return leads

    async def get_by_id(
        self,
        lead_id: int,
        include_call_sessions: bool = False
    ) -> Optional[Lead]:
        """
        Get lead by ID.

        Args:
            lead_id: Lead ID
            include_call_sessions: Whether to load related call sessions

        Returns:
            Lead if found, None otherwise
        """
        query = select(Lead).where(Lead.id == lead_id)

        if include_call_sessions:
            query = query.options(selectinload(Lead.call_sessions))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[Lead]:
        """
        Get lead by phone number.

        Args:
            phone: Phone number

        Returns:
            Lead if found, None otherwise
        """
        query = select(Lead).where(Lead.phone == phone)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        campaign_id: Optional[int] = None,
        source: Optional[LeadSource] = None
    ) -> List[Lead]:
        """
        Get all leads with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            campaign_id: Filter by campaign ID
            source: Filter by lead source

        Returns:
            List of leads
        """
        query = select(Lead)

        # Apply filters
        filters = []
        if campaign_id is not None:
            filters.append(Lead.campaign_id == campaign_id)
        if source:
            filters.append(Lead.source == source)

        if filters:
            query = query.where(and_(*filters))

        # Apply pagination
        query = query.offset(skip).limit(limit).order_by(Lead.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, lead_id: int, **kwargs) -> Optional[Lead]:
        """
        Update lead fields.

        Args:
            lead_id: Lead ID
            **kwargs: Fields to update

        Returns:
            Updated lead if found, None otherwise
        """
        # Add updated_at timestamp
        kwargs['updated_at'] = datetime.utcnow()

        query = (
            update(Lead)
            .where(Lead.id == lead_id)
            .values(**kwargs)
            .returning(Lead)
        )

        result = await self.session.execute(query)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def increment_call_attempts(self, lead_id: int) -> Optional[Lead]:
        """
        Increment call attempts counter for a lead.

        Args:
            lead_id: Lead ID

        Returns:
            Updated lead if found, None otherwise
        """
        lead = await self.get_by_id(lead_id)
        if not lead:
            return None

        lead.call_attempts += 1
        lead.last_call_attempt = datetime.utcnow()
        lead.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(lead)
        return lead

    async def delete(self, lead_id: int) -> bool:
        """
        Delete a lead.

        Args:
            lead_id: Lead ID

        Returns:
            True if deleted, False if not found
        """
        query = delete(Lead).where(Lead.id == lead_id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0

    async def search(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Lead]:
        """
        Search leads by name, phone, or email.

        Args:
            search_term: Term to search for
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching leads
        """
        search_pattern = f"%{search_term}%"
        query = (
            select(Lead)
            .where(
                or_(
                    Lead.name.ilike(search_pattern),
                    Lead.phone.ilike(search_pattern),
                    Lead.email.ilike(search_pattern)
                )
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def check_duplicate(
        self,
        phone: str,
        campaign_id: Optional[int] = None
    ) -> bool:
        """
        Check if a lead with the given phone already exists.

        Args:
            phone: Phone number to check
            campaign_id: Optional campaign ID to check within

        Returns:
            True if duplicate exists, False otherwise
        """
        filters = [Lead.phone == phone]
        if campaign_id is not None:
            filters.append(Lead.campaign_id == campaign_id)

        query = select(Lead).where(and_(*filters))
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
