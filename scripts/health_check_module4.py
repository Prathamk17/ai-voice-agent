"""
Health Check Script for Module 4

Verifies all Module 4 components are working correctly:
- AI service connections (Deepgram, OpenAI, ElevenLabs)
- Audio processing
- Conversation engine
- WebSocket server
- Redis sessions
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audio.processor import AudioProcessor
from src.ai.stt_service import DeepgramSTTService
from src.ai.tts_service import ElevenLabsTTSService
from src.ai.llm_service import LLMService
from src.conversation.engine import ConversationEngine
from src.models.conversation import ConversationSession
from src.websocket.session_manager import SessionManager
from src.config.settings import settings


class HealthChecker:
    """Health check for Module 4 components"""

    def __init__(self):
        self.results = []

    def log_success(self, component: str, message: str = ""):
        """Log successful check"""
        self.results.append((component, True, message))
        print(f"✅ {component}: {message or 'OK'}")

    def log_failure(self, component: str, error: str):
        """Log failed check"""
        self.results.append((component, False, error))
        print(f"❌ {component}: {error}")

    def log_warning(self, component: str, message: str):
        """Log warning"""
        print(f"⚠️  {component}: {message}")

    async def check_configuration(self):
        """Check environment configuration"""
        print("\n📋 Checking Configuration...")

        # Check Deepgram
        if settings.DEEPGRAM_API_KEY:
            self.log_success("Deepgram API Key", "Configured")
        else:
            self.log_failure("Deepgram API Key", "Not configured in .env")

        # Check OpenAI
        if settings.OPENAI_API_KEY:
            self.log_success("OpenAI API Key", "Configured")
        else:
            self.log_failure("OpenAI API Key", "Not configured in .env")

        # Check ElevenLabs
        if settings.ELEVENLABS_API_KEY:
            self.log_success("ElevenLabs API Key", "Configured")
        else:
            self.log_failure("ElevenLabs API Key", "Not configured in .env")

        # Check voice ID
        if settings.ELEVENLABS_VOICE_ID:
            self.log_success("ElevenLabs Voice ID", "Configured")
        else:
            self.log_warning("ElevenLabs Voice ID", "Not set, will use default voice")

    async def check_audio_processing(self):
        """Check audio processing"""
        print("\n🎵 Checking Audio Processing...")

        try:
            # Test encoding/decoding
            test_audio = b"test audio data" * 100
            encoded = AudioProcessor.encode_for_exotel(test_audio)
            decoded = AudioProcessor.decode_exotel_audio(encoded)

            if decoded == test_audio:
                self.log_success("Audio Encode/Decode", "Working correctly")
            else:
                self.log_failure("Audio Encode/Decode", "Data mismatch after decode")

            # Test chunking
            chunks = AudioProcessor.chunk_audio(test_audio, chunk_duration_ms=100)
            if len(chunks) > 0:
                self.log_success("Audio Chunking", f"{len(chunks)} chunks created")
            else:
                self.log_failure("Audio Chunking", "No chunks created")

            # Test duration calculation
            duration = AudioProcessor.get_audio_duration_ms(b"x" * 16000)
            if duration == 1000:
                self.log_success("Audio Duration", "Calculation correct")
            else:
                self.log_failure("Audio Duration", f"Expected 1000ms, got {duration}ms")

        except Exception as e:
            self.log_failure("Audio Processing", str(e))

    async def check_deepgram(self):
        """Check Deepgram STT service"""
        print("\n🎤 Checking Deepgram STT...")

        try:
            stt = DeepgramSTTService()
            if stt.dg_client:
                self.log_success("Deepgram Client", "Initialized")
            else:
                self.log_failure("Deepgram Client", "Client not initialized")
        except Exception as e:
            self.log_failure("Deepgram STT", str(e))

    async def check_openai(self):
        """Check OpenAI LLM service"""
        print("\n🤖 Checking OpenAI LLM...")

        try:
            llm = LLMService()
            if llm.client:
                self.log_success("OpenAI Client", "Initialized")

                # Test simple generation
                print("   Testing response generation...")
                response = await llm.generate_response(
                    user_input="Hello",
                    conversation_history=[],
                    lead_context={"lead_name": "Test"},
                    current_stage="intro",
                    system_prompt="You are a helpful assistant. Respond with just 'Hi there!'"
                )

                if response:
                    self.log_success("OpenAI Generation", f"Response: {response[:50]}...")
                else:
                    self.log_failure("OpenAI Generation", "No response generated")

            else:
                self.log_failure("OpenAI Client", "Client not initialized")

        except Exception as e:
            self.log_failure("OpenAI LLM", str(e))

    async def check_elevenlabs(self):
        """Check ElevenLabs TTS service"""
        print("\n🔊 Checking ElevenLabs TTS...")

        try:
            tts = ElevenLabsTTSService()
            if tts.enabled:
                self.log_success("ElevenLabs Client", "Initialized")

                # Test simple generation (small text to minimize cost)
                print("   Testing speech generation...")
                audio = await tts.generate_speech("Hi", "test_call")

                if audio and len(audio) > 0:
                    self.log_success("ElevenLabs Generation", f"Generated {len(audio)} bytes")
                else:
                    self.log_failure("ElevenLabs Generation", "No audio generated")

            else:
                self.log_failure("ElevenLabs Client", "Not enabled (API key missing)")

        except Exception as e:
            self.log_failure("ElevenLabs TTS", str(e))

    async def check_conversation_engine(self):
        """Check conversation engine"""
        print("\n💬 Checking Conversation Engine...")

        try:
            engine = ConversationEngine()
            self.log_success("Conversation Engine", "Initialized")

            # Test intro generation
            session = ConversationSession(
                call_sid="health_check",
                lead_id=1,
                lead_name="Test User",
                lead_phone="+919876543210",
                property_type="2BHK",
                location="Bangalore",
                budget=5000000.0
            )

            intro = await engine.generate_intro(session)
            if intro and len(intro) > 0:
                self.log_success("Intro Generation", f"Generated: {intro[:60]}...")
            else:
                self.log_failure("Intro Generation", "No intro generated")

        except Exception as e:
            self.log_failure("Conversation Engine", str(e))

    async def check_session_manager(self):
        """Check Redis session management"""
        print("\n💾 Checking Session Manager...")

        try:
            manager = SessionManager()
            self.log_success("Session Manager", "Initialized")

            # Test session creation
            test_call_sid = "health_check_session"
            session = await manager.create_session(
                test_call_sid,
                {
                    "lead_id": 1,
                    "lead_name": "Test",
                    "phone": "+919876543210"
                }
            )

            if session:
                self.log_success("Session Creation", "Session created in Redis")

                # Test session retrieval
                retrieved = await manager.get_session(test_call_sid)
                if retrieved:
                    self.log_success("Session Retrieval", "Session retrieved from Redis")
                else:
                    self.log_failure("Session Retrieval", "Could not retrieve session")

                # Cleanup
                await manager.delete_session(test_call_sid)
                self.log_success("Session Cleanup", "Session deleted")

            else:
                self.log_failure("Session Creation", "Could not create session")

        except Exception as e:
            self.log_failure("Session Manager", str(e))

    async def check_websocket_server(self):
        """Check WebSocket server availability"""
        print("\n🔌 Checking WebSocket Server...")

        try:
            from src.websocket.server import websocket_server
            self.log_success("WebSocket Server", "Initialized")

            # Check active connections
            count = websocket_server.get_active_connections_count()
            self.log_success("Active Connections", f"{count} active")

        except Exception as e:
            self.log_failure("WebSocket Server", str(e))

    def print_summary(self):
        """Print summary of health check results"""
        print("\n" + "=" * 60)
        print("📊 HEALTH CHECK SUMMARY")
        print("=" * 60)

        total = len(self.results)
        passed = sum(1 for _, success, _ in self.results if success)
        failed = total - passed

        print(f"\nTotal Checks: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")

        if failed > 0:
            print("\n⚠️  Failed Checks:")
            for component, success, message in self.results:
                if not success:
                    print(f"   - {component}: {message}")

        print("\n" + "=" * 60)

        if failed == 0:
            print("✅ ALL CHECKS PASSED - Module 4 is ready!")
            return 0
        else:
            print("❌ SOME CHECKS FAILED - Please fix the issues above")
            return 1


async def main():
    """Run all health checks"""
    checker = HealthChecker()

    print("""
╔════════════════════════════════════════════════════════════╗
║         Module 4 Health Check - AI Conversation Engine    ║
╚════════════════════════════════════════════════════════════╝
    """)

    await checker.check_configuration()
    await checker.check_audio_processing()
    await checker.check_deepgram()
    await checker.check_openai()
    await checker.check_elevenlabs()
    await checker.check_conversation_engine()
    await checker.check_session_manager()
    await checker.check_websocket_server()

    return checker.print_summary()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
