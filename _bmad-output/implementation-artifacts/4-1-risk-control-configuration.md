# Story 4.1: 风险控制配置

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **开发者**,
I want **定义风险控制参数并集成到配置系统**,
So that **风险规则可配置且易于调整**.

## Acceptance Criteria

**Given** Epic 1 配置系统已完成
**When** 扩展 `src/config.py` 添加风险控制配置
**Then** 添加以下配置项:

```python
# 资金管理
INITIAL_CAPITAL: float = 200.0
MAX_SINGLE_RATIO: float = 0.20  # 单笔最大 20%
MIN_BET: float = 5.0

# 熔断机制
CONSECUTIVE_LOSSES_LIMIT: int = 3
REDUCE_RATIO_AFTER_LOSSES: float = 0.10
DAILY_LOSS_LIMIT: float = 0.30  # 日亏损 30% 停止
CAPITAL_THRESHOLD: float = 100.0  # 资金低于 $100
REDUCE_RATIO_LOW_CAPITAL: float = 0.10

# 置信度门槛
MIN_CONFIDENCE: float = 0.75
MIN_EDGE: float = 0.10

# 持仓限制
MAX_POSITION_PER_MARKET: float = 0.40
MAX_OPEN_MARKETS: int = 3
```

**And** 所有参数有默认值和验证 (0-1 范围的参数验证)
**And** 更新 `.env.example`

## Tasks / Subtasks

- [ ] Task 1: 扩展 RiskControlSettings 配置类 (AC: 1)
  - [ ] 1.1 添加 `min_bet: float = Field(default=5.0, gt=0, description="Minimum bet amount in USD")`
  - [ ] 1.2 添加 `reduce_ratio_after_losses: float = Field(default=0.10, ge=0, le=1, alias="REDUCE_RATIO_AFTER_LOSSES")`
  - [ ] 1.3 添加 `reduce_ratio_low_capital: float = Field(default=0.10, ge=0, le=1, alias="REDUCE_RATIO_LOW_CAPITAL")`
  - [ ] 1.4 添加 `max_position_per_market: float = Field(default=0.40, ge=0, le=1, alias="MAX_POSITION_PER_MARKET")`
  - [ ] 1.5 重命名 `max_concurrent_trades` 为 `max_open_markets` (保持向后兼容)

- [ ] Task 2: 添加参数验证 (AC: 2)
  - [ ] 2.1 验证 0-1 范围参数使用 `ge=0, le=1` 约束
  - [ ] 2.2 验证正数参数使用 `gt=0` 约束
  - [ ] 2.3 添加 `__post_init__` 方法进行跨字段验证 (如果需要)

- [ ] Task 3: 更新 .env.example 文件 (AC: 3)
  - [ ] 3.1 添加 `MIN_BET=5.0`
  - [ ] 3.2 添加 `REDUCE_RATIO_AFTER_LOSSES=0.10`
  - [ ] 3.3 添加 `REDUCE_RATIO_LOW_CAPITAL=0.10`
  - [ ] 3.4 添加 `MAX_POSITION_PER_MARKET=0.40`
  - [ ] 3.5 添加 `MAX_OPEN_MARKETS=3` (已有，确认存在)
  - [ ] 3.6 添加注释说明每个参数的用途

- [ ] Task 4: 更新单元测试 (AC: All)
  - [ ] 4.1 扩展 `tests/test_config.py` 测试新参数
  - [ ] 4.2 测试默认值正确性
  - [ ] 4.3 测试边界值验证 (0-1 范围)
  - [ ] 4.4 测试环境变量覆盖

- [ ] Task 5: 代码质量检查 (AC: All)
  - [ ] 5.1 运行 `mypy src/config.py` 无错误
  - [ ] 5.2 运行 `black --check src/config.py` 通过
  - [ ] 5.3 运行 `isort --check src/config.py` 通过
  - [ ] 5.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#Core Dependencies]

**配置管理使用 Pydantic v2:**
- 使用 `BaseSettings` 从环境变量加载
- 使用 `Field()` 定义默认值和验证规则
- 使用 `alias` 支持环境变量别名
- 使用 `model_config` 配置 `env_prefix` 等

### 已存在的 RiskControlSettings [Source: src/config.py]

**当前实现:**

```python
class RiskControlSettings(BaseSettings):
    """Risk control parameters configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    max_single_ratio: float = Field(
        default=0.20,
        alias="MAX_SINGLE_RATIO",
        ge=0,
        le=1,
        description="Maximum single trade ratio of capital (0-1)",
    )
    min_confidence: float = Field(
        default=0.75,
        alias="MIN_CONFIDENCE",
        ge=0,
        le=1,
        description="Minimum LLM confidence to trade (0-1)",
    )
    min_edge: float = Field(
        default=0.10,
        alias="MIN_EDGE",
        ge=0,
        le=1,
        description="Minimum edge (price gap) to trade (0-1)",
    )
    max_concurrent_trades: int = Field(
        default=3,
        alias="MAX_CONCURRENT_TRADES",
        gt=0,
        description="Maximum number of concurrent positions",
    )
    daily_loss_limit: float = Field(
        default=0.30,
        alias="DAILY_LOSS_LIMIT",
        ge=0,
        le=1,
        description="Daily loss limit to stop trading (0-1)",
    )
    consecutive_losses_limit: int = Field(
        default=3,
        alias="CONSECUTIVE_LOSSES_LIMIT",
        gt=0,
        description="Consecutive losses before reducing position",
    )
    capital_threshold: float = Field(
        default=100.0,
        alias="CAPITAL_THRESHOLD",
        gt=0,
        description="Capital threshold for reduced mode",
    )
```

### 需要添加的参数 [Source: epics.md#Story 4.1]

| 参数 | 默认值 | 类型 | 验证 | 说明 |
|------|--------|------|------|------|
| `min_bet` | 5.0 | float | gt=0 | 最小交易金额 (USD) |
| `reduce_ratio_after_losses` | 0.10 | float | ge=0, le=1 | 连续亏损后降级比例 |
| `reduce_ratio_low_capital` | 0.10 | float | ge=0, le=1 | 低资金时降级比例 |
| `max_position_per_market` | 0.40 | float | ge=0, le=1 | 单市场最大持仓比例 |

### 实现模板

**扩展后的 RiskControlSettings:**

```python
class RiskControlSettings(BaseSettings):
    """Risk control parameters configuration.

    风险控制参数配置，包括资金管理、熔断机制、置信度门槛和持仓限制。

    Attributes:
        max_single_ratio: 单笔交易最大资金比例 (0-1)
        min_confidence: 最小 LLM 置信度门槛 (0-1)
        min_edge: 最小 Edge 门槛 (0-1)
        max_open_markets: 最大同时持仓数量
        daily_loss_limit: 日亏损停止门槛 (0-1)
        consecutive_losses_limit: 连续亏损次数触发熔断
        capital_threshold: 低资金门槛 (USD)
        min_bet: 最小交易金额 (USD)
        reduce_ratio_after_losses: 连续亏损后降级比例 (0-1)
        reduce_ratio_low_capital: 低资金时降级比例 (0-1)
        max_position_per_market: 单市场最大持仓比例 (0-1)

    Example:
        >>> from src.config import settings
        >>> settings.risk.min_confidence
        0.75
        >>> settings.risk.max_position_per_market
        0.40
    """

    model_config = SettingsConfigDict(env_prefix="")

    # 资金管理
    max_single_ratio: float = Field(
        default=0.20,
        alias="MAX_SINGLE_RATIO",
        ge=0,
        le=1,
        description="Maximum single trade ratio of capital (0-1)",
    )
    min_bet: float = Field(
        default=5.0,
        alias="MIN_BET",
        gt=0,
        description="Minimum bet amount in USD",
    )

    # 熔断机制
    consecutive_losses_limit: int = Field(
        default=3,
        alias="CONSECUTIVE_LOSSES_LIMIT",
        gt=0,
        description="Consecutive losses before reducing position",
    )
    reduce_ratio_after_losses: float = Field(
        default=0.10,
        alias="REDUCE_RATIO_AFTER_LOSSES",
        ge=0,
        le=1,
        description="Position ratio after consecutive losses (0-1)",
    )
    daily_loss_limit: float = Field(
        default=0.30,
        alias="DAILY_LOSS_LIMIT",
        ge=0,
        le=1,
        description="Daily loss limit to stop trading (0-1)",
    )
    capital_threshold: float = Field(
        default=100.0,
        alias="CAPITAL_THRESHOLD",
        gt=0,
        description="Capital threshold for reduced mode",
    )
    reduce_ratio_low_capital: float = Field(
        default=0.10,
        alias="REDUCE_RATIO_LOW_CAPITAL",
        ge=0,
        le=1,
        description="Position ratio when capital below threshold (0-1)",
    )

    # 置信度门槛
    min_confidence: float = Field(
        default=0.75,
        alias="MIN_CONFIDENCE",
        ge=0,
        le=1,
        description="Minimum LLM confidence to trade (0-1)",
    )
    min_edge: float = Field(
        default=0.10,
        alias="MIN_EDGE",
        ge=0,
        le=1,
        description="Minimum edge (price gap) to trade (0-1)",
    )

    # 持仓限制
    max_position_per_market: float = Field(
        default=0.40,
        alias="MAX_POSITION_PER_MARKET",
        ge=0,
        le=1,
        description="Maximum position ratio per market (0-1)",
    )
    max_open_markets: int = Field(
        default=3,
        alias="MAX_OPEN_MARKETS",
        gt=0,
        description="Maximum number of open positions",
    )

    @field_validator("max_open_markets")
    @classmethod
    def validate_max_open_markets(cls, v: int) -> int:
        """Validate max_open_markets is reasonable."""
        if v > 20:
            raise ValueError("MAX_OPEN_MARKETS should not exceed 20 for risk management")
        return v
```

### 项目结构 [Source: architecture.md#Project Structure]

**修改文件:**
```
src/
├── config.py            # 修改: 扩展 RiskControlSettings

tests/
├── test_config.py       # 修改: 添加新参数测试

.env.example             # 修改: 添加新环境变量
```

### 测试策略

```python
# tests/test_config.py 扩展测试
"""Tests for extended RiskControlSettings."""


class TestRiskControlSettingsExtended:
    """测试扩展的风险控制配置."""

    def test_min_bet_default(self) -> None:
        """测试 min_bet 默认值."""
        settings = Settings()
        assert settings.risk.min_bet == 5.0

    def test_reduce_ratio_after_losses_default(self) -> None:
        """测试 reduce_ratio_after_losses 默认值."""
        settings = Settings()
        assert settings.risk.reduce_ratio_after_losses == 0.10

    def test_reduce_ratio_low_capital_default(self) -> None:
        """测试 reduce_ratio_low_capital 默认值."""
        settings = Settings()
        assert settings.risk.reduce_ratio_low_capital == 0.10

    def test_max_position_per_market_default(self) -> None:
        """测试 max_position_per_market 默认值."""
        settings = Settings()
        assert settings.risk.max_position_per_market == 0.40

    def test_min_bet_must_be_positive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """测试 min_bet 必须为正数."""
        with pytest.raises(ValidationError):
            RiskControlSettings(min_bet=-1.0)

    def test_reduce_ratio_range_validation(self) -> None:
        """测试 reduce_ratio 参数范围验证 (0-1)."""
        with pytest.raises(ValidationError):
            RiskControlSettings(reduce_ratio_after_losses=1.5)
        with pytest.raises(ValidationError):
            RiskControlSettings(reduce_ratio_low_capital=-0.1)

    def test_max_position_per_market_range_validation(self) -> None:
        """测试 max_position_per_market 范围验证 (0-1)."""
        with pytest.raises(ValidationError):
            RiskControlSettings(max_position_per_market=1.5)

    def test_env_override_min_bet(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """测试环境变量覆盖 min_bet."""
        monkeypatch.setenv("MIN_BET", "10.0")
        settings = Settings()
        assert settings.risk.min_bet == 10.0

    def test_max_open_markets_too_large_validation(self) -> None:
        """测试 max_open_markets 过大时抛出验证错误."""
        with pytest.raises(ValidationError):
            RiskControlSettings(max_open_markets=25)
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (已完成 - Settings 基类)

**后续故事依赖本故事:**
- Story 4.2: 线程安全状态管理 (需要 reduce_ratio 参数)
- Story 4.3: 熔断机制实现 (需要 consecutive_losses_limit, reduce_ratio_after_losses)
- Story 4.4: 交易前风险检查 (需要 min_confidence, min_edge, max_position_per_market)

### 实现注意事项

**关键点:**

1. **向后兼容** - 保持现有参数名称不变，避免影响已完成的故事
2. **类型安全** - 使用 Pydantic Field 验证确保参数类型正确
3. **范围验证** - 0-1 范围的参数使用 `ge=0, le=1` 约束
4. **正数验证** - 正数参数使用 `gt=0` 约束
5. **环境变量别名** - 使用 `alias` 支持大写下划线命名的环境变量

**Pydantic v2 最佳实践:**

```python
# 使用 Field 定义参数
field_name: type = Field(
    default=...,
    alias="ENV_VAR_NAME",
    ge=0, le=1,  # 范围验证
    description="参数说明"
)

# 使用 field_validator 进行自定义验证
@field_validator("field_name")
@classmethod
def validate_field(cls, v: type) -> type:
    if condition:
        raise ValueError("Error message")
    return v
```

### 前一个故事学习 [Source: 3-3-llm-analysis-engine.md]

**从 Story 3.3 学到的模式:**

1. **使用 `from __future__ import annotations`** - 支持 Python 3.10+ 类型语法
2. **完整 docstring** - 包含 Args, Returns, Raises, Example
3. **单元测试覆盖** - 正常情况 + 边界情况 + 错误情况
4. **`__all__` 导出列表** - 明确模块公共 API
5. **类型注解使用 `float | None`** - 而非 `Optional[float]`

### References

- [Source: architecture.md#Core Dependencies] - 配置管理技术栈
- [Source: architecture.md#Configuration Template] - .env.example 模板
- [Source: src/config.py] - 现有配置实现
- [Source: epics.md#Story 4.1] - 原始 Story 定义
- [Source: 3-3-llm-analysis-engine.md] - 前一个故事参考

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
