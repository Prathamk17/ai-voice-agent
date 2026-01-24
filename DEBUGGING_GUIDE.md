# 🐛 Debugging & Monitoring Guide

Complete guide to debugging your AI Voice Agent with real-time monitoring tools.

---

## 🎯 Quick Start

### Option 1: Full Real-Time Monitor (RECOMMENDED)
```bash
python scripts/live_call_monitor.py
```
**Shows everything in real-time with colors:**
- 📞 New calls starting
- 👤 User speech (transcribed by Deepgram)
- 🤖 AI responses (from playbook/GPT-4)
- 📍 Stage changes (intro → discovery → closing)
- 📊 Collected data (budget, timeline, etc.)
- ⚠️  Objections detected
- 🔊 Bot speaking status
- ⏳ Waiting for user input

**Perfect for**: Watching calls happen live, debugging conversation flow

---

### Option 2: Transcript-Only Monitor
```bash
# Monitor all calls
python scripts/live_transcript_monitor.py

# Monitor specific call
python scripts/live_transcript_monitor.py <call_sid>
```
**Shows**: Just the conversation transcript (cleaner view)

**Perfect for**: Focusing on what's being said

---

### Option 3: View Past Transcripts
```bash
# List all active calls (in Redis)
python scripts/view_call_transcript.py

# View specific active call
python scripts/view_call_transcript.py <call_sid>

# Export to file
python scripts/view_call_transcript.py <call_sid> --export transcript.txt
```

---

### Option 4: View Completed Calls (Database)
```bash
# List recent calls
python scripts/view_transcripts.py

# View last 20 calls
python scripts/view_transcripts.py --last 20

# View specific call
python scripts/view_transcripts.py <call_sid>
```

---

## 📋 Typical Debugging Workflow

### 1. Start the Monitor BEFORE Making a Call
```bash
# In terminal 1: Start real-time monitor
python scripts/live_call_monitor.py
```

### 2. Make a Test Call
Call your Exotel number from your phone

### 3. Watch the Output
You'll see:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📞 NEW CALL STARTED                                                                          ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃   🆔 Call SID: b4258b1168f2c651847ae823b9661a1n                                              ┃
┃   👤 Lead:     Customer (09116430391)                                                        ┃
┃   📍 Stage:    intro                                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

[20:10:21] [b4258b1168f2...]  🤖 AI:   Hi! This is Alex from DreamHome Properties. Am I
                                       speaking with Customer?

[20:10:23] 🔊  Bot speaking: True
[20:10:25] ✅  Bot speaking: False
[20:10:25] ⏳  Waiting for user: True

[20:10:27] [b4258b1168f2...]  👤 USER: Hello?

[20:10:27] 📊 Collected: response = unclear
```

### 4. After the Call
```bash
# View the full transcript
python scripts/view_call_transcript.py b4258b1168f2c651847ae823b9661a1n

# Or check database (after call finalizes)
python scripts/view_transcripts.py --last 5
```

---

## 🔍 What to Look For

### ✅ GOOD - Everything Working
```
[20:10:21] [abc123...]  🤖 AI:   Hi! This is Alex...     ← AI speaks
[20:10:23] 🔊  Bot speaking: True                        ← TTS starts
[20:10:25] ✅  Bot speaking: False                       ← TTS finishes
[20:10:25] ⏳  Waiting for user: True                    ← Ready for input
[20:10:27] [abc123...]  👤 USER: Hello?                  ← User transcribed!
[20:10:28] 📊 Collected: response = yes                  ← Data collected
[20:10:29] [abc123...]  🤖 AI:   Great! I'm calling...   ← AI responds
```

### ❌ BAD - Transcripts Not Saving
```
[20:10:21] [abc123...]  🤖 AI:   Hi! This is Alex...
[20:10:23] 🔊  Bot speaking: True
[20:10:25] ✅  Bot speaking: False
[20:10:25] ⏳  Waiting for user: True
(nothing appears when you speak)                          ← Problem!
```

**Diagnosis**: If you see NO user transcripts appearing:
1. Deepgram STT might be failing
2. Audio buffer not accumulating
3. VAD threshold too high

### ⚠️ PARTIAL - User Speaks But Not Transcribed
**Server logs show**:
```
INFO - Transcription complete | transcript=Hello?
INFO - User spoke | call_sid=..., transcript=Hello?
```

**But monitor shows**: Nothing!

**Diagnosis**: `add_to_transcript()` is not saving to Redis

---

## 🛠️ Common Issues & Fixes

### Issue 1: Empty Transcripts
**Symptom**: Monitor shows call started, but no USER entries appear

**Check**:
```bash
# 1. Watch the monitor while speaking
python scripts/live_call_monitor.py

# 2. Speak LOUDLY and CLEARLY for 2-3 seconds
# 3. Do you see a USER entry?
```

**If NO**:
- Audio buffer might not be accumulating (8000 bytes needed)
- VAD threshold too high (RMS > 500)
- Deepgram API failing

**If logs show transcription but monitor doesn't**:
- Bug in `add_to_transcript()` function
- Redis not saving properly

### Issue 2: Audio Quality Poor
**Symptom**: Robotic, choppy voice

**Already Fixed**: Changed from turbo to multilingual_v2 model

**Test**: Make a new call and listen

### Issue 3: AI Not Responding
**Symptom**: USER speaks, transcript appears, but no AI response

**Check**:
- Does conversation_stage change?
- Are objections being detected?
- Check server logs for LLM errors

---

## 📊 Understanding the Output

### Color Coding
- 🟢 **GREEN**: User speech
- 🔵 **BLUE**: AI speech
- 🟡 **YELLOW**: State changes, warnings
- 🔴 **RED**: Errors, call ended
- 🔵 **CYAN**: Stage changes, data collected

### Icons Guide
- 📞 New call started
- 👤 User speaking
- 🤖 AI speaking
- 📍 Stage change
- 📊 Data collected
- ⚠️  Objection detected
- 🔊 Bot is speaking
- 🔇 Bot stopped speaking
- ⏳ Waiting for user input
- ✅ Ready for response
- 📵 Call ended

---

## 🧪 Testing Checklist

Use this checklist when testing your voice agent:

```bash
# Terminal 1: Start monitor
python scripts/live_call_monitor.py
```

Then make a call and verify:

- [ ] ✅ Call connects (see "NEW CALL STARTED")
- [ ] ✅ AI intro plays (see 🤖 AI: line)
- [ ] ✅ Bot speaking flag appears (🔊 Bot speaking: True)
- [ ] ✅ Bot stops speaking (✅ Bot speaking: False)
- [ ] ✅ System waits for user (⏳ Waiting for user: True)
- [ ] ✅ User speech appears after speaking (👤 USER: ...)
- [ ] ✅ Data gets collected (📊 Collected: ...)
- [ ] ✅ AI responds to user (🤖 AI: ...)
- [ ] ✅ Stage progresses (📍 Stage: intro → discovery)
- [ ] ✅ Objections handled if present (⚠️ New objection: ...)
- [ ] ✅ Call ends gracefully (📵 CALL ENDED)

If ANY step fails, you know exactly where the issue is!

---

## 💡 Pro Tips

### Tip 1: Split Screen
```bash
# Terminal 1: Monitor
python scripts/live_call_monitor.py

# Terminal 2: Server logs
tail -f server.log

# Terminal 3: Commands
# Keep this free for running other commands
```

### Tip 2: Export Transcripts
```bash
# After call, export for analysis
python scripts/view_call_transcript.py <call_sid> --export analysis.txt
```

### Tip 3: Monitor Specific Call
```bash
# If multiple calls, focus on one
python scripts/live_transcript_monitor.py <call_sid>
```

### Tip 4: Check Redis Directly
```bash
# See what's actually in Redis
redis-cli
> KEYS session:*
> GET session:<call_sid>
> exit
```

---

## 🚨 Emergency Debugging

If something is completely broken:

### 1. Check Services
```bash
# PostgreSQL
pg_isready

# Redis
redis-cli ping
# Should return: PONG

# Server
curl http://localhost:8000/health
```

### 2. Check API Keys
```bash
python3 -c "
from src.config.settings import settings
print('Deepgram:', 'OK' if settings.DEEPGRAM_API_KEY else 'MISSING')
print('OpenAI:', 'OK' if settings.OPENAI_API_KEY else 'MISSING')
print('ElevenLabs:', 'OK' if settings.ELEVENLABS_API_KEY else 'MISSING')
"
```

### 3. Test APIs Directly
```bash
# Test Deepgram
python3 test_deepgram.py

# Check the scripts/ folder for other test scripts
ls scripts/test_*.py
```

### 4. Clear All Sessions
```bash
# If Redis has stale sessions
redis-cli
> KEYS session:*
> DEL session:<call_sid>  # Delete specific
> FLUSHDB  # Delete ALL (use carefully!)
```

---

## 📞 Support

If you're still stuck:

1. **Capture the output**:
   ```bash
   python scripts/live_call_monitor.py > debug.log 2>&1
   ```

2. **Make a test call** while monitoring

3. **Share**:
   - The `debug.log` file
   - The call_sid
   - What you said during the call
   - What you expected vs what happened

---

## 🎓 Learning More

- [Server Logs Guide](MODULE4_README.md)
- [Conversation Playbook](config/conversation_playbook.yaml)
- [API Documentation](docs/)

---

**Happy Debugging! 🐛→🦋**
