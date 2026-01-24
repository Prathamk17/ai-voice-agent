# Exotel Integration - Quick Reference Guide

## File Locations

```
WebSocket Endpoint:           src/main.py (line 166)
WebSocket Server:             src/websocket/server.py
Event Handlers:               src/websocket/event_handlers.py
Session Management:           src/websocket/session_manager.py
REST API Client:              src/integrations/exotel_client.py
Audio Processing:             src/audio/processor.py
Configuration:                src/config/settings.py
Status Callbacks:             src/api/webhooks.py
Models:                        src/models/conversation.py, call_session.py
```

## Configuration Variables

| Variable | Purpose | Where to Get |
|----------|---------|--------------|
| `EXOTEL_ACCOUNT_SID` | Account ID | Exotel Dashboard → Settings → Account Settings |
| `EXOTEL_API_KEY` | API credentials | Exotel Dashboard → Settings → API Settings |
| `EXOTEL_API_TOKEN` | API credentials | Exotel Dashboard → Settings → API Settings |
| `EXOTEL_VIRTUAL_NUMBER` | Outbound caller ID | Exotel Dashboard → My Numbers |
| `EXOTEL_EXOPHLO_ID` | Call flow with Voicebot | Exotel Dashboard → Exophlo |
| `OUR_BASE_URL` | Public server URL | Your domain or ngrok URL |
| `DEEPGRAM_API_KEY` | Speech-to-text | deepgram.com |
| `OPENAI_API_KEY` | LLM | openai.com |
| `ELEVENLABS_API_KEY` | Text-to-speech | elevenlabs.io |

## WebSocket Endpoint

```
Path:     /media
Protocol: WebSocket (wss:// for HTTPS)
URL:      wss://{OUR_BASE_URL}/media
Handler:  ExotelWebSocketServer.handle_connection()
```

## Call Flow - Step by Step

```
1. REST API Call
   ExotelClient.make_call() → Exotel API
   
2. WebSocket Connection
   Exotel Voicebot opens connection to /media
   
3. Events Received
   "connected" → "start" → "media" (loop) → "stop"
   
4. Each Media Event
   Decode Base64 → Accumulate in buffer → Detect silence → 
   Transcribe with Deepgram → Send to OpenAI → 
   Generate TTS with ElevenLabs → Encode to Base64 → Send back
   
5. Session Storage
   All state saved in Redis (key: "session:{call_sid}")
   
6. Status Callback
   Separate webhook receives call status updates
```

## Audio Format

```
Format:       16-bit Linear PCM
Sample Rate:  8000 Hz
Channels:     Mono (1)
Duration:     Continuous streaming
Encoding:     Base64 (for WebSocket)

Chunk Size:   20ms = 320 bytes
Duration:     8000 bytes = 0.5 seconds
Silence:      600ms to trigger transcription
```

## Key Classes

### ExotelClient
```python
client = ExotelClient(
    account_sid="...",
    api_key="...",
    api_token="...",
    virtual_number="080..."
)
result = await client.make_call(
    to_number="+919876543210",
    custom_field={"lead_id": 123, "lead_name": "John"},
    status_callback_url="https://your-domain.com/webhooks/exotel/call-status"
)
```

### ExotelEventHandler
```python
handler = ExotelEventHandler()
await handler.handle_connected(websocket, data)
session = await handler.handle_start(websocket, data)
await handler.handle_media(websocket, session, media_data)
await handler.handle_stop(websocket, session)
```

### SessionManager
```python
manager = SessionManager()
session = await manager.create_session(call_sid, lead_context)
session = await manager.get_session(call_sid)
await manager.save_session(session)
await manager.add_to_transcript(call_sid, "user", text)
```

### AudioProcessor
```python
# Decode incoming audio
audio_bytes = AudioProcessor.decode_exotel_audio(base64_payload)

# Encode outgoing audio
base64_string = AudioProcessor.encode_for_exotel(pcm_bytes)

# Chunk audio for streaming (20ms chunks)
chunks = AudioProcessor.chunk_audio(audio_bytes, chunk_duration_ms=20)

# Get duration
duration_ms = AudioProcessor.get_audio_duration_ms(audio_bytes)
```

## WebSocket Message Examples

### Incoming: Connected
```json
{"event": "connected"}
```

### Incoming: Start (Session Creation)
```json
{
  "event": "start",
  "start": {
    "call_sid": "call_abc123",
    "from": "+919876543210",
    "to": "080XXXXXXXX"
  },
  "customField": "{\"lead_id\": 123}"
}
```

### Incoming: Media (Audio Chunk)
```json
{
  "event": "media",
  "media": {"payload": "gABkAGYAZ..."}
}
```

### Outgoing: Send Audio
```json
{
  "event": "media",
  "media": {"payload": "gABkAGYAZ..."}
}
```

## Status Callback Webhook

```
URL: POST https://your-domain.com/webhooks/exotel/call-status

Statuses:
- initiated    → Call request sent
- ringing      → Phone is ringing
- in-progress  → Call answered
- completed    → Call ended normally
- failed       → Technical error
- busy         → Line was busy
- no-answer    → No one picked up

Payload (form-data):
- CallSid: call_abc123
- Status: completed
- Duration: 245
- RecordingUrl: https://cdn.exotel.com/...
- CustomField: {...}
```

## Conversation States

```
ConversationStage:
- INTRO          → Initial greeting
- QUALIFICATION  → Asking qualification questions
- CLOSING        → Wrapping up
- COMPLETED      → Call ended

Session Flags:
- is_bot_speaking        → AI is currently playing audio
- waiting_for_response   → Listening for customer
- should_stop_speaking   → Customer interrupted (barge-in)
- escalation_requested   → Customer pressed 0
```

## Voice Activity Detection (VAD)

```python
# Simple energy-based detection
VOICE_THRESHOLD = 500  # RMS energy

# Silence triggers transcription when:
- Audio buffer >= 8000 bytes (0.5 seconds)
- Silence >= 600ms (10 chunks of 60ms each)

# Then:
1. Transcribe with Deepgram
2. Send to OpenAI LLM
3. Generate TTS response
4. Send audio back to customer
5. Listen for interruption (barge-in support)
```

## Barge-in (Interruption) Support

```
While AI is speaking:
1. Check every 3 chunks for voice activity (60ms latency)
2. If voice detected → Set should_stop_speaking=True
3. Stop sending TTS chunks
4. Process customer's input

Latency Masking:
- If LLM takes >300ms → Play filler audio ("hmm", "okay")
- Makes conversation feel more natural
```

## Troubleshooting Checklist

### Connection Issues
- [ ] Server running on port 8000
- [ ] Firewall allows port 8000
- [ ] OUR_BASE_URL is HTTPS (not HTTP)
- [ ] WebSocket path is `/media`

### Configuration Issues
- [ ] EXOTEL_ACCOUNT_SID is correct
- [ ] EXOTEL_API_KEY and API_TOKEN are valid
- [ ] EXOTEL_VIRTUAL_NUMBER exists in Exotel
- [ ] EXOTEL_EXOPHLO_ID has Voicebot Applet
- [ ] Exophlo WebSocket URL points to your `/media`

### Audio Issues
- [ ] Exophlo Voicebot uses PCM format
- [ ] Sample rate is 8000 Hz
- [ ] Bit depth is 16-bit
- [ ] Channels is mono (1)
- [ ] Voice Activity Detection enabled

### Redis/Database Issues
- [ ] Redis is running on REDIS_URL
- [ ] PostgreSQL is running on DATABASE_URL
- [ ] Tables are initialized

### AI Services
- [ ] DEEPGRAM_API_KEY is valid
- [ ] OPENAI_API_KEY is valid
- [ ] ELEVENLABS_API_KEY is valid
- [ ] APIs are accessible from your server

## Performance Notes

```
Typical Latencies:
- Exotel audio chunk:      20-60ms
- Deepgram transcription:  200-500ms
- OpenAI LLM response:     300-800ms
- ElevenLabs TTS:          500-2000ms
- Total end-to-end:        1-2 seconds (acceptable for voice)

Optimization:
- Filler audio plays after 300ms to mask LLM latency
- Barge-in checked every 60ms for responsiveness
- Audio buffered until silence for complete sentences
- Session state in Redis for fast access
```

## Related Documentation

- Complete guide: `EXOTEL_INTEGRATION_ANALYSIS.md`
- Setup guide: `MODULE4_SETUP.md`
- API docs: https://developer.exotel.com/api/
- Exotel Voicebot docs: https://developer.exotel.com/voicebot/

