# Module 4 Examples

This directory contains practical examples for using Module 4 components.

## Examples

### 1. Custom Conversation Prompt

See how to customize the AI's personality and behavior:

```python
from src.conversation.prompt_templates import get_real_estate_system_prompt

# Customize the AI's personality
custom_prompt = get_real_estate_system_prompt(
    lead_context={
        "lead_name": "John",
        "property_type": "3BHK",
        "location": "Mumbai",
        "budget": 10000000
    },
    current_stage="presentation"
)

print(custom_prompt)
```

### 2. Process User Input

```python
from src.conversation.engine import ConversationEngine
from src.models.conversation import ConversationSession

async def process_conversation():
    engine = ConversationEngine()

    session = ConversationSession(
        call_sid="example_001",
        lead_id=1,
        lead_name="Priya Sharma",
        lead_phone="+919876543210",
        property_type="2BHK",
        location="Bangalore",
        budget=6000000.0
    )

    # Generate intro
    intro = await engine.generate_intro(session)
    print(f"AI: {intro}")

    # Process user response
    user_input = "Yes, I have time to talk"
    response, should_end, outcome = await engine.process_user_input(
        session, user_input
    )

    print(f"User: {user_input}")
    print(f"AI: {response}")
    print(f"Stage: {session.conversation_stage}")
```

### 3. Manual Audio Processing

```python
from src.audio.processor import AudioProcessor
import base64

# Encode audio for Exotel
audio_data = b"raw PCM audio bytes here..."
encoded = AudioProcessor.encode_for_exotel(audio_data)

# Send via WebSocket
websocket.send_json({
    "event": "media",
    "media": {"payload": encoded}
})

# Decode received audio
received_encoded = "base64_audio_here..."
decoded = AudioProcessor.decode_exotel_audio(received_encoded)
```

### 4. Session Management

```python
from src.websocket.session_manager import SessionManager

async def manage_session():
    manager = SessionManager()

    # Create session
    session = await manager.create_session(
        "call_123",
        {
            "lead_id": 1,
            "lead_name": "Test",
            "phone": "+919876543210"
        }
    )

    # Update session
    await manager.update_session(
        "call_123",
        {"is_bot_speaking": True}
    )

    # Add to transcript
    await manager.add_to_transcript(
        "call_123",
        "ai",
        "Hello, how are you?"
    )

    # Retrieve session
    session = await manager.get_session("call_123")
    print(session.transcript_history)

    # Cleanup
    await manager.delete_session("call_123")
```

### 5. Custom Objection Handler

```python
from src.conversation.prompt_templates import get_objection_response_template

# Add custom objection type
def get_custom_objection_response(objection_type: str) -> str:
    custom_templates = {
        "already_bought": "I understand you've already made a purchase. Would you be interested in investment properties for future growth?",

        "wrong_location": "I appreciate that. We actually have projects across multiple locations. What area would you prefer?",

        "need_loan": "No problem at all! We work with multiple banks and can help you get the best loan rates. Would you like me to connect you with our loan advisor?",
    }

    return custom_templates.get(
        objection_type,
        get_objection_response_template(objection_type)  # Fallback
    )

# Use it
response = get_custom_objection_response("need_loan")
print(response)
```

### 6. Analyze Sentiment

```python
from src.ai.llm_service import LLMService

async def analyze_sentiment():
    llm = LLMService()

    user_input = "The price seems too high for me"

    analysis = await llm.analyze_input(
        user_input=user_input,
        context={"stage": "presentation"}
    )

    print(f"Sentiment: {analysis['sentiment']}")
    print(f"Is Objection: {analysis['is_objection']}")
    print(f"Objection Type: {analysis['objection_type']}")
```

### 7. Generate TTS Audio

```python
from src.ai.tts_service import ElevenLabsTTSService

async def generate_audio():
    tts = ElevenLabsTTSService()

    text = "Hello! I'm calling from PropertyHub."
    audio_bytes = await tts.generate_speech(text, "call_123")

    # Save to file (for testing)
    with open("test_audio.pcm", "wb") as f:
        f.write(audio_bytes)

    print(f"Generated {len(audio_bytes)} bytes")
```

### 8. Custom State Machine

```python
from src.conversation.state_machine import ConversationStateMachine
from src.models.conversation import ConversationStage

# Extend the state machine
class CustomStateMachine(ConversationStateMachine):
    def __init__(self):
        super().__init__()

        # Add custom stage
        self.transitions[ConversationStage.PRESENTATION].append(
            "site_visit_scheduled"  # Custom stage
        )

    def determine_next_stage(self, current_stage, analysis, collected_data):
        # Custom logic
        if "visit" in analysis.get("extracted_info", {}).get("response", "").lower():
            return "site_visit_scheduled"

        # Fall back to default logic
        return super().determine_next_stage(current_stage, analysis, collected_data)
```

### 9. WebSocket Client Integration

```python
import asyncio
import websockets
import json

async def call_with_websocket():
    uri = "wss://your-domain.com/media"

    async with websockets.connect(uri) as ws:
        # Send connected event
        await ws.send(json.dumps({
            "event": "connected",
            "call_sid": "custom_call_123",
            "customField": json.dumps({
                "lead_id": 1,
                "lead_name": "Custom Lead",
                "phone": "+919876543210",
                "property_type": "2BHK",
                "location": "Delhi",
                "budget": 7000000
            })
        }))

        # Send start
        await ws.send(json.dumps({
            "event": "start",
            "call_sid": "custom_call_123"
        }))

        # Receive intro
        while True:
            message = await ws.recv()
            data = json.loads(message)

            if data.get("event") == "media":
                print("Received audio chunk")
                # Process audio...
                break

asyncio.run(call_with_websocket())
```

### 10. Monitor Active Sessions

```python
from src.websocket.session_manager import SessionManager
from src.database.connection import redis_client

async def monitor_sessions():
    manager = SessionManager()

    # Get all active sessions
    active = await manager.get_all_active_sessions()
    print(f"Active sessions: {len(active)}")

    # Get details for each
    for call_sid in active:
        session = await manager.get_session(call_sid)
        print(f"\nCall: {call_sid}")
        print(f"  Lead: {session.lead_name}")
        print(f"  Stage: {session.conversation_stage}")
        print(f"  Speaking: {session.is_bot_speaking}")
        print(f"  Exchanges: {len(session.transcript_history)}")

asyncio.run(monitor_sessions())
```

## Running Examples

Each example can be run directly:

```bash
# Copy example to a script
cat examples/README.md | grep -A 20 "Example 2" > test_example.py

# Run it
python test_example.py
```

Or use them in your own code by importing the modules.

## More Resources

- **Full Documentation**: [MODULE4_README.md](../MODULE4_README.md)
- **Quick Start**: [QUICKSTART_MODULE4.md](../QUICKSTART_MODULE4.md)
- **Test Scripts**: [scripts/](../scripts/)
