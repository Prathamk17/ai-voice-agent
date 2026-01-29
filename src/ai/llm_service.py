"""
OpenAI LLM service for conversation management.

Handles response generation and input analysis using GPT-4o-mini.
"""

from typing import Dict, Any, List, Optional
import json
import time

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from src.config.settings import settings
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)

# Import metrics (optional, won't fail if not available)
try:
    from src.monitoring.metrics import metrics
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False
    logger.debug("Metrics not available")


class LLMService:
    """
    Language Model service using GPT-4o-mini

    Handles:
    - Response generation
    - Intent analysis
    - Objection detection
    - Conversation management
    """

    def __init__(self):
        if AsyncOpenAI is None:
            raise ImportError(
                "openai is required. Install it with: pip install openai"
            )

        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not configured")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Using gpt-4o-mini for low-latency voice responses (~1s vs ~2.5s for gpt-4o)
        self.model = "gpt-4o-mini"

    async def generate_streaming_response(
        self,
        user_input: str,
        conversation_history: List[Dict[str, str]],
        lead_context: Dict[str, Any],
        system_prompt: str
    ) -> Dict[str, Any]:
        """
        Generate AI response with streaming using GPT-4o-mini

        Returns structured JSON:
        {
            "intent": str,
            "next_action": "ask_question | respond | schedule_visit | end_call",
            "response_text": str,
            "should_end_call": bool
        }

        Args:
            user_input: What the lead just said
            conversation_history: Previous exchanges
            lead_context: Lead information (name, property type, etc.)
            system_prompt: Instructions for the AI

        Returns:
            Structured response dict
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return self._default_streaming_response()

        try:
            # Build messages
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # Add conversation history (last 8 exchanges for better context retention)
            for exchange in conversation_history[-8:]:
                messages.append({
                    "role": "user" if exchange["speaker"] == "user" else "assistant",
                    "content": exchange["text"]
                })

            # Add current input
            messages.append({
                "role": "user",
                "content": user_input
            })

            logger.info(
                "Generating streaming LLM response",
                history_length=len(conversation_history)
            )

            # Call GPT-4o-mini with timing and streaming
            start_time = time.time()

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,  # Increased from 0.7 for more natural, human-like variety
                max_tokens=200,  # Increased from 150 to allow slightly longer natural responses
                stream=True,  # Enable streaming
                response_format={"type": "json_object"}  # Enforce JSON output
            )

            # Collect streamed response
            full_response = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    # Yield tokens to enable downstream streaming (future enhancement)

            duration = time.time() - start_time

            # Parse JSON response
            try:
                result = json.loads(full_response)
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response", response=full_response[:200])
                return self._default_streaming_response(full_response)

            # Validate structure
            required_fields = ["intent", "next_action", "response_text", "should_end_call"]
            if not all(k in result for k in required_fields):
                logger.warning("Incomplete JSON structure", result=result)
                result = self._fix_json_structure(result, full_response)

            # Ensure extracted_data field exists (even if empty)
            if "extracted_data" not in result:
                result["extracted_data"] = {}

            # Record metrics
            if METRICS_ENABLED:
                metrics.record_llm_request(self.model, duration)

            logger.info(
                "Streaming LLM response generated",
                response_length=len(result.get("response_text", "")),
                intent=result.get("intent"),
                next_action=result.get("next_action"),
                extracted_fields=list(k for k, v in result.get("extracted_data", {}).items() if v),
                duration_seconds=round(duration, 3)
            )

            return result

        except Exception as e:
            logger.error("Streaming LLM generation failed", error=str(e))

            # Record error
            if METRICS_ENABLED:
                metrics.record_error("llm_request_failed", "llm_service")

            return self._default_streaming_response()

    def _default_streaming_response(self, fallback_text: str = "") -> Dict[str, Any]:
        """Return safe default when LLM fails"""
        return {
            "intent": "unclear",
            "next_action": "respond",
            "response_text": fallback_text or "Sorry, could you repeat that?",
            "should_end_call": False,
            "extracted_data": {}
        }

    def _fix_json_structure(self, partial: Dict, raw: str) -> Dict[str, Any]:
        """Fix incomplete JSON from LLM"""
        return {
            "intent": partial.get("intent", "unclear"),
            "next_action": partial.get("next_action", "respond"),
            "response_text": partial.get("response_text") or partial.get("response") or raw[:150],
            "should_end_call": partial.get("should_end_call", False),
            "extracted_data": partial.get("extracted_data", {})
        }

    # Legacy method kept for backward compatibility (deprecated)
    async def generate_response(
        self,
        user_input: str,
        conversation_history: List[Dict[str, str]],
        lead_context: Dict[str, Any],
        current_stage: str,
        system_prompt: str
    ) -> str:
        """
        DEPRECATED: Use generate_streaming_response() instead

        Generate AI response using GPT-4o-mini (non-streaming, legacy)
        """
        logger.warning("Using deprecated generate_response() - use generate_streaming_response() instead")

        if not self.client:
            logger.error("OpenAI client not initialized")
            return "I apologize, I'm having technical difficulties. Could you please repeat?"

        try:
            # Build messages
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # Add conversation history (last 8 exchanges for better context retention)
            for exchange in conversation_history[-8:]:
                messages.append({
                    "role": "user" if exchange["speaker"] == "user" else "assistant",
                    "content": exchange["text"]
                })

            # Add current input
            messages.append({
                "role": "user",
                "content": user_input
            })

            logger.info(
                "Generating LLM response",
                stage=current_stage,
                history_length=len(conversation_history)
            )

            # Call GPT-4o-mini with timing
            start_time = time.time()

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=150,  # Keep responses concise for voice
            )

            duration = time.time() - start_time

            # Record metrics
            if METRICS_ENABLED:
                metrics.record_llm_request(self.model, duration)

            ai_response = response.choices[0].message.content.strip()

            logger.info(
                "LLM response generated",
                response_length=len(ai_response),
                response_preview=ai_response[:100],
                duration_seconds=round(duration, 3)
            )

            return ai_response

        except Exception as e:
            logger.error("LLM generation failed", error=str(e))

            # Record error
            if METRICS_ENABLED:
                metrics.record_error("llm_request_failed", "llm_service")

            # Fallback response
            return "I apologize, I'm having trouble processing that. Could you repeat?"

    async def analyze_input(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze user input for intent, sentiment, objections

        Args:
            user_input: User's spoken text
            context: Current conversation context

        Returns:
            {
                "sentiment": "positive/neutral/negative",
                "is_objection": bool,
                "objection_type": str or None,
                "buying_signals": List[str],
                "extracted_info": Dict
            }
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return self._default_analysis()

        try:
            analysis_prompt = f"""
Analyze this response from a real estate lead:
"{user_input}"

Lead context: {json.dumps(context)}

Extract and return ONLY a JSON object with:
{{
    "sentiment": "positive/neutral/negative",
    "is_objection": true/false,
    "objection_type": "budget/location/timing/family_approval/just_browsing/none",
    "buying_signals": ["signal1", "signal2"],
    "extracted_info": {{
        "budget_mentioned": null or number,
        "timeline_mentioned": null or string,
        "location_preference": null or string,
        "response": "yes/no/maybe/unclear"
    }}
}}
"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            analysis = json.loads(response.choices[0].message.content)

            logger.info("Input analysis complete", analysis=analysis)

            return analysis

        except Exception as e:
            logger.error("Input analysis failed", error=str(e))
            return self._default_analysis()

    def _default_analysis(self) -> Dict[str, Any]:
        """Return safe default analysis when LLM fails"""
        return {
            "sentiment": "neutral",
            "is_objection": False,
            "objection_type": None,
            "buying_signals": [],
            "extracted_info": {}
        }
