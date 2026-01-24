"""
Tests for Call Scheduler service.
"""

import pytest
from datetime import datetime, timedelta
from src.services.call_scheduler import CallScheduler
from src.models.scheduled_call import ScheduledCallStatus


class TestCallScheduler:
    """Test CallScheduler service"""

    def test_get_next_available_slot_within_hours(self):
        """Test scheduling within calling hours"""
        scheduler = CallScheduler(db_session=None)

        # Test at 2 PM (within 10 AM - 7 PM)
        test_time = datetime(2024, 1, 15, 14, 30)  # Monday 2:30 PM
        result = scheduler._get_next_available_slot(
            test_time,
            calling_hours_start=10,
            calling_hours_end=19
        )

        # Should return the same time (within calling hours)
        assert result.hour >= 10
        assert result.hour < 19

    def test_get_next_available_slot_before_hours(self):
        """Test scheduling before calling hours"""
        scheduler = CallScheduler(db_session=None)

        # Test at 8 AM (before 10 AM)
        test_time = datetime(2024, 1, 15, 8, 0)  # Monday 8:00 AM
        result = scheduler._get_next_available_slot(
            test_time,
            calling_hours_start=10,
            calling_hours_end=19
        )

        # Should schedule for 10 AM today
        assert result.hour == 10
        assert result.minute == 0
        assert result.day == test_time.day

    def test_get_next_available_slot_after_hours(self):
        """Test scheduling after calling hours"""
        scheduler = CallScheduler(db_session=None)

        # Test at 8 PM (after 7 PM)
        test_time = datetime(2024, 1, 15, 20, 0)  # Monday 8:00 PM
        result = scheduler._get_next_available_slot(
            test_time,
            calling_hours_start=10,
            calling_hours_end=19
        )

        # Should schedule for 10 AM next day
        assert result.hour == 10
        assert result.minute == 0
        assert result.day == test_time.day + 1

    def test_get_next_available_slot_skip_sunday(self):
        """Test that Sunday is skipped"""
        scheduler = CallScheduler(db_session=None)

        # Test on Saturday evening
        test_time = datetime(2024, 1, 20, 20, 0)  # Saturday 8:00 PM
        # Next day would be Sunday, should skip to Monday
        result = scheduler._get_next_available_slot(
            test_time,
            calling_hours_start=10,
            calling_hours_end=19
        )

        # Should skip Sunday and schedule for Monday
        assert result.weekday() != 6  # Not Sunday
        assert result.hour == 10

    def test_scheduled_call_status_enum(self):
        """Test ScheduledCallStatus enum values"""
        assert ScheduledCallStatus.PENDING == "pending"
        assert ScheduledCallStatus.CALLING == "calling"
        assert ScheduledCallStatus.COMPLETED == "completed"
        assert ScheduledCallStatus.FAILED == "failed"
        assert ScheduledCallStatus.CANCELLED == "cancelled"
        assert ScheduledCallStatus.MAX_RETRIES_REACHED == "max_retries_reached"

    # NOTE: The following tests would require a test database
    # They are marked as skip for now but should be implemented with proper DB fixtures

    @pytest.mark.skip(reason="Requires test database setup")
    @pytest.mark.asyncio
    async def test_schedule_campaign_calls(self):
        """Test scheduling calls for a campaign"""
        # This would require:
        # 1. Test database setup
        # 2. Creating test campaign
        # 3. Creating test leads
        # 4. Verifying scheduled_calls are created
        pass

    @pytest.mark.skip(reason="Requires test database setup")
    @pytest.mark.asyncio
    async def test_get_pending_calls_respects_calling_hours(self):
        """Test that pending calls are only returned during calling hours"""
        # This would require:
        # 1. Test database setup
        # 2. Creating scheduled calls
        # 3. Testing at different times of day
        pass

    @pytest.mark.skip(reason="Requires test database setup")
    @pytest.mark.asyncio
    async def test_get_pending_calls_respects_concurrency(self):
        """Test that concurrency limits are respected"""
        # This would require:
        # 1. Test database setup
        # 2. Creating multiple scheduled calls
        # 3. Some marked as CALLING
        # 4. Verifying only allowed number are returned
        pass

    @pytest.mark.skip(reason="Requires test database setup")
    @pytest.mark.asyncio
    async def test_schedule_retry_increments_attempt(self):
        """Test that retry scheduling increments attempt number"""
        # This would require:
        # 1. Test database setup
        # 2. Creating a failed scheduled call
        # 3. Calling schedule_retry
        # 4. Verifying attempt_number increases
        pass

    @pytest.mark.skip(reason="Requires test database setup")
    @pytest.mark.asyncio
    async def test_schedule_retry_max_retries_reached(self):
        """Test that max retries stops scheduling"""
        # This would require:
        # 1. Test database setup
        # 2. Creating a scheduled call at max attempts
        # 3. Calling schedule_retry
        # 4. Verifying status changes to MAX_RETRIES_REACHED
        pass
