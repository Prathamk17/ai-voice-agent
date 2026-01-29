"""
Deepgram Speech-to-Text service.

Handles transcription of audio to text using Deepgram API.
"""

from typing import Optional, Dict, Any
import asyncio
import time
import struct
import io

try:
    from deepgram import DeepgramClient
    DEEPGRAM_AVAILABLE = True
except ImportError:
    DeepgramClient = None
    DEEPGRAM_AVAILABLE = False

from src.config.settings import settings
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)

# Import metrics (optional)
try:
    from src.monitoring.metrics import metrics
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False
    logger.debug("Metrics not available")


class DeepgramSTTService:
    """
    Speech-to-Text using Deepgram

    Features:
    - Real-time transcription
    - Indian accent support
    - Voice Activity Detection
    - Interim results
    """

    def __init__(self):
        if not DEEPGRAM_AVAILABLE:
            logger.warning("Deepgram SDK not available - transcription will be disabled")
            self.dg_client = None
        elif not settings.DEEPGRAM_API_KEY:
            logger.warning("DEEPGRAM_API_KEY not configured - transcription will be disabled")
            self.dg_client = None
        else:
            # Deepgram SDK v5.x requires api_key as keyword argument
            self.dg_client = DeepgramClient(api_key=settings.DEEPGRAM_API_KEY)

        # Persistent WebSocket connections: call_sid -> {connection, transcript_buffer}
        self.active_streams: Dict[str, Dict[str, Any]] = {}

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        call_sid: str
    ) -> Optional[str]:
        """
        Transcribe audio chunk using persistent WebSocket connection.

        Sends audio through the EXISTING persistent connection (no handshake!).
        Does NOT call finish() - connection stays open for next chunk.

        Args:
            audio_bytes: Raw audio bytes (PCM 8kHz 16-bit mono)
            call_sid: Call session ID

        Returns:
            Accumulated final transcript, or None if no complete sentence yet
        """
        # Check if persistent connection exists
        if call_sid not in self.active_streams:
            logger.warning(
                "⚠️ No persistent connection found - falling back to legacy mode",
                call_sid=call_sid,
                active_streams_count=len(self.active_streams),
                active_call_sids=list(self.active_streams.keys())
            )
            return await self.transcribe_audio_legacy(audio_bytes, call_sid)

        try:
            start_time = time.time()
            stream_data = self.active_streams[call_sid]
            dg_connection = stream_data['connection']
            transcript_buffer = stream_data['transcript_buffer']

            # Clear previous final transcripts
            transcript_buffer['final_transcripts'].clear()

            # Send audio through persistent connection (NO handshake, NO finish!)
            logger.debug(
                "Sending audio to persistent WebSocket",
                call_sid=call_sid,
                audio_size=len(audio_bytes)
            )

            dg_connection.send(audio_bytes)

            # Wait briefly for Deepgram to process and send back transcripts
            # Increased from 150ms to 300ms for more reliable results
            await asyncio.sleep(0.3)

            duration = time.time() - start_time

            # Record metrics
            if METRICS_ENABLED:
                metrics.record_stt_request(duration)

            # Get final transcripts accumulated during this chunk
            final_transcripts = transcript_buffer['final_transcripts'].copy()

            if final_transcripts:
                result_text = " ".join(final_transcripts).strip()

                # Post-process transcript
                cleaned_transcript = self._post_process_transcript(result_text)

                logger.info(
                    "✅ Streaming transcription (persistent WS)",
                    call_sid=call_sid,
                    transcript=cleaned_transcript[:100],
                    duration_seconds=round(duration, 3),
                    latency_improvement="~700ms saved vs legacy"
                )

                return cleaned_transcript

            # No final transcript yet (user still speaking or silence)
            logger.debug(
                "No final transcript yet from WebSocket",
                call_sid=call_sid,
                interim=transcript_buffer.get('last_interim', '')[:50] if transcript_buffer.get('last_interim') else None
            )
            return None

        except Exception as e:
            logger.error(
                "Streaming transcription failed",
                call_sid=call_sid,
                error=str(e)
            )

            if METRICS_ENABLED:
                metrics.record_error("stt_streaming_failed", "stt_service")

            # Fallback to legacy
            logger.info("Falling back to legacy file-based transcription", call_sid=call_sid)
            return await self.transcribe_audio_legacy(audio_bytes, call_sid)

    async def transcribe_audio_streaming(
        self,
        audio_bytes: bytes,
        call_sid: str,
        callback=None
    ) -> Optional[str]:
        """
        Transcribe audio using Deepgram WebSocket for streaming

        Args:
            audio_bytes: Raw audio bytes (PCM 8kHz 16-bit mono)
            call_sid: Call session ID
            callback: Optional callback for interim results

        Returns:
            Final transcript when speech ends
        """
        if not self.dg_client:
            logger.error("Deepgram client not initialized")
            return None

        try:
            start_time = time.time()

            # Deepgram WebSocket streaming configuration
            try:
                from deepgram import LiveTranscriptionEvents, LiveOptions
            except ImportError:
                logger.warning("Deepgram WebSocket not available, falling back to file-based")
                return await self.transcribe_audio_legacy(audio_bytes, call_sid)

            # Create WebSocket connection
            dg_connection = self.dg_client.listen.live.v("1")

            # Store final transcript
            final_transcript = []

            # Event handlers
            def on_message(self, result, **kwargs):
                sentence = result.channel.alternatives[0].transcript
                if len(sentence) > 0:
                    if result.is_final:
                        final_transcript.append(sentence)
                        logger.info(f"Final transcript: {sentence}", call_sid=call_sid)
                    else:
                        # Interim result (optional callback)
                        if callback:
                            callback(sentence, is_final=False)
                        logger.debug(f"Interim transcript: {sentence}", call_sid=call_sid)

            def on_metadata(self, metadata, **kwargs):
                logger.debug(f"Metadata: {metadata}", call_sid=call_sid)

            def on_error(self, error, **kwargs):
                logger.error(f"Deepgram error: {error}", call_sid=call_sid)

            # Register event handlers
            dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
            dg_connection.on(LiveTranscriptionEvents.Error, on_error)

            # Configure streaming options with optimized settings
            # Indian location keywords for better recognition
            location_keywords = [
                "Kharadi", "Pune", "Whitefield", "HSR Layout", "Koramangala",
                "Bandra", "Mumbai", "Gurgaon", "Noida", "Bangalore", "Bengaluru",
                "Hyderabad", "Chennai", "Jaipur", "Jhotwara", "Vaishali Nagar",
                "Hinjewadi", "Wakad", "Viman Nagar", "Aundh", "Baner"
            ]

            # Real estate specific keywords
            re_keywords = [
                "BHK", "2BHK", "3BHK", "4BHK", "registry", "patta", "possession",
                "ready to move", "under construction", "Vastu", "lakh", "crore"
            ]

            options = LiveOptions(
                model="nova-2-phonecall",  # Optimized for phone calls (changed from nova-2)
                language="en-IN",  # Indian English
                interim_results=True,  # Enable interim transcripts
                endpointing=300,  # 300ms silence detection (was missing)
                smart_format=True,  # Smart formatting
                punctuate=True,
                encoding="linear16",
                sample_rate=8000,
                channels=1,
                keywords=location_keywords + re_keywords  # Boost Indian location and RE terms
            )

            # Start connection
            if dg_connection.start(options) is False:
                logger.error("Failed to start Deepgram connection", call_sid=call_sid)
                return None

            # Send audio data
            dg_connection.send(audio_bytes)

            # Finish sending (triggers final transcript)
            dg_connection.finish()

            # Wait briefly for final result
            await asyncio.sleep(0.1)

            duration = time.time() - start_time

            # Record metrics
            if METRICS_ENABLED:
                metrics.record_stt_request(duration)

            # Combine final transcripts
            result_text = " ".join(final_transcript).strip()

            if result_text:
                logger.info(
                    "Streaming transcription complete",
                    call_sid=call_sid,
                    transcript=result_text[:100],
                    duration_seconds=round(duration, 3)
                )
                return result_text

            return None

        except Exception as e:
            logger.error("Streaming transcription failed", call_sid=call_sid, error=str(e))
            if METRICS_ENABLED:
                metrics.record_error("stt_request_failed", "stt_service")
            # Fallback to legacy method
            logger.info("Falling back to file-based transcription", call_sid=call_sid)
            return await self.transcribe_audio_legacy(audio_bytes, call_sid)

    async def transcribe_audio_legacy(
        self,
        audio_bytes: bytes,
        call_sid: str
    ) -> Optional[str]:
        """
        Legacy file-based transcription (fallback)
        """
        if not self.dg_client:
            logger.error("Deepgram client not initialized")
            return None

        try:
            # Transcribe with timing
            start_time = time.time()

            # DEBUG: Log audio buffer size
            audio_duration_sec = len(audio_bytes) / 16000  # 8kHz 16-bit = 16000 bytes/sec
            logger.info(
                f"🎙️ Sending to Deepgram: {len(audio_bytes)} bytes ({audio_duration_sec:.2f}s)",
                call_sid=call_sid
            )

            if len(audio_bytes) == 0:
                logger.error("❌ EMPTY AUDIO BUFFER! Cannot transcribe 0 bytes", call_sid=call_sid)
                return None

            # Convert raw PCM to WAV format with header (so Deepgram knows sample rate)
            wav_audio = self._add_wav_header(audio_bytes, sample_rate=8000, channels=1, bits_per_sample=16)

            # Use Deepgram SDK v3.x API
            # Transcribe using listen.prerecorded.v("1").transcribe_file()
            # Indian location keywords for better recognition
            location_keywords = [
                "Kharadi", "Pune", "Whitefield", "HSR Layout", "Koramangala",
                "Bandra", "Mumbai", "Gurgaon", "Noida", "Bangalore", "Bengaluru",
                "Hyderabad", "Chennai", "Jaipur", "Jhotwara", "Vaishali Nagar",
                "Hinjewadi", "Wakad", "Viman Nagar", "Aundh", "Baner"
            ]

            # Real estate specific keywords
            re_keywords = [
                "BHK", "2BHK", "3BHK", "4BHK", "registry", "patta", "possession",
                "ready to move", "under construction", "Vastu", "lakh", "crore"
            ]

            response = self.dg_client.listen.prerecorded.v("1").transcribe_file(
                request=wav_audio,
                model="nova-3",  # ⚡ UPGRADED: Latest model for better Hinglish
                language="en-IN",
                punctuate=True,
                smart_format=True,
                keywords=location_keywords + re_keywords  # Boost Indian location and RE terms
            )

            duration = time.time() - start_time

            # Record metrics
            if METRICS_ENABLED:
                metrics.record_stt_request(duration)

            # Extract transcript (Deepgram v5 response structure)
            if (hasattr(response, 'results') and
                response.results and
                hasattr(response.results, 'channels') and
                response.results.channels and
                len(response.results.channels) > 0 and
                hasattr(response.results.channels[0], 'alternatives') and
                response.results.channels[0].alternatives and
                len(response.results.channels[0].alternatives) > 0):

                alternative = response.results.channels[0].alternatives[0]
                transcript = alternative.transcript

                # 🚨 CONFIDENCE FILTERING: Reject low-confidence transcriptions
                confidence = getattr(alternative, 'confidence', 0.0)
                MIN_CONFIDENCE = 0.65  # 65% minimum confidence (lowered from 75% for phone calls)

                if confidence > 0 and confidence < MIN_CONFIDENCE:
                    logger.warning(
                        "❌ LOW CONFIDENCE TRANSCRIPT REJECTED",
                        call_sid=call_sid,
                        confidence=f"{confidence*100:.1f}%",
                        transcript=transcript[:50],
                        reason="Below minimum threshold"
                    )
                    return None

                if transcript and transcript.strip():
                    # Post-process to fix common transcription errors
                    cleaned_transcript = self._post_process_transcript(transcript)

                    logger.info(
                        "Legacy transcription complete",
                        call_sid=call_sid,
                        transcript=cleaned_transcript[:100],
                        confidence=f"{confidence*100:.1f}%" if confidence > 0 else "N/A",
                        duration_seconds=round(duration, 3)
                    )

                    # Log if we made corrections
                    if cleaned_transcript != transcript:
                        logger.info(
                            "Applied STT corrections",
                            call_sid=call_sid,
                            original=transcript[:50],
                            corrected=cleaned_transcript[:50]
                        )

                    return cleaned_transcript.strip()

            return None

        except Exception as e:
            logger.error(
                "Legacy transcription failed",
                call_sid=call_sid,
                error=str(e)
            )

            # Record error
            if METRICS_ENABLED:
                metrics.record_error("stt_request_failed", "stt_service")
            return None

    async def start_streaming(self, call_sid: str):
        """
        Start persistent WebSocket streaming transcription session.

        Opens a WebSocket connection ONCE at call start and keeps it open
        for the entire call duration. This eliminates handshake overhead
        on every chunk (300-500ms in India).

        Args:
            call_sid: Call session ID
        """
        if not self.dg_client:
            logger.error("Deepgram client not initialized", call_sid=call_sid)
            return

        if call_sid in self.active_streams:
            logger.warning("Stream already exists for this call", call_sid=call_sid)
            return

        try:
            # Import Deepgram WebSocket classes
            try:
                from deepgram import LiveTranscriptionEvents, LiveOptions
            except ImportError:
                logger.error("Deepgram WebSocket not available", call_sid=call_sid)
                return

            # Create persistent WebSocket connection
            dg_connection = self.dg_client.listen.live.v("1")

            # Store transcripts for this call
            transcript_buffer = {
                'final_transcripts': [],
                'last_interim': None
            }

            # Event handlers
            def on_message(self, result, **kwargs):
                sentence = result.channel.alternatives[0].transcript
                if len(sentence) > 0:
                    if result.is_final:
                        transcript_buffer['final_transcripts'].append(sentence)
                        logger.info(
                            "Final transcript chunk",
                            call_sid=call_sid,
                            text=sentence[:50]
                        )
                    else:
                        # Store interim for context
                        transcript_buffer['last_interim'] = sentence
                        logger.debug(
                            "Interim transcript",
                            call_sid=call_sid,
                            text=sentence[:30]
                        )

            def on_metadata(self, metadata, **kwargs):
                logger.debug("Deepgram metadata received", call_sid=call_sid)

            def on_error(self, error, **kwargs):
                logger.error(
                    "Deepgram WebSocket error",
                    call_sid=call_sid,
                    error=str(error)
                )

            # Register event handlers
            dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
            dg_connection.on(LiveTranscriptionEvents.Error, on_error)

            # Configure with OPTIMIZED low-latency settings for India (Hinglish)
            # Indian location keywords for better recognition
            location_keywords = [
                "Kharadi", "Pune", "Whitefield", "HSR Layout", "Koramangala",
                "Bandra", "Mumbai", "Gurgaon", "Noida", "Bangalore", "Bengaluru",
                "Hyderabad", "Chennai", "Jaipur", "Jhotwara", "Vaishali Nagar",
                "Hinjewadi", "Wakad", "Viman Nagar", "Aundh", "Baner"
            ]

            # Real estate specific keywords
            re_keywords = [
                "BHK", "2BHK", "3BHK", "4BHK", "registry", "patta", "possession",
                "ready to move", "under construction", "Vastu", "lakh", "crore"
            ]

            options = LiveOptions(
                model="nova-3",  # ⚡ UPGRADED: Latest model, better Hinglish + faster
                language="en-IN",  # Indian English (hardcoded for speed)
                detect_language=False,  # ⚡ Disable detection for lower latency
                interim_results=True,  # Enable real-time interim transcripts
                endpointing=300,  # 300ms silence detection
                smart_format=True,
                punctuate=True,
                encoding="linear16",
                sample_rate=8000,
                channels=1,
                keywords=location_keywords + re_keywords
            )

            # Start persistent connection (handshake ONCE)
            # Use to_thread to prevent blocking if this is a sync operation
            logger.info(
                "Starting persistent Deepgram connection...",
                call_sid=call_sid
            )

            start_result = await asyncio.to_thread(dg_connection.start, options)

            if start_result is False:
                logger.error(
                    "❌ Failed to start persistent Deepgram connection (returned False)",
                    call_sid=call_sid
                )
                return

            # Store connection and transcript buffer
            self.active_streams[call_sid] = {
                'connection': dg_connection,
                'transcript_buffer': transcript_buffer,
                'started_at': time.time()
            }

            logger.info(
                "✅ Persistent WebSocket connection established (LOW LATENCY MODE)",
                call_sid=call_sid,
                model="nova-3",
                active_streams_count=len(self.active_streams),
                stored_call_sids=list(self.active_streams.keys())
            )

        except Exception as e:
            import traceback
            logger.error(
                "Failed to start streaming",
                call_sid=call_sid,
                error=str(e),
                traceback=traceback.format_exc()
            )

    async def stop_streaming(self, call_sid: str):
        """
        Stop persistent WebSocket streaming session.

        Calls finish() ONCE at call end to properly close the connection
        and get final transcripts. This is where we pay the 200-400ms
        "final pass" delay, but only once instead of per chunk.

        Args:
            call_sid: Call session ID
        """
        if call_sid not in self.active_streams:
            logger.debug("No active stream to stop", call_sid=call_sid)
            return

        try:
            stream_data = self.active_streams[call_sid]
            dg_connection = stream_data['connection']
            started_at = stream_data['started_at']

            # Call finish() to close connection and get final results
            dg_connection.finish()

            # Wait briefly for final transcripts
            await asyncio.sleep(0.1)

            duration = time.time() - started_at

            logger.info(
                "✅ Persistent WebSocket connection closed",
                call_sid=call_sid,
                duration_seconds=round(duration, 2)
            )

            # Clean up
            del self.active_streams[call_sid]

        except Exception as e:
            logger.error(
                "Error stopping streaming",
                call_sid=call_sid,
                error=str(e)
            )
            # Clean up anyway
            if call_sid in self.active_streams:
                del self.active_streams[call_sid]

    @staticmethod
    def _add_wav_header(pcm_data: bytes, sample_rate: int = 8000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
        """
        Add WAV header to raw PCM data

        Args:
            pcm_data: Raw PCM audio bytes
            sample_rate: Sample rate in Hz (default 8000)
            channels: Number of channels (default 1 for mono)
            bits_per_sample: Bits per sample (default 16)

        Returns:
            WAV format audio with header
        """
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        data_size = len(pcm_data)

        # Create WAV header
        header = struct.pack('<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            data_size + 36,  # File size - 8
            b'WAVE',
            b'fmt ',
            16,  # fmt chunk size
            1,   # PCM format
            channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
            b'data',
            data_size
        )

        return header + pcm_data

    @staticmethod
    def _post_process_transcript(transcript: str) -> str:
        """
        Post-process transcript to fix common STT errors from phone audio

        Args:
            transcript: Raw transcript from Deepgram

        Returns:
            Cleaned transcript with common errors fixed
        """
        if not transcript:
            return transcript

        # Common phrase corrections (case-insensitive)
        corrections = {
            # Common misheard phrases
            r"\bjust exploding\b": "just exploring",
            r"\bexploding\b": "exploring",
            r"\bget i am\b": "yeah I am",
            r"\balex it'?s been running\b": "okay",
            r"\bwhat am i [a-z]+ to do\b": "what am I going to do",

            # Remove filler artifacts
            r"\b(um|uh|er|ah)\b": "",

            # Fix common real estate terms
            r"\bbhk\b": "BHK",
            r"\blac\b": "lakh",
            r"\blakh?s?\b": "lakhs",
            r"\bcrores?\b": "crore",

            # Clean up multiple spaces
            r"\s+": " ",
        }

        import re
        cleaned = transcript

        for pattern, replacement in corrections.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        return cleaned.strip()
