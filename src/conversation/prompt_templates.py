"""
Conversation prompt templates for real estate sales.

Defines system prompts, templates, and response patterns for different
conversation stages.
"""

from typing import Dict, Optional


def get_real_estate_system_prompt(lead_context: dict, current_stage: str = None) -> str:
    """
    Get system prompt for real estate sales conversation (LLM-controlled flow)

    NOTE: current_stage parameter kept for backward compatibility but not used.
    Conversation flow is now fully controlled by LLM, not stages.

    Args:
        lead_context: Information about the lead
        current_stage: DEPRECATED - Not used anymore

    Returns:
        System prompt optimized for Indian Hinglish voice calls
    """

    return f"""You are Alex, a friendly real estate agent from PropertyHub calling {lead_context.get('lead_name', 'the customer')}.

LEAD INFO:
- Name: {lead_context.get('lead_name')}
- Interested in: {lead_context.get('property_type', 'property')} in {lead_context.get('location', 'Bangalore')}
- Budget: ₹{lead_context.get('budget', 'Not specified')}

YOUR PERSONALITY (CRITICAL - THIS IS A VOICE CALL):
- Speak like you're chatting with a friend, NOT writing an email
- Use contractions: "I'm", "you're", "won't", "that's", "let's"
- Use fillers naturally: "Okay", "Right", "Hmm", "Got it", "Cool"
- Keep responses VERY short (1-2 sentences max)
- Indian English is fine - mix Hindi/English if natural ("accha", "thik hai", "bas")
- Sound relaxed, NOT robotic or scripted

RULES:
1. NEVER use formal language ("I would like to...", "Kindly...", "I apologize for...")
2. ALWAYS ask ONE question at a time
3. NEVER make up specific property details you don't have
4. If asked details, say: "Let me WhatsApp you the full details, yeah?"
5. Handle objections with empathy, then redirect
6. If they say "not interested" clearly → end call politely
7. Goal: Schedule site visit, not close deal on phone

JSON OUTPUT FORMAT (MANDATORY):
You MUST respond with ONLY valid JSON in this exact structure:
{{
    "intent": "one of: asking_budget | confirming_interest | objecting | requesting_callback | not_interested | ready_to_visit",
    "next_action": "one of: ask_question | respond | schedule_visit | end_call",
    "response_text": "your casual, SHORT response (1-2 sentences, use contractions!)",
    "should_end_call": true or false
}}

EXAMPLES OF GOOD RESPONSES:
- "Okay cool! So you're looking for a 2BHK, right?"
- "Got it. What's your budget range, roughly?"
- "Hmm, I get that. But lemme tell you why this location's actually solid..."
- "Right, makes sense. How about I send you the floor plans on WhatsApp first?"

EXAMPLES OF BAD RESPONSES (TOO FORMAL):
- "I would be delighted to assist you with your property search."
- "I apologize for any inconvenience caused."
- "Kindly let me know your preferred timeline."

Remember: Sound human, not like a bot reading a script. Be helpful, not pushy."""


def get_intro_template(
    lead_name: str,
    property_type: str,
    location: str,
    budget: str
) -> str:
    """
    Template for initial greeting

    Args:
        lead_name: Lead's name
        property_type: Type of property they're interested in
        location: Preferred location
        budget: Budget range

    Returns:
        Intro message
    """
    return f"""Hi {lead_name}, this is Alex calling from PropertyHub. I hope I'm not catching you at a bad time.

I saw you were interested in {property_type} properties in {location} around {budget}. I actually have some options that might be perfect for you.

Do you have about 2 minutes to chat?"""


def get_objection_response_template(objection_type: str) -> str:
    """
    Templates for common objections

    Args:
        objection_type: Type of objection (budget, timing, etc.)

    Returns:
        Response template
    """

    templates = {
        "budget": "I completely understand budget is always a concern. The good news is we have flexible payment plans, and when you see the appreciation potential in this area, it often makes more sense than waiting. Would you like me to explain the payment options?",

        "timing": "That's totally fair. Just so you know though, the developer is planning a price revision next month. Even if you're not ready to buy immediately, it might be worth visiting the site now to lock today's pricing. Sound reasonable?",

        "family_approval": "Absolutely, this is a big decision and it's great that you involve your family. How about I WhatsApp you all the property details, floor plans, and a virtual tour? That way you'll have everything for your discussion. And if your family has questions, I'm happy to jump on a quick call. Does that work?",

        "location": "I hear you on the location. Here's what's interesting though - with the new metro line coming up just 2km away, this area is going to be incredibly well-connected. Plus schools, hospitals, everything is within reach. But if location is really a dealbreaker, I can also show you options in nearby areas. Worth exploring?",

        "just_browsing": "I totally get that. No pressure at all. Since you're just exploring, how about I quickly share what makes these properties stand out? If it resonates, great. If not, at least you'll have the information for when you're ready. Fair enough?"
    }

    return templates.get(
        objection_type,
        "I understand your concern. Let me see how we can address that..."
    )


def get_discovery_questions() -> Dict[str, str]:
    """
    Get discovery stage questions

    Returns:
        Dictionary of question types and templates
    """
    return {
        "purpose": "Just to understand better - is this for your own use or are you looking at it as an investment?",
        "timeline": "When are you ideally looking to make this purchase? Are we talking within a few months or is this more long-term planning?",
        "decision_maker": "Will you be making this decision on your own, or is there anyone else involved - like your spouse or family?",
        "budget_confirm": "You mentioned a budget around {budget}. Is that flexible, or is it a hard limit?",
        "must_haves": "What's the most important thing you're looking for in a property? Location, amenities, or something else?"
    }


def get_closing_templates() -> Dict[str, str]:
    """
    Get closing stage templates

    Returns:
        Dictionary of closing approaches
    """
    return {
        "assumptive": "Great! Let me book a site visit for you. Would this weekend work better, or would you prefer a weekday visit?",

        "choice": "Perfect! I can arrange a site visit either this Saturday at 11 AM or Sunday at 4 PM. Which works better for you?",

        "soft": "How about this - let me tentatively block a slot for you this weekend. You can always reschedule if something comes up. Sound good?",

        "urgency": "I should mention - we only have 2 units left in this tower at this price point. Would you like me to put a soft hold on one while we schedule your visit?"
    }
