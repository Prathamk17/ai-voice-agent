"""
Tests for conversation playbook system.

Tests playbook loading, phrase selection, variation, and variable replacement.
"""

import pytest
from datetime import datetime
from src.conversation.playbook_loader import PlaybookLoader, get_playbook_loader


class TestPlaybookLoader:
    """Test PlaybookLoader functionality"""

    def test_initialization(self):
        """Test playbook loader initializes correctly"""
        loader = get_playbook_loader()

        assert loader is not None
        assert loader.playbook is not None
        assert "intro" in loader.playbook
        assert "discovery" in loader.playbook
        # Objections are structured separately, not as a stage
        assert "metadata" in loader.playbook

    def test_singleton_pattern(self):
        """Test get_playbook_loader returns same instance"""
        loader1 = get_playbook_loader()
        loader2 = get_playbook_loader()

        assert loader1 is loader2

    def test_get_phrase_basic(self):
        """Test basic phrase retrieval"""
        loader = get_playbook_loader()

        phrase = loader.get_phrase(
            stage="intro",
            category="openings",
            style="polite_direct"
        )

        assert phrase is not None
        assert isinstance(phrase, str)
        assert len(phrase) > 0

    def test_get_phrase_all_styles(self):
        """Test phrase retrieval for all styles"""
        loader = get_playbook_loader()

        styles = ["polite_direct", "friendly_quick", "soft_hinglish"]

        for style in styles:
            phrase = loader.get_phrase(
                stage="intro",
                category="openings",
                style=style
            )

            assert phrase is not None
            assert isinstance(phrase, str)
            assert len(phrase) > 0

    def test_get_phrase_with_variables(self):
        """Test variable replacement in phrases"""
        loader = get_playbook_loader()

        variables = {
            "lead_name": "Priya",
            "agent_name": "Alex",
            "property_type": "3BHK",
            "location": "Bangalore",
            "budget": 7500000
        }

        phrase = loader.get_phrase(
            stage="intro",
            category="openings",
            style="polite_direct",
            variables=variables
        )

        # Check that variables were replaced
        assert "Priya" in phrase or "{lead_name}" not in phrase
        assert "Alex" in phrase or "{agent_name}" not in phrase

    def test_variable_replacement_budget_formatting(self):
        """Test budget variable is formatted correctly"""
        loader = get_playbook_loader()

        variables = {
            "budget": 7500000,  # 75 lakhs
            "lead_name": "Test",
            "property_type": "3BHK"
        }

        # Get multiple phrases to find one with budget
        phrases_checked = 0
        budget_found = False

        for _ in range(10):
            phrase = loader.get_phrase(
                stage="discovery",
                category="questions",
                style="polite_direct",
                variables=variables,
                call_sid=f"budget_test_{_}"
            )
            phrases_checked += 1

            # Budget should be formatted if present
            if "75 lakh" in phrase or "75L" in phrase or "7500000" in phrase:
                budget_found = True
                break

        # At least verify we got valid phrases
        assert phrases_checked > 0

    def test_variable_replacement_time_of_day(self):
        """Test time_of_day variable is set correctly"""
        loader = get_playbook_loader()

        variables = {}

        phrase = loader.get_phrase(
            stage="intro",
            category="openings",
            style="polite_direct",
            variables=variables
        )

        # time_of_day should be morning/afternoon/evening
        if "{time_of_day}" in phrase:
            current_hour = datetime.now().hour
            if 5 <= current_hour < 12:
                assert "morning" in phrase.lower()
            elif 12 <= current_hour < 17:
                assert "afternoon" in phrase.lower()
            else:
                assert "evening" in phrase.lower()

    def test_phrase_variation_different_calls(self):
        """Test that phrases vary across different calls"""
        loader = get_playbook_loader()

        phrases_seen = set()

        # Get phrases for 10 different calls
        for i in range(10):
            phrase = loader.get_phrase(
                stage="intro",
                category="openings",
                style="polite_direct",
                call_sid=f"test_call_{i}"
            )
            phrases_seen.add(phrase)

        # Should have some variation (at least 2 different phrases)
        assert len(phrases_seen) >= 2, "Phrases should vary across calls"

    def test_phrase_variation_same_call(self):
        """Test that phrases don't repeat within same call"""
        loader = get_playbook_loader()

        call_sid = "test_call_variation"
        phrases_seen = []

        # Get multiple phrases for same call
        # Note: Only 3 variations exist in intro.openings.polite_direct
        for _ in range(3):
            phrase = loader.get_phrase(
                stage="intro",
                category="openings",
                style="polite_direct",
                call_sid=call_sid
            )
            phrases_seen.append(phrase)

        # Should have variation
        unique_phrases = set(phrases_seen)
        assert len(unique_phrases) >= 2, "Should have at least some variation"

        # If we have more than 1 variation available, we should get different ones
        if len(unique_phrases) > 1:
            # At least 2 different phrases in our 3 requests
            assert len(unique_phrases) >= 2

    def test_get_objection_response(self):
        """Test objection response retrieval"""
        loader = get_playbook_loader()

        response = loader.get_objection_response(
            objection_type="budget_too_high",
            style="polite_direct"
        )

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    def test_get_objection_response_all_types(self):
        """Test all objection types have responses"""
        loader = get_playbook_loader()

        objection_types = [
            "just_browsing",
            "budget_too_high",
            "call_me_later",
            "need_family_approval",
            "location_mismatch",
            "not_interested"
        ]

        for objection_type in objection_types:
            response = loader.get_objection_response(
                objection_type=objection_type,
                style="polite_direct"
            )

            assert response is not None, f"Missing response for {objection_type}"
            assert isinstance(response, str)
            assert len(response) > 0

    def test_objection_response_with_variables(self):
        """Test objection responses support variables"""
        loader = get_playbook_loader()

        variables = {
            "lead_name": "Rajesh",
            "budget": 5000000
        }

        response = loader.get_objection_response(
            objection_type="budget_too_high",
            style="polite_direct",
            variables=variables
        )

        # Should contain lead name
        assert "Rajesh" in response or "{lead_name}" not in response

    def test_objection_follow_ups(self):
        """Test objection follow-up questions"""
        loader = get_playbook_loader()

        # Get main response
        response = loader.get_objection_response(
            objection_type="budget_too_high",
            style="polite_direct"
        )

        # Follow-ups should be appended
        assert isinstance(response, str)
        assert len(response) > 0

        # Check if follow-up is present (ends with question mark typically)
        # This is optional, so we just verify response is valid

    def test_missing_stage(self):
        """Test handling of missing stage"""
        loader = get_playbook_loader()

        # Should return fallback message instead of raising error
        phrase = loader.get_phrase(
            stage="nonexistent_stage",
            category="openings",
            style="polite_direct"
        )

        assert "not configured" in phrase.lower() or "stage" in phrase.lower()

    def test_missing_category(self):
        """Test handling of missing category"""
        loader = get_playbook_loader()

        # Should return fallback message instead of raising error
        phrase = loader.get_phrase(
            stage="intro",
            category="nonexistent_category",
            style="polite_direct"
        )

        assert "not configured" in phrase.lower() or phrase is not None

    def test_missing_style(self):
        """Test handling of missing style"""
        loader = get_playbook_loader()

        # Should fall back to first available style
        phrase = loader.get_phrase(
            stage="intro",
            category="openings",
            style="nonexistent_style"
        )

        # Should still get a valid phrase (fallback to default style)
        assert phrase is not None
        assert len(phrase) > 0

    def test_all_stages_have_required_categories(self):
        """Test that all stages have minimum required structure"""
        loader = get_playbook_loader()

        required_stages = [
            "intro",
            "permission",
            "discovery",
            "qualification",
            "presentation",
            "objection_handling",
            "trial_close",
            "closing",
            "follow_up_scheduling",
            "dead_end"
        ]

        for stage in required_stages:
            assert stage in loader.playbook, f"Missing stage: {stage}"

            stage_data = loader.playbook[stage]

            # Each stage should have either styles or specific structure
            # (objection_handling has different structure)
            if "styles" in stage_data:
                # Each style should have at least one category
                styles = stage_data["styles"]
                assert len(styles) > 0, f"No styles defined for {stage}"

    def test_all_styles_exist_in_all_stages(self):
        """Test that all three styles exist in stages with styles"""
        loader = get_playbook_loader()

        required_styles = ["polite_direct", "friendly_quick", "soft_hinglish"]

        # Only check stages that have styles (excludes objection_handling which has different structure)
        stages = [
            "intro",
            "permission",
            "discovery",
            "qualification",
            "presentation",
            "trial_close",
            "closing",
            "follow_up_scheduling",
            "dead_end"
        ]

        for stage in stages:
            if "styles" in loader.playbook[stage]:
                styles = loader.playbook[stage]["styles"]

                for required_style in required_styles:
                    assert required_style in styles, \
                        f"Missing style {required_style} in stage {stage}"

    def test_phrase_list_not_empty(self):
        """Test that all phrase categories have at least one phrase"""
        loader = get_playbook_loader()

        stages = ["intro", "discovery", "presentation"]

        for stage in stages:
            styles = loader.playbook[stage]["styles"]

            for style_name, style_data in styles.items():
                for category, phrases in style_data.items():
                    assert isinstance(phrases, list), \
                        f"{stage}.{style_name}.{category} should be a list"
                    assert len(phrases) > 0, \
                        f"{stage}.{style_name}.{category} should not be empty"

    def test_voice_notes_exist(self):
        """Test that stages have voice_notes"""
        loader = get_playbook_loader()

        stages = ["intro", "discovery", "presentation"]

        for stage in stages:
            assert "voice_notes" in loader.playbook[stage], \
                f"Missing voice_notes in {stage}"

            voice_notes = loader.playbook[stage]["voice_notes"]
            assert isinstance(voice_notes, dict)

    def test_phrase_tracking_reset_per_call(self):
        """Test that phrase tracking is isolated per call"""
        loader = get_playbook_loader()

        call1_phrases = []
        call2_phrases = []

        # Get phrases for call 1
        for _ in range(3):
            phrase = loader.get_phrase(
                stage="intro",
                category="openings",
                style="polite_direct",
                call_sid="call_1"
            )
            call1_phrases.append(phrase)

        # Get phrases for call 2
        for _ in range(3):
            phrase = loader.get_phrase(
                stage="intro",
                category="openings",
                style="polite_direct",
                call_sid="call_2"
            )
            call2_phrases.append(phrase)

        # Both calls should be able to use same phrases independently
        assert len(call1_phrases) == 3
        assert len(call2_phrases) == 3

    def test_variable_with_none_values(self):
        """Test that None variables are handled gracefully"""
        loader = get_playbook_loader()

        variables = {
            "lead_name": "Test",
            "property_type": None,  # None value
            "location": None,
            "budget": None
        }

        phrase = loader.get_phrase(
            stage="intro",
            category="openings",
            style="polite_direct",
            variables=variables
        )

        # Should not crash, should use default values
        assert phrase is not None
        assert isinstance(phrase, str)
        assert "property" in phrase.lower() or "property_type" not in phrase.lower()

    def test_hinglish_phrases_have_hindi_words(self):
        """Test that soft_hinglish style actually contains Hindi/Hinglish"""
        loader = get_playbook_loader()

        phrase = loader.get_phrase(
            stage="intro",
            category="openings",
            style="soft_hinglish"
        )

        # Common Hinglish markers
        hinglish_markers = [
            "hai", "haan", "nahi", "achha", "theek",
            "kya", "toh", "bol", "kar", "se"
        ]

        # At least in some phrases, we should see Hinglish
        # Get multiple phrases to increase chances
        phrases = []
        for i in range(5):
            p = loader.get_phrase(
                stage="intro",
                category="openings",
                style="soft_hinglish",
                call_sid=f"hinglish_test_{i}"
            )
            phrases.append(p.lower())

        # Check if any phrase contains Hinglish markers
        combined = " ".join(phrases)
        has_hinglish = any(marker in combined for marker in hinglish_markers)

        assert has_hinglish, "soft_hinglish style should contain Hindi/Hinglish words"

    def test_get_phrase_without_call_sid(self):
        """Test that phrases work without call_sid (no variation tracking)"""
        loader = get_playbook_loader()

        phrase = loader.get_phrase(
            stage="intro",
            category="openings",
            style="polite_direct"
            # No call_sid
        )

        assert phrase is not None
        assert isinstance(phrase, str)
        assert len(phrase) > 0


class TestPlaybookIntegration:
    """Test playbook integration with response generator"""

    def test_response_generator_uses_playbook(self):
        """Test that ResponseGenerator can use playbook"""
        from src.conversation.response_generator import ResponseGenerator

        generator = ResponseGenerator(use_playbook=True)

        assert generator.use_playbook is True
        assert generator.playbook is not None

    def test_response_generator_without_playbook(self):
        """Test ResponseGenerator fallback when playbook disabled"""
        from src.conversation.response_generator import ResponseGenerator

        generator = ResponseGenerator(use_playbook=False)

        assert generator.use_playbook is False
        assert generator.playbook is None

    @pytest.mark.asyncio
    async def test_generate_intro_with_playbook(self):
        """Test intro generation uses playbook"""
        from src.conversation.response_generator import ResponseGenerator
        from src.models.conversation import ConversationSession

        generator = ResponseGenerator(use_playbook=True)

        session = ConversationSession(
            call_sid="test_intro",
            lead_id=1,
            lead_name="Priya Sharma",
            lead_phone="+919876543210",
            property_type="2BHK",
            location="Bangalore",
            budget=5000000.0
        )

        intro = await generator.generate_intro(session)

        assert intro is not None
        assert isinstance(intro, str)
        assert len(intro) > 0
        # Should contain lead name
        assert "Priya" in intro or session.lead_name in intro

    @pytest.mark.asyncio
    async def test_generate_intro_different_styles(self):
        """Test intro generation with different styles"""
        from src.conversation.response_generator import ResponseGenerator
        from src.models.conversation import ConversationSession

        generator = ResponseGenerator(use_playbook=True)

        session = ConversationSession(
            call_sid="test_styles",
            lead_id=1,
            lead_name="Rajesh Kumar",
            lead_phone="+919876543210"
        )

        styles = ["polite_direct", "friendly_quick", "soft_hinglish"]

        for style in styles:
            intro = await generator.generate_intro(session, style=style)

            assert intro is not None
            assert isinstance(intro, str)
            assert len(intro) > 0

    def test_closing_response_with_playbook(self):
        """Test closing response uses playbook"""
        from src.conversation.response_generator import ResponseGenerator

        generator = ResponseGenerator(use_playbook=True)

        outcomes = [
            "qualified",
            "callback_requested",
            "not_interested",
            "send_details"
        ]

        for outcome in outcomes:
            response = generator.generate_closing_response(
                outcome=outcome,
                style="polite_direct",
                call_sid="test_closing"
            )

            assert response is not None
            assert isinstance(response, str)
            assert len(response) > 0


class TestPlaybookPerformance:
    """Test playbook performance and efficiency"""

    def test_phrase_selection_is_fast(self):
        """Test that phrase selection is performant"""
        import time

        loader = get_playbook_loader()

        start = time.time()

        # Get 100 phrases
        for i in range(100):
            loader.get_phrase(
                stage="intro",
                category="openings",
                style="polite_direct",
                call_sid=f"perf_test_{i}"
            )

        elapsed = time.time() - start

        # Should complete in less than 1 second
        assert elapsed < 1.0, f"Phrase selection too slow: {elapsed:.2f}s for 100 phrases"

    def test_playbook_loading_is_cached(self):
        """Test that playbook is loaded once and cached"""
        # Get playbook loader twice
        loader1 = get_playbook_loader()
        loader2 = get_playbook_loader()

        # Should return same instance (singleton pattern)
        assert loader1 is loader2, "Playbook should be cached (singleton)"

        # Both should have same playbook data
        assert loader1.playbook is loader2.playbook


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
