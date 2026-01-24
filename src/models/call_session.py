"""
Call session model representing a single call attempt and its outcome.
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from enum import Enum
from typing import Optional

from src.database.connection import Base


class CallStatus(str, Enum):
    """Status of the call"""
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"


class CallOutcome(str, Enum):
    """Outcome of the call conversation"""
    QUALIFIED = "qualified"
    NOT_INTERESTED = "not_interested"
    CALLBACK_REQUESTED = "callback_requested"
    NO_ANSWER = "no_answer"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class CallSession(Base):
    """
    Represents a single call attempt and its outcome.
    Tracks the entire lifecycle of a call from initiation to completion.
    """
    __tablename__ = "call_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Identifiers
    call_sid: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True, nullable=False)

    # Call Details
    status: Mapped[str] = mapped_column(SQLEnum(CallStatus), nullable=False)
    outcome: Mapped[Optional[str]] = mapped_column(SQLEnum(CallOutcome), nullable=True)

    # Duration
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Conversation Data
    full_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    collected_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string

    # Recording
    recording_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    lead: Mapped["Lead"] = relationship("Lead", back_populates="call_sessions")

    def __repr__(self):
        return f"<CallSession(id={self.id}, call_sid={self.call_sid}, status={self.status})>"
