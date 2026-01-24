"""
Call Executor Service for executing scheduled calls via Exotel.
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from src.integrations.exotel_client import ExotelClient, ExotelCallStatus
from src.models.scheduled_call import ScheduledCall, ScheduledCallStatus
from src.models.call_session import CallSession, CallStatus as DBCallStatus
from src.models.lead import Lead
from src.services.call_scheduler import CallScheduler
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__, settings.ENVIRONMENT)


class CallExecutor:
    """
    Service for executing calls via Exotel
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.exotel_client = ExotelClient()
        self.scheduler = CallScheduler(db_session)

    async def execute_call(self, scheduled_call: ScheduledCall) -> Dict[str, Any]:
        """
        Execute a scheduled call

        Steps:
        1. Get lead details
        2. Build custom field data
        3. Call Exotel API
        4. Create CallSession record
        5. Update ScheduledCall status
        """

        # Get lead
        lead = scheduled_call.lead

        logger.info(
            "Executing call",
            extra={
                "scheduled_call_id": scheduled_call.id,
                "lead_id": lead.id,
                "lead_name": lead.name,
                "attempt": scheduled_call.attempt_number
            }
        )

        # Build custom field data (passed to WebSocket)
        custom_field = {
            "lead_id": lead.id,
            "lead_name": lead.name,
            "phone": lead.phone,
            "property_type": lead.property_type,
            "location": lead.location,
            "budget": lead.budget,
            "campaign_id": scheduled_call.campaign_id,
            "scheduled_call_id": scheduled_call.id
        }

        try:
            # Build status callback URL
            status_callback_url = f"{settings.OUR_BASE_URL}/webhooks/exotel/call-status"

            # Make call via Exotel
            call_result = await self.exotel_client.make_call(
                to_number=lead.phone,
                custom_field=custom_field,
                status_callback_url=status_callback_url,
                record=True
            )

            call_sid = call_result["call_sid"]

            # Create CallSession record
            call_session = CallSession(
                call_sid=call_sid,
                lead_id=lead.id,
                status=DBCallStatus.INITIATED
            )
            self.db.add(call_session)

            # Update ScheduledCall
            await self.scheduler.update_call_status(
                scheduled_call_id=scheduled_call.id,
                status=ScheduledCallStatus.CALLING,
                call_sid=call_sid,
                exotel_status=call_result["status"]
            )

            # Update Lead
            lead.call_attempts += 1
            lead.last_call_attempt = datetime.utcnow()

            await self.db.commit()

            logger.info(
                "Call initiated successfully",
                extra={
                    "call_sid": call_sid,
                    "lead_id": lead.id,
                    "scheduled_call_id": scheduled_call.id
                }
            )

            return {
                "success": True,
                "call_sid": call_sid,
                "scheduled_call_id": scheduled_call.id
            }

        except Exception as e:
            logger.error(
                "Failed to execute call",
                extra={
                    "scheduled_call_id": scheduled_call.id,
                    "lead_id": lead.id,
                    "error": str(e)
                }
            )

            # Get campaign to get retry delay
            campaign = scheduled_call.campaign
            retry_delay = campaign.retry_delay_hours if campaign else 2

            # Schedule retry
            await self.scheduler.schedule_retry(
                scheduled_call_id=scheduled_call.id,
                failure_reason=f"Exotel API error: {str(e)}",
                delay_hours=retry_delay
            )

            return {
                "success": False,
                "error": str(e),
                "scheduled_call_id": scheduled_call.id
            }

    async def close(self):
        """Close resources"""
        await self.exotel_client.close()
