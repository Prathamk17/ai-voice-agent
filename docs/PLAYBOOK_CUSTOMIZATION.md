# Conversation Playbook Customization Guide

Complete guide to customizing your AI's conversation patterns using the YAML playbook.

---

## 📚 Table of Contents

1. [Understanding the Playbook Structure](#understanding-the-playbook-structure)
2. [Quick Modifications](#quick-modifications)
3. [Adding New Phrases](#adding-new-phrases)
4. [Customizing Speaking Styles](#customizing-speaking-styles)
5. [Objection Handling](#objection-handling)
6. [Variable Reference](#variable-reference)
7. [Voice Behavior Notes](#voice-behavior-notes)
8. [Advanced: Adding New Stages](#advanced-adding-new-stages)
9. [Testing Your Changes](#testing-your-changes)
10. [Best Practices](#best-practices)

---

## Understanding the Playbook Structure

The playbook is located at `config/conversation_playbook.yaml` and follows this structure:

```yaml
stage_name:
  goal: "What this stage accomplishes"

  styles:
    polite_direct:
      category_name:
        - "Phrase variation 1"
        - "Phrase variation 2"
        - "Phrase variation 3"

    friendly_quick:
      category_name:
        - "Casual phrase 1"
        - "Casual phrase 2"

    soft_hinglish:
      category_name:
        - "Hinglish phrase 1"
        - "Hinglish phrase 2"

  voice_notes:
    pacing: "Speed guidance"
    tone: "Emotional tone"
    fillers: "Natural hesitations"
```

### Key Concepts

**Stages**: Major conversation phases (intro, discovery, presentation, etc.)
**Styles**: Speaking approaches (polite_direct, friendly_quick, soft_hinglish)
**Categories**: Types of phrases within a stage (openings, questions, benefits, etc.)
**Variations**: Multiple ways to say the same thing (prevents repetition)

---

## Quick Modifications

### Change an Existing Phrase

**File**: `config/conversation_playbook.yaml`

**Find the phrase:**
```yaml
intro:
  styles:
    polite_direct:
      openings:
        - "Hi {lead_name}, this is {agent_name} from PropertyHub. Hope I'm not disturbing?"
```

**Replace with your version:**
```yaml
intro:
  styles:
    polite_direct:
      openings:
        - "Hello {lead_name}, {agent_name} calling from RealEstate Pro. Got a minute?"
```

**That's it!** The AI will now use your phrase.

### Change Company Name Globally

**Search for**: `PropertyHub`
**Replace with**: `YourCompany`

All phrases will automatically update.

### Adjust AI Personality

**Current**:
```yaml
intro:
  voice_notes:
    tone: "Warm, confident, professional"
```

**More casual**:
```yaml
intro:
  voice_notes:
    tone: "Friendly, relaxed, approachable"
```

**More formal**:
```yaml
intro:
  voice_notes:
    tone: "Professional, respectful, courteous"
```

---

## Adding New Phrases

### Add Phrase Variations

**Why**: Prevents the AI from sounding repetitive. More variations = more natural.

**Example**: Add a new opening line

```yaml
intro:
  styles:
    polite_direct:
      openings:
        - "Hi {lead_name}, this is {agent_name} from PropertyHub. Hope I'm not disturbing?"
        - "Hello {lead_name}! {agent_name} calling from PropertyHub. Is now a good time?"
        - "Good {time_of_day} {lead_name}, {agent_name} here from PropertyHub. Quick moment?"  # NEW
```

The AI will randomly select from these variations for each call.

### Add New Category to a Stage

**Example**: Add "ice_breakers" to the intro stage

```yaml
intro:
  styles:
    polite_direct:
      openings:
        - "Hi {lead_name}..."

      transitions:
        - "I'm calling because..."

      # NEW CATEGORY
      ice_breakers:
        - "Hope you're having a great day!"
        - "Thanks for taking my call!"
```

**Use it in code**:
```python
ice_breaker = playbook.get_phrase(
    stage="intro",
    category="ice_breakers",
    style="polite_direct"
)
```

---

## Customizing Speaking Styles

### Understanding the 3 Styles

**polite_direct**
- Most formal
- Full sentences
- Proper grammar
- Best for: High-value leads, older demographics

**friendly_quick**
- Casual but professional
- Shorter sentences
- Conversational
- Best for: Young professionals, quick conversations

**soft_hinglish**
- Mix of English and Hindi
- Very relatable
- Indian market specific
- Best for: Local leads, tier 2/3 cities

### Modify a Style

**Example**: Make friendly_quick even more casual

```yaml
discovery:
  styles:
    friendly_quick:
      questions:
        - "So what kind of place are you looking for?"  # Current
        - "What's your dream home like?"                # More casual
        - "Tell me about your ideal property?"          # More casual
```

### Add a New Style (Advanced)

**Step 1**: Add the style to every stage

```yaml
intro:
  styles:
    polite_direct:
      openings: [...]

    friendly_quick:
      openings: [...]

    soft_hinglish:
      openings: [...]

    # NEW STYLE
    ultra_formal:
      openings:
        - "Good {time_of_day}, Mr./Ms. {lead_name}. This is {agent_name} representing PropertyHub."
      transitions:
        - "I am reaching out regarding your inquiry for {property_type} properties in {location}."
```

**Step 2**: Update style detection logic

**File**: `src/conversation/response_generator.py`

```python
def _determine_style(self, session: ConversationSession) -> str:
    # ... existing logic ...

    # Add ultra formal detection
    formal_markers = ["sir", "madam", "kindly", "request"]
    if any(marker in recent_text for marker in formal_markers):
        return "ultra_formal"

    return "polite_direct"
```

---

## Objection Handling

### Modify Existing Objection Response

**File**: `config/conversation_playbook.yaml`

**Find**:
```yaml
objections:
  budget_too_high:
    responses:
      polite_direct:
        - "I completely understand, {lead_name}. Let me be honest..."
```

**Replace**:
```yaml
objections:
  budget_too_high:
    responses:
      polite_direct:
        - "I hear you on the budget, {lead_name}. Let me share something..."
        - "{lead_name}, great that you're budget-conscious! Here's the thing..."
```

### Add New Objection Type

**Step 1**: Add to playbook

```yaml
objections:
  # ... existing objections ...

  # NEW OBJECTION
  area_safety_concerns:
    responses:
      polite_direct:
        - "That's a very valid concern, {lead_name}. Let me share what we've done for security..."
        - "Safety is our top priority, {lead_name}. The project has 24/7 security with..."

      friendly_quick:
        - "Totally get it! Security here is actually pretty solid - 24/7 guards, CCTV..."

      soft_hinglish:
        - "Haan {lead_name}, safety bahut important hai. Yahan 24/7 security hai with full CCTV coverage..."

    follow_ups:
      - "Would you like to see the security setup during a site visit?"
      - "We can arrange a meeting with our security team if that helps?"
```

**Step 2**: Update LLM to detect it

**File**: `src/conversation/prompt_templates.py`

Find the objection types list and add:
```python
OBJECTION_TYPES = [
    "just_browsing",
    "budget_too_high",
    # ... existing types ...
    "area_safety_concerns"  # NEW
]
```

---

## Variable Reference

### Available Variables

Variables are automatically replaced with actual values when phrases are used.

| Variable | Description | Example Output |
|----------|-------------|----------------|
| `{lead_name}` | Lead's name | "Priya" |
| `{agent_name}` | AI's name | "Alex" |
| `{property_type}` | Type of property | "3BHK apartment" |
| `{location}` | Property location | "Whitefield, Bangalore" |
| `{budget}` | Formatted budget | "₹75 lakhs" |
| `{phone}` | Lead's phone | "+919876543210" |
| `{time_of_day}` | Current time of day | "morning" / "afternoon" / "evening" |

### Using Variables in Phrases

**Basic usage**:
```yaml
openings:
  - "Hi {lead_name}, this is {agent_name} from PropertyHub."
```

**Multiple variables**:
```yaml
transitions:
  - "You were looking at {property_type} in {location} around {budget}, correct?"
```

**Optional variables** (graceful fallback):
```yaml
questions:
  - "What's your budget range, {lead_name}?"  # Works even if budget is None
```

### Adding Custom Variables

**Step 1**: Update variable extraction

**File**: `src/conversation/response_generator.py`

```python
def _get_session_variables(self, session: ConversationSession) -> Dict[str, Any]:
    return {
        "lead_name": session.lead_name,
        "agent_name": "Alex",
        "property_type": session.property_type or "property",
        "location": session.location or "your area",
        "budget": session.budget,
        "phone": session.lead_phone,
        # ADD NEW VARIABLE
        "bedrooms": session.collected_data.get("bedrooms", "2-3"),
        "move_in_date": session.collected_data.get("timeline", "soon")
    }
```

**Step 2**: Use in playbook

```yaml
questions:
  - "You mentioned wanting {bedrooms} bedrooms. Is that still the plan?"
  - "When are you looking to move in? You said {move_in_date}, right?"
```

---

## Voice Behavior Notes

Voice notes guide the TTS engine on HOW to speak the phrases.

### Current Voice Notes

```yaml
intro:
  voice_notes:
    pacing: "Medium speed, allow pauses"
    tone: "Warm, confident, professional"
    fillers: "Use natural pauses like 'um', light hesitation"
    pauses: "After name, after company name"
```

### Customizing Voice Notes

**Make AI speak faster**:
```yaml
voice_notes:
  pacing: "Quick, energetic, no long pauses"
```

**Make AI sound more enthusiastic**:
```yaml
voice_notes:
  tone: "Excited, upbeat, energetic"
  fillers: "Use positive affirmations like 'absolutely!', 'definitely!'"
```

**Make AI sound more empathetic**:
```yaml
voice_notes:
  tone: "Warm, understanding, patient"
  pacing: "Slow, deliberate, giving time to think"
  fillers: "Use empathetic sounds like 'mm-hmm', 'I see'"
```

**Regional accent**:
```yaml
voice_notes:
  accent: "Indian English with slight Hindi influence"
  pronunciation: "Softer 't' and 'd' sounds"
```

---

## Advanced: Adding New Stages

### When to Add a New Stage

**Good reasons**:
- You have a unique step in your sales process
- You need different conversation logic
- You want separate tracking/analytics

**Example**: Add "technical_discussion" stage

### Step 1: Add to Playbook

**File**: `config/conversation_playbook.yaml`

```yaml
# Add after presentation stage
technical_discussion:
  goal: "Answer detailed technical questions about the property"

  styles:
    polite_direct:
      openings:
        - "Let me walk you through the technical specifications, {lead_name}."
        - "Great questions! Here are the detailed specs..."

      answers:
        - "The carpet area is {carpet_area} sq ft, which is quite spacious."
        - "We're using {construction_material} for better durability."

      transitions:
        - "Does this answer your technical questions?"
        - "Anything else you'd like to know about the construction?"

  voice_notes:
    pacing: "Measured, clear, precise"
    tone: "Knowledgeable, confident, detailed"
```

### Step 2: Add to State Machine

**File**: `src/conversation/state_machine.py`

```python
class ConversationStage(str, Enum):
    # ... existing stages ...
    TECHNICAL_DISCUSSION = "technical_discussion"  # ADD THIS

# Then add transitions
self.transitions = {
    # ... existing transitions ...
    ConversationStage.PRESENTATION: [
        ConversationStage.TECHNICAL_DISCUSSION,  # NEW
        ConversationStage.OBJECTION_HANDLING,
        ConversationStage.TRIAL_CLOSE
    ],
    ConversationStage.TECHNICAL_DISCUSSION: [  # NEW STAGE
        ConversationStage.TRIAL_CLOSE,
        ConversationStage.CLOSING
    ]
}
```

### Step 3: Add Detection Logic

**File**: `src/conversation/state_machine.py`

```python
def determine_next_stage(self, current_stage, analysis, collected_data):
    # ... existing logic ...

    # Detect technical questions
    if current_stage == ConversationStage.PRESENTATION:
        technical_keywords = ["specification", "sq ft", "carpet area", "construction"]
        user_response = analysis.get("user_intent", "").lower()

        if any(keyword in user_response for keyword in technical_keywords):
            return ConversationStage.TECHNICAL_DISCUSSION

    # ... rest of logic ...
```

---

## Testing Your Changes

### 1. Validate YAML Syntax

```bash
# Check for YAML errors
python -c "import yaml; yaml.safe_load(open('config/conversation_playbook.yaml'))"
```

If no errors, you'll see no output. If there are errors, you'll get line numbers.

### 2. Test Specific Phrases

**Create a test script**: `test_playbook.py`

```python
from src.conversation.playbook_loader import get_playbook_loader

playbook = get_playbook_loader()

# Test a specific phrase
phrase = playbook.get_phrase(
    stage="intro",
    category="openings",
    style="polite_direct",
    variables={
        "lead_name": "Test User",
        "agent_name": "Alex"
    }
)

print(f"Generated phrase: {phrase}")
```

Run it:
```bash
python test_playbook.py
```

### 3. Test Variation System

```python
# Test that variations are working
for i in range(10):
    phrase = playbook.get_phrase(
        stage="intro",
        category="openings",
        style="polite_direct",
        variables={"lead_name": "Test", "agent_name": "Alex"},
        call_sid=f"test_call_{i}"
    )
    print(f"Variation {i}: {phrase}")
```

You should see different phrases each time.

### 4. Test with Demo Conversation

```bash
# Run interactive demo to test changes
python scripts/demo_conversation.py 6
```

### 5. Run Full Tests

```bash
# After creating playbook tests
pytest tests/test_playbook.py -v
```

---

## Best Practices

### 1. Phrase Variations

**❌ Bad**: Only 1-2 variations
```yaml
openings:
  - "Hi {lead_name}, this is {agent_name}."
  - "Hello {lead_name}, {agent_name} calling."
```

**✅ Good**: 5-10 variations
```yaml
openings:
  - "Hi {lead_name}, this is {agent_name} from PropertyHub. Hope I'm not disturbing?"
  - "Hello {lead_name}! {agent_name} calling from PropertyHub. Is now a good time?"
  - "Good {time_of_day} {lead_name}, {agent_name} here from PropertyHub. Got a minute?"
  - "{lead_name}, hi! This is {agent_name} with PropertyHub. Quick call - is this okay?"
  - "Hey {lead_name}, {agent_name} from PropertyHub. Catching you at a good time?"
```

### 2. Natural Language

**❌ Bad**: Robotic, formal
```yaml
- "I am calling to inform you about our property offerings."
```

**✅ Good**: Conversational, natural
```yaml
- "I'm calling because you were looking at properties in {location}, right?"
```

### 3. Variable Usage

**❌ Bad**: Hardcoded values
```yaml
- "I'm calling about the 2BHK apartment in Bangalore."
```

**✅ Good**: Use variables
```yaml
- "I'm calling about the {property_type} in {location}."
```

### 4. Style Consistency

**❌ Bad**: Mixing formality within same style
```yaml
soft_hinglish:
  - "Namaste {lead_name}, I am reaching out to discuss..."  # Too formal
  - "Kya haal hai? Ready to buy?"  # Too casual
```

**✅ Good**: Consistent tone
```yaml
soft_hinglish:
  - "Hi {lead_name}, {agent_name} bol raha hoon PropertyHub se."
  - "Hello {lead_name}! Main {agent_name}, PropertyHub se call kar raha hoon."
```

### 5. Objection Responses

**❌ Bad**: Defensive or pushy
```yaml
- "But you should really consider this opportunity!"
```

**✅ Good**: Empathetic and solution-focused
```yaml
- "I completely understand, {lead_name}. Let me share something that might help..."
```

### 6. Keep It Concise

**❌ Bad**: Long-winded
```yaml
- "I wanted to reach out to you today because we have received information that you have been searching for residential properties in the Bangalore area and we have some excellent options that I believe would be of great interest to you and I would love to discuss them if you have a few minutes available."
```

**✅ Good**: Short and clear
```yaml
- "Hi {lead_name}! You were looking at properties in {location}, right? Got a minute to chat?"
```

### 7. Backup Your Changes

```bash
# Before making major changes
cp config/conversation_playbook.yaml config/conversation_playbook.backup.yaml
```

---

## Common Customization Scenarios

### Scenario 1: Change from Real Estate to Another Industry

**Example**: Adapt for car sales

```yaml
intro:
  goal: "Identify yourself, establish permission, create interest in vehicles"

  styles:
    polite_direct:
      openings:
        - "Hi {lead_name}, this is {agent_name} from AutoHub. Hope I'm not disturbing?"

      transitions:
        - "I'm calling because you were looking at {vehicle_model} in your budget, right?"

      value_props:
        - "We have an amazing {vehicle_type} that just came in."
        - "There's a special offer on {vehicle_model} this week."
```

**Update variables**:
```python
def _get_session_variables(self, session):
    return {
        "lead_name": session.lead_name,
        "agent_name": "Alex",
        "vehicle_type": session.product_type,
        "vehicle_model": session.model,
        "budget": session.budget
    }
```

### Scenario 2: Add Regional Language Support

**Example**: Add Tamil support

```yaml
intro:
  styles:
    # ... existing styles ...

    tamil_friendly:
      openings:
        - "Vanakkam {lead_name}, naan {agent_name} PropertyHub-lerundhu."
        - "Hello {lead_name}, {agent_name} speaking from PropertyHub. Pesalama?"

      transitions:
        - "Neenga {location}-la {property_type} paakura-ingala?"
```

### Scenario 3: High-Value Luxury Properties

**Add luxury style**:

```yaml
intro:
  styles:
    luxury_exclusive:
      openings:
        - "Good {time_of_day}, {lead_name}. This is {agent_name}, your dedicated consultant from PropertyHub Luxury."

      value_props:
        - "We have an exceptional {property_type} that matches your refined taste."
        - "This is a rare opportunity in {location}'s most prestigious address."

  voice_notes:
    pacing: "Slow, deliberate, unhurried"
    tone: "Sophisticated, refined, confident"
    vocabulary: "Premium, exclusive, bespoke, curated"
```

---

## Troubleshooting

### Issue: "KeyError: stage not found"

**Cause**: You're trying to use a stage that doesn't exist in the playbook.

**Solution**: Add the stage to `conversation_playbook.yaml` or fix the typo.

### Issue: Variables not replacing

**Cause**: Variable not passed to `get_phrase()` or wrong format.

**Solution**: Check variable dict:
```python
variables = {
    "lead_name": "John",  # String, not None
    "budget": 5000000     # Number, not None
}
```

### Issue: Same phrase repeating

**Cause**: Not enough variations or call_sid not being passed.

**Solution**:
1. Add more phrase variations (5-10 minimum)
2. Ensure call_sid is passed: `get_phrase(..., call_sid=session.call_sid)`

### Issue: YAML syntax error

**Common mistakes**:
```yaml
# ❌ Wrong: Inconsistent indentation
openings:
  - "Phrase 1"
   - "Phrase 2"  # Extra space

# ✅ Correct
openings:
  - "Phrase 1"
  - "Phrase 2"

# ❌ Wrong: Missing quotes with special characters
- Hello {lead_name}: how are you?

# ✅ Correct
- "Hello {lead_name}: how are you?"
```

---

## Advanced Tips

### 1. A/B Testing Phrases

Track which phrases lead to better outcomes:

```python
# In playbook_loader.py, log phrase selection
logger.info(
    "Phrase selected",
    stage=stage,
    category=category,
    phrase_index=selected_index,
    call_sid=call_sid
)
```

Analyze logs to see which variations perform best.

### 2. Time-of-Day Variations

```yaml
intro:
  styles:
    polite_direct:
      openings:
        - "Good morning {lead_name}, this is {agent_name}..."  # Use with time_of_day filter
        - "Good afternoon {lead_name}, {agent_name} calling..."
        - "Good evening {lead_name}, this is {agent_name}..."
```

### 3. Sentiment-Based Responses

```yaml
objection_handling:
  styles:
    polite_direct:
      positive_sentiment:
        - "That's great to hear, {lead_name}! Let's move forward..."

      neutral_sentiment:
        - "I understand, {lead_name}. Let me clarify..."

      negative_sentiment:
        - "I completely understand your concern, {lead_name}. Here's what we can do..."
```

### 4. Dynamic Phrase Loading

For very large playbooks, consider splitting by stage:

```yaml
# config/playbook/intro.yaml
# config/playbook/discovery.yaml
# config/playbook/presentation.yaml
```

Load on demand to reduce memory usage.

---

## Resources

- **Playbook File**: [config/conversation_playbook.yaml](../config/conversation_playbook.yaml)
- **Loader Code**: [src/conversation/playbook_loader.py](../src/conversation/playbook_loader.py)
- **Response Generator**: [src/conversation/response_generator.py](../src/conversation/response_generator.py)
- **Examples**: [examples/README.md](../examples/README.md)

---

## Getting Help

### Check Playbook Syntax
```bash
python -c "import yaml; print('✅ Valid YAML') if yaml.safe_load(open('config/conversation_playbook.yaml')) else print('❌ Invalid')"
```

### Test Your Changes
```bash
python scripts/demo_conversation.py 6  # Interactive mode
```

### View Logs
```bash
tail -f logs/app.log | grep "Playbook"
```

---

**Happy customizing!** 🎨

The playbook system is designed to be flexible and powerful. Start with small changes and iterate based on real conversation outcomes.

Remember: The best conversation flow is one that feels natural to YOUR leads in YOUR market. Test, iterate, and improve!
