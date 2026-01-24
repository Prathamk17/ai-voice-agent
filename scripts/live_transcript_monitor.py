#!/usr/bin/env python3
"""
Real-time transcript monitor - watch calls as they happen!

Usage:
    # Monitor all active calls
    python scripts/live_transcript_monitor.py

    # Monitor specific call
    python scripts/live_transcript_monitor.py <call_sid>

Press Ctrl+C to stop monitoring
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, Set

# Add parent directory to path
sys.path.insert(0, '/Users/prathamkhandelwal/AI Voice Agent')

from src.database.connection import get_redis_client, init_redis
from src.config.settings import settings


class TranscriptMonitor:
    """Monitor Redis for real-time transcript updates"""

    def __init__(self, specific_call_sid: str = None):
        self.specific_call_sid = specific_call_sid
        self.known_transcripts: Dict[str, int] = {}  # call_sid -> transcript count
        self.known_sessions: Set[str] = set()

    async def get_all_sessions(self):
        """Get all active session IDs from Redis"""
        redis = await get_redis_client()
        pattern = "session:*"
        sessions = []

        async for key in redis.scan_iter(match=pattern):
            call_sid = key.decode('utf-8').replace('session:', '')

            # Filter by specific call if provided
            if self.specific_call_sid and call_sid != self.specific_call_sid:
                continue

            sessions.append(call_sid)

        return sessions

    async def get_session_data(self, call_sid: str):
        """Get session data from Redis"""
        redis = await get_redis_client()
        key = f"session:{call_sid}"
        data = await redis.get(key)

        if data:
            return json.loads(data)
        return None

    def format_transcript_entry(self, call_sid: str, entry: dict, index: int):
        """Format a single transcript entry for display"""
        speaker = entry.get('speaker', 'unknown')
        text = entry.get('text', '')
        timestamp = entry.get('timestamp', '')

        # Parse timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%H:%M:%S')
        except:
            time_str = timestamp[:8] if len(timestamp) >= 8 else 'N/A'

        # Format speaker with color
        if speaker == "ai":
            speaker_label = "🤖 AI:  "
            color = "\033[94m"  # Blue
        else:
            speaker_label = "👤 USER:"
            color = "\033[92m"  # Green

        reset = "\033[0m"

        # Format output
        output = f"{color}[{time_str}] [{call_sid[:8]}...] {speaker_label} {text}{reset}"
        return output

    async def print_new_sessions(self, sessions: list):
        """Print info about new sessions"""
        for call_sid in sessions:
            if call_sid not in self.known_sessions:
                self.known_sessions.add(call_sid)

                # Get session data
                session_data = await self.get_session_data(call_sid)
                if session_data:
                    lead_name = session_data.get('lead_name', 'Unknown')
                    lead_phone = session_data.get('lead_phone', 'Unknown')
                    stage = session_data.get('conversation_stage', 'Unknown')

                    print("\n" + "="*80)
                    print(f"📞 NEW CALL STARTED")
                    print(f"   Call SID:   {call_sid}")
                    print(f"   Lead:       {lead_name} ({lead_phone})")
                    print(f"   Stage:      {stage}")
                    print("="*80 + "\n")

    async def print_new_transcripts(self, call_sid: str, session_data: dict):
        """Print new transcript entries"""
        transcript_history = session_data.get('transcript_history', [])
        current_count = len(transcript_history)

        # Initialize if first time seeing this call
        if call_sid not in self.known_transcripts:
            self.known_transcripts[call_sid] = 0

        previous_count = self.known_transcripts[call_sid]

        # Print new entries
        if current_count > previous_count:
            new_entries = transcript_history[previous_count:]

            for i, entry in enumerate(new_entries, start=previous_count):
                print(self.format_transcript_entry(call_sid, entry, i))

            # Update known count
            self.known_transcripts[call_sid] = current_count

    async def print_session_updates(self, call_sid: str, session_data: dict):
        """Print important session state changes"""
        stage = session_data.get('conversation_stage')
        is_bot_speaking = session_data.get('is_bot_speaking', False)
        waiting_for_response = session_data.get('waiting_for_response', False)
        should_stop_speaking = session_data.get('should_stop_speaking', False)
        collected_data = session_data.get('collected_data', {})
        objections = session_data.get('objections_encountered', [])

        # You can add state change tracking here if needed
        # For now, we'll just monitor transcripts

    async def monitor_loop(self):
        """Main monitoring loop"""
        print("\n" + "="*80)
        print("🎧 LIVE TRANSCRIPT MONITOR")
        print("="*80)

        if self.specific_call_sid:
            print(f"📍 Monitoring specific call: {self.specific_call_sid}")
        else:
            print("📍 Monitoring ALL active calls")

        print("⏰ Refreshing every 0.5 seconds")
        print("⚠️  Press Ctrl+C to stop\n")
        print("="*80 + "\n")

        try:
            while True:
                # Get all active sessions
                sessions = await self.get_all_sessions()

                # Print new sessions
                await self.print_new_sessions(sessions)

                # Check each session for new transcripts
                for call_sid in sessions:
                    session_data = await self.get_session_data(call_sid)

                    if session_data:
                        # Print new transcript entries
                        await self.print_new_transcripts(call_sid, session_data)

                # Remove sessions that are no longer active
                active_call_sids = set(sessions)
                removed_calls = set(self.known_transcripts.keys()) - active_call_sids

                for call_sid in removed_calls:
                    print(f"\n⚠️  Call ended: {call_sid}\n")
                    del self.known_transcripts[call_sid]
                    if call_sid in self.known_sessions:
                        self.known_sessions.remove(call_sid)

                # Sleep before next check
                await asyncio.sleep(0.5)

        except KeyboardInterrupt:
            print("\n\n" + "="*80)
            print("🛑 Monitoring stopped")
            print("="*80 + "\n")

async def main():
    """Main function"""

    # Initialize Redis
    await init_redis(settings.REDIS_URL)

    # Parse arguments
    call_sid = None
    if len(sys.argv) > 1:
        call_sid = sys.argv[1]

    # Create monitor
    monitor = TranscriptMonitor(specific_call_sid=call_sid)

    # Start monitoring
    await monitor.monitor_loop()

    # Close Redis
    redis = await get_redis_client()
    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
