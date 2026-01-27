"""
PHASE 3 EVENT HANDLERS - OpenAI LLM Integration

This file provides event handlers for Phase 3 testing that:
- ✅ Uses Deepgram for speech-to-text transcription
- ✅ Uses OpenAI (GPT-4o-mini) for intelligent conversation
- ✅ Generates contextual responses based on real estate sales
- ✅ Logs all transcriptions and AI responses
- ✅ Sends simple test audio responses (beeps for acknowledgment)
- ❌ NO ElevenLabs (TTS) - will be added in Phase 4

Use this to test the full conversation flow with AI.
"""

from typing import Dict, Any
import json
import base64
from sqlalchemy import select

from src.websocket.session_manager import SessionManager
from src.ai.stt_service import DeepgramSTTService
from src.audio.processor import AudioProcessor
from src.conversation.engine import ConversationEngine
from src.models.call_session import CallSession
from src.database.connection import get_async_session_maker
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class Phase3EventHandler:
    """
    Phase 3 event handler - Full AI conversation with OpenAI LLM

    Tests the complete flow: STT → LLM → Response (with beep acknowledgment)
    """

    def __init__(self):
        self.session_manager = SessionManager()
        self.stt_service = DeepgramSTTService()
        self.audio_processor = AudioProcessor()
        self.conversation_engine = ConversationEngine()  # NEW: AI conversation

        # Track audio buffers per call_sid (can't store on session due to Redis serialization)
        self.audio_buffers = {}  # {call_sid: bytearray()}
        self.chunk_counters = {}  # {call_sid: int}

        # Voice Activity Detection (VAD) state
        self.is_speech_active = {}  # {call_sid: bool}
        self.silence_chunk_count = {}  # {call_sid: int}

        # VAD thresholds
        # Baseline noise: RMS ~8 (should be ignored)
        # Actual speech: RMS 50-5000+ (should be detected)
        self.SPEECH_THRESHOLD = 30  # Set to 30 to filter baseline noise but capture speech
        self.SILENCE_CHUNKS_REQUIRED = 20  # 20 chunks (~400ms) of silence to end speech

        # Track if intro has been sent
        self.intro_sent = {}  # {call_sid: bool}

        # Track stream_sid for each call (needed for sending audio back to Exotel)
        self.stream_sids = {}  # {call_sid: stream_sid}

    async def handle_connected(
        self,
        websocket,
        data: Dict[str, Any]
    ):
        """Handle 'connected' event - just log it"""
        logger.info("✅ PHASE 3: WebSocket CONNECTED event received")
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
        - Creates a conversation session
        - Sends AI-generated greeting
        """
        # Extract call details
        start_data = data.get("start", {})
        call_sid = start_data.get("call_sid") or data.get("call_sid") or data.get("CallSid")
        stream_sid = start_data.get("stream_sid") or data.get("stream_sid") or data.get("streamSid")
        caller_number = start_data.get("from") or data.get("from")
        virtual_number = start_data.get("to") or data.get("to")

        logger.info("✅ PHASE 3: Media streaming STARTED")
        logger.info(f"   Call SID: {call_sid}")
        logger.info(f"   Stream SID: {stream_sid}")
        logger.info(f"   From: {caller_number}")
        logger.info(f"   To: {virtual_number}")

        # Create realistic lead context for real estate conversation
        lead_context = {
            "phone": caller_number or "+910000000000",
            "lead_id": 1,
            "lead_name": "Test Customer",
            "property_type": "2BHK apartment",
            "location": "Whitefield, Bangalore",
            "budget": None,  # Set to None to avoid validation error (can be numeric like 8000000.0 if needed)
            "source": "phase3_test"
        }

        # Create session
        try:
            logger.info(f"🔧 DEBUG: About to create session for call_sid={call_sid}")
            session = await self.session_manager.create_session(
                call_sid=call_sid,
                lead_context=lead_context
            )
            logger.info(f"   Session created: {session.call_sid}")
        except Exception as e:
            logger.error(f"❌ CRITICAL: Session creation failed with error: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            logger.error(f"❌ Call SID: {call_sid}")
            logger.error(f"❌ Lead context: {lead_context}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            raise
        logger.info("   📢 Ready to have an AI conversation!")
        logger.info("   💬 Try saying: 'Hello, who is this?'")

        # Initialize audio buffer for this call
        self.audio_buffers[call_sid] = bytearray()
        self.chunk_counters[call_sid] = 0
        self.is_speech_active[call_sid] = False
        self.silence_chunk_count[call_sid] = 0
        self.intro_sent[call_sid] = False
        self.stream_sids[call_sid] = stream_sid  # Store stream_sid for sending audio back

        # Send initial greeting tone
        await self.send_test_greeting(websocket, call_sid)

        # Generate and log the AI intro message (but don't speak it yet - using beeps)
        try:
            intro_message = await self.conversation_engine.generate_intro(session)

            logger.info("=" * 80)
            logger.info("🤖 PHASE 3: AI INTRO MESSAGE GENERATED")
            logger.info(f"   Agent would say: '{intro_message}'")
            logger.info("   (Using beep for now - TTS will be added in Phase 4)")
            logger.info("=" * 80)

            # Add intro to transcript
            await self.session_manager.add_to_transcript(
                call_sid=call_sid,
                speaker="agent",
                text=intro_message
            )

            self.intro_sent[call_sid] = True

        except Exception as e:
            logger.error(f"❌ PHASE 3: Failed to generate intro: {e}")

        return session

    async def handle_media(
        self,
        websocket,
        session,
        media_data: Dict[str, Any]
    ):
        """
        Handle 'media' event

        - Accumulates audio in buffer
        - Detects silence
        - Transcribes with Deepgram
        - NEW: Generates AI response with OpenAI
        - Logs the AI response
        - Sends acknowledgment beep
        """
        payload = media_data.get("payload", "")

        if not payload:
            return

        try:
            # Decode base64 audio
            audio_bytes = base64.b64decode(payload)

            # Get or initialize buffers for this call
            call_sid = session.call_sid
            if call_sid not in self.audio_buffers:
                self.audio_buffers[call_sid] = bytearray()
                self.chunk_counters[call_sid] = 0
                self.is_speech_active[call_sid] = False
                self.silence_chunk_count[call_sid] = 0

            # Calculate RMS (root mean square) for Voice Activity Detection
            import struct
            samples = struct.unpack(f"<{len(audio_bytes)//2}h", audio_bytes)
            rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
            max_amplitude = max(abs(s) for s in samples)

            # Increment chunk counter
            self.chunk_counters[call_sid] += 1
            chunk_count = self.chunk_counters[call_sid]

            # DIAGNOSTIC: Log audio analysis every 50 chunks
            if chunk_count % 50 == 0:
                logger.info(f"🔍 AUDIO ANALYSIS: RMS={rms:.2f}, Max={max_amplitude}, Bytes={len(audio_bytes)}, "
                           f"Speech Active={self.is_speech_active[call_sid]}, "
                           f"Silence Count={self.silence_chunk_count[call_sid]}")

            # Voice Activity Detection (VAD) Logic
            is_speech_chunk = rms > self.SPEECH_THRESHOLD

            if is_speech_chunk:
                # Speech detected!
                if not self.is_speech_active[call_sid]:
                    logger.info(f"🎤 PHASE 3: SPEECH STARTED (RMS={rms:.2f})")
                    self.is_speech_active[call_sid] = True

                # Reset silence counter and add to buffer
                self.silence_chunk_count[call_sid] = 0
                self.audio_buffers[call_sid].extend(audio_bytes)

            else:
                # Silence or low audio
                if self.is_speech_active[call_sid]:
                    # We were speaking, now it's quiet - increment silence counter
                    self.silence_chunk_count[call_sid] += 1
                    self.audio_buffers[call_sid].extend(audio_bytes)  # Keep trailing silence

                    # Check if silence period is long enough to end speech
                    if self.silence_chunk_count[call_sid] >= self.SILENCE_CHUNKS_REQUIRED:
                        logger.info(f"🔇 PHASE 3: SPEECH ENDED (silence for {self.silence_chunk_count[call_sid]} chunks)")

                        # Transcribe the buffered audio
                        if len(self.audio_buffers[call_sid]) > 3200:  # At least 0.2 seconds (reduced to capture short responses)
                            audio_to_transcribe = bytes(self.audio_buffers[call_sid])

                            logger.info(f"🎤 PHASE 3: Transcribing {len(audio_to_transcribe)} bytes...")

                            try:
                                # Step 1: Transcribe with Deepgram
                                transcription = await self.stt_service.transcribe_audio(audio_to_transcribe, call_sid)

                                if transcription and transcription.strip():
                                    logger.info("=" * 80)
                                    logger.info(f"✅ PHASE 3: TRANSCRIPTION SUCCESSFUL!")
                                    logger.info(f"   📝 Customer said: '{transcription}'")
                                    logger.info(f"   🔊 Audio size: {len(audio_to_transcribe)} bytes")
                                    logger.info("=" * 80)

                                    # Add to transcript
                                    await self.session_manager.add_to_transcript(
                                        call_sid=session.call_sid,
                                        speaker="customer",
                                        text=transcription
                                    )

                                    # Step 2: NEW - Generate AI response with OpenAI
                                    await self.generate_ai_response(websocket, session, transcription)

                                else:
                                    logger.info(f"⚠️ PHASE 3: Transcription returned empty")

                            except Exception as e:
                                logger.error(f"❌ PHASE 3: Processing failed: {e}")

                        else:
                            logger.info(f"⚠️ PHASE 3: Audio too short ({len(self.audio_buffers[call_sid])} bytes), skipping")

                        # Reset for next speech segment
                        self.audio_buffers[call_sid] = bytearray()
                        self.is_speech_active[call_sid] = False
                        self.silence_chunk_count[call_sid] = 0

        except Exception as e:
            logger.error(f"❌ PHASE 3: Error processing media: {e}")

    async def generate_ai_response(self, websocket, session, user_input: str):
        """
        Generate AI response using OpenAI LLM

        This is the NEW Phase 3 functionality that adds intelligence!
        """
        try:
            logger.info("🤖 PHASE 3: Generating AI response with OpenAI...")

            # Session is already a ConversationSession object from session_manager.create_session()
            # Just use it directly - no need to recreate it

            # Call the conversation engine to process input
            response_text, should_end_call, call_outcome = await self.conversation_engine.process_user_input(
                session=session,
                user_input=user_input
            )

            # Log the AI response
            logger.info("=" * 80)
            logger.info("🤖 PHASE 3: AI RESPONSE GENERATED!")
            logger.info(f"   💬 Agent says: '{response_text}'")
            logger.info(f"   📊 Should end call: {should_end_call}")
            logger.info(f"   🎯 Call outcome: {call_outcome or 'ongoing'}")
            logger.info("   (Using beep for now - TTS will be added in Phase 4)")
            logger.info("=" * 80)

            # Add AI response to transcript
            await self.session_manager.add_to_transcript(
                call_sid=session.call_sid,
                speaker="agent",
                text=response_text
            )

            # Save updated session (with collected_data) back to Redis
            await self.session_manager.save_session(session)

            # Send acknowledgment beep (Phase 4 will replace this with actual TTS)
            await self.send_acknowledgment_beep(websocket, session.call_sid)

            # If AI decided to end call, log it
            if should_end_call:
                logger.info("🔚 PHASE 3: AI decided to end call")
                logger.info(f"   Final outcome: {call_outcome}")
                # In production, this would trigger call termination
                # For testing, we just log it

        except Exception as e:
            logger.error(f"❌ PHASE 3: AI response generation failed: {e}")
            # Send error beep
            await self.send_acknowledgment_beep(websocket, session.call_sid)

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
        """Handle 'stop' event - log and show final transcript with AI conversation"""
        logger.info("✅ PHASE 3: Call STOPPED")
        logger.info(f"   Call SID: {session.call_sid}")

        call_sid = session.call_sid

        # Get final transcript (using correct attribute name)
        transcript = session.transcript_history if hasattr(session, 'transcript_history') else []

        if transcript:
            logger.info("=" * 80)
            logger.info("📋 PHASE 3: FINAL CONVERSATION TRANSCRIPT")
            logger.info("   (This shows the full AI conversation that took place)")
            logger.info("-" * 80)
            for entry in transcript:
                speaker = entry.get('speaker', 'unknown')
                text = entry.get('text', '')
                timestamp = entry.get('timestamp', '')

                # Format nicely for readability
                if speaker == 'agent':
                    logger.info(f"   🤖 AGENT: {text}")
                elif speaker == 'customer':
                    logger.info(f"   👤 CUSTOMER: {text}")
                else:
                    logger.info(f"   [{speaker.upper()}] {text}")
            logger.info("=" * 80)
        else:
            logger.info("   ℹ️ No conversation captured during this call")

        # Log total chunks received
        if call_sid in self.chunk_counters:
            logger.info(f"   Total audio chunks received: {self.chunk_counters[call_sid]}")

            # Cleanup buffers and VAD state
            if call_sid in self.audio_buffers:
                del self.audio_buffers[call_sid]
            if call_sid in self.chunk_counters:
                del self.chunk_counters[call_sid]
            if call_sid in self.is_speech_active:
                del self.is_speech_active[call_sid]
            if call_sid in self.silence_chunk_count:
                del self.silence_chunk_count[call_sid]
            if call_sid in self.intro_sent:
                del self.intro_sent[call_sid]

        # Persist session data to PostgreSQL
        await self.persist_session_to_db(call_sid)

    async def handle_clear(
        self,
        websocket,
        session
    ):
        """Handle 'clear' event - log it"""
        logger.info("✅ PHASE 3: CLEAR event received")
        logger.info(f"   Call SID: {session.call_sid}")

    async def handle_dtmf(
        self,
        websocket,
        session,
        digit: str
    ):
        """Handle 'dtmf' event - log keypress"""
        logger.info("✅ PHASE 3: DTMF key pressed")
        logger.info(f"   Call SID: {session.call_sid}")
        logger.info(f"   Digit: {digit}")

    async def send_test_greeting(self, websocket, call_sid: str):
        """
        Send a simple greeting tone (440Hz for 0.5 seconds)

        This lets the caller know the call is ready.
        """
        try:
            import math
            sample_rate = 8000
            duration = 0.5  # 0.5 second
            frequency = 440  # A4 note

            samples = []
            for i in range(int(sample_rate * duration)):
                t = i / sample_rate
                sample = math.sin(2 * math.pi * frequency * t)
                pcm_value = int(sample * 32767)
                samples.append(pcm_value.to_bytes(2, byteorder='little', signed=True))

            audio_bytes = b''.join(samples)
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

            # Get the stream_sid for this call
            stream_sid = self.stream_sids.get(call_sid)
            if not stream_sid:
                logger.error(f"❌ PHASE 3: No stream_sid found for call_sid {call_sid}")
                return

            message = {
                "event": "media",
                "streamSid": call_sid,  # Use call_sid to match working test handler
                "media": {
                    "payload": audio_base64
                }
            }

            await websocket.send_json(message)
            logger.info("✅ PHASE 3: Sent greeting tone (440Hz, 0.5s)")

        except Exception as e:
            logger.error(f"❌ PHASE 3: Failed to send greeting: {e}")

    async def send_acknowledgment_beep(self, websocket, call_sid: str):
        """
        Send a short beep to acknowledge we heard the user

        880Hz (A5) for 0.2 seconds - a quick "got it!" beep

        In Phase 4, this will be replaced with actual TTS speech.
        """
        try:
            import math
            sample_rate = 8000
            duration = 0.2  # 0.2 second - short beep
            frequency = 880  # A5 note (higher pitch)

            samples = []
            for i in range(int(sample_rate * duration)):
                t = i / sample_rate
                sample = math.sin(2 * math.pi * frequency * t)
                pcm_value = int(sample * 32767)
                samples.append(pcm_value.to_bytes(2, byteorder='little', signed=True))

            audio_bytes = b''.join(samples)
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

            # Get the stream_sid for this call
            stream_sid = self.stream_sids.get(call_sid)
            if not stream_sid:
                logger.error(f"❌ PHASE 3: No stream_sid found for call_sid {call_sid}")
                return

            message = {
                "event": "media",
                "streamSid": call_sid,  # Use call_sid to match working test handler
                "media": {
                    "payload": audio_base64
                }
            }

            await websocket.send_json(message)
            logger.info("✅ PHASE 3: Sent acknowledgment beep (880Hz, 0.2s)")

        except Exception as e:
            logger.error(f"❌ PHASE 3: Failed to send acknowledgment: {e}")

    async def send_tts_to_caller(self, websocket, text: str, session):
        """
        Placeholder method for Phase 4 (TTS integration)

        In Phase 4, this will call ElevenLabs TTS service.
        In Phase 3, we just log.
        """
        logger.info(f"✅ PHASE 3: Would send TTS: '{text}' (skipped - TTS coming in Phase 4)")
