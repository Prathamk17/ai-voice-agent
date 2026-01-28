"""
Email parsers for extracting lead information from different real estate platforms.
Supports MagicBricks, 99Acres, and other sources.
"""

import re
from typing import Optional
from datetime import datetime
from abc import ABC, abstractmethod

from src.models.email_lead import EmailLead, ParsedEmailResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BaseEmailParser(ABC):
    """Base class for email parsers."""

    @abstractmethod
    def can_parse(self, subject: str, body: str) -> bool:
        """
        Check if this parser can handle the given email.

        Args:
            subject: Email subject
            body: Email body

        Returns:
            True if this parser can parse the email
        """
        pass

    @abstractmethod
    def parse(
        self,
        subject: str,
        body: str,
        message_id: str,
        received_at: datetime
    ) -> ParsedEmailResult:
        """
        Parse email and extract lead information.

        Args:
            subject: Email subject
            body: Email body
            message_id: Unique email message ID
            received_at: Timestamp when email was received

        Returns:
            ParsedEmailResult with lead data or error
        """
        pass

    def extract_phone(self, text: str) -> Optional[str]:
        """Extract Indian phone number from text."""
        # Patterns for Indian phone numbers
        patterns = [
            r'\+91[-\s]?\d{10}',  # +91 with optional separator
            r'91[-\s]?\d{10}',    # 91 with optional separator
            r'\b0?\d{10}\b',      # 10 digits with optional leading 0
            r'\d{5}[-\s]\d{5}',   # XXXXX-XXXXX or XXXXX XXXXX
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return None

    def extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text."""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(pattern, text)
        return match.group(0) if match else None

    def extract_budget(self, text: str) -> Optional[int]:
        """Extract budget from text (in INR)."""
        # Look for common budget patterns (supports decimals like 1.5 crore)
        patterns = [
            r'(?:budget|price|budget range)[:\s]*₹?\s*([\d,.]+)\s*(?:lakh|lac|l)',  # X lakh
            r'(?:budget|price|budget range)[:\s]*₹?\s*([\d,.]+)\s*(?:crore|cr)',    # X crore
            r'(?:budget|price|budget range)[:\s]*₹?\s*([\d,.]+)',                   # Direct amount
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')

                # Handle decimal values
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue

                # Convert lakh/crore to actual amount
                if 'lakh' in pattern or 'lac' in pattern or 'l' in pattern:
                    return int(amount * 100000)
                elif 'crore' in pattern or 'cr' in pattern:
                    return int(amount * 10000000)
                else:
                    return int(amount)

        return None


class MagicBricksParser(BaseEmailParser):
    """Parser for MagicBricks lead notification emails."""

    def can_parse(self, subject: str, body: str) -> bool:
        """Check if email is from MagicBricks."""
        subject_lower = subject.lower()
        body_lower = body.lower()

        return (
            'magicbricks' in subject_lower or
            'magicbricks' in body_lower or
            'mb.com' in body_lower or
            '@magicbricks.com' in body_lower
        )

    def parse(
        self,
        subject: str,
        body: str,
        message_id: str,
        received_at: datetime
    ) -> ParsedEmailResult:
        """Parse MagicBricks email."""
        try:
            # Extract name
            name_patterns = [
                r'(?:Name|Customer Name|Lead Name)[:\s]*([A-Za-z\s]+?)(?:\n|<br|$)',
                r'(?:Contact|Enquiry from)[:\s]*([A-Za-z\s]+?)(?:\n|<br|$)',
            ]
            name = None
            for pattern in name_patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    break

            if not name:
                # Try to extract from subject
                subject_match = re.search(r'(?:from|by)\s+([A-Za-z\s]+)', subject, re.IGNORECASE)
                if subject_match:
                    name = subject_match.group(1).strip()

            # Extract phone
            phone = self.extract_phone(body)
            if not phone:
                raise ValueError("Phone number not found in email")

            # Extract email
            email = self.extract_email(body)

            # Extract property type
            property_type_match = re.search(
                r'(?:Property Type|Looking for)[:\s]*(\d+\s*BHK|Villa|Plot|Commercial|Office)',
                body,
                re.IGNORECASE
            )
            property_type = property_type_match.group(1).strip() if property_type_match else None

            # Extract location
            location_match = re.search(
                r'(?:Location|City|Area|Locality)[:\s]*([A-Za-z\s,]+?)(?:\n|<br|$)',
                body,
                re.IGNORECASE
            )
            location = location_match.group(1).strip() if location_match else None

            # Extract budget
            budget = self.extract_budget(body)

            # Extract URL
            url_match = re.search(r'https?://(?:www\.)?magicbricks\.com/[^\s<]+', body)
            source_url = url_match.group(0) if url_match else None

            # Extract message
            message_match = re.search(
                r'(?:Message|Comments|Requirement)[:\s]*(.+?)(?:\n\n|<br><br|$)',
                body,
                re.IGNORECASE | re.DOTALL
            )
            message = message_match.group(1).strip() if message_match else None

            lead = EmailLead(
                name=name or "Unknown",
                phone=phone,
                email=email,
                property_type=property_type,
                location=location,
                budget=budget,
                source="magicbricks",
                source_url=source_url,
                email_subject=subject,
                email_received_at=received_at,
                email_message_id=message_id,
                message=message,
                tags="magicbricks,email-lead"
            )

            logger.info(
                "Successfully parsed MagicBricks email",
                lead_name=lead.name,
                phone=lead.phone,
                location=lead.location
            )

            return ParsedEmailResult(
                success=True,
                lead=lead,
                error=None,
                raw_email_subject=subject,
                raw_email_body=body
            )

        except Exception as e:
            logger.error(f"Failed to parse MagicBricks email: {str(e)}")
            return ParsedEmailResult(
                success=False,
                lead=None,
                error=str(e),
                raw_email_subject=subject,
                raw_email_body=body
            )


class NinetyNineAcresParser(BaseEmailParser):
    """Parser for 99Acres lead notification emails."""

    def can_parse(self, subject: str, body: str) -> bool:
        """Check if email is from 99Acres."""
        subject_lower = subject.lower()
        body_lower = body.lower()

        return (
            '99acres' in subject_lower or
            '99acres' in body_lower or
            '99acre' in body_lower or
            '@99acres.com' in body_lower
        )

    def parse(
        self,
        subject: str,
        body: str,
        message_id: str,
        received_at: datetime
    ) -> ParsedEmailResult:
        """Parse 99Acres email."""
        try:
            # Extract name
            name_patterns = [
                r'(?:Name|Buyer Name|Contact)[:\s]*([A-Za-z\s]+?)(?:\n|<br|$)',
                r'(?:Lead from)[:\s]*([A-Za-z\s]+?)(?:\n|<br|$)',
            ]
            name = None
            for pattern in name_patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    break

            # Extract phone
            phone = self.extract_phone(body)
            if not phone:
                raise ValueError("Phone number not found in email")

            # Extract email
            email = self.extract_email(body)

            # Extract property type
            property_type_match = re.search(
                r'(?:Property Type|Type)[:\s]*(\d+\s*BHK|Villa|Plot|Flat|Apartment)',
                body,
                re.IGNORECASE
            )
            property_type = property_type_match.group(1).strip() if property_type_match else None

            # Extract location
            location_match = re.search(
                r'(?:Location|City|Locality|Area)[:\s]*([A-Za-z\s,]+?)(?:\n|<br|$)',
                body,
                re.IGNORECASE
            )
            location = location_match.group(1).strip() if location_match else None

            # Extract budget
            budget = self.extract_budget(body)

            # Extract URL
            url_match = re.search(r'https?://(?:www\.)?99acres\.com/[^\s<]+', body)
            source_url = url_match.group(0) if url_match else None

            # Extract message
            message_match = re.search(
                r'(?:Message|Query|Enquiry)[:\s]*(.+?)(?:\n\n|<br><br|$)',
                body,
                re.IGNORECASE | re.DOTALL
            )
            message = message_match.group(1).strip() if message_match else None

            lead = EmailLead(
                name=name or "Unknown",
                phone=phone,
                email=email,
                property_type=property_type,
                location=location,
                budget=budget,
                source="99acres",
                source_url=source_url,
                email_subject=subject,
                email_received_at=received_at,
                email_message_id=message_id,
                message=message,
                tags="99acres,email-lead"
            )

            logger.info(
                "Successfully parsed 99Acres email",
                lead_name=lead.name,
                phone=lead.phone,
                location=lead.location
            )

            return ParsedEmailResult(
                success=True,
                lead=lead,
                error=None,
                raw_email_subject=subject,
                raw_email_body=body
            )

        except Exception as e:
            logger.error(f"Failed to parse 99Acres email: {str(e)}")
            return ParsedEmailResult(
                success=False,
                lead=None,
                error=str(e),
                raw_email_subject=subject,
                raw_email_body=body
            )


class LandingPageParser(BaseEmailParser):
    """Parser for landing page enquiries from leadsvasupujya@gmail.com."""

    def can_parse(self, subject: str, body: str) -> bool:
        """Check if email is from landing page."""
        subject_lower = subject.lower()
        body_lower = body.lower()

        return (
            'landing page enquiry' in subject_lower or
            'leadsvasupujya@gmail.com' in body_lower or
            'enquire about project' in body_lower or
            'enquiry generated by' in body_lower
        )

    def parse(
        self,
        subject: str,
        body: str,
        message_id: str,
        received_at: datetime
    ) -> ParsedEmailResult:
        """Parse landing page email."""
        try:
            # Extract name - pattern: "Name : Durgesh Singh"
            name_match = re.search(
                r'(?:Name|Enquiry Generated by)\s*[:\s]*([A-Za-z\s]+?)(?:\n|$)',
                body,
                re.IGNORECASE
            )
            name = name_match.group(1).strip() if name_match else None

            # Extract email - pattern: "Email : singhdurgesh2881@gmail.com"
            email = self.extract_email(body)

            # Extract phone - pattern: "Contact No. : 9131119914"
            phone_match = re.search(
                r'(?:Contact No\.|Mobile|Phone)\s*[:\s]*([+\d\s-]+)',
                body,
                re.IGNORECASE
            )
            phone = phone_match.group(1).strip() if phone_match else self.extract_phone(body)

            if not phone:
                raise ValueError("Phone number not found in email")

            # Extract property type - pattern: "Enquire About Project : 2 BHK"
            property_type_match = re.search(
                r'(?:Enquire About Project|Property Type|Requirement)\s*[:\s]*([^\n]+)',
                body,
                re.IGNORECASE
            )
            property_type = property_type_match.group(1).strip() if property_type_match else None

            # Extract source and sub-source
            source_match = re.search(r'Source\s*[:\s]*([^\n]+)', body, re.IGNORECASE)
            sub_source_match = re.search(r'Sub Source\s*[:\s]*([^\n]+)', body, re.IGNORECASE)

            source_info = source_match.group(1).strip() if source_match else None
            sub_source_info = sub_source_match.group(1).strip() if sub_source_match else None

            # Extract location from subject if present (e.g., "Neco Park Central")
            location = None
            if 'neco park' in subject.lower():
                location = "Neco Park Central, Kharadi, Pune"
            elif 'kharadi' in subject.lower() or 'kharadi' in body.lower():
                location = "Kharadi, Pune"

            # Extract Client IP for tracking
            ip_match = re.search(r'Client IP\s*[:\s]*([\d.]+)', body, re.IGNORECASE)
            client_ip = ip_match.group(1) if ip_match else None

            # Build tags
            tags_list = ["website-lead", "landing-page"]
            if source_info:
                tags_list.append(f"source-{source_info.lower()}")
            if sub_source_info:
                tags_list.append(f"subsource-{sub_source_info.lower()}")

            tags = ",".join(tags_list)

            # Build message with all context
            message_parts = []
            if source_info:
                message_parts.append(f"Source: {source_info}")
            if sub_source_info:
                message_parts.append(f"Sub Source: {sub_source_info}")
            if client_ip:
                message_parts.append(f"IP: {client_ip}")

            message = " | ".join(message_parts) if message_parts else "Landing page enquiry"

            lead = EmailLead(
                name=name or "Unknown",
                phone=phone,
                email=email,
                property_type=property_type,
                location=location,
                budget=None,
                source="website",
                source_url=None,
                email_subject=subject,
                email_received_at=received_at,
                email_message_id=message_id,
                message=message,
                tags=tags
            )

            logger.info(
                "Successfully parsed Landing Page email",
                lead_name=lead.name,
                phone=lead.phone,
                property_type=lead.property_type,
                source=source_info
            )

            return ParsedEmailResult(
                success=True,
                lead=lead,
                error=None,
                raw_email_subject=subject,
                raw_email_body=body
            )

        except Exception as e:
            logger.error(f"Failed to parse Landing Page email: {str(e)}")
            return ParsedEmailResult(
                success=False,
                lead=None,
                error=str(e),
                raw_email_subject=subject,
                raw_email_body=body
            )


class MetaLeadsParser(BaseEmailParser):
    """Parser for Meta/Facebook leads from Digital Tokri (leads@digitaltokri.in)."""

    def can_parse(self, subject: str, body: str) -> bool:
        """Check if email is from Meta/Digital Tokri."""
        subject_lower = subject.lower()
        body_lower = body.lower()

        return (
            'meta leads' in subject_lower or
            'digitaltokri' in body_lower or
            'digital tokri' in body_lower or
            '@digitaltokri.in' in body_lower or
            'looking for property?' in body_lower or
            'site visit preference' in body_lower
        )

    def parse(
        self,
        subject: str,
        body: str,
        message_id: str,
        received_at: datetime
    ) -> ParsedEmailResult:
        """Parse Meta/Digital Tokri email."""
        try:
            # Extract name - pattern: "Name: Radhe Radhe" or "3. Name: Radhe Radhe"
            name_match = re.search(
                r'(?:\d+\.\s*)?Name\s*[:\s]*([A-Za-z\s]+?)(?:\n|$)',
                body,
                re.IGNORECASE
            )
            name = name_match.group(1).strip() if name_match else None

            # Extract email - pattern: "Email: apatel93421@gmail.com"
            email = self.extract_email(body)

            # Extract phone - pattern: "Mobile No.: +918081030962" or "Mobile: 9810089654"
            phone_match = re.search(
                r'(?:Mobile No\.|Mobile)\s*[:\s]*([+\d\s-]+)',
                body,
                re.IGNORECASE
            )
            phone = phone_match.group(1).strip() if phone_match else self.extract_phone(body)

            if not phone:
                raise ValueError("Phone number not found in email")

            # Extract property type - pattern: "Requirement: 2_bhk_at_₹1.09_cr*"
            requirement_match = re.search(
                r'Requirement\s*[:\s]*([^\n]+)',
                body,
                re.IGNORECASE
            )

            property_type = None
            budget = None

            if requirement_match:
                requirement = requirement_match.group(1).strip()

                # Extract property type from requirement (e.g., "2_bhk" -> "2 BHK")
                bhk_match = re.search(r'(\d+)_?bhk', requirement, re.IGNORECASE)
                if bhk_match:
                    property_type = f"{bhk_match.group(1)} BHK"

                # Extract budget from requirement (e.g., "₹1.09_cr" -> 10900000)
                budget_match = re.search(r'₹?([\d.]+)\s*(?:cr|crore)', requirement, re.IGNORECASE)
                if budget_match:
                    budget = int(float(budget_match.group(1)) * 10000000)

            # Extract location preference
            looking_for_match = re.search(
                r'Looking for property\?\s*[:\s]*([^\n]+)',
                body,
                re.IGNORECASE
            )
            looking_for = looking_for_match.group(1).strip() if looking_for_match else None

            # Extract site visit preference - pattern: "Site Visit Preference: today"
            site_visit_match = re.search(
                r'Site Visit Preference\s*[:\s]*([^\n]+)',
                body,
                re.IGNORECASE
            )
            site_visit = site_visit_match.group(1).strip() if site_visit_match else None

            # Determine location from subject or set default
            location = None
            if 'neco park' in subject.lower() or 'neco park' in body.lower():
                location = "Neco Park Central, Kharadi, Pune"
            elif 'kharadi' in subject.lower() or 'kharadi' in body.lower():
                location = "Kharadi, Pune"

            # Build tags
            tags_list = ["meta-lead", "facebook-lead", "digital-tokri"]
            if site_visit:
                tags_list.append(f"site-visit-{site_visit.lower().replace(' ', '-')}")

            tags = ",".join(tags_list)

            # Build message with all context
            message_parts = []
            if looking_for:
                message_parts.append(f"Looking for: {looking_for}")
            if site_visit:
                message_parts.append(f"Site Visit: {site_visit}")
            if requirement_match:
                message_parts.append(f"Requirement: {requirement_match.group(1)}")

            message = " | ".join(message_parts) if message_parts else "Meta lead"

            lead = EmailLead(
                name=name or "Unknown",
                phone=phone,
                email=email,
                property_type=property_type,
                location=location,
                budget=budget,
                source="advertisement",  # Meta/Facebook ads
                source_url=None,
                email_subject=subject,
                email_received_at=received_at,
                email_message_id=message_id,
                message=message,
                tags=tags
            )

            logger.info(
                "Successfully parsed Meta/Digital Tokri email",
                lead_name=lead.name,
                phone=lead.phone,
                property_type=lead.property_type,
                site_visit=site_visit
            )

            return ParsedEmailResult(
                success=True,
                lead=lead,
                error=None,
                raw_email_subject=subject,
                raw_email_body=body
            )

        except Exception as e:
            logger.error(f"Failed to parse Meta/Digital Tokri email: {str(e)}")
            return ParsedEmailResult(
                success=False,
                lead=None,
                error=str(e),
                raw_email_subject=subject,
                raw_email_body=body
            )


class GenericLeadParser(BaseEmailParser):
    """Generic parser for other lead notification emails."""

    def can_parse(self, subject: str, body: str) -> bool:
        """Can parse any email (fallback parser)."""
        return True  # Always return True as this is the fallback

    def parse(
        self,
        subject: str,
        body: str,
        message_id: str,
        received_at: datetime
    ) -> ParsedEmailResult:
        """Parse generic lead email."""
        try:
            # Try to extract basic information
            phone = self.extract_phone(body)
            if not phone:
                raise ValueError("Phone number not found in email")

            # Extract name (try common patterns)
            name_patterns = [
                r'(?:Name|Contact Name)[:\s]*([A-Za-z\s]+?)(?:\n|<br|$)',
                r'^([A-Za-z\s]+?)(?:\n|<br)',  # First line might be name
            ]
            name = None
            for pattern in name_patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    break

            email = self.extract_email(body)

            # Try to extract property type
            property_type_match = re.search(
                r'(\d+\s*BHK|Villa|Plot|Apartment|Flat)',
                body,
                re.IGNORECASE
            )
            property_type = property_type_match.group(1).strip() if property_type_match else None

            # Try to extract location
            location_match = re.search(
                r'(?:in|at|@)\s+([A-Za-z\s]+?)(?:\n|,|$)',
                body,
                re.IGNORECASE
            )
            location = location_match.group(1).strip() if location_match else None

            budget = self.extract_budget(body)

            lead = EmailLead(
                name=name or "Unknown",
                phone=phone,
                email=email,
                property_type=property_type,
                location=location,
                budget=budget,
                source="other",
                source_url=None,
                email_subject=subject,
                email_received_at=received_at,
                email_message_id=message_id,
                message=body[:500],  # First 500 chars as message
                tags="email-lead,generic"
            )

            logger.info(
                "Successfully parsed generic email",
                lead_name=lead.name,
                phone=lead.phone
            )

            return ParsedEmailResult(
                success=True,
                lead=lead,
                error=None,
                raw_email_subject=subject,
                raw_email_body=body
            )

        except Exception as e:
            logger.error(f"Failed to parse generic email: {str(e)}")
            return ParsedEmailResult(
                success=False,
                lead=None,
                error=str(e),
                raw_email_subject=subject,
                raw_email_body=body
            )


class EmailParserFactory:
    """Factory for getting the appropriate email parser."""

    def __init__(self):
        """Initialize parser factory with all available parsers."""
        self.parsers = [
            MagicBricksParser(),
            NinetyNineAcresParser(),
            LandingPageParser(),
            MetaLeadsParser(),
            GenericLeadParser(),  # This should be last as it's the fallback
        ]

    def get_parser(self, subject: str, body: str) -> BaseEmailParser:
        """
        Get the appropriate parser for the given email.

        Args:
            subject: Email subject
            body: Email body

        Returns:
            Appropriate email parser
        """
        for parser in self.parsers:
            if parser.can_parse(subject, body):
                return parser

        # Should never reach here as GenericLeadParser always returns True
        return self.parsers[-1]

    def parse_email(
        self,
        subject: str,
        body: str,
        message_id: str,
        received_at: datetime
    ) -> ParsedEmailResult:
        """
        Parse email using the appropriate parser.

        Args:
            subject: Email subject
            body: Email body
            message_id: Unique email message ID
            received_at: Timestamp when email was received

        Returns:
            ParsedEmailResult with lead data or error
        """
        parser = self.get_parser(subject, body)
        return parser.parse(subject, body, message_id, received_at)
