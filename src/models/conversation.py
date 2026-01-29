"""
Conversation state model for active call sessions.
This is stored in Redis, not in the database.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ConversationStage(str, Enum):
    """Stages of the sales conversation"""
    INTRO = "intro"
    PERMISSION = "permission"
    DISCOVERY = "discovery"
    QUALIFICATION = "qualification"
    PRESENTATION = "presentation"
    OBJECTION_HANDLING = "objection_handling"
    TRIAL_CLOSE = "trial_close"
    CLOSING = "closing"
    FOLLOW_UP_SCHEDULED = "follow_up_scheduled"
    DEAL_CLOSED = "deal_closed"
    DEAD_END = "dead_end"


class ConversationSession(BaseModel):
    """
    In-memory conversation state stored in Redis during active calls.
    This model is NOT a database table - it represents the real-time state
    of an ongoing conversation.
    """

    # Session Identifiers
    call_sid: str
    lead_id: int

    # Lead Context
    lead_name: str
    lead_phone: str
    property_type: Optional[str] = None
    location: Optional[str] = None
    budget: Optional[float] = None
    source: Optional[str] = None

    # Conversation State
    conversation_stage: ConversationStage = ConversationStage.INTRO

    # Audio Buffers (stored as empty bytes by default, populated during call)
    audio_buffer: bytes = b""

    # Voice Activity Detection (for silence detection)
    silence_chunks: int = 0
    last_voice_time: float = 0.0

    # Conversation History
    transcript_history: List[Dict[str, str]] = Field(default_factory=list)
    # Format: [{"speaker": "ai", "text": "...", "timestamp": "..."}, ...]

    # Context Tracking (for better turn-taking and response understanding)
    last_agent_question: Optional[str] = None  # Track the last question asked
    last_agent_question_type: Optional[str] = None  # "purpose", "budget", "timeline", etc.
    customer_mid_sentence: bool = False  # Flag if customer seems to be mid-thought

    # Collected Information during the call
    collected_data: Dict[str, Any] = Field(default_factory=dict)
    # e.g., {"purpose": "end_user", "budget_confirmed": 5000000, "timeline": "3_months"}

    # State Flags
    is_bot_speaking: bool = False
    waiting_for_response: bool = True
    should_stop_speaking: bool = False  # Set to True when user interrupts
    escalation_requested: bool = False

    # Metrics
    objections_encountered: List[str] = Field(default_factory=list)
    close_attempts: int = 0

    # Timing
    session_start_time: datetime = Field(default_factory=datetime.utcnow)
    last_interaction_time: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True  # Allow bytes type

    def to_redis_dict(self) -> dict:
        """Convert to dictionary for Redis storage"""
        data = self.model_dump()
        # Convert datetime to ISO format
        data['session_start_time'] = data['session_start_time'].isoformat()
        data['last_interaction_time'] = data['last_interaction_time'].isoformat()
        # Convert bytes to hex string for storage
        data['audio_buffer'] = data['audio_buffer'].hex() if data['audio_buffer'] else ""
        return data

    @classmethod
    def from_redis_dict(cls, data: dict) -> "ConversationSession":
        """Create instance from Redis dictionary"""
        # Convert ISO format back to datetime
        data['session_start_time'] = datetime.fromisoformat(data['session_start_time'])
        data['last_interaction_time'] = datetime.fromisoformat(data['last_interaction_time'])
        # Convert hex string back to bytes
        data['audio_buffer'] = bytes.fromhex(data['audio_buffer']) if data['audio_buffer'] else b""
        return cls(**data)
