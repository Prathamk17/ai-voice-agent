# Exotel Integration Analysis - Complete Architecture

## Overview
This document provides a complete analysis of how Exotel is integrated into the Real Estate Voice AI system, covering WebSocket connections, audio handling, and the full flow.

---

## 1. Exotel WebSocket Endpoint Definition

### Primary Endpoint Location
**File:** `/Users/prathamkhandelwal/AI Voice Agent/src/main.py` (lines 165-177)

```python
@app.websocket("/media")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Exotel voice connections.
    
    Exotel connects to this endpoint when a call is initiated.
    The endpoint handles real-time audio streaming and AI conversation.
    """
    await websocket_server.handle_connection(websocket)
```

### Endpoint Details
- **Path:** `/media`
- **Protocol:** WebSocket
- **Public URL Configuration:** Must be set via `OUR_BASE_URL` environment variable
- **Example URL:** `wss://your-ngrok-url.ngrok.io/media` or `wss://your-domain.com/media`

### How Exotel Connects
1. When a call is initiated via `ExotelClient.make_call()`, it specifies an Exophlo (voice flow) in the Exotel dashboard
2. The Exophlo contains a "Voicebot Applet" that opens the WebSocket connection to this `/media` endpoint
3. Exotel initiates the WebSocket connection and sends events in JSON format

---

## 2. How Exotel Connects to WebSocket

### Connection Flow

#### Step 1: Initiate Outbound Call
**File:** `/Users/prathamkhandelwal/AI Voice Agent/src/integrations/exotel_client.py` (lines 58-141)

```python
async def make_call(
    self,
    to_number: str,
    custom_field: Dict[str, Any],
    caller_id: str = None,
    status_callback_url: str = None,
    record: bool = True
) -> Dict[str, Any]:
```

**Process:**
- Calls Exotel REST API: `POST https://api.exotel.com/v1/Accounts/{account_sid}/Calls/connect.json`
- Uses Basic Auth: `auth=(EXOTEL_API_KEY, EXOTEL_API_TOKEN)`
- Payload includes:
  - `From`: Virtual number (outbound caller ID)
  - `To`: Customer phone number (E.164 format)
  - `CallerId`: Caller ID to display
  - `CustomField`: JSON with lead context (lead_id, lead_name, property_info, etc.)
  - `Record`: Whether to record call (default: true)
  - `Url`: Exophlo URL pointing to the Voicebot Applet
  - `StatusCallback`: Webhook URL for status updates

**Example Request:**
```python
payload = {
    "From": "080XXXXXXXX",  # Your virtual number
    "To": "+919876543210",  # Customer's number
    "CallerId": "080XXXXXXXX",
    "CustomField": '{"lead_id": 123, "lead_name": "John", "property_type": "apartment"}',
    "Record": "true",
    "Url": "http://my.exotel.com/exoml/start/YOUR_EXOPHLO_ID",
    "StatusCallback": "https://your-domain.com/webhooks/exotel/call-status"
}
```

#### Step 2: Exotel Initiates WebSocket Connection
When the call is answered:
1. Exotel looks up the Exophlo URL from the call initiation
2. The Exophlo Voicebot Applet triggers and opens a WebSocket connection to your `/media` endpoint
3. Connection is established from Exotel's servers to your application

#### Step 3: WebSocket Events Start Flowing
Exotel sends the following events in sequence:

### Exotel WebSocket Event Sequence

**File:** `/Users/prathamkhandelwal/AI Voice Agent/src/websocket/server.py` (lines 35-133)

```
1. "connected" event
   ├─ Exotel has opened the WebSocket
   └─ No data payload
   
2. "start" event
   ├─ Media streaming about to begin
   ├─ Contains: call_sid, from, to, customField
   └─ Session is created here
   
3. "media" events (multiple)
   ├─ Audio chunks from customer
   ├─ Format: Base64-encoded PCM
   └─ Sent continuously until silence detected
   
4. "stop" event
   ├─ Call ended by customer
   └─ Triggers cleanup
   
Optional events:
   - "clear": Reset conversation
   - "dtmf": Keypress detected (e.g., press 0 for human)
```

**Event Handler:**
```python
class ExotelWebSocketServer:
    async def handle_connection(self, websocket: WebSocket):
        """Main event loop processing events from Exotel"""
        
        event_type = data.get("event")
        
        if event_type == "connected":
            await self.event_handler.handle_connected(websocket, data)
            
        elif event_type == "start":
            session = await self.event_handler.handle_start(websocket, data)
            
        elif event_type == "media":
            await self.event_handler.handle_media(websocket, session, data)
            
        elif event_type == "stop":
            await self.event_handler.handle_stop(websocket, session)
```

---

## 3. Current Flow (Complete Conversation Flow)

### Full Conversation Lifecycle

**File:** `/Users/prathamkhandelwal/AI Voice Agent/src/websocket/event_handlers.py`

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Call Initiated (REST API)                                │
│    → ExotelClient.make_call()                               │
│    → Exotel API creates call, triggers Exophlo              │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 2. WebSocket Connection Established                         │
│    → Customer picks up phone                                │
│    → Exotel sends "connected" event                         │
│    → WebSocket connection ready at /media endpoint          │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 3. Session Creation (handle_start)                          │
│    → Extract: call_sid, customer phone, lead context        │
│    → Create ConversationSession in Redis                    │
│    → Generate intro text                                    │
│    → Convert intro to speech (ElevenLabs TTS)              │
│    → Send audio chunks to Exotel via WebSocket             │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 4. Listen for Customer Response (handle_media - Loop)       │
│    → Receive "media" event with audio payload               │
│    → Decode Base64 → PCM audio bytes                        │
│    → Buffer audio chunks                                    │
│    → Detect voice activity (energy-based VAD)              │
│                                                              │
│    a) While collecting audio:                               │
│       └─ Count silence chunks                               │
│       └─ When speech ends (600ms silence):                 │
│          • Transcribe buffered audio (Deepgram STT)        │
│          • Add to transcript                                │
│                                                              │
│    b) Interruption Detection (Barge-in):                    │
│       └─ If is_bot_speaking AND voice detected:            │
│          • Stop bot speech immediately                      │
│          • Clear buffer and restart                         │
│          • Process customer's interruption                  │
│                                                              │
│    c) Latency Masking:                                      │
│       └─ If LLM response > 300ms:                           │
│          • Play filler audio ("hmm", "okay", "right")      │
│          • Makes conversation feel natural                  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 5. Process with LLM (ConversationEngine)                    │
│    → Send transcript to OpenAI GPT-4o-mini                  │
│    → Get response text and decision (continue/end)          │
│    → Add to transcript                                      │
│    → Extract collected data (property type, budget, etc.)   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 6. Send Response to Customer (send_tts_to_caller)           │
│    → Convert response text to speech (ElevenLabs TTS)       │
│    → Chunk audio into 20ms segments                         │
│    → Base64 encode each chunk                               │
│    → Send via WebSocket "media" event                       │
│    → Monitor for interruptions (barge-in support)           │
│    → After response: Set waiting_for_response=True          │
│    → Loop back to Step 4 to listen for next input           │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 7. Call End Condition                                       │
│    → LLM returns should_end=True, OR                        │
│    → Customer sends "stop" event, OR                        │
│    → Call naturally ends                                    │
│                                                              │
│    → Close WebSocket connection                             │
│    → Trigger Exotel to disconnect call                      │
│    → Finalize session (save transcript, outcome)            │
│    → Process call outcome (qualified, not interested, etc.) │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 8. Webhook Status Callback (Separate Async)                │
│    → Exotel sends status callback to:                       │
│      POST /webhooks/exotel/call-status                      │
│    → Statuses: initiated, ringing, in-progress, completed   │
│    → Update CallSession DB record                           │
│    → Save recording URL if available                        │
└─────────────────────────────────────────────────────────────┘
```

### Key Session States During Conversation

**File:** `/Users/prathamkhandelwal/AI Voice Agent/src/models/conversation.py`

```python
class ConversationSession:
    call_sid: str                          # Exotel call ID
    lead_id: int                           # Lead being called
    lead_phone: str                        # Customer phone
    lead_name: str                         # Customer name
    
    conversation_stage: ConversationStage  # INTRO, QUALIFICATION, CLOSING
    is_bot_speaking: bool                  # True while AI is speaking
    waiting_for_response: bool             # True when listening to customer
    should_stop_speaking: bool             # True when customer interrupts
    
    audio_buffer: bytes                    # Accumulating audio chunks
    transcript_history: list               # All exchanges in call
    collected_data: dict                   # Extracted: budget, property type, etc.
    
    escalation_requested: bool             # True if customer pressed 0
    final_outcome: str                     # Result: qualified, not_interested, etc.
```

### Audio Buffer Management

**File:** `/Users/prathamkhandelwal/AI Voice Agent/src/websocket/event_handlers.py` (lines 150-326)

```python
# Silence detection thresholds:
min_audio_bytes = 8000          # 0.5 seconds of audio minimum
silence_threshold = 10          # ~600ms of silence (10 * 60ms chunks)

# When these conditions are met:
if len(session.audio_buffer) >= min_audio_bytes and \
   session.silence_chunks >= silence_threshold:
    # ✅ Transcribe and send to LLM
```

---

## 4. Configuration Required for Exotel

### Environment Variables

**File:** `/Users/prathamkhandelwal/AI Voice Agent/.env.example` (lines 17-25)

```env
# Exotel Configuration (Indian Telephony Provider)
EXOTEL_ACCOUNT_SID=your_account_sid_here
EXOTEL_API_KEY=your_api_key_here
EXOTEL_API_TOKEN=your_api_token_here
EXOTEL_VIRTUAL_NUMBER=080XXXXXXXX
EXOTEL_EXOPHLO_ID=your_exophlo_id_here

# Server Base URL (for webhooks and WebSocket)
OUR_BASE_URL=http://localhost:8000
```

### Configuration Loading

**File:** `/Users/prathamkhandelwal/AI Voice Agent/src/config/settings.py` (lines 40-45)

```python
class Settings(BaseSettings):
    EXOTEL_ACCOUNT_SID: str = ""
    EXOTEL_API_KEY: str = ""
    EXOTEL_API_TOKEN: str = ""
    EXOTEL_VIRTUAL_NUMBER: str = ""
    EXOTEL_EXOPHLO_ID: str = ""
```

### How to Get Configuration Values

#### 1. EXOTEL_ACCOUNT_SID
- Log in to https://exotel.com
- Go to Settings → Account Settings
- Copy "Account SID"
- Format: Usually alphanumeric string (e.g., `abc123def456`)

#### 2. EXOTEL_API_KEY & EXOTEL_API_TOKEN
- Go to Settings → API Settings
- Create new API credentials if needed
- Copy "API Key" and "API Token"
- These are used for Basic Auth in REST API calls

#### 3. EXOTEL_VIRTUAL_NUMBER
- Go to My Numbers
- Select an Exophone (virtual number)
- Format: 080XXXXXXXX or similar (10-digit Indian number)
- This is the "From" number when making calls

#### 4. EXOTEL_EXOPHLO_ID
- Go to Exophlo (Call Flows)
- Create or select your flow with "Voicebot Applet"
- Copy the Exophlo ID
- This must contain a "Voicebot Applet" that:
  1. Opens WebSocket to your `/media` endpoint
  2. Streams audio bidirectionally
  3. Implements VAD (voice activity detection)

#### 5. OUR_BASE_URL (For WebSocket)
- Local development: `http://localhost:8000`
- Ngrok tunneling: `https://your-id.ngrok.io`
- Production: `https://your-domain.com`
- This is used to construct the WebSocket URL and status callback URL

### Exophlo Configuration in Exotel Dashboard

The Exophlo (call flow) must be configured with:

```xml
<!-- Simplified Exophlo XML structure -->
<exoml>
  <session>
    <!-- When call is answered, open WebSocket -->
    <voicebot>
      <stream>
        <!-- Connect to your WebSocket endpoint -->
        <websocket>
          <url>wss://OUR_BASE_URL/media</url>
          <format>pcm</format>
          <encoding>base64</encoding>
          <sample_rate>8000</sample_rate>
          <bit_depth>16</bit_depth>
          <channels>1</channels>
        </websocket>
      </stream>
    </voicebot>
  </session>
</exoml>
```

**Key Settings in Voicebot Applet:**
- WebSocket URL: `wss://your-domain.com/media`
- Audio Format: PCM (not GSM)
- Sample Rate: 8kHz
- Bit Depth: 16-bit
- Channels: Mono (1 channel)
- Voice Activity Detection: Enabled (to detect silence)

---

## 5. Audio Format & Encoding/Decoding

### Audio Specifications

**File:** `/Users/prathamkhandelwal/AI Voice Agent/src/audio/processor.py`

```python
class AudioProcessor:
    """
    Exotel Audio Format:
    - Format: 16-bit Linear PCM
    - Sample Rate: 8000 Hz
    - Channels: Mono (1)
    - Encoding: Base64 (for WebSocket transmission)
    """
```

### Audio Processing Pipeline

```
Incoming from Exotel:
┌─────────────────────────────────────────────┐
│ "media" event with Base64-encoded payload   │
│ {                                            │
│   "event": "media",                         │
│   "media": {                                │
│     "payload": "gABkAGYAZ..."  (base64)     │
│   }                                          │
│ }                                            │
└────────────────┬────────────────────────────┘
                 │
        1. decode_exotel_audio()
        │  Base64 → binary PCM bytes
        │
        ▼
┌─────────────────────────────────────────────┐
│ Raw PCM bytes (16-bit, 8kHz, mono)          │
│ Length: typically 160 bytes (20ms chunk)    │
└────────────────┬────────────────────────────┘
                 │
        2. Accumulate in buffer
        │  session.audio_buffer += audio_bytes
        │
        ▼
┌─────────────────────────────────────────────┐
│ When speech ends (silence detected):        │
│ - Transcribe buffer with Deepgram STT      │
│ - Clear buffer                              │
└─────────────────────────────────────────────┘

Outgoing to Exotel:
┌─────────────────────────────────────────────┐
│ Text response from LLM                       │
└────────────────┬────────────────────────────┘
                 │
        1. ElevenLabs TTS
        │  Text → PCM audio (8kHz, 16-bit, mono)
        │
        ▼
┌─────────────────────────────────────────────┐
│ Raw PCM bytes from TTS                       │
└────────────────┬────────────────────────────┘
                 │
        2. chunk_audio(chunk_duration_ms=20)
        │  Split into 20ms chunks (320 bytes each)
        │
        ▼
┌─────────────────────────────────────────────┐
│ List of PCM chunks                          │
└────────────────┬────────────────────────────┘
                 │
        3. For each chunk: encode_for_exotel()
        │  Binary PCM → Base64 string
        │
        ▼
┌─────────────────────────────────────────────┐
│ "media" events sent to Exotel               │
│ {                                            │
│   "event": "media",                         │
│   "media": {                                │
│     "payload": "gABkAGYAZ..."  (base64)     │
│   }                                          │
│ }                                            │
└─────────────────────────────────────────────┘
```

### Codec Functions

```python
# Decoding incoming audio
audio_bytes = AudioProcessor.decode_exotel_audio(base64_payload)
# Returns: bytes of raw PCM audio

# Encoding outgoing audio
base64_string = AudioProcessor.encode_for_exotel(pcm_bytes)
# Returns: string of Base64-encoded PCM

# Chunking for streaming
chunks = AudioProcessor.chunk_audio(audio_bytes, chunk_duration_ms=20)
# Each chunk = 320 bytes (20ms at 8kHz)

# Calculate duration
duration_ms = AudioProcessor.get_audio_duration_ms(audio_bytes)
# 1 second = 16,000 bytes
```

---

## 6. WebSocket Message Structure

### Incoming Messages from Exotel

#### "connected" Event
```json
{
  "event": "connected"
}
```
Response: No response needed, just acknowledge

#### "start" Event (Most Important)
```json
{
  "event": "start",
  "start": {
    "call_sid": "call_abc123def456",
    "from": "+919876543210",
    "to": "080XXXXXXXX",
    "caller_id": "+919876543210"
  },
  "customField": "{\"lead_id\": 123, \"lead_name\": \"John\", \"property_type\": \"apartment\"}",
  "CallSid": "call_abc123def456"  // Alternative format
}
```
Handler: `handle_start()` - Creates session, generates intro

#### "media" Event
```json
{
  "event": "media",
  "media": {
    "payload": "gABkAGYAZ..."  // Base64-encoded PCM audio
  }
}
```
Handler: `handle_media()` - Accumulates audio, detects speech

#### "stop" Event
```json
{
  "event": "stop"
}
```
Handler: `handle_stop()` - Marks call ended, prepares cleanup

#### "dtmf" Event (Optional)
```json
{
  "event": "dtmf",
  "dtmf": {
    "digit": "0"  // Keys pressed: 0-9, *, #
  }
}
```
Handler: `handle_dtmf()` - Example: Press 0 to escalate

#### "clear" Event (Optional)
```json
{
  "event": "clear"
}
```
Handler: `handle_clear()` - Reset conversation, restart intro

### Outgoing Messages to Exotel

#### Send Audio
```json
{
  "event": "media",
  "media": {
    "payload": "gABkAGYAZ..."  // Base64-encoded PCM audio
  }
}
```

#### Other Possible Commands
```json
{
  "event": "dtmf",
  "dtmf": "1"  // Simulate keypress (rarely used)
}
```

---

## 7. Status Callback Webhook

### Webhook Endpoint

**File:** `/Users/prathamkhandelwal/AI Voice Agent/src/api/webhooks.py` (lines 23-100)

```python
@router.post("/exotel/call-status")
async def exotel_call_status_webhook(request: Request, db: AsyncSession = Depends(get_db_session)):
    """
    Receive call status updates from Exotel
    URL: POST https://your-domain.com/webhooks/exotel/call-status
    """
```

### Status Callback Flow

```
1. When initiating call:
   ├─ Set StatusCallback parameter:
   │  StatusCallback=https://your-domain.com/webhooks/exotel/call-status
   │
   ▼
2. Throughout call lifecycle, Exotel sends status updates:
   ├─ initiated → Call request sent
   ├─ ringing → Phone is ringing
   ├─ in-progress → Call answered (coincides with WebSocket start)
   ├─ completed → Call ended normally
   ├─ failed → Technical error
   ├─ busy → Recipient's line was busy
   └─ no-answer → No one picked up

3. Webhook receives:
   POST /webhooks/exotel/call-status
   Form Data:
   ├─ CallSid: "call_abc123def456"
   ├─ Status: "in-progress" | "completed" | etc.
   ├─ Duration: "245" (seconds)
   ├─ RecordingUrl: "https://cdn.exotel.com/recording123.mp3"
   └─ CustomField: "{...}" (same as sent during call initiation)

4. Update Database:
   └─ Find CallSession by call_sid
      └─ Update status
      └─ Set answered_at / ended_at timestamps
      └─ Save recording URL
      └─ Trigger outcome processing
```

### Status Mapping

```python
status_mapping = {
    "initiated": CallStatus.INITIATED,
    "ringing": CallStatus.RINGING,
    "in-progress": CallStatus.IN_PROGRESS,
    "completed": CallStatus.COMPLETED,
    "failed": CallStatus.FAILED,
    "busy": CallStatus.BUSY,
    "no-answer": CallStatus.NO_ANSWER,
}
```

---

## 8. Complete Configuration Checklist

### Required Configuration

- [ ] **EXOTEL_ACCOUNT_SID**: Your Exotel account ID
- [ ] **EXOTEL_API_KEY**: API key for REST calls
- [ ] **EXOTEL_API_TOKEN**: API token for REST calls
- [ ] **EXOTEL_VIRTUAL_NUMBER**: Your Exotel virtual number (080XXXXXXXX)
- [ ] **EXOTEL_EXOPHLO_ID**: Exophlo ID with Voicebot Applet
- [ ] **OUR_BASE_URL**: Public URL (for WebSocket and webhooks)
- [ ] **REDIS_URL**: Redis server (for session management)
- [ ] **DATABASE_URL**: PostgreSQL (for call history)

### AI Services Configuration

- [ ] **DEEPGRAM_API_KEY**: For speech-to-text
- [ ] **OPENAI_API_KEY**: For LLM (conversation)
- [ ] **ELEVENLABS_API_KEY**: For text-to-speech
- [ ] **ELEVENLABS_VOICE_ID**: (Optional) For custom voice

### Network Configuration

- [ ] **Firewall**: Port 8000 (or custom port) open
- [ ] **SSL/TLS**: HTTPS required for WebSocket (wss://)
- [ ] **Ngrok** (local dev): `ngrok http 8000` for tunneling
- [ ] **Domain DNS**: Point to your server

### Exotel Dashboard Configuration

- [ ] **Exophone (Virtual Number)**: Configured and active
- [ ] **Exophlo (Call Flow)**: Created with Voicebot Applet
- [ ] **Voicebot Applet Settings**:
  - [ ] WebSocket URL: `wss://your-domain.com/media`
  - [ ] Audio Format: PCM
  - [ ] Sample Rate: 8000 Hz
  - [ ] Voice Activity Detection: Enabled
- [ ] **Status Callback URL**: `https://your-domain.com/webhooks/exotel/call-status`

---

## 9. Key Files Reference

### Core Exotel Files

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `src/integrations/exotel_client.py` | REST API client | `ExotelClient.make_call()` |
| `src/websocket/server.py` | WebSocket handler | `ExotelWebSocketServer.handle_connection()` |
| `src/websocket/event_handlers.py` | Event processing | `ExotelEventHandler` with `handle_start()`, `handle_media()` |
| `src/websocket/session_manager.py` | Session state in Redis | `SessionManager.create_session()` |
| `src/audio/processor.py` | Audio encoding/decoding | `encode_for_exotel()`, `decode_exotel_audio()` |
| `src/config/settings.py` | Configuration loading | `Settings` class |
| `src/api/webhooks.py` | Status callbacks | `exotel_call_status_webhook()` |
| `src/main.py` | FastAPI app | `@app.websocket("/media")` |

### Related Services

| File | Purpose |
|------|---------|
| `src/ai/stt_service.py` | Deepgram speech-to-text |
| `src/ai/tts_service.py` | ElevenLabs text-to-speech |
| `src/conversation/engine.py` | LLM conversation processing |
| `src/models/call_session.py` | Database call records |
| `src/database/connection.py` | Redis & PostgreSQL connections |

---

## 10. Troubleshooting

### WebSocket Connection Issues

1. **"Connection refused"**
   - Ensure server is running: `python src/main.py`
   - Check port 8000 is accessible
   - For local dev: Use ngrok tunneling

2. **"Invalid certificate"**
   - Ensure HTTPS/WSS (not HTTP/WS)
   - Certificate must match domain name
   - Try: `ngrok http 8000` for local testing

3. **"WebSocket closed unexpectedly"**
   - Check logs for errors
   - Verify Redis connection
   - Ensure AI services (Deepgram, OpenAI, ElevenLabs) are accessible

### Audio Issues

1. **"Failed to decode audio"**
   - Verify base64 is valid
   - Check audio format is PCM 16-bit, 8kHz, mono
   - Test: `AudioProcessor.decode_exotel_audio(payload)`

2. **"No audio received from customer"**
   - Check Exophlo Voicebot settings
   - Verify VAD (voice activity detection) is enabled
   - Test with actual phone call

### Configuration Issues

1. **"Exotel API error: 401"**
   - Verify EXOTEL_API_KEY and EXOTEL_API_TOKEN
   - Check they're not expired

2. **"Missing lead_id in session"**
   - Ensure CustomField is sent with call initiation
   - Verify JSON parsing in handle_start()

---

## Summary

**Exotel Integration Summary:**

1. **Initiation**: `ExotelClient.make_call()` triggers REST API call to Exotel
2. **Connection**: Exotel's Voicebot Applet opens WebSocket to `/media` endpoint
3. **Events**: Exotel streams "start", "media", "stop" events as JSON
4. **Audio**: All audio is Base64-encoded PCM (16-bit, 8kHz, mono)
5. **Session**: ConversationSession in Redis tracks state during call
6. **Processing**: Each media event → buffer → detect silence → transcribe → LLM → TTS → send back
7. **Callback**: Separate webhook receives status updates (initiated, ringing, completed, etc.)
8. **Cleanup**: WebSocket close triggers session finalization and database updates

**Critical Configuration:**
- Exotel account credentials (SID, Key, Token, Virtual Number)
- Exophlo with Voicebot Applet pointing to your WebSocket URL
- Public HTTPS domain for WebSocket connections
- Status callback URL for call lifecycle tracking
