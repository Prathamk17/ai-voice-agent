#!/usr/bin/env python3
"""
View call history and transcripts from database

Usage:
    # View recent calls
    python scripts/view_call_history.py

    # View specific call by call_sid
    python scripts/view_call_history.py <call_sid>

    # View last N calls
    python scripts/view_call_history.py --last 10
"""

import asyncio
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/Users/prathamkhandelwal/AI Voice Agent')

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db_session, init_db
from src.models.call_session import CallSession
from src.models.lead import Lead
from src.config.settings import settings


def format_call_details(call: CallSession, lead: Lead = None) -> str:
    """Format call details for display"""
    output = []
    output.append("=" * 80)
    output.append("📞 CALL DETAILS")
    output.append("=" * 80)
    output.append("")

    # Call info
    output.append("📋 CALL INFO:")
    output.append(f"  Call SID:       {call.call_sid}")
    output.append(f"  Status:         {call.status}")
    output.append(f"  Outcome:        {call.outcome or 'N/A'}")
    output.append(f"  Duration:       {call.duration_seconds}s" if call.duration_seconds else "  Duration:       N/A")
    output.append(f"  Initiated:      {call.initiated_at}")
    output.append(f"  Answered:       {call.answered_at or 'N/A'}")
    output.append(f"  Ended:          {call.ended_at or 'N/A'}")
    output.append("")

    # Lead info
    if lead:
        output.append("👤 LEAD INFO:")
        output.append(f"  Name:           {lead.name}")
        output.append(f"  Phone:          {lead.phone}")
        output.append(f"  Email:          {lead.email or 'N/A'}")
        output.append(f"  Property Type:  {lead.property_type or 'N/A'}")
        output.append(f"  Location:       {lead.location or 'N/A'}")
        if lead.budget:
            output.append(f"  Budget:         ₹{lead.budget/100000:.1f}L")
        output.append("")

    # Collected data
    if call.collected_data:
        try:
            collected = json.loads(call.collected_data)
            output.append("📊 COLLECTED DATA:")
            for key, value in collected.items():
                output.append(f"  {key}: {value}")
            output.append("")
        except:
            pass

    # Transcript
    if call.full_transcript:
        output.append("📝 FULL TRANSCRIPT:")
        output.append("-" * 80)

        try:
            # Try to parse as JSON (structured transcript)
            transcript = json.loads(call.full_transcript)

            if isinstance(transcript, list):
                for i, exchange in enumerate(transcript, 1):
                    speaker = exchange.get('speaker', 'unknown')
                    text = exchange.get('text', '')
                    timestamp = exchange.get('timestamp', '')

                    # Parse timestamp
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M:%S')
                    except:
                        time_str = timestamp[:8] if len(timestamp) >= 8 else timestamp

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

                    # Print first line with speaker
                    output.append(f"[{time_str}] {speaker_label} {lines[0] if lines else ''}")

                    # Print continuation lines
                    for line in lines[1:]:
                        output.append(f"             {' ' * 12} {line}")

                    output.append("")
            else:
                # Not a list, print as-is
                output.append(str(transcript))

        except json.JSONDecodeError:
            # Plain text transcript
            output.append(call.full_transcript)

        output.append("-" * 80)
    else:
        output.append("📝 TRANSCRIPT: (empty)")

    output.append("")

    # Recording
    if call.recording_url:
        output.append(f"🎙️  RECORDING: {call.recording_url}")
        output.append("")

    output.append("=" * 80)

    return "\n".join(output)


async def get_recent_calls(limit: int = 10):
    """Get recent calls from database"""
    async for db in get_db_session():
        stmt = (
            select(CallSession)
            .order_by(desc(CallSession.initiated_at))
            .limit(limit)
        )

        result = await db.execute(stmt)
        calls = result.scalars().all()

        return calls


async def get_call_by_sid(call_sid: str):
    """Get specific call by call_sid"""
    async for db in get_db_session():
        stmt = (
            select(CallSession)
            .where(CallSession.call_sid == call_sid)
        )

        result = await db.execute(stmt)
        call = result.scalar_one_or_none()

        return call


async def main():
    """Main function"""

    # Initialize database
    await init_db(settings.DATABASE_URL)

    # Parse arguments
    call_sid = None
    limit = 10

    if len(sys.argv) > 1:
        if sys.argv[1] == '--last' and len(sys.argv) > 2:
            limit = int(sys.argv[2])
        else:
            call_sid = sys.argv[1]

    try:
        if call_sid:
            # View specific call
            print(f"\n🔍 Fetching call: {call_sid}\n")
            result = await get_call_by_sid(call_sid)

            if result:
                formatted = format_call_details(result, None)
                print(formatted)
            else:
                print(f"❌ Call not found: {call_sid}")
                print("\nTip: Try viewing recent calls with:")
                print("  python scripts/view_call_history.py --last 10")
        else:
            # List recent calls
            print(f"\n🔍 Fetching last {limit} calls from database...\n")
            calls = await get_recent_calls(limit)

            if not calls:
                print("❌ No calls found in database")
                print("\nTip: Calls are saved to the database after they complete.")
                return

            print(f"📞 Found {len(calls)} call(s):\n")
            print("-" * 110)
            print(f"{'CALL SID':<30} {'STATUS':<15} {'OUTCOME':<20} {'DURATION':<10} {'DATE':<35}")
            print("-" * 110)

            for call in calls:
                duration = f"{call.duration_seconds}s" if call.duration_seconds else "N/A"
                date_str = call.initiated_at.strftime('%Y-%m-%d %H:%M:%S') if call.initiated_at else 'N/A'
                outcome = call.outcome or 'N/A'

                print(f"{call.call_sid:<30} {call.status:<15} {outcome:<20} {duration:<10} {date_str:<35}")

            print("-" * 110)
            print(f"\nTo view a specific call transcript, run:")
            print(f"  python scripts/view_call_history.py <call_sid>")

            if calls:
                print(f"\nExample:")
                print(f"  python scripts/view_call_history.py {calls[0].call_sid}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
