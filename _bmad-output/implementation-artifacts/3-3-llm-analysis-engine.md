# Story 3.3: LLM 分析引擎

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **用户**,
I want **系统能够使用 LLM 分析市场并给出概率估算**,
So that **我能够获得数据驱动的交易建议**.

## Acceptance Criteria

**Given** LLM 客户端和提示词模板已实现
**When** 实现 `src/analysis/llm_analyzer.py`
**Then** 实现 `analyze_market(market: Market)` 方法
**And** 返回 `PredictionResult` 模型包含:
- `predicted_probability`: 预测概率 (0-1)
- `confidence`: 置信度 (0-1)
- `reasoning`: 分析理由
- `key_assumptions`: 关键假设列表
- `recommendation`: 交易建议
**And** 验证输出: 置信度 >= 0.75 (MIN_CONFIDENCE) 才标记为可交易
**And** 记录分析日志 (包含 emoji 🧠)
**And** 处理 LLM 返回格式错误

## Tasks / Subtasks

- [ ] Task 1: 创建 LLM 分析器基础结构 (AC: 1)
  - [ ] 1.1 创建 `src/analysis/llm_analyzer.py` 文件
  - [ ] 1.2 添加模块 docstring
  - [ ] 1.3 导入必要模块 (LLMClient, prompts, Market, PredictionResult)
  - [ ] 1.4 定义 `__all__` 导出列表

- [ ] Task 2: 实现 LLMAnalyzer 类 (AC: 1, 2)
  - [ ] 2.1 创建 `LLMAnalyzer` 类
  - [ ] 2.2 实现 `__init__()` 初始化 LLM 客户端
  - [ ] 2.3 从配置加载 `min_confidence` 和 `min_edge`
  - [ ] 2.4 初始化日志器

- [ ] Task 3: 实现 analyze_market 方法 (AC: 1, 2, 3)
  - [ ] 3.1 定义方法签名 `async def analyze_market(market: Market) -> PredictionResult`
  - [ ] 3.2 调用 `build_market_analysis_prompt(market)` 构建提示词
  - [ ] 3.3 调用 `LLMClient.chat_with_system()` 发送请求
  - [ ] 3.4 调用 `parse_llm_analysis_response()` 解析响应
  - [ ] 3.5 记录分析日志 (🧠 LLM 分析完成)

- [ ] Task 4: 实现置信度验证逻辑 (AC: 4)
  - [ ] 4.1 在 `PredictionResult` 添加 `is_tradeable` 属性
  - [ ] 4.2 验证 `confidence >= settings.risk.min_confidence`
  - [ ] 4.3 验证 `recommendation != NO_TRADE`
  - [ ] 4.4 记录验证结果日志

- [ ] Task 5: 实现错误处理 (AC: 6)
  - [ ] 5.1 捕获 `ValueError` (JSON 解析错误)
  - [ ] 5.2 捕获 `NetworkError` (LLM API 错误)
  - [ ] 5.3 捕获 `RequestTimeoutError` (超时)
  - [ ] 5.4 记录错误日志 (❌ LLM 分析失败)
  - [ ] 5.5 抛出自定义 `AnalysisError` 异常

- [ ] Task 6: 实现 Edge 计算扩展方法 (AC: 2)
  - [ ] 6.1 实现 `calculate_edge(result, market_price)` 方法
  - [ ] 6.2 BUY_YES edge = predicted_probability - market_price
  - [ ] 6.3 BUY_NO edge = (1 - predicted_probability) - (1 - market_price)
  - [ ] 6.4 返回 edge 值

- [ ] Task 7: 实现批量分析方法 (AC: All)
  - [ ] 7.1 实现 `analyze_markets(markets: list[Market])` 方法
  - [ ] 7.2 并发控制 (使用 asyncio.Semaphore)
  - [ ] 7.3 返回 `list[tuple[Market, PredictionResult | Exception]]`
  - [ ] 7.4 记录批量分析统计日志

- [ ] Task 8: 更新模块导出 (AC: All)
  - [ ] 8.1 更新 `src/analysis/__init__.py` 导出 `LLMAnalyzer`
  - [ ] 8.2 创建 `AnalysisError` 异常类 (如果需要)

- [ ] Task 9: 编写测试 (AC: All)
  - [ ] 9.1 创建 `tests/test_analysis/test_llm_analyzer.py`
  - [ ] 9.2 测试 `analyze_market()` 成功场景
  - [ ] 9.3 测试 `analyze_market()` LLM API 错误
  - [ ] 9.4 测试 `analyze_market()` JSON 解析错误
  - [ ] 9.5 测试 `analyze_market()` 超时处理
  - [ ] 9.6 测试 `is_tradeable` 属性
  - [ ] 9.7 测试 `calculate_edge()` 方法
  - [ ] 9.8 测试 `analyze_markets()` 批量分析
  - [ ] 9.9 Mock LLMClient 和依赖

- [ ] Task 10: 代码质量检查 (AC: All)
  - [ ] 10.1 运行 `mypy src/analysis/llm_analyzer.py` 无错误
  - [ ] 10.2 运行 `black --check src/analysis/llm_analyzer.py` 通过
  - [ ] 10.3 运行 `isort --check src/analysis/llm_analyzer.py` 通过
  - [ ] 10.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#Core Dependencies]

**LLM 配置:**
- 使用 OpenAI 兼容协议连接 GLM API
- API Base: `https://open.bigmodel.cn/api/paas/v4`
- 默认模型: `glm-4`
- 超时: 30 秒 (NFR3)

**风险控制配置 [Source: src/config.py]:**
```python
class RiskSettings(BaseSettings):
    min_confidence: float = Field(
        default=0.75, ge=0.0, le=1.0, description="Minimum LLM confidence for trading"
    )
    min_edge: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Minimum edge vs market price"
    )
```

### 已实现的相关模块

**Story 3.1 实现的 LLMClient [Source: src/api/llm.py]:**

```python
from src.api import LLMClient

with LLMClient() as client:
    response = client.chat_with_system(
        system_prompt="You are a prediction market analyst.",
        user_prompt="Analyze this market: ..."
    )
```

**Story 3.2 实现的 Prompts [Source: src/analysis/prompts.py]:**

```python
from src.analysis import (
    MARKET_ANALYST_SYSTEM_PROMPT,
    build_market_analysis_prompt,
    parse_llm_analysis_response,
    LLMAnalysisResult,
    Recommendation,
)

# 构建提示词
user_prompt = build_market_analysis_prompt(market)

# 解析响应
result = parse_llm_analysis_response(response)
```

**已存在的 PredictionResult 模型 [Source: src/models/prediction.py]:**

```python
from src.models.prediction import PredictionResult, Recommendation

result = PredictionResult(
    predicted_probability=0.72,
    confidence=0.85,
    reasoning="Strong technical indicators...",
    key_assumptions=["Economic stability continues"],
    recommendation=Recommendation.BUY_YES,
)
```

### Market 模型 [Source: src/models/market.py]

**已存在的 Market 模型:**

```python
class Market(BaseModel):
    """市场数据模型."""

    id: str
    title: str
    description: str | None = None
    category: MarketCategory | None = None
    yes_price: float | None = None
    no_price: float | None = None
    liquidity: float | None = None
    deadline: datetime | None = None
    resolution_status: str | None = None
    resolution_outcome: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

### 实现模板

**llm_analyzer.py 完整模板:**

```python
# src/analysis/llm_analyzer.py
"""LLM-powered market analysis engine.

This module provides the LLMAnalyzer class that integrates with the LLM API
to analyze prediction markets and generate probability estimates.

Usage:
    from src.analysis import LLMAnalyzer

    analyzer = LLMAnalyzer()
    result = await analyzer.analyze_market(market)

    if result.is_tradeable:
        print(f"Recommendation: {result.recommendation}")
"""

from __future__ import annotations

__all__ = ["LLMAnalyzer", "AnalysisError"]

import asyncio
from typing import Any

from src.api import LLMClient
from src.analysis.prompts import (
    LLMAnalysisResult,
    MARKET_ANALYST_SYSTEM_PROMPT,
    Recommendation,
    build_market_analysis_prompt,
    parse_llm_analysis_response,
)
from src.config import settings
from src.exceptions import NetworkError, RequestTimeoutError, ValidationError
from src.models.market import Market
from src.models.prediction import PredictionResult
from src.utils.logger import OPERATION_EMOJIS, get_logger


class AnalysisError(Exception):
    """LLM 分析错误.

    当 LLM 分析过程中出现错误时抛出。

    Attributes:
        message: 错误信息
        market_id: 相关市场 ID
        original_exception: 原始异常 (可选)
    """

    def __init__(
        self,
        message: str,
        market_id: str | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        """初始化分析错误.

        Args:
            message: 错误信息
            market_id: 相关市场 ID (可选)
            original_exception: 原始异常 (可选)
        """
        self.message = message
        self.market_id = market_id
        self.original_exception = original_exception
        super().__init__(message)


class LLMAnalyzer:
    """LLM 驱动的市场分析引擎.

    使用 LLM 分析预测市场并生成概率估算和交易建议。

    Attributes:
        _min_confidence: 最小置信度阈值
        _min_edge: 最小 Edge 阈值
        _logger: 日志器

    Example:
        >>> analyzer = LLMAnalyzer()
        >>> result = await analyzer.analyze_market(market)
        >>> print(result.predicted_probability)
        0.75
    """

    def __init__(self) -> None:
        """初始化 LLM 分析器."""
        self._logger = get_logger(__name__)
        self._min_confidence = settings.risk.min_confidence
        self._min_edge = settings.risk.min_edge

        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} Initializing LLMAnalyzer "
            f"(min_confidence={self._min_confidence}, min_edge={self._min_edge})"
        )

    async def analyze_market(self, market: Market) -> PredictionResult:
        """分析单个市场.

        使用 LLM 分析预测市场并返回预测结果。

        Args:
            market: 要分析的市场

        Returns:
            PredictionResult 包含预测概率、置信度、建议等

        Raises:
            AnalysisError: 如果分析过程中出现错误

        Example:
            >>> analyzer = LLMAnalyzer()
            >>> result = await analyzer.analyze_market(market)
            >>> result.predicted_probability
            0.75
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} Starting analysis for market: {market.id}"
        )

        try:
            # 构建提示词
            user_prompt = build_market_analysis_prompt(market)

            # 调用 LLM API
            with LLMClient() as client:
                response = client.chat_with_system(
                    system_prompt=MARKET_ANALYST_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                )

            # 解析响应
            llm_result = parse_llm_analysis_response(response)

            # 转换为 PredictionResult
            result = PredictionResult(
                predicted_probability=llm_result.predicted_probability,
                confidence=llm_result.confidence,
                reasoning=llm_result.reasoning,
                key_assumptions=llm_result.key_assumptions,
                recommendation=Recommendation(llm_result.recommendation.value),
            )

            # 验证是否可交易
            is_tradeable = self._is_tradeable(result, market.yes_price)

            self._logger.info(
                f"{OPERATION_EMOJIS['analysis']} Analysis complete for market {market.id}: "
                f"probability={result.predicted_probability:.2f}, "
                f"confidence={result.confidence:.2f}, "
                f"recommendation={result.recommendation.value}, "
                f"is_tradeable={is_tradeable}"
            )

            return result

        except ValueError as e:
            self._logger.error(
                f"❌ Failed to parse LLM response for market {market.id}: {e}"
            )
            raise AnalysisError(
                message=f"Failed to parse LLM response: {e}",
                market_id=market.id,
                original_exception=e,
            )
        except (NetworkError, RequestTimeoutError) as e:
            self._logger.error(
                f"❌ LLM API error for market {market.id}: {e}"
            )
            raise AnalysisError(
                message=f"LLM API error: {e}",
                market_id=market.id,
                original_exception=e,
            )
        except Exception as e:
            self._logger.error(
                f"❌ Unexpected error analyzing market {market.id}: {e}"
            )
            raise AnalysisError(
                message=f"Unexpected error: {e}",
                market_id=market.id,
                original_exception=e,
            )

    def _is_tradeable(
        self, result: PredictionResult, market_yes_price: float | None
    ) -> bool:
        """判断分析结果是否满足交易条件.

        Args:
            result: LLM 分析结果
            market_yes_price: 市场当前 YES 价格

        Returns:
            True 如果满足交易条件，否则 False
        """
        # 检查置信度
        if result.confidence < self._min_confidence:
            return False

        # 检查是否为 NO_TRADE
        if result.recommendation == Recommendation.NO_TRADE:
            return False

        # 检查 Edge (如果有市场价格)
        if market_yes_price is not None:
            edge = self.calculate_edge(result, market_yes_price)
            if edge < self._min_edge:
                return False

        return True

    def calculate_edge(
        self, result: PredictionResult, market_yes_price: float
    ) -> float:
        """计算 Edge (预测概率与市场价格的差距).

        Args:
            result: LLM 分析结果
            market_yes_price: 市场当前 YES 价格 (0-1)

        Returns:
            Edge 值 (正数表示预测概率高于市场价格)

        Example:
            >>> result = PredictionResult(
            ...     predicted_probability=0.8,
            ...     recommendation=Recommendation.BUY_YES,
            ...     ...
            ... )
            >>> edge = analyzer.calculate_edge(result, 0.65)
            >>> edge
            0.15
        """
        if result.recommendation == Recommendation.BUY_YES:
            return result.predicted_probability - market_yes_price
        elif result.recommendation == Recommendation.BUY_NO:
            return (1 - result.predicted_probability) - (1 - market_yes_price)
        else:
            return 0.0

    async def analyze_markets(
        self,
        markets: list[Market],
        max_concurrent: int = 3,
    ) -> list[tuple[Market, PredictionResult | AnalysisError]]:
        """批量分析多个市场.

        使用并发控制批量分析多个市场。

        Args:
            markets: 要分析的市场列表
            max_concurrent: 最大并发数 (默认 3)

        Returns:
            列表，每个元素为 (Market, PredictionResult) 或 (Market, AnalysisError)

        Example:
            >>> results = await analyzer.analyze_markets(markets)
            >>> for market, result in results:
            ...     if isinstance(result, PredictionResult):
            ...         print(f"{market.id}: {result.recommendation}")
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} Starting batch analysis of {len(markets)} markets"
        )

        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_semaphore(
            market: Market,
        ) -> tuple[Market, PredictionResult | AnalysisError]:
            async with semaphore:
                try:
                    result = await self.analyze_market(market)
                    return (market, result)
                except AnalysisError as e:
                    return (market, e)

        # 并发执行分析
        tasks = [analyze_with_semaphore(market) for market in markets]
        results = await asyncio.gather(*tasks)

        # 统计结果
        success_count = sum(
            1 for _, r in results if isinstance(r, PredictionResult)
        )
        error_count = len(results) - success_count

        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} Batch analysis complete: "
            f"{success_count} succeeded, {error_count} failed"
        )

        return results
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增/修改文件:**
```
src/analysis/
├── __init__.py          # 更新: 导出 LLMAnalyzer
├── market_filter.py     # 已存在 (Story 2.3)
├── prompts.py           # 已存在 (Story 3.2)
└── llm_analyzer.py      # 新增: LLM 分析引擎

tests/test_analysis/
├── __init__.py          # 已存在
├── test_market_filter.py # 已存在
├── test_prompts.py      # 已存在 (Story 3.2)
└── test_llm_analyzer.py # 新增: LLM 分析引擎测试
```

### 测试策略

```python
# tests/test_analysis/test_llm_analyzer.py
"""Tests for LLM market analyzer."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.analysis.llm_analyzer import LLMAnalyzer, AnalysisError
from src.analysis.prompts import Recommendation, LLMAnalysisResult
from src.models.market import Market, MarketCategory
from src.models.prediction import PredictionResult
from src.exceptions import NetworkError, RequestTimeoutError


class TestLLMAnalyzer:
    """测试 LLMAnalyzer 类."""

    @pytest.fixture
    def analyzer(self) -> LLMAnalyzer:
        """创建分析器实例."""
        return LLMAnalyzer()

    @pytest.fixture
    def sample_market(self) -> Market:
        """创建示例市场."""
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

    @pytest.mark.asyncio
    async def test_analyze_market_success(
        self, analyzer: LLMAnalyzer, sample_market: Market
    ) -> None:
        """测试成功分析市场."""
        mock_response = '''```json
        {
            "predicted_probability": 0.75,
            "confidence": 0.85,
            "reasoning": "Based on current trends...",
            "key_assumptions": ["Economic stability continues"],
            "recommendation": "BUY_YES"
        }
        ```'''

        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze_market(sample_market)

            assert isinstance(result, PredictionResult)
            assert result.predicted_probability == 0.75
            assert result.confidence == 0.85
            assert result.recommendation == Recommendation.BUY_YES

    @pytest.mark.asyncio
    async def test_analyze_market_json_parse_error(
        self, analyzer: LLMAnalyzer, sample_market: Market
    ) -> None:
        """测试 JSON 解析错误."""
        mock_response = "This is not valid JSON"

        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(AnalysisError) as exc_info:
                await analyzer.analyze_market(sample_market)

            assert "Failed to parse LLM response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_market_network_error(
        self, analyzer: LLMAnalyzer, sample_market: Market
    ) -> None:
        """测试网络错误处理."""
        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.side_effect = NetworkError(
                message="Connection failed",
                endpoint="chat",
            )
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(AnalysisError) as exc_info:
                await analyzer.analyze_market(sample_market)

            assert "LLM API error" in str(exc_info.value)

    def test_is_tradeable_high_confidence(
        self, analyzer: LLMAnalyzer
    ) -> None:
        """测试高置信度可交易."""
        result = PredictionResult(
            predicted_probability=0.8,
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.BUY_YES,
        )
        assert analyzer._is_tradeable(result, 0.65) is True

    def test_is_tradeable_low_confidence(
        self, analyzer: LLMAnalyzer
    ) -> None:
        """测试低置信度不可交易."""
        result = PredictionResult(
            predicted_probability=0.8,
            confidence=0.5,  # Below 0.75
            reasoning="Analysis",
            recommendation=Recommendation.BUY_YES,
        )
        assert analyzer._is_tradeable(result, 0.65) is False

    def test_is_tradeable_no_trade_recommendation(
        self, analyzer: LLMAnalyzer
    ) -> None:
        """测试 NO_TRADE 建议不可交易."""
        result = PredictionResult(
            predicted_probability=0.55,
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.NO_TRADE,
        )
        assert analyzer._is_tradeable(result, 0.65) is False

    def test_calculate_edge_buy_yes(self, analyzer: LLMAnalyzer) -> None:
        """测试 BUY_YES Edge 计算."""
        result = PredictionResult(
            predicted_probability=0.8,
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.BUY_YES,
        )
        edge = analyzer.calculate_edge(result, 0.65)
        assert edge == 0.15  # 0.8 - 0.65

    def test_calculate_edge_buy_no(self, analyzer: LLMAnalyzer) -> None:
        """测试 BUY_NO Edge 计算."""
        result = PredictionResult(
            predicted_probability=0.3,  # 1 - 0.3 = 0.7 NO probability
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.BUY_NO,
        )
        market_yes_price = 0.4  # NO price = 0.6
        edge = analyzer.calculate_edge(result, market_yes_price)
        # (1 - 0.3) - (1 - 0.4) = 0.7 - 0.6 = 0.1
        assert edge == 0.1

    @pytest.mark.asyncio
    async def test_analyze_markets_batch(
        self, analyzer: LLMAnalyzer, sample_market: Market
    ) -> None:
        """测试批量分析."""
        markets = [sample_market] * 3

        mock_response = '''{
            "predicted_probability": 0.75,
            "confidence": 0.85,
            "reasoning": "Analysis",
            "key_assumptions": [],
            "recommendation": "BUY_YES"
        }'''

        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            results = await analyzer.analyze_markets(markets)

            assert len(results) == 3
            for market, result in results:
                assert isinstance(result, PredictionResult)
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (RiskSettings)
- Story 1.4: 自定义异常体系 (NetworkError, RequestTimeoutError)
- Story 1.7: Pydantic 数据模型 (Market, PredictionResult)
- Story 3.1: LLM API 客户端 (LLMClient)
- Story 3.2: LLM 提示词模板 (prompts.py)

**后续故事依赖本故事:**
- Story 3.4: 预测结果存储 (需要 LLMAnalyzer)
- Story 3.5: Edge 计算 (需要 calculate_edge 方法)
- Story 4.4: 交易前风险检查 (需要 PredictionResult)
- Story 5.3: 交易决策流程 (需要 analyze_market 方法)

### 实现注意事项

**关键点:**

1. **异步设计** - `analyze_market` 是异步方法，支持并发分析
2. **错误处理** - 使用自定义 `AnalysisError` 包装所有异常
3. **可交易判断** - 综合检查置信度、建议类型和 Edge
4. **并发控制** - `analyze_markets` 使用 `asyncio.Semaphore` 控制并发
5. **日志记录** - 使用 emoji 标记分析状态 (🧠 分析中/完成，❌ 错误)

**与现有模块的集成:**

```python
from src.analysis import LLMAnalyzer, MarketFilter
from src.models import Market

# 完整的分析流程
async def analyze_and_filter():
    # 1. 筛选市场
    market_filter = MarketFilter()
    filtered = market_filter.filter_markets(markets)

    # 2. LLM 分析
    analyzer = LLMAnalyzer()
    results = await analyzer.analyze_markets(filtered.passed)

    # 3. 筛选可交易的市场
    tradeable = [
        (market, result)
        for market, result in results
        if isinstance(result, PredictionResult) and result.is_tradeable
    ]

    return tradeable
```

### 前一个故事学习 [Source: 3-2-llm-prompt-template.md]

**从 Story 3.2 学到的模式:**

1. **使用 `from __future__ import annotations`** - 支持 Python 3.10+ 类型语法
2. **类型注解使用 `str | None`** - 而非 `Optional[str]`
3. **类型注解使用 `list[X]`** - 而非 `List[X]`
4. **Pydantic Field 验证** - 使用 `ge=0.0, le=1.0` 约束范围
5. **完整 docstring** - 包含 Args, Returns, Raises, Example
6. **单元测试覆盖** - 正常情况 + 边界情况 + 错误情况
7. **`__all__` 导出列表** - 明确模块公共 API
8. **Emoji 日志** - 使用 OPERATION_EMOJIS 字典

### References

- [Source: architecture.md#Core Dependencies] - LLM 技术栈
- [Source: architecture.md#Data Architecture] - 数据模型设计
- [Source: src/config.py] - RiskSettings 配置
- [Source: src/models/market.py] - Market 模型
- [Source: src/models/prediction.py] - PredictionResult 模型
- [Source: src/api/llm.py] - LLMClient 实现
- [Source: src/analysis/prompts.py] - 提示词模板
- [Source: epics.md#Story 3.3] - 原始 Story 定义
- [Source: 3-2-llm-prompt-template.md] - 前一个故事参考

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
