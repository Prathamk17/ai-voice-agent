"""
Response generator for AI conversation.

Generates appropriate responses using playbook-based templates and LLM.
Now integrated with YAML conversation playbook for Indian market.
"""

from typing import Dict, Any, Optional
import random

from src.conversation.prompt_templates import (
    get_real_estate_system_prompt,
    get_intro_template,
    get_objection_response_template
)
from src.conversation.playbook_loader import get_playbook_loader
from src.ai.llm_service import LLMService
from src.models.conversation import ConversationSession
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class ResponseGenerator:
    """
    Generate appropriate responses based on conversation context

    Uses:
    - Playbook-based phrases (natural, varied, Indian market-specific)
    - Templates for common scenarios (fast, consistent)
    - LLM for dynamic/complex responses

    Priority: Playbook > Templates > LLM
    """

    def __init__(self, use_playbook: bool = True):
        """
        Initialize response generator

        Args:
            use_playbook: Whether to use YAML playbook (recommended)
        """
        self.llm_service = LLMService()
        self.use_playbook = use_playbook

        if self.use_playbook:
            try:
                self.playbook = get_playbook_loader()
                logger.info("Response generator initialized with playbook")
            except Exception as e:
                logger.warning("Failed to load playbook, falling back to templates", error=str(e))
                self.use_playbook = False
                self.playbook = None
        else:
            self.playbook = None

    async def generate_intro(
        self,
        session: ConversationSession,
        style: Optional[str] = None
    ) -> str:
        """
        Generate personalized intro message
        AI speaks first when call connects

        Args:
            session: Current conversation session
            style: Speaking style (polite_direct, friendly_quick, soft_hinglish)

        Returns:
            Intro message
        """
        # Use playbook if available
        if self.use_playbook and self.playbook:
            try:
                # Determine style based on context if not provided
                if not style:
                    style = self._determine_style(session)

                # Prepare variables
                variables = {
                    "lead_name": session.lead_name,
                    "agent_name": "Alex",  # TODO: Make configurable
                    "property_type": session.property_type or "property",
                    "location": session.location or "your area",
                    "budget": session.budget
                }

                # Get opening + transition as intro
                opening = self.playbook.get_phrase(
                    stage="intro",
                    category="openings",
                    style=style,
                    variables=variables,
                    call_sid=session.call_sid
                )

                transition = self.playbook.get_phrase(
                    stage="intro",
                    category="transitions",
                    style=style,
                    variables=variables,
                    call_sid=session.call_sid
                )

                intro = f"{opening} {transition}"

                logger.info(
                    "Generated intro from playbook",
                    call_sid=session.call_sid,
                    style=style,
                    intro_length=len(intro)
                )

                return intro

            except Exception as e:
                logger.warning("Playbook intro failed, using fallback", error=str(e))

        # Fallback to template
        intro = get_intro_template(
            lead_name=session.lead_name,
            property_type=session.property_type or "property",
            location=session.location or "your area",
            budget=f"₹{session.budget/100000:.0f} lakhs" if session.budget else "your budget"
        )

        logger.info(
            "Generated intro from template",
            call_sid=session.call_sid,
            intro_length=len(intro)
        )

        return intro

    async def generate_response(
        self,
        session: ConversationSession,
        user_input: str,
        analysis: Dict[str, Any],
        style: Optional[str] = None
    ) -> str:
        """
        Generate response based on user input and analysis

        Decision tree:
        1. If objection -> Use playbook objection patterns
        2. If standard flow -> Use playbook phrases
        3. Otherwise -> Use LLM for dynamic response

        Args:
            session: Current conversation session
            user_input: User's spoken text
            analysis: Analysis of user input
            style: Speaking style override

        Returns:
            AI response text
        """

        # Determine style
        if not style:
            style = self._determine_style(session)

        # Prepare variables
        variables = self._get_session_variables(session)

        # Handle objections with playbook (fastest, most natural)
        if analysis.get("is_objection"):
            objection_type = analysis.get("objection_type")
            if objection_type and objection_type != "none":
                # Try playbook first
                if self.use_playbook and self.playbook:
                    try:
                        response = self.playbook.get_objection_response(
                            objection_type=objection_type,
                            style=style,
                            variables=variables
                        )
                        logger.info(
                            "Using playbook objection response",
                            call_sid=session.call_sid,
                            objection_type=objection_type,
                            style=style
                        )
                        return response
                    except Exception as e:
                        logger.warning("Playbook objection failed", error=str(e))

                # Fallback to template
                response = get_objection_response_template(objection_type)
                logger.info(
                    "Using template objection response",
                    call_sid=session.call_sid,
                    objection_type=objection_type
                )
                return response

        # Try playbook for standard responses
        if self.use_playbook and self.playbook:
            try:
                # Map sentiment to category
                sentiment = analysis.get("sentiment", "neutral")
                response_category = self._get_response_category(
                    session.conversation_stage,
                    sentiment,
                    analysis
                )

                if response_category:
                    response = self.playbook.get_phrase(
                        stage=session.conversation_stage,
                        category=response_category,
                        style=style,
                        variables=variables,
                        call_sid=session.call_sid
                    )

                    logger.info(
                        "Using playbook response",
                        call_sid=session.call_sid,
                        stage=session.conversation_stage,
                        category=response_category
                    )
                    return response

            except Exception as e:
                logger.warning("Playbook response failed, using LLM", error=str(e))

        # Use LLM for dynamic response
        system_prompt = get_real_estate_system_prompt(
            lead_context={
                "lead_name": session.lead_name,
                "property_type": session.property_type,
                "location": session.location,
                "budget": session.budget
            },
            current_stage=session.conversation_stage
        )

        response = await self.llm_service.generate_response(
            user_input=user_input,
            conversation_history=session.transcript_history,
            lead_context=session.collected_data,
            current_stage=session.conversation_stage,
            system_prompt=system_prompt
        )

        logger.info("Using LLM response", call_sid=session.call_sid)
        return response

    def generate_closing_response(
        self,
        outcome: str,
        style: Optional[str] = None,
        call_sid: Optional[str] = None
    ) -> str:
        """
        Generate final response based on call outcome

        Args:
            outcome: Call outcome (qualified, not_interested, etc.)
            style: Speaking style
            call_sid: Call SID

        Returns:
            Closing message
        """
        # Try playbook first
        if self.use_playbook and self.playbook:
            try:
                if not style:
                    style = "polite_direct"  # Default for closing

                # Map outcome to stage
                stage_map = {
                    "qualified": "closing",
                    "callback_requested": "follow_up_scheduling",
                    "not_interested": "dead_end",
                    "send_details": "follow_up_scheduling"
                }

                stage = stage_map.get(outcome, "dead_end")

                response = self.playbook.get_phrase(
                    stage=stage,
                    category="closings",
                    style=style,
                    variables={},
                    call_sid=call_sid
                )

                return response

            except Exception as e:
                logger.warning("Playbook closing failed, using template", error=str(e))

        # Fallback to template
        closings = {
            "qualified": "Perfect! I've scheduled your site visit. You'll receive a WhatsApp with all the details and a calendar invite. Looking forward to showing you around. Have a great day!",

            "callback_requested": "Absolutely! I'll have someone call you back at that time. Thanks for your interest, and talk to you soon!",

            "not_interested": "No problem at all! Thanks for your time. If you change your mind or want to explore options later, feel free to reach out. Have a great day!",

            "send_details": "Perfect! I'll WhatsApp you all the property details, floor plans, and a virtual tour link right away. Feel free to reach out if you have any questions. Thanks!"
        }

        return closings.get(outcome, "Thank you for your time. Have a great day!")

    def _determine_style(self, session: ConversationSession) -> str:
        """
        Determine appropriate speaking style based on session context

        Args:
            session: Conversation session

        Returns:
            Style name (polite_direct, friendly_quick, soft_hinglish)
        """
        # Simple logic - can be made more sophisticated
        # Could analyze user's language patterns, formality, etc.

        # If we detect Hinglish in transcript, use soft_hinglish
        if session.transcript_history:
            recent_text = " ".join([
                t["text"] for t in session.transcript_history[-3:]
                if t["speaker"] == "user"
            ]).lower()

            # Simple Hinglish detection
            hinglish_markers = ["hai", "haan", "nahi", "achha", "theek", "kya", "toh"]
            if any(marker in recent_text for marker in hinglish_markers):
                return "soft_hinglish"

            # Check for casual language
            casual_markers = ["cool", "okay", "yeah", "yup"]
            if any(marker in recent_text for marker in casual_markers):
                return "friendly_quick"

        # Default to polite_direct
        return "polite_direct"

    def _get_session_variables(self, session: ConversationSession) -> Dict[str, Any]:
        """Get variables from session for phrase replacement"""
        return {
            "lead_name": session.lead_name,
            "agent_name": "Alex",  # TODO: Make configurable
            "property_type": session.property_type or "property",
            "location": session.location or "your area",
            "budget": session.budget,
            "phone": session.lead_phone
        }

    def _get_response_category(
        self,
        stage: str,
        sentiment: str,
        analysis: Dict[str, Any]
    ) -> Optional[str]:
        """
        Determine appropriate response category based on context

        Args:
            stage: Current conversation stage
            sentiment: User sentiment
            analysis: Input analysis

        Returns:
            Category name or None
        """
        # Discovery stage - ask questions
        if stage == "discovery":
            return "questions"

        # Permission stage - ask for time
        elif stage == "permission":
            return "openings"

        # Presentation - share benefits
        elif stage == "presentation":
            return "benefits" if "benefits" in analysis.get("user_intent", "") else "transitions"

        # Trial close or closing - confirmations
        elif stage in ["trial_close", "closing"]:
            if sentiment == "positive":
                return "confirmations"
            else:
                return "soft_exits"

        # Default to acknowledgements for other stages
        return "acknowledgements"
