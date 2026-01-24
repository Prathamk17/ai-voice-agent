"""
Tests for Exotel integration.
"""

import pytest
from src.integrations.exotel_client import ExotelClient, ExotelCallStatus


class TestExotelClient:
    """Test ExotelClient initialization and methods"""

    @pytest.mark.asyncio
    async def test_exotel_client_initialization(self):
        """Test Exotel client can be initialized"""
        client = ExotelClient(
            account_sid="test_sid",
            api_key="test_key",
            api_token="test_token",
            virtual_number="1234567890"
        )

        assert client.account_sid == "test_sid"
        assert client.api_key == "test_key"
        assert client.api_token == "test_token"
        assert client.virtual_number == "1234567890"
        assert client.base_url == "https://api.exotel.com/v1/Accounts/test_sid/"

        await client.close()

    @pytest.mark.asyncio
    async def test_exotel_client_uses_settings_by_default(self):
        """Test Exotel client uses settings when no params provided"""
        client = ExotelClient()

        # Should not raise an error even if settings are empty
        assert client.account_sid is not None
        assert client.base_url is not None

        await client.close()

    def test_exotel_call_status_constants(self):
        """Test ExotelCallStatus constants are defined correctly"""
        assert ExotelCallStatus.INITIATED == "initiated"
        assert ExotelCallStatus.RINGING == "ringing"
        assert ExotelCallStatus.IN_PROGRESS == "in-progress"
        assert ExotelCallStatus.COMPLETED == "completed"
        assert ExotelCallStatus.FAILED == "failed"
        assert ExotelCallStatus.BUSY == "busy"
        assert ExotelCallStatus.NO_ANSWER == "no-answer"
        assert ExotelCallStatus.CANCELLED == "cancelled"

    # NOTE: The following tests would require mocking the Exotel API
    # We don't want to make actual API calls in tests to avoid charges
    # In a real-world scenario, you would use pytest-mock or responses library
    # to mock the HTTP requests

    @pytest.mark.skip(reason="Requires mocking Exotel API - implement when needed")
    @pytest.mark.asyncio
    async def test_make_call_success(self):
        """Test making a call successfully"""
        # This would require mocking the Exotel API response
        pass

    @pytest.mark.skip(reason="Requires mocking Exotel API - implement when needed")
    @pytest.mark.asyncio
    async def test_make_call_failure(self):
        """Test handling call failure"""
        # This would require mocking the Exotel API error response
        pass

    @pytest.mark.skip(reason="Requires mocking Exotel API - implement when needed")
    @pytest.mark.asyncio
    async def test_get_call_details(self):
        """Test getting call details"""
        # This would require mocking the Exotel API response
        pass
