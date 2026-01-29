# Integration Todo: Complete AI Voice Agent System

## Overview
This document provides a complete overview of your AI Voice Agent system, integration points, and what needs to be done to connect all components together.

**Current Status:** Phase 4 Complete (Full AI Voice Agent with STT + LLM + TTS)
**Build Date:** 2026-01-28
**Repository:** /Users/prathamkhandelwal/AI Voice Agent

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SYSTEMS                              │
├─────────────────────────────────────────────────────────────────────┤
│  Exotel (Telephony)  │  Deepgram (STT)  │  OpenAI (LLM)  │  ElevenLabs (TTS)
└────────────┬──────────────────┬──────────────────┬──────────────────┘
             │                  │                  │
             │ WebSocket        │ API Calls        │ API Calls
             │                  │                  │
┌────────────▼──────────────────▼──────────────────▼──────────────────┐
│                    FASTAPI APPLICATION                               │
├────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  REST API Layer (for campaign management)                         │
│  ├─ POST /campaigns                    (Create campaign)          │
│  ├─ POST /campaigns/{id}/upload-csv    (Upload leads)             │
│  ├─ POST /campaigns/{id}/start         (Start calling)            │
│  └─ GET /campaigns/{id}                (Get status)               │
│                                                                    │
│  WebSocket Layer (for voice calls)                                │
│  └─ WS /media                          (Exotel voice connection)  │
│                                                                    │
│  Webhook Layer (for call status updates)                          │
│  └─ POST /webhooks/exotel/call-status  (Status callbacks)         │
│                                                                    │
│  Analytics & Dashboard APIs                                       │
│  ├─ GET /analytics/campaign/{id}       (Campaign stats)           │
│  ├─ GET /debug/sessions                (Active sessions)          │
│  └─ GET /exports/calls/{id}            (Call transcripts)         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
             │                  │                  │
             │ Database         │ Redis (sessions) │ Logs
             │ Queries          │ Caching          │ Monitoring
             │                  │                  │
┌────────────▼──────────────────▼──────────────────▼──────────────────┐
│                    DATA LAYER                                         │
├────────────────────────────────────────────────────────────────────┤
│  PostgreSQL               │  Redis            │  File System        │
│  ├─ campaigns             │  ├─ sessions      │  ├─ logs            │
│  ├─ leads                 │  ├─ cache         │  └─ transcripts     │
│  ├─ call_sessions         │  └─ ephemeral     │                     │
│  ├─ scheduled_calls       │    session state  │                     │
│  ├─ conversations         │                   │                     │
│  └─ email_leads           │                   │                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. VOICE CALL INITIATION
**Files:** 
- `/Users/prathamkhandelwal/AI Voice Agent/src/integrations/exotel_client.py`
- `/Users/prathamkhandelwal/AI Voice Agent/src/services/call_executor.py`
- `/Users/prathamkhandelwal/AI Voice Agent/src/api/campaigns.py`

**Entry Points:**
```
POST /campaigns/{campaign_id}/start
  ↓
CallScheduler.schedule_campaign_calls()
  ↓ (background job)
CallExecutor.execute_call()
  ↓
ExotelClient.make_call()
  ↓ (HTTP REST)
Exotel API: POST /v1/Accounts/{SID}/Calls/connect.json
  ↓ (initiates call)
Customer's phone rings
  ↓ (when answered)
Exotel opens WebSocket to /media endpoint
```

**Parameters Needed:**
```python
ExotelClient.make_call(
    to_number: str,              # E.164 format: "+919876543210"
    custom_field: Dict,          # Lead context data
    caller_id: str,              # Optional caller ID
    status_callback_url: str,    # Webhook for status updates
    record: bool                 # Record the call (default: True)
)
```

**Custom Field Example:**
```json
{
  "lead_id": 123,
  "lead_name": "John Doe",
  "phone": "+919876543210",
  "property_type": "2BHK Apartment",
  "location": "Bangalore",
  "budget": "50L - 75L",
  "campaign_id": 1,
  "scheduled_call_id": 456
}
```

### 2. REAL-TIME VOICE HANDLING
**Files:**
- `/Users/prathamkhandelwal/AI Voice Agent/src/websocket/server.py`
- `/Users/prathamkhandelwal/AI Voice Agent/src/websocket/phase4_event_handlers.py`
- `/Users/prathamkhandelwal/AI Voice Agent/src/websocket/session_manager.py`

**WebSocket Endpoint:** `WS /media` (port 8000)

**Full URL:** `wss://your-domain.com/media` (configured in Exotel dashboard Exophlo)

**WebSocket Event Sequence:**
```
1. "connected" 
   └─ Exotel has opened WebSocket connection

2. "start"
   ├─ Contains: call_sid, from, to, customField
   └─ Session created in memory/Redis

3. "media" (repeated)
   ├─ Audio chunks from customer (Base64-encoded PCM)
   ├─ Deepgram transcribes
   ├─ OpenAI generates response
   ├─ ElevenLabs generates audio
   └─ Audio sent back to customer

4. "stop"
   ├─ Call ended
   └─ Session persisted to database

Optional: "dtmf", "clear"
```

### 3. SPEECH-TO-TEXT (Deepgram)
**Files:**
- `/Users/prathamkhandelwal/AI Voice Agent/src/ai/stt_service.py`

**Configuration:**
```
DEEPGRAM_API_KEY=your_key_here
```

**Integration:**
```python
# In phase4_event_handlers.py
STTService.transcribe(audio_bytes)
  ↓
Deepgram API (real-time streaming)
  ↓
Returns: Transcript text with confidence scores
```

### 4. LANGUAGE MODEL (OpenAI)
**Files:**
- `/Users/prathamkhandelwal/AI Voice Agent/src/ai/llm_service.py`
- `/Users/prathamkhandelwal/AI Voice Agent/src/conversation/engine.py`
- `/Users/prathamkhandelwal/AI Voice Agent/src/conversation/prompt_templates.py`

**Configuration:**
```
OPENAI_API_KEY=your_key_here
```

**Integration:**
```python
# In phase4_event_handlers.py
LLMService.generate_response(
    transcript=user_text,
    context={
        "lead_name": "John",
        "property_type": "2BHK",
        "conversation_stage": "intro"
    }
)
  ↓
OpenAI API: gpt-4o-mini
  ↓
Returns: AI response text + intent/metadata
```

**Prompting Strategy:**
- Uses playbook-based prompts (real estate qualification)
- Maintains conversation state/stage
- Detects customer intent
- Knows when to continue/end call

### 5. TEXT-TO-SPEECH (ElevenLabs)
**Files:**
- `/Users/prathamkhandelwal/AI Voice Agent/src/ai/tts_service.py`

**Configuration:**
```
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here
```

**Integration:**
```python
# In phase4_event_handlers.py
TTSService.synthesize(
    text=ai_response,
    voice_id=settings.ELEVENLABS_VOICE_ID
)
  ↓
ElevenLabs API (text-to-speech)
  ↓
Returns: Audio stream (MP3/WAV)
  ↓
Convert to Exotel format (µ-law)
  ↓
Send to customer via WebSocket
```

### 6. CALL STATUS WEBHOOKS
**Files:**
- `/Users/prathamkhandelwal/AI Voice Agent/src/api/webhooks.py`

**Webhook Endpoint:** `POST /webhooks/exotel/call-status`

**Called By:** Exotel after every call state change

**Statuses Received:**
```
- initiated: Call request sent
- ringing: Phone ringing
- in-progress: Call answered, audio streaming
- completed: Call ended normally
- busy: Line was busy
- no-answer: Didn't pick up
- failed: Technical failure
```

**Actions Taken:**
- Update CallSession status in database
- Schedule retries if needed
- Mark leads as qualified/unqualified
- Store call recordings

### 7. CAMPAIGN MANAGEMENT
**Files:**
- `/Users/prathamkhandelwal/AI Voice Agent/src/api/campaigns.py`
- `/Users/prathamkhandelwal/AI Voice Agent/src/services/call_scheduler.py`
- `/Users/prathamkhandelwal/AI Voice Agent/src/workers/campaign_worker.py`

**REST API:**
```
POST /campaigns                          Create campaign
POST /campaigns/{id}/upload-csv          Upload CSV with leads
POST /campaigns/{id}/start               Start calling leads
GET  /campaigns/{id}                     Get campaign status
PATCH /campaigns/{id}                    Update campaign settings
GET  /campaigns/{id}/leads               List campaign leads
```

**Campaign Flow:**
```
1. Create campaign
2. Upload CSV with leads (phone, name, property type, etc.)
3. Start campaign
4. System schedules calls respecting:
   - Calling hours (default: 10 AM - 7 PM)
   - Max concurrent calls (default: 10)
   - Retry logic (up to 3 attempts per lead)
5. Background worker executes pending calls
6. Webhooks update statuses
7. Results tracked in analytics
```

### 8. DATA PERSISTENCE
**Files:**
- `/Users/prathamkhandelwal/AI Voice Agent/src/models/` (SQLAlchemy models)
- `/Users/prathamkhandelwal/AI Voice Agent/src/database/connection.py` (DB setup)

**Database Schema:**
```
campaigns
├─ id (PK)
├─ name, status, created_at
├─ calling_hours, max_concurrent_calls
└─ relationships: leads, scheduled_calls

leads
├─ id (PK)
├─ campaign_id (FK)
├─ name, phone, email, property_type, location, budget
├─ call_attempts, last_call_attempt
└─ relationships: scheduled_calls, call_sessions

scheduled_calls
├─ id (PK)
├─ campaign_id (FK), lead_id (FK)
├─ scheduled_time, status, attempt_number
├─ current_call_sid (links to Exotel call)
└─ failure_reason, max_attempts

call_sessions
├─ id (PK)
├─ call_sid (from Exotel), lead_id (FK)
├─ status (initiated, ringing, in_progress, completed, failed)
├─ duration_seconds, recording_url
├─ answered_at, ended_at
└─ conversation (transcript stored in separate table)

conversations
├─ id (PK)
├─ call_session_id (FK)
├─ transcript_history (JSON)
├─ final_outcome, lead_qualified
└─ extracted_data (JSON)
```

**Session State (Redis or In-Memory):**
```json
{
  "call_sid": "xyz123",
  "lead_id": 456,
  "lead_name": "John",
  "conversation_stage": "intro",
  "transcript_history": [
    {"speaker": "ai", "text": "Hello, I'm calling...", "timestamp": "2026-01-28T10:30:00"},
    {"speaker": "user", "text": "Hi, who is this?", "timestamp": "2026-01-28T10:30:05"}
  ],
  "waiting_for_response": false,
  "last_interaction_time": "2026-01-28T10:30:05"
}
```

---

## Complete Integration Checklist

### Phase 1: Setup & Configuration
- [ ] Exotel account created and verified
- [ ] Exotel API credentials obtained (Account SID, API Key, API Token)
- [ ] Virtual number allocated by Exotel
- [ ] `.env` file configured with all API keys:
  - [ ] EXOTEL_ACCOUNT_SID
  - [ ] EXOTEL_API_KEY
  - [ ] EXOTEL_API_TOKEN
  - [ ] EXOTEL_VIRTUAL_NUMBER
  - [ ] EXOTEL_EXOPHLO_ID
  - [ ] DEEPGRAM_API_KEY
  - [ ] OPENAI_API_KEY
  - [ ] ELEVENLABS_API_KEY
  - [ ] ELEVENLABS_VOICE_ID
  - [ ] DATABASE_URL (PostgreSQL)
  - [ ] REDIS_URL
  - [ ] OUR_BASE_URL (ngrok URL or domain)

### Phase 2: Database Setup
- [ ] PostgreSQL database created
- [ ] Database migrations run (`alembic upgrade head` or equivalent)
- [ ] Tables created: campaigns, leads, scheduled_calls, call_sessions, conversations
- [ ] Redis instance running (or using in-memory fallback)

### Phase 3: Exotel Dashboard Configuration
- [ ] Exophlo (voice flow) created in Exotel dashboard
- [ ] Exophlo configured with:
  - [ ] Voicebot Applet enabled
  - [ ] WebSocket endpoint URL: `wss://your-domain.com/media`
  - [ ] Recording enabled (if desired)
- [ ] Status callback URL configured: `https://your-domain.com/webhooks/exotel/call-status`
- [ ] Exophlo ID saved to `.env` as EXOTEL_EXOPHLO_ID

### Phase 4: Application Deployment
- [ ] Application deployed to cloud (Railway, Heroku, EC2, etc.)
- [ ] Public URL accessible and HTTPS enabled
- [ ] ngrok running (if testing locally): `ngrok http 8000`
- [ ] Firewall rules allow WebSocket connections
- [ ] Health check endpoint responding: `GET /health`

### Phase 5: Campaign Creation
- [ ] Campaign created via REST API: `POST /campaigns`
- [ ] Campaign CSV uploaded with leads: `POST /campaigns/{id}/upload-csv`
- [ ] CSV format correct (name, phone, property_type, location, budget)

### Phase 6: Testing & Validation
- [ ] Test single call: Use test_exotel_call.sh script
- [ ] Verify WebSocket connection in logs
- [ ] Verify Deepgram transcription working
- [ ] Verify OpenAI responses generated
- [ ] Verify ElevenLabs audio synthesis working
- [ ] Verify call recordings stored
- [ ] Verify database records created

### Phase 7: Production Hardening
- [ ] Error handling tested
- [ ] Retry logic tested
- [ ] Max concurrent calls limit tested
- [ ] Calling hours restrictions tested
- [ ] Session persistence tested
- [ ] Database connection pooling configured
- [ ] Logging aggregation configured (CloudWatch, DataDog, etc.)
- [ ] Monitoring/alerting configured

### Phase 8: Scaling & Optimization
- [ ] Load testing performed
- [ ] Database indexes optimized
- [ ] Redis cache strategy optimized
- [ ] Websocket connection pooling configured
- [ ] Rate limiting configured for APIs
- [ ] Cost optimization (API calls, concurrent connections)

---

## Integration Testing Guide

### 1. Local Testing Setup
```bash
# Terminal 1: Start application
cd /Users/prathamkhandelwal/AI\ Voice\ Agent
source venv/bin/activate
python -m src.main

# Terminal 2: Start ngrok
ngrok http 8000
# Copy ngrok URL and update OUR_BASE_URL in .env

# Terminal 3: Run tests
bash test_exotel_call.sh
```

### 2. Test Workflow
```bash
# 1. Create campaign
curl -X POST http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Campaign",
    "max_attempts_per_lead": 3,
    "calling_hours_start": 10,
    "calling_hours_end": 19
  }'

# Note campaign_id from response

# 2. Upload leads CSV
curl -X POST http://localhost:8000/campaigns/1/upload-csv \
  -F "file=@leads.csv"

# 3. Start campaign
curl -X POST http://localhost:8000/campaigns/1/start

# 4. Monitor call in logs
tail -f logs/server.log | grep "call_sid"

# 5. Get campaign status
curl http://localhost:8000/campaigns/1

# 6. Check active sessions
curl http://localhost:8000/debug/sessions
```

### 3. Key Log Points to Watch
```
✓ "Initiating Exotel call" - Call being sent to Exotel
✓ "WebSocket connection established" - Customer connected
✓ "WebSocket event received" - Events flowing from Exotel
✓ "Deepgram transcription" - Speech being converted to text
✓ "OpenAI response generated" - AI generating reply
✓ "ElevenLabs audio synthesized" - Voice being generated
✓ "Exotel webhook received" - Call completion notification
✓ "Session persisted to database" - Transcript saved
```

---

## Troubleshooting Integration Issues

### Issue 1: WebSocket Connection Fails
**Symptom:** "WebSocket connection refused"
**Solution:**
- Verify Exophlo URL in Exotel dashboard is correct
- Verify OUR_BASE_URL environment variable is set to public URL
- Verify ngrok is running if testing locally
- Check firewall allows port 8000

### Issue 2: Exotel API Error
**Symptom:** "Exotel API error: 401"
**Solution:**
- Verify EXOTEL_API_KEY and EXOTEL_API_TOKEN are correct
- Verify EXOTEL_ACCOUNT_SID is correct
- Check Exotel dashboard for account status
- Verify virtual number is active

### Issue 3: No Transcription
**Symptom:** "No transcript received from Deepgram"
**Solution:**
- Verify DEEPGRAM_API_KEY is correct
- Check if audio is being sent to Deepgram
- Verify audio format is correct (µ-law mono 8kHz)
- Check Deepgram dashboard for API usage

### Issue 4: OpenAI Not Responding
**Symptom:** "OpenAI API error" or timeout
**Solution:**
- Verify OPENAI_API_KEY is correct
- Check OpenAI usage dashboard
- Verify API key has sufficient quota
- Check if rate limit exceeded

### Issue 5: ElevenLabs Audio Issues
**Symptom:** "Robotic audio" or "Audio not streaming"
**Solution:**
- Verify ELEVENLABS_API_KEY and VOICE_ID are correct
- Check if voice exists in your account
- Verify audio format conversion working
- Check ElevenLabs dashboard for issues

### Issue 6: Database Connection Fails
**Symptom:** "Cannot connect to PostgreSQL"
**Solution:**
- Verify DATABASE_URL format is correct
- Check PostgreSQL server is running
- Verify database credentials
- Verify database exists
- Check network connectivity

### Issue 7: No Calls Being Scheduled
**Symptom:** "Campaign started but no calls"
**Solution:**
- Verify leads were uploaded successfully
- Check current time is within calling hours
- Check day is not Sunday
- Check max concurrent calls not exceeded
- Verify campaign status is RUNNING

---

## Next Steps for Full Integration

### Immediate (This Week)
1. **Verify All Configurations**
   - Run health check: `curl http://localhost:8000/health`
   - Verify all environment variables loaded
   - Test database connection
   - Test Redis connection

2. **Test Single Call Flow**
   - Create test campaign
   - Upload single lead
   - Start campaign
   - Monitor complete call in logs
   - Verify transcript saved

3. **Test Error Scenarios**
   - Test with invalid phone number
   - Test retry logic (no answer)
   - Test max concurrent calls limit
   - Test calling hours restriction

### Short-term (This Month)
1. **Production Deployment**
   - Deploy to Railway/Heroku/AWS
   - Configure custom domain
   - Update Exotel webhook URLs
   - Run full campaign test

2. **Analytics & Monitoring**
   - Enable detailed logging
   - Configure error alerting
   - Set up dashboard
   - Track key metrics

3. **Performance Optimization**
   - Load test with multiple concurrent calls
   - Optimize database queries
   - Configure connection pooling
   - Monitor resource usage

### Long-term (Ongoing)
1. **Feature Enhancements**
   - Add lead qualification scoring
   - Implement callback scheduling
   - Add multi-language support
   - Add SMS follow-ups

2. **System Reliability**
   - Implement automatic failover
   - Add redundancy for critical services
   - Implement comprehensive logging
   - Add alerting for SLA breaches

3. **Cost Optimization**
   - Monitor API usage and costs
   - Optimize concurrent call limits
   - Implement call duration limits
   - Track ROI per campaign

---

## Key Files Reference

| Component | File Path | Purpose |
|-----------|-----------|---------|
| Exotel Integration | `src/integrations/exotel_client.py` | REST API calls to Exotel |
| Call Execution | `src/services/call_executor.py` | Triggers individual calls |
| Call Scheduling | `src/services/call_scheduler.py` | Schedules and manages queue |
| Campaign API | `src/api/campaigns.py` | REST endpoints for campaign management |
| WebSocket Server | `src/websocket/server.py` | Main WebSocket connection handler |
| Event Handlers | `src/websocket/phase4_event_handlers.py` | Processes Exotel events |
| Session Manager | `src/websocket/session_manager.py` | In-memory session state |
| STT Service | `src/ai/stt_service.py` | Deepgram integration |
| LLM Service | `src/ai/llm_service.py` | OpenAI integration |
| TTS Service | `src/ai/tts_service.py` | ElevenLabs integration |
| Webhooks | `src/api/webhooks.py` | Receives Exotel status callbacks |
| Main App | `src/main.py` | FastAPI application setup |
| Settings | `src/config/settings.py` | Configuration management |
| Database | `src/database/connection.py` | Database initialization |
| Models | `src/models/` | SQLAlchemy data models |

---

## Environment Variables Checklist

```env
# Application
APP_NAME=Real Estate Voice AI
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Server
HOST=0.0.0.0
PORT=8000

# Database (Required)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/voiceai

# Redis (Optional - will use in-memory fallback)
REDIS_URL=redis://localhost:6379

# Exotel (Required)
EXOTEL_ACCOUNT_SID=xxx
EXOTEL_API_KEY=xxx
EXOTEL_API_TOKEN=xxx
EXOTEL_VIRTUAL_NUMBER=080XXXXXXXX
EXOTEL_EXOPHLO_ID=xxx
OUR_BASE_URL=https://your-domain.com

# AI Services (Required)
DEEPGRAM_API_KEY=xxx
OPENAI_API_KEY=xxx
ELEVENLABS_API_KEY=xxx
ELEVENLABS_VOICE_ID=xxx

# Call Settings
MAX_CALL_DURATION_MINUTES=10
CALLING_HOURS_START=10
CALLING_HOURS_END=19
MAX_CONCURRENT_CALLS=10
```

---

**Document Status:** Ready for Integration
**Last Updated:** 2026-01-28
**Maintainer:** AI Voice Agent Development Team
