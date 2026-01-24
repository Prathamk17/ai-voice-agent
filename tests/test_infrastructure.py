"""
Infrastructure tests for Module 1.
Tests configuration, models, and basic application setup.
"""

import pytest
from datetime import datetime

from src.config.settings import Settings
from src.models.lead import Lead, LeadSource
from src.models.call_session import CallSession, CallStatus, CallOutcome
from src.models.conversation import ConversationSession, ConversationStage


class TestSettings:
    """Test configuration management"""

    def test_settings_load(self):
        """Test that settings load correctly from environment"""
        settings = Settings()
        assert settings.APP_NAME is not None
        assert settings.PORT == 8000
        assert settings.ENVIRONMENT in ["development", "staging", "production"]

    def test_settings_defaults(self):
        """Test default values"""
        settings = Settings()
        assert settings.HOST == "0.0.0.0"
        assert settings.MAX_CALL_DURATION_MINUTES == 10
        assert settings.CALLING_HOURS_START == 10
        assert settings.CALLING_HOURS_END == 19
        assert settings.MAX_CONCURRENT_CALLS == 10

    def test_database_url_required(self):
        """Test that DATABASE_URL is required"""
        settings = Settings()
        assert settings.DATABASE_URL is not None
        assert "postgresql" in settings.DATABASE_URL


class TestLeadModel:
    """Test Lead model"""

    def test_lead_source_enum(self):
        """Test LeadSource enum values"""
        assert LeadSource.WEBSITE == "website"
        assert LeadSource.REFERRAL == "referral"
        assert LeadSource.ADVERTISEMENT == "advertisement"
        assert LeadSource.PARTNER == "partner"

    def test_lead_model_attributes(self):
        """Test Lead model has required attributes"""
        # Just verify the model class exists and has expected attributes
        assert hasattr(Lead, '__tablename__')
        assert Lead.__tablename__ == "leads"
        assert hasattr(Lead, 'name')
        assert hasattr(Lead, 'phone')
        assert hasattr(Lead, 'email')
        assert hasattr(Lead, 'property_type')
        assert hasattr(Lead, 'location')
        assert hasattr(Lead, 'budget')
        assert hasattr(Lead, 'source')
        assert hasattr(Lead, 'call_attempts')


class TestCallSessionModel:
    """Test CallSession model"""

    def test_call_status_enum(self):
        """Test CallStatus enum values"""
        assert CallStatus.INITIATED == "initiated"
        assert CallStatus.RINGING == "ringing"
        assert CallStatus.IN_PROGRESS == "in_progress"
        assert CallStatus.COMPLETED == "completed"
        assert CallStatus.FAILED == "failed"
        assert CallStatus.NO_ANSWER == "no_answer"
        assert CallStatus.BUSY == "busy"

    def test_call_outcome_enum(self):
        """Test CallOutcome enum values"""
        assert CallOutcome.QUALIFIED == "qualified"
        assert CallOutcome.NOT_INTERESTED == "not_interested"
        assert CallOutcome.CALLBACK_REQUESTED == "callback_requested"
        assert CallOutcome.NO_ANSWER == "no_answer"
        assert CallOutcome.DISCONNECTED == "disconnected"
        assert CallOutcome.ERROR == "error"

    def test_call_session_model_attributes(self):
        """Test CallSession model has required attributes"""
        assert hasattr(CallSession, '__tablename__')
        assert CallSession.__tablename__ == "call_sessions"
        assert hasattr(CallSession, 'call_sid')
        assert hasattr(CallSession, 'lead_id')
        assert hasattr(CallSession, 'status')
        assert hasattr(CallSession, 'outcome')
        assert hasattr(CallSession, 'duration_seconds')


class TestConversationModel:
    """Test ConversationSession Pydantic model"""

    def test_conversation_stage_enum(self):
        """Test ConversationStage enum values"""
        assert ConversationStage.INTRO == "intro"
        assert ConversationStage.PERMISSION == "permission"
        assert ConversationStage.DISCOVERY == "discovery"
        assert ConversationStage.QUALIFICATION == "qualification"
        assert ConversationStage.PRESENTATION == "presentation"
        assert ConversationStage.CLOSING == "closing"

    def test_conversation_session_creation(self):
        """Test ConversationSession model creation"""
        session = ConversationSession(
            call_sid="test_123",
            lead_id=1,
            lead_name="Test User",
            lead_phone="+919876543210"
        )

        assert session.call_sid == "test_123"
        assert session.lead_id == 1
        assert session.lead_name == "Test User"
        assert session.lead_phone == "+919876543210"
        assert session.conversation_stage == ConversationStage.INTRO
        assert session.waiting_for_response is True
        assert len(session.transcript_history) == 0
        assert session.is_bot_speaking is False
        assert session.escalation_requested is False

    def test_conversation_session_defaults(self):
        """Test ConversationSession default values"""
        session = ConversationSession(
            call_sid="test_123",
            lead_id=1,
            lead_name="Test User",
            lead_phone="+919876543210"
        )

        assert session.audio_buffer == b""
        assert isinstance(session.transcript_history, list)
        assert isinstance(session.collected_data, dict)
        assert isinstance(session.objections_encountered, list)
        assert session.close_attempts == 0
        assert isinstance(session.session_start_time, datetime)
        assert isinstance(session.last_interaction_time, datetime)

    def test_conversation_session_with_data(self):
        """Test ConversationSession with collected data"""
        session = ConversationSession(
            call_sid="test_123",
            lead_id=1,
            lead_name="Test User",
            lead_phone="+919876543210",
            property_type="3BHK",
            location="Mumbai",
            budget=5000000.0
        )

        assert session.property_type == "3BHK"
        assert session.location == "Mumbai"
        assert session.budget == 5000000.0

    def test_conversation_session_to_redis_dict(self):
        """Test conversion to Redis dictionary"""
        session = ConversationSession(
            call_sid="test_123",
            lead_id=1,
            lead_name="Test User",
            lead_phone="+919876543210"
        )

        redis_dict = session.to_redis_dict()

        assert isinstance(redis_dict, dict)
        assert redis_dict['call_sid'] == "test_123"
        assert redis_dict['lead_id'] == 1
        assert 'session_start_time' in redis_dict
        assert isinstance(redis_dict['session_start_time'], str)  # ISO format
        assert redis_dict['audio_buffer'] == ""  # Empty hex string

    def test_conversation_session_from_redis_dict(self):
        """Test creation from Redis dictionary"""
        session = ConversationSession(
            call_sid="test_123",
            lead_id=1,
            lead_name="Test User",
            lead_phone="+919876543210"
        )

        redis_dict = session.to_redis_dict()
        restored_session = ConversationSession.from_redis_dict(redis_dict)

        assert restored_session.call_sid == session.call_sid
        assert restored_session.lead_id == session.lead_id
        assert restored_session.lead_name == session.lead_name
        assert restored_session.conversation_stage == session.conversation_stage


class TestLogger:
    """Test logging utility"""

    def test_logger_import(self):
        """Test that logger can be imported"""
        from src.utils.logger import StructuredLogger, get_logger

        logger = get_logger(__name__)
        assert isinstance(logger, StructuredLogger)

    def test_logger_methods(self):
        """Test logger has all required methods"""
        from src.utils.logger import get_logger

        logger = get_logger(__name__)
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'critical')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
