"""
Scheduled Call model for tracking call scheduling and retries.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from enum import Enum
from typing import Optional

from src.database.connection import Base


class ScheduledCallStatus(str, Enum):
    """Scheduled call status enum"""
    PENDING = "pending"          # Queued for calling
    CALLING = "calling"          # Call in progress
    COMPLETED = "completed"      # Call completed
    FAILED = "failed"           # Call failed (will retry)
    CANCELLED = "cancelled"      # Manually cancelled
    MAX_RETRIES_REACHED = "max_retries_reached"  # Exhausted retries


class ScheduledCall(Base):
    """
    Represents a scheduled call to a lead
    Tracks retry attempts and scheduling
    """
    __tablename__ = "scheduled_calls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # References
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True, nullable=False)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True, nullable=False)

    # Scheduling
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        SQLEnum(ScheduledCallStatus),
        default=ScheduledCallStatus.PENDING,
        nullable=False,
        index=True
    )

    # Retry tracking
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    last_attempt_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Call tracking
    current_call_sid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_call_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Failure tracking
    failure_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign")
    lead: Mapped["Lead"] = relationship("Lead")

    def __repr__(self):
        return f"<ScheduledCall(id={self.id}, lead_id={self.lead_id}, status={self.status}, attempt={self.attempt_number})>"
