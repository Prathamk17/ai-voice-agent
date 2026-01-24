"""
Tests for Module 4: WebSocket Server & AI Conversation Engine

Tests:
- Audio processing (encode/decode, chunking)
- Conversation state machine
- Session management
- Mock WebSocket interactions
"""

import pytest
import base64
from datetime import datetime

from src.audio.processor import AudioProcessor
from src.conversation.state_machine import ConversationStateMachine
from src.models.conversation import ConversationSession, ConversationStage


class TestAudioProcessor:
    """Test audio encoding/decoding"""

    def test_encode_decode_audio(self):
        """Test that audio can be encoded and decoded"""
        # Create sample audio data
        original_audio = b"sample audio data" * 100

        # Encode
        encoded = AudioProcessor.encode_for_exotel(original_audio)
        assert isinstance(encoded, str)

        # Decode
        decoded = AudioProcessor.decode_exotel_audio(encoded)
        assert decoded == original_audio

    def test_chunk_audio(self):
        """Test audio chunking"""
        # Create 1 second of audio (16000 bytes for 8kHz 16-bit mono)
        audio_bytes = b"x" * 16000

        # Chunk into 100ms pieces
        chunks = AudioProcessor.chunk_audio(audio_bytes, chunk_duration_ms=100)

        # Should have 10 chunks (1000ms / 100ms)
        assert len(chunks) == 10

        # Each chunk should be ~1600 bytes (100ms worth)
        for chunk in chunks:
            assert len(chunk) == 1600

    def test_get_audio_duration(self):
        """Test audio duration calculation"""
        # 1 second of audio = 16000 bytes
        audio_bytes = b"x" * 16000

        duration_ms = AudioProcessor.get_audio_duration_ms(audio_bytes)
        assert duration_ms == 1000  # 1 second

        # 0.5 seconds
        audio_bytes = b"x" * 8000
        duration_ms = AudioProcessor.get_audio_duration_ms(audio_bytes)
        assert duration_ms == 500

    def test_decode_invalid_base64(self):
        """Test handling of invalid base64"""
        with pytest.raises(ValueError):
            AudioProcessor.decode_exotel_audio("not valid base64!!!")


class TestConversationStateMachine:
    """Test conversation state transitions"""

    def test_intro_to_discovery_transition(self):
        """Test transition from intro to discovery"""
        sm = ConversationStateMachine()

        # Valid transition
        assert sm.transition(
            ConversationStage.INTRO,
            ConversationStage.DISCOVERY,
            reason="User agreed to talk"
        )

        # Invalid transition
        assert not sm.transition(
            ConversationStage.INTRO,
            ConversationStage.CLOSING,
            reason="Cannot jump to closing"
        )

    def test_determine_next_stage_intro(self):
        """Test next stage determination from intro"""
        sm = ConversationStateMachine()

        # Positive response should go to discovery
        analysis = {
            "sentiment": "positive",
            "is_objection": False,
            "extracted_info": {"response": "yes"}
        }

        next_stage = sm.determine_next_stage(
            ConversationStage.INTRO,
            analysis,
            {}
        )

        assert next_stage == ConversationStage.DISCOVERY

    def test_determine_next_stage_objection(self):
        """Test objection handling"""
        sm = ConversationStateMachine()

        # Objection should transition to objection handling
        analysis = {
            "sentiment": "neutral",
            "is_objection": True,
            "objection_type": "budget"
        }

        next_stage = sm.determine_next_stage(
            ConversationStage.PRESENTATION,
            analysis,
            {}
        )

        assert next_stage == ConversationStage.OBJECTION_HANDLING

    def test_determine_next_stage_discovery_complete(self):
        """Test transition from discovery when all info collected"""
        sm = ConversationStateMachine()

        analysis = {
            "sentiment": "positive",
            "is_objection": False,
            "extracted_info": {}
        }

        # Without all required fields
        collected_data = {"purpose": "investment"}
        next_stage = sm.determine_next_stage(
            ConversationStage.DISCOVERY,
            analysis,
            collected_data
        )
        assert next_stage == ConversationStage.DISCOVERY

        # With all required fields
        collected_data = {
            "purpose": "investment",
            "budget_confirmed": True,
            "timeline": "3_months"
        }
        next_stage = sm.determine_next_stage(
            ConversationStage.DISCOVERY,
            analysis,
            collected_data
        )
        assert next_stage == ConversationStage.QUALIFICATION


class TestConversationSession:
    """Test conversation session model"""

    def test_create_session(self):
        """Test creating a conversation session"""
        session = ConversationSession(
            call_sid="test_call_123",
            lead_id=1,
            lead_name="John Doe",
            lead_phone="+919876543210",
            property_type="2BHK",
            location="Bangalore",
            budget=5000000.0
        )

        assert session.call_sid == "test_call_123"
        assert session.lead_name == "John Doe"
        assert session.conversation_stage == ConversationStage.INTRO
        assert session.is_bot_speaking is False
        assert session.waiting_for_response is True
        assert len(session.transcript_history) == 0

    def test_session_to_redis_dict(self):
        """Test converting session to Redis dict"""
        session = ConversationSession(
            call_sid="test_call_123",
            lead_id=1,
            lead_name="John Doe",
            lead_phone="+919876543210"
        )

        redis_dict = session.to_redis_dict()

        assert isinstance(redis_dict, dict)
        assert redis_dict["call_sid"] == "test_call_123"
        assert redis_dict["lead_name"] == "John Doe"
        assert isinstance(redis_dict["session_start_time"], str)

    def test_session_from_redis_dict(self):
        """Test creating session from Redis dict"""
        session = ConversationSession(
            call_sid="test_call_123",
            lead_id=1,
            lead_name="John Doe",
            lead_phone="+919876543210"
        )

        # Convert to dict and back
        redis_dict = session.to_redis_dict()
        restored_session = ConversationSession.from_redis_dict(redis_dict)

        assert restored_session.call_sid == session.call_sid
        assert restored_session.lead_name == session.lead_name
        assert restored_session.conversation_stage == session.conversation_stage


class TestPromptTemplates:
    """Test prompt template generation"""

    def test_get_intro_template(self):
        """Test intro template generation"""
        from src.conversation.prompt_templates import get_intro_template

        intro = get_intro_template(
            lead_name="Rajesh",
            property_type="3BHK apartment",
            location="Whitefield",
            budget="₹80 lakhs"
        )

        assert "Rajesh" in intro
        assert "3BHK apartment" in intro
        assert "Whitefield" in intro
        assert "80 lakhs" in intro
        assert "PropertyHub" in intro

    def test_get_objection_response_template(self):
        """Test objection response templates"""
        from src.conversation.prompt_templates import get_objection_response_template

        # Test budget objection
        response = get_objection_response_template("budget")
        assert "budget" in response.lower()
        assert "payment plans" in response.lower()

        # Test timing objection
        response = get_objection_response_template("timing")
        assert "price revision" in response.lower() or "timing" in response.lower()

        # Test unknown objection
        response = get_objection_response_template("unknown_type")
        assert len(response) > 0


@pytest.mark.asyncio
class TestSessionManager:
    """Test session management (requires Redis)"""

    async def test_session_lifecycle(self):
        """Test creating, updating, and deleting a session"""
        from src.websocket.session_manager import SessionManager

        manager = SessionManager()

        # Create session
        lead_context = {
            "lead_id": 123,
            "lead_name": "Test User",
            "phone": "+919876543210",
            "property_type": "2BHK",
            "location": "Bangalore",
            "budget": 5000000
        }

        session = await manager.create_session("test_call_456", lead_context)
        assert session.call_sid == "test_call_456"
        assert session.lead_name == "Test User"

        # Get session
        retrieved_session = await manager.get_session("test_call_456")
        assert retrieved_session is not None
        assert retrieved_session.lead_name == "Test User"

        # Update session
        await manager.update_session(
            "test_call_456",
            {"is_bot_speaking": True}
        )

        updated_session = await manager.get_session("test_call_456")
        assert updated_session.is_bot_speaking is True

        # Add to transcript
        await manager.add_to_transcript(
            "test_call_456",
            "ai",
            "Hello, how are you?"
        )

        session_with_transcript = await manager.get_session("test_call_456")
        assert len(session_with_transcript.transcript_history) == 1
        assert session_with_transcript.transcript_history[0]["speaker"] == "ai"

        # Delete session
        await manager.delete_session("test_call_456")

        deleted_session = await manager.get_session("test_call_456")
        assert deleted_session is None


# Integration test example (requires all services)
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires AI service credentials")
class TestFullConversationFlow:
    """Test complete conversation flow (integration test)"""

    async def test_conversation_intro_to_discovery(self):
        """Test conversation from intro through discovery"""
        from src.conversation.engine import ConversationEngine
        from src.models.conversation import ConversationSession

        engine = ConversationEngine()

        # Create session
        session = ConversationSession(
            call_sid="integration_test",
            lead_id=1,
            lead_name="Test Lead",
            lead_phone="+919876543210",
            property_type="2BHK",
            location="Bangalore",
            budget=5000000.0
        )

        # Generate intro
        intro = await engine.generate_intro(session)
        assert len(intro) > 0
        assert "Test Lead" in intro

        # Process positive response
        response, should_end, outcome = await engine.process_user_input(
            session,
            "Yes, I have time to talk"
        )

        assert not should_end
        assert session.conversation_stage in [
            ConversationStage.DISCOVERY,
            ConversationStage.PERMISSION
        ]
