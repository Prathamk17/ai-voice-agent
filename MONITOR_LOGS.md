# 📊 How to Monitor Your Refactored AI Voice Agent

## Real-Time Log Monitoring

Use this command to see only the important events from the new refactored system:

```bash
tail -f server.log | grep -E "⚡|✨|🛑|Streaming LLM|LOW LATENCY|immediate barge-in|LLM decision"
```

## What to Look For

### ✅ **When a Call Comes In:**

**1. Streaming Transcription (NEW)**
```
INFO - Streaming transcription complete | model=nova-2-phonecall
```
- Confirms Deepgram WebSocket streaming is working
- Should show model: `nova-2-phonecall` (not `nova-2`)

---

**2. LLM Response (NEW)**
```
INFO - Streaming LLM response generated | intent=asking_budget | next_action=ask_question
⚡ LLM response time: 450ms
```
- Shows LLM streaming is working
- Response time should be <800ms (target: <500ms)
- Shows intent and next_action (NEW JSON structure)

---

**3. LLM Decision Logging (NEW)**
```
INFO - LLM decision | intent=not_interested | next_action=end_call | should_end_call=true | outcome=not_interested
```
- Confirms conversation flow is LLM-controlled (not playbook)
- Shows what the LLM decided to do

---

**4. Low Latency TTS (NEW)**
```
INFO - Generating speech (LOW LATENCY MODE) | text_preview=Okay cool! So you're looking for...
INFO - Speech generated (low latency) | duration_seconds=0.289
```
- Confirms `eleven_turbo_v2_5` is being used
- TTS should be <500ms (target: <300ms)

---

**5. Filler Audio (NEW)**
```
⏱️ LLM taking >300ms, playing filler
✨ Played filler audio: hmm.pcm
```
- Only shows if LLM takes >300ms
- Masks latency with natural fillers

---

**6. Immediate Barge-in (NEW)**
```
🛑 TTS interrupted by user (immediate barge-in) | chunks_sent=15 | total_chunks=200
```
- Shows user interrupted the bot
- Should happen within ~60-100ms of user speaking

---

## Alternative: See ALL Activity

To see everything happening in real-time:

```bash
tail -f server.log
```

---

## Test Checklist

### **Make a Test Call**

1. Call your Exotel number
2. Let the bot introduce itself
3. Respond to the bot's questions
4. Try interrupting the bot mid-sentence (test barge-in)
5. Ask a complex question (test filler audio)
6. Say "not interested" (test call ending)

---

### **What You Should Hear**

✅ **Casual, natural tone**: "I'm Alex" (not "I am Alex")
✅ **Fast responses**: <1 second from when you stop speaking
✅ **Filler words**: "Hmm", "Okay" before complex responses
✅ **Immediate interruption**: Bot stops within 100ms when you speak
✅ **Indian Hinglish**: Uses "accha", "thik hai", contractions

---

### **What You Should NOT Hear**

❌ Formal language: "I would like to assist you"
❌ Long delays: >2 seconds before response
❌ Robotic speech: No variation in tone
❌ Continues speaking when interrupted

---

## Troubleshooting

### **If you see "Playbook loaded successfully"**
- Old code is still running
- Kill server: `pkill -f uvicorn`
- Restart: `uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`

### **If you see "File-based transcription"**
- Deepgram WebSocket failed (fallback is OK)
- Check Deepgram API key is valid
- Upgrade SDK: `pip install --upgrade deepgram-sdk`

### **If no logs appear during call**
- Check server is running: `lsof -i :8000`
- Check Exotel webhook URL is correct
- Check network connectivity

### **If TTS fails with "model not found"**
- ElevenLabs turbo model not available
- Edit [src/ai/tts_service.py:114](src/ai/tts_service.py#L114)
- Change back to: `model_id="eleven_multilingual_v2"`

---

## Success Criteria

**Minimum Requirements (Must Pass):**
- ✅ No "Playbook loaded" messages in logs
- ✅ Sees "Streaming LLM response generated" on every user turn
- ✅ Sees "LLM decision" with intent and next_action
- ✅ Response times <1.5s (target: <1s)
- ✅ Casual tone in responses

**Ideal Performance (Target):**
- 🎯 LLM response time <500ms
- 🎯 TTS generation <300ms
- 🎯 Total time-to-first-audio <1s
- 🎯 Filler audio plays <20% of the time
- 🎯 Barge-in latency <100ms

---

## Quick Commands Reference

```bash
# Monitor refactored system activity
tail -f server.log | grep -E "⚡|✨|🛑|Streaming LLM|LOW LATENCY"

# See all logs
tail -f server.log

# Check server status
lsof -i :8000

# Restart server
pkill -f uvicorn && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Check error count
grep "ERROR" server.log | tail -20

# Check last 10 calls
grep "WebSocket connected" server.log | tail -10
```

---

**Your refactored system is READY for testing!** 🚀

Make a test call and watch the logs to verify the new LLM-controlled flow is working correctly.
