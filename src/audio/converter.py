"""
Audio format converter.

Converts between different audio formats (e.g., MP3 to PCM).
Used to convert ElevenLabs output to Exotel-compatible format.
"""

import io
import subprocess
import tempfile
from typing import Optional
from pathlib import Path

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    AudioSegment = None
    PYDUB_AVAILABLE = False


class AudioConverter:
    """
    Convert between different audio formats
    Used to convert ElevenLabs output to Exotel format
    """

    def __init__(self):
        # Check for ffmpeg
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            self.ffmpeg_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.ffmpeg_available = False

        self.enabled = PYDUB_AVAILABLE or self.ffmpeg_available

        if not self.enabled:
            import warnings
            warnings.warn(
                "Neither pydub nor ffmpeg available - audio conversion will fail. "
                "Install ffmpeg with: brew install ffmpeg"
            )

    @staticmethod
    def convert_to_pcm_8khz(
        audio_bytes: bytes,
        source_format: str = "mp3"
    ) -> bytes:
        """
        Convert audio to PCM 8kHz mono 16-bit

        Args:
            audio_bytes: Input audio in any format
            source_format: Input format (mp3, wav, etc.)

        Returns:
            PCM audio bytes in Exotel format

        Raises:
            ValueError: If conversion fails
        """
        # Try ffmpeg first (more reliable for Python 3.13+)
        try:
            return AudioConverter._convert_with_ffmpeg(audio_bytes, source_format)
        except Exception as ffmpeg_error:
            # Fallback to pydub if available
            if AudioSegment is not None:
                try:
                    return AudioConverter._convert_with_pydub(audio_bytes, source_format)
                except Exception as pydub_error:
                    raise ValueError(f"Audio conversion failed with both ffmpeg ({ffmpeg_error}) and pydub ({pydub_error})")
            else:
                raise ValueError(f"Audio conversion failed: {ffmpeg_error}")

    @staticmethod
    def _convert_with_ffmpeg(audio_bytes: bytes, source_format: str) -> bytes:
        """Convert audio using ffmpeg directly"""
        with tempfile.NamedTemporaryFile(suffix=f'.{source_format}', delete=False) as input_file:
            input_path = input_file.name
            input_file.write(audio_bytes)

        with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as output_file:
            output_path = output_file.name

        try:
            # Convert to PCM 8kHz mono 16-bit using ffmpeg
            subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-ar', '8000',      # 8kHz sample rate
                '-ac', '1',         # Mono
                '-f', 's16le',      # 16-bit PCM little-endian
                '-y',               # Overwrite output
                output_path
            ], check=True, capture_output=True)

            # Read the converted audio
            with open(output_path, 'rb') as f:
                pcm_bytes = f.read()

            return pcm_bytes
        finally:
            # Clean up temp files
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

    @staticmethod
    def _convert_with_pydub(audio_bytes: bytes, source_format: str) -> bytes:
        """Convert audio using pydub (legacy fallback)"""
        # Load audio from bytes
        audio = AudioSegment.from_file(
            io.BytesIO(audio_bytes),
            format=source_format
        )

        # Convert to required format
        audio = audio.set_frame_rate(8000)  # 8kHz
        audio = audio.set_channels(1)       # Mono
        audio = audio.set_sample_width(2)   # 16-bit

        # Export as raw PCM
        return audio.raw_data

    @staticmethod
    def get_audio_duration_ms(audio_bytes: bytes, format: str = "mp3") -> int:
        """
        Get audio duration in milliseconds

        Args:
            audio_bytes: Audio data
            format: Audio format

        Returns:
            Duration in milliseconds

        Raises:
            ValueError: If duration calculation fails
        """
        if AudioSegment is None:
            raise ImportError("pydub is required for audio processing")

        try:
            audio = AudioSegment.from_file(
                io.BytesIO(audio_bytes),
                format=format
            )
            return len(audio)
        except Exception as e:
            raise ValueError(f"Failed to get audio duration: {str(e)}")

    @staticmethod
    def convert_from_wav_to_pcm(wav_bytes: bytes) -> bytes:
        """
        Convert WAV to raw PCM 8kHz mono 16-bit

        Args:
            wav_bytes: WAV audio data

        Returns:
            Raw PCM bytes
        """
        return AudioConverter.convert_to_pcm_8khz(wav_bytes, source_format="wav")
