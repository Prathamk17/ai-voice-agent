"""
Database connection setup for PostgreSQL and Redis.
Handles async SQLAlchemy engine and Redis client initialization.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import redis.asyncio as redis
from typing import AsyncGenerator

# Create base for models
Base = declarative_base()

# Global database engine and session maker
engine = None
async_session_maker = None
redis_client = None


async def init_db(database_url: str) -> None:
    """
    Initialize database connection and create tables.

    Args:
        database_url: PostgreSQL connection string (must use asyncpg driver)
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

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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


async def init_redis(redis_url: str) -> None:
    """
    Initialize Redis connection for session storage.

    Args:
        redis_url: Redis connection string (e.g., redis://localhost:6379)
    """
    global redis_client

    redis_client = await redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=False,  # We'll handle encoding ourselves
        socket_connect_timeout=5,
        socket_keepalive=True,
        health_check_interval=30,
    )


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
