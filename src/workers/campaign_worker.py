"""
Background worker for executing scheduled calls.
Runs every 30 seconds to process pending calls.
"""

import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.config.settings import settings
from src.services.call_scheduler import CallScheduler
from src.services.call_executor import CallExecutor
from src.models.scheduled_call import ScheduledCall
from src.utils.logger import get_logger

logger = get_logger(__name__, settings.ENVIRONMENT)


class CampaignWorker:
    """
    Background worker that executes scheduled calls

    Runs every 30 seconds to:
    1. Check for pending calls
    2. Execute calls respecting concurrency limits
    3. Respect calling hours
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

        # Create separate DB engine for background tasks (only if DATABASE_URL is configured)
        if not settings.DATABASE_URL:
            logger.warning("DATABASE_URL not configured - campaign worker disabled")
            self.engine = None
            self.async_session_maker = None
            return

        self.engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            echo=False
        )

        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def process_pending_calls(self):
        """
        Main worker loop - process pending calls
        """
        async with self.async_session_maker() as session:
            try:
                scheduler = CallScheduler(session)
                executor = CallExecutor(session)

                # Get pending calls
                pending_calls = await scheduler.get_pending_calls(
                    limit=100,
                    max_concurrent=settings.MAX_CONCURRENT_CALLS
                )

                if not pending_calls:
                    logger.debug("No pending calls")
                    return

                logger.info(f"Processing {len(pending_calls)} pending calls")

                # Execute calls
                for scheduled_call in pending_calls:
                    try:
                        result = await executor.execute_call(scheduled_call)

                        if result["success"]:
                            logger.info(
                                "Call executed",
                                extra={
                                    "call_sid": result["call_sid"],
                                    "scheduled_call_id": result["scheduled_call_id"]
                                }
                            )
                        else:
                            logger.error(
                                "Call execution failed",
                                extra={
                                    "error": result.get("error"),
                                    "scheduled_call_id": result["scheduled_call_id"]
                                }
                            )

                    except Exception as e:
                        logger.error(
                            "Error executing call",
                            extra={
                                "scheduled_call_id": scheduled_call.id,
                                "error": str(e)
                            }
                        )

                await executor.close()

            except Exception as e:
                logger.error("Worker error", extra={"error": str(e)})

    def start(self):
        """Start the background worker"""
        if not self.engine:
            logger.warning("Campaign worker not started - DATABASE_URL not configured")
            return

        logger.info("Starting campaign worker")

        # Schedule the job to run every 30 seconds
        self.scheduler.add_job(
            self.process_pending_calls,
            'interval',
            seconds=30,
            id='process_pending_calls',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Campaign worker started")

    def stop(self):
        """Stop the background worker"""
        if not self.engine:
            return

        logger.info("Stopping campaign worker")
        self.scheduler.shutdown()


# Global worker instance
worker = CampaignWorker()


# Functions to start/stop worker
def start_worker():
    """Start the campaign worker"""
    worker.start()


def stop_worker():
    """Stop the campaign worker"""
    worker.stop()
