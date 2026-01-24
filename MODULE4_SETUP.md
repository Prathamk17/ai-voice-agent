# Module 4 Setup Guide

Quick setup guide for getting Module 4 (WebSocket Server & AI Conversation Engine) running.

## Prerequisites

- ✅ Module 1 (Infrastructure) completed
- ✅ Module 2 (Campaign Management) completed
- ✅ Module 3 (Exotel Integration) completed
- ✅ PostgreSQL running
- ✅ Redis running

## Step 1: Install Dependencies

### Python Packages

```bash
pip install -r requirements.txt
```

This will install:
- `python-socketio` - WebSocket support
- `pydub`, `scipy`, `numpy` - Audio processing
- `deepgram-sdk` - Speech-to-Text
- `elevenlabs` - Text-to-Speech
- `openai` - GPT-4o-mini LLM

### System Packages

**macOS:**
```bash
brew install ffmpeg libsndfile
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg libsndfile1
```

**Verify installation:**
```bash
ffmpeg -version
```

## Step 2: Get API Keys

### 1. Deepgram (Speech-to-Text)

1. Go to https://deepgram.com
2. Sign up for a free account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key

**Free Tier:** 45,000 minutes/month

### 2. OpenAI (GPT-4o-mini)

1. Go to https://platform.openai.com
2. Sign up / Log in
3. Go to API Keys: https://platform.openai.com/api-keys
4. Create new secret key
5. Copy the key immediately (won't show again)

**Pricing:** ~$0.15 per 1M input tokens, $0.60 per 1M output tokens

### 3. ElevenLabs (Text-to-Speech)

1. Go to https://elevenlabs.io
2. Sign up for a free account
3. Go to Profile → API Keys
4. Copy your API key
5. (Optional) Go to Voice Library to get a voice ID

**Free Tier:** 10,000 characters/month
**Paid:** Starts at $5/month for 30,000 characters

**Getting Voice ID:**
- Use default voice (no ID needed), or
- Clone your own voice:
  1. Go to Voice Lab
  2. Click "Add Voice"
  3. Upload 1-minute audio sample
  4. Copy the generated Voice ID

## Step 3: Configure Environment Variables

Update your `.env` file:

```env
# Existing variables...
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/voiceai
REDIS_URL=redis://localhost:6379
EXOTEL_ACCOUNT_SID=your_account_sid
EXOTEL_API_KEY=your_api_key
EXOTEL_API_TOKEN=your_api_token
EXOTEL_VIRTUAL_NUMBER=your_virtual_number
EXOTEL_EXOPHLO_ID=your_exophlo_id

# NEW: Module 4 - AI Services
DEEPGRAM_API_KEY=your_deepgram_api_key_here
OPENAI_API_KEY=sk-your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here  # Optional

# WebSocket Configuration
WEBSOCKET_ENDPOINT_PATH=/media
OUR_BASE_URL=https://your-ngrok-url.ngrok.io  # Your public URL
```

## Step 4: Test Individual Components

### Test Audio Processing

```python
python -c "
from src.audio.processor import AudioProcessor
import base64

# Test encoding/decoding
audio = b'test audio data'
encoded = AudioProcessor.encode_for_exotel(audio)
decoded = AudioProcessor.decode_exotel_audio(encoded)
assert decoded == audio
print('✅ Audio processing works!')
"
```

### Test Deepgram STT

```python
python -c "
import asyncio
from src.ai.stt_service import DeepgramSTTService

async def test():
    stt = DeepgramSTTService()
    # Note: This will fail without actual audio, but tests initialization
    print('✅ Deepgram STT initialized!')

asyncio.run(test())
"
```

### Test OpenAI LLM

```python
python -c "
import asyncio
from src.ai.llm_service import LLMService

async def test():
    llm = LLMService()
    response = await llm.generate_response(
        user_input='Hello',
        conversation_history=[],
        lead_context={'lead_name': 'Test'},
        current_stage='intro',
        system_prompt='You are a helpful assistant.'
    )
    print(f'✅ OpenAI LLM works! Response: {response[:50]}...')

asyncio.run(test())
"
```

### Test ElevenLabs TTS

```python
python -c "
import asyncio
from src.ai.tts_service import ElevenLabsTTSService

async def test():
    tts = ElevenLabsTTSService()
    audio = await tts.generate_speech('Hello world', 'test_call')
    print(f'✅ ElevenLabs TTS works! Generated {len(audio)} bytes')

asyncio.run(test())
"
```

### Test Conversation Engine

```python
python -c "
import asyncio
from src.conversation.engine import ConversationEngine
from src.models.conversation import ConversationSession

async def test():
    engine = ConversationEngine()
    session = ConversationSession(
        call_sid='test',
        lead_id=1,
        lead_name='Test User',
        lead_phone='+919876543210'
    )
    intro = await engine.generate_intro(session)
    print(f'✅ Conversation engine works!')
    print(f'   Intro: {intro[:100]}...')

asyncio.run(test())
"
```

## Step 5: Start the Server

```bash
python -m src.main
```

You should see:
```
INFO:     Starting application
INFO:     Database initialized successfully
INFO:     Redis initialized successfully
INFO:     Campaign scheduler started
INFO:     Campaign worker started
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 6: Expose WebSocket Endpoint

### Using ngrok

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from ngrok.com

# Start ngrok tunnel
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

Update `.env`:
```env
OUR_BASE_URL=https://abc123.ngrok.io
```

Your WebSocket URL is:
```
wss://abc123.ngrok.io/media
```

## Step 7: Test WebSocket Connection

Create a test file `test_websocket.py`:

```python
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8000/media"

    async with websockets.connect(uri) as ws:
        print("✅ Connected to WebSocket")

        # Send connected event
        await ws.send(json.dumps({
            "event": "connected",
            "call_sid": "test_123",
            "customField": json.dumps({
                "lead_id": 1,
                "lead_name": "Test User",
                "phone": "+919876543210",
                "property_type": "2BHK",
                "location": "Bangalore",
                "budget": 5000000
            })
        }))

        print("✅ Sent connected event")

        # Send start event
        await ws.send(json.dumps({
            "event": "start",
            "call_sid": "test_123"
        }))

        print("✅ Sent start event")

        # Receive responses (intro message)
        try:
            while True:
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(response)
                print(f"📩 Received: {data.get('event', 'unknown')}")
        except asyncio.TimeoutError:
            print("✅ Test complete")

asyncio.run(test())
```

Run:
```bash
python test_websocket.py
```

## Step 8: Configure Exotel

In your Exotel dashboard:

1. Go to your Exophlo (flow)
2. Add "Connect to WebSocket" node
3. Set URL: `wss://your-ngrok-url.ngrok.io/media`
4. Set Custom Field:
   ```json
   {
     "lead_id": {{lead.id}},
     "lead_name": "{{lead.name}}",
     "phone": "{{lead.phone}}",
     "property_type": "{{lead.property_type}}",
     "location": "{{lead.location}}",
     "budget": {{lead.budget}}
   }
   ```

## Step 9: Make a Test Call

1. Create a test lead in your database
2. Create a campaign
3. Schedule a call
4. Monitor logs:

```bash
tail -f logs/app.log
```

Watch for:
- ✅ WebSocket connection established
- ✅ Session created
- ✅ Intro message generated
- ✅ TTS audio sent
- ✅ User speech transcribed
- ✅ Response generated
- ✅ Stage transitions

## Troubleshooting

### Issue: "Deepgram client not initialized"
**Solution:**
```bash
# Check env variable is set
echo $DEEPGRAM_API_KEY

# If empty, add to .env and restart server
```

### Issue: "Failed to decode audio"
**Solution:**
- Check Exotel audio format is correct (PCM 8kHz 16-bit mono)
- Verify base64 encoding in Exotel

### Issue: "Audio conversion failed"
**Solution:**
```bash
# Verify ffmpeg is installed
ffmpeg -version

# Reinstall if needed
brew reinstall ffmpeg  # macOS
sudo apt-get install --reinstall ffmpeg  # Ubuntu
```

### Issue: "Session not found"
**Solution:**
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# If not running:
redis-server  # or brew services start redis
```

### Issue: WebSocket connection refused
**Solution:**
- Check server is running on port 8000
- Verify firewall allows WebSocket connections
- Test locally first: `ws://localhost:8000/media`
- Then test with ngrok: `wss://your-url.ngrok.io/media`

## Verification Checklist

- [ ] All dependencies installed
- [ ] ffmpeg installed and working
- [ ] All API keys configured in `.env`
- [ ] Server starts without errors
- [ ] WebSocket endpoint accessible
- [ ] Test WebSocket connection works
- [ ] Redis sessions are created
- [ ] Audio encoding/decoding works
- [ ] STT transcribes correctly
- [ ] LLM generates responses
- [ ] TTS generates audio
- [ ] Conversation state transitions properly

## Cost Monitoring

Monitor your API usage:

- **Deepgram**: Dashboard → Usage
- **OpenAI**: Platform → Usage
- **ElevenLabs**: Profile → Usage

Set up billing alerts to avoid surprises!

## Next Steps

Once Module 4 is working:

1. Test with real calls
2. Review conversation transcripts
3. Tune prompts for better responses
4. Adjust conversation flow if needed
5. Move to Module 5 (Call Outcome Processing)

## Support

If you encounter issues:

1. Check logs: `tail -f logs/app.log`
2. Test components individually (Step 4)
3. Verify API keys are correct
4. Check Redis is running
5. Review error messages in detail

Happy building! 🚀
