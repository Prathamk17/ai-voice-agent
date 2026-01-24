"""Campaign model for managing outbound calling campaigns."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    String, Integer, DateTime, Text, Boolean, Enum as SQLEnum, Float
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.database.connection import Base


class CampaignStatus(str, Enum):
    """Campaign status enum."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Campaign(Base):
    """
    Campaign model for managing lead calling campaigns.

    Tracks campaign metadata, scheduling, and performance metrics.
    """
    __tablename__ = "campaigns"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Campaign Details
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        SQLEnum(CampaignStatus),
        default=CampaignStatus.DRAFT,
        nullable=False,
        index=True
    )

    # Scheduling
    scheduled_start_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    scheduled_end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    actual_start_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    actual_end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Campaign Settings
    max_attempts_per_lead: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False
    )
    retry_delay_hours: Mapped[int] = mapped_column(
        Integer,
        default=24,
        nullable=False
    )
    calling_hours_start: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False
    )
    calling_hours_end: Mapped[int] = mapped_column(
        Integer,
        default=19,
        nullable=False
    )
    max_concurrent_calls: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False
    )

    # Script Configuration
    script_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    qualification_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Performance Metrics
    total_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_called: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_qualified: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_call_duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Success Metrics
    success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    qualification_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    average_call_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Control Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    leads: Mapped[list["Lead"]] = relationship(
        "Lead",
        back_populates="campaign",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"

    def calculate_metrics(self) -> None:
        """Calculate and update campaign metrics."""
        if self.leads_called > 0:
            self.success_rate = (self.leads_completed / self.leads_called) * 100

        if self.leads_completed > 0:
            self.qualification_rate = (self.leads_qualified / self.leads_completed) * 100

        if self.leads_called > 0:
            self.average_call_duration = (
                self.total_call_duration_seconds / self.leads_called
            )
