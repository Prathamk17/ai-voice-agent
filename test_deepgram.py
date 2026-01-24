#!/usr/bin/env python3
"""
Quick test to verify Deepgram transcription is working
"""
import asyncio
from src.ai.stt_service import DeepgramSTTService

async def test_deepgram():
    """Test Deepgram with a small audio sample"""
    stt = DeepgramSTTService()

    if not stt.dg_client:
        print("❌ Deepgram client not initialized (check API key)")
        return

    print("✅ Deepgram client initialized")
    print(f"   Client type: {type(stt.dg_client)}")

    # Create a small test audio (silence - just to test API)
    # 8kHz, 16-bit, mono, 0.5 seconds = 8000 bytes
    test_audio = b'\x00' * 8000

    print("\n🧪 Testing transcription with silence (should return None)...")
    try:
        result = await stt.transcribe_audio(test_audio, "test-call")
        if result:
            print(f"✅ Transcription returned: '{result}'")
        else:
            print("✅ Transcription returned None (expected for silence)")
        print("\n🎉 Deepgram API is working correctly!")
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        print("\n💡 Check if the API method is correct for your Deepgram SDK version")

if __name__ == "__main__":
    asyncio.run(test_deepgram())
