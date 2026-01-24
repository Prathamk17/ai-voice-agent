"""
Exotel API Client for making outbound calls.

Documentation: https://developer.exotel.com/api/
"""

import httpx
from typing import Optional, Dict, Any
from urllib.parse import urljoin
import json
from datetime import datetime

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__, settings.ENVIRONMENT)


class ExotelCallStatus:
    """Exotel call status constants"""
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no-answer"
    CANCELLED = "cancelled"


class ExotelClient:
    """
    Client for Exotel API

    Documentation: https://developer.exotel.com/api/
    """

    def __init__(
        self,
        account_sid: str = None,
        api_key: str = None,
        api_token: str = None,
        virtual_number: str = None
    ):
        self.account_sid = account_sid or settings.EXOTEL_ACCOUNT_SID
        self.api_key = api_key or settings.EXOTEL_API_KEY
        self.api_token = api_token or settings.EXOTEL_API_TOKEN
        self.virtual_number = virtual_number or settings.EXOTEL_VIRTUAL_NUMBER

        self.base_url = f"https://api.exotel.com/v1/Accounts/{self.account_sid}/"

        # Create async HTTP client with auth
        self.client = httpx.AsyncClient(
            auth=(self.api_key, self.api_token),
            timeout=30.0
        )

    async def make_call(
        self,
        to_number: str,
        custom_field: Dict[str, Any],
        caller_id: str = None,
        status_callback_url: str = None,
        record: bool = True
    ) -> Dict[str, Any]:
        """
        Initiate an outbound call via Exotel

        Args:
            to_number: Lead's phone number (E.164 format)
            custom_field: Lead context (lead_id, name, property info, etc.)
            caller_id: Caller ID to display (defaults to virtual_number)
            status_callback_url: URL for status callbacks
            record: Whether to record the call

        Returns:
            Response from Exotel with call_sid and status

        API Docs: https://developer.exotel.com/api/#create-call
        """

        endpoint = urljoin(self.base_url, "Calls/connect.json")

        # Build request payload
        payload = {
            "From": self.virtual_number,
            "To": to_number,
            "CallerId": caller_id or self.virtual_number,
            "CustomField": json.dumps(custom_field),
            "Record": str(record).lower(),  # "true" or "false"
        }

        # Add status callback if provided
        if status_callback_url:
            payload["StatusCallback"] = status_callback_url

        # Add Exophlo URL (configured in Exotel dashboard)
        # The Exophlo contains the Voicebot Applet that opens WebSocket
        if settings.EXOTEL_EXOPHLO_ID:
            payload["Url"] = f"http://my.exotel.com/exoml/start/{settings.EXOTEL_EXOPHLO_ID}"

        try:
            logger.info(
                "Initiating Exotel call",
                extra={
                    "to": to_number,
                    "custom_field": custom_field
                }
            )

            response = await self.client.post(
                endpoint,
                data=payload  # Exotel expects form data, not JSON
            )

            response.raise_for_status()
            result = response.json()

            # Extract call details
            call_data = result.get("Call", {})
            call_sid = call_data.get("Sid")
            status = call_data.get("Status")

            logger.info(
                "Exotel call initiated",
                extra={
                    "call_sid": call_sid,
                    "status": status,
                    "to": to_number
                }
            )

            return {
                "call_sid": call_sid,
                "status": status,
                "to": to_number,
                "from": self.virtual_number,
                "custom_field": custom_field,
                "raw_response": call_data
            }

        except httpx.HTTPStatusError as e:
            logger.error(
                "Exotel API error",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                    "to": to_number
                }
            )
            raise Exception(f"Exotel API error: {e.response.status_code} - {e.response.text}")

        except Exception as e:
            logger.error(
                "Failed to initiate call",
                extra={
                    "error": str(e),
                    "to": to_number
                }
            )
            raise

    async def get_call_details(self, call_sid: str) -> Dict[str, Any]:
        """
        Get details of a specific call

        API Docs: https://developer.exotel.com/api/#call-details
        """
        endpoint = urljoin(self.base_url, f"Calls/{call_sid}.json")

        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()

            return response.json().get("Call", {})

        except Exception as e:
            logger.error(
                "Failed to get call details",
                extra={
                    "call_sid": call_sid,
                    "error": str(e)
                }
            )
            raise

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
