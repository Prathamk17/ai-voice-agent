"""
Database connection setup for PostgreSQL and Redis.
Handles async SQLAlchemy engine and Redis client initialization.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import redis.asyncio as redis
from typing import AsyncGenerator
import asyncio
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Create base for models
Base = declarative_base()

# Global database engine and session maker
engine = None
async_session_maker = None
redis_client = None


async def init_db(database_url: str, max_retries: int = 5, retry_delay: int = 2) -> None:
    """
    Initialize database connection and create tables with retry logic.

    Args:
        database_url: PostgreSQL connection string (must use asyncpg driver)
        max_retries: Maximum number of connection attempts (default: 5)
        retry_delay: Initial delay between retries in seconds (default: 2)
    """
    global engine, async_session_maker

    engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL query logging in development
        pool_size=20,
        max_overflow=40,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Import models to register them with Base
    from src.models.lead import Lead
    from src.models.call_session import CallSession
    from src.models.scheduled_call import ScheduledCall

    # Create tables with retry logic (Railway services may not be ready immediately)
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempting database connection (attempt {attempt}/{max_retries})")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
            return
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait_time = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                logger.warning(
                    f"Database connection failed (attempt {attempt}/{max_retries}): {str(e)}. "
                    f"Retrying in {wait_time} seconds..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Database connection failed after {max_retries} attempts: {str(e)}")

    # If we get here, all retries failed
    raise last_error


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI endpoints to get database session.

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...

    Yields:
        AsyncSession: Database session
    """
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_redis(redis_url: str, max_retries: int = 5, retry_delay: int = 2) -> None:
    """
    Initialize Redis connection for session storage with retry logic.

    Args:
        redis_url: Redis connection string (e.g., redis://localhost:6379)
        max_retries: Maximum number of connection attempts (default: 5)
        retry_delay: Initial delay between retries in seconds (default: 2)
    """
    global redis_client

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempting Redis connection (attempt {attempt}/{max_retries})")
            redis_client = await redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            # Test the connection
            await redis_client.ping()
            logger.info("Redis connection established successfully")
            return
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait_time = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                logger.warning(
                    f"Redis connection failed (attempt {attempt}/{max_retries}): {str(e)}. "
                    f"Retrying in {wait_time} seconds..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Redis connection failed after {max_retries} attempts: {str(e)}")

    # If we get here, all retries failed
    raise last_error


async def get_redis_client() -> redis.Redis:
    """
    Get Redis client instance.

    Returns:
        Redis client
    """
    if redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis_client


def get_async_session_maker():
    """
    Get the async session maker for creating database sessions.

    Used by background tasks that need to create their own sessions.

    Returns:
        async_sessionmaker: Session factory
    """
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return async_session_maker


async def close_db() -> None:
    """
    Close database and Redis connections.
    Should be called on application shutdown.
    """
    global engine, redis_client

    if engine:
        await engine.dispose()

    if redis_client:
        await redis_client.close()
