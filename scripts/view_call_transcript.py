#!/usr/bin/env python3
"""
View call transcripts for debugging

Usage:
    # View all active calls
    python scripts/view_call_transcript.py

    # View specific call
    python scripts/view_call_transcript.py <call_sid>

    # Export to file
    python scripts/view_call_transcript.py <call_sid> --export transcript.txt
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, '/Users/prathamkhandelwal/AI Voice Agent')

from src.database.connection import get_redis_client, init_redis
from src.models.conversation import ConversationSession
from src.config.settings import settings


async def get_all_sessions():
    """Get all active session IDs from Redis"""
    redis = await get_redis_client()
    pattern = "session:*"
    sessions = []

    async for key in redis.scan_iter(match=pattern):
        call_sid = key.decode('utf-8').replace('session:', '')
        data = await redis.get(key)

        if data:
            session_dict = json.loads(data)
            sessions.append({
                'call_sid': call_sid,
                'lead_name': session_dict.get('lead_name', 'Unknown'),
                'lead_phone': session_dict.get('lead_phone', 'Unknown'),
                'stage': session_dict.get('conversation_stage', 'Unknown'),
                'started_at': session_dict.get('started_at', 'Unknown'),
                'transcript_count': len(session_dict.get('transcript_history', []))
            })

    return sessions


async def get_session_transcript(call_sid: str):
    """Get full transcript for a specific call"""
    redis = await get_redis_client()
    key = f"session:{call_sid}"

    data = await redis.get(key)

    if not data:
        print(f"❌ Session not found: {call_sid}")
        return None

    session_dict = json.loads(data)
    return session_dict


def format_transcript(session_dict: dict) -> str:
    """Format transcript for display"""
    output = []
    output.append("=" * 80)
    output.append("📞 CALL TRANSCRIPT")
    output.append("=" * 80)
    output.append("")

    # Call metadata
    output.append("📋 CALL INFO:")
    output.append(f"  Call SID:       {session_dict.get('call_sid', 'Unknown')}")
    output.append(f"  Lead Name:      {session_dict.get('lead_name', 'Unknown')}")
    output.append(f"  Lead Phone:     {session_dict.get('lead_phone', 'Unknown')}")
    output.append(f"  Property Type:  {session_dict.get('property_type', 'Not specified')}")
    output.append(f"  Location:       {session_dict.get('location', 'Not specified')}")
    output.append(f"  Budget:         ₹{session_dict.get('budget', 0)/100000:.1f}L" if session_dict.get('budget') else "  Budget:         Not specified")
    output.append(f"  Stage:          {session_dict.get('conversation_stage', 'Unknown')}")
    output.append(f"  Started:        {session_dict.get('started_at', 'Unknown')}")
    output.append("")

    # Collected data
    collected_data = session_dict.get('collected_data', {})
    if collected_data:
        output.append("📊 COLLECTED DATA:")
        for key, value in collected_data.items():
            output.append(f"  {key}: {value}")
        output.append("")

    # Objections encountered
    objections = session_dict.get('objections_encountered', [])
    if objections:
        output.append(f"⚠️  OBJECTIONS: {', '.join(objections)}")
        output.append("")

    # Transcript
    transcript_history = session_dict.get('transcript_history', [])

    if not transcript_history:
        output.append("📝 TRANSCRIPT: (empty)")
    else:
        output.append(f"📝 TRANSCRIPT: ({len(transcript_history)} exchanges)")
        output.append("-" * 80)

        for i, exchange in enumerate(transcript_history, 1):
            speaker = exchange.get('speaker', 'unknown')
            text = exchange.get('text', '')
            timestamp = exchange.get('timestamp', '')

            # Parse timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M:%S')
            except:
                time_str = timestamp

            # Format speaker
            speaker_emoji = "🤖 AI:" if speaker == "ai" else "👤 USER:"
            speaker_label = f"{speaker_emoji:12}"

            # Word wrap text at 65 chars
            max_width = 65
            words = text.split()
            lines = []
            current_line = []
            current_length = 0

            for word in words:
                word_length = len(word) + 1  # +1 for space
                if current_length + word_length > max_width and current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = word_length
                else:
                    current_line.append(word)
                    current_length += word_length

            if current_line:
                lines.append(' '.join(current_line))

            # Print first line with speaker
            output.append(f"[{time_str}] {speaker_label} {lines[0] if lines else ''}")

            # Print continuation lines
            for line in lines[1:]:
                output.append(f"             {' ' * 12} {line}")

            output.append("")

    output.append("=" * 80)

    return "\n".join(output)


async def main():
    """Main function"""

    # Initialize Redis
    await init_redis(settings.REDIS_URL)

    # Parse arguments
    call_sid = None
    export_file = None

    if len(sys.argv) > 1:
        call_sid = sys.argv[1]

        if len(sys.argv) > 3 and sys.argv[2] == '--export':
            export_file = sys.argv[3]

    try:
        if call_sid:
            # View specific call
            print(f"\n🔍 Fetching transcript for call: {call_sid}\n")
            session_dict = await get_session_transcript(call_sid)

            if session_dict:
                formatted = format_transcript(session_dict)
                print(formatted)

                if export_file:
                    with open(export_file, 'w') as f:
                        f.write(formatted)
                    print(f"\n💾 Exported to: {export_file}")
        else:
            # List all active calls
            print("\n🔍 Fetching all active calls...\n")
            sessions = await get_all_sessions()

            if not sessions:
                print("❌ No active calls found in Redis")
                print("\nTip: Transcripts are only stored during active calls.")
                print("     After a call ends, they're moved to the database.")
                return

            print(f"📞 Found {len(sessions)} active call(s):\n")
            print("-" * 100)
            print(f"{'CALL SID':<30} {'LEAD NAME':<20} {'PHONE':<15} {'STAGE':<20} {'EXCHANGES':<10}")
            print("-" * 100)

            for session in sessions:
                print(f"{session['call_sid']:<30} {session['lead_name']:<20} {session['lead_phone']:<15} {session['stage']:<20} {session['transcript_count']:<10}")

            print("-" * 100)
            print(f"\nTo view a specific transcript, run:")
            print(f"  python scripts/view_call_transcript.py <call_sid>")
            print(f"\nExample:")
            print(f"  python scripts/view_call_transcript.py {sessions[0]['call_sid']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Close Redis connection
        redis = await get_redis_client()
        await redis.close()


if __name__ == "__main__":
    asyncio.run(main())
