"""
Input preprocessor for handling technical questions and edge cases.

Catches common technical questions BEFORE they reach the LLM to provide
instant responses and prevent confusion.
"""

import re
from typing import Tuple, Optional


# Technical question patterns with instant responses
TECHNICAL_PATTERNS = {
    r"\b(am i|can you hear|do you hear|am i audible)\b": "Haan, I can hear you clearly! ",
    r"\b(hello|are you there|you there)\b": "Haan, I'm here! ",
    r"\b(can you understand|are you listening)\b": "Yes yes, perfectly! ",
}

# Filler words indicating customer is mid-sentence
FILLER_WORDS = [
    "like", "umm", "uh", "so", "basically",
    "you know", "i mean", "well", "actually"
]

# Wrong name patterns (customer confusing agent name)
WRONG_NAME_PATTERNS = [
    r"\b(amit|rahul|priya|ravi|sanjay|raj)\b"
]


def preprocess_user_input(user_input: str) -> Tuple[Optional[str], bool, bool]:
    """
    Preprocess user input to handle technical questions and edge cases.

    Args:
        user_input: Raw user input text

    Returns:
        Tuple of:
        - response_prefix: Instant response to prepend (if technical question)
        - is_technical: True if this was a technical clarification
        - is_mid_sentence: True if customer seems to be mid-thought
    """
    if not user_input:
        return None, False, False

    input_lower = user_input.lower().strip()

    # Check for technical questions
    for pattern, response in TECHNICAL_PATTERNS.items():
        if re.search(pattern, input_lower, re.IGNORECASE):
            # Technical question detected
            return response, True, False

    # Check if customer is mid-sentence
    is_mid_sentence = _is_mid_sentence(user_input)

    return None, False, is_mid_sentence


def _is_mid_sentence(text: str) -> bool:
    """
    Detect if customer is mid-sentence (using filler words or trailing punctuation).

    Args:
        text: User input text

    Returns:
        True if likely mid-sentence, False otherwise
    """
    text_lower = text.lower().strip()

    # Check for filler words at the end
    for filler in FILLER_WORDS:
        if text_lower.endswith(filler):
            return True
        # Also check with punctuation
        if text_lower.endswith(filler + ",") or text_lower.endswith(filler + "..."):
            return True

    # Check for trailing ellipsis or comma
    if text.strip().endswith(("...", ",", "like", "like,")):
        return True

    # Check for very short incomplete sentences
    words = text_lower.split()
    if len(words) <= 3 and any(filler in words for filler in FILLER_WORDS):
        return True

    return False


def detect_wrong_name(user_input: str) -> bool:
    """
    Detect if customer is using wrong agent name.

    Args:
        user_input: User input text

    Returns:
        True if wrong name detected, False otherwise
    """
    input_lower = user_input.lower()

    for pattern in WRONG_NAME_PATTERNS:
        if re.search(pattern, input_lower, re.IGNORECASE):
            # Check if it's actually addressing someone
            # (not just mentioning a name in context)
            if re.search(r"(hi|hello|hey)\s+" + pattern, input_lower, re.IGNORECASE):
                return True

    return False


def should_wait_for_completion(user_input: str, is_bot_speaking: bool) -> bool:
    """
    Determine if system should wait for customer to complete their thought.

    Args:
        user_input: Current user input
        is_bot_speaking: Whether agent is currently speaking

    Returns:
        True if should wait, False if can proceed
    """
    # If bot is speaking and user said very little, wait a bit
    if is_bot_speaking and len(user_input.strip().split()) < 3:
        return True

    # If clearly mid-sentence, wait
    if _is_mid_sentence(user_input):
        return True

    return False
