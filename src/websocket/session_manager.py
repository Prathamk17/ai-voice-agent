"""
Session manager for WebSocket conversations.

Manages conversation state in Redis during active calls.
"""

from typing import Optional, Dict, Any
import json
from datetime import datetime

from src.database.connection import redis_client, get_redis_client
from src.models.conversation import ConversationSession, ConversationStage
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class SessionManager:
    """
    Manage WebSocket session state in Redis
    """

    def __init__(self):
        self.session_prefix = "session:"
        self.session_ttl = 3600  # 1 hour

    async def _get_redis(self):
        """Get Redis client dynamically"""
        return await get_redis_client()

    async def create_session(
        self,
        call_sid: str,
        lead_context: Dict[str, Any]
    ) -> ConversationSession:
        """
        Create new conversation session

        Args:
            call_sid: Exotel call SID
            lead_context: Lead information

        Returns:
            New ConversationSession
        """
        session = ConversationSession(
            call_sid=call_sid,
            lead_id=lead_context.get("lead_id", 0),
            lead_name=lead_context.get("lead_name", "Customer"),
            lead_phone=lead_context.get("phone", ""),
            property_type=lead_context.get("property_type"),
            location=lead_context.get("location"),
            budget=lead_context.get("budget"),
            source=lead_context.get("source"),
            conversation_stage=ConversationStage.INTRO
        )

        await self.save_session(session)

        logger.info(
            "Session created",
            call_sid=call_sid,
            lead_id=lead_context.get("lead_id")
        )

        return session

    async def get_session(self, call_sid: str) -> Optional[ConversationSession]:
        """
        Get session from Redis

        Args:
            call_sid: Call SID

        Returns:
            ConversationSession if found, None otherwise
        """
        key = f"{self.session_prefix}{call_sid}"
        redis = await self._get_redis()

        data = await redis.get(key)

        if not data:
            logger.warning("Session not found", call_sid=call_sid)
            return None

        session_dict = json.loads(data)
        return ConversationSession.from_redis_dict(session_dict)

    async def save_session(self, session: ConversationSession):
        """
        Save session to Redis

        Args:
            session: Session to save
        """
        key = f"{self.session_prefix}{session.call_sid}"
        redis = await self._get_redis()

        # Convert to dict for Redis storage
        session_dict = session.to_redis_dict()

        await redis.set(
            key,
            json.dumps(session_dict),
            ex=self.session_ttl
        )

    async def update_session(
        self,
        call_sid: str,
        updates: Dict[str, Any]
    ):
        """
        Update specific session fields

        Args:
            call_sid: Call SID
            updates: Dictionary of fields to update
        """
        session = await self.get_session(call_sid)

        if not session:
            logger.warning("Session not found for update", call_sid=call_sid)
            return

        # Apply updates
        for field, value in updates.items():
            if hasattr(session, field):
                setattr(session, field, value)

        session.last_interaction_time = datetime.utcnow()

        await self.save_session(session)

    async def delete_session(self, call_sid: str):
        """
        Delete session from Redis

        Args:
            call_sid: Call SID
        """
        key = f"{self.session_prefix}{call_sid}"
        redis = await self._get_redis()
        await redis.delete(key)

        logger.info("Session deleted", call_sid=call_sid)

    async def add_to_transcript(
        self,
        call_sid: str,
        speaker: str,
        text: str
    ):
        """
        Add exchange to transcript

        Args:
            call_sid: Call SID
            speaker: "ai" or "user"
            text: Spoken text
        """
        session = await self.get_session(call_sid)

        if not session:
            return

        session.transcript_history.append({
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.utcnow().isoformat()
        })

        await self.save_session(session)

    async def get_all_active_sessions(self) -> list[str]:
        """
        Get all active session IDs

        Returns:
            List of call SIDs
        """
        pattern = f"{self.session_prefix}*"
        keys = []
        redis = await self._get_redis()

        async for key in redis.scan_iter(match=pattern):
            call_sid = key.decode('utf-8').replace(self.session_prefix, '')
            keys.append(call_sid)

        return keys
