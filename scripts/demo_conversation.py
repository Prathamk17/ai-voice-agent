"""
Conversation Demo Script

Demonstrates the conversation engine capabilities without WebSocket.
Shows how the AI responds to different scenarios and objections.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.conversation.engine import ConversationEngine
from src.models.conversation import ConversationSession, ConversationStage
from src.conversation.prompt_templates import (
    get_intro_template,
    get_objection_response_template
)


async def demo_successful_conversation():
    """Demo a successful conversation flow"""
    print("\n" + "=" * 70)
    print("📞 DEMO: Successful Conversation Flow")
    print("=" * 70)

    engine = ConversationEngine()

    # Create session
    session = ConversationSession(
        call_sid="demo_success",
        lead_id=1,
        lead_name="Rajesh Kumar",
        lead_phone="+919876543210",
        property_type="3BHK Apartment",
        location="Whitefield, Bangalore",
        budget=8000000.0
    )

    print(f"\n👤 Lead: {session.lead_name}")
    print(f"🏠 Looking for: {session.property_type} in {session.location}")
    print(f"💰 Budget: ₹{session.budget/100000:.0f} lakhs")
    print("\n" + "-" * 70)

    # Generate intro
    intro = await engine.generate_intro(session)
    print(f"\n🤖 AI ({session.conversation_stage}): {intro}")

    # Simulate conversation flow
    exchanges = [
        ("Yes, I have 2 minutes", ConversationStage.DISCOVERY),
        ("It's for my family to live in", ConversationStage.DISCOVERY),
        ("Within the next 3 months", ConversationStage.DISCOVERY),
        ("Yes, my wife and I will decide together", ConversationStage.QUALIFICATION),
        ("Yes, that's correct", ConversationStage.PRESENTATION),
        ("That sounds interesting, tell me more", ConversationStage.TRIAL_CLOSE),
        ("Yes, I'd like to visit the site", ConversationStage.CLOSING),
        ("Saturday works for me", ConversationStage.DEAL_CLOSED),
    ]

    for user_input, expected_stage in exchanges:
        print(f"\n👤 User: {user_input}")
        print("⏳ Processing...")

        response, should_end, outcome = await engine.process_user_input(
            session, user_input
        )

        print(f"🤖 AI ({session.conversation_stage}): {response}")

        if should_end:
            print(f"\n🎯 Call Outcome: {outcome}")
            break

    print("\n" + "=" * 70)
    print("✅ Conversation completed successfully!")


async def demo_objection_handling():
    """Demo objection handling"""
    print("\n" + "=" * 70)
    print("📞 DEMO: Objection Handling")
    print("=" * 70)

    engine = ConversationEngine()

    session = ConversationSession(
        call_sid="demo_objection",
        lead_id=2,
        lead_name="Priya Sharma",
        lead_phone="+919876543211",
        property_type="2BHK",
        location="HSR Layout, Bangalore",
        budget=6000000.0
    )

    print(f"\n👤 Lead: {session.lead_name}")
    print("\n" + "-" * 70)

    # Start at presentation stage
    session.conversation_stage = ConversationStage.PRESENTATION

    objections = [
        ("The budget seems a bit high for me", "budget"),
        ("I need to discuss with my family first", "family_approval"),
        ("I'm not sure about the location", "location"),
        ("I'm just browsing for now", "just_browsing"),
    ]

    for objection, objection_type in objections:
        print(f"\n👤 User: {objection}")
        print(f"🔍 Detected: {objection_type} objection")

        # Get template response
        response = get_objection_response_template(objection_type)
        print(f"🤖 AI (template): {response}")

    print("\n" + "=" * 70)
    print("✅ All objections handled!")


async def demo_conversation_stages():
    """Demo all conversation stages"""
    print("\n" + "=" * 70)
    print("📞 DEMO: Conversation Stages")
    print("=" * 70)

    from src.conversation.state_machine import ConversationStateMachine

    sm = ConversationStateMachine()

    stages = [
        (ConversationStage.INTRO, "Initial greeting and permission"),
        (ConversationStage.PERMISSION, "Asking for time to talk"),
        (ConversationStage.DISCOVERY, "Understanding requirements"),
        (ConversationStage.QUALIFICATION, "Confirming understanding"),
        (ConversationStage.PRESENTATION, "Presenting properties"),
        (ConversationStage.OBJECTION_HANDLING, "Addressing concerns"),
        (ConversationStage.TRIAL_CLOSE, "Testing readiness"),
        (ConversationStage.CLOSING, "Scheduling visit"),
        (ConversationStage.DEAL_CLOSED, "Success!"),
    ]

    print("\n📊 Conversation Flow:")
    for i, (stage, description) in enumerate(stages, 1):
        print(f"\n{i}. {stage.upper()}")
        print(f"   └─ {description}")

        # Show valid transitions
        next_stages = sm.transitions.get(stage, [])
        if next_stages:
            print(f"   └─ Next: {', '.join([s.value for s in next_stages])}")

    print("\n" + "=" * 70)


async def demo_prompt_templates():
    """Demo prompt templates"""
    print("\n" + "=" * 70)
    print("📞 DEMO: Prompt Templates")
    print("=" * 70)

    # Intro template
    intro = get_intro_template(
        lead_name="Amit Patel",
        property_type="3BHK apartment",
        location="Indiranagar",
        budget="₹75 lakhs"
    )

    print("\n📝 INTRO TEMPLATE:")
    print(intro)

    # Objection templates
    print("\n📝 OBJECTION TEMPLATES:")

    objection_types = ["budget", "timing", "family_approval", "location"]
    for obj_type in objection_types:
        response = get_objection_response_template(obj_type)
        print(f"\n🔹 {obj_type.upper()}:")
        print(f"   {response[:100]}...")

    print("\n" + "=" * 70)


async def demo_analysis():
    """Demo input analysis"""
    print("\n" + "=" * 70)
    print("📞 DEMO: Input Analysis")
    print("=" * 70)

    from src.ai.llm_service import LLMService

    llm = LLMService()

    if not llm.client:
        print("\n⚠️  OpenAI not configured, skipping analysis demo")
        return

    test_inputs = [
        "Yes, I'm interested in buying",
        "The price is too high for me",
        "I need to discuss with my wife",
        "Not interested, please don't call again",
        "My budget is around 80 lakhs",
    ]

    print("\n🔍 Analyzing user inputs...")

    for user_input in test_inputs:
        print(f"\n👤 User: '{user_input}'")
        print("⏳ Analyzing...")

        analysis = await llm.analyze_input(
            user_input=user_input,
            context={"lead_name": "Test", "stage": "presentation"}
        )

        print(f"   Sentiment: {analysis.get('sentiment')}")
        print(f"   Is Objection: {analysis.get('is_objection')}")
        print(f"   Objection Type: {analysis.get('objection_type')}")
        print(f"   Buying Signals: {analysis.get('buying_signals')}")

    print("\n" + "=" * 70)


async def interactive_conversation():
    """Interactive conversation mode"""
    print("\n" + "=" * 70)
    print("📞 INTERACTIVE CONVERSATION MODE")
    print("=" * 70)

    engine = ConversationEngine()

    lead_name = input("\nLead name: ") or "Test User"
    property_type = input("Property type: ") or "2BHK"
    location = input("Location: ") or "Bangalore"
    budget = input("Budget: ") or "5000000"

    session = ConversationSession(
        call_sid="interactive",
        lead_id=999,
        lead_name=lead_name,
        lead_phone="+919876543210",
        property_type=property_type,
        location=location,
        budget=float(budget)
    )

    print("\n" + "-" * 70)
    print(f"Lead Profile:")
    print(f"  Name: {session.lead_name}")
    print(f"  Looking for: {session.property_type} in {session.location}")
    print(f"  Budget: ₹{session.budget/100000:.0f} lakhs")
    print("-" * 70)

    # Generate intro
    intro = await engine.generate_intro(session)
    print(f"\n🤖 AI: {intro}")

    # Interactive loop
    print("\n💬 Type your responses (or 'quit' to exit):")

    while True:
        try:
            user_input = input(f"\n👤 {lead_name}: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Ending conversation...")
                break

            if not user_input:
                continue

            print("⏳ AI is thinking...")

            response, should_end, outcome = await engine.process_user_input(
                session, user_input
            )

            print(f"\n🤖 AI ({session.conversation_stage}): {response}")

            if should_end:
                print(f"\n🎯 Call Outcome: {outcome}")
                print("✅ Conversation ended")
                break

        except KeyboardInterrupt:
            print("\n\n👋 Exiting...")
            break


async def main():
    """Run all demos"""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║          Conversation Engine Demo - Module 4                       ║
║                                                                    ║
║  Demonstrates the AI conversation capabilities                    ║
╚════════════════════════════════════════════════════════════════════╝
    """)

    demos = {
        "1": ("Successful Conversation Flow", demo_successful_conversation),
        "2": ("Objection Handling", demo_objection_handling),
        "3": ("Conversation Stages", demo_conversation_stages),
        "4": ("Prompt Templates", demo_prompt_templates),
        "5": ("Input Analysis (requires OpenAI)", demo_analysis),
        "6": ("Interactive Mode", interactive_conversation),
    }

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        print("\nAvailable Demos:")
        for key, (name, _) in demos.items():
            print(f"  {key}. {name}")
        print(f"  all. Run all demos")
        choice = input("\nSelect demo (1-6, all): ").strip()

    if choice == "all":
        for name, demo_func in demos.values():
            await demo_func()
            await asyncio.sleep(1)
    elif choice in demos:
        name, demo_func = demos[choice]
        await demo_func()
    else:
        print(f"\n❌ Invalid choice: {choice}")
        sys.exit(1)

    print("\n✅ Demo complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
