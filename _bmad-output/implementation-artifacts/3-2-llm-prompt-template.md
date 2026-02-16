# Story 3.2: LLM 提示词模板

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **开发者**,
I want **定义结构化的 LLM 提示词模板**,
So that **LLM 能够输出标准化的分析结果**.

## Acceptance Criteria

**Given** LLM 客户端已实现
**When** 实现 `src/analysis/prompts.py`
**Then** 创建市场分析提示词模板:
- System Prompt: 定义 LLM 为预测市场分析师角色
- User Prompt Template: 包含市场标题、描述、当前价格、截止日期
**And** 要求 LLM 输出 JSON 格式:
```json
{
  "predicted_probability": 0.xx,
  "confidence": 0.xx,
  "reasoning": "分析理由...",
  "key_assumptions": ["假设1", "假设2"],
  "recommendation": "BUY_YES / BUY_NO / NO_TRADE"
}
```
**And** 输出包含概率估算和置信度 (0-1 范围)

## Tasks / Subtasks

- [x] Task 1: 创建提示词模块基础结构 (AC: 1)
  - [x] 1.1 创建 `src/analysis/prompts.py` 文件
  - [x] 1.2 添加模块 docstring
  - [x] 1.3 导入必要模块 (Pydantic, json, datetime)
  - [x] 1.4 定义 `__all__` 导出列表

- [x] Task 2: 定义输出数据模型 (AC: 2)
  - [x] 2.1 创建 `LLMAnalysisResult` Pydantic 模型
  - [x] 2.2 定义 `predicted_probability: float` 字段 (0-1 范围)
  - [x] 2.3 定义 `confidence: float` 字段 (0-1 范围)
  - [x] 2.4 定义 `reasoning: str` 字段
  - [x] 2.5 定义 `key_assumptions: list[str]` 字段
  - [x] 2.6 定义 `recommendation: str` 字段 (枚举值)
  - [x] 2.7 添加 `Recommendation` 枚举类型
  - [x] 2.8 添加字段验证 (概率范围 0-1)

- [x] Task 3: 实现 System Prompt (AC: 1)
  - [x] 3.1 定义 `MARKET_ANALYST_SYSTEM_PROMPT` 常量
  - [x] 3.2 定义角色: 预测市场分析师
  - [x] 3.3 定义输出格式: JSON
  - [x] 3.4 定义分析维度: 概率、置信度、关键假设、建议
  - [x] 3.5 定义分析原则: 客观、基于证据

- [x] Task 4: 实现 User Prompt Template (AC: 1)
  - [x] 4.1 创建 `build_market_analysis_prompt()` 函数
  - [x] 4.2 接收参数: market (Market 模型)
  - [x] 4.3 包含市场标题
  - [x] 4.4 包含市场描述
  - [x] 4.5 包含当前价格 (YES/NO)
  - [x] 4.6 包含截止日期
  - [x] 4.7 包含流动性信息 (可选)
  - [x] 4.8 包含类别信息 (可选)

- [x] Task 5: 实现 JSON 解析器 (AC: 2)
  - [x] 5.1 创建 `parse_llm_analysis_response()` 函数
  - [x] 5.2 从 LLM 响应文本提取 JSON
  - [x] 5.3 处理 markdown 代码块格式 (```json ... ```)
  - [x] 5.4 处理纯 JSON 格式
  - [x] 5.5 解析为 `LLMAnalysisResult` 模型
  - [x] 5.6 处理解析错误和格式异常
  - [x] 5.7 验证概率和置信度范围

- [x] Task 6: 实现辅助函数 (AC: All)
  - [x] 6.1 创建 `validate_analysis_result()` 函数
  - [x] 6.2 验证置信度 >= MIN_CONFIDENCE (0.75)
  - [x] 6.3 验证 recommendation 值有效
  - [x] 6.4 创建 `_format_price()` 函数 (格式化价格为百分比)

- [x] Task 7: 更新模块导出 (AC: All)
  - [x] 7.1 更新 `src/analysis/__init__.py` 导出新类和函数
  - [x] 7.2 确保从 src.analysis 可以导入

- [x] Task 8: 编写测试 (AC: All)
  - [x] 8.1 创建 `tests/test_analysis/test_prompts.py`
  - [x] 8.2 测试 System Prompt 内容
  - [x] 8.3 测试 User Prompt 生成
  - [x] 8.4 测试 JSON 解析 (正确格式)
  - [x] 8.5 测试 JSON 解析 (markdown 代码块)
  - [x] 8.6 测试 JSON 解析 (错误格式)
  - [x] 8.7 测试 `LLMAnalysisResult` 模型验证
  - [x] 8.8 测试边界情况 (空字符串、无效 JSON、超出范围值)

- [x] Task 9: 代码质量检查 (AC: All)
  - [x] 9.1 运行 `mypy src/analysis/prompts.py` 无错误
  - [x] 9.2 运行 `black --check src/analysis/prompts.py` 通过
  - [x] 9.3 运行 `isort --check src/analysis/prompts.py` 通过
  - [x] 9.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#Core Dependencies]

**LLM 配置:**
- 使用 OpenAI 兼容协议连接 GLM API
- API Base: `https://open.bigmodel.cn/api/paas/v4`
- 默认模型: `glm-4`
- 超时: 30 秒 (NFR3)

**提示词设计原则:**
- 明确角色定义
- 结构化输出格式
- 包含分析维度
- 易于解析验证

### 已实现的相关模块 [Source: src/api/llm.py]

**Story 3.1 实现的 LLMClient:**

```python
from src.api import LLMClient

with LLMClient() as client:
    response = client.chat_with_system(
        system_prompt="You are a prediction market analyst.",
        user_prompt="Analyze this market: ..."
    )
```

**本故事需要提供:**
- `MARKET_ANALYST_SYSTEM_PROMPT` - System Prompt 常量
- `build_market_analysis_prompt(market)` - User Prompt 生成函数
- `parse_llm_analysis_response(response)` - 响应解析函数

### Market 模型 [Source: src/models/market.py]

**已存在的 Market 模型:**

```python
class Market(BaseModel):
    """市场数据模型."""

    id: str
    title: str
    description: str | None = None
    category: str | None = None
    yes_price: float | None = None
    no_price: float | None = None
    liquidity: float | None = None
    deadline: datetime | None = None
    resolution_status: str | None = None
    resolution_outcome: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

### 配置参数 [Source: src/config.py]

**已存在的风险控制配置:**

```python
class RiskSettings(BaseSettings):
    """Risk control settings."""

    model_config = SettingsConfigDict(env_prefix="RISK_")

    min_confidence: float = Field(
        default=0.75, ge=0.0, le=1.0, description="Minimum LLM confidence for trading"
    )
    min_edge: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Minimum edge vs market price"
    )
```

**使用方式:**
```python
from src.config import settings

min_confidence = settings.risk.min_confidence  # 0.75
min_edge = settings.risk.min_edge  # 0.10
```

### 实现模板

**prompts.py 完整模板:**

```python
# src/analysis/prompts.py
"""LLM prompt templates for market analysis.

This module provides structured prompt templates for the LLM
to analyze prediction markets and output standardized results.

Usage:
    from src.analysis import (
        MARKET_ANALYST_SYSTEM_PROMPT,
        build_market_analysis_prompt,
        parse_llm_analysis_response,
        LLMAnalysisResult,
    )

    # Build prompt
    user_prompt = build_market_analysis_prompt(market)

    # Get LLM response
    with LLMClient() as client:
        response = client.chat_with_system(
            system_prompt=MARKET_ANALYST_SYSTEM_PROMPT,
            user_prompt=user_prompt
        )

    # Parse response
    result = parse_llm_analysis_response(response)
"""

from __future__ import annotations

__all__ = [
    "MARKET_ANALYST_SYSTEM_PROMPT",
    "Recommendation",
    "LLMAnalysisResult",
    "build_market_analysis_prompt",
    "parse_llm_analysis_response",
    "validate_analysis_result",
]

import json
import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.models.market import Market


class Recommendation(str, Enum):
    """交易建议枚举."""

    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    NO_TRADE = "NO_TRADE"


class LLMAnalysisResult(BaseModel):
    """LLM 分析结果模型."""

    predicted_probability: float = Field(
        ..., ge=0.0, le=1.0, description="预测概率 (0-1)"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="置信度 (0-1)"
    )
    reasoning: str = Field(..., min_length=10, description="分析理由")
    key_assumptions: list[str] = Field(
        default_factory=list, description="关键假设列表"
    )
    recommendation: Recommendation = Field(..., description="交易建议")

    @field_validator("key_assumptions")
    @classmethod
    def validate_assumptions(cls, v: list[str]) -> list[str]:
        """验证关键假设不为空."""
        return [a.strip() for a in v if a.strip()]


MARKET_ANALYST_SYSTEM_PROMPT = """You are an expert prediction market analyst with deep knowledge of:
- Political events and elections
- Economic indicators and trends
- Technology and crypto markets
- Sports and entertainment outcomes

Your role is to analyze prediction markets and provide:
1. A probability estimate (0.00 to 1.00) for the YES outcome
2. A confidence level (0.00 to 1.00) in your analysis
3. A detailed reasoning explaining your estimate
4. Key assumptions underlying your analysis
5. A trading recommendation

**IMPORTANT OUTPUT FORMAT:**
You MUST respond with ONLY a valid JSON object in this exact format:
```json
{
  "predicted_probability": 0.XX,
  "confidence": 0.XX,
  "reasoning": "Your detailed analysis...",
  "key_assumptions": ["Assumption 1", "Assumption 2", "Assumption 3"],
  "recommendation": "BUY_YES or BUY_NO or NO_TRADE"
}
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


def build_market_analysis_prompt(market: Market) -> str:
    """构建市场分析 User Prompt.

    Args:
        market: 市场数据模型

    Returns:
        格式化的 User Prompt 字符串
    """
    # 格式化价格
    yes_price_str = _format_price(market.yes_price)
    no_price_str = _format_price(market.no_price)

    # 格式化截止日期
    deadline_str = _format_deadline(market.deadline)

    # 格式化流动性
    liquidity_str = _format_liquidity(market.liquidity)

    prompt = f"""Analyze the following prediction market and provide your assessment:

**Market Title:** {market.title}

**Description:** {market.description or "No description available."}

**Category:** {market.category or "Uncategorized"}

**Current Prices:**
- YES: {yes_price_str}
- NO: {no_price_str}

**Market Deadline:** {deadline_str}

**Liquidity:** {liquidity_str}

Based on your analysis, provide your probability estimate, confidence level, reasoning, key assumptions, and trading recommendation in the required JSON format.
"""
    return prompt


def _format_price(price: float | None) -> str:
    """格式化价格为百分比字符串."""
    if price is None:
        return "Unknown"
    return f"{price * 100:.1f}%"


def _format_deadline(deadline: datetime | None) -> str:
    """格式化截止日期."""
    if deadline is None:
        return "Unknown"
    return deadline.strftime("%Y-%m-%d %H:%M UTC")


def _format_liquidity(liquidity: float | None) -> str:
    """格式化流动性."""
    if liquidity is None:
        return "Unknown"
    return f"${liquidity:,.0f}"


def parse_llm_analysis_response(response: str) -> LLMAnalysisResult:
    """解析 LLM 响应为 LLMAnalysisResult.

    Args:
        response: LLM 返回的原始响应字符串

    Returns:
        解析后的 LLMAnalysisResult

    Raises:
        ValueError: 如果响应无法解析为有效的 JSON
    """
    # 清理响应
    cleaned = response.strip()

    # 尝试提取 JSON 代码块
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if json_match:
        json_str = json_match.group(1)
    else:
        # 尝试直接解析整个响应为 JSON
        json_str = cleaned

    # 去除可能的前后空白和字符
    json_str = json_str.strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}\nResponse: {cleaned[:500]}")

    # 验证必要字段
    required_fields = ["predicted_probability", "confidence", "reasoning", "recommendation"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # 处理 recommendation 大小写
    recommendation_str = data["recommendation"].upper().replace("-", "_")
    try:
        data["recommendation"] = Recommendation(recommendation_str)
    except ValueError:
        raise ValueError(f"Invalid recommendation value: {data['recommendation']}")

    # 确保 key_assumptions 是列表
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
    """验证分析结果是否满足交易条件.

    Args:
        result: LLM 分析结果
        min_confidence: 最小置信度阈值 (默认 0.75)
        min_edge: 最小 Edge 阈值 (默认 0.10)
        market_yes_price: 市场当前 YES 价格 (可选)

    Returns:
        (is_valid, reason): 是否有效及原因说明
    """
    # 检查置信度
    if result.confidence < min_confidence:
        return False, f"Confidence {result.confidence:.2f} below minimum {min_confidence}"

    # 检查是否为 NO_TRADE
    if result.recommendation == Recommendation.NO_TRADE:
        return False, "LLM recommends NO_TRADE"

    # 如果提供了市场价格，检查 Edge
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
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增文件:**
```
src/analysis/
├── __init__.py          # 更新: 导出 prompts 模块
├── market_filter.py     # 已存在 (Story 2.3)
└── prompts.py           # 新增: LLM 提示词模板

tests/test_analysis/
├── __init__.py          # 已存在
├── test_market_filter.py # 已存在
└── test_prompts.py      # 新增: 提示词模板测试
```

### 测试策略

```python
# tests/test_analysis/test_prompts.py
"""Tests for LLM prompt templates."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from src.analysis.prompts import (
    MARKET_ANALYST_SYSTEM_PROMPT,
    LLMAnalysisResult,
    Recommendation,
    build_market_analysis_prompt,
    parse_llm_analysis_response,
    validate_analysis_result,
)
from src.models.market import Market


class TestPromptsConstants:
    """测试提示词常量."""

    def test_system_prompt_exists(self) -> None:
        """测试 System Prompt 存在."""
        assert MARKET_ANALYST_SYSTEM_PROMPT is not None
        assert len(MARKET_ANALYST_SYSTEM_PROMPT) > 100

    def test_system_prompt_contains_json_format(self) -> None:
        """测试 System Prompt 包含 JSON 格式说明."""
        assert "JSON" in MARKET_ANALYST_SYSTEM_PROMPT
        assert "predicted_probability" in MARKET_ANALYST_SYSTEM_PROMPT
        assert "confidence" in MARKET_ANALYST_SYSTEM_PROMPT

    def test_system_prompt_contains_recommendation_options(self) -> None:
        """测试 System Prompt 包含建议选项."""
        assert "BUY_YES" in MARKET_ANALYST_SYSTEM_PROMPT
        assert "BUY_NO" in MARKET_ANALYST_SYSTEM_PROMPT
        assert "NO_TRADE" in MARKET_ANALYST_SYSTEM_PROMPT


class TestBuildMarketAnalysisPrompt:
    """测试 User Prompt 生成."""

    @pytest.fixture
    def sample_market(self) -> Market:
        """创建示例市场."""
        return Market(
            id="test-market-123",
            title="Will X happen by 2026?",
            description="A test prediction market",
            category="Politics",
            yes_price=0.65,
            no_price=0.35,
            liquidity=50000.0,
            deadline=datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc),
        )

    def test_prompt_contains_title(self, sample_market: Market) -> None:
        """测试 Prompt 包含市场标题."""
        prompt = build_market_analysis_prompt(sample_market)
        assert sample_market.title in prompt

    def test_prompt_contains_description(self, sample_market: Market) -> None:
        """测试 Prompt 包含市场描述."""
        prompt = build_market_analysis_prompt(sample_market)
        assert sample_market.description in prompt

    def test_prompt_contains_prices(self, sample_market: Market) -> None:
        """测试 Prompt 包含价格信息."""
        prompt = build_market_analysis_prompt(sample_market)
        assert "65.0%" in prompt  # YES price
        assert "35.0%" in prompt  # NO price

    def test_prompt_contains_deadline(self, sample_market: Market) -> None:
        """测试 Prompt 包含截止日期."""
        prompt = build_market_analysis_prompt(sample_market)
        assert "2026-12-31" in prompt

    def test_prompt_with_none_values(self) -> None:
        """测试 Prompt 处理 None 值."""
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
        assert "Unknown" in prompt


class TestLLMAnalysisResult:
    """测试 LLMAnalysisResult 模型."""

    def test_valid_result(self) -> None:
        """测试有效结果."""
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

    def test_probability_out_of_range(self) -> None:
        """测试概率超出范围."""
        with pytest.raises(ValueError):
            LLMAnalysisResult(
                predicted_probability=1.5,  # Invalid
                confidence=0.85,
                reasoning="Analysis",
                recommendation=Recommendation.BUY_YES,
            )

    def test_confidence_out_of_range(self) -> None:
        """测试置信度超出范围."""
        with pytest.raises(ValueError):
            LLMAnalysisResult(
                predicted_probability=0.7,
                confidence=-0.1,  # Invalid
                reasoning="Analysis",
                recommendation=Recommendation.BUY_YES,
            )

    def test_empty_assumptions_filtered(self) -> None:
        """测试空假设被过滤."""
        result = LLMAnalysisResult(
            predicted_probability=0.7,
            confidence=0.85,
            reasoning="Analysis",
            key_assumptions=["Valid", "", "  ", "Also Valid"],
            recommendation=Recommendation.BUY_YES,
        )
        assert len(result.key_assumptions) == 2


class TestParseLLMAnalysisResponse:
    """测试 LLM 响应解析."""

    def test_parse_json_block(self) -> None:
        """测试解析 JSON 代码块."""
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
        assert result.recommendation == Recommendation.BUY_YES

    def test_parse_pure_json(self) -> None:
        """测试解析纯 JSON."""
        response = '''{"predicted_probability": 0.65, "confidence": 0.80, "reasoning": "Analysis", "key_assumptions": [], "recommendation": "BUY_NO"}'''
        result = parse_llm_analysis_response(response)
        assert result.predicted_probability == 0.65
        assert result.recommendation == Recommendation.BUY_NO

    def test_parse_invalid_json(self) -> None:
        """测试解析无效 JSON."""
        response = "This is not valid JSON"
        with pytest.raises(ValueError):
            parse_llm_analysis_response(response)

    def test_parse_missing_field(self) -> None:
        """测试缺少必要字段."""
        response = '{"predicted_probability": 0.7, "confidence": 0.8}'
        with pytest.raises(ValueError):
            parse_llm_analysis_response(response)

    def test_parse_invalid_recommendation(self) -> None:
        """测试无效建议值."""
        response = '{"predicted_probability": 0.7, "confidence": 0.8, "reasoning": "Test", "recommendation": "INVALID"}'
        with pytest.raises(ValueError):
            parse_llm_analysis_response(response)


class TestValidateAnalysisResult:
    """测试分析结果验证."""

    def test_valid_result(self) -> None:
        """测试有效结果."""
        result = LLMAnalysisResult(
            predicted_probability=0.8,
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.BUY_YES,
        )
        is_valid, reason = validate_analysis_result(result)
        assert is_valid is True

    def test_low_confidence(self) -> None:
        """测试低置信度."""
        result = LLMAnalysisResult(
            predicted_probability=0.8,
            confidence=0.5,  # Below 0.75
            reasoning="Analysis",
            recommendation=Recommendation.BUY_YES,
        )
        is_valid, reason = validate_analysis_result(result)
        assert is_valid is False
        assert "Confidence" in reason

    def test_no_trade_recommendation(self) -> None:
        """测试 NO_TRADE 建议."""
        result = LLMAnalysisResult(
            predicted_probability=0.55,
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.NO_TRADE,
        )
        is_valid, reason = validate_analysis_result(result)
        assert is_valid is False
        assert "NO_TRADE" in reason

    def test_insufficient_edge_buy_yes(self) -> None:
        """测试 BUY_YES Edge 不足."""
        result = LLMAnalysisResult(
            predicted_probability=0.70,  # Only 5% above market
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.BUY_YES,
        )
        is_valid, reason = validate_analysis_result(result, market_yes_price=0.65)
        assert is_valid is False
        assert "Edge" in reason

    def test_sufficient_edge_buy_yes(self) -> None:
        """测试 BUY_YES Edge 充足."""
        result = LLMAnalysisResult(
            predicted_probability=0.80,  # 15% above market
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.BUY_YES,
        )
        is_valid, reason = validate_analysis_result(result, market_yes_price=0.65)
        assert is_valid is True
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (RiskSettings)
- Story 1.7: Pydantic 数据模型 (Market)
- Story 3.1: LLM API 客户端 (LLMClient)

**后续故事依赖本故事:**
- Story 3.3: LLM 分析引擎 (需要 prompts.py)
- Story 3.5: Edge 计算 (需要 LLMAnalysisResult)

### 实现注意事项

**关键点:**

1. **JSON 输出格式** - 必须要求 LLM 输出纯 JSON，便于解析
2. **Markdown 代码块** - LLM 可能返回 ` ```json ... ``` ` 格式，需要处理
3. **概率范围验证** - 0-1 范围，使用 Pydantic Field 验证
4. **置信度阈值** - 0.75，从配置读取
5. **Edge 阈值** - 0.10 (10%)，从配置读取
6. **Recommendation 枚举** - 三种值: BUY_YES, BUY_NO, NO_TRADE

**与 Story 3.1 的集成:**

```python
from src.api import LLMClient
from src.analysis import (
    MARKET_ANALYST_SYSTEM_PROMPT,
    build_market_analysis_prompt,
    parse_llm_analysis_response,
)

# 完整的 LLM 分析流程
def analyze_market(market: Market) -> LLMAnalysisResult:
    user_prompt = build_market_analysis_prompt(market)

    with LLMClient() as client:
        response = client.chat_with_system(
            system_prompt=MARKET_ANALYST_SYSTEM_PROMPT,
            user_prompt=user_prompt
        )

    return parse_llm_analysis_response(response)
```

### 前一个故事学习 [Source: 3-1-llm-api-client.md]

**从 Story 3.1 学到的模式:**

1. **使用 `from __future__ import annotations`** - 支持 Python 3.10+ 类型语法
2. **类型注解使用 `str | None`** - 而非 `Optional[str]`
3. **类型注解使用 `list[str]`** - 而非 `List[str]`
4. **Pydantic Field 验证** - 使用 `ge=0.0, le=1.0` 约束范围
5. **完整 docstring** - 包含 Args, Returns, Raises, Example
6. **单元测试覆盖** - 正常情况 + 边界情况 + 错误情况
7. **`__all__` 导出列表** - 明确模块公共 API

### References

- [Source: architecture.md#Core Dependencies] - LLM 技术栈
- [Source: architecture.md#Data Architecture] - 数据模型设计
- [Source: src/config.py] - RiskSettings 配置
- [Source: src/models/market.py] - Market 模型
- [Source: src/api/llm.py] - LLMClient 实现
- [Source: epics.md#Story 3.2] - 原始 Story 定义
- [Source: 3-1-llm-api-client.md] - 前一个故事参考

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A

### Completion Notes List

1. 所有 9 个任务及其子任务均已完成
2. 实现了 `src/analysis/prompts.py` 模块，包含:
   - `Recommendation` 枚举 (BUY_YES, BUY_NO, NO_TRADE)
   - `LLMAnalysisResult` Pydantic 模型 (带验证)
   - `MARKET_ANALYST_SYSTEM_PROMPT` 系统提示词
   - `build_market_analysis_prompt()` 用户提示词生成
   - `parse_llm_analysis_response()` JSON 解析
   - `validate_analysis_result()` 结果验证
3. 更新了 `src/analysis/__init__.py` 导出新模块
4. 创建了 57 个单元测试，全部通过
5. 代码质量检查全部通过 (mypy, black, isort)
6. 完整测试套件 538 个测试全部通过

### File List

**新增文件:**
- `/Users/nick/CascadeProjects/polymarket-trader/src/analysis/prompts.py` - LLM 提示词模板模块
- `/Users/nick/CascadeProjects/polymarket-trader/tests/test_analysis/test_prompts.py` - 提示词模板测试

**修改文件:**
- `/Users/nick/CascadeProjects/polymarket-trader/src/analysis/__init__.py` - 更新导出列表
- `/Users/nick/CascadeProjects/polymarket-trader/_bmad-output/implementation-artifacts/3-2-llm-prompt-template.md` - 更新任务状态
