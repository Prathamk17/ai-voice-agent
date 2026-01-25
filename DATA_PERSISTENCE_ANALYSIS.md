# Data Persistence Analysis

## Current Architecture: Redis + PostgreSQL

### How Data is Supposed to Flow:

```
Call Starts → Redis (active session) → Call Ends → PostgreSQL (permanent storage)
```

---

## ✅ What IS Working:

### 1. **Redis - Active Call Storage**
- **Location**: `src/websocket/session_manager.py`
- **Purpose**: Store conversation state during **active calls**
- **Data Stored**:
  - `transcript_history`: Real-time conversation transcript
  - `collected_data`: Lead information gathered during call
  - `conversation_stage`: Current stage of conversation
  - `objections_encountered`: List of objections
  - All other session state (audio buffers, flags, etc.)
- **Key Pattern**: `session:<call_sid>`
- **TTL**: 1 hour (auto-expires after call ends)

### 2. **PostgreSQL - Call Sessions Table**
- **Location**: `src/models/call_session.py`
- **Purpose**: **Permanent storage** of completed calls
- **Data Fields**:
  - `full_transcript`: JSON string of complete conversation
  - `collected_data`: JSON string of gathered lead info
  - `duration_seconds`: Call duration
  - `recording_url`: Link to call recording
  - `status`, `outcome`, timestamps, etc.

---

## ❌ CRITICAL ISSUE FOUND:

### **Transcripts Are NOT Being Persisted to PostgreSQL!**

When a call ends, the transcript data in Redis should be moved to the PostgreSQL `call_sessions` table, but **this is not happening**.

### Evidence:

1. **`src/websocket/event_handlers.py:412-436`** - `handle_stop()` method:
   - Only updates `waiting_for_response` flag
   - Does NOT save transcript to database
   - Comment says "Will be cleaned up by finalize_call" but `finalize_call()` doesn't exist

2. **`src/api/webhooks.py:23-110`** - Exotel webhook handler:
   - Updates call status (initiated, ringing, completed, etc.)
   - Updates duration and recording URL
   - Does NOT copy transcript from Redis to PostgreSQL

3. **`src/websocket/server.py:143-160`** - WebSocket disconnect:
   - Just updates session flag
   - Does NOT persist transcript

### Result:
- ✅ Transcripts ARE being collected during calls (in Redis)
- ❌ Transcripts ARE NOT saved to database when calls end
- ⚠️ Redis TTL = 1 hour, so transcripts disappear after that

---

## 🔍 Why You Can't See Your Test Call Transcript:

Your test call transcript is probably:
1. **Still in Redis** (if the call ended less than 1 hour ago) - but you're checking the production Redis on Railway, not local
2. **Already expired from Redis** (if >1 hour has passed)
3. **Never saved to PostgreSQL** (due to the missing persistence logic)

---

## 🛠️ The Fix Needed:

You need to add code that:
1. **On call end** (when `handle_stop()` is called or WebSocket disconnects)
2. **Fetches the session from Redis** (using `session_manager.get_session()`)
3. **Gets the CallSession from PostgreSQL** (using the `call_sid`)
4. **Updates CallSession** with:
   ```python
   call_session.full_transcript = json.dumps(session.transcript_history)
   call_session.collected_data = json.dumps(session.collected_data)
   call_session.outcome = determine_outcome(session)
   ```
5. **Commits to database**
6. **Deletes from Redis** (optional, since TTL handles it)

### Where to Add This:
Either in:
- `src/websocket/event_handlers.py` - `handle_stop()` method
- `src/api/webhooks.py` - when status is "completed"
- A new background task triggered on disconnect

---

## 📊 Usage Summary:

| Database | Purpose | When Used | Data Stored |
|----------|---------|-----------|-------------|
| **Redis** | Temporary session state | During active calls | Real-time transcript, session state |
| **PostgreSQL** | Permanent records | After call ends | Final transcript, analytics, history |

### Current Issue:
The **bridge between Redis → PostgreSQL is missing**, so data gets lost!

---

## Next Steps:

Would you like me to:
1. **Fix the missing persistence logic** to save transcripts to PostgreSQL?
2. **Check your Railway Redis** to see if the recent test call is still there?
3. **Add a background job** that periodically saves active sessions?
