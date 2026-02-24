"""Market filtering engine for selecting high-quality markets.

This module implements the market filter that selects markets
suitable for LLM analysis based on liquidity, deadline, category,
and exclusion rules.

Example:
    >>> from src.analysis import MarketFilter
    >>> from src.config import Settings
    >>>
    >>> settings = Settings()
    >>> filter = MarketFilter(settings)
    >>> result = filter.filter_markets(markets)
    >>> print(f"Filtered {len(result.markets)} markets")
"""

from __future__ import annotations

__all__ = ["MarketFilter", "FilterResult", "FilterStatistics"]

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from src.config import Settings
from src.models import Market, MarketCategory
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)


@dataclass
class FilterStatistics:
    """Statistics about the filtering process.

    Attributes:
        total_input: Total markets input to filter
        passed_hard_liquidity: Markets passing hard liquidity exclusion
        passed_hard_deadline: Markets passing hard deadline exclusion
        passed_soft_liquidity: Markets passing soft liquidity filter
        passed_soft_deadline: Markets passing soft deadline filter
        passed_max_deadline: Markets passing max deadline filter
        passed_category: Markets passing category filter
        passed_exclusion: Markets passing exclusion rules
        final_count: Final count of filtered markets
    """

    total_input: int = 0
    passed_hard_liquidity: int = 0
    passed_hard_deadline: int = 0
    passed_soft_liquidity: int = 0
    passed_soft_deadline: int = 0
    passed_max_deadline: int = 0
    passed_category: int = 0
    passed_exclusion: int = 0
    final_count: int = 0


@dataclass
class FilterResult:
    """Result of market filtering.

    Attributes:
        markets: List of filtered markets
        statistics: Filtering statistics
    """

    markets: list[Market] = field(default_factory=list)
    statistics: FilterStatistics = field(default_factory=FilterStatistics)


class MarketFilter:
    """Market filter for selecting high-quality markets.

    Filters markets based on:
    - Liquidity (minimum threshold)
    - Deadline (minimum days remaining)
    - Category (target categories)
    - Exclusion rules (keywords, etc.)

    Hard Exclusion Rules (applied first):
    - Liquidity < $5,000: Excluded (too low liquidity)
    - Deadline < 3 days: Excluded (not enough time for analysis)

    Soft Filter Rules:
    - Liquidity >= $10,000: Required for quality
    - Deadline >= 7 days: Required for analysis time
    - Category in target categories: POLITICS, BUSINESS, TECHNOLOGY, ECONOMICS, CRYPTO

    Exclusion Rules:
    - Title contains "price", "USD", "tomorrow" (case insensitive)
    - Description contains controversial terms (configurable)

    Example:
        >>> filter = MarketFilter(settings)
        >>> result = filter.filter_markets(markets)
        >>> print(f"Filtered {len(result.markets)} markets")
    """

    # Target categories for analysis
    TARGET_CATEGORIES: set[MarketCategory] = {
        MarketCategory.POLITICS,
        MarketCategory.BUSINESS,
        MarketCategory.TECHNOLOGY,
        MarketCategory.ECONOMICS,
        MarketCategory.CRYPTO,
    }

    # Hard exclusion thresholds
    HARD_EXCLUDE_LIQUIDITY: float = 5000.0
    HARD_EXCLUDE_DEADLINE_HOURS: int = 1  # Same as min_deadline_hours for short-term markets

    # Default excluded keywords for title (case insensitive)
    DEFAULT_EXCLUDED_KEYWORDS: list[str] = ["price", "USD", "tomorrow"]

    # Default controversial keywords for description (case insensitive)
    DEFAULT_CONTROVERSIAL_KEYWORDS: list[str] = []

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the market filter.

        Args:
            settings: Application settings (optional, uses defaults if None)
        """
        self._settings = settings or Settings()
        self._min_liquidity = self._settings.market_filter.min_liquidity
        self._min_deadline_hours = self._settings.market_filter.min_deadline_hours
        self._max_deadline_hours = self._settings.market_filter.max_deadline_hours
        # Get excluded keywords from settings or use defaults
        self._excluded_keywords = getattr(
            self._settings.market_filter,
            "excluded_keywords",
            self.DEFAULT_EXCLUDED_KEYWORDS,
        )
        self._controversial_keywords = getattr(
            self._settings.market_filter,
            "controversial_keywords",
            self.DEFAULT_CONTROVERSIAL_KEYWORDS,
        )

    def _contains_keyword(
        self, text: str, keywords: list[str]
    ) -> tuple[bool, str | None]:
        """Check if text contains any keyword using word boundary matching.

        Uses regex word boundaries to avoid false positives like
        "priceless" matching "price".

        Args:
            text: Text to search in
            keywords: List of keywords to search for

        Returns:
            Tuple of (found, matched_keyword) where matched_keyword is the
            first keyword found, or None if no match.
        """
        text_lower = text.lower()
        for keyword in keywords:
            # Use word boundary regex for more accurate matching
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
            if re.search(pattern, text_lower):
                return True, keyword
        return False, None

    def filter_markets(self, markets: list[Market]) -> FilterResult:
        """Filter markets based on configured rules.

        Args:
            markets: List of markets to filter

        Returns:
            FilterResult containing filtered markets and statistics
        """
        if not markets:
            logger.info(f"{OPERATION_EMOJIS['data']} No markets to filter")
            return FilterResult()

        stats = FilterStatistics(total_input=len(markets))
        logger.info(f"{OPERATION_EMOJIS['data']} Filtering {len(markets)} markets...")

        # Step 1: Hard exclusion by liquidity (< $5,000)
        current = self._hard_exclude_by_liquidity(markets)
        stats.passed_hard_liquidity = len(current)

        # Step 2: Hard exclusion by deadline (< 3 days)
        current = self._hard_exclude_by_deadline(current)
        stats.passed_hard_deadline = len(current)

        # Step 3: Soft filter by liquidity (>= $10,000)
        current = self._filter_by_liquidity(current)
        stats.passed_soft_liquidity = len(current)

        # Step 4: Soft filter by deadline (>= 7 days)
        current = self._filter_by_deadline(current)
        stats.passed_soft_deadline = len(current)

        # Step 4.5: Filter by max deadline (only markets ending within max_deadline_hours)
        current = self._filter_by_max_deadline(current)
        stats.passed_max_deadline = len(current)

        # Step 5: Filter by category
        current = self._filter_by_category(current)
        stats.passed_category = len(current)

        # Step 6: Apply exclusion rules (title and description)
        current = self._apply_exclusion_rules(current)
        stats.passed_exclusion = len(current)

        stats.final_count = len(current)

        logger.info(
            f"{OPERATION_EMOJIS['data']} ✅ Filtered {stats.final_count} / "
            f"{stats.total_input} markets"
        )

        return FilterResult(markets=current, statistics=stats)

    def _hard_exclude_by_liquidity(self, markets: list[Market]) -> list[Market]:
        """Hard exclude markets below minimum liquidity threshold.

        Markets with liquidity < $5,000 are excluded immediately.

        Args:
            markets: List of markets to filter

        Returns:
            List of markets passing hard liquidity threshold
        """
        result = []
        excluded_count = 0

        for market in markets:
            if market.liquidity is None:
                excluded_count += 1
                logger.debug(
                    f"{OPERATION_EMOJIS['data']} ⚠️ Excluded (no liquidity): "
                    f"{market.id}"
                )
            elif market.liquidity < self.HARD_EXCLUDE_LIQUIDITY:
                excluded_count += 1
                logger.debug(
                    f"{OPERATION_EMOJIS['data']} ⚠️ Excluded (liquidity < "
                    f"${self.HARD_EXCLUDE_LIQUIDITY}): {market.id}"
                )
            else:
                result.append(market)

        if excluded_count > 0:
            logger.info(
                f"{OPERATION_EMOJIS['data']} Hard excluded {excluded_count} "
                f"markets by liquidity (< ${self.HARD_EXCLUDE_LIQUIDITY})"
            )

        return result

    def _hard_exclude_by_deadline(self, markets: list[Market]) -> list[Market]:
        """Hard exclude markets with deadline too close.

        Markets with deadline < min_deadline_hours are excluded immediately.

        Args:
            markets: List of markets to filter

        Returns:
            List of markets passing hard deadline threshold
        """
        result = []
        excluded_count = 0
        now = datetime.now(timezone.utc)

        for market in markets:
            if market.deadline is None:
                excluded_count += 1
                logger.debug(
                    f"{OPERATION_EMOJIS['data']} ⚠️ Excluded (no deadline): "
                    f"{market.id}"
                )
            else:
                time_remaining = market.deadline - now
                hours_remaining = time_remaining.total_seconds() / 3600
                if hours_remaining < self._min_deadline_hours:
                    excluded_count += 1
                    logger.debug(
                        f"{OPERATION_EMOJIS['data']} ⚠️ Excluded (deadline < "
                        f"{self._min_deadline_hours} hours): {market.id}"
                    )
                else:
                    result.append(market)

        if excluded_count > 0:
            logger.info(
                f"{OPERATION_EMOJIS['data']} Hard excluded {excluded_count} "
                f"markets by deadline (< {self._min_deadline_hours} hours)"
            )

        return result

    def _filter_by_liquidity(self, markets: list[Market]) -> list[Market]:
        """Filter markets by minimum liquidity.

        Markets with liquidity >= min_liquidity pass.
        Markets with liquidity < min_liquidity are filtered out.

        Args:
            markets: List of markets to filter

        Returns:
            List of markets passing liquidity filter
        """
        result = []
        filtered_count = 0

        for market in markets:
            if market.liquidity is None or market.liquidity < self._min_liquidity:
                filtered_count += 1
                logger.debug(
                    f"{OPERATION_EMOJIS['data']} ⚠️ Filtered (liquidity < "
                    f"${self._min_liquidity}): {market.id}"
                )
            else:
                result.append(market)

        if filtered_count > 0:
            logger.info(
                f"{OPERATION_EMOJIS['data']} Filtered {filtered_count} "
                f"markets by liquidity (< ${self._min_liquidity})"
            )

        return result

    def _filter_by_deadline(self, markets: list[Market]) -> list[Market]:
        """Filter markets by minimum deadline hours.

        Markets with deadline >= min_deadline_hours pass.
        Markets with deadline < min_deadline_hours are filtered out.

        Args:
            markets: List of markets to filter

        Returns:
            List of markets passing deadline filter
        """
        result = []
        filtered_count = 0
        now = datetime.now(timezone.utc)

        for market in markets:
            if market.deadline is None:
                filtered_count += 1
                logger.debug(
                    f"{OPERATION_EMOJIS['data']} ⚠️ Filtered (no deadline): "
                    f"{market.id}"
                )
            else:
                time_remaining = market.deadline - now
                hours_remaining = time_remaining.total_seconds() / 3600
                if hours_remaining < self._min_deadline_hours:
                    filtered_count += 1
                    logger.debug(
                        f"{OPERATION_EMOJIS['data']} ⚠️ Filtered (deadline < "
                        f"{self._min_deadline_hours} hours): {market.id}"
                    )
                else:
                    result.append(market)

        if filtered_count > 0:
            logger.info(
                f"{OPERATION_EMOJIS['data']} Filtered {filtered_count} "
                f"markets by deadline (< {self._min_deadline_hours} hours)"
            )

        return result

    def _filter_by_max_deadline(self, markets: list[Market]) -> list[Market]:
        """Filter markets by maximum deadline hours.

        Only markets with deadline <= max_deadline_hours pass.
        Markets with deadline > max_deadline_hours are filtered out.
        If max_deadline_hours is None or 0, all markets pass (no limit).

        Args:
            markets: List of markets to filter

        Returns:
            List of markets passing max deadline filter
        """
        # If no max deadline configured (None or 0), pass all markets
        if self._max_deadline_hours is None or self._max_deadline_hours == 0:
            return markets

        result = []
        filtered_count = 0
        now = datetime.now(timezone.utc)

        for market in markets:
            if market.deadline is None:
                # Markets with no deadline are kept (already filtered by min deadline)
                result.append(market)
            else:
                time_remaining = market.deadline - now
                hours_remaining = time_remaining.total_seconds() / 3600
                if hours_remaining > self._max_deadline_hours:
                    filtered_count += 1
                    logger.debug(
                        f"{OPERATION_EMOJIS['data']} ⚠️ Filtered (deadline > "
                        f"{self._max_deadline_hours} hours): {market.id}"
                    )
                else:
                    result.append(market)

        if filtered_count > 0:
            logger.info(
                f"{OPERATION_EMOJIS['data']} Filtered {filtered_count} "
                f"markets by max deadline (> {self._max_deadline_hours} hours)"
            )

        return result

    def _filter_by_category(self, markets: list[Market]) -> list[Market]:
        """Filter markets by target categories.

        Markets with category in TARGET_CATEGORIES pass.
        Markets with no category (None) are kept by default.
        Markets with other categories are filtered out.

        Args:
            markets: List of markets to filter

        Returns:
            List of markets passing category filter
        """
        result = []
        filtered_count = 0

        for market in markets:
            if market.category is None:
                # Markets with no category are kept
                result.append(market)
            elif market.category in self.TARGET_CATEGORIES:
                result.append(market)
            else:
                filtered_count += 1
                logger.debug(
                    f"{OPERATION_EMOJIS['data']} ⚠️ Filtered (category not in "
                    f"targets): {market.id} ({market.category})"
                )

        if filtered_count > 0:
            logger.info(
                f"{OPERATION_EMOJIS['data']} Filtered {filtered_count} "
                f"markets by category"
            )

        return result

    def _apply_exclusion_rules(self, markets: list[Market]) -> list[Market]:
        """Apply keyword and other exclusion rules.

        Excludes markets based on:
        - Title containing "price", "USD", "tomorrow" (case insensitive, word boundary)
        - Description containing controversial terms (configurable)

        Args:
            markets: List of markets to filter

        Returns:
            List of markets passing exclusion rules
        """
        result = []
        excluded_by_title = 0
        excluded_by_description = 0

        for market in markets:
            # Check title for excluded keywords (word boundary matching)
            title_excluded, title_keyword = self._contains_keyword(
                market.title, self._excluded_keywords
            )

            if title_excluded:
                excluded_by_title += 1
                logger.debug(
                    f"{OPERATION_EMOJIS['data']} ⚠️ Excluded (title keyword "
                    f"'{title_keyword}'): {market.id}"
                )
                continue

            # Check description for controversial keywords (if configured)
            if market.description and self._controversial_keywords:
                desc_excluded, desc_keyword = self._contains_keyword(
                    market.description, self._controversial_keywords
                )
                if desc_excluded:
                    excluded_by_description += 1
                    logger.debug(
                        f"{OPERATION_EMOJIS['data']} ⚠️ Excluded (description "
                        f"keyword '{desc_keyword}'): {market.id}"
                    )
                    continue

            result.append(market)

        if excluded_by_title > 0:
            logger.info(
                f"{OPERATION_EMOJIS['data']} Excluded {excluded_by_title} "
                f"markets by title keyword rules"
            )

        if excluded_by_description > 0:
            logger.info(
                f"{OPERATION_EMOJIS['data']} Excluded {excluded_by_description} "
                f"markets by description keyword rules"
            )

        return result
