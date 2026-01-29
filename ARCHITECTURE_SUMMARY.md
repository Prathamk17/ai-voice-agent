# AI Voice Agent - Architecture Summary & Integration Guide

## System Overview

Your AI Voice Agent is a **complete, production-ready system** for automated voice calling with AI-powered conversations. It consists of multiple integrated components working together in real-time.

---

## 1. Call Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                      INITIATION PHASE                                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  User: POST /campaigns/{id}/start                                    │
│    │                                                                  │
│    ├─> CallScheduler.schedule_campaign_calls()                       │
│    │     ├─ Get all leads from campaign                              │
│    │     └─ Calculate scheduled times (respecting calling hours)     │
│    │                                                                  │
│    └─> Background Worker (continuous job)                           │
│          ├─ Polls for pending calls every 10 seconds               │
│          ├─ Limits to MAX_CONCURRENT_CALLS (default: 10)           │
│          └─ Only during calling hours (10 AM - 7 PM, not Sunday)   │
│                                                                      │
│          For each pending call:                                      │
│          ├─> CallExecutor.execute_call()                           │
│          │    ├─ Get lead details                                  │
│          │    ├─ Build custom_field JSON                          │
│          │    └─ Call Exotel REST API                              │
│          │         ↓                                                │
│          │    ExotelClient.make_call(                               │
│          │      to_number="+919876543210",                          │
│          │      custom_field={lead_id, lead_name, ...},            │
│          │      status_callback_url="https://domain/webhooks/...", │
│          │    )                                                     │
│          │         ↓                                                │
│          └─> Exotel API creates call + schedules WebSocket         │
│                                                                      │
│              Phone rings...                                          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                    REAL-TIME CONVERSATION PHASE                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Customer answers phone                                              │
│    │                                                                  │
│    └─> Exotel initiates WebSocket: wss://domain.com/media          │
│         ├─ Sends "connected" event                                  │
│         ├─ Sends "start" event (with call_sid, customField)        │
│         └─ Session created in memory/Redis                         │
│                                                                      │
│  AI speaks greeting (ElevenLabs TTS)                                │
│    │                                                                  │
│    └─> "Hello John! I'm calling about..."                          │
│         └─> WebSocket sends audio chunk to Exotel                  │
│             └─> Customer hears greeting                            │
│                                                                      │
│  Customer speaks                                                     │
│    │                                                                  │
│    └─> Exotel sends "media" event with audio bytes                 │
│         ├─> Buffer audio until silence detected                    │
│         └─> When silence detected:                                 │
│              ├─> Deepgram STT: Convert audio → text               │
│              │   "I'm interested in 2BHK apartments"               │
│              │                                                      │
│              ├─> OpenAI LLM: Generate response                     │
│              │   Input: customer transcript + context              │
│              │   Output: "Great! Let me tell you about..."         │
│              │                                                      │
│              └─> ElevenLabs TTS: Convert text → audio              │
│                   └─> WebSocket sends audio to Exotel             │
│                       └─> Customer hears response                  │
│                                                                      │
│  Loop continues until call ends...                                  │
│                                                                      │
│  Customer hangs up                                                   │
│    │                                                                  │
│    └─> Exotel sends "stop" event                                    │
│         └─> Session persisted to PostgreSQL database               │
│             ├─ Transcript saved                                     │
│             ├─ Call duration recorded                               │
│             └─ Lead qualified status updated                        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                    STATUS UPDATE PHASE                                │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Throughout call: Exotel sends status webhooks                      │
│    │                                                                  │
│    └─> POST /webhooks/exotel/call-status                           │
│         │                                                            │
│         ├─ Status: "initiated"                                      │
│         ├─ Status: "ringing"                                        │
│         ├─ Status: "in-progress"                                    │
│         └─ Status: "completed" / "no-answer" / "busy" / "failed"   │
│             │                                                        │
│             └─> Update CallSession in PostgreSQL                   │
│                  ├─ If no-answer: Schedule retry (2 hours later)   │
│                  ├─ If busy: Schedule retry (4 hours later)        │
│                  └─ If completed: Mark as done                     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Infrastructure Components

### REST API Layer (Campaign Management)
```
FastAPI Application: http://localhost:8000

GET    /health                              ← Health check
POST   /campaigns                           ← Create campaign
GET    /campaigns                           ← List all campaigns
GET    /campaigns/{id}                      ← Get campaign details
PATCH  /campaigns/{id}                      ← Update campaign
POST   /campaigns/{id}/upload-csv           ← Upload leads (CSV)
GET    /campaigns/{id}/leads                ← List campaign leads
POST   /campaigns/{id}/start                ← Start calling
POST   /campaigns/{id}/pause                ← Pause calling

GET    /analytics/campaign/{id}             ← Campaign analytics
GET    /debug/sessions                      ← Active WebSocket sessions
GET    /exports/calls/{id}                  ← Export transcripts
```

### WebSocket Layer (Voice Calls)
```
WebSocket: wss://your-domain.com/media

Events from Exotel → Server:
  "connected"    ← WebSocket connection established
  "start"        ← Call starting (contains call_sid, customField)
  "media"        ← Audio data from customer (repeated)
  "stop"         ← Call ended
  "dtmf"         ← DTMF digit pressed (optional)
  "clear"        ← Reset conversation (optional)

Events from Server → Exotel:
  "connected"    → Acknowledge connection
  "media"        → Audio data to customer (streaming)
```

### Webhook Layer (Call Status)
```
POST /webhooks/exotel/call-status

Receives:
  CallSid      ← Exotel call ID (from custom_field.lead_id, etc.)
  Status       ← initiated, ringing, in-progress, completed, failed, etc.
  Duration     ← Call duration in seconds
  RecordingUrl ← URL to call recording
  CustomField  ← Original lead data passed in
```

---

## 3. Data Flow & Storage

### PostgreSQL Database
```
campaigns
  ├─ id, name, status (DRAFT/SCHEDULED/RUNNING/PAUSED/COMPLETED)
  ├─ calling_hours_start/end, max_concurrent_calls
  ├─ total_leads, leads_called, leads_completed
  └─ FK: leads, scheduled_calls

leads
  ├─ id, campaign_id, name, phone, email
  ├─ property_type, location, budget
  ├─ call_attempts, last_call_attempt
  └─ FK: scheduled_calls, call_sessions

scheduled_calls
  ├─ id, campaign_id, lead_id
  ├─ scheduled_time, status, attempt_number
  ├─ current_call_sid (links to Exotel call)
  ├─ failure_reason, max_attempts
  └─ FK: call_sessions

call_sessions
  ├─ id, call_sid (from Exotel), lead_id
  ├─ status (INITIATED/RINGING/IN_PROGRESS/COMPLETED/FAILED/BUSY/NO_ANSWER)
  ├─ answered_at, ended_at, duration_seconds
  ├─ recording_url
  └─ FK: conversations

conversations
  ├─ id, call_session_id
  ├─ transcript_history (JSON array of turns)
  ├─ final_outcome, lead_qualified
  └─ extracted_data (JSON extracted from conversation)
```

### Redis / In-Memory Session State
```json
"session:{call_sid}" → {
  "call_sid": "CAxxxxxxx",
  "lead_id": 123,
  "lead_name": "John",
  "lead_phone": "+919876543210",
  "property_type": "2BHK",
  "location": "Bangalore",
  "budget": "50L-75L",
  "conversation_stage": "qualification",
  "transcript_history": [
    {"speaker": "ai", "text": "Hello John...", "timestamp": "2026-01-28T10:30:00Z"},
    {"speaker": "user", "text": "Hi there...", "timestamp": "2026-01-28T10:30:05Z"},
    {"speaker": "ai", "text": "Are you interested in...", "timestamp": "2026-01-28T10:30:07Z"}
  ],
  "waiting_for_response": false,
  "last_interaction_time": "2026-01-28T10:30:07Z"
}
```

---

## 4. Integration Points & APIs

### External Services Integration

**Exotel (Telephony)**
```
REST API: POST https://api.exotel.com/v1/Accounts/{SID}/Calls/connect.json
Auth: Basic Auth with EXOTEL_API_KEY, EXOTEL_API_TOKEN
WebSocket: Connects to wss://your-domain.com/media
Webhook: Sends POST to /webhooks/exotel/call-status
```

**Deepgram (Speech-to-Text)**
```
Streaming API over WebSocket
Input: Audio bytes (µ-law PCM)
Output: Transcription with confidence scores
API Key: DEEPGRAM_API_KEY
```

**OpenAI (Language Model)**
```
REST API: https://api.openai.com/v1/chat/completions
Model: gpt-4o-mini (for speed and cost)
Input: Chat messages + system prompt + context
Output: AI response text
API Key: OPENAI_API_KEY
```

**ElevenLabs (Text-to-Speech)**
```
REST API: https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
Input: Text response from OpenAI
Output: Audio stream (MP3)
Voice ID: ELEVENLABS_VOICE_ID
API Key: ELEVENLABS_API_KEY
```

---

## 5. Configuration Checklist

### Must-Have Environment Variables
```env
# Exotel Credentials
EXOTEL_ACCOUNT_SID=your_account_sid
EXOTEL_API_KEY=your_api_key
EXOTEL_API_TOKEN=your_api_token
EXOTEL_VIRTUAL_NUMBER=080XXXXXXXX
EXOTEL_EXOPHLO_ID=your_exophlo_id
OUR_BASE_URL=https://your-domain.com (or ngrok URL for testing)

# AI Services
DEEPGRAM_API_KEY=your_deepgram_key
OPENAI_API_KEY=your_openai_key
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id

# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/voiceai
REDIS_URL=redis://localhost:6379

# Call Settings
CALLING_HOURS_START=10    # 10 AM
CALLING_HOURS_END=19      # 7 PM
MAX_CONCURRENT_CALLS=10
MAX_CALL_DURATION_MINUTES=10
```

---

## 6. File Structure Reference

```
src/
├── api/
│   ├── campaigns.py          ← REST endpoints for campaign management
│   ├── webhooks.py           ← Receives Exotel status callbacks
│   ├── analytics.py          ← Campaign analytics API
│   ├── dashboard.py          ← Dashboard API
│   ├── debug.py              ← Debug/monitoring endpoints
│   └── health.py             ← Health check endpoint
│
├── integrations/
│   └── exotel_client.py       ← Exotel REST API client
│
├── services/
│   ├── call_executor.py       ← Executes individual calls
│   ├── call_scheduler.py      ← Schedules calls, manages queue
│   ├── campaign_scheduler.py  ← Background scheduler
│   ├── csv_service.py         ← CSV parsing
│   └── export_service.py      ← Export functionality
│
├── websocket/
│   ├── server.py              ← Main WebSocket handler
│   ├── phase4_event_handlers.py ← Full AI event processor
│   └── session_manager.py     ← In-memory session state
│
├── ai/
│   ├── stt_service.py         ← Deepgram speech-to-text
│   ├── llm_service.py         ← OpenAI language model
│   └── tts_service.py         ← ElevenLabs text-to-speech
│
├── conversation/
│   ├── engine.py              ← Conversation logic
│   ├── prompt_templates.py    ← System prompts
│   ├── playbook_loader.py     ← Conversation playbooks
│   └── state_machine.py       ← Conversation state
│
├── models/
│   ├── campaign.py            ← Campaign SQLAlchemy model
│   ├── lead.py                ← Lead model
│   ├── scheduled_call.py       ← Scheduled call model
│   ├── call_session.py         ← Call session model
│   └── conversation.py         ← Conversation model
│
├── database/
│   ├── connection.py           ← DB/Redis initialization
│   └── repositories.py         ← Data access layer
│
├── config/
│   └── settings.py             ← Pydantic settings
│
├── utils/
│   └── logger.py               ← Structured logging
│
├── workers/
│   └── campaign_worker.py      ← Background job worker
│
└── main.py                      ← FastAPI entry point
```

---

## 7. Deployment Checklist

### Pre-Deployment
- [ ] All environment variables configured
- [ ] PostgreSQL database created and initialized
- [ ] Redis instance running (or configured in-memory mode)
- [ ] Exophlo created in Exotel dashboard with correct WebSocket URL
- [ ] SSL certificate configured (HTTPS required for webhooks)
- [ ] Application health check passing

### Post-Deployment
- [ ] Update OUR_BASE_URL to production domain
- [ ] Update Exotel webhook callbacks to production domain
- [ ] Update Exotel dashboard Exophlo URL to production domain
- [ ] Test single call end-to-end
- [ ] Monitor logs for errors
- [ ] Set up log aggregation & monitoring
- [ ] Set up alerts for failed calls

---

## 8. Testing Your Integration

### Quick Test
```bash
# 1. Start server
python -m src.main

# 2. Create campaign
curl -X POST http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "calling_hours_start": 10, "calling_hours_end": 19}'

# 3. Upload test leads
curl -X POST http://localhost:8000/campaigns/1/upload-csv \
  -F "file=@test_leads.csv"

# 4. Start campaign
curl -X POST http://localhost:8000/campaigns/1/start

# 5. Monitor logs
tail -f logs/server.log
```

### Verify Each Component
```
✓ Health endpoint responding
✓ Campaign creation working
✓ CSV upload processing leads
✓ Call scheduling respects calling hours
✓ WebSocket connection established
✓ Deepgram transcription working
✓ OpenAI generating responses
✓ ElevenLabs audio synthesizing
✓ Database recording call data
✓ Webhooks updating status
✓ Retry logic working on no-answer
```

---

## 9. Monitoring & Observability

### Key Metrics to Track
```
✓ Calls initiated (vs Exotel API failures)
✓ WebSocket connections (vs disconnections)
✓ Average call duration
✓ Successful transcriptions (vs Deepgram errors)
✓ AI response generation latency
✓ Audio synthesis latency
✓ Lead qualification rate
✓ Retry rate
✓ Database query latency
✓ Webhook processing latency
```

### Log Patterns to Monitor
```
ERROR: "Exotel API error"     → Check credentials
ERROR: "WebSocket disconnect" → Check network
ERROR: "Deepgram timeout"     → Check API quota
ERROR: "OpenAI rate limit"    → Reduce concurrent calls
ERROR: "Database connection"  → Check PostgreSQL
WARN:  "Redis unavailable"    → Fallback to in-memory
```

---

## 10. Next Steps

### Immediate
1. Verify all environment variables are set
2. Test health endpoint
3. Run single test call

### This Week
1. Deploy to production
2. Test with real leads
3. Monitor for 24 hours

### This Month
1. Load test with multiple concurrent calls
2. Optimize performance
3. Set up comprehensive monitoring
4. Train on conversation playbooks

---

## Support & Troubleshooting

**WebSocket not connecting?**
- Verify OUR_BASE_URL is public and HTTPS
- Verify Exophlo URL in Exotel dashboard
- Check firewall allows port 8000

**Calls failing?**
- Check Exotel dashboard for account status
- Verify virtual number is active
- Check API credentials

**Transcription issues?**
- Verify audio format (must be µ-law PCM)
- Check Deepgram API key
- Monitor Deepgram dashboard for errors

**AI not responding?**
- Verify OpenAI API key has quota
- Check conversation context
- Monitor OpenAI rate limits

**Audio not playing?**
- Verify ElevenLabs API key
- Check voice ID exists
- Monitor TTS latency

---

**System Status:** Production Ready
**Last Updated:** 2026-01-28
**Architecture Version:** Phase 4 Complete
