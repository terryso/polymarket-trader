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

from src.analysis.prompts import (
    MARKET_ANALYST_SYSTEM_PROMPT,
    Recommendation,
    build_market_analysis_prompt,
    parse_llm_analysis_response,
)
from src.api import LLMClient
from src.config import settings
from src.exceptions import NetworkError, RequestTimeoutError
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

    def __str__(self) -> str:
        """Return string representation of the error."""
        details = []
        if self.market_id:
            details.append(f"market_id={self.market_id}")
        if self.original_exception:
            details.append(f"caused by: {self.original_exception}")
        if details:
            return f"{self.message} ({', '.join(details)})"
        return self.message


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
            f"(min_confidence={self._min_confidence}, "
            f"min_edge={self._min_edge})"
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
            f"{OPERATION_EMOJIS['analysis']} Starting analysis for market: "
            f"{market.id}"
        )

        try:
            # 构建提示词
            user_prompt = build_market_analysis_prompt(market)

            # 调用 LLM API (同步调用在异步函数中)
            with LLMClient() as client:
                response = client.chat_with_system(
                    system_prompt=MARKET_ANALYST_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                )

            # 解析响应
            llm_result = parse_llm_analysis_response(response)

            # 转换为 PredictionResult
            # 使用 prompts.py 中的 Recommendation
            # 需要转换为 models/prediction.py 中的 Recommendation
            from src.models.prediction import Recommendation as PredRecommendation

            recommendation_mapping = {
                Recommendation.BUY_YES: PredRecommendation.BUY_YES,
                Recommendation.BUY_NO: PredRecommendation.BUY_NO,
                Recommendation.NO_TRADE: PredRecommendation.NO_TRADE,
            }

            result = PredictionResult(
                predicted_probability=llm_result.predicted_probability,
                confidence=llm_result.confidence,
                reasoning=llm_result.reasoning,
                key_assumptions=llm_result.key_assumptions,
                recommendation=(recommendation_mapping[llm_result.recommendation]),
            )

            # 计算 Edge (如果有市场价格)
            if market.yes_price is not None:
                raw_edge = self.calculate_edge(result, market.yes_price)
                result.edge = abs(raw_edge)  # 使用绝对值
                self._logger.info(
                    f"{OPERATION_EMOJIS['analysis']} Edge calculated for "
                    f"market {market.id}: edge={result.edge:.4f}, "
                    f"min_edge={self._min_edge}"
                )

            # 验证是否可交易
            is_tradeable = self._is_tradeable(result, market.yes_price)

            self._logger.info(
                f"{OPERATION_EMOJIS['analysis']} Analysis complete for "
                f"market {market.id}: "
                f"probability={result.predicted_probability:.2f}, "
                f"confidence={result.confidence:.2f}, "
                f"recommendation={result.recommendation.value}, "
                f"is_tradeable={is_tradeable}"
            )

            return result

        except ValueError as e:
            self._logger.error(
                f"❌ Failed to parse LLM response for market " f"{market.id}: {e}"
            )
            raise AnalysisError(
                message=f"Failed to parse LLM response: {e}",
                market_id=market.id,
                original_exception=e,
            )
        except (NetworkError, RequestTimeoutError) as e:
            self._logger.error(f"❌ LLM API error for market {market.id}: {e}")
            raise AnalysisError(
                message=f"LLM API error: {e}",
                market_id=market.id,
                original_exception=e,
            )
        except Exception as e:
            self._logger.error(f"❌ Unexpected error analyzing market {market.id}: {e}")
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
        from src.models.prediction import Recommendation as PredRecommendation

        if result.recommendation == PredRecommendation.NO_TRADE:
            return False

        # 检查 Edge (使用预计算的 edge 值)
        if result.edge is not None:
            if result.edge < self._min_edge:
                return False
        elif market_yes_price is not None:
            # 兼容旧逻辑: 如果 edge 未预计算，则计算
            edge = abs(self.calculate_edge(result, market_yes_price))
            if edge < self._min_edge:
                return False

        return True

    def calculate_edge(
        self, result: PredictionResult, market_yes_price: float
    ) -> float:
        """计算 Edge (预测概率与市场价格的差距).

        Edge 表示 LLM 预测概率与市场价格之间的差距。
        正值表示预测概率高于市场价格，负值表示低于。

        计算公式:
            - BUY_YES: edge = predicted_probability - market_yes_price
            - BUY_NO: edge = (1 - predicted_probability) - (1 - market_yes_price)
                      = market_yes_price - predicted_probability
            - NO_TRADE: edge = 0

        Args:
            result: LLM 分析结果
            market_yes_price: 市场当前 YES 价格 (0-1)

        Returns:
            Edge 值 (有符号值，正数表示预测概率高于市场价格)

        Example:
            >>> # BUY_YES 场景
            >>> result = PredictionResult(
            ...     predicted_probability=0.80,
            ...     confidence=0.85,
            ...     reasoning="Strong buy signal",
            ...     recommendation=Recommendation.BUY_YES,
            ... )
            >>> edge = analyzer.calculate_edge(result, 0.65)
            >>> edge
            0.15  # 0.80 - 0.65

            >>> # BUY_NO 场景
            >>> result = PredictionResult(
            ...     predicted_probability=0.30,
            ...     confidence=0.85,
            ...     reasoning="Strong sell signal",
            ...     recommendation=Recommendation.BUY_NO,
            ... )
            >>> edge = analyzer.calculate_edge(result, 0.65)
            >>> edge
            0.35  # (1 - 0.30) - (1 - 0.65) = 0.70 - 0.35

            >>> # NO_TRADE 场景
            >>> result = PredictionResult(
            ...     predicted_probability=0.50,
            ...     confidence=0.60,
            ...     reasoning="No clear edge",
            ...     recommendation=Recommendation.NO_TRADE,
            ... )
            >>> edge = analyzer.calculate_edge(result, 0.50)
            >>> edge
            0.0
        """
        from src.models.prediction import Recommendation as PredRecommendation

        if result.recommendation == PredRecommendation.BUY_YES:
            return result.predicted_probability - market_yes_price
        elif result.recommendation == PredRecommendation.BUY_NO:
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
            f"{OPERATION_EMOJIS['analysis']} Starting batch analysis of "
            f"{len(markets)} markets"
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
        success_count = sum(1 for _, r in results if isinstance(r, PredictionResult))
        error_count = len(results) - success_count

        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} Batch analysis complete: "
            f"{success_count} succeeded, {error_count} failed"
        )

        return results
