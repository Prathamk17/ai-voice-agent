# Module 4 Quick Start Guide

Get Module 4 (WebSocket Server & AI Conversation Engine) running in 15 minutes!

## ⚡ Quick Setup (5 minutes)

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install system packages
# macOS:
brew install ffmpeg libsndfile

# Ubuntu:
sudo apt-get install ffmpeg libsndfile1
```

### 2. Get API Keys (Sign up for free)

| Service | URL | Free Tier |
|---------|-----|-----------|
| **Deepgram** | https://deepgram.com | 45,000 min/month |
| **OpenAI** | https://platform.openai.com | Pay-as-you-go |
| **ElevenLabs** | https://elevenlabs.io | 10,000 chars/month |

### 3. Configure Environment

Copy `.env.example` to `.env` and add your keys:

```bash
cp .env.example .env
```

Edit `.env`:
```env
DEEPGRAM_API_KEY=your_deepgram_key_here
OPENAI_API_KEY=sk-your_openai_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
```

## ✅ Verify Installation (2 minutes)

Run the health check:

```bash
python scripts/health_check_module4.py
```

Expected output:
```
✅ Deepgram API Key: Configured
✅ OpenAI API Key: Configured
✅ ElevenLabs API Key: Configured
✅ Audio Encode/Decode: Working correctly
✅ Deepgram Client: Initialized
✅ OpenAI Client: Initialized
✅ ElevenLabs Client: Initialized
✅ Conversation Engine: Initialized
✅ Session Manager: Initialized
✅ WebSocket Server: Initialized

✅ ALL CHECKS PASSED - Module 4 is ready!
```

## 🧪 Test the System (5 minutes)

### Option 1: Quick Demo (No Server Needed)

```bash
# Run conversation demo
python scripts/demo_conversation.py 1

# Interactive mode
python scripts/demo_conversation.py 6
```

### Option 2: Test WebSocket Server

**Terminal 1** - Start server:
```bash
python -m src.main
```

**Terminal 2** - Run test client:
```bash
python scripts/test_websocket_client.py
```

Expected output:
```
🔌 Connecting to ws://localhost:8000/media
📞 Call SID: test_20240120_143025
✅ WebSocket connected
✅ Sent connected event
✅ Sent start event
📩 Received: audio chunk (AI intro)
✅ Test complete
```

## 🌐 Expose to Internet (3 minutes)

For Exotel to connect, you need a public URL:

### Using ngrok (Recommended)

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from ngrok.com

# Start tunnel
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

Update `.env`:
```env
OUR_BASE_URL=https://abc123.ngrok.io
```

Your WebSocket URL:
```
wss://abc123.ngrok.io/media
```

## 🎯 Make a Test Call

### 1. Configure Exotel Flow

In your Exotel dashboard:

1. Go to your Exophlo (call flow)
2. Add "Connect to WebSocket" node
3. URL: `wss://your-ngrok-url.ngrok.io/media`
4. Custom Field:
   ```json
   {
     "lead_id": 123,
     "lead_name": "Test User",
     "phone": "+919876543210",
     "property_type": "2BHK",
     "location": "Bangalore",
     "budget": 5000000
   }
   ```

### 2. Create Test Lead & Campaign

```bash
# Start server if not running
python -m src.main
```

Then create a campaign via API or UI and make a call!

### 3. Monitor Logs

```bash
tail -f logs/app.log | grep "WebSocket\|Session\|Transcription"
```

Watch for:
- ✅ WebSocket connection established
- ✅ Session created
- ✅ Intro generated
- ✅ User speech transcribed
- ✅ Response generated

## 📊 Common Commands

### Run Tests
```bash
# All tests
pytest tests/test_module4.py -v

# Specific test
pytest tests/test_module4.py::TestAudioProcessor -v
```

### Check Active Sessions
```bash
redis-cli KEYS "session:*"
```

### View Session Data
```bash
redis-cli GET "session:CAxxxx"
```

### Health Check
```bash
python scripts/health_check_module4.py
```

### Demo Conversations
```bash
# All demos
python scripts/demo_conversation.py all

# Specific demo
python scripts/demo_conversation.py 1  # Successful flow
python scripts/demo_conversation.py 2  # Objection handling
python scripts/demo_conversation.py 6  # Interactive mode
```

### Test WebSocket
```bash
# Quick test
python scripts/test_websocket_client.py

# Interactive mode
python scripts/test_websocket_client.py interactive
```

## 🐛 Troubleshooting

### "Deepgram client not initialized"
```bash
# Check if key is set
echo $DEEPGRAM_API_KEY

# If empty, add to .env:
DEEPGRAM_API_KEY=your_key_here
```

### "Audio conversion failed"
```bash
# Check ffmpeg is installed
ffmpeg -version

# If not installed:
brew install ffmpeg  # macOS
sudo apt install ffmpeg  # Ubuntu
```

### "Session not found"
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# If not running:
redis-server
```

### WebSocket connection fails
```bash
# Check server is running
curl http://localhost:8000/health

# Check WebSocket endpoint
wscat -c ws://localhost:8000/media
# (Install wscat: npm install -g wscat)
```

## 💡 Pro Tips

### Reduce Costs
- Use template responses for common objections (faster + cheaper)
- Keep prompts concise
- Set `max_tokens=150` for voice responses

### Improve Latency
- Use templates instead of LLM when possible
- Optimize prompt lengths
- Consider caching common responses

### Better Conversations
- Review transcripts regularly
- Tune prompts based on outcomes
- A/B test different approaches
- Collect feedback from sales team

## 📚 Next Steps

1. **Test with Real Calls**: Make 5-10 test calls
2. **Review Transcripts**: Check conversation quality
3. **Tune Prompts**: Adjust AI personality
4. **Monitor Costs**: Watch API usage
5. **Optimize Flow**: Improve conversation stages
6. **Deploy to Production**: Follow [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

## 🔗 Resources

- **Full Documentation**: [MODULE4_README.md](MODULE4_README.md)
- **Setup Guide**: [MODULE4_SETUP.md](MODULE4_SETUP.md)
- **Deployment**: [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- **Summary**: [MODULE4_SUMMARY.md](MODULE4_SUMMARY.md)

## 🆘 Getting Help

### Check Logs
```bash
tail -f logs/app.log
```

### Run Health Check
```bash
python scripts/health_check_module4.py
```

### Test Components Individually
```bash
# Test audio
python -c "from src.audio.processor import AudioProcessor; print('✅ Audio OK')"

# Test STT
python -c "from src.ai.stt_service import DeepgramSTTService; print('✅ STT OK')"

# Test TTS
python -c "from src.ai.tts_service import ElevenLabsTTSService; print('✅ TTS OK')"

# Test LLM
python -c "from src.ai.llm_service import LLMService; print('✅ LLM OK')"
```

## ⚙️ Configuration Reference

### Minimum Requirements
- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- 2GB RAM
- ffmpeg

### Environment Variables
```env
# Database
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379

# AI Services
DEEPGRAM_API_KEY=...
OPENAI_API_KEY=...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...  # Optional

# Server
OUR_BASE_URL=https://your-domain.com

# WebSocket
WEBSOCKET_ENDPOINT_PATH=/media
```

### Cost Estimates
- ~$0.26 per 5-minute call
  - Deepgram: $0.06
  - OpenAI: $0.05
  - ElevenLabs: $0.15

---

**You're all set! 🎉**

Module 4 is now ready to power intelligent voice conversations with your leads.

Happy building! 🚀
