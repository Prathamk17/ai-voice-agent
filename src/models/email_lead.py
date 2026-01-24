"""
Email Lead models for parsing lead information from emails.
Supports MagicBricks, 99Acres, and other real estate platforms.
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import re


class EmailLead(BaseModel):
    """
    Parsed lead information from email notification.

    This model represents a lead extracted from an email notification
    from real estate platforms like MagicBricks or 99Acres.
    """

    # Lead Information
    name: str
    phone: str
    email: Optional[EmailStr] = None

    # Property Details
    property_type: Optional[str] = None  # e.g., "2BHK", "3BHK", "Villa"
    location: Optional[str] = None  # e.g., "Gurgaon", "Noida"
    budget: Optional[int] = None  # Budget in INR

    # Source Information
    source: str  # "magicbricks", "99acres", "website", etc.
    source_url: Optional[str] = None  # Original listing URL if available

    # Email Metadata
    email_subject: str
    email_received_at: datetime
    email_message_id: str  # Unique email ID to prevent duplicates

    # Additional Details
    message: Optional[str] = None  # Any additional message from the lead
    tags: Optional[str] = None  # Comma-separated tags

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate and format Indian phone number."""
        if not v:
            raise ValueError("Phone number is required")

        # Remove all non-digit characters
        phone = re.sub(r'\D', '', v)

        # Handle different formats
        if len(phone) == 10:  # 10-digit number
            return f"+91{phone}"
        elif len(phone) == 11 and phone.startswith('0'):  # 0XXXXXXXXXX
            return f"+91{phone[1:]}"
        elif len(phone) == 12 and phone.startswith('91'):  # 91XXXXXXXXXX
            return f"+{phone}"
        elif len(phone) == 13 and phone.startswith('91'):  # +91XXXXXXXXXX (already formatted)
            return f"+{phone}"
        else:
            raise ValueError(f"Invalid Indian phone number: {v}")

    @field_validator('property_type')
    @classmethod
    def normalize_property_type(cls, v: Optional[str]) -> Optional[str]:
        """Normalize property type to uppercase."""
        if v:
            return v.upper()
        return v

    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate and normalize source."""
        valid_sources = ['magicbricks', '99acres', 'housing', 'website', 'referral', 'other']
        v_lower = v.lower()

        # Map common variations
        if 'magic' in v_lower or 'mb' in v_lower:
            return 'magicbricks'
        elif '99' in v_lower or 'acre' in v_lower:
            return '99acres'
        elif 'housing.com' in v_lower:
            return 'housing'
        elif v_lower in valid_sources:
            return v_lower
        else:
            return 'other'

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Rajesh Kumar",
                "phone": "9876543210",
                "email": "rajesh@example.com",
                "property_type": "2BHK",
                "location": "Gurgaon",
                "budget": 5000000,
                "source": "magicbricks",
                "source_url": "https://www.magicbricks.com/property/...",
                "email_subject": "New Lead: Rajesh Kumar interested in 2BHK in Gurgaon",
                "email_received_at": "2024-01-20T10:30:00",
                "email_message_id": "msg123456",
                "message": "Looking for 2BHK apartment in Gurgaon",
                "tags": "first-time-buyer,urgent"
            }
        }


class ParsedEmailResult(BaseModel):
    """Result of email parsing operation."""

    success: bool
    lead: Optional[EmailLead] = None
    error: Optional[str] = None
    raw_email_subject: str
    raw_email_body: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "lead": {
                    "name": "Rajesh Kumar",
                    "phone": "+919876543210",
                    "email": "rajesh@example.com",
                    "property_type": "2BHK",
                    "location": "Gurgaon",
                    "source": "magicbricks",
                    "email_subject": "New Lead from MagicBricks",
                    "email_received_at": "2024-01-20T10:30:00",
                    "email_message_id": "msg123456"
                },
                "error": None,
                "raw_email_subject": "New Lead from MagicBricks",
                "raw_email_body": "Name: Rajesh Kumar..."
            }
        }
