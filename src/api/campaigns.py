"""Campaign management API endpoints."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.database.connection import get_db_session
from src.database.repositories import CampaignRepository, LeadRepository
from src.models.campaign import Campaign, CampaignStatus
from src.services.csv_service import CSVService
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/campaigns", tags=["campaigns"])


# Pydantic schemas for request/response
class CampaignCreate(BaseModel):
    """Schema for creating a new campaign."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    max_attempts_per_lead: int = Field(default=3, ge=1, le=10)
    retry_delay_hours: int = Field(default=24, ge=1, le=168)
    calling_hours_start: int = Field(default=10, ge=0, le=23)
    calling_hours_end: int = Field(default=19, ge=0, le=23)
    max_concurrent_calls: int = Field(default=5, ge=1, le=50)
    script_template: Optional[str] = None
    qualification_criteria: Optional[str] = None


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[CampaignStatus] = None
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    max_attempts_per_lead: Optional[int] = Field(None, ge=1, le=10)
    retry_delay_hours: Optional[int] = Field(None, ge=1, le=168)
    calling_hours_start: Optional[int] = Field(None, ge=0, le=23)
    calling_hours_end: Optional[int] = Field(None, ge=0, le=23)
    max_concurrent_calls: Optional[int] = Field(None, ge=1, le=50)
    script_template: Optional[str] = None
    qualification_criteria: Optional[str] = None
    is_active: Optional[bool] = None


class CampaignResponse(BaseModel):
    """Schema for campaign response."""
    id: int
    name: str
    description: Optional[str]
    status: CampaignStatus
    scheduled_start_time: Optional[datetime]
    scheduled_end_time: Optional[datetime]
    actual_start_time: Optional[datetime]
    actual_end_time: Optional[datetime]
    max_attempts_per_lead: int
    retry_delay_hours: int
    calling_hours_start: int
    calling_hours_end: int
    max_concurrent_calls: int
    total_leads: int
    leads_called: int
    leads_completed: int
    leads_qualified: int
    success_rate: Optional[float]
    qualification_rate: Optional[float]
    average_call_duration: Optional[float]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CSVUploadResponse(BaseModel):
    """Schema for CSV upload response."""
    campaign_id: int
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    leads_imported: int
    errors: List[dict]


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new campaign."""
    try:
        campaign_repo = CampaignRepository(db)

        # Create campaign instance
        campaign = Campaign(
            name=campaign_data.name,
            description=campaign_data.description,
            status=CampaignStatus.DRAFT,
            scheduled_start_time=campaign_data.scheduled_start_time,
            scheduled_end_time=campaign_data.scheduled_end_time,
            max_attempts_per_lead=campaign_data.max_attempts_per_lead,
            retry_delay_hours=campaign_data.retry_delay_hours,
            calling_hours_start=campaign_data.calling_hours_start,
            calling_hours_end=campaign_data.calling_hours_end,
            max_concurrent_calls=campaign_data.max_concurrent_calls,
            script_template=campaign_data.script_template,
            qualification_criteria=campaign_data.qualification_criteria
        )

        # Save to database
        created_campaign = await campaign_repo.create(campaign)
        await db.commit()

        logger.info(
            f"Campaign created successfully",
            campaign_id=created_campaign.id,
            campaign_name=created_campaign.name
        )

        return created_campaign

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create campaign: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create campaign: {str(e)}"
        )


@router.get("/", response_model=List[CampaignResponse])
async def list_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[CampaignStatus] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List all campaigns with optional filtering."""
    try:
        campaign_repo = CampaignRepository(db)
        campaigns = await campaign_repo.get_all(
            skip=skip,
            limit=limit,
            status=status_filter,
            include_deleted=False
        )

        return campaigns

    except Exception as e:
        logger.error(f"Failed to list campaigns: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list campaigns: {str(e)}"
        )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """Get campaign by ID."""
    try:
        campaign_repo = CampaignRepository(db)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found"
            )

        return campaign

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get campaign: {str(e)}", campaign_id=campaign_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get campaign: {str(e)}"
        )


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    campaign_data: CampaignUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update campaign details."""
    try:
        campaign_repo = CampaignRepository(db)

        # Check if campaign exists
        existing_campaign = await campaign_repo.get_by_id(campaign_id)
        if not existing_campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found"
            )

        # Prepare update data (exclude None values)
        update_data = campaign_data.model_dump(exclude_unset=True)

        if not update_data:
            return existing_campaign

        # Update campaign
        updated_campaign = await campaign_repo.update(campaign_id, **update_data)
        await db.commit()

        logger.info(
            f"Campaign updated successfully",
            campaign_id=campaign_id,
            updated_fields=list(update_data.keys())
        )

        return updated_campaign

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update campaign: {str(e)}", campaign_id=campaign_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update campaign: {str(e)}"
        )


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a campaign."""
    try:
        campaign_repo = CampaignRepository(db)

        # Check if campaign exists
        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found"
            )

        # Soft delete
        await campaign_repo.soft_delete(campaign_id)
        await db.commit()

        logger.info(f"Campaign deleted successfully", campaign_id=campaign_id)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete campaign: {str(e)}", campaign_id=campaign_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete campaign: {str(e)}"
        )


@router.post(
    "/{campaign_id}/upload-csv",
    response_model=CSVUploadResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_leads_csv(
    campaign_id: int,
    file: UploadFile = File(..., description="CSV file with lead data"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Upload CSV file with leads for a campaign.

    Expected CSV format:
    - name (required): Lead name
    - phone (required): Phone number (10 digits or with country code)
    - email (optional): Email address
    - property_type (required): Type of property (e.g., 2BHK, 3BHK)
    - location (required): Location preference
    - budget (optional): Budget in INR
    - source (optional): Lead source (website/referral/advertisement/partner)
    - tags (optional): Comma-separated tags
    """
    try:
        # Verify campaign exists
        campaign_repo = CampaignRepository(db)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found"
            )

        # Check file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only CSV files are allowed"
            )

        # Read file content
        file_content = await file.read()

        # Parse CSV
        csv_service = CSVService()
        parse_result = await csv_service.parse_csv_file(
            file_content,
            campaign_id,
            check_duplicates=True
        )

        # Convert valid rows to Lead models
        if parse_result.valid_rows > 0:
            lead_models = await csv_service.convert_to_lead_models(
                parse_result.leads,
                campaign_id
            )

            # Save leads to database
            lead_repo = LeadRepository(db)
            created_leads = await lead_repo.create_bulk(lead_models)

            # Update campaign total_leads count
            await campaign_repo.update(
                campaign_id,
                total_leads=campaign.total_leads + len(created_leads)
            )

            await db.commit()

            logger.info(
                f"Leads imported successfully",
                campaign_id=campaign_id,
                leads_imported=len(created_leads),
                total_rows=parse_result.total_rows,
                invalid_rows=parse_result.invalid_rows
            )

            return CSVUploadResponse(
                campaign_id=campaign_id,
                total_rows=parse_result.total_rows,
                valid_rows=parse_result.valid_rows,
                invalid_rows=parse_result.invalid_rows,
                duplicate_rows=parse_result.duplicate_rows,
                leads_imported=len(created_leads),
                errors=parse_result.errors
            )
        else:
            logger.warning(
                f"No valid leads found in CSV",
                campaign_id=campaign_id,
                total_rows=parse_result.total_rows
            )

            return CSVUploadResponse(
                campaign_id=campaign_id,
                total_rows=parse_result.total_rows,
                valid_rows=0,
                invalid_rows=parse_result.invalid_rows,
                duplicate_rows=parse_result.duplicate_rows,
                leads_imported=0,
                errors=parse_result.errors
            )

    except HTTPException:
        raise
    except ValueError as e:
        await db.rollback()
        logger.error(f"CSV validation failed: {str(e)}", campaign_id=campaign_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to upload CSV: {str(e)}", campaign_id=campaign_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload CSV: {str(e)}"
        )


@router.get("/{campaign_id}/leads")
async def get_campaign_leads(
    campaign_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all leads for a campaign."""
    try:
        campaign_repo = CampaignRepository(db)

        # Verify campaign exists
        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found"
            )

        # Get leads
        leads = await campaign_repo.get_campaign_leads(
            campaign_id,
            skip=skip,
            limit=limit
        )

        return {
            "campaign_id": campaign_id,
            "total_leads": campaign.total_leads,
            "leads": leads
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get campaign leads: {str(e)}",
            campaign_id=campaign_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get campaign leads: {str(e)}"
        )


@router.get("/templates/csv-sample")
async def get_csv_template():
    """Get a sample CSV template for lead import."""
    try:
        csv_service = CSVService()
        sample_csv = await csv_service.generate_sample_csv()

        from fastapi.responses import Response

        return Response(
            content=sample_csv,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=leads_template.csv"
            }
        )

    except Exception as e:
        logger.error(f"Failed to generate CSV template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate CSV template: {str(e)}"
        )


@router.post("/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """Start a campaign manually."""
    try:
        campaign_repo = CampaignRepository(db)

        # Get campaign
        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found"
            )

        # Validate campaign can be started
        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED, CampaignStatus.PAUSED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start campaign with status: {campaign.status}"
            )

        if campaign.total_leads == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot start campaign without leads. Please upload a CSV first."
            )

        # Update status to running
        updated_campaign = await campaign_repo.update_status(
            campaign_id,
            CampaignStatus.RUNNING
        )

        # Set actual start time
        updated_campaign.actual_start_time = datetime.utcnow()

        await db.commit()

        # Schedule calls for all leads in the campaign
        from src.services.call_scheduler import CallScheduler
        scheduler = CallScheduler(db)
        calls_scheduled = await scheduler.schedule_campaign_calls(campaign_id)

        logger.info(
            f"Campaign started successfully",
            campaign_id=campaign_id,
            calls_scheduled=calls_scheduled
        )

        return updated_campaign

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to start campaign: {str(e)}", campaign_id=campaign_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start campaign: {str(e)}"
        )


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """Pause a running campaign."""
    try:
        campaign_repo = CampaignRepository(db)

        # Get campaign
        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found"
            )

        if campaign.status != CampaignStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause campaign with status: {campaign.status}"
            )

        # Update status to paused
        updated_campaign = await campaign_repo.update_status(
            campaign_id,
            CampaignStatus.PAUSED
        )
        await db.commit()

        logger.info(f"Campaign paused successfully", campaign_id=campaign_id)

        return updated_campaign

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to pause campaign: {str(e)}", campaign_id=campaign_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause campaign: {str(e)}"
        )
