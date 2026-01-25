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

        # Generate and SPEAK the AI intro message (not just beep)
        if self.intro_sent.get(call_sid):
            # Get the intro message from transcript
            intro_message = None
            if hasattr(session, 'transcript') and session.transcript:
                # Find the first agent message in transcript
                for entry in session.transcript:
                    if entry.get('speaker') == 'agent':
                        intro_message = entry.get('text')
                        break

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
            logger.info("🤖 PHASE 4: Generating AI response with OpenAI...")

            # Call the conversation engine to process input
            response_text, should_end_call, call_outcome = await self.conversation_engine.process_user_input(
                session=session,
                user_input=user_input
            )

            # Log the AI response
            logger.info("=" * 80)
            logger.info("🤖 PHASE 4: AI RESPONSE GENERATED!")
            logger.info(f"   💬 Agent says: '{response_text}'")
            logger.info(f"   📊 Should end call: {should_end_call}")
            logger.info(f"   🎯 Call outcome: {call_outcome or 'ongoing'}")
            logger.info("=" * 80)

            # Add AI response to transcript
            await self.session_manager.add_to_transcript(
                call_sid=session.call_sid,
                speaker="agent",
                text=response_text
            )

            # PHASE 4: Send actual TTS instead of beep!
            logger.info("🎙️ PHASE 4: Converting response to speech with ElevenLabs TTS...")
            await self.send_tts_to_caller(websocket, response_text, session)

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
            pcm_audio = await self.tts_service.generate_speech(
                text=text,
                call_sid=call_sid
            )

            logger.info(f"✅ PHASE 4: TTS generated, audio size: {len(pcm_audio)} bytes")

            # Calculate duration for logging
            duration_ms = AudioProcessor.get_audio_duration_ms(pcm_audio)
            logger.info(f"   📊 Audio duration: {duration_ms}ms ({duration_ms/1000:.2f}s)")

            # Send audio to caller via WebSocket
            await self._stream_audio_to_caller(websocket, pcm_audio, call_sid)

            logger.info("✅ PHASE 4: TTS audio sent to caller successfully")

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
                    "streamSid": call_sid,
                    "media": {
                        "payload": audio_base64
                    }
                }

                # Send to WebSocket
                await websocket.send_json(message)

                # Small delay between chunks for natural pacing (20ms per chunk)
                # This matches the chunk duration for real-time playback
                await asyncio.sleep(0.02)  # 20ms

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
