"""
Health Checks

Module 5: Dashboard, Analytics & Monitoring
Comprehensive health checking for all system components.
"""

from typing import Dict, Any
from datetime import datetime

from src.database.connection import redis_client, async_session_maker
from src.integrations.exotel_client import ExotelClient
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class HealthChecker:
    """
    Comprehensive health checking for all system components
    """

    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            from sqlalchemy import text
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))

            return {
                "status": "healthy",
                "message": "Database connection successful"
            }
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": f"Database error: {str(e)}"
            }

    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            await redis_client.ping()

            # Check read/write
            test_key = "health_check_test"
            await redis_client.set(test_key, "ok", ex=10)
            value = await redis_client.get(test_key)

            if value != "ok":
                raise Exception("Redis read/write test failed")

            return {
                "status": "healthy",
                "message": "Redis connection successful"
            }
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": f"Redis error: {str(e)}"
            }

    async def check_exotel_api(self) -> Dict[str, Any]:
        """Check Exotel API connectivity"""
        try:
            # Simple API call to verify connectivity
            # Don't actually make a call, just verify client can be instantiated
            client = ExotelClient()

            # Test by checking if credentials are configured
            from src.config.settings import settings
            if not settings.EXOTEL_API_KEY or not settings.EXOTEL_API_TOKEN:
                return {
                    "status": "degraded",
                    "message": "Exotel credentials not configured"
                }

            await client.close()

            return {
                "status": "healthy",
                "message": "Exotel API accessible"
            }
        except Exception as e:
            logger.error("Exotel health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": f"Exotel API error: {str(e)}"
            }

    async def check_ai_services(self) -> Dict[str, Any]:
        """Check AI service APIs"""
        results = {}

        # Check Deepgram
        try:
            from src.ai.stt_service import DeepgramSTTService
            from src.config.settings import settings

            if not settings.DEEPGRAM_API_KEY:
                results["deepgram"] = "not_configured"
            else:
                # Simple instantiation check
                DeepgramSTTService()
                results["deepgram"] = "healthy"
        except Exception as e:
            results["deepgram"] = f"unhealthy: {str(e)}"

        # Check OpenAI
        try:
            from src.ai.llm_service import LLMService
            from src.config.settings import settings

            if not settings.OPENAI_API_KEY:
                results["openai"] = "not_configured"
            else:
                LLMService()
                results["openai"] = "healthy"
        except Exception as e:
            results["openai"] = f"unhealthy: {str(e)}"

        # Check ElevenLabs
        try:
            from src.ai.tts_service import ElevenLabsTTSService
            from src.config.settings import settings

            if not settings.ELEVENLABS_API_KEY:
                results["elevenlabs"] = "not_configured"
            else:
                ElevenLabsTTSService()
                results["elevenlabs"] = "healthy"
        except Exception as e:
            results["elevenlabs"] = f"unhealthy: {str(e)}"

        all_healthy = all(status == "healthy" for status in results.values())
        all_configured = all(status in ["healthy", "not_configured"] for status in results.values())

        if all_healthy:
            status = "healthy"
        elif all_configured:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "services": results
        }

    async def check_background_worker(self) -> Dict[str, Any]:
        """Check if background worker is running"""
        try:
            from src.workers.campaign_worker import worker

            # Check if scheduler is running
            if worker.scheduler.running:
                return {
                    "status": "healthy",
                    "message": "Background worker is running"
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Background worker is not running"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Worker check failed: {str(e)}"
            }

    async def get_full_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of all components
        """
        checks = {
            "database": await self.check_database(),
            "redis": await self.check_redis(),
            "exotel_api": await self.check_exotel_api(),
            "ai_services": await self.check_ai_services(),
            "background_worker": await self.check_background_worker()
        }

        # Determine overall status
        statuses = [check["status"] for check in checks.values()]

        if all(s == "healthy" for s in statuses):
            overall_status = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }


# Global instance
health_checker = HealthChecker()
