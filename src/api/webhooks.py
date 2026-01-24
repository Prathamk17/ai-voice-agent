"""
Webhook handlers for receiving callbacks from external services.
"""

from fastapi import APIRouter, Request, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
from datetime import datetime

from src.database.connection import get_db_session
from src.models.call_session import CallSession, CallStatus as DBCallStatus, CallOutcome
from src.models.scheduled_call import ScheduledCall, ScheduledCallStatus
from src.integrations.exotel_client import ExotelCallStatus
from src.services.call_scheduler import CallScheduler
from src.utils.logger import get_logger
from src.config.settings import settings

router = APIRouter()
logger = get_logger(__name__, settings.ENVIRONMENT)


@router.post("/exotel/call-status")
async def exotel_call_status_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Receive call status updates from Exotel

    Exotel sends these statuses:
    - initiated: Call request sent
    - ringing: Phone is ringing
    - in-progress: Call answered, conversation active
    - completed: Call ended normally
    - busy: Line was busy
    - no-answer: Lead didn't pick up
    - failed: Technical failure

    Docs: https://developer.exotel.com/api/#status-callback
    """

    # Exotel sends data as form-encoded
    form_data = await request.form()
    data = dict(form_data)

    call_sid = data.get("CallSid")
    status = data.get("Status")
    duration = data.get("Duration")
    recording_url = data.get("RecordingUrl")
    custom_field = data.get("CustomField")

    logger.info(
        "Received Exotel webhook",
        extra={
            "call_sid": call_sid,
            "status": status,
            "duration": duration
        }
    )

    # Update CallSession
    result = await db.execute(
        select(CallSession).where(CallSession.call_sid == call_sid)
    )
    call_session = result.scalar_one_or_none()

    if not call_session:
        logger.warning("CallSession not found", extra={"call_sid": call_sid})
        return {"status": "received", "warning": "session_not_found"}

    # Update call status
    status_mapping = {
        ExotelCallStatus.INITIATED: DBCallStatus.INITIATED,
        ExotelCallStatus.RINGING: DBCallStatus.RINGING,
        ExotelCallStatus.IN_PROGRESS: DBCallStatus.IN_PROGRESS,
        ExotelCallStatus.COMPLETED: DBCallStatus.COMPLETED,
        ExotelCallStatus.FAILED: DBCallStatus.FAILED,
        ExotelCallStatus.BUSY: DBCallStatus.BUSY,
        ExotelCallStatus.NO_ANSWER: DBCallStatus.NO_ANSWER,
    }

    call_session.status = status_mapping.get(status, DBCallStatus.FAILED)

    if status == ExotelCallStatus.IN_PROGRESS:
        call_session.answered_at = datetime.utcnow()

    if status in [ExotelCallStatus.COMPLETED, ExotelCallStatus.FAILED,
                  ExotelCallStatus.BUSY, ExotelCallStatus.NO_ANSWER]:
        call_session.ended_at = datetime.utcnow()

        if duration:
            call_session.duration_seconds = int(duration)

        if recording_url:
            call_session.recording_url = recording_url

    await db.commit()

    # Update ScheduledCall and handle retries
    background_tasks.add_task(
        handle_call_completion,
        call_sid,
        status,
        custom_field
    )

    return {"status": "received", "call_sid": call_sid}


async def handle_call_completion(
    call_sid: str,
    exotel_status: str,
    custom_field: str
):
    """
    Handle call completion - update ScheduledCall and schedule retries

    This runs as a background task to avoid blocking the webhook response
    """
    # Import here to avoid circular imports
    from src.database.connection import get_async_session_maker

    async_session_maker = get_async_session_maker()

    async with async_session_maker() as db:
        # Get ScheduledCall
        result = await db.execute(
            select(ScheduledCall).where(ScheduledCall.current_call_sid == call_sid)
        )
        scheduled_call = result.scalar_one_or_none()

        if not scheduled_call:
            logger.warning("ScheduledCall not found", extra={"call_sid": call_sid})
            return

        scheduler = CallScheduler(db)

        # Handle different outcomes
        if exotel_status == ExotelCallStatus.COMPLETED:
            # Call completed successfully
            # Outcome will be determined by WebSocket handler (Module 4)
            scheduled_call.status = ScheduledCallStatus.COMPLETED
            await db.commit()

            logger.info("Call completed", extra={"call_sid": call_sid})

        elif exotel_status == ExotelCallStatus.NO_ANSWER:
            # Schedule retry
            await scheduler.schedule_retry(
                scheduled_call_id=scheduled_call.id,
                failure_reason="No answer",
                delay_hours=2
            )

            logger.info("Call no answer - retry scheduled", extra={"call_sid": call_sid})

        elif exotel_status == ExotelCallStatus.BUSY:
            # Schedule retry with longer delay
            await scheduler.schedule_retry(
                scheduled_call_id=scheduled_call.id,
                failure_reason="Line busy",
                delay_hours=4
            )

            logger.info("Call busy - retry scheduled", extra={"call_sid": call_sid})

        elif exotel_status == ExotelCallStatus.FAILED:
            # Schedule retry
            await scheduler.schedule_retry(
                scheduled_call_id=scheduled_call.id,
                failure_reason="Call failed",
                delay_hours=1
            )

            logger.error("Call failed - retry scheduled", extra={"call_sid": call_sid})
