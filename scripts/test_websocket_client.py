"""
WebSocket Test Client for Module 4

Simulates an Exotel WebSocket connection to test the conversation engine.
Useful for testing without making actual phone calls.
"""

import asyncio
import websockets
import json
import base64
from datetime import datetime


class WebSocketTestClient:
    """Test client for WebSocket conversations"""

    def __init__(self, url: str = "ws://localhost:8000/media"):
        self.url = url
        self.call_sid = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    async def simulate_call(
        self,
        lead_name: str = "Test User",
        property_type: str = "2BHK",
        location: str = "Bangalore",
        budget: int = 5000000
    ):
        """
        Simulate a complete call conversation

        Args:
            lead_name: Lead's name
            property_type: Property type
            location: Location
            budget: Budget in rupees
        """
        print(f"🔌 Connecting to {self.url}")
        print(f"📞 Call SID: {self.call_sid}")
        print("-" * 60)

        async with websockets.connect(self.url) as websocket:
            print("✅ WebSocket connected")

            # 1. Send connected event
            await self.send_connected(websocket, lead_name, property_type, location, budget)

            # 2. Send start event
            await self.send_start(websocket)

            # 3. Wait for intro audio
            await self.receive_messages(websocket, count=5)

            # 4. Simulate user responses
            print("\n📝 Simulating user responses...")

            # Response 1: Positive
            await self.send_text_as_audio(websocket, "Yes, I have time to talk")
            await self.receive_messages(websocket, count=3)

            # Response 2: Answer discovery question
            await self.send_text_as_audio(websocket, "It's for my family to live in")
            await self.receive_messages(websocket, count=3)

            # Response 3: Timeline
            await self.send_text_as_audio(websocket, "Within the next 3 months")
            await self.receive_messages(websocket, count=3)

            # Response 4: Interest
            await self.send_text_as_audio(websocket, "Yes, I'd like to see the property")
            await self.receive_messages(websocket, count=3)

            # 5. Send stop event
            await self.send_stop(websocket)

            print("\n✅ Call simulation complete")

    async def send_connected(
        self,
        websocket,
        lead_name: str,
        property_type: str,
        location: str,
        budget: int
    ):
        """Send connected event"""
        message = {
            "event": "connected",
            "call_sid": self.call_sid,
            "CallSid": self.call_sid,
            "customField": json.dumps({
                "lead_id": 999,
                "lead_name": lead_name,
                "phone": "+919876543210",
                "property_type": property_type,
                "location": location,
                "budget": budget,
                "source": "test"
            })
        }

        await websocket.send(json.dumps(message))
        print(f"📤 Sent: connected event")

    async def send_start(self, websocket):
        """Send start event"""
        message = {
            "event": "start",
            "call_sid": self.call_sid
        }

        await websocket.send(json.dumps(message))
        print(f"📤 Sent: start event")

    async def send_stop(self, websocket):
        """Send stop event"""
        message = {
            "event": "stop",
            "call_sid": self.call_sid
        }

        await websocket.send(json.dumps(message))
        print(f"📤 Sent: stop event")

    async def send_text_as_audio(self, websocket, text: str):
        """
        Simulate sending audio by sending text directly
        (In real scenario, this would be actual audio)

        Args:
            websocket: WebSocket connection
            text: Text to simulate as speech
        """
        # Create dummy audio data (in real scenario, this would be actual PCM audio)
        dummy_audio = text.encode('utf-8')
        base64_audio = base64.b64encode(dummy_audio).decode('utf-8')

        message = {
            "event": "media",
            "call_sid": self.call_sid,
            "media": {
                "payload": base64_audio
            }
        }

        await websocket.send(json.dumps(message))
        print(f"\n👤 User said: '{text}'")

    async def receive_messages(self, websocket, count: int = 1):
        """
        Receive and display messages from server

        Args:
            websocket: WebSocket connection
            count: Number of messages to receive
        """
        for _ in range(count):
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3)
                data = json.loads(response)

                event = data.get("event", "unknown")
                if event == "media":
                    print(f"📥 Received: audio chunk")
                else:
                    print(f"📥 Received: {event}")

            except asyncio.TimeoutError:
                break
            except Exception as e:
                print(f"❌ Error receiving: {e}")
                break


async def interactive_mode():
    """
    Interactive mode for manual testing

    Allows you to type responses and see AI reactions in real-time
    """
    client = WebSocketTestClient()

    print("🎤 Interactive WebSocket Test Mode")
    print("=" * 60)

    lead_name = input("Lead name (default: Test User): ") or "Test User"
    property_type = input("Property type (default: 2BHK): ") or "2BHK"
    location = input("Location (default: Bangalore): ") or "Bangalore"
    budget = input("Budget (default: 5000000): ") or "5000000"

    print("\n🔌 Connecting to WebSocket...")
    print(f"📞 Call SID: {client.call_sid}")
    print("-" * 60)

    async with websockets.connect(client.url) as websocket:
        print("✅ Connected!")

        # Send connected event
        await client.send_connected(
            websocket,
            lead_name,
            property_type,
            location,
            int(budget)
        )

        # Send start event
        await client.send_start(websocket)

        # Wait for intro
        print("\n⏳ Waiting for AI intro...")
        await client.receive_messages(websocket, count=5)

        # Interactive loop
        print("\n💬 Type your responses (or 'quit' to exit):")
        while True:
            try:
                user_input = input("\n👤 You: ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    await client.send_stop(websocket)
                    break

                if user_input:
                    await client.send_text_as_audio(websocket, user_input)
                    print("\n⏳ AI is responding...")
                    await client.receive_messages(websocket, count=3)

            except KeyboardInterrupt:
                print("\n\n👋 Exiting...")
                await client.send_stop(websocket)
                break


async def quick_test():
    """Quick automated test"""
    client = WebSocketTestClient()

    print("🚀 Quick WebSocket Test")
    print("=" * 60)

    await client.simulate_call(
        lead_name="Rajesh Kumar",
        property_type="3BHK",
        location="Whitefield, Bangalore",
        budget=8000000
    )


if __name__ == "__main__":
    import sys

    print("""
╔════════════════════════════════════════════════════════════╗
║           WebSocket Test Client for Module 4              ║
║                                                            ║
║  Tests the AI conversation engine without making calls    ║
╚════════════════════════════════════════════════════════════╝
    """)

    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        print("Mode: Interactive\n")
        asyncio.run(interactive_mode())
    else:
        print("Mode: Quick Test")
        print("(Use 'python test_websocket_client.py interactive' for interactive mode)\n")
        asyncio.run(quick_test())
