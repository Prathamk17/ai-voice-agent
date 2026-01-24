"""
Lead data model for real estate leads from CSV upload.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from enum import Enum
from typing import Optional, List

from src.database.connection import Base


class LeadSource(str, Enum):
    """Source of the lead"""
    WEBSITE = "website"
    REFERRAL = "referral"
    ADVERTISEMENT = "advertisement"
    PARTNER = "partner"


class Lead(Base):
    """
    Represents a real estate lead from CSV upload.
    Each lead contains contact information and property preferences.
    """
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Contact Information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Property Preferences (from CSV)
    property_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 2BHK, 3BHK, etc.
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Lead Metadata
    source: Mapped[str] = mapped_column(SQLEnum(LeadSource), nullable=False)
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # JSON string
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Additional notes about the lead
    campaign_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("campaigns.id"),
        nullable=True,
        index=True
    )

    # Call Tracking
    call_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_call_attempt: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    call_sessions: Mapped[List["CallSession"]] = relationship(
        "CallSession",
        back_populates="lead",
        cascade="all, delete-orphan"
    )

    campaign: Mapped[Optional["Campaign"]] = relationship(
        "Campaign",
        back_populates="leads"
    )

    def __repr__(self):
        return f"<Lead(id={self.id}, name={self.name}, phone={self.phone})>"
