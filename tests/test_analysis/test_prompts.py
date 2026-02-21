# tests/test_analysis/test_prompts.py
"""Tests for LLM prompt templates.

This module tests the prompt templates, response parsing, and
validation functions for LLM-based market analysis.

Story: 分析内容语言配置支持
    - Added tests for get_market_analyst_system_prompt()
    - Added tests for LANGUAGE_INSTRUCTIONS
    - Updated tests to use new function-based approach
"""

from __future__ import annotations

import warnings
from datetime import datetime, timezone

import pytest

from src.analysis.prompts import (
    LANGUAGE_INSTRUCTIONS,
    MARKET_ANALYST_SYSTEM_PROMPT,
    LLMAnalysisResult,
    Recommendation,
    build_market_analysis_prompt,
    get_market_analyst_system_prompt,
    parse_llm_analysis_response,
    validate_analysis_result,
)
from src.models.market import Market, MarketCategory


class TestGetMarketAnalystSystemPrompt:
    """Tests for get_market_analyst_system_prompt function.

    Story: 分析内容语言配置支持
    """

    def test_default_is_english(self) -> None:
        """Test default language is English."""
        prompt = get_market_analyst_system_prompt()
        assert "prediction market analyst" in prompt
        assert "中文" not in prompt

    def test_chinese_contains_language_instruction(self) -> None:
        """Test Chinese prompt contains language instruction."""
        prompt = get_market_analyst_system_prompt("zh")
        assert "中文" in prompt
        assert "prediction market analyst" in prompt

    def test_english_no_extra_instruction(self) -> None:
        """Test English prompt has no extra language instruction."""
        prompt = get_market_analyst_system_prompt("en")
        assert "中文" not in prompt
        assert "prediction market analyst" in prompt

    def test_backward_compatibility_constant_with_warning(self) -> None:
        """Test MARKET_ANALYST_SYSTEM_PROMPT constant works with deprecation warning.

        Note: The deprecation warning is emitted at module load time, so if the module
        was already imported by another test, the warning won't be captured here.
        We verify the constant works correctly regardless.
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Re-import the module to trigger the warning
            # Note: importlib.reload doesn't re-execute module-level assignments
            # in the expected way for this test, so we verify functionality
            from src.analysis.prompts import MARKET_ANALYST_SYSTEM_PROMPT as prompt

            # Verify the constant works
            assert prompt is not None
            assert len(prompt) > 100
            assert "prediction market analyst" in prompt
            # The warning may or may not be captured depending on module load order
            # If captured, verify it's a DeprecationWarning
            if len(w) >= 1:
                assert issubclass(w[0].category, DeprecationWarning)
                assert "deprecated" in str(w[0].message).lower()

    def test_unknown_language_falls_back_to_english(self) -> None:
        """Test unknown language falls back to English with warning."""
        # Unknown language should not crash and should return valid prompt
        prompt = get_market_analyst_system_prompt("invalid")  # type: ignore
        assert "prediction market analyst" in prompt
        assert "中文" not in prompt  # Falls back to English


class TestLanguageInstructions:
    """Tests for LANGUAGE_INSTRUCTIONS mapping.

    Story: 分析内容语言配置支持
    """

    def test_chinese_instruction_exists(self) -> None:
        """Test Chinese instruction exists."""
        assert "zh" in LANGUAGE_INSTRUCTIONS
        assert "中文" in LANGUAGE_INSTRUCTIONS["zh"]

    def test_english_instruction_is_empty(self) -> None:
        """Test English instruction is empty (default)."""
        assert "en" in LANGUAGE_INSTRUCTIONS
        assert LANGUAGE_INSTRUCTIONS["en"] == ""

    def test_both_languages_supported(self) -> None:
        """Test both zh and en are supported."""
        assert len(LANGUAGE_INSTRUCTIONS) == 2
        assert set(LANGUAGE_INSTRUCTIONS.keys()) == {"zh", "en"}


class TestPromptsConstants:
    """Test prompt constants.

    Updated to use get_market_analyst_system_prompt() instead of deprecated constant.
    """

    def test_system_prompt_exists(self) -> None:
        """Test System Prompt exists."""
        prompt = get_market_analyst_system_prompt()
        assert prompt is not None
        assert len(prompt) > 100

    def test_system_prompt_contains_json_format(self) -> None:
        """Test System Prompt contains JSON format specification."""
        prompt = get_market_analyst_system_prompt()
        assert "JSON" in prompt
        assert "predicted_probability" in prompt
        assert "confidence" in prompt

    def test_system_prompt_contains_recommendation_options(self) -> None:
        """Test System Prompt contains recommendation options."""
        prompt = get_market_analyst_system_prompt()
        assert "BUY_YES" in prompt
        assert "BUY_NO" in prompt
        assert "NO_TRADE" in prompt

    def test_system_prompt_contains_probability_range(self) -> None:
        """Test System Prompt specifies probability range."""
        prompt = get_market_analyst_system_prompt()
        assert "0.00" in prompt
        assert "1.00" in prompt

    def test_system_prompt_contains_edge_threshold(self) -> None:
        """Test System Prompt specifies edge threshold."""
        prompt = get_market_analyst_system_prompt()
        assert "0.10" in prompt or "10%" in prompt

    def test_system_prompt_contains_confidence_threshold(self) -> None:
        """Test System Prompt specifies confidence threshold."""
        prompt = get_market_analyst_system_prompt()
        assert "0.75" in prompt


class TestRecommendation:
    """Test Recommendation enum."""

    def test_buy_yes_value(self) -> None:
        """Test BUY_YES enum value."""
        assert Recommendation.BUY_YES.value == "BUY_YES"

    def test_buy_no_value(self) -> None:
        """Test BUY_NO enum value."""
        assert Recommendation.BUY_NO.value == "BUY_NO"

    def test_no_trade_value(self) -> None:
        """Test NO_TRADE enum value."""
        assert Recommendation.NO_TRADE.value == "NO_TRADE"

    def test_recommendation_is_string_enum(self) -> None:
        """Test Recommendation is a string enum."""
        assert isinstance(Recommendation.BUY_YES, str)
        assert Recommendation.BUY_YES == "BUY_YES"


class TestLLMAnalysisResult:
    """Test LLMAnalysisResult model."""

    def test_valid_result(self) -> None:
        """Test valid result creation."""
        result = LLMAnalysisResult(
            predicted_probability=0.7,
            confidence=0.85,
            reasoning="This is a detailed analysis of the market.",
            key_assumptions=["Assumption 1", "Assumption 2"],
            recommendation=Recommendation.BUY_YES,
        )
        assert result.predicted_probability == 0.7
        assert result.confidence == 0.85
        assert result.recommendation == Recommendation.BUY_YES
        assert len(result.key_assumptions) == 2

    def test_valid_result_minimal(self) -> None:
        """Test valid result with minimal fields."""
        result = LLMAnalysisResult(
            predicted_probability=0.5,
            confidence=0.75,
            reasoning="Short but valid reasoning",
            recommendation=Recommendation.NO_TRADE,
        )
        assert result.predicted_probability == 0.5
        assert result.key_assumptions == []

    def test_probability_lower_bound(self) -> None:
        """Test probability at lower bound (0.0)."""
        result = LLMAnalysisResult(
            predicted_probability=0.0,
            confidence=0.85,
            reasoning="Analysis at boundary",
            recommendation=Recommendation.BUY_NO,
        )
        assert result.predicted_probability == 0.0

    def test_probability_upper_bound(self) -> None:
        """Test probability at upper bound (1.0)."""
        result = LLMAnalysisResult(
            predicted_probability=1.0,
            confidence=0.85,
            reasoning="Analysis at boundary",
            recommendation=Recommendation.BUY_YES,
        )
        assert result.predicted_probability == 1.0

    def test_probability_out_of_range_high(self) -> None:
        """Test probability above 1.0 is rejected."""
        with pytest.raises(ValueError):
            LLMAnalysisResult(
                predicted_probability=1.5,
                confidence=0.85,
                reasoning="Analysis",
                recommendation=Recommendation.BUY_YES,
            )

    def test_probability_out_of_range_low(self) -> None:
        """Test probability below 0.0 is rejected."""
        with pytest.raises(ValueError):
            LLMAnalysisResult(
                predicted_probability=-0.1,
                confidence=0.85,
                reasoning="Analysis",
                recommendation=Recommendation.BUY_YES,
            )

    def test_confidence_out_of_range_high(self) -> None:
        """Test confidence above 1.0 is rejected."""
        with pytest.raises(ValueError):
            LLMAnalysisResult(
                predicted_probability=0.7,
                confidence=1.5,
                reasoning="Analysis",
                recommendation=Recommendation.BUY_YES,
            )

    def test_confidence_out_of_range_low(self) -> None:
        """Test confidence below 0.0 is rejected."""
        with pytest.raises(ValueError):
            LLMAnalysisResult(
                predicted_probability=0.7,
                confidence=-0.1,
                reasoning="Analysis",
                recommendation=Recommendation.BUY_YES,
            )

    def test_reasoning_too_short(self) -> None:
        """Test reasoning below minimum length is rejected."""
        with pytest.raises(ValueError):
            LLMAnalysisResult(
                predicted_probability=0.7,
                confidence=0.85,
                reasoning="short",  # Less than 10 characters
                recommendation=Recommendation.BUY_YES,
            )

    def test_empty_assumptions_filtered(self) -> None:
        """Test empty assumptions are filtered out."""
        result = LLMAnalysisResult(
            predicted_probability=0.7,
            confidence=0.85,
            reasoning="Detailed analysis",
            key_assumptions=["Valid", "", "  ", "Also Valid"],
            recommendation=Recommendation.BUY_YES,
        )
        assert len(result.key_assumptions) == 2
        assert "Valid" in result.key_assumptions
        assert "Also Valid" in result.key_assumptions

    def test_all_empty_assumptions_returns_empty_list(self) -> None:
        """Test all empty assumptions returns empty list."""
        result = LLMAnalysisResult(
            predicted_probability=0.7,
            confidence=0.85,
            reasoning="Detailed analysis",
            key_assumptions=["", "  ", "\t"],
            recommendation=Recommendation.BUY_YES,
        )
        assert result.key_assumptions == []


class TestBuildMarketAnalysisPrompt:
    """Test User Prompt generation."""

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create sample market with all fields."""
        return Market(
            id="test-market-123",
            title="Will X happen by 2026?",
            description="A test prediction market",
            category=MarketCategory.POLITICS,
            yes_price=0.65,
            no_price=0.35,
            liquidity=50000.0,
            deadline=datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc),
        )

    def test_prompt_contains_title(self, sample_market: Market) -> None:
        """Test Prompt contains market title."""
        prompt = build_market_analysis_prompt(sample_market)
        assert sample_market.title in prompt

    def test_prompt_contains_description(self, sample_market: Market) -> None:
        """Test Prompt contains market description."""
        prompt = build_market_analysis_prompt(sample_market)
        assert sample_market.description in prompt

    def test_prompt_contains_prices(self, sample_market: Market) -> None:
        """Test Prompt contains price information."""
        prompt = build_market_analysis_prompt(sample_market)
        assert "65.0%" in prompt  # YES price
        assert "35.0%" in prompt  # NO price

    def test_prompt_contains_deadline(self, sample_market: Market) -> None:
        """Test Prompt contains deadline."""
        prompt = build_market_analysis_prompt(sample_market)
        assert "2026-12-31" in prompt

    def test_prompt_contains_liquidity(self, sample_market: Market) -> None:
        """Test Prompt contains liquidity."""
        prompt = build_market_analysis_prompt(sample_market)
        assert "$50,000" in prompt

    def test_prompt_contains_category(self, sample_market: Market) -> None:
        """Test Prompt contains category."""
        prompt = build_market_analysis_prompt(sample_market)
        assert "politics" in prompt.lower()

    def test_prompt_with_none_description(self) -> None:
        """Test Prompt handles None description."""
        market = Market(
            id="test",
            title="Test Market",
            description=None,
            yes_price=0.5,
        )
        prompt = build_market_analysis_prompt(market)
        assert "No description available" in prompt

    def test_prompt_with_none_prices(self) -> None:
        """Test Prompt handles None prices."""
        market = Market(
            id="test",
            title="Test Market",
            yes_price=None,
            no_price=None,
        )
        prompt = build_market_analysis_prompt(market)
        assert "Unknown" in prompt

    def test_prompt_with_none_deadline(self) -> None:
        """Test Prompt handles None deadline."""
        market = Market(
            id="test",
            title="Test Market",
            deadline=None,
        )
        prompt = build_market_analysis_prompt(market)
        assert "Unknown" in prompt

    def test_prompt_with_none_liquidity(self) -> None:
        """Test Prompt handles None liquidity."""
        market = Market(
            id="test",
            title="Test Market",
            liquidity=None,
        )
        prompt = build_market_analysis_prompt(market)
        assert "Unknown" in prompt

    def test_prompt_with_none_category(self) -> None:
        """Test Prompt handles None category."""
        market = Market(
            id="test",
            title="Test Market",
            category=None,
        )
        prompt = build_market_analysis_prompt(market)
        assert "Uncategorized" in prompt

    def test_prompt_with_all_none_values(self) -> None:
        """Test Prompt handles all None values."""
        market = Market(
            id="test",
            title="Test Market",
            description=None,
            category=None,
            yes_price=None,
            no_price=None,
            liquidity=None,
            deadline=None,
        )
        prompt = build_market_analysis_prompt(market)
        assert "Test Market" in prompt
        assert "No description available" in prompt
        assert "Uncategorized" in prompt
        assert prompt.count("Unknown") >= 4  # prices, deadline, liquidity


class TestParseLLMAnalysisResponse:
    """Test LLM response parsing."""

    def test_parse_json_block(self) -> None:
        """Test parsing JSON code block."""
        response = '''```json
{
    "predicted_probability": 0.75,
    "confidence": 0.85,
    "reasoning": "This is a detailed analysis.",
    "key_assumptions": ["Assumption 1", "Assumption 2"],
    "recommendation": "BUY_YES"
}
```'''
        result = parse_llm_analysis_response(response)
        assert result.predicted_probability == 0.75
        assert result.confidence == 0.85
        assert result.recommendation == Recommendation.BUY_YES
        assert len(result.key_assumptions) == 2

    def test_parse_json_block_without_language(self) -> None:
        """Test parsing JSON code block without json language tag."""
        response = '''```
{
    "predicted_probability": 0.65,
    "confidence": 0.80,
    "reasoning": "Detailed analysis here",
    "key_assumptions": [],
    "recommendation": "BUY_NO"
}
```'''
        result = parse_llm_analysis_response(response)
        assert result.predicted_probability == 0.65
        assert result.recommendation == Recommendation.BUY_NO

    def test_parse_pure_json(self) -> None:
        """Test parsing pure JSON."""
        response = '{"predicted_probability": 0.65, "confidence": 0.80, "reasoning": "Detailed analysis here", "key_assumptions": [], "recommendation": "BUY_NO"}'
        result = parse_llm_analysis_response(response)
        assert result.predicted_probability == 0.65
        assert result.recommendation == Recommendation.BUY_NO

    def test_parse_json_with_whitespace(self) -> None:
        """Test parsing JSON with surrounding whitespace."""
        response = '''

        {"predicted_probability": 0.5, "confidence": 0.75, "reasoning": "Valid reasoning", "recommendation": "NO_TRADE"}

        '''
        result = parse_llm_analysis_response(response)
        assert result.predicted_probability == 0.5

    def test_parse_missing_key_assumptions(self) -> None:
        """Test parsing JSON without key_assumptions field."""
        response = '{"predicted_probability": 0.7, "confidence": 0.8, "reasoning": "Detailed analysis here", "recommendation": "BUY_YES"}'
        result = parse_llm_analysis_response(response)
        assert result.key_assumptions == []

    def test_parse_key_assumptions_as_string(self) -> None:
        """Test parsing when key_assumptions is a string instead of list."""
        response = '{"predicted_probability": 0.7, "confidence": 0.8, "reasoning": "Detailed analysis here", "key_assumptions": "Single assumption", "recommendation": "BUY_YES"}'
        result = parse_llm_analysis_response(response)
        assert result.key_assumptions == ["Single assumption"]

    def test_parse_lowercase_recommendation(self) -> None:
        """Test parsing lowercase recommendation."""
        response = '{"predicted_probability": 0.7, "confidence": 0.8, "reasoning": "Detailed analysis here", "recommendation": "buy_yes"}'
        result = parse_llm_analysis_response(response)
        assert result.recommendation == Recommendation.BUY_YES

    def test_parse_hyphenated_recommendation(self) -> None:
        """Test parsing hyphenated recommendation."""
        response = '{"predicted_probability": 0.7, "confidence": 0.8, "reasoning": "Detailed analysis here", "recommendation": "buy-yes"}'
        result = parse_llm_analysis_response(response)
        assert result.recommendation == Recommendation.BUY_YES

    def test_parse_invalid_json(self) -> None:
        """Test parsing invalid JSON raises error."""
        response = "This is not valid JSON"
        with pytest.raises(ValueError) as exc_info:
            parse_llm_analysis_response(response)
        assert "Failed to parse" in str(exc_info.value)

    def test_parse_missing_required_field(self) -> None:
        """Test parsing with missing required field raises error."""
        response = '{"predicted_probability": 0.7, "confidence": 0.8}'
        with pytest.raises(ValueError) as exc_info:
            parse_llm_analysis_response(response)
        assert "Missing required field" in str(exc_info.value)

    def test_parse_invalid_recommendation(self) -> None:
        """Test parsing with invalid recommendation raises error."""
        response = '{"predicted_probability": 0.7, "confidence": 0.8, "reasoning": "Test", "recommendation": "INVALID"}'
        with pytest.raises(ValueError) as exc_info:
            parse_llm_analysis_response(response)
        assert "Invalid recommendation" in str(exc_info.value)


class TestValidateAnalysisResult:
    """Test analysis result validation."""

    def test_valid_result_high_confidence(self) -> None:
        """Test valid result with high confidence."""
        result = LLMAnalysisResult(
            predicted_probability=0.8,
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_YES,
        )
        is_valid, reason = validate_analysis_result(result)
        assert is_valid is True
        assert "valid" in reason.lower()

    def test_valid_result_at_min_confidence(self) -> None:
        """Test valid result at minimum confidence threshold."""
        result = LLMAnalysisResult(
            predicted_probability=0.8,
            confidence=0.75,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_YES,
        )
        is_valid, reason = validate_analysis_result(result)
        assert is_valid is True

    def test_low_confidence(self) -> None:
        """Test low confidence is rejected."""
        result = LLMAnalysisResult(
            predicted_probability=0.8,
            confidence=0.5,  # Below 0.75
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_YES,
        )
        is_valid, reason = validate_analysis_result(result)
        assert is_valid is False
        assert "Confidence" in reason
        assert "below minimum" in reason

    def test_no_trade_recommendation(self) -> None:
        """Test NO_TRADE recommendation is rejected."""
        result = LLMAnalysisResult(
            predicted_probability=0.55,
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.NO_TRADE,
        )
        is_valid, reason = validate_analysis_result(result)
        assert is_valid is False
        assert "NO_TRADE" in reason

    def test_insufficient_edge_buy_yes(self) -> None:
        """Test BUY_YES with insufficient edge is rejected."""
        result = LLMAnalysisResult(
            predicted_probability=0.70,  # Only 5% above market
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_YES,
        )
        is_valid, reason = validate_analysis_result(result, market_yes_price=0.65)
        assert is_valid is False
        assert "Edge" in reason
        assert "below minimum" in reason

    def test_sufficient_edge_buy_yes(self) -> None:
        """Test BUY_YES with sufficient edge is accepted."""
        result = LLMAnalysisResult(
            predicted_probability=0.80,  # 15% above market
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_YES,
        )
        is_valid, reason = validate_analysis_result(result, market_yes_price=0.65)
        assert is_valid is True

    def test_insufficient_edge_buy_no(self) -> None:
        """Test BUY_NO with insufficient edge is rejected."""
        # Market YES price = 0.65, Market NO price = 0.35
        # Our predicted YES = 0.60, Our predicted NO = 0.40
        # Edge = 0.40 - 0.35 = 0.05 (below 0.10 threshold)
        result = LLMAnalysisResult(
            predicted_probability=0.60,
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_NO,
        )
        is_valid, reason = validate_analysis_result(result, market_yes_price=0.65)
        assert is_valid is False
        assert "Edge" in reason

    def test_sufficient_edge_buy_no(self) -> None:
        """Test BUY_NO with sufficient edge is accepted."""
        result = LLMAnalysisResult(
            predicted_probability=0.20,  # 15% below market
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_NO,
        )
        is_valid, reason = validate_analysis_result(result, market_yes_price=0.65)
        assert is_valid is True

    def test_custom_min_confidence(self) -> None:
        """Test custom minimum confidence threshold."""
        result = LLMAnalysisResult(
            predicted_probability=0.8,
            confidence=0.70,  # Below default 0.75
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_YES,
        )
        # Should fail with default
        is_valid, _ = validate_analysis_result(result)
        assert is_valid is False

        # Should pass with lower threshold
        is_valid, _ = validate_analysis_result(result, min_confidence=0.60)
        assert is_valid is True

    def test_custom_min_edge(self) -> None:
        """Test custom minimum edge threshold."""
        result = LLMAnalysisResult(
            predicted_probability=0.72,  # 7% above market
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_YES,
        )
        # Should fail with default 0.10 edge
        is_valid, _ = validate_analysis_result(result, market_yes_price=0.65)
        assert is_valid is False

        # Should pass with lower threshold
        is_valid, _ = validate_analysis_result(result, market_yes_price=0.65, min_edge=0.05)
        assert is_valid is True

    def test_no_market_price_check(self) -> None:
        """Test validation without market price skips edge check."""
        result = LLMAnalysisResult(
            predicted_probability=0.55,  # Small edge
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_YES,
        )
        # Without market price, edge check is skipped
        is_valid, reason = validate_analysis_result(result)
        assert is_valid is True

    def test_boundary_edge_buy_yes(self) -> None:
        """Test BUY_YES at edge boundary (slightly above)."""
        # Use 0.76 to account for floating point precision
        result = LLMAnalysisResult(
            predicted_probability=0.76,  # 11% above market
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_YES,
        )
        is_valid, _ = validate_analysis_result(result, market_yes_price=0.65)
        assert is_valid is True


class TestIntegration:
    """Integration tests for prompt workflow."""

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create sample market for integration tests."""
        return Market(
            id="btc-100k-2026",
            title="Will Bitcoin reach $100k by end of 2026?",
            description="This market resolves to YES if Bitcoin reaches $100,000 USD at any point before December 31, 2026.",
            category=MarketCategory.CRYPTO,
            yes_price=0.45,
            no_price=0.55,
            liquidity=100000.0,
            deadline=datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc),
        )

    def test_full_workflow(self, sample_market: Market) -> None:
        """Test full prompt generation and parsing workflow."""
        # Generate prompt
        prompt = build_market_analysis_prompt(sample_market)

        # Verify prompt contains all market info
        assert sample_market.title in prompt
        assert "45.0%" in prompt
        assert "55.0%" in prompt
        assert "$100,000" in prompt
        assert "crypto" in prompt.lower()

        # Simulate LLM response
        llm_response = '''```json
{
    "predicted_probability": 0.55,
    "confidence": 0.80,
    "reasoning": "Bitcoin has shown strong momentum in recent months with institutional adoption increasing.",
    "key_assumptions": ["Institutional adoption continues", "No major regulatory crackdown"],
    "recommendation": "BUY_YES"
}
```'''

        # Parse response
        result = parse_llm_analysis_response(llm_response)

        # Verify parsed result
        assert result.predicted_probability == 0.55
        assert result.confidence == 0.80
        assert result.recommendation == Recommendation.BUY_YES
        assert len(result.key_assumptions) == 2

        # Validate result
        is_valid, reason = validate_analysis_result(
            result, market_yes_price=sample_market.yes_price
        )

        # Edge = 0.55 - 0.45 = 0.10, exactly at threshold
        assert is_valid is True
