#!/usr/bin/env python3
"""
Quick script to inspect Redis session data
"""

import asyncio
import json
import sys

sys.path.insert(0, '/Users/prathamkhandelwal/AI Voice Agent')

from src.database.connection import init_redis, get_redis_client
from src.config.settings import settings


async def inspect_session(call_sid: str):
    """Inspect a specific Redis session"""

    await init_redis(settings.REDIS_URL)
    redis = await get_redis_client()

    key = f"session:{call_sid}"

    print(f"\n🔍 Inspecting Redis key: {key}\n")

    # Get the data
    data = await redis.get(key)

    if not data:
        print(f"❌ Session not found in Redis")

        # List all available sessions
        print("\n📋 Available sessions in Redis:")
        async for k in redis.scan_iter(match="session:*"):
            decoded_key = k.decode('utf-8')
            print(f"   - {decoded_key}")

        await redis.aclose()
        return

    # Parse JSON
    session_dict = json.loads(data)

    print("=" * 80)
    print("📦 FULL SESSION DATA")
    print("=" * 80)
    print()

    # Print all fields
    for key, value in session_dict.items():
        if key == 'transcript_history':
            print(f"📝 {key}: ({len(value)} exchanges)")
            for i, exchange in enumerate(value, 1):
                speaker = exchange.get('speaker', 'unknown')
                text = exchange.get('text', '')
                emoji = "🤖" if speaker == "ai" or speaker == "agent" else "👤"
                print(f"   {i}. {emoji} {speaker.upper()}: {text}")
        elif key == 'collected_data':
            print(f"📊 {key}: {json.dumps(value, indent=2)}")
        elif isinstance(value, (dict, list)) and len(str(value)) > 100:
            print(f"🔑 {key}: {type(value).__name__} (length: {len(value)})")
        else:
            print(f"🔑 {key}: {value}")

    print()
    print("=" * 80)

    # Summary
    transcript_count = len(session_dict.get('transcript_history', []))
    collected_count = len(session_dict.get('collected_data', {}))

    print(f"\n✅ Summary:")
    print(f"   - Transcript exchanges: {transcript_count}")
    print(f"   - Collected data fields: {collected_count}")
    print(f"   - Session size: {len(data)} bytes")

    await redis.aclose()


async def list_all_sessions():
    """List all sessions in Redis"""

    await init_redis(settings.REDIS_URL)
    redis = await get_redis_client()

    print("\n📋 All sessions in Redis:\n")

    sessions = []
    async for key in redis.scan_iter(match="session:*"):
        decoded_key = key.decode('utf-8')
        call_sid = decoded_key.replace('session:', '')

        # Get basic info
        data = await redis.get(key)
        if data:
            session_dict = json.loads(data)
            transcript_count = len(session_dict.get('transcript_history', []))
            lead_name = session_dict.get('lead_name', 'Unknown')

            sessions.append({
                'call_sid': call_sid,
                'lead_name': lead_name,
                'exchanges': transcript_count,
                'size': len(data)
            })

    if not sessions:
        print("❌ No sessions found in Redis")
    else:
        print(f"{'CALL SID':<40} {'LEAD NAME':<20} {'EXCHANGES':<12} {'SIZE'}")
        print("-" * 90)
        for s in sessions:
            print(f"{s['call_sid']:<40} {s['lead_name']:<20} {s['exchanges']:<12} {s['size']} bytes")

    await redis.aclose()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        call_sid = sys.argv[1]
        asyncio.run(inspect_session(call_sid))
    else:
        asyncio.run(list_all_sessions())
        print("\n💡 To inspect a specific session, run:")
        print("   python3 scripts/inspect_redis_session.py <call_sid>")
