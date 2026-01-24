"""
MINIMAL TEST EVENT HANDLERS - FOR EXOTEL WEBSOCKET TESTING ONLY

This file provides minimal event handlers that:
- ✅ Log all incoming WebSocket events from Exotel
- ✅ Send back a simple test audio response
- ❌ NO Deepgram (STT)
- ❌ NO OpenAI (LLM)
- ❌ NO ElevenLabs (TTS)

Use this for testing basic Exotel WebSocket connectivity.
"""

from typing import Dict, Any
import json
import base64

from src.websocket.session_manager import SessionManager
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class TestExotelEventHandler:
    """
    Minimal test event handler for Exotel WebSocket

    Only logs events and sends simple test responses.
    Does NOT call any AI services.
    """

    def __init__(self):
        self.session_manager = SessionManager()

    async def handle_connected(
        self,
        websocket,
        data: Dict[str, Any]
    ):
        """Handle 'connected' event - just log it"""
        logger.info("✅ TEST: WebSocket CONNECTED event received")
        logger.info(f"   Data: {json.dumps(data, indent=2)}")
        return None

    async def handle_start(
        self,
        websocket,
        data: Dict[str, Any]
    ):
        """
        Handle 'start' event

        - Logs call details
        - Creates a basic session
        - Sends a simple test audio message (440Hz tone for 1 second)
        """
        # Extract call details
        start_data = data.get("start", {})
        call_sid = start_data.get("call_sid") or data.get("call_sid") or data.get("CallSid")
        caller_number = start_data.get("from") or data.get("from")
        virtual_number = start_data.get("to") or data.get("to")

        logger.info("✅ TEST: Media streaming STARTED")
        logger.info(f"   Call SID: {call_sid}")
        logger.info(f"   From: {caller_number}")
        logger.info(f"   To: {virtual_number}")
        logger.info(f"   Full data: {json.dumps(data, indent=2)}")

        # Create minimal lead context
        lead_context = {
            "phone": caller_number or "+910000000000",
            "lead_id": 0,
            "lead_name": "Test Customer",
            "source": "test"
        }

        # Create session (just for tracking)
        session = await self.session_manager.create_session(
            call_sid=call_sid,
            lead_context=lead_context
        )

        logger.info(f"   Session created: {session.call_sid}")

        # Send a simple test audio message
        # This is a simple 440Hz sine wave tone (1 second at 8kHz sample rate)
        await self.send_test_audio(websocket, call_sid)

        return session

    async def handle_media(
        self,
        websocket,
        session,
        media_data: Dict[str, Any]
    ):
        """
        Handle 'media' event

        - Just logs incoming audio chunks
        - Does NOT transcribe or process audio
        """
        payload = media_data.get("payload", "")
        chunk_id = media_data.get("chunk", "unknown")

        # Log every 10th chunk to avoid spam
        if not hasattr(self, 'media_count'):
            self.media_count = {}

        if session.call_sid not in self.media_count:
            self.media_count[session.call_sid] = 0

        self.media_count[session.call_sid] += 1
        count = self.media_count[session.call_sid]

        if count % 10 == 1:  # Log 1st, 11th, 21st, etc.
            logger.info(
                f"✅ TEST: MEDIA event #{count} received",
                call_sid=session.call_sid,
                chunk=chunk_id,
                payload_size=len(payload) if payload else 0
            )
            logger.info(f"   Audio chunk (base64): {payload[:100]}..." if payload else "   (empty payload)")

    async def handle_stop(
        self,
        websocket,
        session
    ):
        """Handle 'stop' event - log and cleanup"""
        logger.info("✅ TEST: Call STOPPED")
        logger.info(f"   Call SID: {session.call_sid}")

        if hasattr(self, 'media_count') and session.call_sid in self.media_count:
            total = self.media_count[session.call_sid]
            logger.info(f"   Total media chunks received: {total}")
            del self.media_count[session.call_sid]

    async def handle_clear(
        self,
        websocket,
        session
    ):
        """Handle 'clear' event - log it"""
        logger.info("✅ TEST: CLEAR event received")
        logger.info(f"   Call SID: {session.call_sid}")

    async def handle_dtmf(
        self,
        websocket,
        session,
        digit: str
    ):
        """Handle 'dtmf' event - log keypress"""
        logger.info("✅ TEST: DTMF key pressed")
        logger.info(f"   Call SID: {session.call_sid}")
        logger.info(f"   Digit: {digit}")

    async def send_test_audio(self, websocket, call_sid: str):
        """
        Send a simple test audio message to Exotel

        Sends a 440Hz sine wave tone (1 second)
        Audio format: 16-bit PCM, 8kHz, mono, base64-encoded (as per Exotel specs)
        """
        try:
            # Generate a simple 440Hz sine wave tone (1 second at 8kHz)
            import math
            sample_rate = 8000
            duration = 1.0  # 1 second
            frequency = 440  # A4 note

            samples = []
            for i in range(int(sample_rate * duration)):
                # Generate sine wave
                t = i / sample_rate
                sample = math.sin(2 * math.pi * frequency * t)
                # Convert to 16-bit PCM (signed short: -32768 to 32767)
                pcm_value = int(sample * 32767)
                # Convert to bytes (little-endian)
                samples.append(pcm_value.to_bytes(2, byteorder='little', signed=True))

            # Concatenate all samples
            audio_bytes = b''.join(samples)

            # Encode to base64
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

            # Send to Exotel
            message = {
                "event": "media",
                "streamSid": call_sid,
                "media": {
                    "payload": audio_base64
                }
            }

            await websocket.send_json(message)

            logger.info("✅ TEST: Sent test audio (440Hz tone, 1 second)")
            logger.info(f"   Call SID: {call_sid}")
            logger.info(f"   Audio size: {len(audio_bytes)} bytes")

        except Exception as e:
            logger.error(f"❌ TEST: Failed to send test audio: {e}")

    async def send_tts_to_caller(self, websocket, text: str, session):
        """
        Placeholder method (not used in test mode)

        In production, this would call TTS service and send audio.
        In test mode, we just log.
        """
        logger.info(f"✅ TEST: Would send TTS: '{text}' (skipped in test mode)")
