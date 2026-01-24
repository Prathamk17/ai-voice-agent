#!/usr/bin/env python3
"""
Simple transcript viewer using direct SQL queries

Usage:
    # View recent calls
    python scripts/view_transcripts.py

    # View specific call
    python scripts/view_transcripts.py <call_sid>
"""

import asyncio
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/Users/prathamkhandelwal/AI Voice Agent')

import asyncpg
from src.config.settings import settings


async def get_recent_calls(limit: int = 10):
    """Get recent calls using direct SQL"""
    # Parse connection string
    conn = await asyncpg.connect(settings.DATABASE_URL.replace('+asyncpg', ''))

    try:
        rows = await conn.fetch("""
            SELECT
                call_sid, status, outcome, duration_seconds,
                full_transcript, collected_data,
                initiated_at, answered_at, ended_at
            FROM call_sessions
            ORDER BY initiated_at DESC
            LIMIT $1
        """, limit)

        return rows
    finally:
        await conn.close()


async def get_call_by_sid(call_sid: str):
    """Get specific call by call_sid"""
    conn = await asyncpg.connect(settings.DATABASE_URL.replace('+asyncpg', ''))

    try:
        row = await conn.fetchrow("""
            SELECT
                call_sid, status, outcome, duration_seconds,
                full_transcript, collected_data,
                initiated_at, answered_at, ended_at
            FROM call_sessions
            WHERE call_sid = $1
        """, call_sid)

        return row
    finally:
        await conn.close()


def format_call(row) -> str:
    """Format call details"""
    output = []
    output.append("=" * 80)
    output.append("📞 CALL TRANSCRIPT")
    output.append("=" * 80)
    output.append("")

    output.append("📋 CALL INFO:")
    output.append(f"  Call SID:       {row['call_sid']}")
    output.append(f"  Status:         {row['status']}")
    output.append(f"  Outcome:        {row['outcome'] or 'N/A'}")
    output.append(f"  Duration:       {row['duration_seconds']}s" if row['duration_seconds'] else "  Duration:       N/A")
    output.append(f"  Initiated:      {row['initiated_at']}")
    output.append(f"  Answered:       {row['answered_at'] or 'N/A'}")
    output.append(f"  Ended:          {row['ended_at'] or 'N/A'}")
    output.append("")

    # Collected data
    if row['collected_data']:
        try:
            collected = json.loads(row['collected_data'])
            output.append("📊 COLLECTED DATA:")
            for key, value in collected.items():
                output.append(f"  {key}: {value}")
            output.append("")
        except:
            pass

    # Transcript
    if row['full_transcript']:
        output.append("📝 FULL TRANSCRIPT:")
        output.append("-" * 80)

        try:
            # Parse transcript
            transcript = json.loads(row['full_transcript'])

            if isinstance(transcript, list):
                for exchange in transcript:
                    speaker = exchange.get('speaker', 'unknown')
                    text = exchange.get('text', '')
                    timestamp = exchange.get('timestamp', '')

                    # Format timestamp
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M:%S')
                    except:
                        time_str = timestamp[:8] if len(timestamp) >= 8 else ''

                    # Format speaker
                    speaker_emoji = "🤖 AI:" if speaker == "ai" else "👤 USER:"

                    output.append(f"[{time_str}] {speaker_emoji:12} {text}")
                    output.append("")
            else:
                output.append(str(transcript))
        except:
            # Plain text
            output.append(row['full_transcript'])

        output.append("-" * 80)
    else:
        output.append("📝 TRANSCRIPT: (empty - call may not have completed)")

    output.append("")
    output.append("=" * 80)

    return "\n".join(output)


async def main():
    """Main function"""

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
            row = await get_call_by_sid(call_sid)

            if row:
                print(format_call(row))
            else:
                print(f"❌ Call not found: {call_sid}")
        else:
            # List recent calls
            print(f"\n🔍 Fetching last {limit} calls...\n")
            rows = await get_recent_calls(limit)

            if not rows:
                print("❌ No calls found")
                print("\nMake some test calls first!")
                return

            print(f"📞 Found {len(rows)} call(s):\n")
            print("-" * 110)
            print(f"{'CALL SID':<30} {'STATUS':<15} {'OUTCOME':<20} {'DURATION':<10} {'DATE':<35}")
            print("-" * 110)

            for row in rows:
                duration = f"{row['duration_seconds']}s" if row['duration_seconds'] else "N/A"
                date_str = row['initiated_at'].strftime('%Y-%m-%d %H:%M:%S') if row['initiated_at'] else 'N/A'
                outcome = row['outcome'] or 'N/A'

                print(f"{row['call_sid']:<30} {row['status']:<15} {outcome:<20} {duration:<10} {date_str:<35}")

            print("-" * 110)
            print(f"\nTo view a specific transcript, run:")
            print(f"  python scripts/view_transcripts.py <call_sid>")

            if rows:
                print(f"\nExample:")
                print(f"  python scripts/view_transcripts.py {rows[0]['call_sid']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
