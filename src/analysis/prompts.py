# src/analysis/prompts.py
"""LLM prompt templates for market analysis.

This module provides structured prompt templates for the LLM
to analyze prediction markets and output standardized results.

Usage:
    from src.analysis import (
        get_market_analyst_system_prompt,
        build_market_analysis_prompt,
        parse_llm_analysis_response,
        LLMAnalysisResult,
    )

    # Build prompt
    user_prompt = build_market_analysis_prompt(market)

    # Get LLM response
    with LLMClient() as client:
        response = client.chat_with_system(
            system_prompt=get_market_analyst_system_prompt(language="zh"),
            user_prompt=user_prompt
        )

    # Parse response
    result = parse_llm_analysis_response(response)

Story: 分析内容语言配置支持
    - Added get_market_analyst_system_prompt() for dynamic language support
    - Added LanguageType and LANGUAGE_INSTRUCTIONS for language configuration
    - Deprecated MARKET_ANALYST_SYSTEM_PROMPT constant
"""

from __future__ import annotations

__all__ = [
    "MARKET_ANALYST_SYSTEM_PROMPT",
    "LanguageType",
    "LANGUAGE_INSTRUCTIONS",
    "get_market_analyst_system_prompt",
    "Recommendation",
    "LLMAnalysisResult",
    "build_market_analysis_prompt",
    "parse_llm_analysis_response",
    "validate_analysis_result",
]

import json
import logging
import re
import warnings
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from src.models.market import Market

_logger = logging.getLogger(__name__)


# Type alias for supported languages
LanguageType = Literal["zh", "en"]

# Language-specific instructions to append to system prompt
LANGUAGE_INSTRUCTIONS: dict[LanguageType, str] = {
    "zh": "\n\n**IMPORTANT: Please output all analysis content (reasoning and key_assumptions) in Chinese (中文).**",
    "en": "",  # English is the default, no additional instruction needed
}


class Recommendation(str, Enum):
    """Trading recommendation enumeration."""

    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    NO_TRADE = "NO_TRADE"


class LLMAnalysisResult(BaseModel):
    """LLM analysis result model.

    Represents the structured output from the LLM market analysis.

    Attributes:
        predicted_probability: Predicted probability for YES outcome (0-1)
        confidence: Confidence level in the analysis (0-1)
        reasoning: Detailed analysis reasoning
        key_assumptions: List of key assumptions underlying the analysis
        recommendation: Trading recommendation (BUY_YES, BUY_NO, NO_TRADE)

    Example:
        >>> result = LLMAnalysisResult(
        ...     predicted_probability=0.75,
        ...     confidence=0.85,
        ...     reasoning="Based on current trends...",
        ...     key_assumptions=["Economic conditions remain stable"],
        ...     recommendation=Recommendation.BUY_YES,
        ... )
    """

    predicted_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Predicted probability for YES outcome (0-1)"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence level in the analysis (0-1)"
    )
    reasoning: str = Field(
        ..., min_length=10, description="Detailed analysis reasoning"
    )
    key_assumptions: list[str] = Field(
        default_factory=list, description="Key assumptions underlying the analysis"
    )
    recommendation: Recommendation = Field(..., description="Trading recommendation")

    @field_validator("key_assumptions")
    @classmethod
    def validate_assumptions(cls, v: list[str]) -> list[str]:
        """Validate and clean key assumptions.

        Removes empty or whitespace-only assumptions.

        Args:
            v: List of assumption strings

        Returns:
            Cleaned list of non-empty assumptions
        """
        return [a.strip() for a in v if a.strip()]


def get_market_analyst_system_prompt(
    language: LanguageType = "en",
    research_summary: str | None = None
) -> str:
    """Get market analyst system prompt with language instruction.

    Args:
        language: Output language ("zh" for Chinese, "en" for English)
        research_summary: Optional web research summary to include in system prompt

    Returns:
        System prompt string with language instruction appended

    Example:
        >>> prompt = get_market_analyst_system_prompt("zh")
        >>> "中文" in prompt
        True
        >>> prompt = get_market_analyst_system_prompt("en", "Latest news: ...")
        >>> "Latest news" in prompt
        True
    """
    if language not in LANGUAGE_INSTRUCTIONS:
        _logger.warning(
            f"Unknown language '{language}', using default (English). "
            f"Supported languages: {list(LANGUAGE_INSTRUCTIONS.keys())}"
        )

    # Build research context section if provided
    research_context = ""
    if research_summary and research_summary.strip() and "No search results found" not in research_summary:
        research_context = f"""

**Latest Market Context from Web Research:**
{research_summary}

**IMPORTANT:** Use this latest market information to inform your analysis. The web research above contains the most recent news and developments related to this market. Incorporate this information into your probability estimate and reasoning.
"""

    base_prompt = f"""You are an expert prediction market analyst with deep knowledge of:
- Political events and elections
- Economic indicators and trends
- Technology and crypto markets
- Sports and entertainment outcomes
{research_context}
Your role is to analyze prediction markets and provide:
1. A probability estimate (0.00 to 1.00) for the YES outcome
2. A confidence level (0.00 to 1.00) in your analysis
3. A detailed reasoning explaining your estimate
4. Key assumptions underlying your analysis
5. A trading recommendation

**IMPORTANT OUTPUT FORMAT:**
You MUST respond with ONLY a valid JSON object in this exact format:
```json
{{
  "predicted_probability": 0.XX,
  "confidence": 0.XX,
  "reasoning": "Your detailed analysis...",
  "key_assumptions": ["Assumption 1", "Assumption 2", "Assumption 3"],
  "recommendation": "BUY_YES or BUY_NO or NO_TRADE"
}}
```

**Analysis Guidelines:**
- predicted_probability: Your estimate of YES outcome probability (0.00-1.00)
- confidence: How confident you are in your analysis (0.00-1.00)
- reasoning: Explain your analysis in detail (at least 100 words)
- key_assumptions: List 2-5 key assumptions that could change the outcome
- recommendation:
  - BUY_YES: If your probability > market price + 0.10 (10% edge)
  - BUY_NO: If (1 - your probability) > market price + 0.10 (10% edge)
  - NO_TRADE: If no significant edge exists or confidence is below 0.75

**Critical Rules:**
- Be objective and evidence-based
- Consider market efficiency and public information
- Acknowledge uncertainty in predictions
- Do NOT output anything outside the JSON structure
"""
    instruction = LANGUAGE_INSTRUCTIONS.get(language, "")
    return base_prompt + instruction


def _get_deprecated_constant() -> str:
    """Get deprecated MARKET_ANALYST_SYSTEM_PROMPT constant.

    Emits deprecation warning and returns English prompt for backward compatibility.
    """
    warnings.warn(
        "MARKET_ANALYST_SYSTEM_PROMPT is deprecated. "
        "Use get_market_analyst_system_prompt() instead.",
        DeprecationWarning,
        stacklevel=3,
    )
    return get_market_analyst_system_prompt("en")


# Backward compatibility - deprecated constant
MARKET_ANALYST_SYSTEM_PROMPT = _get_deprecated_constant()


def build_market_analysis_prompt(
    market: Market, research_context: str | None = None
) -> str:
    """Build market analysis User Prompt.

    Constructs a formatted prompt containing all relevant market information
    for the LLM to analyze.

    Args:
        market: Market data model containing title, description, prices, etc.
        research_context: Optional web research context to include in prompt

    Returns:
        Formatted User Prompt string for LLM analysis

    Example:
        >>> from src.models.market import Market
        >>> market = Market(
        ...     id="test-123",
        ...     title="Will X happen?",
        ...     yes_price=0.65,
        ... )
        >>> prompt = build_market_analysis_prompt(market)
        >>> "Will X happen?" in prompt
        True
    """
    # Format prices
    yes_price_str = _format_price(market.yes_price)
    no_price_str = _format_price(market.no_price)

    # Format deadline
    deadline_str = _format_deadline(market.deadline)

    # Format liquidity
    liquidity_str = _format_liquidity(market.liquidity)

    # Format category
    category_str = market.category.value if market.category else "Uncategorized"

    # Build base prompt
    prompt = f"""Analyze the following prediction market and provide your assessment:

**Market Title:** {market.title}

**Description:** {market.description or "No description available."}

**Category:** {category_str}

**Current Prices:**
- YES: {yes_price_str}
- NO: {no_price_str}

**Market Deadline:** {deadline_str}

**Liquidity:** {liquidity_str}
"""

    # Add research context if provided
    if research_context:
        prompt += f"""

**Additional Research Context:**
{research_context}

Please consider this research context in your analysis, but also apply your own judgment and expertise.
"""

    prompt += """

Based on your analysis, provide your probability estimate, confidence level, reasoning, key assumptions, and trading recommendation in the required JSON format.
"""

    return prompt


def _format_price(price: float | None) -> str:
    """Format price as percentage string.

    Args:
        price: Price value (0-1 range) or None

    Returns:
        Formatted percentage string (e.g., "65.0%") or "Unknown"
    """
    if price is None:
        return "Unknown"
    return f"{price * 100:.1f}%"


def _format_deadline(deadline: datetime | None) -> str:
    """Format deadline datetime.

    Args:
        deadline: Deadline datetime or None

    Returns:
        Formatted datetime string or "Unknown"
    """
    if deadline is None:
        return "Unknown"
    return deadline.strftime("%Y-%m-%d %H:%M UTC")


def _format_liquidity(liquidity: float | None) -> str:
    """Format liquidity value.

    Args:
        liquidity: Liquidity amount in USD or None

    Returns:
        Formatted currency string (e.g., "$50,000") or "Unknown"
    """
    if liquidity is None:
        return "Unknown"
    return f"${liquidity:,.0f}"


def parse_llm_analysis_response(response: str) -> LLMAnalysisResult:
    """Parse LLM response into LLMAnalysisResult.

    Extracts and parses JSON from the LLM response, handling both
    plain JSON and markdown code block formats.

    Args:
        response: Raw LLM response string

    Returns:
        Parsed LLMAnalysisResult model

    Raises:
        ValueError: If response cannot be parsed as valid JSON or
                   missing required fields or invalid values

    Example:
        >>> response = '''```json
        ... {"predicted_probability": 0.75, "confidence": 0.85,
        ...  "reasoning": "Analysis", "recommendation": "BUY_YES"}
        ... ```'''
        >>> result = parse_llm_analysis_response(response)
        >>> result.predicted_probability
        0.75
    """
    # Clean response
    cleaned = response.strip()

    # Try to extract JSON code block
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to parse entire response as JSON
        json_str = cleaned

    # Strip whitespace
    json_str = json_str.strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse LLM response as JSON: {e}\nResponse: {cleaned[:500]}"
        )

    # Validate required fields
    required_fields = [
        "predicted_probability",
        "confidence",
        "reasoning",
        "recommendation",
    ]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Handle recommendation case variations
    recommendation_str = data["recommendation"].upper().replace("-", "_")
    try:
        data["recommendation"] = Recommendation(recommendation_str)
    except ValueError:
        raise ValueError(f"Invalid recommendation value: {data['recommendation']}")

    # Ensure key_assumptions is a list
    if "key_assumptions" not in data:
        data["key_assumptions"] = []
    elif isinstance(data["key_assumptions"], str):
        data["key_assumptions"] = [data["key_assumptions"]]

    return LLMAnalysisResult(**data)


def validate_analysis_result(
    result: LLMAnalysisResult,
    min_confidence: float = 0.75,
    min_edge: float = 0.10,
    market_yes_price: float | None = None,
) -> tuple[bool, str]:
    """Validate analysis result meets trading criteria.

    Checks if the LLM analysis result satisfies the minimum confidence
    and edge requirements for executing a trade.

    Args:
        result: LLM analysis result to validate
        min_confidence: Minimum confidence threshold (default 0.75)
        min_edge: Minimum edge threshold (default 0.10)
        market_yes_price: Current market YES price for edge calculation

    Returns:
        Tuple of (is_valid, reason) where is_valid indicates if the result
        is suitable for trading and reason explains why if not

    Example:
        >>> result = LLMAnalysisResult(
        ...     predicted_probability=0.8,
        ...     confidence=0.85,
        ...     reasoning="Analysis",
        ...     recommendation=Recommendation.BUY_YES,
        ... )
        >>> is_valid, reason = validate_analysis_result(result)
        >>> is_valid
        True
    """
    # Check confidence threshold
    if result.confidence < min_confidence:
        return (
            False,
            f"Confidence {result.confidence:.2f} below minimum {min_confidence}",
        )

    # Check if NO_TRADE recommendation
    if result.recommendation == Recommendation.NO_TRADE:
        return False, "LLM recommends NO_TRADE"

    # Check edge if market price provided
    if market_yes_price is not None:
        if result.recommendation == Recommendation.BUY_YES:
            edge = result.predicted_probability - market_yes_price
            if edge < min_edge:
                return False, f"Edge {edge:.2f} below minimum {min_edge} for BUY_YES"
        elif result.recommendation == Recommendation.BUY_NO:
            edge = (1 - result.predicted_probability) - (1 - market_yes_price)
            if edge < min_edge:
                return False, f"Edge {edge:.2f} below minimum {min_edge} for BUY_NO"

    return True, "Analysis result is valid for trading"
