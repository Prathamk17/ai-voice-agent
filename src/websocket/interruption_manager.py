"""
In-memory interruption manager for fast barge-in detection.

Replaces Redis checks with in-memory flags to reduce interruption detection
latency from ~50-100ms (Redis roundtrip) to <1ms (memory access).
"""

from typing import Dict
import threading


class InterruptionManager:
    """
    Thread-safe in-memory manager for interruption flags.

    Used during TTS playback to quickly check if customer has interrupted
    without the latency of Redis roundtrips.
    """

    _flags: Dict[str, bool] = {}
    _lock = threading.Lock()

    @classmethod
    def set_interrupted(cls, call_sid: str) -> None:
        """
        Mark a call as interrupted.

        Args:
            call_sid: Call session ID
        """
        with cls._lock:
            cls._flags[call_sid] = True

    @classmethod
    def check_interrupted(cls, call_sid: str) -> bool:
        """
        Check if a call has been interrupted.

        Args:
            call_sid: Call session ID

        Returns:
            True if interrupted, False otherwise
        """
        with cls._lock:
            return cls._flags.get(call_sid, False)

    @classmethod
    def clear_interrupted(cls, call_sid: str) -> None:
        """
        Clear interruption flag for a call.

        Args:
            call_sid: Call session ID
        """
        with cls._lock:
            cls._flags.pop(call_sid, None)

    @classmethod
    def reset(cls, call_sid: str) -> None:
        """
        Reset interruption state for a call (alias for clear_interrupted).

        Args:
            call_sid: Call session ID
        """
        cls.clear_interrupted(call_sid)

    @classmethod
    def cleanup(cls, call_sid: str) -> None:
        """
        Cleanup all state for a call (when call ends).

        Args:
            call_sid: Call session ID
        """
        cls.clear_interrupted(call_sid)
