# Data Extraction & Repetition Fix

## Issues Fixed

### Issue #1: Empty collected_data
**Problem**: After 11 conversation exchanges, `collected_data` was completely empty `{}` even though the customer mentioned "TBHK in white field" and other details.

**Root Cause**:
- System prompt didn't ask LLM to extract structured data
- LLM response format didn't include extracted_data field
- Conversation engine had a TODO comment but no actual implementation
- Session updates weren't being saved back to Redis

**Solution**:
1. ✅ Updated system prompt to explicitly request data extraction
2. ✅ Added `extracted_data` field to JSON response format
3. ✅ Updated LLM service to handle and validate extracted_data
4. ✅ Updated conversation engine to merge extracted_data into session.collected_data
5. ✅ Added session save after AI response generation

---

### Issue #2: Repetitive AI Responses
**Problem**: AI asked "So you're looking for a 2BHK in Whitefield, right?" three times in a row (exchanges 7, 9, and 11).

**Root Cause**:
- No instructions in system prompt to avoid repetition
- LLM wasn't being shown what data was already collected
- No mechanism to prevent asking the same question twice

**Solution**:
1. ✅ Added "INFORMATION ALREADY COLLECTED" section to system prompt
2. ✅ Added explicit rules: "NEVER ask the same question twice"
3. ✅ Added examples of what NOT to do (repetition examples)
4. ✅ Pass collected_data to LLM so it knows what's already been gathered

---

## Files Modified

### 1. [src/conversation/prompt_templates.py](src/conversation/prompt_templates.py)
**Changes**:
- Added "INFORMATION ALREADY COLLECTED" section showing what's already been gathered
- Added explicit rule #3: "NEVER ask the same question twice"
- Added rule #4: "NEVER repeat yourself - move the conversation forward"
- Added "DATA EXTRACTION (CRITICAL)" section with fields to extract
- Updated JSON format to include `extracted_data` field with 5 subfields:
  - property_type
  - location
  - budget
  - timeline
  - purpose
- Added examples of repetition to avoid

### 2. [src/ai/llm_service.py](src/ai/llm_service.py)
**Changes**:
- Added validation for `extracted_data` field in response
- Updated logging to show extracted fields
- Updated `_fix_json_structure()` to include extracted_data
- Updated `_default_streaming_response()` to include empty extracted_data

### 3. [src/conversation/engine.py](src/conversation/engine.py)
**Changes**:
- Extract `extracted_data` from LLM result
- Filter out null/None values from extracted_data
- Merge new data into `session.collected_data`
- Added logging for data collection

### 4. [src/websocket/phase3_event_handlers.py](src/websocket/phase3_event_handlers.py)
**Changes**:
- Added `await self.session_manager.save_session(session)` after generating AI response
- Ensures collected_data updates are persisted to Redis

### 5. [src/websocket/phase4_event_handlers.py](src/websocket/phase4_event_handlers.py)
**Changes**:
- Added `await self.session_manager.save_session(session)` after generating AI response
- Ensures collected_data updates are persisted to Redis

---

## How It Works Now

### Before:
```
User: "I'm looking for a TBHK in white field"
LLM: {
  "response_text": "So you're looking for a 2BHK in Whitefield, right?"
}
collected_data: {}  ❌

Next exchange:
User: "Yes"
LLM: {
  "response_text": "So you're looking for a 2BHK in Whitefield, right?"  ❌ REPETITION
}
collected_data: {}  ❌
```

### After:
```
User: "I'm looking for a TBHK in white field"
LLM: {
  "response_text": "So you're looking for a 3BHK in Whitefield, right?",
  "extracted_data": {
    "property_type": "3BHK",
    "location": "Whitefield",
    "budget": null,
    "timeline": null,
    "purpose": null
  }
}
collected_data: {
  "property_type": "3BHK",
  "location": "Whitefield"
}  ✅

Next exchange:
User: "Yes"
LLM sees:
- INFORMATION ALREADY COLLECTED:
  - property_type: 3BHK
  - location: Whitefield

LLM: {
  "response_text": "Great! What's your budget for this?",  ✅ MOVES FORWARD
  "extracted_data": {...}
}
```

---

## Expected Behavior After Fix

### 1. Data Extraction
The AI will now extract and store:
- **property_type**: "2BHK", "3BHK", "villa", etc.
- **location**: "Whitefield", "Koramangala", "HSR Layout", etc.
- **budget**: "50 lakhs", "1 crore", "5000000", etc.
- **timeline**: "immediately", "next 3 months", "just exploring"
- **purpose**: "self-use", "investment", "rental"

### 2. No Repetition
The AI will:
- Check what information has already been collected
- Ask new questions to gather missing information
- Move the conversation forward instead of repeating

### 3. Redis Storage
After each AI response:
```python
session.collected_data = {
    "property_type": "3BHK",
    "location": "Whitefield",
    "budget": "50 lakhs",
    "timeline": "next 3 months",
    "purpose": "self-use"
}
# Saved to Redis immediately ✅
```

---

## Testing the Fix

### Deploy to Railway
```bash
git add .
git commit -m "Fix: Extract lead data & prevent AI repetition in conversations"
git push
```

### Make a Test Call
1. **Call your Exotel number**
2. **Have a short conversation** mentioning:
   - Property type (e.g., "I'm looking for a 2BHK")
   - Location (e.g., "in Koramangala")
   - Budget (e.g., "around 50 lakhs")

### Check Redis
```bash
python3 scripts/inspect_redis_session.py <call_sid>
```

**Expected output**:
```
📊 collected_data: {
  "property_type": "2BHK",
  "location": "Koramangala",
  "budget": "50 lakhs"
}

📝 transcript_history: (X exchanges)
   1. 🤖 AGENT: Hi! This is Alex from PropertyHub...
   2. 👤 CUSTOMER: I'm looking for a 2BHK in Koramangala
   3. 🤖 AGENT: Great! What's your budget for this?  ✅ NEW QUESTION
   4. 👤 CUSTOMER: Around 50 lakhs
   5. 🤖 AGENT: Got it! When are you looking to move?  ✅ MOVING FORWARD
```

### Check Logs
Look for these log lines:
```
INFO - Updated collected data | new_fields=['property_type', 'location'] | all_collected={'property_type': '2BHK', 'location': 'Koramangala'}
INFO - Streaming LLM response generated | extracted_fields=['property_type', 'location']
```

---

## Summary

**Before**:
- ❌ collected_data always empty
- ❌ AI repeated the same question
- ❌ No data extraction from conversation
- ❌ Session updates not saved

**After**:
- ✅ AI extracts 5 types of lead information
- ✅ AI checks what's already collected
- ✅ AI moves conversation forward
- ✅ All updates saved to Redis
- ✅ Data persisted to PostgreSQL when call ends

---

## Next Steps

1. **Deploy the fixes** to Railway
2. **Make a test call** with property details
3. **Check Redis** for collected_data
4. **Verify** no repetition in conversation
5. **Check PostgreSQL** for persisted data

Ready to deploy when you are! 🚀
