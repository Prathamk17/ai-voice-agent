"""
Email monitoring service for real-time lead detection.
Polls email inbox for new lead notifications and triggers immediate calls.
"""

import asyncio
import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import Optional, List, Set
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database.connection import get_async_session_maker
from src.models.email_lead import EmailLead, ParsedEmailResult
from src.models.lead import Lead, LeadSource
from src.services.email_parsers import EmailParserFactory
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmailMonitor:
    """
    Email monitoring service for real-time lead detection.

    Responsibilities:
    - Connect to email inbox via IMAP
    - Poll for new lead notification emails
    - Parse emails to extract lead information
    - Create leads in database
    - Trigger immediate calls to leads
    - Track processed emails to avoid duplicates
    """

    def __init__(self, poll_interval_seconds: int = None):
        """
        Initialize email monitor.

        Args:
            poll_interval_seconds: How often to check for new emails (default from settings)
        """
        self.poll_interval = poll_interval_seconds or settings.EMAIL_POLL_INTERVAL_SECONDS
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self.parser_factory = EmailParserFactory()
        self.processed_message_ids: Set[str] = set()  # Track processed emails

    async def start(self):
        """Start the email monitoring background task."""
        if self.running:
            logger.warning("Email monitor is already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._run_monitor())
        logger.info(
            "Email monitor started",
            poll_interval_seconds=self.poll_interval,
            email_address=settings.EMAIL_ADDRESS
        )

    async def stop(self):
        """Stop the email monitoring background task."""
        if not self.running:
            return

        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Email monitor stopped")

    async def _run_monitor(self):
        """Main monitoring loop."""
        while self.running:
            try:
                await self._check_emails()
            except Exception as e:
                logger.error(f"Error in email monitor: {str(e)}")

            # Wait before next check
            await asyncio.sleep(self.poll_interval)

    async def _check_emails(self):
        """Check for new emails and process them."""
        try:
            # Run IMAP operations in thread pool (IMAP is blocking)
            loop = asyncio.get_event_loop()
            new_emails = await loop.run_in_executor(None, self._fetch_new_emails)

            if not new_emails:
                return

            logger.info(f"Found {len(new_emails)} new email(s)")

            # Process each email
            for email_data in new_emails:
                try:
                    await self._process_email(email_data)
                except Exception as e:
                    logger.error(
                        f"Failed to process email: {str(e)}",
                        subject=email_data.get('subject', 'Unknown')
                    )

        except Exception as e:
            logger.error(f"Failed to check emails: {str(e)}")

    def _fetch_new_emails(self) -> List[dict]:
        """
        Fetch new unread emails from inbox via IMAP.

        Returns:
            List of email data dictionaries

        Note: This is a blocking operation, should be run in executor
        """
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(settings.EMAIL_IMAP_HOST, settings.EMAIL_IMAP_PORT)
            mail.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)

            # Select inbox
            mail.select(settings.EMAIL_FOLDER)

            # Search for unread emails
            status, messages = mail.search(None, 'UNSEEN')

            if status != 'OK':
                logger.error("Failed to search for emails")
                mail.logout()
                return []

            email_ids = messages[0].split()

            if not email_ids:
                mail.logout()
                return []

            emails = []

            # Fetch each email
            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, '(RFC822)')

                if status != 'OK':
                    continue

                # Parse email
                msg = email.message_from_bytes(msg_data[0][1])

                # Extract subject
                subject = self._decode_header(msg.get('Subject', ''))

                # Extract body
                body = self._get_email_body(msg)

                # Get message ID
                message_id = msg.get('Message-ID', f'unknown-{email_id.decode()}')

                # Get received time
                date_str = msg.get('Date', '')
                received_at = email.utils.parsedate_to_datetime(date_str) if date_str else datetime.utcnow()

                emails.append({
                    'email_id': email_id,
                    'subject': subject,
                    'body': body,
                    'message_id': message_id,
                    'received_at': received_at,
                })

                # Mark as read if configured
                if settings.EMAIL_MARK_AS_READ:
                    mail.store(email_id, '+FLAGS', '\\Seen')

            mail.logout()
            return emails

        except Exception as e:
            logger.error(f"Error fetching emails via IMAP: {str(e)}")
            return []

    def _decode_header(self, header: str) -> str:
        """Decode email header."""
        if not header:
            return ""

        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                decoded_parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
            else:
                decoded_parts.append(part)

        return ''.join(decoded_parts)

    def _get_email_body(self, msg) -> str:
        """Extract email body from message."""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                # Get text/plain or text/html
                if content_type == "text/plain" or content_type == "text/html":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break  # Use first text part
                    except:
                        continue
        else:
            # Not multipart
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body = str(msg.get_payload())

        return body

    async def _process_email(self, email_data: dict):
        """
        Process a single email: parse, create lead, trigger call.

        Args:
            email_data: Email data dictionary
        """
        message_id = email_data['message_id']

        # Skip if already processed
        if message_id in self.processed_message_ids:
            logger.debug(f"Skipping already processed email: {message_id}")
            return

        subject = email_data['subject']
        body = email_data['body']
        received_at = email_data['received_at']

        # Skip old emails (more than 7 days old)
        from datetime import timedelta, timezone
        now = datetime.now(timezone.utc)
        email_age = now - received_at
        if email_age > timedelta(days=7):
            logger.debug(
                f"Skipping old email (age: {email_age.days} days)",
                subject=subject[:100],
                received_at=received_at
            )
            # Mark as processed to avoid checking again
            self.processed_message_ids.add(message_id)
            return

        # Skip emails that are clearly not real estate leads
        skip_keywords = [
            'linkedin', 'notification', 'weekly digest', 'recently posted',
            'tradingview', 'cursor', 'new message', 'add connection',
            'follow', 'event happening', 'register now', 'act fast',
            'you have 1 new message', 'your turn',
        ]
        subject_lower = subject.lower()
        body_lower = body.lower()

        # Skip if subject or body contains skip keywords and no real estate indicators
        real_estate_keywords = [
            'property', 'bhk', 'apartment', 'villa', 'flat', 'real estate',
            'magicbricks', '99acres', 'housing', 'site visit', 'buyer',
            'enquiry', 'enquire', 'neco park', 'kharadi', 'pune'
        ]

        has_skip_keyword = any(kw in subject_lower or kw in body_lower for kw in skip_keywords)
        has_real_estate_keyword = any(kw in subject_lower or kw in body_lower for kw in real_estate_keywords)

        if has_skip_keyword and not has_real_estate_keyword:
            logger.debug(
                f"Skipping non-lead email",
                subject=subject[:100]
            )
            # Mark as processed to avoid checking again
            self.processed_message_ids.add(message_id)
            return

        logger.info(
            "Processing email",
            subject=subject[:100],
            received_at=received_at
        )

        # Parse email to extract lead
        result: ParsedEmailResult = self.parser_factory.parse_email(
            subject=subject,
            body=body,
            message_id=message_id,
            received_at=received_at
        )

        if not result.success or not result.lead:
            logger.warning(
                "Failed to parse email",
                error=result.error,
                subject=subject[:100]
            )
            return

        email_lead: EmailLead = result.lead

        # Create lead in database
        try:
            lead = await self._create_lead_from_email(email_lead)

            if lead:
                # Mark as processed
                self.processed_message_ids.add(message_id)

                logger.info(
                    "Successfully created lead from email",
                    lead_id=lead.id,
                    lead_name=lead.name,
                    phone=lead.phone,
                    source=lead.source
                )

                # Trigger immediate call
                await self._trigger_immediate_call(lead)

        except Exception as e:
            logger.error(
                f"Failed to create lead from email: {str(e)}",
                email_lead_name=email_lead.name,
                phone=email_lead.phone
            )

    async def _create_lead_from_email(self, email_lead: EmailLead) -> Optional[Lead]:
        """
        Create Lead model from parsed EmailLead.

        Args:
            email_lead: Parsed email lead data

        Returns:
            Created Lead or None if failed
        """
        try:
            async_session_maker = get_async_session_maker()
            async with async_session_maker() as session:
                # Check if lead with same phone already exists
                from sqlalchemy import select
                from src.models.lead import Lead as LeadModel

                stmt = select(LeadModel).where(LeadModel.phone == email_lead.phone)
                result = await session.execute(stmt)
                existing_lead = result.scalar_one_or_none()

                if existing_lead:
                    logger.info(
                        "Lead with phone already exists, skipping",
                        phone=email_lead.phone,
                        existing_lead_id=existing_lead.id
                    )
                    return existing_lead

                # Map email source to LeadSource enum
                source_mapping = {
                    'magicbricks': LeadSource.ADVERTISEMENT,
                    '99acres': LeadSource.ADVERTISEMENT,
                    'housing': LeadSource.ADVERTISEMENT,
                    'website': LeadSource.WEBSITE,
                    'referral': LeadSource.REFERRAL,
                    'other': LeadSource.WEBSITE,
                }
                lead_source = source_mapping.get(email_lead.source, LeadSource.WEBSITE)

                # Get or create the default email leads campaign
                from src.services.email_lead_campaign import get_email_leads_campaign
                email_campaign = await get_email_leads_campaign(session)

                # Create new lead
                lead = LeadModel(
                    name=email_lead.name,
                    phone=email_lead.phone,
                    email=email_lead.email,
                    property_type=email_lead.property_type,
                    location=email_lead.location,
                    budget=email_lead.budget,
                    source=lead_source,
                    notes=email_lead.message or f"Email lead from {email_lead.source}",
                    tags=email_lead.tags,
                    call_attempts=0,
                    campaign_id=email_campaign.id,  # Associate with email leads campaign
                )

                session.add(lead)
                await session.commit()
                await session.refresh(lead)

                # Update campaign lead count
                from src.services.email_lead_campaign import EmailLeadCampaignService
                campaign_service = EmailLeadCampaignService(session)
                await campaign_service.increment_lead_count(email_campaign)

                return lead

        except Exception as e:
            logger.error(f"Failed to create lead in database: {str(e)}")
            return None

    async def _trigger_immediate_call(self, lead: Lead):
        """
        Trigger immediate call to the lead by creating a ScheduledCall record.

        Args:
            lead: Lead to call

        The background worker will automatically pick up the scheduled call
        and execute it via Exotel.
        """
        # Check if auto-calling is enabled
        if not settings.EMAIL_LEADS_AUTO_CALL:
            logger.info(
                "Email leads auto-calling is disabled",
                lead_id=lead.id,
                lead_name=lead.name
            )
            return

        logger.info(
            "🔔 IMMEDIATE CALL TRIGGER - Scheduling call",
            lead_id=lead.id,
            lead_name=lead.name,
            phone=lead.phone,
            location=lead.location,
            property_type=lead.property_type
        )

        try:
            async_session_maker = get_async_session_maker()
            async with async_session_maker() as session:
                from src.services.call_scheduler import CallScheduler
                from src.models.scheduled_call import ScheduledCall, ScheduledCallStatus

                scheduler = CallScheduler(session)

                # Get next available calling slot (respects calling hours)
                current_time = datetime.utcnow()
                scheduled_time = scheduler._get_next_available_slot(
                    current_time,
                    calling_hours_start=settings.CALLING_HOURS_START,
                    calling_hours_end=settings.CALLING_HOURS_END
                )

                # Create ScheduledCall record
                scheduled_call = ScheduledCall(
                    campaign_id=lead.campaign_id,  # Email leads campaign
                    lead_id=lead.id,
                    scheduled_time=scheduled_time,
                    status=ScheduledCallStatus.PENDING,
                    max_attempts=settings.EMAIL_LEADS_MAX_RETRY_ATTEMPTS,
                    attempt_number=1
                )

                session.add(scheduled_call)
                await session.commit()
                await session.refresh(scheduled_call)

                # Check if it's within calling hours
                current_hour = datetime.utcnow().hour
                is_within_hours = (
                    settings.CALLING_HOURS_START <= current_hour < settings.CALLING_HOURS_END
                )

                if is_within_hours and scheduled_time <= datetime.utcnow():
                    logger.info(
                        "✅ Call scheduled for IMMEDIATE execution",
                        lead_id=lead.id,
                        lead_name=lead.name,
                        phone=lead.phone,
                        scheduled_call_id=scheduled_call.id,
                        scheduled_time=scheduled_time.isoformat(),
                        message="Background worker will pick this up in the next 30 seconds"
                    )
                else:
                    logger.info(
                        "⏰ Call scheduled for later",
                        lead_id=lead.id,
                        lead_name=lead.name,
                        phone=lead.phone,
                        scheduled_call_id=scheduled_call.id,
                        scheduled_time=scheduled_time.isoformat(),
                        reason="Outside calling hours" if not is_within_hours else "Scheduled for future"
                    )

        except Exception as e:
            logger.error(
                "Failed to schedule call for email lead",
                lead_id=lead.id,
                error=str(e)
            )


# Global email monitor instance
_email_monitor: Optional[EmailMonitor] = None


def get_email_monitor() -> EmailMonitor:
    """Get or create the global email monitor instance."""
    global _email_monitor
    if _email_monitor is None:
        _email_monitor = EmailMonitor()
    return _email_monitor


async def start_email_monitor():
    """Start the global email monitor."""
    monitor = get_email_monitor()
    await monitor.start()


async def stop_email_monitor():
    """Stop the global email monitor."""
    monitor = get_email_monitor()
    await monitor.stop()
