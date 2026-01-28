"""
Exotel WebSocket event handlers.

Handles events: connected, start, media, stop, clear, dtmf
"""

from typing import Dict, Any
from datetime import datetime
import json
from sqlalchemy import select

from src.websocket.session_manager import SessionManager
from src.conversation.engine import ConversationEngine
from src.ai.stt_service import DeepgramSTTService
from src.ai.tts_service import ElevenLabsTTSService
from src.audio.processor import AudioProcessor
from src.models.conversation import ConversationStage
from src.models.call_session import CallSession
from src.database.connection import get_async_session_maker
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class ExotelEventHandler:
    """
    Handle events from Exotel WebSocket

    Events:
    - connected: WebSocket established
    - start: Media streaming started
    - media: Audio chunk received
    - stop: Call ended
    - clear: Reset conversation
    - dtmf: Keypress detected
    """

    def __init__(self):
        self.session_manager = SessionManager()
        self.conversation_engine = ConversationEngine()
        self.stt_service = DeepgramSTTService()
        self.tts_service = ElevenLabsTTSService()
        self.audio_processor = AudioProcessor()

    async def handle_connected(
        self,
        websocket,
        data: Dict[str, Any]
    ):
        """
        Handle 'connected' event

        - Acknowledge WebSocket connection
        - Note: Exotel sends no data in this event
        - Session will be created in 'start' event

        Args:
            websocket: WebSocket connection
            data: Event data (usually empty for Exotel)

        Returns:
            None
        """
        logger.info("WebSocket connected - waiting for start event with call details")
        return None

    async def handle_start(
        self,
        websocket,
        data: Dict[str, Any]
    ):
        """
        Handle 'start' event

        - Extract call details from Exotel's 'start' nested object
        - Create conversation session
        - Generate intro message
        - Convert to speech
        - Send to Exotel

        Args:
            websocket: WebSocket connection
            data: Event data containing call_sid and caller info

        Returns:
            ConversationSession
        """
        # Extract data from Exotel's nested 'start' object or top-level (for compatibility)
        start_data = data.get("start", {})
        call_sid = start_data.get("call_sid") or data.get("call_sid") or data.get("CallSid")
        caller_number = start_data.get("from") or data.get("from")
        virtual_number = start_data.get("to") or data.get("to")

        # Extract custom field if provided (for lead context)
        custom_field = data.get("customField") or data.get("CustomField", "{}")

        try:
            lead_context = json.loads(custom_field) if isinstance(custom_field, str) else custom_field
        except:
            lead_context = {}

        # Ensure lead_phone is set (required field)
        if not lead_context.get("phone"):
            lead_context["phone"] = caller_number or "+910000000000"

        # Ensure lead_id and lead_name are set
        if not lead_context.get("lead_id"):
            lead_context["lead_id"] = 0
        if not lead_context.get("lead_name"):
            lead_context["lead_name"] = "Customer"
        if not lead_context.get("source"):
            lead_context["source"] = "inbound"

        logger.info(
            "Media streaming started",
            call_sid=call_sid,
            caller=caller_number,
            virtual_number=virtual_number,
            lead_id=lead_context.get("lead_id"),
            lead_name=lead_context.get("lead_name")
        )

        # Check if session already exists (Exotel sometimes sends duplicate "start" events)
        existing_session = await self.session_manager.get_session(call_sid)
        if existing_session:
            logger.info(
                "Session already exists, skipping duplicate start event",
                call_sid=call_sid
            )
            return existing_session

        # Create session
        session = await self.session_manager.create_session(
            call_sid=call_sid,
            lead_context=lead_context
        )

        # ⚡ Start persistent WebSocket connection for STT (LOW LATENCY MODE)
        await self.stt_service.start_streaming(call_sid)

        # Generate intro
        intro_text = await self.conversation_engine.generate_intro(session)

        # Add to transcript
        await self.session_manager.add_to_transcript(
            call_sid=session.call_sid,
            speaker="ai",
            text=intro_text
        )

        # Convert to speech and send
        await self.send_tts_to_caller(websocket, intro_text, session)

        return session

    async def handle_media(
        self,
        websocket,
        session,
        media_data: Dict[str, Any]
    ):
        """
        Handle 'media' event

        - Decode audio
        - Buffer chunks
        - Transcribe when enough audio
        - Process through conversation engine
        - Generate and send response
        - Support voice interruption (barge-in)

        Args:
            websocket: WebSocket connection
            session: Conversation session
            media_data: Media event data
        """

        # Get audio payload
        audio_payload = media_data.get("payload")
        if not audio_payload:
            return

        # Decode audio
        try:
            audio_bytes = self.audio_processor.decode_exotel_audio(audio_payload)
        except Exception as e:
            logger.error("Failed to decode audio", call_sid=session.call_sid, error=str(e))
            return

        # Accumulate in buffer
        session.audio_buffer += audio_bytes

        # Detect voice activity even when bot is speaking (for interruption)
        if session.is_bot_speaking:
            # Check if user is trying to interrupt (using simple energy-based VAD)
            has_voice = await self._detect_voice_activity(audio_bytes)

            if has_voice:
                logger.info(
                    "🎤 USER INTERRUPTION DETECTED! Stopping bot speech",
                    call_sid=session.call_sid,
                    buffer_size=len(audio_bytes)
                )
                # Stop bot from speaking and save immediately to Redis
                session.is_bot_speaking = False
                session.should_stop_speaking = True
                await self.session_manager.save_session(session)
                # Clear buffer and continue to process user's interruption
                session.audio_buffer = b""
            else:
                # No voice detected during bot speech, ignore silence
                logger.debug(
                    "No voice detected during bot speech",
                    call_sid=session.call_sid,
                    buffer_size=len(audio_bytes)
                )
                return

        # Only process if waiting for user response or if interruption detected
        if not session.waiting_for_response and not session.should_stop_speaking:
            return

        # Detect if current chunk has voice activity
        has_voice_now = await self._detect_voice_activity(audio_bytes)

        # Track silence duration
        if not hasattr(session, 'silence_chunks'):
            session.silence_chunks = 0
            session.last_voice_time = 0

        if has_voice_now:
            session.silence_chunks = 0  # Reset silence counter
        else:
            session.silence_chunks += 1

        # Only transcribe when we have enough audio AND detect silence (speech ended)
        # Min 0.5s of audio + 400ms of silence (faster response, reduced from 600ms)
        min_audio_bytes = 8000  # 0.5 seconds
        silence_threshold = 7  # ~400ms of silence (7 chunks × ~60ms each)

        if len(session.audio_buffer) >= min_audio_bytes and session.silence_chunks >= silence_threshold:
            logger.info(
                f"🎙️ Speech ended (silence detected): {len(session.audio_buffer)} bytes ({len(session.audio_buffer)/16000:.2f}s), transcribing...",
                call_sid=session.call_sid
            )
            # Transcribe
            transcript = await self.stt_service.transcribe_audio(
                audio_bytes=session.audio_buffer,
                call_sid=session.call_sid
            )

            if not transcript:
                # 🚨 TRANSCRIPT EMPTY: Low confidence or failed transcription
                logger.warning(
                    "❌ EMPTY TRANSCRIPT: Asking user to repeat",
                    call_sid=session.call_sid,
                    buffer_size=len(session.audio_buffer)
                )

                # Ask user to repeat (don't add to transcript history)
                clarification_messages = [
                    "Sorry, I didn't catch that. Could you repeat?",
                    "Sorry, could you say that again?",
                    "Sorry, I missed that. Can you repeat?"
                ]
                import random
                clarification = random.choice(clarification_messages)

                await self.send_tts_to_caller(websocket, clarification, session)

                # Clear buffer and continue listening
                session.audio_buffer = b""
                session.silence_chunks = 0
                await self.session_manager.save_session(session)
                return

            # Valid transcript received
            logger.info(
                "User spoke",
                call_sid=session.call_sid,
                transcript=transcript
            )

            # Add to transcript
            await self.session_manager.add_to_transcript(
                call_sid=session.call_sid,
                speaker="user",
                text=transcript
            )

            # LATENCY MASKING: Play filler if LLM takes >300ms
            import asyncio
            import time

            llm_start_time = time.time()

            # Start filler audio task if LLM might take >300ms
            filler_task = asyncio.create_task(asyncio.sleep(0.3))  # 300ms delay

            # Process through conversation engine
            response_future = asyncio.create_task(
                self.conversation_engine.process_user_input(
                    session=session,
                    user_input=transcript
                )
            )

            # Wait for either filler timeout or LLM response
            done, pending = await asyncio.wait(
                [filler_task, response_future],
                return_when=asyncio.FIRST_COMPLETED
            )

            # If filler timeout happened first, play filler
            if filler_task in done and response_future in pending:
                logger.info("⏱️ LLM taking >300ms, playing filler", call_sid=session.call_sid)
                await self.play_filler_audio(websocket, session)

            # Wait for LLM response
            response_text, should_end, outcome = await response_future

            llm_duration = time.time() - llm_start_time
            logger.info(f"⚡ LLM response time: {llm_duration*1000:.0f}ms", call_sid=session.call_sid)

            # Update session
            await self.session_manager.save_session(session)

            # Add AI response to transcript
            await self.session_manager.add_to_transcript(
                call_sid=session.call_sid,
                speaker="ai",
                text=response_text
            )

            # Send response
            await self.send_tts_to_caller(websocket, response_text, session)

            # End call if needed
            if should_end:
                logger.info(
                    "Call ending",
                    call_sid=session.call_sid,
                    outcome=outcome
                )

                # Save outcome to session for later processing
                session.collected_data["final_outcome"] = outcome
                await self.session_manager.save_session(session)

                # Close WebSocket (triggers Exotel to end call)
                await websocket.close()

            # Clear buffer and reset interruption flag
            session.audio_buffer = b""
            session.should_stop_speaking = False
            session.silence_chunks = 0  # Reset silence tracking
            await self.session_manager.save_session(session)

    async def _detect_voice_activity(self, audio_bytes: bytes) -> bool:
        """
        Simple energy-based Voice Activity Detection

        Args:
            audio_bytes: Raw PCM audio bytes

        Returns:
            True if voice activity detected, False otherwise
        """
        if len(audio_bytes) < 320:  # Need at least 20ms of audio
            return False

        try:
            # Calculate RMS energy
            import struct
            samples = struct.unpack(f"{len(audio_bytes)//2}h", audio_bytes)
            rms = (sum(s**2 for s in samples) / len(samples)) ** 0.5

            # Threshold for voice detection (adjust based on testing)
            # 8kHz 16-bit audio typically has RMS > 500 for speech
            VOICE_THRESHOLD = 500

            is_voice = rms > VOICE_THRESHOLD

            # Log for debugging (only when voice detected to avoid spam)
            if is_voice:
                logger.info(f"Voice detected! RMS: {rms:.0f} (threshold: {VOICE_THRESHOLD})")

            return is_voice
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return False

    async def play_filler_audio(
        self,
        websocket,
        session
    ) -> bool:
        """
        Play cached filler audio ("Hmm", "Okay", "Right") for latency masking

        Returns:
            True if filler was played successfully
        """
        # Predefined filler audio files
        import random
        import os

        fillers = ["hmm.pcm", "okay.pcm", "right.pcm"]
        filler_file = random.choice(fillers)
        filler_path = f"assets/filler_audio/{filler_file}"

        try:
            # Load pre-recorded filler audio
            if not os.path.exists(filler_path):
                logger.warning(f"Filler audio not found: {filler_path}", call_sid=session.call_sid)
                return False

            with open(filler_path, "rb") as f:
                filler_pcm = f.read()

            # Chunk and send
            chunks = self.audio_processor.chunk_audio(filler_pcm, chunk_duration_ms=20)

            for chunk in chunks:
                # Check if interrupted
                fresh_session = await self.session_manager.get_session(session.call_sid)
                if fresh_session and fresh_session.should_stop_speaking:
                    break

                base64_chunk = self.audio_processor.encode_for_exotel(chunk)
                await websocket.send_json({
                    "event": "media",
                    "media": {"payload": base64_chunk}
                })

            logger.info(f"✨ Played filler audio: {filler_file}", call_sid=session.call_sid)
            return True

        except Exception as e:
            logger.error(f"Failed to play filler audio: {e}", call_sid=session.call_sid)
            return False

    async def persist_session_to_db(self, call_sid: str):
        """
        Persist conversation session from Redis to PostgreSQL.

        This saves the transcript and collected data permanently to the database
        when a call ends, preventing data loss after Redis TTL expires.

        Args:
            call_sid: Call SID to persist
        """
        try:
            # Get session from Redis
            session = await self.session_manager.get_session(call_sid)

            if not session:
                logger.warning(
                    "Cannot persist session - not found in Redis",
                    call_sid=call_sid
                )
                return

            # Get database session
            async_session_maker = get_async_session_maker()

            async with async_session_maker() as db:
                # Find CallSession in database
                result = await db.execute(
                    select(CallSession).where(CallSession.call_sid == call_sid)
                )
                call_session = result.scalar_one_or_none()

                if not call_session:
                    logger.warning(
                        "Cannot persist session - CallSession not found in database",
                        call_sid=call_sid
                    )
                    return

                # Persist transcript
                if session.transcript_history:
                    call_session.full_transcript = json.dumps(session.transcript_history)
                    logger.info(
                        "Persisting transcript to database",
                        call_sid=call_sid,
                        exchanges=len(session.transcript_history)
                    )

                # Persist collected data
                if session.collected_data:
                    call_session.collected_data = json.dumps(session.collected_data)
                    logger.info(
                        "Persisting collected data to database",
                        call_sid=call_sid,
                        fields=list(session.collected_data.keys())
                    )

                # Commit to database
                await db.commit()

                logger.info(
                    "Session successfully persisted to database",
                    call_sid=call_sid
                )

        except Exception as e:
            logger.error(
                "Failed to persist session to database",
                call_sid=call_sid,
                error=str(e)
            )
            import traceback
            logger.error(traceback.format_exc())

    async def handle_stop(
        self,
        websocket,
        session
    ):
        """
        Handle 'stop' event

        - Customer disconnected
        - Save final state to database
        - Cleanup session

        Args:
            websocket: WebSocket connection
            session: Conversation session
        """
        logger.info("Call stopped", call_sid=session.call_sid)

        # ⚡ Stop persistent WebSocket connection for STT
        await self.stt_service.stop_streaming(session.call_sid)

        # Mark that call ended
        await self.session_manager.update_session(
            call_sid=session.call_sid,
            updates={"waiting_for_response": False}
        )

        # Persist session data to PostgreSQL before Redis expires
        await self.persist_session_to_db(session.call_sid)

    async def handle_clear(
        self,
        websocket,
        session
    ):
        """
        Handle 'clear' event

        - Reset conversation context
        - Clear buffers
        - Restart from intro

        Args:
            websocket: WebSocket connection
            session: Conversation session
        """
        logger.info("Clearing conversation", call_sid=session.call_sid)

        # Reset session
        session.conversation_stage = ConversationStage.INTRO
        session.audio_buffer = b""
        session.collected_data = {}
        session.transcript_history = []

        await self.session_manager.save_session(session)

        # Send fresh intro
        await self.handle_start(websocket, session)

    async def handle_dtmf(
        self,
        websocket,
        session,
        digit: str
    ):
        """
        Handle 'dtmf' event

        - Keypress detected
        - Can be used for fallback options

        Args:
            websocket: WebSocket connection
            session: Conversation session
            digit: Pressed digit
        """
        logger.info("DTMF received", call_sid=session.call_sid, digit=digit)

        # Example: Press 0 to speak to human
        if digit == "0":
            response = "Let me connect you with our team. Please hold."
            await self.send_tts_to_caller(websocket, response, session)

            # Mark for escalation
            session.escalation_requested = True
            await self.session_manager.save_session(session)

            # Close to trigger escalation
            await websocket.close()

    async def send_tts_to_caller(
        self,
        websocket,
        text: str,
        session
    ):
        """
        Generate TTS and send to Exotel with interruption support

        Steps:
        1. Generate audio via ElevenLabs
        2. Chunk audio into smaller pieces
        3. Encode to base64
        4. Send via WebSocket (with interruption checks)

        Args:
            websocket: WebSocket connection
            text: Text to convert to speech
            session: Conversation session
        """

        # Mark bot as speaking
        session.is_bot_speaking = True
        session.waiting_for_response = False
        session.should_stop_speaking = False
        await self.session_manager.save_session(session)

        try:
            # Generate TTS
            pcm_audio = await self.tts_service.generate_speech(
                text=text,
                call_sid=session.call_sid
            )

            # Chunk audio for streaming (reduced to 20ms for smoother playback)
            chunks = self.audio_processor.chunk_audio(pcm_audio, chunk_duration_ms=20)

            # Send chunks with IMMEDIATE interruption support
            chunks_sent = 0
            for i, chunk in enumerate(chunks):
                # Check EVERY 3 chunks for immediate barge-in response (~60ms latency)
                # (every 1 chunk would be too aggressive with Redis overhead)
                if i % 3 == 0:
                    fresh_session = await self.session_manager.get_session(session.call_sid)
                    if fresh_session and fresh_session.should_stop_speaking:
                        logger.info(
                            "🛑 TTS interrupted by user (immediate barge-in)",
                            call_sid=session.call_sid,
                            chunks_sent=chunks_sent,
                            total_chunks=len(chunks)
                        )
                        break

                base64_chunk = self.audio_processor.encode_for_exotel(chunk)

                await websocket.send_json({
                    "event": "media",
                    "media": {
                        "payload": base64_chunk
                    }
                })
                chunks_sent += 1

            # Mark done and ready for user response
            session.is_bot_speaking = False
            session.waiting_for_response = True
            await self.session_manager.save_session(session)

            logger.info(
                "TTS sent to caller",
                call_sid=session.call_sid,
                text_length=len(text),
                chunks_sent=chunks_sent,
                total_chunks=len(chunks)
            )

        except Exception as e:
            logger.error(
                "Failed to send TTS",
                call_sid=session.call_sid,
                error=str(e)
            )
            # Mark ready for response anyway
            session.is_bot_speaking = False
            session.waiting_for_response = True
            await self.session_manager.save_session(session)
