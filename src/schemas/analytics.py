"""
Analytics and Metrics Schemas

Module 5: Dashboard, Analytics & Monitoring
Pydantic schemas for analytics data, metrics, and reports.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, date


class CampaignMetrics(BaseModel):
    """Metrics for a single campaign"""
    campaign_id: int
    campaign_name: str

    # Lead metrics
    total_leads: int
    valid_leads: int
    dnc_filtered: int

    # Call metrics
    calls_initiated: int
    calls_completed: int
    calls_in_progress: int
    calls_pending: int

    # Outcome metrics
    calls_qualified: int
    calls_not_interested: int
    calls_no_answer: int
    calls_busy: int
    calls_failed: int

    # Calculated metrics
    answer_rate: float = Field(default=0.0)  # % of calls answered
    qualification_rate: float = Field(default=0.0)  # % of completed calls that qualified
    conversion_rate: float = Field(default=0.0)  # % of total leads qualified

    # Time metrics
    avg_call_duration_seconds: Optional[float] = None
    total_call_time_minutes: Optional[float] = None

    # Status
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DailyStats(BaseModel):
    """Daily statistics"""
    date: date
    calls_made: int
    calls_answered: int
    calls_qualified: int
    total_duration_minutes: float
    avg_duration_seconds: float


class ConversationMetrics(BaseModel):
    """Metrics for conversation quality"""
    call_sid: str
    lead_name: str

    # Conversation details
    duration_seconds: int
    total_exchanges: int  # Number of back-and-forth
    stages_reached: List[str]

    # Objections
    objections_encountered: List[str]
    objections_count: int

    # Outcome
    outcome: str
    qualification_score: Optional[float] = None

    # Timestamps
    started_at: datetime
    ended_at: datetime


class SystemMetrics(BaseModel):
    """System-wide metrics"""
    # Overall stats
    total_campaigns: int
    active_campaigns: int
    total_leads: int
    total_calls_today: int

    # Current status
    calls_in_progress: int
    calls_queued: int

    # Success rates
    overall_answer_rate: float
    overall_qualification_rate: float

    # System health
    redis_connected: bool
    database_connected: bool
    exotel_api_healthy: bool


class LeadActivity(BaseModel):
    """Recent activity for a lead"""
    lead_id: int
    lead_name: str
    phone: str
    property_type: str
    location: str

    # Call history
    total_attempts: int
    last_attempt: Optional[datetime] = None
    last_outcome: Optional[str] = None

    # Status
    current_status: str  # pending, qualified, not_interested, etc.
    next_action: Optional[str] = None
    next_scheduled_call: Optional[datetime] = None


class ExportRequest(BaseModel):
    """Request for data export"""
    export_type: str  # "campaign_results", "call_transcripts", "lead_list"
    campaign_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    format: str = "csv"  # csv or xlsx
