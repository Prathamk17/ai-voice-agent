#!/bin/bash

# AI Voice Agent - Startup Script
echo "🚀 Starting AI Voice Agent (Refactored Version)"
echo "=============================================="
echo ""

# Check for required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set in environment"
    echo "   Loading from .env file..."
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the server
echo "📡 Starting server on http://localhost:8000"
echo "📊 Logs will be written to: logs/app.log"
echo ""
echo "To monitor logs in real-time, run in another terminal:"
echo "  tail -f logs/app.log | grep '⚡\\|✨\\|🛑'"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
