"""Tests for Email Service: Email parsing and lead extraction."""

import pytest
from datetime import datetime

from src.models.email_lead import EmailLead, ParsedEmailResult
from src.services.email_parsers import (
    MagicBricksParser,
    NinetyNineAcresParser,
    GenericLeadParser,
    EmailParserFactory
)


class TestEmailLeadModel:
    """Tests for EmailLead model."""

    def test_email_lead_creation(self):
        """Test EmailLead model can be instantiated."""
        lead = EmailLead(
            name="Rajesh Kumar",
            phone="9876543210",
            email="rajesh@example.com",
            property_type="2BHK",
            location="Gurgaon",
            budget=5000000,
            source="magicbricks",
            email_subject="New Lead from MagicBricks",
            email_received_at=datetime.utcnow(),
            email_message_id="msg123"
        )

        assert lead.name == "Rajesh Kumar"
        assert lead.phone == "+919876543210"  # Auto-formatted
        assert lead.email == "rajesh@example.com"
        assert lead.property_type == "2BHK"
        assert lead.source == "magicbricks"

    def test_phone_validation_10_digits(self):
        """Test phone validation with 10-digit number."""
        lead = EmailLead(
            name="Test User",
            phone="9876543210",
            source="magicbricks",
            email_subject="Test",
            email_received_at=datetime.utcnow(),
            email_message_id="msg1"
        )

        assert lead.phone == "+919876543210"

    def test_phone_validation_with_country_code(self):
        """Test phone validation with country code."""
        lead = EmailLead(
            name="Test User",
            phone="919876543210",
            source="magicbricks",
            email_subject="Test",
            email_received_at=datetime.utcnow(),
            email_message_id="msg1"
        )

        assert lead.phone == "+919876543210"

    def test_phone_validation_invalid(self):
        """Test phone validation rejects invalid numbers."""
        with pytest.raises(ValueError, match="Invalid Indian phone number"):
            EmailLead(
                name="Test User",
                phone="12345",  # Too short
                source="magicbricks",
                email_subject="Test",
                email_received_at=datetime.utcnow(),
                email_message_id="msg1"
            )

    def test_source_normalization(self):
        """Test source field normalization."""
        lead = EmailLead(
            name="Test",
            phone="9876543210",
            source="MAGICBRICKS",  # Uppercase
            email_subject="Test",
            email_received_at=datetime.utcnow(),
            email_message_id="msg1"
        )

        assert lead.source == "magicbricks"  # Normalized

    def test_property_type_uppercase(self):
        """Test property type is converted to uppercase."""
        lead = EmailLead(
            name="Test",
            phone="9876543210",
            property_type="2bhk",  # Lowercase
            source="website",
            email_subject="Test",
            email_received_at=datetime.utcnow(),
            email_message_id="msg1"
        )

        assert lead.property_type == "2BHK"


class TestMagicBricksParser:
    """Tests for MagicBricks email parser."""

    def test_can_parse_magicbricks_email(self):
        """Test parser recognizes MagicBricks emails."""
        parser = MagicBricksParser()

        assert parser.can_parse("New Lead from MagicBricks", "Some body text")
        assert parser.can_parse("Lead Notification", "Contact from magicbricks.com")
        assert parser.can_parse("New Enquiry", "Visit mb.com for details")

    def test_parse_magicbricks_email(self):
        """Test parsing a MagicBricks email."""
        parser = MagicBricksParser()

        subject = "New Lead from MagicBricks"
        body = """
        New lead received from MagicBricks!

        Name: Rajesh Kumar
        Phone: 9876543210
        Email: rajesh@example.com
        Property Type: 2BHK
        Location: Gurgaon
        Budget: 50 lakh
        Message: Looking for 2BHK apartment in Gurgaon

        Visit: https://www.magicbricks.com/property/12345
        """

        result = parser.parse(
            subject=subject,
            body=body,
            message_id="msg123",
            received_at=datetime.utcnow()
        )

        assert result.success is True
        assert result.lead is not None
        assert result.lead.name == "Rajesh Kumar"
        assert result.lead.phone == "+919876543210"
        assert result.lead.email == "rajesh@example.com"
        assert result.lead.property_type == "2BHK"
        assert result.lead.location == "Gurgaon"
        assert result.lead.budget == 5000000  # 50 lakh = 5000000
        assert result.lead.source == "magicbricks"

    def test_extract_phone_number(self):
        """Test phone number extraction from text."""
        parser = MagicBricksParser()

        assert parser.extract_phone("+91 9876543210") == "+91 9876543210"
        assert parser.extract_phone("Call me at 9876543210") == "9876543210"
        assert parser.extract_phone("Phone: 98765 43210") is not None

    def test_extract_email(self):
        """Test email extraction from text."""
        parser = MagicBricksParser()

        assert parser.extract_email("Contact: rajesh@example.com") == "rajesh@example.com"
        assert parser.extract_email("Email me at test.user@domain.co.in") == "test.user@domain.co.in"

    def test_extract_budget(self):
        """Test budget extraction from text."""
        parser = MagicBricksParser()

        # Test lakh format
        assert parser.extract_budget("Budget: 50 lakh") == 5000000
        assert parser.extract_budget("Budget: ₹50 lakh") == 5000000

        # Test crore format
        assert parser.extract_budget("Budget: 1 crore") == 10000000
        assert parser.extract_budget("Budget: ₹1.5 crore") == 15000000


class TestNinetyNineAcresParser:
    """Tests for 99Acres email parser."""

    def test_can_parse_99acres_email(self):
        """Test parser recognizes 99Acres emails."""
        parser = NinetyNineAcresParser()

        assert parser.can_parse("New Lead from 99Acres", "Some body")
        assert parser.can_parse("Enquiry", "Contact from 99acres.com")
        assert parser.can_parse("Lead", "Property on 99acre.com")

    def test_parse_99acres_email(self):
        """Test parsing a 99Acres email."""
        parser = NinetyNineAcresParser()

        subject = "New Enquiry from 99Acres"
        body = """
        Buyer Name: Priya Sharma
        Phone: +91 9123456789
        Email: priya@example.com
        Property Type: 3BHK Flat
        Location: Noida, Sector 62
        Budget: 75 lakh

        Visit property: https://www.99acres.com/property/xyz
        """

        result = parser.parse(
            subject=subject,
            body=body,
            message_id="msg456",
            received_at=datetime.utcnow()
        )

        assert result.success is True
        assert result.lead is not None
        assert result.lead.name == "Priya Sharma"
        assert result.lead.phone == "+919123456789"
        assert result.lead.source == "99acres"


class TestGenericLeadParser:
    """Tests for generic email parser."""

    def test_can_parse_any_email(self):
        """Test generic parser accepts any email."""
        parser = GenericLeadParser()

        assert parser.can_parse("Random subject", "Random body") is True

    def test_parse_generic_email(self):
        """Test parsing a generic lead email."""
        parser = GenericLeadParser()

        subject = "Property Enquiry"
        body = """
        Name: Amit Singh
        Contact: 9988776655

        Interested in 2BHK apartment in Bangalore.
        """

        result = parser.parse(
            subject=subject,
            body=body,
            message_id="msg789",
            received_at=datetime.utcnow()
        )

        assert result.success is True
        assert result.lead is not None
        assert result.lead.phone == "+919988776655"
        assert result.lead.source == "other"


class TestEmailParserFactory:
    """Tests for EmailParserFactory."""

    def test_get_parser_for_magicbricks(self):
        """Test factory returns MagicBricks parser."""
        factory = EmailParserFactory()

        parser = factory.get_parser("New Lead from MagicBricks", "Some text")

        assert isinstance(parser, MagicBricksParser)

    def test_get_parser_for_99acres(self):
        """Test factory returns 99Acres parser."""
        factory = EmailParserFactory()

        parser = factory.get_parser("Lead from 99Acres", "Some text")

        assert isinstance(parser, NinetyNineAcresParser)

    def test_get_parser_generic_fallback(self):
        """Test factory returns generic parser as fallback."""
        factory = EmailParserFactory()

        parser = factory.get_parser("Random email", "No specific source")

        assert isinstance(parser, GenericLeadParser)

    def test_parse_email_with_factory(self):
        """Test parsing email using factory."""
        factory = EmailParserFactory()

        subject = "New Lead from MagicBricks"
        body = """
        Name: Test User
        Phone: 9876543210
        Property: 2BHK
        """

        result = factory.parse_email(
            subject=subject,
            body=body,
            message_id="msg999",
            received_at=datetime.utcnow()
        )

        assert result.success is True
        assert result.lead is not None
        assert result.lead.source == "magicbricks"


# Run tests with: pytest tests/test_email_service.py -v
