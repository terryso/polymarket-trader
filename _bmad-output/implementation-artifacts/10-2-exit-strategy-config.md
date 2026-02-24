# Story 10.2: 退出策略配置

Status: done

## Story

As a **用户**,
I want **配置止盈、止损等退出策略参数**,
So that **系统能够根据我的风险偏好自动决定何时卖出**.

## Acceptance Criteria

1. **Given** Epic 1 配置系统已完成
   **When** 扩展 `src/config.py` 添加退出策略配置
   **Then** 创建 `ExitStrategySettings` 配置类

2. **止盈配置:**
   - `TAKE_PROFIT_ENABLED: bool = True` - 启用止盈
   - `TAKE_PROFIT_PCT: float = 0.50` - 盈利 50% 时止盈

3. **止损配置:**
   - `STOP_LOSS_ENABLED: bool = True` - 启用止损
   - `STOP_LOSS_PCT: float = -0.30` - 亏损 30% 时止损

4. **时间退出配置:**
   - `TIME_EXIT_ENABLED: bool = False` - 启用时间退出
   - `TIME_EXIT_HOURS: int = 72` - 持仓超过 72 小时自动退出

5. **信号退出配置:**
   - `SIGNAL_EXIT_ENABLED: bool = True` - 启用信号反转退出
   - 当 LLM 重新分析给出相反建议时退出

6. **退出检查间隔:**
   - `EXIT_CHECK_INTERVAL_MINUTES: int = 5` - 每 5 分钟检查一次

7. **参数验证:**
   - `TAKE_PROFIT_PCT` 必须大于 0
   - `STOP_LOSS_PCT` 必须小于 0
   - `TIME_EXIT_HOURS` 必须大于 0
   - `EXIT_CHECK_INTERVAL_MINUTES` 必须大于 0

8. **所有参数支持通过环境变量覆盖**

9. **更新 `.env.example` 添加退出策略配置示例**

## Tasks / Subtasks

- [x] Task 1: 创建 ExitStrategySettings 配置类 (AC: #1-#6)
  - [x] 1.1 在 `src/config.py` 中创建 `ExitStrategySettings` 类
  - [x] 1.2 添加止盈配置字段 (TAKE_PROFIT_ENABLED, TAKE_PROFIT_PCT)
  - [x] 1.3 添加止损配置字段 (STOP_LOSS_ENABLED, STOP_LOSS_PCT)
  - [x] 1.4 添加时间退出配置字段 (TIME_EXIT_ENABLED, TIME_EXIT_HOURS)
  - [x] 1.5 添加信号退出配置字段 (SIGNAL_EXIT_ENABLED)
  - [x] 1.6 添加退出检查间隔字段 (EXIT_CHECK_INTERVAL_MINUTES)

- [x] Task 2: 添加参数验证 (AC: #7)
  - [x] 2.1 使用 Pydantic Field 验证 TAKE_PROFIT_PCT > 0
  - [x] 2.2 使用 Pydantic Field 验证 STOP_LOSS_PCT < 0
  - [x] 2.3 使用 Pydantic Field 验证 TIME_EXIT_HOURS > 0
  - [x] 2.4 使用 Pydantic Field 验证 EXIT_CHECK_INTERVAL_MINUTES > 0

- [x] Task 3: 集成到 Settings 主类 (AC: #8)
  - [x] 3.1 在 `Settings` 类中添加 `exit_strategy: ExitStrategySettings` 字段
  - [x] 3.2 确保 BaseEnvSettings 继承以支持 .env 文件

- [x] Task 4: 更新 .env.example (AC: #9)
  - [x] 4.1 添加退出策略配置章节
  - [x] 4.2 添加所有退出策略参数示例
  - [x] 4.3 添加配置说明注释

- [x] Task 5: 添加单元测试 (AC: All)
  - [x] 5.1 测试默认值正确性
  - [x] 5.2 测试参数验证 (无效值应抛出异常)
  - [x] 5.3 测试环境变量覆盖
  - [x] 5.4 测试 Settings 集成 (settings.exit_strategy 可用)

## Dev Notes

### 现有配置系统分析

**src/config.py 结构:**
- 使用 Pydantic v2 `BaseEnvSettings` (自定义的 BaseSettings 子类)
- 每个 Settings 类使用 `model_config = SettingsConfigDict(...)`
- 支持 `env_prefix` 和 `alias` 两种环境变量命名方式
- 主 `Settings` 类使用嵌套字段组织配置

**现有配置类模式参考:**
```python
class RiskControlSettings(BaseEnvSettings):
    """风险控制参数配置。"""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_single_ratio: float = Field(
        default=0.20,
        alias="MAX_SINGLE_RATIO",
        ge=0,
        le=1,
        description="Maximum single trade ratio of capital (0-1)",
    )
```

### 新配置类实现模式

**ExitStrategySettings 实现参考:**
```python
class ExitStrategySettings(BaseEnvSettings):
    """退出策略配置参数。

    退出策略配置，包括止盈、止损、时间退出和信号反转退出。

    Attributes:
        take_profit_enabled: 是否启用止盈
        take_profit_pct: 止盈百分比阈值 (大于 0，如 0.50 = 50%)
        stop_loss_enabled: 是否启用止损
        stop_loss_pct: 止损百分比阈值 (小于 0，如 -0.30 = -30%)
        time_exit_enabled: 是否启用时间退出
        time_exit_hours: 时间退出小时数
        signal_exit_enabled: 是否启用信号反转退出
        exit_check_interval_minutes: 退出检查间隔 (分钟)
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 止盈配置
    take_profit_enabled: bool = Field(
        default=True,
        alias="TAKE_PROFIT_ENABLED",
        description="Enable take profit exit strategy",
    )
    take_profit_pct: float = Field(
        default=0.50,
        alias="TAKE_PROFIT_PCT",
        gt=0,
        description="Take profit percentage threshold (e.g., 0.50 = 50% profit)",
    )

    # 止损配置
    stop_loss_enabled: bool = Field(
        default=True,
        alias="STOP_LOSS_ENABLED",
        description="Enable stop loss exit strategy",
    )
    stop_loss_pct: float = Field(
        default=-0.30,
        alias="STOP_LOSS_PCT",
        lt=0,
        ge=-1,
        description="Stop loss percentage threshold (e.g., -0.30 = -30% loss)",
    )

    # 时间退出配置
    time_exit_enabled: bool = Field(
        default=False,
        alias="TIME_EXIT_ENABLED",
        description="Enable time-based exit strategy",
    )
    time_exit_hours: int = Field(
        default=72,
        alias="TIME_EXIT_HOURS",
        gt=0,
        description="Hours after which to exit position",
    )

    # 信号退出配置
    signal_exit_enabled: bool = Field(
        default=True,
        alias="SIGNAL_EXIT_ENABLED",
        description="Enable signal reversal exit (when LLM suggests opposite)",
    )

    # 退出检查间隔
    exit_check_interval_minutes: int = Field(
        default=5,
        alias="EXIT_CHECK_INTERVAL_MINUTES",
        gt=0,
        description="Interval in minutes for checking exit conditions",
    )
```

**Settings 集成:**
```python
class Settings(BaseEnvSettings):
    # ... 现有字段 ...

    # 添加退出策略配置
    exit_strategy: ExitStrategySettings = Field(default_factory=ExitStrategySettings)
```

### .env.example 新增内容

```bash
# ========== Exit Strategy Configuration ==========
# Take Profit: Exit when profit reaches this percentage
TAKE_PROFIT_ENABLED=true
TAKE_PROFIT_PCT=0.50

# Stop Loss: Exit when loss reaches this percentage (negative value)
STOP_LOSS_ENABLED=true
STOP_LOSS_PCT=-0.30

# Time Exit: Exit after holding for this many hours (disabled by default)
TIME_EXIT_ENABLED=false
TIME_EXIT_HOURS=72

# Signal Exit: Exit when LLM analysis suggests opposite direction
SIGNAL_EXIT_ENABLED=true

# How often to check exit conditions (in minutes)
EXIT_CHECK_INTERVAL_MINUTES=5
```

### 退出策略优先级 (供后续 Story 10.3 参考)

| 策略 | 优先级 | 触发条件 |
|------|--------|----------|
| 止损 | 最高 | PnL <= STOP_LOSS_PCT |
| 止盈 | 高 | PnL >= TAKE_PROFIT_PCT |
| 时间退出 | 中 | 持仓时间 >= TIME_EXIT_HOURS |
| 信号退出 | 低 | LLM 建议反转 |

### 与现有配置的关系

- **RiskControlSettings** - 控制交易前的风险检查 (买入前)
- **ExitStrategySettings** - 控制交易后的退出策略 (卖出前)
- 两者配合使用，RiskControl 控制入口，ExitStrategy 控制出口

### Project Structure Notes

- 遵循现有 `src/config.py` 的结构和模式
- 测试放在 `tests/test_config.py` (已有文件，追加测试)
- 使用 Pydantic v2 的 Field 验证

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 10] - Epic 需求
- [Source: src/config.py] - 现有配置系统实现
- [Source: .env.example] - 现有环境变量示例
- [Source: _bmad-output/project-context.md] - Pydantic v2 模式

## Dev Agent Record

### Agent Model Used

GLM-5 (claude-opus-4-6 via Claude Code)

### Debug Log References

无

### Completion Notes List

- 2026-02-25: 完成 Story 10.2 退出策略配置实现
  - 创建了 `ExitStrategySettings` 配置类，包含止盈、止损、时间退出、信号退出四种退出策略配置
  - 使用 Pydantic Field 验证所有参数（TAKE_PROFIT_PCT > 0, STOP_LOSS_PCT < 0 且 >= -1, TIME_EXIT_HOURS > 0, EXIT_CHECK_INTERVAL_MINUTES > 0）
  - 集成到 Settings 主类，支持通过环境变量覆盖所有参数
  - 更新 .env.example 添加完整的配置示例和注释
  - 添加 11 个单元测试覆盖默认值、验证、环境变量覆盖和 Settings 集成
  - 所有 112 个测试通过，ruff lint 检查通过

### File List

- `src/config.py` - 添加 ExitStrategySettings 类和 exit_strategy 字段
- `.env.example` - 添加退出策略配置示例和注释
- `tests/test_config.py` - 添加 TestExitStrategySettings 和 TestSettingsExitStrategy 测试类

### Change Log

- 2026-02-25: Story 10.2 初始实现完成，状态更新为 review
