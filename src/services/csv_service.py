"""CSV upload and parsing service for lead import."""

import csv
import io
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import pandas as pd
from pydantic import BaseModel, ValidationError, field_validator

from src.models.lead import Lead, LeadSource
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LeadCSVRow(BaseModel):
    """Validation model for CSV row data."""
    name: str
    phone: str
    email: Optional[str] = None
    property_type: str
    location: str
    budget: Optional[float] = None
    source: str = "website"
    tags: Optional[str] = None

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number format."""
        # Remove spaces and special characters
        cleaned = ''.join(filter(str.isdigit, v))

        # Indian phone numbers should be 10 digits
        if len(cleaned) == 10:
            return f"+91{cleaned}"
        elif len(cleaned) == 12 and cleaned.startswith('91'):
            return f"+{cleaned}"
        elif len(cleaned) == 13 and cleaned.startswith('+91'):
            return cleaned
        else:
            raise ValueError(
                f"Invalid Indian phone number format. Expected 10 digits, got {len(cleaned)}"
            )

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format."""
        if v is None or v.strip() == "":
            return None

        # Basic email validation
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError(f"Invalid email format: {v}")

        return v.lower().strip()

    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate lead source."""
        try:
            LeadSource(v.lower())
            return v.lower()
        except ValueError:
            valid_sources = [s.value for s in LeadSource]
            raise ValueError(
                f"Invalid source '{v}'. Must be one of: {', '.join(valid_sources)}"
            )

    @field_validator('property_type')
    @classmethod
    def validate_property_type(cls, v: str) -> str:
        """Validate and normalize property type."""
        return v.strip().upper()

    @field_validator('budget')
    @classmethod
    def validate_budget(cls, v: Optional[float]) -> Optional[float]:
        """Validate budget is positive."""
        if v is not None and v <= 0:
            raise ValueError("Budget must be positive")
        return v


class CSVParseResult(BaseModel):
    """Result of CSV parsing operation."""
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    leads: List[LeadCSVRow]
    errors: List[Dict[str, str]]


class CSVService:
    """Service for handling CSV upload and parsing operations."""

    def __init__(self):
        """Initialize CSV service."""
        self.required_columns = {'name', 'phone', 'property_type', 'location'}
        self.optional_columns = {'email', 'budget', 'source', 'tags'}
        self.all_columns = self.required_columns | self.optional_columns

    async def parse_csv_file(
        self,
        file_content: bytes,
        campaign_id: int,
        check_duplicates: bool = True
    ) -> CSVParseResult:
        """
        Parse CSV file content and validate lead data.

        Args:
            file_content: Raw CSV file bytes
            campaign_id: Campaign ID to associate leads with
            check_duplicates: Whether to check for duplicate phone numbers

        Returns:
            CSVParseResult with parsed leads and errors
        """
        try:
            # Decode file content
            content_str = file_content.decode('utf-8')

            # Use pandas to read CSV for better handling
            df = pd.read_csv(io.StringIO(content_str))

            # Normalize column names (lowercase, strip whitespace)
            df.columns = df.columns.str.lower().str.strip()

            # Validate required columns
            missing_columns = self.required_columns - set(df.columns)
            if missing_columns:
                raise ValueError(
                    f"Missing required columns: {', '.join(missing_columns)}"
                )

            total_rows = len(df)
            valid_leads = []
            errors = []
            phone_numbers_seen = set()
            duplicate_count = 0

            for idx, row in df.iterrows():
                row_num = idx + 2  # +2 for header and 0-based index

                try:
                    # Convert row to dict and handle NaN values
                    row_dict = row.to_dict()
                    cleaned_dict = {
                        k: (None if pd.isna(v) else v)
                        for k, v in row_dict.items()
                        if k in self.all_columns
                    }

                    # Validate using Pydantic model
                    lead_row = LeadCSVRow(**cleaned_dict)

                    # Check for duplicates within the file
                    if check_duplicates:
                        if lead_row.phone in phone_numbers_seen:
                            duplicate_count += 1
                            errors.append({
                                'row': str(row_num),
                                'phone': lead_row.phone,
                                'error': 'Duplicate phone number in CSV'
                            })
                            continue
                        phone_numbers_seen.add(lead_row.phone)

                    valid_leads.append(lead_row)

                except ValidationError as e:
                    # Collect validation errors
                    error_messages = []
                    for error in e.errors():
                        field = error['loc'][0] if error['loc'] else 'unknown'
                        message = error['msg']
                        error_messages.append(f"{field}: {message}")

                    errors.append({
                        'row': str(row_num),
                        'phone': row_dict.get('phone', 'N/A'),
                        'error': '; '.join(error_messages)
                    })

                except Exception as e:
                    errors.append({
                        'row': str(row_num),
                        'phone': row_dict.get('phone', 'N/A'),
                        'error': str(e)
                    })

            result = CSVParseResult(
                total_rows=total_rows,
                valid_rows=len(valid_leads),
                invalid_rows=len(errors),
                duplicate_rows=duplicate_count,
                leads=valid_leads,
                errors=errors
            )

            logger.info(
                "CSV parsing completed",
                total_rows=total_rows,
                valid_rows=len(valid_leads),
                invalid_rows=len(errors),
                duplicate_rows=duplicate_count,
                campaign_id=campaign_id
            )

            return result

        except UnicodeDecodeError:
            raise ValueError("Invalid file encoding. Please use UTF-8 encoded CSV file.")
        except pd.errors.EmptyDataError:
            raise ValueError("CSV file is empty")
        except Exception as e:
            logger.error(f"CSV parsing failed: {str(e)}", campaign_id=campaign_id)
            raise ValueError(f"Failed to parse CSV file: {str(e)}")

    async def convert_to_lead_models(
        self,
        csv_rows: List[LeadCSVRow],
        campaign_id: int
    ) -> List[Lead]:
        """
        Convert validated CSV rows to Lead model instances.

        Args:
            csv_rows: List of validated CSV row data
            campaign_id: Campaign ID to associate leads with

        Returns:
            List of Lead instances ready for database insertion
        """
        leads = []

        for row in csv_rows:
            lead = Lead(
                name=row.name.strip(),
                phone=row.phone,
                email=row.email,
                property_type=row.property_type,
                location=row.location.strip(),
                budget=row.budget,
                source=LeadSource(row.source),
                tags=row.tags,
                campaign_id=campaign_id,
                call_attempts=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            leads.append(lead)

        logger.info(
            f"Converted {len(leads)} CSV rows to Lead models",
            campaign_id=campaign_id
        )

        return leads

    async def generate_sample_csv(self) -> str:
        """
        Generate a sample CSV template for lead import.

        Returns:
            CSV content as string
        """
        sample_data = [
            {
                'name': 'Rajesh Kumar',
                'phone': '9876543210',
                'email': 'rajesh.kumar@example.com',
                'property_type': '2BHK',
                'location': 'Gurgaon',
                'budget': '5000000',
                'source': 'website',
                'tags': 'first-time-buyer,urgent'
            },
            {
                'name': 'Priya Sharma',
                'phone': '9123456789',
                'email': 'priya.sharma@example.com',
                'property_type': '3BHK',
                'location': 'Noida',
                'budget': '7500000',
                'source': 'referral',
                'tags': 'investor'
            },
            {
                'name': 'Amit Patel',
                'phone': '9988776655',
                'email': '',
                'property_type': '4BHK',
                'location': 'Bangalore',
                'budget': '12000000',
                'source': 'advertisement',
                'tags': ''
            }
        ]

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=list(sample_data[0].keys())
        )
        writer.writeheader()
        writer.writerows(sample_data)

        return output.getvalue()

    def validate_csv_format(self, file_content: bytes) -> Tuple[bool, Optional[str]]:
        """
        Quick validation of CSV format without full parsing.

        Args:
            file_content: Raw CSV file bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            content_str = file_content.decode('utf-8')
            df = pd.read_csv(io.StringIO(content_str), nrows=1)

            # Normalize column names
            df.columns = df.columns.str.lower().str.strip()

            # Check required columns
            missing_columns = self.required_columns - set(df.columns)
            if missing_columns:
                return False, f"Missing required columns: {', '.join(missing_columns)}"

            return True, None

        except UnicodeDecodeError:
            return False, "Invalid file encoding. Please use UTF-8."
        except Exception as e:
            return False, f"Invalid CSV format: {str(e)}"
