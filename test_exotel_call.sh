#!/bin/bash

# Exotel Test Call Script
# This script makes a test call using Exotel API to verify WebSocket connectivity

# Exotel credentials (from your .env)
ACCOUNT_SID="goldmines2"
API_KEY="1f5a5273623729740fd49ee35671d4a14dd092526f5087cb"
API_TOKEN="a87e1bf70db6003a7be5b988ba5fec349ac90e282af3c5b3"
VIRTUAL_NUMBER="01414939962"

# Your Railway WebSocket URL (Exotel will connect here)
WEBSOCKET_URL="wss://ai-voice-agent-production-9d41.up.railway.app/media"

# Test call parameters
# IMPORTANT: Replace with YOUR phone number to receive the test call
TO_NUMBER="+91XXXXXXXXXX"  # <-- CHANGE THIS to your phone number (with country code)

echo "🚀 Making test call via Exotel API..."
echo "   From: $VIRTUAL_NUMBER"
echo "   To: $TO_NUMBER"
echo "   WebSocket: $WEBSOCKET_URL"
echo ""

# Make the API call
# Exotel API endpoint: https://api.exotel.com/v1/Accounts/{AccountSid}/Calls/connect
response=$(curl -X POST \
  "https://api.exotel.com/v1/Accounts/${ACCOUNT_SID}/Calls/connect" \
  -u "${API_KEY}:${API_TOKEN}" \
  -d "From=${VIRTUAL_NUMBER}" \
  -d "To=${TO_NUMBER}" \
  -d "CallerId=${VIRTUAL_NUMBER}" \
  -d "StatusCallback=https://ai-voice-agent-production-9d41.up.railway.app/webhooks/exotel/status" \
  2>&1)

echo "📞 API Response:"
echo "$response"
echo ""
echo "✅ Call initiated! Check:"
echo "   1. Your phone should ring in ~5 seconds"
echo "   2. Answer the call to trigger WebSocket connection"
echo "   3. Check Railway logs for WebSocket events"
echo ""
echo "📊 View Railway logs:"
echo "   https://railway.app → Your project → View Logs"
