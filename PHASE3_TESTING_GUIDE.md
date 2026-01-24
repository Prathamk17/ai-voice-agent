# 🤖 Phase 3 Testing Guide - OpenAI LLM Integration

## ✅ What Was Implemented

Phase 3 adds **intelligent AI conversation** to your voice agent! Here's what's new:

### New Features
- ✅ **OpenAI GPT-4o-mini Integration** - Bot has intelligent conversations
- ✅ **Context-Aware Responses** - Remembers conversation history
- ✅ **Real Estate Sales Context** - Asks qualification questions naturally
- ✅ **Intent Detection** - Understands customer interest level
- ✅ **Call Flow Management** - Decides when to continue or end calls
- ✅ **Full Conversation Logging** - Tracks entire customer-agent dialogue

### What Works Now
```
Customer speaks → Deepgram STT → OpenAI LLM → Intelligent Response (logged)
                                               ↓
                                         Beep acknowledgment
```

### What's Still Missing (Coming in Phase 4)
- ❌ Natural voice responses (ElevenLabs TTS)
- Currently using beeps instead of spoken words

---

## 🔧 Configuration

### 1. Update Your `.env` File

**IMPORTANT:** Set the test mode to Phase 3:

```bash
# Add this line to your .env file
EXOTEL_TEST_MODE=phase3
```

### 2. Verify Required API Keys

Phase 3 requires these API keys in your `.env`:

```bash
# Deepgram (for speech-to-text)
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# OpenAI (for conversation - NEW for Phase 3!)
OPENAI_API_KEY=your_openai_api_key_here
```

**Don't have these keys?**
- Deepgram: https://deepgram.com (Free tier available)
- OpenAI: https://platform.openai.com/api-keys (Uses GPT-4o-mini - very affordable)

### 3. Optional: Railway Deployment URL

If testing via Exotel on Railway:

```bash
OUR_BASE_URL=https://your-app-name.railway.app
```

---

## �� How to Start Phase 3

### Local Testing

```bash
# 1. Activate virtual environment
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# 2. Make sure .env has EXOTEL_TEST_MODE=phase3

# 3. Start the server
python3 -m src.main
```

**You should see:**
```
INFO - 🤖 WebSocket server initialized in PHASE 3 MODE (Deepgram STT + OpenAI LLM)
INFO - Application startup complete
```

### Railway Deployment

If deployed on Railway:

1. **Set environment variable** in Railway dashboard:
   ```
   EXOTEL_TEST_MODE=phase3
   ```

2. **Redeploy** to apply changes

3. **Verify** by visiting: `https://your-app.railway.app/`
   - Should show: "🤖 Phase 3: Full AI conversation..."

---

## 📞 Testing the Conversation Flow

### Test Scenario: Real Estate Qualification Call

When you call the WebSocket endpoint, here's what happens:

#### 1. **Call Starts**
- You hear a greeting beep (440Hz tone)
- AI generates intro message (logged, not spoken yet):
  ```
  "Hi Test Customer, this is Alex from PropertyHub. Hope I'm not catching you
  at a bad time? I saw you were looking at 2BHK apartment in Whitefield,
  Bangalore. Got a couple minutes to chat?"
  ```

#### 2. **Customer Speaks: "Hello, who is this?"**
- ✅ Deepgram transcribes your speech
- ✅ OpenAI generates contextual response:
  ```
  "Hi! This is Alex from PropertyHub. I'm calling about the 2BHK apartments
  you were interested in. Do you have a quick minute?"
  ```
- 🔊 You hear acknowledgment beep (880Hz)

#### 3. **Customer: "Yes, what's the price?"**
- ✅ AI understands intent (asking about budget)
- ✅ Generates natural response:
  ```
  "Great question! The 2BHK units in Whitefield start at ₹80 lakhs.
  Does that fit your budget range?"
  ```
- 🔊 Beep acknowledgment

#### 4. **Customer: "That's too expensive."**
- ✅ AI detects objection
- ✅ Handles it naturally:
  ```
  "I totally get that. We do have flexible payment plans though, and the
  area's seeing great appreciation. Want me to WhatsApp you the payment options?"
  ```
- 🔊 Beep acknowledgment

#### 5. **Customer: "No thanks, not interested."**
- ✅ AI detects "not interested" intent
- ✅ Decides to end call politely:
  ```
  {
    "should_end_call": true,
    "call_outcome": "not_interested",
    "response_text": "No worries at all! Thanks for your time. Have a great day!"
  }
  ```

---

## 📋 What You'll See in the Logs

### When Call Starts
```
✅ PHASE 3: Media streaming STARTED
   Call SID: CA1234567890
   From: +919876543210
   To: +918012345678
   Session created: CA1234567890
   📢 Ready to have an AI conversation!
   💬 Try saying: 'Hello, who is this?'

════════════════════════════════════════════════════════════════════════════════
🤖 PHASE 3: AI INTRO MESSAGE GENERATED
   Agent would say: 'Hi Test Customer, this is Alex from PropertyHub...'
   (Using beep for now - TTS will be added in Phase 4)
════════════════════════════════════════════════════════════════════════════════
```

### When Customer Speaks
```
🎤 PHASE 3: SPEECH STARTED (RMS=127.45)
🔇 PHASE 3: SPEECH ENDED (silence for 20 chunks)
🎤 PHASE 3: Transcribing 24000 bytes...

════════════════════════════════════════════════════════════════════════════════
✅ PHASE 3: TRANSCRIPTION SUCCESSFUL!
   📝 Customer said: 'Hello, who is this?'
   🔊 Audio size: 24000 bytes
════════════════════════════════════════════════════════════════════════════════

🤖 PHASE 3: Generating AI response with OpenAI...

════════════════════════════════════════════════════════════════════════════════
🤖 PHASE 3: AI RESPONSE GENERATED!
   💬 Agent says: 'Hi! This is Alex from PropertyHub. I'm calling about
                  the 2BHK apartments you were interested in.'
   📊 Should end call: False
   🎯 Call outcome: ongoing
   (Using beep for now - TTS will be added in Phase 4)
════════════════════════════════════════════════════════════════════════════════

✅ PHASE 3: Sent acknowledgment beep (880Hz, 0.2s)
```

### When Call Ends
```
✅ PHASE 3: Call STOPPED
   Call SID: CA1234567890

════════════════════════════════════════════════════════════════════════════════
📋 PHASE 3: FINAL CONVERSATION TRANSCRIPT
   (This shows the full AI conversation that took place)
────────────────────────────────────────────────────────────────────────────────
   🤖 AGENT: Hi Test Customer, this is Alex from PropertyHub...
   👤 CUSTOMER: Hello, who is this?
   🤖 AGENT: Hi! This is Alex from PropertyHub. I'm calling about the 2BHK...
   👤 CUSTOMER: Yes, what's the price?
   🤖 AGENT: Great question! The 2BHK units in Whitefield start at ₹80 lakhs...
   👤 CUSTOMER: That's too expensive.
   🤖 AGENT: I totally get that. We do have flexible payment plans though...
   👤 CUSTOMER: No thanks, not interested.
   🤖 AGENT: No worries at all! Thanks for your time. Have a great day!
════════════════════════════════════════════════════════════════════════════════
```

---

## 🎯 What to Test

### Test Case 1: Interested Customer
```
You: "Hi, I'm interested in the property"
AI: Should acknowledge and ask qualifying questions

You: "I'm looking for a 2BHK, budget around 80 lakhs"
AI: Should confirm interest and move toward scheduling visit

You: "Yes, I'd like to visit this weekend"
AI: Should offer to schedule site visit
```

### Test Case 2: Objection Handling
```
You: "The location is too far from my office"
AI: Should handle objection (mention metro connectivity, etc.)

You: "I need to discuss with my family first"
AI: Should offer to send details via WhatsApp

You: "I'm just browsing for now"
AI: Should stay friendly, not pushy
```

### Test Case 3: Not Interested
```
You: "Not interested, please don't call again"
AI: Should politely end the call
   - should_end_call: true
   - call_outcome: "not_interested"
```

---

## 🔍 Verifying Phase 3 Works

### ✅ Success Indicators

1. **Server starts with Phase 3 mode:**
   ```
   🤖 WebSocket server initialized in PHASE 3 MODE
   ```

2. **Transcriptions appear in logs:**
   ```
   📝 Customer said: 'your spoken text'
   ```

3. **AI responses are generated:**
   ```
   🤖 PHASE 3: AI RESPONSE GENERATED!
   💬 Agent says: 'intelligent response here'
   ```

4. **Full conversation transcript at end:**
   ```
   📋 PHASE 3: FINAL CONVERSATION TRANSCRIPT
   ```

### ❌ Troubleshooting

**Problem:** "OPENAI_API_KEY not configured"
- **Solution:** Add your OpenAI API key to `.env`

**Problem:** AI responses are generic/repetitive
- **Solution:** This is normal - OpenAI is following the prompt template
- Check [prompt_templates.py](src/conversation/prompt_templates.py:26-70) for customization

**Problem:** Conversation doesn't make sense
- **Solution:** Check if transcript history is being maintained
- Look for: `conversation_history=session.transcript`

---

## 📊 Phase 3 Architecture

```
┌─────────────────────┐
│   Phone Call        │
│   (You speak)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Exotel            │
│   (WebSocket)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Railway Server    │
│   Phase 3 Handler   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Voice Activity    │
│   Detection (VAD)   │
│   RMS > 50          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Deepgram STT      │  ← Converts speech to text
│   "Hello there"     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Conversation       │  ← NEW IN PHASE 3!
│  Engine             │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  OpenAI GPT-4o-mini │  ← Generates intelligent response
│  + System Prompt    │
│  + Conversation     │
│    History          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  AI Response        │
│  {                  │
│    intent: "...",   │
│    response: "Hi!   │
│      This is Alex   │
│      from...",      │
│    should_end: false│
│  }                  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Log Response       │  ← Logged to console
│  + Add to           │     (Phase 4 will speak it)
│    Transcript       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Send Beep          │  🔊 Acknowledgment
│  (880Hz, 0.2s)      │
└─────────────────────┘
```

---

## 🎓 Understanding the Code

### Key Files for Phase 3

| File | Purpose |
|------|---------|
| [phase3_event_handlers.py](src/websocket/phase3_event_handlers.py) | Main Phase 3 logic |
| [engine.py](src/conversation/engine.py:36-111) | Conversation orchestration |
| [llm_service.py](src/ai/llm_service.py:55-165) | OpenAI API integration |
| [prompt_templates.py](src/conversation/prompt_templates.py:11-70) | System prompts for AI |
| [server.py](src/websocket/server.py:39-49) | WebSocket mode selection |

### How AI Response Generation Works

```python
# 1. Customer speech is transcribed
transcription = await stt_service.transcribe_audio(audio_bytes)

# 2. Conversation engine processes it
response_text, should_end_call, outcome = await conversation_engine.process_user_input(
    session=conversation_session,
    user_input=transcription
)

# 3. LLM service generates response
llm_result = await llm_service.generate_streaming_response(
    user_input=transcription,
    conversation_history=session.transcript,
    lead_context={...},
    system_prompt=get_real_estate_system_prompt()
)

# 4. Response is logged and transcript updated
await session_manager.add_to_transcript(
    call_sid=call_sid,
    speaker="agent",
    text=response_text
)
```

---

## 🚀 Next Steps: Phase 4

Phase 3 gives your bot **intelligence**, but it still uses beeps for acknowledgment.

**Phase 4 will add:**
- ✨ Natural voice responses using ElevenLabs TTS
- 🔊 Bot actually speaks the AI-generated responses
- 🎙️ Realistic human-like voice
- 🇮🇳 Indian English accent options

After Phase 4, you'll have a **fully conversational AI voice agent**!

---

## 📝 Summary: Phase 3 vs Phase 2

| Feature | Phase 2 | Phase 3 |
|---------|---------|---------|
| WebSocket Connectivity | ✅ | ✅ |
| Voice Activity Detection | ✅ | ✅ |
| Deepgram STT | ✅ | ✅ |
| OpenAI Conversation | ❌ | ✅ NEW! |
| Context-Aware Responses | ❌ | ✅ NEW! |
| Intent Detection | ❌ | ✅ NEW! |
| Objection Handling | ❌ | ✅ NEW! |
| Call Flow Management | ❌ | ✅ NEW! |
| Natural Voice (TTS) | ❌ | ❌ (Phase 4) |

---

## 💡 Tips for Testing

1. **Speak clearly** - Deepgram works best with clear audio
2. **Pause between sentences** - VAD needs silence to detect end of speech
3. **Watch the logs** - All transcriptions and AI responses are logged
4. **Try different scenarios** - Test interested, objections, not interested
5. **Check conversation history** - Each response uses context from previous exchanges

---

## 🎉 Congratulations!

You now have an **intelligent AI voice agent** that:
- ✅ Understands customer speech
- ✅ Has contextual conversations
- ✅ Handles objections naturally
- ✅ Qualifies real estate leads
- ✅ Decides when to end calls

Next up: **Phase 4** - Adding natural voice responses! 🚀
