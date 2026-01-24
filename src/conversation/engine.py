"""
Conversation engine - main orchestration logic.

Handles conversation flow, state management, and decision making.
"""

from typing import Tuple, Optional

from src.models.conversation import ConversationSession, ConversationStage
# REMOVED: Playbook-based components (no longer used)
# from src.conversation.state_machine import ConversationStateMachine
# from src.conversation.response_generator import ResponseGenerator
from src.ai.llm_service import LLMService
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class ConversationEngine:
    """
    Main conversation orchestration engine

    Responsibilities:
    - Process user input
    - Determine conversation flow
    - Generate appropriate responses
    - Track conversation state
    - Decide when to end call
    """

    def __init__(self):
        # REMOVED: Playbook-based components (state_machine, response_generator)
        # Conversation flow is now 100% LLM-controlled
        self.llm_service = LLMService()

    async def process_user_input(
        self,
        session: ConversationSession,
        user_input: str
    ) -> Tuple[str, bool, Optional[str]]:
        """
        Process user input using LLM-only flow (no playbooks, no stages)

        Args:
            session: Current conversation session
            user_input: User's spoken text

        Returns:
            (response_text, should_end_call, call_outcome)
        """

        logger.info(
            "Processing user input (LLM-controlled flow)",
            call_sid=session.call_sid,
            input=user_input[:100]
        )

        # Build system prompt
        from src.conversation.prompt_templates import get_real_estate_system_prompt
        system_prompt = get_real_estate_system_prompt(
            lead_context={
                "lead_name": session.lead_name,
                "property_type": session.property_type,
                "location": session.location,
                "budget": session.budget,
                "collected_data": session.collected_data
            }
        )

        # Get LLM response with streaming (single call, no separate analysis)
        llm_result = await self.llm_service.generate_streaming_response(
            user_input=user_input,
            conversation_history=session.transcript_history,
            lead_context={
                "lead_name": session.lead_name,
                "property_type": session.property_type,
                "location": session.location,
                "budget": session.budget,
            },
            system_prompt=system_prompt
        )

        # Extract response components
        response_text = llm_result["response_text"]
        should_end_call = llm_result["should_end_call"]
        intent = llm_result["intent"]
        next_action = llm_result["next_action"]

        # Determine outcome for call tracking
        call_outcome = None
        if should_end_call:
            if intent == "not_interested":
                call_outcome = "not_interested"
            elif intent == "ready_to_visit" or next_action == "schedule_visit":
                call_outcome = "qualified"
            else:
                call_outcome = "callback_requested"

        logger.info(
            "LLM decision",
            call_sid=session.call_sid,
            intent=intent,
            next_action=next_action,
            should_end_call=should_end_call,
            outcome=call_outcome
        )

        # Update collected data from LLM output (optional enhancement)
        # You could parse response_text for budget/timeline mentions if needed

        return response_text, should_end_call, call_outcome

    async def generate_intro(
        self,
        session: ConversationSession
    ) -> str:
        """
        Generate intro message when call starts (now LLM-generated, not playbook)

        Args:
            session: Conversation session

        Returns:
            Intro message
        """
        # Use simple template (can be LLM-generated for variety if needed)
        lead_name = session.lead_name
        property_type = session.property_type or "property"
        location = session.location or "your preferred area"

        # Quick casual intro
        return f"Hi {lead_name}, this is Alex from PropertyHub. Hope I'm not catching you at a bad time? I saw you were looking at {property_type} in {location}. Got a couple minutes to chat?"
