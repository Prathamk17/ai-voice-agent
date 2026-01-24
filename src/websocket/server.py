"""
WebSocket server for handling Exotel voice connections.

Receives WebSocket connections from Exotel and handles real-time
audio streaming for AI voice conversations.
"""

from typing import Dict, Any
import json

from fastapi import WebSocket, WebSocketDisconnect
from src.websocket.event_handlers import ExotelEventHandler
from src.websocket.test_event_handlers import TestExotelEventHandler  # Phase 1
from src.websocket.phase2_event_handlers import Phase2EventHandler  # Phase 2
from src.websocket.session_manager import SessionManager
from src.utils.logger import StructuredLogger
import os

logger = StructuredLogger(__name__)

# TEST MODE Configuration:
# - "phase1" or "true": Minimal test (no AI services)
# - "phase2": Deepgram STT only (no OpenAI, no ElevenLabs)
# - "false": Production mode (all services enabled)
TEST_MODE = os.getenv("EXOTEL_TEST_MODE", "true").lower()


class ExotelWebSocketServer:
    """
    WebSocket server for Exotel voice connections

    Handles:
    - WebSocket connection establishment
    - Event routing
    - Error handling
    - Connection cleanup
    """

    def __init__(self):
        # Select handler based on test mode
        if TEST_MODE in ("phase1", "true"):
            self.event_handler = TestExotelEventHandler()
            logger.info("🧪 WebSocket server initialized in PHASE 1 MODE (no AI services)")
        elif TEST_MODE == "phase2":
            self.event_handler = Phase2EventHandler()
            logger.info("🎤 WebSocket server initialized in PHASE 2 MODE (Deepgram STT only)")
        else:
            self.event_handler = ExotelEventHandler()
            logger.info("🚀 WebSocket server initialized in PRODUCTION MODE (all services)")

        self.session_manager = SessionManager()
        self.active_connections: Dict[str, WebSocket] = {}

    async def handle_connection(self, websocket: WebSocket):
        """
        Handle WebSocket connection from Exotel

        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()

        call_sid = None
        session = None

        try:
            logger.info("WebSocket connection established")

            # Main event loop
            async for message in websocket.iter_text():
                try:
                    # DEBUG: Log raw message from Exotel
                    logger.info(f"RAW WebSocket message received: {message[:500]}")  # Log first 500 chars

                    data = json.loads(message)
                    event_type = data.get("event")

                    logger.info(
                        "WebSocket event received",
                        event=event_type,
                        call_sid=call_sid,
                        data_keys=list(data.keys())[:10]  # Show available keys
                    )

                    # Route event to appropriate handler
                    if event_type == "connected":
                        # Exotel sends no data in connected event, just acknowledge
                        await self.event_handler.handle_connected(websocket, data)
                        # Note: session will be created in 'start' event

                    elif event_type == "start":
                        # Create session from start event data (which contains call_sid)
                        session = await self.event_handler.handle_start(websocket, data)
                        call_sid = session.call_sid
                        self.active_connections[call_sid] = websocket

                    elif event_type == "media":
                        if not session and call_sid:
                            session = await self.session_manager.get_session(call_sid)
                        if session:
                            await self.event_handler.handle_media(
                                websocket, session, data.get("media", {})
                            )

                    elif event_type == "stop":
                        if session:
                            await self.event_handler.handle_stop(websocket, session)
                        break  # Exit loop on stop

                    elif event_type == "clear":
                        if session:
                            await self.event_handler.handle_clear(websocket, session)

                    elif event_type == "dtmf":
                        if session:
                            digit = data.get("dtmf", {}).get("digit")
                            await self.event_handler.handle_dtmf(
                                websocket, session, digit
                            )

                    else:
                        logger.warning("Unknown event type", event=event_type)

                except json.JSONDecodeError as e:
                    logger.error("Failed to parse WebSocket message", error=str(e))
                except Exception as e:
                    logger.error(
                        "Error handling WebSocket event",
                        error=str(e),
                        call_sid=call_sid
                    )

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected", call_sid=call_sid)

        except Exception as e:
            logger.error("WebSocket error", error=str(e), call_sid=call_sid)

        finally:
            # Cleanup
            if call_sid:
                if call_sid in self.active_connections:
                    del self.active_connections[call_sid]

                # Update session if exists
                if session:
                    await self.session_manager.update_session(
                        call_sid=call_sid,
                        updates={"waiting_for_response": False}
                    )

                logger.info("WebSocket connection closed", call_sid=call_sid)

    async def send_message(self, call_sid: str, message: Dict[str, Any]):
        """
        Send message to specific WebSocket connection

        Args:
            call_sid: Call SID
            message: Message to send
        """
        if call_sid in self.active_connections:
            try:
                await self.active_connections[call_sid].send_json(message)
            except Exception as e:
                logger.error(
                    "Failed to send message",
                    call_sid=call_sid,
                    error=str(e)
                )

    async def disconnect(self, call_sid: str):
        """
        Disconnect a WebSocket connection

        Args:
            call_sid: Call SID
        """
        if call_sid in self.active_connections:
            try:
                await self.active_connections[call_sid].close()
                del self.active_connections[call_sid]
                logger.info("WebSocket disconnected", call_sid=call_sid)
            except Exception as e:
                logger.error(
                    "Failed to disconnect WebSocket",
                    call_sid=call_sid,
                    error=str(e)
                )

    def get_active_connections_count(self) -> int:
        """Get number of active WebSocket connections"""
        return len(self.active_connections)

    def is_connected(self, call_sid: str) -> bool:
        """
        Check if call is connected via WebSocket

        Args:
            call_sid: Call SID

        Returns:
            True if connected
        """
        return call_sid in self.active_connections


# Global WebSocket server instance
websocket_server = ExotelWebSocketServer()
