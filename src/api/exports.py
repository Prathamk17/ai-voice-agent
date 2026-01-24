"""
Export API Endpoints

Module 5: Dashboard, Analytics & Monitoring
FastAPI routes for data exports (CSV and Excel).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from src.database.connection import get_db_session
from src.services.export_service import ExportService
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)
router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/campaigns/{campaign_id}/results")
async def export_campaign_results(
    campaign_id: int,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Export campaign results with all call outcomes

    Parameters:
    - campaign_id: ID of the campaign
    - format: Export format (csv or xlsx)

    Returns:
    - Downloadable file with campaign results including:
      - Lead information
      - Call attempts and outcomes
      - Duration and recording URLs
      - Collected data (purpose, timeline, etc.)
    """
    service = ExportService(db)

    try:
        data = await service.export_campaign_results(campaign_id, format)

        # Set appropriate headers
        if format == "csv":
            media_type = "text/csv"
            filename = f"campaign_{campaign_id}_results.csv"
        else:
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"campaign_{campaign_id}_results.xlsx"

        return StreamingResponse(
            io.BytesIO(data),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Export failed for campaign {campaign_id}", error=str(e))
        raise HTTPException(500, f"Export failed: {str(e)}")


@router.get("/campaigns/{campaign_id}/transcripts")
async def export_call_transcripts(
    campaign_id: int,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Export call transcripts for a campaign

    Parameters:
    - campaign_id: ID of the campaign
    - format: Export format (csv or xlsx)

    Returns:
    - Downloadable file with call transcripts including:
      - Call details (SID, lead name, phone, date)
      - Call duration
      - Outcome
      - Full conversation transcript
    """
    service = ExportService(db)

    try:
        data = await service.export_call_transcripts(campaign_id, format)

        if format == "csv":
            media_type = "text/csv"
            filename = f"campaign_{campaign_id}_transcripts.csv"
        else:
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"campaign_{campaign_id}_transcripts.xlsx"

        return StreamingResponse(
            io.BytesIO(data),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Transcript export failed for campaign {campaign_id}", error=str(e))
        raise HTTPException(500, f"Export failed: {str(e)}")


@router.get("/campaigns/{campaign_id}/leads")
async def export_lead_list(
    campaign_id: int,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Export lead list for a campaign

    Parameters:
    - campaign_id: ID of the campaign
    - format: Export format (csv or xlsx)

    Returns:
    - Downloadable file with lead list including:
      - Lead ID
      - Contact information
      - Property details
      - Call attempts
    """
    service = ExportService(db)

    try:
        data = await service.export_lead_list(campaign_id, format)

        if format == "csv":
            media_type = "text/csv"
            filename = f"campaign_{campaign_id}_leads.csv"
        else:
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"campaign_{campaign_id}_leads.xlsx"

        return StreamingResponse(
            io.BytesIO(data),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Lead export failed for campaign {campaign_id}", error=str(e))
        raise HTTPException(500, f"Export failed: {str(e)}")
