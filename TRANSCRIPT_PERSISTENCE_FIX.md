# Transcript Persistence Fix - Summary

## Problem Fixed
Previously, conversation transcripts were being collected in Redis during calls but were **never saved to PostgreSQL** when calls ended. This meant:
- ❌ Transcripts disappeared after 1 hour (Redis TTL)
- ❌ No permanent record of conversations
- ❌ Analytics and reporting couldn't access call data

## Solution Implemented

### 1. Added `persist_session_to_db()` Method
**Location**: [`src/websocket/event_handlers.py:413-477`](src/websocket/event_handlers.py#L413-L477)

This new method:
- ✅ Fetches session data from Redis
- ✅ Finds the corresponding CallSession in PostgreSQL
- ✅ Saves `full_transcript` (conversation history)
- ✅ Saves `collected_data` (lead information)
- ✅ Commits to database
- ✅ Includes error handling and logging

### 2. Updated `handle_stop()` Method
**Location**: [`src/websocket/event_handlers.py:503`](src/websocket/event_handlers.py#L503)

Now calls `persist_session_to_db()` when a call ends normally.

### 3. Updated WebSocket Disconnect Handler
**Location**: [`src/websocket/server.py:165-171`](src/websocket/server.py#L165-L171)

Added persistence in the cleanup `finally` block to ensure transcripts are saved even if the `stop` event isn't received.

### 4. Updated Phase 3 Event Handler
**Location**: [`src/websocket/phase3_event_handlers.py:362`](src/websocket/phase3_event_handlers.py#L362)

Added persistence call after displaying the transcript.

### 5. Phase 4 Event Handler
Phase 4 already calls `super().handle_stop()` which chains to Phase 3, so it automatically gets the persistence functionality.

---

## Files Modified

1. ✏️ [`src/websocket/event_handlers.py`](src/websocket/event_handlers.py)
   - Added imports: `CallSession`, `get_async_session_maker`, `select`
   - Added `persist_session_to_db()` method
   - Updated `handle_stop()` to call persistence

2. ✏️ [`src/websocket/server.py`](src/websocket/server.py)
   - Updated `finally` block to persist data on disconnect

3. ✏️ [`src/websocket/phase3_event_handlers.py`](src/websocket/phase3_event_handlers.py)
   - Updated `handle_stop()` to call persistence

---

## How It Works Now

```
┌─────────────────────────────────────────────────────────────┐
│                     Call Flow                                │
└─────────────────────────────────────────────────────────────┘

1. Call Starts
   └─> Session created in Redis
       - transcript_history: []
       - collected_data: {}

2. During Call
   └─> Redis session updated in real-time
       - transcript_history: [user, ai, user, ai...]
       - collected_data: {budget: 5000000, location: "Mumbai"...}

3. Call Ends (stop event OR disconnect)
   └─> persist_session_to_db() called
       ├─> Get session from Redis
       ├─> Find CallSession in PostgreSQL
       ├─> Update full_transcript = JSON(transcript_history)
       ├─> Update collected_data = JSON(collected_data)
       └─> Commit to database ✅

4. After 1 Hour
   └─> Redis auto-expires (TTL)
       BUT data is safe in PostgreSQL! ✅
```

---

## Testing the Fix

### Option 1: Make a New Test Call

1. **Make a test call** to your Exotel number
2. **Have a short conversation** with the AI
3. **End the call**
4. **Check the database**:
   ```bash
   python3 scripts/view_transcripts.py
   ```

Expected output:
```
📞 Found 1 call(s):

CALL SID                       STATUS          OUTCOME             DURATION   DATE
---------------------------------------------------------------------------------
CA1234567890abcdef...          completed       qualified           45s        2026-01-25 16:45:00

To view a specific transcript, run:
  python3 scripts/view_transcripts.py <call_sid>
```

5. **View full transcript**:
   ```bash
   python3 scripts/view_transcripts.py CA1234567890abcdef...
   ```

Expected output:
```
================================================================================
📞 CALL TRANSCRIPT
================================================================================

📋 CALL INFO:
  Call SID:       CA1234567890abcdef...
  Status:         completed
  Duration:       45s

📊 COLLECTED DATA:
  budget: 5000000
  location: Mumbai

📝 FULL TRANSCRIPT:
--------------------------------------------------------------------------------
[16:45:12] 🤖 AI:         Hello! I'm calling from Real Estate...
[16:45:18] 👤 USER:       Hi, yes?
[16:45:20] 🤖 AI:         Great! What's your budget for this property?
[16:45:25] 👤 USER:       Around 50 lakhs
...
```

### Option 2: Check Production Database

If you want to see if any old calls have data, connect to your Railway PostgreSQL:

```bash
# Get DATABASE_URL from Railway dashboard
export DATABASE_URL="postgresql://..."

# Run the script
python3 scripts/view_transcripts.py
```

---

## What to Look For in Logs

When a call ends, you should now see these log messages:

```
INFO - Call stopped | call_sid=CA123...
INFO - Persisting transcript to database | call_sid=CA123... | exchanges=8
INFO - Persisting collected data to database | call_sid=CA123... | fields=['budget', 'location', 'property_type']
INFO - Session successfully persisted to database | call_sid=CA123...
```

If you see any errors:
```
ERROR - Failed to persist session to database | call_sid=CA123... | error=...
```

Check:
1. Database connection is working
2. CallSession record exists for that call_sid
3. Redis session exists at the time of persistence

---

## Deployment

### Deploy to Railway

```bash
# Commit the changes
git add .
git commit -m "Fix: Persist conversation transcripts to PostgreSQL when calls end"
git push

# Railway will auto-deploy
```

### Verify Deployment

1. Check Railway logs for startup messages
2. Make a test call
3. Check database using the scripts above

---

## Future Improvements

### Optional Enhancements:

1. **Add Retry Logic**: If database save fails, retry a few times
2. **Background Task**: Move persistence to a background job for faster response
3. **Periodic Backup**: Save sessions to DB every 30 seconds during long calls
4. **Analytics**: Trigger analytics computation after persisting

---

## Rollback Plan

If something goes wrong, you can rollback:

```bash
git revert HEAD
git push
```

This will remove the persistence changes and restore the previous behavior (transcripts only in Redis).

---

## Questions or Issues?

If transcripts still aren't appearing:
1. Check Railway logs for persistence errors
2. Verify DATABASE_URL is set correctly
3. Ensure CallSession records are being created (check webhooks)
4. Run the monitoring script during a call:
   ```bash
   python3 scripts/live_call_monitor.py
   ```
