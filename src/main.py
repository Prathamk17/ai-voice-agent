"""
Main FastAPI application for Real Estate Voice AI Agent.
Entry point for the application.
Build: 2026-01-24-v2
"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from src.config.settings import settings
from src.database.connection import init_db, init_redis, close_db
from src.utils.logger import get_logger
from src.api.health import router as health_router
from src.api.campaigns import router as campaigns_router
from src.api.webhooks import router as webhooks_router
from src.api.analytics import router as analytics_router
from src.api.dashboard import router as dashboard_router
from src.api.exports import router as exports_router
from src.services.campaign_scheduler import start_campaign_scheduler, stop_campaign_scheduler
from src.services.email_monitor import start_email_monitor, stop_email_monitor
from src.workers.campaign_worker import start_worker, stop_worker
from src.websocket.server import websocket_server

# Initialize logger
logger = get_logger(__name__, settings.ENVIRONMENT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting application", environment=settings.ENVIRONMENT)

    try:
        # Initialize database (only if DATABASE_URL is configured)
        if settings.DATABASE_URL:
            await init_db(settings.DATABASE_URL)
            logger.info("Database initialized successfully")
        else:
            logger.warning("Database not configured - skipping database initialization")

        # Initialize Redis (only if REDIS_URL points to actual Redis server)
        try:
            await init_redis(settings.REDIS_URL)
            logger.info("Redis initialized successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed - using in-memory fallback: {e}")

        # Start campaign scheduler (requires database)
        if settings.DATABASE_URL:
            try:
                await start_campaign_scheduler()
                logger.info("Campaign scheduler started")
            except Exception as e:
                logger.warning(f"Campaign scheduler failed to start: {e}")
        else:
            logger.warning("Campaign scheduler disabled - DATABASE_URL not configured")

        # Start email monitor (only if email credentials are configured)
        if settings.EMAIL_ADDRESS and settings.EMAIL_PASSWORD and settings.DATABASE_URL:
            try:
                await start_email_monitor()
                logger.info("Email monitor started - monitoring inbox for new leads")
            except Exception as e:
                logger.warning(f"Email monitor failed to start: {e}")
        else:
            logger.warning("Email monitoring disabled - missing configuration")

        # Start campaign worker for call execution (requires database)
        if settings.DATABASE_URL:
            try:
                start_worker()
                logger.info("Campaign worker started")
            except Exception as e:
                logger.warning(f"Campaign worker failed to start: {e}")
        else:
            logger.warning("Campaign worker disabled - DATABASE_URL not configured")

        logger.info(
            "Application startup complete",
            app_name=settings.APP_NAME,
            port=settings.PORT
        )

    except Exception as e:
        logger.error("Failed to initialize infrastructure", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down application")

    # Stop campaign worker
    try:
        stop_worker()
        logger.info("Campaign worker stopped")
    except Exception as e:
        logger.warning(f"Error stopping campaign worker: {e}")

    # Stop email monitor
    try:
        await stop_email_monitor()
        logger.info("Email monitor stopped")
    except Exception as e:
        logger.warning(f"Error stopping email monitor: {e}")

    # Stop campaign scheduler
    try:
        await stop_campaign_scheduler()
        logger.info("Campaign scheduler stopped")
    except Exception as e:
        logger.warning(f"Error stopping campaign scheduler: {e}")

    # Close database connections
    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.warning(f"Error closing database: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Outbound Voice AI Agent for Real Estate Lead Qualification",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(campaigns_router)
app.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])

# Module 5: Dashboard, Analytics & Monitoring
app.include_router(analytics_router)
app.include_router(dashboard_router)
app.include_router(exports_router)

# Mount static files for dashboard UI
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


# WebSocket endpoint for Exotel voice connections
@app.websocket("/media")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Exotel voice connections.

    Exotel connects to this endpoint when a call is initiated.
    The endpoint handles real-time audio streaming and AI conversation.

    Args:
        websocket: WebSocket connection from Exotel
    """
    await websocket_server.handle_connection(websocket)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with basic service information.

    Returns:
        dict: Service information
    """
    import os
    test_mode = os.getenv("EXOTEL_TEST_MODE", "true").lower() == "true"

    return {
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "version": "1.0.0",
        "test_mode": test_mode,
        "websocket_endpoint": f"{settings.OUR_BASE_URL}{settings.WEBSOCKET_ENDPOINT_PATH}",
        "message": "🧪 Exotel WebSocket testing mode (no AI services)" if test_mode else "🚀 Production mode"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
