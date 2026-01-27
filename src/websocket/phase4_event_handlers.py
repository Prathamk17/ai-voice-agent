"""
PHASE 4 EVENT HANDLERS - Full Voice AI with ElevenLabs TTS

This file provides event handlers for Phase 4 testing that:
- ✅ Uses Deepgram for speech-to-text transcription
- ✅ Uses OpenAI (GPT-4o-mini) for intelligent conversation
- ✅ Uses ElevenLabs for Text-to-Speech (natural voice responses)
- ✅ Logs all transcriptions and AI responses
- ✅ Sends natural voice audio instead of beeps

This completes the full AI voice agent experience!
"""

from typing import Dict, Any
import base64
import asyncio
import time

from src.websocket.phase3_event_handlers import Phase3EventHandler
from src.ai.tts_service import ElevenLabsTTSService
from src.audio.processor import AudioProcessor
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class Phase4EventHandler(Phase3EventHandler):
    """
    Phase 4 event handler - Full AI conversation with TTS

    Extends Phase 3 by replacing beeps with natural voice using ElevenLabs TTS.
    """

    def __init__(self):
        # Initialize parent (Phase 3) components
        super().__init__()

        # Add TTS service
        self.tts_service = ElevenLabsTTSService()

        # Track if we've sent the intro speech (not just the greeting tone)
        self.intro_speech_sent = {}  # {call_sid: bool}

        # OPTIMIZATION: VAD threshold tuned for Exotel phone audio
        # Baseline noise: RMS ~8 (should be ignored)
        # Actual speech: RMS 50-5000+ (should be detected)
        self.SPEECH_THRESHOLD = 30  # Set to 30 to filter baseline noise but capture speech
        self.SILENCE_CHUNKS_REQUIRED = 15  # Reduced from 20 for faster response (300ms silence)

    async def handle_start(
        self,
        websocket,
        data: Dict[str, Any]
    ):
        """
        Handle 'start' event - Create session and send AI greeting with voice

        Overrides Phase 3 to use actual TTS instead of beeps.
        """
        # Call parent to create session and setup
        session = await super().handle_start(websocket, data)

        call_sid = session.call_sid

        # Initialize intro speech tracking
        self.intro_speech_sent[call_sid] = False

        # DEBUG: Check if intro was sent by Phase 3
        logger.info(f"🔍 PHASE 4 DEBUG: intro_sent[{call_sid}] = {self.intro_sent.get(call_sid)}")

        # Generate and SPEAK the AI intro message (not just beep)
        if self.intro_sent.get(call_sid):
            logger.info("🔍 PHASE 4 DEBUG: Intro was sent, now fetching session...")

            # Re-fetch session to get the updated transcript with intro message
            session = await self.session_manager.get_session(call_sid)
            logger.info(f"🔍 PHASE 4 DEBUG: Re-fetched session = {session is not None}")

            if session:
                logger.info(f"🔍 PHASE 4 DEBUG: session.transcript_history exists = {hasattr(session, 'transcript_history')}")
                if hasattr(session, 'transcript_history'):
                    logger.info(f"🔍 PHASE 4 DEBUG: transcript length = {len(session.transcript_history) if session.transcript_history else 0}")
                    if session.transcript_history:
                        logger.info(f"🔍 PHASE 4 DEBUG: transcript entries = {session.transcript_history}")

            # Get the intro message from transcript
            intro_message = None
            if session and hasattr(session, 'transcript_history') and session.transcript_history:
                # Find the first agent message in transcript
                for entry in session.transcript_history:
                    if entry.get('speaker') == 'agent':
                        intro_message = entry.get('text')
                        logger.info(f"🔍 PHASE 4 DEBUG: Found intro message: '{intro_message[:50]}...'")
                        break

            if not intro_message:
                logger.warning("⚠️ PHASE 4 DEBUG: No intro message found in transcript!")

            if intro_message:
                try:
                    logger.info("=" * 80)
                    logger.info("🎙️ PHASE 4: SPEAKING AI INTRO WITH TTS")
                    logger.info(f"   Agent says: '{intro_message}'")
                    logger.info("=" * 80)

                    # Generate TTS and send to caller
                    await self.send_tts_to_caller(websocket, intro_message, session)

                    self.intro_speech_sent[call_sid] = True

                except Exception as e:
                    logger.error(f"❌ PHASE 4: Failed to speak intro: {e}")
                    # Fallback to greeting tone
                    await self.send_test_greeting(websocket, call_sid)

        return session

    async def generate_ai_response(self, websocket, session, user_input: str):
        """
        Generate AI response using OpenAI LLM and SPEAK IT with TTS

        Overrides Phase 3 to use actual voice instead of beeps.
        """
        try:
            # === LATENCY TRACKING START ===
            t_start = time.time()

            logger.info("=" * 80)
            logger.info("🤖 PHASE 4: Generating AI response with OpenAI...")
            logger.info(f"   User said: '{user_input}'")

            # Call the conversation engine to process input
            t_llm_start = time.time()
            response_text, should_end_call, call_outcome = await self.conversation_engine.process_user_input(
                session=session,
                user_input=user_input
            )
            t_llm_end = time.time()
            llm_latency_ms = (t_llm_end - t_llm_start) * 1000

            # Log the AI response
            logger.info("=" * 80)
            logger.info("🤖 PHASE 4: AI RESPONSE GENERATED!")
            logger.info(f"   💬 Agent says: '{response_text}'")
            logger.info(f"   📊 Should end call: {should_end_call}")
            logger.info(f"   🎯 Call outcome: {call_outcome or 'ongoing'}")
            logger.info(f"   ⏱️  LLM latency: {llm_latency_ms:.0f}ms ({llm_latency_ms/1000:.2f}s)")
            logger.info("=" * 80)

            # Add AI response to transcript
            await self.session_manager.add_to_transcript(
                call_sid=session.call_sid,
                speaker="agent",
                text=response_text
            )

            # Save updated session (with collected_data) back to Redis
            await self.session_manager.save_session(session)

            # PHASE 4: Send actual TTS instead of beep!
            logger.info("🎙️ PHASE 4: Converting response to speech with ElevenLabs TTS...")
            t_tts_start = time.time()
            await self.send_tts_to_caller(websocket, response_text, session)
            t_tts_end = time.time()
            tts_latency_ms = (t_tts_end - t_tts_start) * 1000

            # === LATENCY TRACKING END ===
            total_latency_ms = (t_tts_end - t_start) * 1000

            logger.info("=" * 80)
            logger.info("⏱️  LATENCY BREAKDOWN")
            logger.info(f"   LLM (OpenAI):       {llm_latency_ms:>6.0f}ms ({llm_latency_ms/total_latency_ms*100:>5.1f}%)")
            logger.info(f"   TTS (ElevenLabs):   {tts_latency_ms:>6.0f}ms ({tts_latency_ms/total_latency_ms*100:>5.1f}%)")
            logger.info(f"   TOTAL:              {total_latency_ms:>6.0f}ms ({total_latency_ms/1000:.2f}s)")
            logger.info("=" * 80)

            # If AI decided to end call, log it
            if should_end_call:
                logger.info("🔚 PHASE 4: AI decided to end call")
                logger.info(f"   Final outcome: {call_outcome}")
                # In production, this would trigger call termination
                # For testing, we just log it

        except Exception as e:
            logger.error(f"❌ PHASE 4: AI response generation or TTS failed: {e}")
            # Send error tone
            await self.send_acknowledgment_beep(websocket, session.call_sid)

    async def send_tts_to_caller(self, websocket, text: str, session):
        """
        Convert text to speech using ElevenLabs and send to caller

        This is the KEY new functionality in Phase 4!
        """
        try:
            call_sid = session.call_sid

            logger.info(f"🎙️ PHASE 4: Generating TTS for: '{text[:100]}...'")

            # Generate speech with ElevenLabs
            t_tts_gen_start = time.time()
            pcm_audio = await self.tts_service.generate_speech(
                text=text,
                call_sid=call_sid
            )
            t_tts_gen_end = time.time()
            tts_gen_latency_ms = (t_tts_gen_end - t_tts_gen_start) * 1000

            logger.info(f"✅ PHASE 4: TTS generated, audio size: {len(pcm_audio)} bytes")

            # Calculate duration for logging
            duration_ms = AudioProcessor.get_audio_duration_ms(pcm_audio)
            logger.info(f"   📊 Audio duration: {duration_ms}ms ({duration_ms/1000:.2f}s)")
            logger.info(f"   ⏱️  TTS generation: {tts_gen_latency_ms:.0f}ms ({tts_gen_latency_ms/1000:.2f}s)")

            # Send audio to caller via WebSocket
            t_stream_start = time.time()
            await self._stream_audio_to_caller(websocket, pcm_audio, call_sid)
            t_stream_end = time.time()
            stream_latency_ms = (t_stream_end - t_stream_start) * 1000

            logger.info(f"✅ PHASE 4: TTS audio sent to caller successfully")
            logger.info(f"   ⏱️  Audio streaming: {stream_latency_ms:.0f}ms ({stream_latency_ms/1000:.2f}s)")

        except Exception as e:
            logger.error(f"❌ PHASE 4: TTS generation/sending failed: {e}")
            # Fallback to beep on error
            logger.info("   ⚠️ Falling back to acknowledgment beep")
            await self.send_acknowledgment_beep(websocket, session.call_sid)
            raise

    async def _stream_audio_to_caller(self, websocket, pcm_audio: bytes, call_sid: str):
        """
        Stream PCM audio to the caller via Exotel WebSocket

        Chunks the audio into smaller pieces for smooth playback.
        """
        try:
            # Get the stream_sid for this call
            logger.info(f"🔍 PHASE 4 DEBUG: Looking up stream_sid for call_sid={call_sid}")
            logger.info(f"🔍 PHASE 4 DEBUG: Available stream_sids: {list(self.stream_sids.keys())}")

            stream_sid = self.stream_sids.get(call_sid)
            logger.info(f"🔍 PHASE 4 DEBUG: stream_sid = {stream_sid}")

            if not stream_sid:
                logger.error(f"❌ PHASE 4: No stream_sid found for call_sid {call_sid}")
                return

            # Split audio into 20ms chunks for smooth streaming
            chunks = AudioProcessor.chunk_audio(pcm_audio, chunk_duration_ms=20)

            logger.info(f"🔊 PHASE 4: Streaming {len(chunks)} audio chunks to caller...")

            # Send each chunk
            for i, chunk in enumerate(chunks):
                # Encode chunk to base64
                audio_base64 = AudioProcessor.encode_for_exotel(chunk)

                # Create WebSocket message
                message = {
                    "event": "media",
                    "streamSid": stream_sid,  # Use the actual stream_sid from Exotel
                    "media": {
                        "payload": audio_base64
                    }
                }

                # Send to WebSocket
                await websocket.send_json(message)

                # OPTIMIZATION: Reduced delay for faster audio streaming
                # 10ms delay = 2x faster streaming while still smooth
                await asyncio.sleep(0.01)  # 10ms (was 20ms)

            logger.info(f"✅ PHASE 4: All {len(chunks)} chunks sent successfully")

        except Exception as e:
            logger.error(f"❌ PHASE 4: Audio streaming failed: {e}")
            raise

    async def handle_stop(
        self,
        websocket,
        session
    ):
        """Handle 'stop' event - cleanup and show transcript"""
        # Call parent's stop handler
        await super().handle_stop(websocket, session)

        # Clean up Phase 4 specific state
        call_sid = session.call_sid
        if call_sid in self.intro_speech_sent:
            del self.intro_speech_sent[call_sid]
