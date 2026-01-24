# Module 4: WebSocket Server & AI Conversation Engine

## Overview

Module 4 implements the real-time AI conversation engine that powers voice interactions with leads. When Exotel initiates a call, it connects to our WebSocket endpoint, streaming audio in real-time. Our system:

1. Receives audio chunks from Exotel
2. Transcribes speech to text (Deepgram)
3. Analyzes intent and sentiment (GPT-4o-mini)
4. Generates intelligent responses (GPT-4o-mini)
5. Converts responses to speech (ElevenLabs)
6. Streams audio back to the caller

## Architecture

```
┌─────────────┐
│   Exotel    │
│  (Caller)   │
└──────┬──────┘
       │ WebSocket
       │ (Audio Stream)
       ▼
┌─────────────────────────────────────┐
│     WebSocket Server                │
│  /media endpoint                    │
└──────┬──────────────────────────────┘
       │
       ▼
┌──────────────────┐
│  Event Handler   │
│  • connected     │
│  • start         │
│  • media         │
│  • stop          │
└────┬─────────────┘
     │
     ├──► Audio Processor (decode/encode)
     │
     ├──► Session Manager (Redis)
     │
     └──► Conversation Engine
           │
           ├──► Deepgram STT
           ├──► GPT-4o-mini LLM
           ├──► ElevenLabs TTS
           └──► State Machine
```

## Components

### 1. Audio Processing (`src/audio/`)

#### `processor.py`
- Base64 encoding/decoding for Exotel audio format
- Audio chunking for streaming (100ms chunks)
- Duration calculation

#### `converter.py`
- Format conversion (MP3 → PCM 8kHz)
- Uses pydub and ffmpeg
- Converts ElevenLabs output to Exotel format

### 2. AI Services (`src/ai/`)

#### `stt_service.py` - Deepgram Speech-to-Text
- Transcribes caller audio to text
- Supports Indian English (en-IN)
- Voice Activity Detection
- Nova-2 model for accuracy

#### `tts_service.py` - ElevenLabs Text-to-Speech
- Converts AI responses to natural speech
- Customizable voice settings
- Multilingual support
- High-quality audio output

#### `llm_service.py` - GPT-4o-mini LLM
- Generates contextual responses
- Analyzes user intent and sentiment
- Detects objections and buying signals
- Extracts information (budget, timeline, etc.)

### 3. Conversation Logic (`src/conversation/`)

#### `prompt_templates.py`
- System prompts for different stages
- Response templates for objections
- Discovery questions
- Closing templates

#### `state_machine.py`
- Manages conversation stage transitions
- Valid transition rules
- Stage determination logic

Stages:
1. **INTRO** - Initial greeting
2. **PERMISSION** - Get permission to continue
3. **DISCOVERY** - Gather requirements
4. **QUALIFICATION** - Confirm understanding
5. **PRESENTATION** - Present properties
6. **OBJECTION_HANDLING** - Address concerns
7. **TRIAL_CLOSE** - Test readiness
8. **CLOSING** - Schedule site visit
9. **DEAL_CLOSED** - Success!
10. **FOLLOW_UP_SCHEDULED** - Callback requested
11. **DEAD_END** - Not interested

#### `response_generator.py`
- Generates intro messages
- Creates contextual responses
- Uses templates for speed
- Falls back to LLM for complex scenarios

#### `engine.py`
- Main orchestration logic
- Processes user input
- Determines conversation flow
- Decides when to end call

### 4. WebSocket Server (`src/websocket/`)

#### `session_manager.py`
- Manages conversation state in Redis
- Session CRUD operations
- Transcript management
- TTL-based cleanup (1 hour)

#### `event_handlers.py`
- **connected**: Initialize session
- **start**: Send intro message
- **media**: Process audio chunks
- **stop**: Clean up session
- **clear**: Reset conversation
- **dtmf**: Handle keypresses

#### `server.py`
- WebSocket connection management
- Event routing
- Error handling
- Connection tracking

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg libsndfile1
```

**macOS:**
```bash
brew install ffmpeg libsndfile
```

### 3. Configure Environment Variables

Add to your `.env` file:

```env
# AI Service API Keys
DEEPGRAM_API_KEY=your_deepgram_api_key
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=your_voice_id  # Optional, uses default if not set

# WebSocket
WEBSOCKET_ENDPOINT_PATH=/media
```

### 4. Get API Keys

#### Deepgram (Speech-to-Text)
1. Sign up at [deepgram.com](https://deepgram.com)
2. Get API key from dashboard
3. Free tier: 45,000 minutes/month

#### OpenAI (GPT-4o-mini)
1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Create API key
3. Pay-as-you-go pricing

#### ElevenLabs (Text-to-Speech)
1. Sign up at [elevenlabs.io](https://elevenlabs.io)
2. Get API key
3. Optional: Clone a voice or use default
4. Free tier: 10,000 characters/month

## Usage

### Starting the Server

```bash
python -m src.main
```

The WebSocket endpoint will be available at:
```
ws://your-domain.com/media
```

or for ngrok:
```
wss://your-ngrok-url.ngrok.io/media
```

### Testing WebSocket Connection

You can test the WebSocket with a simple client:

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/media"

    async with websockets.connect(uri) as websocket:
        # Send connected event
        await websocket.send(json.dumps({
            "event": "connected",
            "call_sid": "test_call_123",
            "customField": json.dumps({
                "lead_id": 1,
                "lead_name": "Test User",
                "phone": "+919876543210",
                "property_type": "2BHK",
                "location": "Bangalore",
                "budget": 5000000
            })
        }))

        # Receive response
        response = await websocket.recv()
        print(f"Received: {response}")

asyncio.run(test_websocket())
```

### Configuring Exotel

In your Exotel flow, configure the WebSocket URL:

```
wss://your-domain.com/media
```

Pass lead context in the `CustomField` parameter as JSON:

```json
{
  "lead_id": 123,
  "lead_name": "Rajesh Kumar",
  "phone": "+919876543210",
  "property_type": "3BHK",
  "location": "Whitefield, Bangalore",
  "budget": 8000000,
  "source": "Facebook Ads"
}
```

## Conversation Flow Example

```
[Call Connects]

AI: "Hi Rajesh, this is Alex calling from PropertyHub. I hope I'm
     not catching you at a bad time. I saw you were interested in
     3BHK properties in Whitefield around ₹80 lakhs. I actually
     have some options that might be perfect for you. Do you have
     about 2 minutes to chat?"

User: "Yes, sure"

[Stage: INTRO → DISCOVERY]

AI: "Great! Just to understand better - is this for your own use
     or are you looking at it as an investment?"

User: "It's for my family to live in"

AI: "Perfect. And when are you ideally looking to make this purchase?"

User: "Within the next 3 months"

[Stage: DISCOVERY → QUALIFICATION]

AI: "Excellent. So to confirm - you're looking for a 3BHK in
     Whitefield for your family, budget around 80 lakhs, and you
     want to move within 3 months. Did I get that right?"

User: "Yes, exactly"

[Stage: QUALIFICATION → PRESENTATION]

AI: "Wonderful! I have a couple of properties that match perfectly.
     There's a new project by a reputed builder, excellent connectivity
     with the upcoming metro station just 2km away. Would you like to
     schedule a site visit this weekend to check it out?"

User: "I need to discuss with my wife first"

[Stage: PRESENTATION → OBJECTION_HANDLING]

AI: "Absolutely, this is a big decision and it's great that you
     involve your family. How about I WhatsApp you all the property
     details, floor plans, and a virtual tour? That way you'll have
     everything for your discussion. Does that work?"

User: "Yes, that would be helpful"

[Stage: OBJECTION_HANDLING → CLOSING]

AI: "Perfect! I'll send that right away. And once you've had a
     chance to review with your wife, shall I schedule a tentative
     site visit for this Saturday? You can always reschedule."

User: "Sure, Saturday works"

[Stage: CLOSING → DEAL_CLOSED]

AI: "Perfect! I've scheduled your site visit for Saturday. You'll
     receive a WhatsApp with all the details. Looking forward to
     showing you around. Have a great day!"

[Call Ends - Outcome: qualified]
```

## State Management

Sessions are stored in Redis with the following structure:

```python
{
    "call_sid": "CAxxxx",
    "lead_id": 123,
    "lead_name": "Rajesh Kumar",
    "conversation_stage": "presentation",
    "transcript_history": [
        {"speaker": "ai", "text": "Hi Rajesh...", "timestamp": "2024-01-20T10:30:00"},
        {"speaker": "user", "text": "Yes, sure", "timestamp": "2024-01-20T10:30:05"}
    ],
    "collected_data": {
        "purpose": "end_user",
        "timeline": "3_months",
        "budget_confirmed": 8000000
    },
    "objections_encountered": ["family_approval"],
    "close_attempts": 1,
    "is_bot_speaking": false,
    "waiting_for_response": true
}
```

## Monitoring & Debugging

### View Active Sessions

```python
from src.websocket.session_manager import SessionManager

manager = SessionManager()
active_sessions = await manager.get_all_active_sessions()
print(f"Active calls: {len(active_sessions)}")
```

### Check Logs

Structured logging includes:
- WebSocket connection events
- Transcription results
- LLM requests/responses
- TTS generation
- Stage transitions
- Errors and warnings

```bash
tail -f logs/app.log | grep "call_sid=CAxxxx"
```

### Common Issues

**Issue: "Deepgram client not initialized"**
- Solution: Set `DEEPGRAM_API_KEY` in `.env`

**Issue: "ElevenLabs TTS not configured"**
- Solution: Set `ELEVENLABS_API_KEY` in `.env`

**Issue: "Audio conversion failed"**
- Solution: Install ffmpeg (`brew install ffmpeg` or `apt-get install ffmpeg`)

**Issue: "Session not found"**
- Solution: Check Redis is running (`redis-cli ping`)

## Performance Considerations

### Latency Optimization

1. **Audio Chunking**: 100ms chunks for smooth streaming
2. **Template Responses**: Use templates for objections (faster than LLM)
3. **Redis Sessions**: Fast in-memory state management
4. **Async Processing**: All I/O operations are async

### Cost Optimization

- **Deepgram**: ~$0.0125 per minute
- **OpenAI GPT-4o-mini**: ~$0.15 per 1M input tokens
- **ElevenLabs**: ~$0.30 per 1K characters
- **Estimated cost per call**: $0.15-$0.30 (5-minute call)

### Scaling

- **Concurrent Calls**: Limited by `MAX_CONCURRENT_CALLS` setting
- **Redis**: Can handle 10,000+ sessions
- **WebSocket**: FastAPI handles 1000+ concurrent connections
- **Horizontal Scaling**: Deploy multiple instances behind load balancer

## Testing

Run tests:

```bash
# Unit tests
pytest tests/test_module4.py -v

# Integration tests (requires API keys)
pytest tests/test_module4.py -v -m "not skip"

# Specific test
pytest tests/test_module4.py::TestAudioProcessor::test_encode_decode_audio -v
```

## Next Steps

Module 4 is now complete! Next modules will cover:

- **Module 5**: Call Outcome Processing & CRM Updates
- **Module 6**: Analytics & Reporting Dashboard
- **Module 7**: Advanced Features (Call Recording, Sentiment Analysis)

## Support

For issues or questions about Module 4:

1. Check logs for detailed error messages
2. Verify all API keys are configured
3. Ensure Redis is running
4. Test WebSocket connection independently
5. Review conversation transcripts in Redis

## Customization

### Custom Voice Personality

Edit [prompt_templates.py:10-40](src/conversation/prompt_templates.py#L10-L40) to change:
- Agent name
- Personality traits
- Conversation rules
- Response style

### Custom Objection Handling

Add templates in [prompt_templates.py:73-107](src/conversation/prompt_templates.py#L73-L107):

```python
templates = {
    "custom_objection": "Your response template here...",
    # ... existing templates
}
```

### Custom Conversation Stages

Modify [state_machine.py:32-71](src/conversation/state_machine.py#L32-L71) to add stages:

```python
ConversationStage.CUSTOM_STAGE: [
    ConversationStage.NEXT_STAGE,
    ConversationStage.ALTERNATE_STAGE
]
```

## License

Same as main project.
