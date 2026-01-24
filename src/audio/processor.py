"""
Audio processor for encoding/decoding audio data for Exotel WebSocket.

Handles:
- Base64 encoding/decoding
- Audio chunking for streaming
- Format: 16-bit Linear PCM, 8000 Hz, Mono
"""

import base64
from typing import List


class AudioProcessor:
    """
    Handle audio encoding/decoding for Exotel WebSocket

    Exotel Format:
    - 16-bit Linear PCM
    - 8000 Hz sample rate
    - Mono channel
    - Base64 encoded
    """

    @staticmethod
    def decode_exotel_audio(base64_payload: str) -> bytes:
        """
        Decode base64 audio from Exotel

        Args:
            base64_payload: Base64-encoded PCM audio

        Returns:
            Raw PCM bytes

        Raises:
            ValueError: If decoding fails
        """
        try:
            audio_bytes = base64.b64decode(base64_payload)
            return audio_bytes
        except Exception as e:
            raise ValueError(f"Failed to decode audio: {str(e)}")

    @staticmethod
    def encode_for_exotel(pcm_bytes: bytes) -> str:
        """
        Encode PCM audio to base64 for Exotel

        Args:
            pcm_bytes: Raw PCM audio bytes (8kHz, 16-bit, mono)

        Returns:
            Base64-encoded string

        Raises:
            ValueError: If encoding fails
        """
        try:
            return base64.b64encode(pcm_bytes).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to encode audio: {str(e)}")

    @staticmethod
    def chunk_audio(audio_bytes: bytes, chunk_duration_ms: int = 100) -> List[bytes]:
        """
        Split audio into chunks for streaming

        Args:
            audio_bytes: Raw PCM audio
            chunk_duration_ms: Duration of each chunk in milliseconds

        Returns:
            List of audio chunks
        """
        # 8kHz, 16-bit, mono = 16000 bytes per second
        # Sample rate: 8000 Hz
        # Bytes per sample: 2 (16-bit)
        # Total bytes per second: 8000 * 2 = 16000
        bytes_per_ms = 16  # (8000 Hz * 2 bytes) / 1000
        chunk_size = bytes_per_ms * chunk_duration_ms

        chunks = []
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            chunks.append(chunk)

        return chunks

    @staticmethod
    def get_audio_duration_ms(audio_bytes: bytes) -> int:
        """
        Calculate audio duration in milliseconds

        Args:
            audio_bytes: Raw PCM audio (8kHz, 16-bit, mono)

        Returns:
            Duration in milliseconds
        """
        # 8kHz, 16-bit, mono = 16000 bytes per second
        bytes_per_second = 16000
        duration_seconds = len(audio_bytes) / bytes_per_second
        return int(duration_seconds * 1000)
