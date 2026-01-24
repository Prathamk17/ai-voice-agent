"""
ElevenLabs Text-to-Speech service.

Handles conversion of text to natural-sounding speech.
"""

from typing import Optional
import asyncio
import time

try:
    # Try ElevenLabs SDK v2.x (newer)
    from elevenlabs.client import ElevenLabs
    ELEVENLABS_AVAILABLE = True
    ELEVENLABS_VERSION = 2
except ImportError:
    try:
        # Fallback to ElevenLabs SDK v0.2.x (older)
        from elevenlabs import generate, set_api_key, Voice, VoiceSettings
        ELEVENLABS_AVAILABLE = True
        ELEVENLABS_VERSION = 1
    except ImportError:
        ELEVENLABS_AVAILABLE = False
        ELEVENLABS_VERSION = 0

from src.config.settings import settings
from src.audio.converter import AudioConverter
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)

# Import metrics (optional)
try:
    from src.monitoring.metrics import metrics
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False
    logger.debug("Metrics not available")


class ElevenLabsTTSService:
    """
    Text-to-Speech using ElevenLabs

    Features:
    - Custom voice cloning
    - Natural prosody
    - Low latency
    """

    def __init__(self):
        if not ELEVENLABS_AVAILABLE:
            logger.warning("ElevenLabs SDK not available - TTS will be disabled")
            self.enabled = False
            self.client = None
        elif not settings.ELEVENLABS_API_KEY:
            logger.warning("ELEVENLABS_API_KEY not configured - TTS will be disabled")
            self.enabled = False
            self.client = None
        else:
            self.voice_id = settings.ELEVENLABS_VOICE_ID or "21m00Tcm4TlvDq8ikWAM"  # Default voice

            if ELEVENLABS_VERSION == 2:
                # ElevenLabs SDK v2.x
                self.client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
                self.enabled = True
            else:
                # ElevenLabs SDK v0.2.x
                set_api_key(settings.ELEVENLABS_API_KEY)
                self.client = None  # v1 uses global functions
                self.enabled = True

        self.converter = AudioConverter()

    async def generate_speech(
        self,
        text: str,
        call_sid: str
    ) -> bytes:
        """
        Generate speech audio from text

        Args:
            text: Text to convert to speech
            call_sid: Call session ID

        Returns:
            PCM audio bytes in Exotel format (8kHz, 16-bit, mono)

        Raises:
            Exception: If TTS generation fails
        """
        if not self.enabled:
            raise Exception("ElevenLabs TTS not configured")

        try:
            logger.info(
                "Generating speech (LOW LATENCY MODE)",
                call_sid=call_sid,
                text_length=len(text),
                text_preview=text[:50]
            )

            # Generate audio using ElevenLabs with optimized low-latency settings
            start_time = time.time()

            if ELEVENLABS_VERSION == 2:
                # ElevenLabs SDK v2.x with OPTIMIZED LOW-LATENCY settings
                from elevenlabs import VoiceSettings
                audio_bytes = await asyncio.to_thread(
                    lambda: b''.join(self.client.text_to_speech.convert(
                        voice_id=self.voice_id,
                        text=text,
                        model_id="eleven_turbo_v2_5",  # FASTEST model for low latency (changed from eleven_multilingual_v2)
                        voice_settings=VoiceSettings(
                            stability=0.40,  # 35-40 for natural variation (reduced from 0.55)
                            similarity_boost=0.75,  # Keep at 75 for voice matching
                            style=0.15,  # 10-20 for slight expressiveness (reduced from 0.2)
                            use_speaker_boost=True
                        ),
                        optimize_streaming_latency=4  # MAX latency optimization (increased from 2)
                        # Note: Using default MP3 format, will convert to PCM 8kHz
                    ))
                )
            else:
                # ElevenLabs SDK v0.2.x with optimized settings
                audio_bytes = await asyncio.to_thread(
                    generate,
                    text=text,
                    voice=Voice(
                        voice_id=self.voice_id,
                        settings=VoiceSettings(
                            stability=0.40,  # Reduced from 0.55
                            similarity_boost=0.75,
                            style=0.15,  # Reduced from 0.2
                            use_speaker_boost=True
                        )
                    ),
                    model="eleven_turbo_v2_5"  # Changed from eleven_multilingual_v2
                )

            # Convert bytes-like object to bytes
            if not isinstance(audio_bytes, bytes):
                audio_bytes = bytes(audio_bytes)

            # Convert to Exotel format (PCM 8kHz 16-bit mono)
            pcm_audio = self.converter.convert_to_pcm_8khz(
                audio_bytes,
                source_format="mp3"
            )

            duration = time.time() - start_time

            # Record metrics
            if METRICS_ENABLED:
                metrics.record_tts_request(duration)

            logger.info(
                "Speech generated (low latency)",
                call_sid=call_sid,
                audio_size=len(pcm_audio),
                duration_seconds=round(duration, 3)
            )

            return pcm_audio

        except Exception as e:
            # Record error
            if METRICS_ENABLED:
                metrics.record_error("tts_request_failed", "tts_service")

            logger.error(
                "TTS generation failed",
                call_sid=call_sid,
                error=str(e)
            )
            raise

    async def generate_streaming(self, text: str, call_sid: str):
        """
        Generate speech with streaming
        For future enhancement - stream audio chunks as they're generated
        """
        # TODO: Implement streaming TTS for lower latency
        logger.info("Streaming TTS not yet implemented", call_sid=call_sid)
