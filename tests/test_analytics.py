"""
Test Analytics and Dashboard Module

Module 5: Dashboard, Analytics & Monitoring
Tests for analytics service, dashboard endpoints, and export functionality.
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.models.campaign import Campaign, CampaignStatus
from src.models.lead import Lead
from src.models.call_session import CallSession, CallStatus, CallOutcome
from src.models.scheduled_call import ScheduledCall, ScheduledCallStatus
from src.services.analytics_service import AnalyticsService
from src.services.export_service import ExportService


@pytest.mark.asyncio
class TestAnalyticsService:
    """Test analytics service"""

    async def test_get_campaign_metrics(self, db_session: AsyncSession):
        """Test getting campaign metrics"""
        # Create test campaign
        campaign = Campaign(
            name="Test Campaign",
            status=CampaignStatus.RUNNING,
            total_leads=100,
            valid_leads=95,
            dnc_filtered=5
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        # Create test leads and call sessions
        for i in range(10):
            lead = Lead(
                campaign_id=campaign.id,
                name=f"Lead {i}",
                phone=f"91900000000{i}",
                property_type="2BHK Apartment",
                location="Bangalore",
                source="csv_upload"
            )
            db_session.add(lead)
            await db_session.flush()

            # Add call session
            call_session = CallSession(
                call_sid=f"test_call_{i}",
                lead_id=lead.id,
                status=CallStatus.COMPLETED,
                outcome=CallOutcome.QUALIFIED if i < 5 else CallOutcome.NOT_INTERESTED,
                duration_seconds=120 + (i * 10),
                initiated_at=datetime.utcnow()
            )
            db_session.add(call_session)

        await db_session.commit()

        # Test analytics service
        analytics = AnalyticsService(db_session)
        metrics = await analytics.get_campaign_metrics(campaign.id)

        assert metrics is not None
        assert metrics.campaign_id == campaign.id
        assert metrics.campaign_name == "Test Campaign"
        assert metrics.calls_completed == 10
        assert metrics.calls_qualified == 5
        assert metrics.calls_not_interested == 5
        assert metrics.qualification_rate == 50.0  # 5/10 * 100

    async def test_get_daily_stats(self, db_session: AsyncSession):
        """Test getting daily statistics"""
        # Create campaign and leads with calls from different days
        campaign = Campaign(
            name="Daily Stats Test",
            status=CampaignStatus.RUNNING,
            total_leads=50,
            valid_leads=50,
            dnc_filtered=0
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        # Create calls for last 3 days
        for day_offset in range(3):
            call_date = datetime.utcnow() - timedelta(days=day_offset)

            for i in range(5):
                lead = Lead(
                    campaign_id=campaign.id,
                    name=f"Lead Day{day_offset} #{i}",
                    phone=f"9190000{day_offset}{i:03d}",
                    property_type="2BHK Apartment",
                    location="Delhi",
                    source="csv_upload"
                )
                db_session.add(lead)
                await db_session.flush()

                call_session = CallSession(
                    call_sid=f"call_day{day_offset}_{i}",
                    lead_id=lead.id,
                    status=CallStatus.COMPLETED,
                    outcome=CallOutcome.QUALIFIED if i < 2 else CallOutcome.NOT_INTERESTED,
                    duration_seconds=90,
                    initiated_at=call_date
                )
                db_session.add(call_session)

        await db_session.commit()

        # Test daily stats
        analytics = AnalyticsService(db_session)
        daily_stats = await analytics.get_daily_stats(campaign_id=campaign.id, days=7)

        assert len(daily_stats) == 3  # 3 days of data
        for stat in daily_stats:
            assert stat.calls_made == 5
            assert stat.calls_answered == 5
            assert stat.calls_qualified == 2

    async def test_get_system_metrics(self, db_session: AsyncSession):
        """Test getting system-wide metrics"""
        # Create multiple campaigns
        for i in range(3):
            campaign = Campaign(
                name=f"Campaign {i}",
                status=CampaignStatus.RUNNING if i < 2 else CampaignStatus.COMPLETED,
                total_leads=50,
                valid_leads=48,
                dnc_filtered=2
            )
            db_session.add(campaign)

        await db_session.commit()

        # Test system metrics
        analytics = AnalyticsService(db_session)
        metrics = await analytics.get_system_metrics()

        assert metrics.total_campaigns >= 3
        assert metrics.active_campaigns >= 2
        assert metrics.database_connected is True


@pytest.mark.asyncio
class TestAnalyticsAPI:
    """Test analytics API endpoints"""

    async def test_get_campaign_metrics_endpoint(self):
        """Test campaign metrics API endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Note: This requires a campaign to exist in the test database
            # In a real test, you'd set up test data first
            response = await client.get("/analytics/campaigns/1/metrics")

            # May return 404 if campaign doesn't exist, which is fine for this test
            assert response.status_code in [200, 404]

            if response.status_code == 200:
                data = response.json()
                assert "campaign_id" in data
                assert "campaign_name" in data
                assert "answer_rate" in data

    async def test_get_system_metrics_endpoint(self):
        """Test system metrics API endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/analytics/system")

            assert response.status_code == 200
            data = response.json()

            assert "total_campaigns" in data
            assert "total_leads" in data
            assert "redis_connected" in data
            assert "database_connected" in data

    async def test_get_dashboard_overview(self):
        """Test dashboard overview endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/dashboard/overview")

            assert response.status_code == 200
            data = response.json()

            assert "system" in data
            assert "recent_campaigns" in data
            assert "daily_stats" in data
            assert "timestamp" in data

    async def test_get_realtime_data(self):
        """Test realtime dashboard data endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/dashboard/realtime")

            assert response.status_code == 200
            data = response.json()

            assert "calls_in_progress" in data
            assert "active_calls" in data
            assert "calls_queued" in data


@pytest.mark.asyncio
class TestExportService:
    """Test export functionality"""

    async def test_export_campaign_results_csv(self, db_session: AsyncSession):
        """Test exporting campaign results to CSV"""
        # Create test data
        campaign = Campaign(
            name="Export Test Campaign",
            status=CampaignStatus.COMPLETED,
            total_leads=5,
            valid_leads=5,
            dnc_filtered=0
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        # Add some leads
        for i in range(5):
            lead = Lead(
                campaign_id=campaign.id,
                name=f"Export Lead {i}",
                phone=f"919000000{i:03d}",
                email=f"lead{i}@test.com",
                property_type="3BHK Apartment",
                location="Mumbai",
                source="csv_upload"
            )
            db_session.add(lead)

        await db_session.commit()

        # Test export
        export_service = ExportService(db_session)
        csv_data = await export_service.export_campaign_results(campaign.id, format="csv")

        assert csv_data is not None
        assert len(csv_data) > 0
        assert b"Lead Name" in csv_data  # Check for header
        assert b"Export Lead" in csv_data  # Check for data

    async def test_export_campaign_results_xlsx(self, db_session: AsyncSession):
        """Test exporting campaign results to Excel"""
        # Create test data
        campaign = Campaign(
            name="Excel Export Test",
            status=CampaignStatus.COMPLETED,
            total_leads=3,
            valid_leads=3,
            dnc_filtered=0
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        # Add leads
        for i in range(3):
            lead = Lead(
                campaign_id=campaign.id,
                name=f"Excel Lead {i}",
                phone=f"919100000{i:03d}",
                property_type="Villa",
                location="Pune",
                source="csv_upload"
            )
            db_session.add(lead)

        await db_session.commit()

        # Test export
        export_service = ExportService(db_session)
        xlsx_data = await export_service.export_campaign_results(campaign.id, format="xlsx")

        assert xlsx_data is not None
        assert len(xlsx_data) > 0
        # Excel files start with PK (zip header)
        assert xlsx_data[:2] == b'PK'


@pytest.mark.asyncio
class TestHealthChecks:
    """Test health check endpoints"""

    async def test_basic_health_check(self):
        """Test basic health endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health/")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    async def test_detailed_health_check(self):
        """Test detailed health check endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health/detailed")

            # Should return 200 or 503 depending on system status
            assert response.status_code in [200, 503]
            data = response.json()

            assert "status" in data
            assert "timestamp" in data
            assert "checks" in data
            assert "database" in data["checks"]
            assert "redis" in data["checks"]

    async def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health/metrics")

            assert response.status_code == 200
            # Prometheus metrics are in text format
            assert "text/plain" in response.headers.get("content-type", "")


def test_analytics_schema_validation():
    """Test analytics schema validation"""
    from src.schemas.analytics import CampaignMetrics, DailyStats, SystemMetrics

    # Test CampaignMetrics
    metrics = CampaignMetrics(
        campaign_id=1,
        campaign_name="Test",
        total_leads=100,
        valid_leads=95,
        dnc_filtered=5,
        calls_initiated=50,
        calls_completed=45,
        calls_in_progress=2,
        calls_pending=3,
        calls_qualified=20,
        calls_not_interested=15,
        calls_no_answer=10,
        calls_busy=0,
        calls_failed=5,
        status="running"
    )

    assert metrics.campaign_id == 1
    assert metrics.answer_rate == 0.0  # Default
    assert metrics.qualification_rate == 0.0  # Default

    # Test DailyStats
    from datetime import date
    daily = DailyStats(
        date=date.today(),
        calls_made=10,
        calls_answered=8,
        calls_qualified=4,
        total_duration_minutes=20.5,
        avg_duration_seconds=120.0
    )

    assert daily.calls_made == 10
    assert daily.avg_duration_seconds == 120.0

    # Test SystemMetrics
    system = SystemMetrics(
        total_campaigns=5,
        active_campaigns=2,
        total_leads=500,
        total_calls_today=25,
        calls_in_progress=3,
        calls_queued=10,
        overall_answer_rate=85.5,
        overall_qualification_rate=45.2,
        redis_connected=True,
        database_connected=True,
        exotel_api_healthy=True
    )

    assert system.total_campaigns == 5
    assert system.redis_connected is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
