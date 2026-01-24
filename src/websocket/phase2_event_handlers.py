"""
PHASE 2 TEST EVENT HANDLERS - Deepgram STT Testing

This file provides event handlers for Phase 2 testing that:
- ✅ Uses Deepgram for speech-to-text transcription
- ✅ Logs all transcriptions
- ✅ Sends simple test audio responses (no AI-generated speech)
- ❌ NO OpenAI (LLM conversation)
- ❌ NO ElevenLabs (TTS)

Use this to test that Deepgram can transcribe your voice correctly.
"""

from typing import Dict, Any
import json
import base64

from src.websocket.session_manager import SessionManager
from src.ai.stt_service import DeepgramSTTService
from src.audio.processor import AudioProcessor
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class Phase2EventHandler:
    """
    Phase 2 event handler - Deepgram STT testing

    Tests speech-to-text without AI conversation or TTS.
    """

    def __init__(self):
        self.session_manager = SessionManager()
        self.stt_service = DeepgramSTTService()
        self.audio_processor = AudioProcessor()

        # Track audio buffers per call_sid (can't store on session due to Redis serialization)
        self.audio_buffers = {}  # {call_sid: bytearray()}
        self.chunk_counters = {}  # {call_sid: int}

    async def handle_connected(
        self,
        websocket,
        data: Dict[str, Any]
    ):
        """Handle 'connected' event - just log it"""
        logger.info("✅ PHASE 2: WebSocket CONNECTED event received")
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
        - Sends a simple greeting message (test audio)
        """
        # Extract call details
        start_data = data.get("start", {})
        call_sid = start_data.get("call_sid") or data.get("call_sid") or data.get("CallSid")
        caller_number = start_data.get("from") or data.get("from")
        virtual_number = start_data.get("to") or data.get("to")

        logger.info("✅ PHASE 2: Media streaming STARTED")
        logger.info(f"   Call SID: {call_sid}")
        logger.info(f"   From: {caller_number}")
        logger.info(f"   To: {virtual_number}")

        # Create minimal lead context
        lead_context = {
            "phone": caller_number or "+910000000000",
            "lead_id": 0,
            "lead_name": "Test Customer",
            "source": "phase2_test"
        }

        # Create session
        session = await self.session_manager.create_session(
            call_sid=call_sid,
            lead_context=lead_context
        )

        logger.info(f"   Session created: {session.call_sid}")
        logger.info("   📢 Ready to transcribe your speech!")
        logger.info("   💬 Try saying: 'Hello, can you hear me?'")

        # Initialize audio buffer for this call
        self.audio_buffers[call_sid] = bytearray()
        self.chunk_counters[call_sid] = 0

        # Send a simple test greeting tone
        await self.send_test_greeting(websocket, call_sid)

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
        - Logs the transcription (does NOT generate AI response)
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

            # DIAGNOSTIC: Analyze audio content (every 50 chunks)
            if self.chunk_counters[call_sid] % 50 == 0:
                # Calculate RMS (root mean square) to detect if audio has content
                import struct
                samples = struct.unpack(f"<{len(audio_bytes)//2}h", audio_bytes)
                rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
                max_amplitude = max(abs(s) for s in samples)

                logger.info(f"🔍 AUDIO ANALYSIS: RMS={rms:.2f}, Max={max_amplitude}, Bytes={len(audio_bytes)}, "
                           f"First 20 bytes: {audio_bytes[:20].hex()}")

            # Add to audio buffer
            self.audio_buffers[call_sid].extend(audio_bytes)
            self.chunk_counters[call_sid] += 1

            chunk_count = self.chunk_counters[call_sid]

            # Log progress every 50 chunks (about 1 second)
            if chunk_count % 50 == 1:
                buffer_size_kb = len(self.audio_buffers[call_sid]) / 1024
                logger.info(
                    f"📊 PHASE 2: Collecting audio... {chunk_count} chunks ({buffer_size_kb:.1f} KB)"
                )

            # Simple silence detection: check if we have enough audio
            # In a real implementation, we'd analyze the audio amplitude
            # For now, we'll transcribe every ~2 seconds of audio (100 chunks)
            if chunk_count % 100 == 0 and len(self.audio_buffers[call_sid]) > 0:
                logger.info(f"🎤 PHASE 2: Attempting transcription after {chunk_count} chunks...")

                # Get audio from buffer
                audio_to_transcribe = bytes(self.audio_buffers[call_sid])

                # Clear buffer for next segment
                self.audio_buffers[call_sid] = bytearray()

                # Transcribe with Deepgram
                try:
                    transcription = await self.stt_service.transcribe_audio(audio_to_transcribe, call_sid)

                    if transcription and transcription.strip():
                        logger.info("=" * 80)
                        logger.info(f"✅ PHASE 2: TRANSCRIPTION SUCCESSFUL!")
                        logger.info(f"   📝 You said: '{transcription}'")
                        logger.info(f"   🔊 Audio size: {len(audio_to_transcribe)} bytes")
                        logger.info(f"   📞 Call SID: {session.call_sid}")
                        logger.info("=" * 80)

                        # Add to transcript
                        await self.session_manager.add_to_transcript(
                            call_sid=session.call_sid,
                            speaker="customer",
                            text=transcription
                        )

                        # Send acknowledgment beep
                        await self.send_acknowledgment_beep(websocket, session.call_sid)

                    else:
                        logger.info(f"⚠️ PHASE 2: Transcription returned empty (silence or unclear speech)")

                except Exception as e:
                    logger.error(f"❌ PHASE 2: Deepgram transcription failed: {e}")

        except Exception as e:
            logger.error(f"❌ PHASE 2: Error processing media: {e}")

    async def handle_stop(
        self,
        websocket,
        session
    ):
        """Handle 'stop' event - log and show final transcript"""
        logger.info("✅ PHASE 2: Call STOPPED")
        logger.info(f"   Call SID: {session.call_sid}")

        call_sid = session.call_sid

        # Get final transcript
        transcript = session.transcript if hasattr(session, 'transcript') else []

        if transcript:
            logger.info("=" * 80)
            logger.info("📋 PHASE 2: FINAL TRANSCRIPT")
            for entry in transcript:
                speaker = entry.get('speaker', 'unknown')
                text = entry.get('text', '')
                timestamp = entry.get('timestamp', '')
                logger.info(f"   [{speaker.upper()}] {text}")
            logger.info("=" * 80)
        else:
            logger.info("   ℹ️ No transcriptions captured during this call")

        # Log total chunks received
        if call_sid in self.chunk_counters:
            logger.info(f"   Total audio chunks received: {self.chunk_counters[call_sid]}")

            # Cleanup buffers
            del self.audio_buffers[call_sid]
            del self.chunk_counters[call_sid]

    async def handle_clear(
        self,
        websocket,
        session
    ):
        """Handle 'clear' event - log it"""
        logger.info("✅ PHASE 2: CLEAR event received")
        logger.info(f"   Call SID: {session.call_sid}")

    async def handle_dtmf(
        self,
        websocket,
        session,
        digit: str
    ):
        """Handle 'dtmf' event - log keypress"""
        logger.info("✅ PHASE 2: DTMF key pressed")
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

            message = {
                "event": "media",
                "streamSid": call_sid,
                "media": {
                    "payload": audio_base64
                }
            }

            await websocket.send_json(message)
            logger.info("✅ PHASE 2: Sent greeting tone (440Hz, 0.5s)")

        except Exception as e:
            logger.error(f"❌ PHASE 2: Failed to send greeting: {e}")

    async def send_acknowledgment_beep(self, websocket, call_sid: str):
        """
        Send a short beep to acknowledge we heard the user

        880Hz (A5) for 0.2 seconds - a quick "got it!" beep
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

            message = {
                "event": "media",
                "streamSid": call_sid,
                "media": {
                    "payload": audio_base64
                }
            }

            await websocket.send_json(message)
            logger.info("✅ PHASE 2: Sent acknowledgment beep (880Hz, 0.2s)")

        except Exception as e:
            logger.error(f"❌ PHASE 2: Failed to send acknowledgment: {e}")

    async def send_tts_to_caller(self, websocket, text: str, session):
        """
        Placeholder method (not used in Phase 2)

        In production, this would call TTS service.
        In Phase 2, we just log.
        """
        logger.info(f"✅ PHASE 2: Would send TTS: '{text}' (skipped - no TTS in Phase 2)")
