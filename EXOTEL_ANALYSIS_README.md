# Exotel Integration Analysis - Complete Documentation

This directory contains comprehensive documentation on how Exotel is integrated into the Real Estate Voice AI system.

## Documentation Files

### 1. **EXOTEL_INTEGRATION_ANALYSIS.md** (Main Reference)
**Length:** 767 lines | **Size:** 29 KB

Complete in-depth guide covering:
- Exotel WebSocket endpoint definition and configuration
- How Exotel connects to the WebSocket (full connection flow)
- Complete conversation lifecycle and current flow
- All configuration required
- Audio format specifications and encoding/decoding
- WebSocket message structure with JSON examples
- Status callback webhooks
- Complete configuration checklist
- Troubleshooting guide
- Full file references

**Best for:** Understanding the complete architecture and detailed flow

---

### 2. **EXOTEL_QUICK_REFERENCE.md** (Quick Lookup)
**Length:** 290 lines | **Size:** 7.4 KB

Quick reference guide with:
- File locations
- Configuration variables table
- WebSocket endpoint details
- Step-by-step call flow
- Audio format specifications
- Key classes and their usage
- WebSocket message examples (JSON)
- Status callback information
- Conversation states
- Voice Activity Detection (VAD) explanation
- Barge-in (interruption) support
- Troubleshooting checklist
- Performance notes

**Best for:** Quick lookup during development, troubleshooting

---

### 3. **EXOTEL_ARCHITECTURE_DIAGRAM.txt** (Visual Reference)
**Length:** 606 lines | **Size:** 38 KB

ASCII diagrams and visual representations:
- Complete component diagram (all services and interactions)
- Call flow sequence diagram (0ms to 15000ms with detailed timeline)
- Audio flow diagrams (both incoming and outgoing)
- Data structure in Redis (ConversationSession)
- Environment configuration
- Exotel dashboard configuration requirements

**Best for:** Understanding system architecture visually, presentations

---

## What You'll Learn

### From Analyzing These Files

1. **WebSocket Endpoint**
   - Located at: `/media`
   - Protocol: WebSocket (wss:// for HTTPS)
   - Public URL: `wss://{OUR_BASE_URL}/media`

2. **Connection Flow**
   - REST API call initiates outbound call to customer
   - Exotel's Voicebot Applet opens WebSocket when call is answered
   - Events flow: connected → start → media (loop) → stop

3. **Current Flow**
   - Customer speaks → Audio received → Buffer accumulates
   - Silence detected → Deepgram transcribes → OpenAI LLM processes
   - LLM generates response → ElevenLabs converts to speech → Sends back
   - Loop continues or call ends based on LLM decision

4. **Configuration**
   - 5 Exotel settings needed (SID, API Key, Token, Virtual Number, Exophlo ID)
   - 3 AI services (Deepgram, OpenAI, ElevenLabs)
   - 2 Infrastructure services (PostgreSQL, Redis)
   - Public URL for WebSocket and webhooks

5. **Audio Format**
   - 16-bit Linear PCM, 8000 Hz, Mono
   - Base64 encoded for WebSocket transmission
   - 20ms chunks = 320 bytes each
   - 0.5 seconds minimum + 600ms silence to trigger transcription

## Key Code Files Referenced

| File | Purpose |
|------|---------|
| `src/main.py` (line 166) | WebSocket endpoint definition |
| `src/websocket/server.py` | WebSocket connection handler |
| `src/websocket/event_handlers.py` | Event processing (start, media, stop, etc.) |
| `src/websocket/session_manager.py` | Redis session management |
| `src/integrations/exotel_client.py` | REST API client for call initiation |
| `src/audio/processor.py` | Audio encoding/decoding |
| `src/config/settings.py` | Configuration loading |
| `src/api/webhooks.py` | Status callback webhook handler |

## Quick Start Checklist

### Read in This Order

1. Start with **EXOTEL_QUICK_REFERENCE.md**
   - Get file locations and overview
   - Understand the call flow at high level

2. Then **EXOTEL_ARCHITECTURE_DIAGRAM.txt**
   - Visualize the component interactions
   - Follow the sequence diagram timeline

3. Finally **EXOTEL_INTEGRATION_ANALYSIS.md**
   - Deep dive into specific sections as needed
   - Reference for detailed implementation

### Configuration Setup

- [ ] Get Exotel credentials from dashboard
- [ ] Configure `.env` with all 5 Exotel settings
- [ ] Set `OUR_BASE_URL` to public HTTPS domain
- [ ] Get API keys: Deepgram, OpenAI, ElevenLabs
- [ ] Configure PostgreSQL and Redis URLs
- [ ] Set up Exophlo in Exotel dashboard with correct WebSocket URL
- [ ] Configure status callback webhook

## Common Questions Answered

### Where is the WebSocket endpoint?
See **EXOTEL_INTEGRATION_ANALYSIS.md** Section 1, or **EXOTEL_QUICK_REFERENCE.md** "WebSocket Endpoint"

### How does Exotel connect?
See **EXOTEL_INTEGRATION_ANALYSIS.md** Section 2, or **EXOTEL_ARCHITECTURE_DIAGRAM.txt** "CALL FLOW SEQUENCE DIAGRAM"

### What's the audio format?
See **EXOTEL_QUICK_REFERENCE.md** "Audio Format" (one-page overview)
Or **EXOTEL_INTEGRATION_ANALYSIS.md** Section 5 (detailed with pipeline diagram)

### What configuration do I need?
See **EXOTEL_QUICK_REFERENCE.md** "Configuration Variables" (table format)
Or **EXOTEL_INTEGRATION_ANALYSIS.md** Section 4 (step-by-step guide)

### How do I troubleshoot?
See **EXOTEL_QUICK_REFERENCE.md** "Troubleshooting Checklist"
Or **EXOTEL_INTEGRATION_ANALYSIS.md** Section 10 "Troubleshooting"

### What events can Exotel send?
See **EXOTEL_INTEGRATION_ANALYSIS.md** Section 6 "WebSocket Message Structure"
Or **EXOTEL_QUICK_REFERENCE.md** "WebSocket Message Examples"

## File Organization

```
/Users/prathamkhandelwal/AI Voice Agent/
├── EXOTEL_ANALYSIS_README.md          (This file - Navigation guide)
├── EXOTEL_INTEGRATION_ANALYSIS.md     (Complete guide - 767 lines)
├── EXOTEL_QUICK_REFERENCE.md          (Quick lookup - 290 lines)
├── EXOTEL_ARCHITECTURE_DIAGRAM.txt    (ASCII diagrams - 606 lines)
│
├── src/
│   ├── main.py                        (WebSocket endpoint)
│   ├── integrations/exotel_client.py  (REST API client)
│   ├── websocket/
│   │   ├── server.py                  (WebSocket server)
│   │   ├── event_handlers.py          (Event processing)
│   │   └── session_manager.py         (Redis sessions)
│   ├── audio/processor.py             (Audio codec)
│   ├── ai/
│   │   ├── stt_service.py             (Deepgram STT)
│   │   └── tts_service.py             (ElevenLabs TTS)
│   ├── conversation/engine.py         (LLM logic)
│   ├── config/settings.py             (Configuration)
│   └── api/webhooks.py                (Status callbacks)
│
└── tests/test_exotel.py               (Unit tests)
```

## Statistics

- **Total Documentation:** 1,663 lines
- **Integration Files:** 3 markdown/text files
- **Code Files Referenced:** 12+ source files
- **Configuration Variables:** 8+ Exotel-specific settings
- **WebSocket Events:** 6 types (connected, start, media, stop, clear, dtmf)
- **External APIs:** 4 (Exotel REST, Deepgram, OpenAI, ElevenLabs)

## Related Documentation

Within this project:
- `MODULE4_SETUP.md` - Complete setup guide
- `MODULE4_COMPLETE.md` - Module 4 completion notes
- `.env.example` - Example configuration

External:
- [Exotel Developer Docs](https://developer.exotel.com/api/)
- [Deepgram Documentation](https://developers.deepgram.com/)
- [OpenAI API Docs](https://platform.openai.com/docs/)
- [ElevenLabs Docs](https://elevenlabs.io/docs/)

## Summary

The Exotel integration enables:
1. **Outbound Calling**: REST API to initiate calls to customer numbers
2. **Real-time Audio Streaming**: WebSocket connection for bidirectional audio
3. **Speech Recognition**: Deepgram converts customer audio to text
4. **AI Conversation**: OpenAI LLM generates contextual responses
5. **Text-to-Speech**: ElevenLabs converts responses back to natural speech
6. **Session Management**: Redis stores conversation state during calls
7. **Call Tracking**: PostgreSQL records full call history and outcomes

All components are documented with configuration requirements, flow diagrams, code references, and troubleshooting guides in these documentation files.

---

Generated: 2026-01-24
For questions or updates, refer to the specific section in the appropriate documentation file.
