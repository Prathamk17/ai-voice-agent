"""
Debug endpoints for monitoring in-memory session data.

These endpoints provide visibility into active conversation sessions
when Redis is not available and in-memory storage is being used.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime
import json

from src.websocket.session_manager import SessionManager
from src.utils.logger import StructuredLogger
from src.database.connection import get_async_session_maker
from src.models.call_session import CallSession
from sqlalchemy import select

logger = StructuredLogger(__name__)
router = APIRouter()

# Initialize session manager
session_manager = SessionManager()


@router.get("/sessions")
async def get_all_sessions() -> Dict[str, Any]:
    """
    Get all active conversation sessions.

    Equivalent to Redis CLI: KEYS "conversation:*"

    Returns:
        Dict containing:
        - count: Number of active sessions
        - sessions: List of session call_sids
        - storage_type: "redis" or "in-memory"
    """
    try:
        session_ids = await session_manager.get_all_active_sessions()

        return {
            "count": len(session_ids),
            "sessions": session_ids,
            "storage_type": "in-memory" if not session_manager.redis_available else "redis",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Failed to get active sessions", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{call_sid}")
async def get_session_details(call_sid: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific session.

    Equivalent to Redis CLI: GET "conversation:<call_sid>"

    Args:
        call_sid: The Exotel call SID

    Returns:
        Complete session data including:
        - call_sid
        - lead context (name, phone, property_type, etc.)
        - transcript (full conversation history)
        - collected_data (extracted information)
        - conversation_stage
        - timestamps
    """
    try:
        session = await session_manager.get_session(call_sid)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session not found: {call_sid}")

        return {
            "call_sid": session.call_sid,
            "lead_id": session.lead_id,
            "lead_name": session.lead_name,
            "lead_phone": session.lead_phone,
            "property_type": session.property_type,
            "location": session.location,
            "budget": session.budget,
            "source": session.source,
            "conversation_stage": session.conversation_stage.value if session.conversation_stage else None,
            "transcript": session.transcript_history,
            "collected_data": session.collected_data,
            "call_outcome": session.call_outcome,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "last_interaction_time": session.last_interaction_time.isoformat() if session.last_interaction_time else None,
            "storage_type": "in-memory" if not session_manager.redis_available else "redis"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get session details", call_sid=call_sid, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{call_sid}/transcript")
async def get_session_transcript(call_sid: str) -> Dict[str, Any]:
    """
    Get only the transcript for a specific session.

    Useful for monitoring conversation progress in real-time.

    Args:
        call_sid: The Exotel call SID

    Returns:
        Transcript array with speaker, text, and timestamps
    """
    try:
        session = await session_manager.get_session(call_sid)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session not found: {call_sid}")

        return {
            "call_sid": call_sid,
            "transcript": session.transcript_history,
            "message_count": len(session.transcript_history),
            "last_updated": session.last_interaction_time.isoformat() if session.last_interaction_time else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get transcript", call_sid=call_sid, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{call_sid}/collected-data")
async def get_session_collected_data(call_sid: str) -> Dict[str, Any]:
    """
    Get only the collected data for a specific session.

    Shows what information has been extracted from the conversation.

    Args:
        call_sid: The Exotel call SID

    Returns:
        Collected data dictionary
    """
    try:
        session = await session_manager.get_session(call_sid)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session not found: {call_sid}")

        return {
            "call_sid": call_sid,
            "collected_data": session.collected_data,
            "fields_collected": list(session.collected_data.keys()) if session.collected_data else [],
            "last_updated": session.last_interaction_time.isoformat() if session.last_interaction_time else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get collected data", call_sid=call_sid, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage-status")
async def get_storage_status() -> Dict[str, Any]:
    """
    Check current storage backend status.

    Returns:
        Information about whether using Redis or in-memory storage
    """
    storage_type = "redis" if session_manager.redis_available else "in-memory"

    # Get memory stats if using in-memory
    memory_sessions = []
    if not session_manager.redis_available:
        memory_sessions = list(session_manager._memory_store.keys())

    return {
        "storage_type": storage_type,
        "redis_available": session_manager.redis_available,
        "in_memory_sessions": memory_sessions,
        "session_count": len(memory_sessions) if not session_manager.redis_available else "unknown (using redis)",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# HISTORICAL DATA ENDPOINTS (Query PostgreSQL Database)
# ============================================================================

@router.get("/history/call-sessions")
async def get_historical_call_sessions(limit: int = 10) -> Dict[str, Any]:
    """
    Get recent call sessions from PostgreSQL database.

    This retrieves completed calls that have been persisted,
    unlike /sessions which only shows active in-memory sessions.

    Args:
        limit: Number of recent calls to retrieve (default: 10)

    Returns:
        List of recent call sessions with basic info
    """
    try:
        async_session_maker = get_async_session_maker()

        async with async_session_maker() as db:
            result = await db.execute(
                select(CallSession)
                .order_by(CallSession.ended_at.desc())
                .limit(limit)
            )
            call_sessions = result.scalars().all()

            sessions_data = []
            for cs in call_sessions:
                sessions_data.append({
                    "call_sid": cs.call_sid,
                    "lead_id": cs.lead_id,
                    "status": cs.status.value if hasattr(cs.status, 'value') else cs.status,
                    "outcome": cs.outcome.value if cs.outcome and hasattr(cs.outcome, 'value') else cs.outcome,
                    "duration_seconds": cs.duration_seconds,
                    "initiated_at": cs.initiated_at.isoformat() if cs.initiated_at else None,
                    "ended_at": cs.ended_at.isoformat() if cs.ended_at else None,
                    "has_transcript": bool(cs.full_transcript),
                    "has_collected_data": bool(cs.collected_data)
                })

            return {
                "count": len(sessions_data),
                "call_sessions": sessions_data,
                "source": "postgresql",
                "timestamp": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error("Failed to get historical call sessions", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/call-sessions/{call_sid}")
async def get_historical_call_session(call_sid: str) -> Dict[str, Any]:
    """
    Get complete details for a specific call from PostgreSQL database.

    This retrieves the full call data including transcript and collected data,
    even after the session has been cleaned up from memory.

    Args:
        call_sid: The Exotel call SID

    Returns:
        Complete call session data including transcript and collected data
    """
    try:
        async_session_maker = get_async_session_maker()

        async with async_session_maker() as db:
            result = await db.execute(
                select(CallSession).where(CallSession.call_sid == call_sid)
            )
            call_session = result.scalar_one_or_none()

            if not call_session:
                raise HTTPException(
                    status_code=404,
                    detail=f"Call session not found in database: {call_sid}"
                )

            # Parse JSON fields
            transcript = None
            if call_session.full_transcript:
                try:
                    transcript = json.loads(call_session.full_transcript)
                except json.JSONDecodeError:
                    transcript = call_session.full_transcript

            collected_data = None
            if call_session.collected_data:
                try:
                    collected_data = json.loads(call_session.collected_data)
                except json.JSONDecodeError:
                    collected_data = call_session.collected_data

            return {
                "call_sid": call_session.call_sid,
                "lead_id": call_session.lead_id,
                "status": call_session.status.value if hasattr(call_session.status, 'value') else call_session.status,
                "outcome": call_session.outcome.value if call_session.outcome and hasattr(call_session.outcome, 'value') else call_session.outcome,
                "duration_seconds": call_session.duration_seconds,
                "transcript": transcript,
                "collected_data": collected_data,
                "recording_url": call_session.recording_url,
                "initiated_at": call_session.initiated_at.isoformat() if call_session.initiated_at else None,
                "answered_at": call_session.answered_at.isoformat() if call_session.answered_at else None,
                "ended_at": call_session.ended_at.isoformat() if call_session.ended_at else None,
                "source": "postgresql",
                "timestamp": datetime.utcnow().isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get historical call session", call_sid=call_sid, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/call-sessions/{call_sid}/transcript")
async def get_historical_transcript(call_sid: str) -> Dict[str, Any]:
    """
    Get only the transcript for a specific call from PostgreSQL database.

    This is useful for retrieving transcripts after the session has been
    cleaned up from memory.

    Args:
        call_sid: The Exotel call SID

    Returns:
        Transcript array with speaker, text, and timestamps
    """
    try:
        async_session_maker = get_async_session_maker()

        async with async_session_maker() as db:
            result = await db.execute(
                select(CallSession).where(CallSession.call_sid == call_sid)
            )
            call_session = result.scalar_one_or_none()

            if not call_session:
                raise HTTPException(
                    status_code=404,
                    detail=f"Call session not found in database: {call_sid}"
                )

            if not call_session.full_transcript:
                return {
                    "call_sid": call_sid,
                    "transcript": [],
                    "message_count": 0,
                    "message": "No transcript available for this call",
                    "source": "postgresql"
                }

            # Parse transcript JSON
            try:
                transcript = json.loads(call_session.full_transcript)
            except json.JSONDecodeError:
                transcript = [{"speaker": "system", "text": call_session.full_transcript, "timestamp": None}]

            return {
                "call_sid": call_sid,
                "transcript": transcript,
                "message_count": len(transcript) if isinstance(transcript, list) else 0,
                "ended_at": call_session.ended_at.isoformat() if call_session.ended_at else None,
                "source": "postgresql",
                "timestamp": datetime.utcnow().isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get historical transcript", call_sid=call_sid, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
