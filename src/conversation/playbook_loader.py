"""
Conversation Playbook Loader

Loads and provides access to the YAML-based conversation playbook.
Handles phrase selection, style management, and dynamic content injection.
"""

import yaml
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache

from src.utils.logger import StructuredLogger

logger = StructuredLogger(__name__)


class PlaybookLoader:
    """
    Loads and manages the conversation playbook

    Handles:
    - YAML loading
    - Phrase selection with variation
    - Dynamic variable replacement
    - Style-based response generation
    """

    def __init__(self, playbook_path: Optional[str] = None):
        """
        Initialize playbook loader

        Args:
            playbook_path: Path to playbook YAML file
        """
        if playbook_path is None:
            # Default path
            base_dir = Path(__file__).parent.parent.parent
            playbook_path = base_dir / "config" / "conversation_playbook.yaml"

        self.playbook_path = Path(playbook_path)
        self.playbook = self._load_playbook()
        self.used_phrases = {}  # Track used phrases to ensure variation

        logger.info("Playbook loaded", path=str(self.playbook_path))

    def _load_playbook(self) -> Dict[str, Any]:
        """Load playbook from YAML file"""
        try:
            with open(self.playbook_path, 'r', encoding='utf-8') as f:
                playbook = yaml.safe_load(f)

            logger.info("Playbook loaded successfully")
            return playbook

        except FileNotFoundError:
            logger.error("Playbook file not found", path=str(self.playbook_path))
            raise
        except yaml.YAMLError as e:
            logger.error("Failed to parse playbook YAML", error=str(e))
            raise

    def get_phrase(
        self,
        stage: str,
        category: str,
        style: str = "polite_direct",
        variables: Optional[Dict[str, Any]] = None,
        call_sid: Optional[str] = None
    ) -> str:
        """
        Get a phrase from the playbook with variation

        Args:
            stage: Conversation stage (e.g., "intro", "discovery")
            category: Phrase category (e.g., "openings", "questions")
            style: Speaking style (e.g., "polite_direct", "soft_hinglish")
            variables: Variables to inject (e.g., {"lead_name": "John"})
            call_sid: Call SID for tracking used phrases

        Returns:
            Selected phrase with variables replaced
        """
        try:
            # Get stage data
            stage_data = self.playbook.get(stage, {})
            if not stage_data:
                logger.warning("Stage not found in playbook", stage=stage)
                return f"Stage {stage} not configured"

            # Get style data
            styles = stage_data.get("styles", {})
            style_data = styles.get(style, {})

            # Fallback to first available style if requested style not found
            if not style_data and styles:
                style = list(styles.keys())[0]
                style_data = styles[style]
                logger.debug("Using fallback style", requested_style=style, using=style)

            # Get phrases for category
            phrases = style_data.get(category, [])

            if not phrases:
                logger.warning(
                    "No phrases found",
                    stage=stage,
                    category=category,
                    style=style
                )
                return f"No {category} configured for {stage}"

            # Select phrase with variation
            phrase = self._select_varied_phrase(phrases, stage, category, call_sid)

            # Replace variables
            if variables:
                phrase = self._replace_variables(phrase, variables)

            return phrase

        except Exception as e:
            logger.error(
                "Failed to get phrase",
                stage=stage,
                category=category,
                error=str(e)
            )
            return "I'm having trouble finding the right words. Let me try again."

    def _select_varied_phrase(
        self,
        phrases: List[str],
        stage: str,
        category: str,
        call_sid: Optional[str]
    ) -> str:
        """
        Select a phrase ensuring variation within the same call

        Args:
            phrases: List of available phrases
            stage: Current stage
            category: Phrase category
            call_sid: Call SID

        Returns:
            Selected phrase
        """
        if not call_sid:
            # No call tracking, just return random
            return random.choice(phrases)

        # Track key for this phrase type in this call
        tracking_key = f"{call_sid}:{stage}:{category}"

        # Get previously used phrases for this call
        if tracking_key not in self.used_phrases:
            self.used_phrases[tracking_key] = set()

        used = self.used_phrases[tracking_key]

        # Get unused phrases
        unused = [p for p in phrases if p not in used]

        # If all phrases used, reset
        if not unused:
            self.used_phrases[tracking_key] = set()
            unused = phrases

        # Select random unused phrase
        selected = random.choice(unused)

        # Mark as used
        self.used_phrases[tracking_key].add(selected)

        return selected

    def _replace_variables(self, phrase: str, variables: Dict[str, Any]) -> str:
        """
        Replace variables in phrase

        Args:
            phrase: Phrase with {variable} placeholders
            variables: Variable values

        Returns:
            Phrase with variables replaced
        """
        try:
            # Find all {variable} patterns
            pattern = r'\{([^}]+)\}'

            def replace_var(match):
                var_name = match.group(1)
                value = variables.get(var_name, match.group(0))

                # Format specific variables
                if var_name == "budget" and isinstance(value, (int, float)):
                    # Convert to lakhs/crores
                    if value >= 10000000:  # 1 crore+
                        return f"₹{value/10000000:.1f} crore"
                    else:
                        return f"₹{value/100000:.0f} lakhs"

                elif var_name == "time_of_day":
                    # Determine time of day
                    from datetime import datetime
                    hour = datetime.now().hour
                    if hour < 12:
                        return "morning"
                    elif hour < 17:
                        return "afternoon"
                    else:
                        return "evening"

                return str(value)

            return re.sub(pattern, replace_var, phrase)

        except Exception as e:
            logger.error("Variable replacement failed", error=str(e))
            return phrase

    def get_stage_goal(self, stage: str) -> str:
        """Get the goal for a conversation stage"""
        stage_data = self.playbook.get(stage, {})
        return stage_data.get("goal", "")

    def get_stage_rules(self, stage: str) -> Dict[str, List[str]]:
        """Get rules (must_do/avoid) for a stage"""
        stage_data = self.playbook.get(stage, {})
        return stage_data.get("rules", {})

    def get_voice_notes(self, stage: str) -> Dict[str, str]:
        """Get voice behavior notes for a stage"""
        stage_data = self.playbook.get(stage, {})
        return stage_data.get("voice_notes", {})

    def get_objection_response(
        self,
        objection_type: str,
        style: str = "polite_direct",
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get response for specific objection type

        Args:
            objection_type: Type of objection
            style: Speaking style
            variables: Variables to inject

        Returns:
            Objection response
        """
        try:
            objection_data = self.playbook.get("objection_handling", {})
            patterns = objection_data.get("patterns", {})
            objection_pattern = patterns.get(objection_type, {})
            responses = objection_pattern.get(style, [])

            if not responses:
                logger.warning("No objection response found", type=objection_type, style=style)
                return "I understand your concern. Let me see how we can address that."

            # Select random response
            response = random.choice(responses)

            # Replace variables if provided
            if variables:
                response = self._replace_variables(response, variables)

            return response

        except Exception as e:
            logger.error("Failed to get objection response", error=str(e))
            return "I understand. Let me think about how we can work with that."

    def get_available_styles(self, stage: str) -> List[str]:
        """Get list of available styles for a stage"""
        stage_data = self.playbook.get(stage, {})
        styles = stage_data.get("styles", {})
        return list(styles.keys())

    def get_global_settings(self) -> Dict[str, Any]:
        """Get global voice and quality settings"""
        return {
            "voice_settings": self.playbook.get("global_voice_settings", {}),
            "quality_standards": self.playbook.get("quality_standards", {})
        }

    def clear_used_phrases(self, call_sid: str):
        """Clear tracked phrases for a call (call ended)"""
        keys_to_remove = [k for k in self.used_phrases.keys() if k.startswith(f"{call_sid}:")]
        for key in keys_to_remove:
            del self.used_phrases[key]

        logger.debug("Cleared used phrases", call_sid=call_sid)


# Singleton instance
_playbook_loader: Optional[PlaybookLoader] = None


def get_playbook_loader(playbook_path: Optional[str] = None) -> PlaybookLoader:
    """
    Get singleton playbook loader instance

    Args:
        playbook_path: Optional custom playbook path

    Returns:
        PlaybookLoader instance
    """
    global _playbook_loader

    if _playbook_loader is None:
        _playbook_loader = PlaybookLoader(playbook_path)

    return _playbook_loader


def reload_playbook():
    """Reload playbook (useful for development/testing)"""
    global _playbook_loader
    _playbook_loader = None
    return get_playbook_loader()
