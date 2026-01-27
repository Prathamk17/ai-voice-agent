"""
Debug endpoints for monitoring in-memory session data.

These endpoints provide visibility into active conversation sessions
when Redis is not available and in-memory storage is being used.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime

from src.websocket.session_manager import SessionManager
from src.utils.logger import StructuredLogger

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
