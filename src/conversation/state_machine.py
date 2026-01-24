"""
Conversation state machine for managing stage transitions.

Defines valid transitions between conversation stages and logic
for determining next stage.
"""

from typing import Dict, Any, Optional

from src.models.conversation import ConversationStage
from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class ConversationStateMachine:
    """
    Manages conversation stage transitions
    """

    def __init__(self):
        # Define valid transitions
        self.transitions = {
            ConversationStage.INTRO: [
                ConversationStage.PERMISSION,
                ConversationStage.DISCOVERY,
                ConversationStage.DEAD_END
            ],
            ConversationStage.PERMISSION: [
                ConversationStage.DISCOVERY,
                ConversationStage.DEAD_END
            ],
            ConversationStage.DISCOVERY: [
                ConversationStage.QUALIFICATION,
                ConversationStage.OBJECTION_HANDLING,
                ConversationStage.DEAD_END
            ],
            ConversationStage.QUALIFICATION: [
                ConversationStage.PRESENTATION,
                ConversationStage.OBJECTION_HANDLING
            ],
            ConversationStage.PRESENTATION: [
                ConversationStage.TRIAL_CLOSE,
                ConversationStage.OBJECTION_HANDLING,
                ConversationStage.DEAD_END
            ],
            ConversationStage.OBJECTION_HANDLING: [
                ConversationStage.PRESENTATION,
                ConversationStage.TRIAL_CLOSE,
                ConversationStage.DEAD_END
            ],
            ConversationStage.TRIAL_CLOSE: [
                ConversationStage.CLOSING,
                ConversationStage.OBJECTION_HANDLING,
                ConversationStage.DEAD_END
            ],
            ConversationStage.CLOSING: [
                ConversationStage.DEAL_CLOSED,
                ConversationStage.FOLLOW_UP_SCHEDULED,
                ConversationStage.OBJECTION_HANDLING
            ]
        }

    def transition(
        self,
        current_stage: ConversationStage,
        target_stage: ConversationStage,
        reason: str = ""
    ) -> bool:
        """
        Attempt to transition to new stage

        Args:
            current_stage: Current conversation stage
            target_stage: Desired next stage
            reason: Reason for transition

        Returns:
            True if transition is valid
        """
        if target_stage in self.transitions.get(current_stage, []):
            logger.info(
                "Stage transition",
                from_stage=current_stage,
                to_stage=target_stage,
                reason=reason
            )
            return True

        logger.warning(
            "Invalid stage transition attempted",
            from_stage=current_stage,
            to_stage=target_stage
        )
        return False

    def determine_next_stage(
        self,
        current_stage: ConversationStage,
        analysis: Dict[str, Any],
        collected_data: Dict[str, Any]
    ) -> ConversationStage:
        """
        Determine next stage based on analysis and context

        Args:
            current_stage: Current stage
            analysis: Analysis of user input
            collected_data: Information collected so far

        Returns:
            Next conversation stage
        """

        # Dead end conditions
        if analysis.get("sentiment") == "negative" and current_stage == ConversationStage.INTRO:
            return ConversationStage.DEAD_END

        # Objection handling
        if analysis.get("is_objection"):
            return ConversationStage.OBJECTION_HANDLING

        # Stage-specific logic
        if current_stage == ConversationStage.INTRO:
            response = analysis.get("extracted_info", {}).get("response", "").lower()
            if "yes" in response or "sure" in response or "okay" in response:
                return ConversationStage.DISCOVERY
            elif "no" in response or "busy" in response:
                return ConversationStage.DEAD_END
            return ConversationStage.PERMISSION

        elif current_stage == ConversationStage.PERMISSION:
            response = analysis.get("extracted_info", {}).get("response", "").lower()
            if "yes" in response or "okay" in response or "sure" in response:
                return ConversationStage.DISCOVERY
            elif "no" in response or "busy" in response or "not interested" in response:
                return ConversationStage.DEAD_END
            # If unclear, stay in permission to re-ask
            return ConversationStage.PERMISSION

        elif current_stage == ConversationStage.DISCOVERY:
            # Check if we have all required info
            required_fields = ["purpose", "budget_confirmed", "timeline"]
            has_all_info = all(
                collected_data.get(field) for field in required_fields
            )
            if has_all_info:
                return ConversationStage.QUALIFICATION
            return ConversationStage.DISCOVERY

        elif current_stage == ConversationStage.QUALIFICATION:
            return ConversationStage.PRESENTATION

        elif current_stage == ConversationStage.PRESENTATION:
            if analysis.get("buying_signals"):
                return ConversationStage.TRIAL_CLOSE
            return ConversationStage.PRESENTATION

        elif current_stage == ConversationStage.TRIAL_CLOSE:
            if analysis.get("sentiment") == "positive":
                return ConversationStage.CLOSING
            return ConversationStage.TRIAL_CLOSE

        elif current_stage == ConversationStage.CLOSING:
            response = analysis.get("extracted_info", {}).get("response", "").lower()
            if "yes" in response or "sure" in response:
                return ConversationStage.DEAL_CLOSED
            return ConversationStage.CLOSING

        elif current_stage == ConversationStage.OBJECTION_HANDLING:
            # Return to previous relevant stage
            return ConversationStage.PRESENTATION

        # Default: stay in current stage
        return current_stage
