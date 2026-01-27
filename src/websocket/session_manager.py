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
    Manage WebSocket session state in Redis (with in-memory fallback)
    """

    # Class-level in-memory store (shared across all instances)
    _shared_memory_store: Dict[str, ConversationSession] = {}

    def __init__(self):
        self.session_prefix = "session:"
        self.session_ttl = 3600  # 1 hour
        self.redis_available = True
        # Use class-level shared memory store
        self._memory_store = SessionManager._shared_memory_store

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
        Get session from Redis (or in-memory if Redis unavailable)

        Args:
            call_sid: Call SID

        Returns:
            ConversationSession if found, None otherwise
        """
        # Try Redis first
        if self.redis_available:
            try:
                key = f"{self.session_prefix}{call_sid}"
                redis = await self._get_redis()

                data = await redis.get(key)

                if data:
                    session_dict = json.loads(data)
                    return ConversationSession.from_redis_dict(session_dict)
            except Exception as e:
                logger.warning(f"Redis get failed, checking memory: {e}")
                self.redis_available = False

        # Fallback to in-memory storage
        session = self._memory_store.get(call_sid)
        if not session:
            logger.warning("Session not found", call_sid=call_sid)
        return session

    async def save_session(self, session: ConversationSession):
        """
        Save session to Redis (or in-memory if Redis fails)

        Args:
            session: Session to save
        """
        # Try Redis first
        if self.redis_available:
            try:
                key = f"{self.session_prefix}{session.call_sid}"
                redis = await self._get_redis()

                # Convert to dict for Redis storage
                session_dict = session.to_redis_dict()

                await redis.set(
                    key,
                    json.dumps(session_dict),
                    ex=self.session_ttl
                )
                return
            except Exception as e:
                logger.warning(f"Redis save failed, using in-memory storage: {e}")
                self.redis_available = False

        # Fallback to in-memory storage
        self._memory_store[session.call_sid] = session
        logger.debug(f"Session saved to memory: {session.call_sid}")

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
        Delete session from Redis (or in-memory)

        Args:
            call_sid: Call SID
        """
        # Try Redis first
        if self.redis_available:
            try:
                key = f"{self.session_prefix}{call_sid}"
                redis = await self._get_redis()
                await redis.delete(key)
                logger.info("Session deleted from Redis", call_sid=call_sid)
                return
            except Exception as e:
                logger.warning(f"Redis delete failed, removing from memory: {e}")
                self.redis_available = False

        # Fallback to in-memory storage
        if call_sid in self._memory_store:
            del self._memory_store[call_sid]
            logger.info("Session deleted from memory", call_sid=call_sid)

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
        Get all active session IDs (from Redis or in-memory)

        Returns:
            List of call SIDs
        """
        keys = []

        # Try Redis first
        if self.redis_available:
            try:
                pattern = f"{self.session_prefix}*"
                redis = await self._get_redis()

                async for key in redis.scan_iter(match=pattern):
                    call_sid = key.decode('utf-8').replace(self.session_prefix, '')
                    keys.append(call_sid)
                return keys
            except Exception as e:
                logger.warning(f"Redis scan failed, using memory: {e}")
                self.redis_available = False

        # Fallback to in-memory storage
        return list(self._memory_store.keys())
