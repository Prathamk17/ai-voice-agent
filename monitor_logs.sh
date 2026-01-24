#!/bin/bash
# Monitor logs for voice AI debugging

echo "================================================"
echo "Voice AI Log Monitor - Watch for key events"
echo "================================================"
echo ""
echo "Looking for process..."

PID=$(ps aux | grep -i "python.*main.py\|uvicorn.*main:app" | grep -v grep | awk '{print $2}' | head -1)

if [ -z "$PID" ]; then
    echo "❌ Application not running!"
    echo "Start it with: python -m uvicorn src.main:app --host 0.0.0.0 --port 8000"
    exit 1
fi

echo "✅ Found process: $PID"
echo ""
echo "Key indicators to watch:"
echo "  🎤 = Voice interruption detected"
echo "  🛑 = Bot speech stopped"
echo "  User spoke = Transcription received"
echo "  TTS sent = Bot finished speaking"
echo ""
echo "Logs:"
echo "================================================"
echo ""

# Follow logs (requires lsof and tail on the log file, or just watch the terminal where uvicorn is running)
echo "Note: Logs are output to the console where you started the server."
echo "Look for these patterns in your terminal:"
echo "  - 'User interruption detected'"
echo "  - 'Voice detected! RMS:'"
echo "  - 'User spoke'"
echo "  - 'TTS sent to caller'"
echo ""
echo "If you don't see 'Voice detected! RMS:' when you speak, the VAD threshold may need adjustment."
