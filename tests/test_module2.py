"""Tests for Module 2: Campaign Management & CSV Upload."""

import pytest
import io
from datetime import datetime, timedelta

from src.models.campaign import Campaign, CampaignStatus
from src.models.lead import Lead, LeadSource
from src.services.csv_service import CSVService, LeadCSVRow


class TestCampaignModel:
    """Tests for Campaign model."""

    def test_campaign_status_enum(self):
        """Test CampaignStatus enum values."""
        assert CampaignStatus.DRAFT == "draft"
        assert CampaignStatus.SCHEDULED == "scheduled"
        assert CampaignStatus.RUNNING == "running"
        assert CampaignStatus.PAUSED == "paused"
        assert CampaignStatus.COMPLETED == "completed"
        assert CampaignStatus.CANCELLED == "cancelled"

    def test_campaign_model_creation(self):
        """Test Campaign model can be instantiated."""
        campaign = Campaign(
            name="Test Campaign",
            description="A test campaign",
            status=CampaignStatus.DRAFT,
            max_attempts_per_lead=3,
            retry_delay_hours=24,
            calling_hours_start=10,
            calling_hours_end=19,
            max_concurrent_calls=5,
            total_leads=0,
            leads_called=0,
            leads_completed=0,
            leads_qualified=0,
            is_active=True,
            is_deleted=False
        )

        assert campaign.name == "Test Campaign"
        assert campaign.description == "A test campaign"
        assert campaign.status == CampaignStatus.DRAFT
        assert campaign.max_attempts_per_lead == 3
        assert campaign.retry_delay_hours == 24
        assert campaign.calling_hours_start == 10
        assert campaign.calling_hours_end == 19
        assert campaign.max_concurrent_calls == 5
        assert campaign.total_leads == 0
        assert campaign.leads_called == 0
        assert campaign.leads_completed == 0
        assert campaign.leads_qualified == 0
        assert campaign.is_active == True
        assert campaign.is_deleted == False

    def test_campaign_calculate_metrics(self):
        """Test Campaign.calculate_metrics method."""
        campaign = Campaign(
            name="Test Campaign",
            total_leads=100,
            leads_called=80,
            leads_completed=60,
            leads_qualified=30,
            total_call_duration_seconds=3600
        )

        campaign.calculate_metrics()

        # Success rate: completed / called = 60/80 = 75%
        assert campaign.success_rate == 75.0

        # Qualification rate: qualified / completed = 30/60 = 50%
        assert campaign.qualification_rate == 50.0

        # Average call duration: total_duration / called = 3600/80 = 45 seconds
        assert campaign.average_call_duration == 45.0

    def test_campaign_calculate_metrics_with_zero_calls(self):
        """Test metrics calculation with zero calls doesn't crash."""
        campaign = Campaign(
            name="Test Campaign",
            total_leads=100,
            leads_called=0,
            leads_completed=0
        )

        # Should not raise exception
        campaign.calculate_metrics()

        assert campaign.success_rate is None
        assert campaign.qualification_rate is None
        assert campaign.average_call_duration is None


class TestLeadCSVRow:
    """Tests for CSV lead validation."""

    def test_valid_lead_csv_row(self):
        """Test valid LeadCSVRow creation."""
        lead = LeadCSVRow(
            name="Rajesh Kumar",
            phone="9876543210",
            email="rajesh@example.com",
            property_type="2BHK",
            location="Gurgaon",
            budget=5000000,
            source="website",
            tags="first-time-buyer"
        )

        assert lead.name == "Rajesh Kumar"
        assert lead.phone == "+919876543210"  # Auto-formatted
        assert lead.email == "rajesh@example.com"
        assert lead.property_type == "2BHK"
        assert lead.location == "Gurgaon"
        assert lead.budget == 5000000
        assert lead.source == "website"
        assert lead.tags == "first-time-buyer"

    def test_phone_validation_10_digits(self):
        """Test phone validation with 10-digit number."""
        lead = LeadCSVRow(
            name="Test User",
            phone="9876543210",
            property_type="3BHK",
            location="Mumbai"
        )

        assert lead.phone == "+919876543210"

    def test_phone_validation_with_country_code(self):
        """Test phone validation with country code."""
        lead = LeadCSVRow(
            name="Test User",
            phone="919876543210",
            property_type="3BHK",
            location="Mumbai"
        )

        assert lead.phone == "+919876543210"

    def test_phone_validation_with_plus(self):
        """Test phone validation with + prefix."""
        lead = LeadCSVRow(
            name="Test User",
            phone="+919876543210",
            property_type="3BHK",
            location="Mumbai"
        )

        assert lead.phone == "+919876543210"

    def test_phone_validation_with_spaces(self):
        """Test phone validation removes spaces."""
        lead = LeadCSVRow(
            name="Test User",
            phone="98765 43210",
            property_type="3BHK",
            location="Mumbai"
        )

        assert lead.phone == "+919876543210"

    def test_phone_validation_invalid(self):
        """Test phone validation rejects invalid numbers."""
        with pytest.raises(ValueError, match="Invalid Indian phone number"):
            LeadCSVRow(
                name="Test User",
                phone="12345",  # Too short
                property_type="3BHK",
                location="Mumbai"
            )

    def test_email_validation_lowercase(self):
        """Test email is converted to lowercase."""
        lead = LeadCSVRow(
            name="Test User",
            phone="9876543210",
            email="TEST@EXAMPLE.COM",
            property_type="3BHK",
            location="Mumbai"
        )

        assert lead.email == "test@example.com"

    def test_email_validation_invalid(self):
        """Test invalid email is rejected."""
        with pytest.raises(ValueError, match="Invalid email format"):
            LeadCSVRow(
                name="Test User",
                phone="9876543210",
                email="invalid-email",
                property_type="3BHK",
                location="Mumbai"
            )

    def test_email_optional(self):
        """Test email is optional."""
        lead = LeadCSVRow(
            name="Test User",
            phone="9876543210",
            property_type="3BHK",
            location="Mumbai"
        )

        assert lead.email is None

    def test_source_validation(self):
        """Test source validation."""
        for source in ["website", "referral", "advertisement", "partner"]:
            lead = LeadCSVRow(
                name="Test User",
                phone="9876543210",
                property_type="3BHK",
                location="Mumbai",
                source=source
            )
            assert lead.source == source

    def test_source_validation_invalid(self):
        """Test invalid source is rejected."""
        with pytest.raises(ValueError, match="Invalid source"):
            LeadCSVRow(
                name="Test User",
                phone="9876543210",
                property_type="3BHK",
                location="Mumbai",
                source="invalid_source"
            )

    def test_property_type_uppercase(self):
        """Test property type is converted to uppercase."""
        lead = LeadCSVRow(
            name="Test User",
            phone="9876543210",
            property_type="2bhk",
            location="Mumbai"
        )

        assert lead.property_type == "2BHK"

    def test_budget_validation_positive(self):
        """Test budget must be positive."""
        with pytest.raises(ValueError, match="Budget must be positive"):
            LeadCSVRow(
                name="Test User",
                phone="9876543210",
                property_type="3BHK",
                location="Mumbai",
                budget=-100000
            )

    def test_budget_optional(self):
        """Test budget is optional."""
        lead = LeadCSVRow(
            name="Test User",
            phone="9876543210",
            property_type="3BHK",
            location="Mumbai"
        )

        assert lead.budget is None


class TestCSVService:
    """Tests for CSV service."""

    def test_csv_service_initialization(self):
        """Test CSVService can be instantiated."""
        service = CSVService()

        assert service.required_columns == {'name', 'phone', 'property_type', 'location'}
        assert 'email' in service.optional_columns
        assert 'budget' in service.optional_columns

    @pytest.mark.asyncio
    async def test_parse_valid_csv(self):
        """Test parsing a valid CSV file."""
        csv_content = """name,phone,email,property_type,location,budget,source,tags
Rajesh Kumar,9876543210,rajesh@example.com,2BHK,Gurgaon,5000000,website,first-time
Priya Sharma,9123456789,priya@example.com,3BHK,Noida,7500000,referral,investor
"""
        service = CSVService()
        result = await service.parse_csv_file(csv_content.encode('utf-8'), campaign_id=1)

        assert result.total_rows == 2
        assert result.valid_rows == 2
        assert result.invalid_rows == 0
        assert result.duplicate_rows == 0
        assert len(result.leads) == 2
        assert len(result.errors) == 0

        # Check first lead
        assert result.leads[0].name == "Rajesh Kumar"
        assert result.leads[0].phone == "+919876543210"
        assert result.leads[0].property_type == "2BHK"

    @pytest.mark.asyncio
    async def test_parse_csv_with_missing_column(self):
        """Test parsing CSV with missing required column."""
        csv_content = """name,phone,location
Rajesh Kumar,9876543210,Gurgaon
"""
        service = CSVService()

        with pytest.raises(ValueError, match="Missing required columns: property_type"):
            await service.parse_csv_file(csv_content.encode('utf-8'), campaign_id=1)

    @pytest.mark.asyncio
    async def test_parse_csv_with_invalid_data(self):
        """Test parsing CSV with invalid phone number."""
        csv_content = """name,phone,email,property_type,location
Rajesh Kumar,12345,invalid-email,2BHK,Gurgaon
Priya Sharma,9123456789,priya@example.com,3BHK,Noida
"""
        service = CSVService()
        result = await service.parse_csv_file(csv_content.encode('utf-8'), campaign_id=1)

        assert result.total_rows == 2
        assert result.valid_rows == 1  # Only second row is valid
        assert result.invalid_rows == 1
        assert len(result.leads) == 1
        assert len(result.errors) == 1

        # Check error details
        error = result.errors[0]
        assert error['row'] == '2'  # First data row (after header)
        assert 'phone' in error['error']

    @pytest.mark.asyncio
    async def test_parse_csv_with_duplicates(self):
        """Test parsing CSV with duplicate phone numbers."""
        csv_content = """name,phone,email,property_type,location
Rajesh Kumar,9876543210,rajesh@example.com,2BHK,Gurgaon
Priya Sharma,9876543210,priya@example.com,3BHK,Noida
"""
        service = CSVService()
        result = await service.parse_csv_file(
            csv_content.encode('utf-8'),
            campaign_id=1,
            check_duplicates=True
        )

        assert result.total_rows == 2
        assert result.valid_rows == 1  # Only first occurrence
        assert result.duplicate_rows == 1
        assert len(result.leads) == 1

    @pytest.mark.asyncio
    async def test_convert_to_lead_models(self):
        """Test converting CSV rows to Lead models."""
        csv_rows = [
            LeadCSVRow(
                name="Rajesh Kumar",
                phone="+919876543210",
                email="rajesh@example.com",
                property_type="2BHK",
                location="Gurgaon",
                budget=5000000,
                source="website"
            )
        ]

        service = CSVService()
        leads = await service.convert_to_lead_models(csv_rows, campaign_id=1)

        assert len(leads) == 1
        lead = leads[0]

        assert isinstance(lead, Lead)
        assert lead.name == "Rajesh Kumar"
        assert lead.phone == "+919876543210"
        assert lead.email == "rajesh@example.com"
        assert lead.property_type == "2BHK"
        assert lead.location == "Gurgaon"
        assert lead.budget == 5000000
        assert lead.source == LeadSource.WEBSITE
        assert lead.campaign_id == 1
        assert lead.call_attempts == 0

    @pytest.mark.asyncio
    async def test_generate_sample_csv(self):
        """Test sample CSV generation."""
        service = CSVService()
        sample = await service.generate_sample_csv()

        assert "name,phone,email,property_type,location,budget,source,tags" in sample
        assert "Rajesh Kumar" in sample
        assert "9876543210" in sample
        assert "2BHK" in sample

    def test_validate_csv_format_valid(self):
        """Test CSV format validation with valid file."""
        csv_content = """name,phone,email,property_type,location
Rajesh,9876543210,r@test.com,2BHK,Delhi
"""
        service = CSVService()
        is_valid, error = service.validate_csv_format(csv_content.encode('utf-8'))

        assert is_valid is True
        assert error is None

    def test_validate_csv_format_missing_column(self):
        """Test CSV format validation with missing column."""
        csv_content = """name,phone,location
Rajesh,9876543210,Delhi
"""
        service = CSVService()
        is_valid, error = service.validate_csv_format(csv_content.encode('utf-8'))

        assert is_valid is False
        assert "Missing required columns: property_type" in error


# Run tests with: pytest tests/test_module2.py -v
