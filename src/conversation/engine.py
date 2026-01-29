"""
Conversation engine - main orchestration logic.

Handles conversation flow, state management, and decision making.
"""

from typing import Tuple, Optional, Dict, Any

from src.models.conversation import ConversationSession, ConversationStage
# REMOVED: Playbook-based components (no longer used)
# from src.conversation.state_machine import ConversationStateMachine
# from src.conversation.response_generator import ResponseGenerator
from src.ai.llm_service import LLMService
from src.conversation.input_preprocessor import preprocess_user_input, detect_wrong_name
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

    def _validate_llm_response(
        self,
        llm_result: Dict[str, Any],
        session: ConversationSession,
        user_input: str
    ) -> Dict[str, Any]:
        """
        Validate and fix LLM response to prevent errors.

        Args:
            llm_result: Raw LLM response
            session: Current conversation session
            user_input: User's input

        Returns:
            Validated and potentially corrected LLM response
        """
        # Check 1: Ensure response_text exists and is not empty
        if not llm_result.get("response_text") or not llm_result["response_text"].strip():
            logger.warning(
                "⚠️ LLM returned empty response, using fallback",
                call_sid=session.call_sid
            )
            # Provide a generic fallback
            llm_result["response_text"] = "I'm here! Could you repeat that?"
            llm_result["should_end_call"] = False

        # Check 2: Prevent premature exits for wrong name
        from src.conversation.input_preprocessor import detect_wrong_name
        if detect_wrong_name(user_input) and llm_result.get("should_end_call"):
            logger.warning(
                "⚠️ Overriding premature exit due to wrong name",
                call_sid=session.call_sid
            )
            llm_result["should_end_call"] = False
            # Prepend name correction if not already in response
            if "alex" not in llm_result["response_text"].lower():
                llm_result["response_text"] = "I'm Alex, but no worries! " + llm_result["response_text"]

        # Check 3: Prevent exit if customer is still engaged
        engaged_signals = [
            "how much", "when", "where", "what", "tell me",
            "interested", "show me", "visit", "see"
        ]
        if llm_result.get("should_end_call") and any(signal in user_input.lower() for signal in engaged_signals):
            logger.warning(
                "⚠️ Overriding exit - customer still engaged",
                call_sid=session.call_sid,
                user_input=user_input[:50]
            )
            llm_result["should_end_call"] = False

        # Check 4: Ensure extracted_data is a dict
        if "extracted_data" in llm_result and not isinstance(llm_result["extracted_data"], dict):
            logger.warning(
                "⚠️ LLM returned invalid extracted_data format",
                call_sid=session.call_sid
            )
            llm_result["extracted_data"] = {}

        return llm_result

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

        # PREPROCESSING: Check for technical questions and wrong name
        response_prefix, is_technical, is_mid_sentence = preprocess_user_input(user_input)

        if is_technical and response_prefix:
            # Technical question detected - provide instant response
            logger.info(
                "🎯 Technical question detected - instant response",
                call_sid=session.call_sid,
                prefix=response_prefix
            )
            # Continue to LLM but prepend the technical response

        # Check for wrong name
        if detect_wrong_name(user_input):
            logger.info(
                "⚠️ Wrong name detected - will handle gracefully",
                call_sid=session.call_sid
            )

        # Build system prompt with context tracking
        from src.conversation.prompt_templates import get_real_estate_system_prompt
        system_prompt = get_real_estate_system_prompt(
            lead_context={
                "lead_name": session.lead_name,
                "property_type": session.property_type,
                "location": session.location,
                "budget": session.budget,
                "collected_data": session.collected_data,
                # Pass context tracking for better response understanding
                "last_agent_question": session.last_agent_question,
                "last_agent_question_type": session.last_agent_question_type
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
                "collected_data": session.collected_data,
                "last_agent_question": session.last_agent_question,
                "last_agent_question_type": session.last_agent_question_type
            },
            system_prompt=system_prompt
        )

        # Validate LLM response before processing
        llm_result = self._validate_llm_response(llm_result, session, user_input)

        # Extract response components
        response_text = llm_result["response_text"]
        should_end_call = llm_result["should_end_call"]
        intent = llm_result["intent"]
        next_action = llm_result["next_action"]
        extracted_data = llm_result.get("extracted_data", {})

        # Extract context tracking fields from LLM response
        last_question_asked = llm_result.get("last_question_asked")
        question_type = llm_result.get("question_type")
        customer_mid_sentence = llm_result.get("customer_mid_sentence", False)

        # Prepend technical response if needed
        if is_technical and response_prefix:
            response_text = response_prefix + response_text

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

        # Update context tracking fields for next turn
        if last_question_asked:
            session.last_agent_question = last_question_asked
            session.last_agent_question_type = question_type
            logger.info(
                "Updated context tracking",
                call_sid=session.call_sid,
                question=last_question_asked,
                question_type=question_type
            )

        # Update mid-sentence flag
        session.customer_mid_sentence = customer_mid_sentence or is_mid_sentence

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

        # Permission-based intro - optimized for voice (short and natural)
        return f"Hi {lead_name}, Alex from PropertyHub. You inquired about {property_type} in {location}. Is this a good time?"
