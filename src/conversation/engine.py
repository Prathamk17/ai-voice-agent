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

    def _check_recent_repetition(self, response_text: str, transcript_history: list) -> bool:
        """
        Check if the agent is asking the same question that was asked in recent exchanges

        Args:
            response_text: Current response from LLM
            transcript_history: Full conversation history

        Returns:
            True if repetition detected, False otherwise
        """
        if not transcript_history or len(transcript_history) < 2:
            return False

        # Get last 3 agent responses (not including current one)
        recent_agent_responses = [
            exchange["text"].lower()
            for exchange in transcript_history[-6:]  # Last 6 exchanges = ~3 agent + 3 user
            if exchange.get("speaker") in ["ai", "agent"]
        ][-3:]  # Take last 3 agent responses

        if not recent_agent_responses:
            return False

        # Normalize current response
        current_lower = response_text.lower().strip()

        # Check for exact or near-exact repetition
        for past_response in recent_agent_responses:
            # Exact match
            if current_lower == past_response.strip():
                logger.warning(
                    "🚨 EXACT REPETITION DETECTED",
                    current=current_lower[:80],
                    past=past_response[:80]
                )
                return True

            # Similar match (>80% similarity using simple word overlap)
            current_words = set(current_lower.split())
            past_words = set(past_response.split())

            if len(current_words) > 3 and len(past_words) > 3:
                overlap = len(current_words & past_words)
                similarity = overlap / max(len(current_words), len(past_words))

                if similarity > 0.8:
                    logger.warning(
                        "🚨 SIMILAR REPETITION DETECTED",
                        similarity=f"{similarity*100:.0f}%",
                        current=current_lower[:80],
                        past=past_response[:80]
                    )
                    return True

        return False

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
                "collected_data": session.collected_data  # Pass collected_data to help LLM
            },
            system_prompt=system_prompt
        )

        # Extract response components
        response_text = llm_result["response_text"]
        should_end_call = llm_result["should_end_call"]
        intent = llm_result["intent"]
        next_action = llm_result["next_action"]
        extracted_data = llm_result.get("extracted_data", {})

        # 🚨 RECENT REPETITION CHECK: Prevent asking same question twice in a row
        if self._check_recent_repetition(response_text, session.transcript_history):
            logger.error(
                "🚨 BLOCKING REPETITIVE RESPONSE - LLM repeated recent question",
                call_sid=session.call_sid,
                blocked_response=response_text[:100]
            )

            # Override with a different question based on conversation stage
            fallback_questions = [
                "When are you ideally looking to move in?",
                "Have you started seeing any properties yet?",
                "Are you flexible with the location, or pretty set on this area?",
                "Is financing sorted, or would you need a home loan?"
            ]

            # Pick a fallback that hasn't been asked recently
            for fallback in fallback_questions:
                if not self._check_recent_repetition(fallback, session.transcript_history):
                    response_text = fallback
                    logger.info(
                        "✅ REPLACED REPETITIVE RESPONSE",
                        call_sid=session.call_sid,
                        new_response=response_text
                    )
                    break
            else:
                # If all fallbacks were asked, move to closing
                response_text = "Based on what you've told me, I think we have some great options. How about I arrange a site visit this weekend?"
                logger.info("✅ MOVED TO CLOSING (all fallbacks exhausted)", call_sid=session.call_sid)

        # 🚨 ANTI-REPETITION VALIDATION: Check if LLM is asking about already-collected data
        response_lower = response_text.lower()
        if session.collected_data and "?" in response_text:
            # Generic detection: Check if asking about ANY field that's already collected
            repetition_patterns = {
                "purpose": [
                    "own use or investment",
                    "self-use or investment",
                    "for yourself or investment",
                    "living or investment",
                    "stay or investment"
                ],
                "budget": [
                    "budget",
                    "price range",
                    "how much",
                    "spend"
                ],
                "timeline": [
                    "when.*move",
                    "when.*looking to",
                    "how soon",
                    "timeline"
                ],
                "location": [
                    "which area",
                    "specific area",
                    "location preference",
                    "where exactly"
                ],
                "property_type": [
                    "how many bhk",
                    "2bhk or 3bhk",
                    "what size",
                    "apartment or villa"
                ]
            }

            for field, patterns in repetition_patterns.items():
                if field in session.collected_data and session.collected_data[field]:
                    # Check if any pattern matches current question
                    import re
                    for pattern in patterns:
                        if re.search(pattern, response_lower):
                            logger.warning(
                                f"🚨 REPETITION DETECTED: Asking about {field} when already collected",
                                call_sid=session.call_sid,
                                field=field,
                                collected_value=session.collected_data[field],
                                pattern_matched=pattern
                            )

                            # Override with progression question
                            fallback_progressions = {
                                "purpose": "Got it. Have you started seeing any properties yet, or just exploring?",
                                "budget": "Perfect! When are you ideally looking to move - next few months?",
                                "timeline": "Great! Should I arrange a site visit for you this weekend?",
                                "location": "Cool! Are you flexible with the exact locality, or pretty set on this area?",
                                "property_type": "Right. Is financing sorted, or would you need a home loan?"
                            }

                            response_text = fallback_progressions.get(
                                field,
                                "Based on what you've shared, I think we have some perfect options. Shall I arrange a site visit?"
                            )

                            logger.info(
                                "✅ REPLACED REPETITIVE QUESTION",
                                call_sid=session.call_sid,
                                field=field,
                                new_response=response_text
                            )
                            break

        # Update collected data from LLM extraction
        if extracted_data:
            # Filter out null/None values and update session
            new_data = {k: v for k, v in extracted_data.items() if v is not None}

            if new_data:
                # Merge with existing collected_data
                session.collected_data.update(new_data)

                logger.info(
                    "Updated collected data",
                    call_sid=session.call_sid,
                    new_fields=list(new_data.keys()),
                    all_collected=session.collected_data
                )

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
        # Use simple template with permission check (like the audio sample)
        lead_name = session.lead_name
        property_type = session.property_type or "property"
        location = session.location or "your preferred area"

        # Permission-based intro following structured call flow
        return f"Hi {lead_name}, this is Alex from PropertyHub. I saw you inquired about {property_type} in {location}. Is this a good time to talk for 2 minutes?"
