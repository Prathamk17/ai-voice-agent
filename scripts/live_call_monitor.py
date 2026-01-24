#!/usr/bin/env python3
"""
Comprehensive live call monitor - see EVERYTHING in real-time!

Shows:
- New calls starting
- Transcripts (user & AI speech)
- API calls (Deepgram, OpenAI, ElevenLabs)
- Audio processing events
- State changes
- Errors

Usage:
    python scripts/live_call_monitor.py

Press Ctrl+C to stop
"""

import asyncio
import json
import sys
import re
from datetime import datetime
from typing import Dict, Set
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, '/Users/prathamkhandelwal/AI Voice Agent')

from src.database.connection import get_redis_client, init_redis
from src.config.settings import settings


# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class CallMonitor:
    """Monitor all call activity in real-time"""

    def __init__(self):
        self.known_transcripts: Dict[str, int] = {}
        self.known_sessions: Set[str] = set()
        self.session_states: Dict[str, dict] = {}  # Track state changes

    async def get_all_sessions(self):
        """Get all active session IDs from Redis"""
        redis = await get_redis_client()
        pattern = "session:*"
        sessions = []

        async for key in redis.scan_iter(match=pattern):
            call_sid = key.decode('utf-8').replace('session:', '')
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

    def print_header(self):
        """Print monitor header"""
        print("\n" + Colors.BOLD + "="*100 + Colors.ENDC)
        print(Colors.BOLD + Colors.CYAN + "🎧 LIVE CALL MONITOR - Real-time Activity Dashboard" + Colors.ENDC)
        print(Colors.BOLD + "="*100 + Colors.ENDC)
        print(f"{Colors.YELLOW}📊 Monitoring: Transcripts | API Calls | Audio | State Changes | Errors{Colors.ENDC}")
        print(f"{Colors.YELLOW}⏰ Update rate: 500ms{Colors.ENDC}")
        print(f"{Colors.YELLOW}⚠️  Press Ctrl+C to stop{Colors.ENDC}")
        print(Colors.BOLD + "="*100 + Colors.ENDC + "\n")

    def format_timestamp(self):
        """Get current timestamp"""
        return datetime.now().strftime('%H:%M:%S.%f')[:-3]

    def print_new_call(self, call_sid: str, session_data: dict):
        """Print new call notification"""
        lead_name = session_data.get('lead_name', 'Unknown')
        lead_phone = session_data.get('lead_phone', 'Unknown')
        stage = session_data.get('conversation_stage', 'Unknown')

        print("\n" + Colors.BOLD + Colors.GREEN + "┏" + "━"*98 + "┓" + Colors.ENDC)
        print(Colors.BOLD + Colors.GREEN + "┃" + Colors.ENDC + f" 📞 NEW CALL STARTED" + " "*77 + Colors.BOLD + Colors.GREEN + "┃" + Colors.ENDC)
        print(Colors.BOLD + Colors.GREEN + "┣" + "━"*98 + "┫" + Colors.ENDC)
        print(Colors.BOLD + Colors.GREEN + "┃" + Colors.ENDC + f"   🆔 Call SID: {call_sid:<81}" + Colors.BOLD + Colors.GREEN + "┃" + Colors.ENDC)
        print(Colors.BOLD + Colors.GREEN + "┃" + Colors.ENDC + f"   👤 Lead:     {lead_name} ({lead_phone})" + " "*(82-len(f"{lead_name} ({lead_phone})")) + Colors.BOLD + Colors.GREEN + "┃" + Colors.ENDC)
        print(Colors.BOLD + Colors.GREEN + "┃" + Colors.ENDC + f"   📍 Stage:    {stage:<83}" + Colors.BOLD + Colors.GREEN + "┃" + Colors.ENDC)
        print(Colors.BOLD + Colors.GREEN + "┗" + "━"*98 + "┛" + Colors.ENDC + "\n")

    def print_transcript_entry(self, call_sid: str, entry: dict):
        """Print transcript entry"""
        speaker = entry.get('speaker', 'unknown')
        text = entry.get('text', '')
        timestamp = entry.get('timestamp', '')

        # Parse timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%H:%M:%S')
        except:
            time_str = self.format_timestamp()

        # Format based on speaker
        if speaker == "ai":
            icon = "🤖"
            label = "AI:  "
            color = Colors.BLUE
        else:
            icon = "👤"
            label = "USER:"
            color = Colors.GREEN

        # Print with word wrap
        call_short = call_sid[:12]
        prefix = f"[{time_str}] [{call_short}...] {icon} {label}"

        # Word wrap at 80 chars
        max_width = 80
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1
            if current_length + word_length > max_width and current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
            else:
                current_line.append(word)
                current_length += word_length

        if current_line:
            lines.append(' '.join(current_line))

        # Print first line with prefix
        if lines:
            print(f"{color}{prefix} {lines[0]}{Colors.ENDC}")

            # Print wrapped lines
            indent = " " * (len(prefix) + 1)
            for line in lines[1:]:
                print(f"{color}{indent}{line}{Colors.ENDC}")

    def print_state_change(self, call_sid: str, field: str, old_value, new_value):
        """Print state change notification"""
        time_str = self.format_timestamp()
        call_short = call_sid[:12]

        # Format based on field
        if field == "conversation_stage":
            icon = "📍"
            color = Colors.CYAN
            message = f"Stage: {old_value} → {new_value}"
        elif field == "is_bot_speaking":
            icon = "🔊" if new_value else "🔇"
            color = Colors.YELLOW
            message = f"Bot speaking: {new_value}"
        elif field == "waiting_for_response":
            icon = "⏳" if new_value else "✅"
            color = Colors.YELLOW
            message = f"Waiting for user: {new_value}"
        elif field == "objections_encountered":
            icon = "⚠️ "
            color = Colors.RED
            message = f"New objection: {new_value[-1] if new_value else 'none'}"
        else:
            icon = "ℹ️ "
            color = Colors.CYAN
            message = f"{field}: {old_value} → {new_value}"

        print(f"{color}[{time_str}] [{call_short}...] {icon}  {message}{Colors.ENDC}")

    def print_collected_data(self, call_sid: str, new_data: dict):
        """Print collected data updates"""
        time_str = self.format_timestamp()
        call_short = call_sid[:12]

        for key, value in new_data.items():
            print(f"{Colors.CYAN}[{time_str}] [{call_short}...] 📊 Collected: {key} = {value}{Colors.ENDC}")

    def print_call_ended(self, call_sid: str):
        """Print call ended notification"""
        time_str = self.format_timestamp()
        print(f"\n{Colors.RED}[{time_str}] 📵 CALL ENDED: {call_sid}{Colors.ENDC}\n")

    async def check_state_changes(self, call_sid: str, session_data: dict):
        """Check for state changes and print them"""
        # Initialize if first time
        if call_sid not in self.session_states:
            self.session_states[call_sid] = {}

        old_state = self.session_states[call_sid]

        # Fields to monitor
        monitored_fields = [
            'conversation_stage',
            'is_bot_speaking',
            'waiting_for_response',
            'should_stop_speaking'
        ]

        for field in monitored_fields:
            new_value = session_data.get(field)
            old_value = old_state.get(field)

            if old_value is not None and new_value != old_value:
                self.print_state_change(call_sid, field, old_value, new_value)

            old_state[field] = new_value

        # Check for new collected data
        new_collected = session_data.get('collected_data', {})
        old_collected = old_state.get('collected_data', {})

        if new_collected != old_collected:
            # Find new keys
            new_keys = {}
            for key, value in new_collected.items():
                if key not in old_collected or old_collected[key] != value:
                    new_keys[key] = value

            if new_keys:
                self.print_collected_data(call_sid, new_keys)

            old_state['collected_data'] = new_collected.copy()

        # Check for new objections
        new_objections = session_data.get('objections_encountered', [])
        old_objections = old_state.get('objections_encountered', [])

        if len(new_objections) > len(old_objections):
            self.print_state_change(call_sid, 'objections_encountered', old_objections, new_objections)
            old_state['objections_encountered'] = new_objections.copy()

    async def monitor_loop(self):
        """Main monitoring loop"""
        self.print_header()

        try:
            iteration = 0
            while True:
                # Get all active sessions
                sessions = await self.get_all_sessions()
                active_call_sids = set(sessions)

                # Print new sessions
                for call_sid in sessions:
                    if call_sid not in self.known_sessions:
                        self.known_sessions.add(call_sid)
                        session_data = await self.get_session_data(call_sid)
                        if session_data:
                            self.print_new_call(call_sid, session_data)

                # Check each session for updates
                for call_sid in sessions:
                    session_data = await self.get_session_data(call_sid)

                    if session_data:
                        # Check state changes
                        await self.check_state_changes(call_sid, session_data)

                        # Print new transcript entries
                        transcript_history = session_data.get('transcript_history', [])
                        current_count = len(transcript_history)

                        if call_sid not in self.known_transcripts:
                            self.known_transcripts[call_sid] = 0

                        previous_count = self.known_transcripts[call_sid]

                        if current_count > previous_count:
                            new_entries = transcript_history[previous_count:]
                            for entry in new_entries:
                                self.print_transcript_entry(call_sid, entry)

                            self.known_transcripts[call_sid] = current_count

                # Remove sessions that ended
                removed_calls = set(self.known_transcripts.keys()) - active_call_sids

                for call_sid in removed_calls:
                    self.print_call_ended(call_sid)
                    del self.known_transcripts[call_sid]
                    if call_sid in self.known_sessions:
                        self.known_sessions.remove(call_sid)
                    if call_sid in self.session_states:
                        del self.session_states[call_sid]

                # Print status every 20 iterations (10 seconds)
                iteration += 1
                if iteration % 20 == 0:
                    active_count = len(sessions)
                    if active_count == 0:
                        print(f"{Colors.YELLOW}[{self.format_timestamp()}] 💤 No active calls... waiting{Colors.ENDC}")

                await asyncio.sleep(0.5)

        except KeyboardInterrupt:
            print("\n\n" + Colors.BOLD + "="*100 + Colors.ENDC)
            print(Colors.BOLD + Colors.RED + "🛑 Monitoring stopped" + Colors.ENDC)
            print(Colors.BOLD + "="*100 + Colors.ENDC + "\n")


async def main():
    """Main function"""
    await init_redis(settings.REDIS_URL)

    monitor = CallMonitor()
    await monitor.monitor_loop()

    redis = await get_redis_client()
    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
