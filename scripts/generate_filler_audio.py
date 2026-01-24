#!/usr/bin/env python3
"""
Generate filler audio files for latency masking.

Creates short PCM audio files for common filler words:
- hmm.pcm
- okay.pcm
- right.pcm

These are played when LLM processing takes >300ms to mask latency.
"""

import asyncio
import os
import sys

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai.tts_service import ElevenLabsTTSService
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


async def generate_fillers():
    """Generate filler audio files"""

    logger.info("Starting filler audio generation...")

    try:
        # Initialize TTS service
        tts = ElevenLabsTTSService()

        # Create output directory
        output_dir = "assets/filler_audio"
        os.makedirs(output_dir, exist_ok=True)

        # Filler words to generate
        fillers = [
            ("Hmm", "hmm.pcm"),
            ("Okay", "okay.pcm"),
            ("Right", "right.pcm")
        ]

        logger.info(f"Generating {len(fillers)} filler audio files...")

        for text, filename in fillers:
            try:
                logger.info(f"Generating: {text} -> {filename}")

                # Generate audio
                audio = await tts.generate_speech(text, call_sid="filler_gen")

                # Save to file
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(audio)

                file_size_kb = len(audio) / 1024
                logger.info(f"✅ Generated: {filepath} ({file_size_kb:.1f} KB)")

            except Exception as e:
                logger.error(f"❌ Failed to generate {filename}: {e}")

        logger.info("✨ Filler audio generation complete!")
        logger.info(f"Files saved to: {os.path.abspath(output_dir)}")

        # List generated files
        logger.info("\nGenerated files:")
        for filename in os.listdir(output_dir):
            filepath = os.path.join(output_dir, filename)
            size = os.path.getsize(filepath)
            logger.info(f"  - {filename} ({size} bytes)")

    except Exception as e:
        logger.error(f"❌ Filler audio generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(generate_fillers())
