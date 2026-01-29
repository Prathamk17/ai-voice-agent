#!/bin/bash

# Fetch the most recent call from Railway API
echo "📊 Fetching most recent call..."
CALL_DATA=$(curl -s https://ai-voice-agent-production-9d41.up.railway.app/debug/history/call-sessions?limit=1)

# Extract call_sid
CALL_SID=$(echo "$CALL_DATA" | jq -r '.call_sessions[0].call_sid')

if [ "$CALL_SID" = "null" ] || [ -z "$CALL_SID" ]; then
    echo "❌ No calls found in database"
    exit 1
fi

echo "📞 Analyzing call: $CALL_SID"
echo ""

# Fetch full transcript
TRANSCRIPT=$(curl -s "https://ai-voice-agent-production-9d41.up.railway.app/debug/history/call-sessions/$CALL_SID/transcript")

# Save to temp file and analyze with Python
echo "$TRANSCRIPT" | jq -r '.transcript' > /tmp/transcript.json

python3 << 'PYTHON'
import json
from datetime import datetime

with open('/tmp/transcript.json', 'r') as f:
    transcript = json.load(f)

if not transcript or len(transcript) < 2:
    print("❌ No transcript data available")
    exit(1)

print("⏱️  CALL LATENCY ANALYSIS")
print("=" * 60)

latencies = []

for i in range(len(transcript) - 1):
    current = transcript[i]
    next_msg = transcript[i + 1]
    
    # Calculate latency when customer speaks -> agent responds
    if current['speaker'] == 'customer' and next_msg['speaker'] == 'agent':
        try:
            customer_time = datetime.fromisoformat(current['timestamp'].replace('Z', '+00:00'))
            agent_time = datetime.fromisoformat(next_msg['timestamp'].replace('Z', '+00:00'))
            
            latency_ms = (agent_time - customer_time).total_seconds() * 1000
            latencies.append(latency_ms)
            
            print(f"Turn {len(latencies):2d}: {latency_ms:>6.0f}ms ({latency_ms/1000:.2f}s)")
        except:
            pass

if latencies:
    print("=" * 60)
    print(f"Average latency: {sum(latencies)/len(latencies):>6.0f}ms ({sum(latencies)/len(latencies)/1000:.2f}s)")
    print(f"Min latency:     {min(latencies):>6.0f}ms ({min(latencies)/1000:.2f}s)")
    print(f"Max latency:     {max(latencies):>6.0f}ms ({max(latencies)/1000:.2f}s)")
    print(f"Total turns:     {len(latencies)}")
else:
    print("No customer-agent turn pairs found")
PYTHON

