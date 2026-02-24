# Story 10.1: 卖出执行器

Status: done

## Story

As a **用户**,
I want **系统能够在 Polymarket 上执行卖出操作**,
So that **我可以在任何时候变现持有的 shares**.

## Acceptance Criteria

1. **Given** Epic 5 Paper Trading 已完成
   **When** 实现 `src/trading/live_trading.py` 扩展卖出功能
   **Then** 在 `LiveTradingExecutor` 添加 `sell_position` 方法

2. **卖出执行流程:**
   - 获取当前市场价格 (YES/NO price)
   - 计算卖出份额 (默认全部)
   - 调用 Polymarket CLOB API 下卖单 (`side="SELL"`)
   - 创建 Trade 记录 (trade_type=SELL_YES/SELL_NO)
   - 更新 Position 状态和盈亏
   - 更新 ThreadSafeState 资金
   - 发送通知

3. **在 `src/models/trade.py` 添加交易类型:**
   - `SELL_YES` - 卖出 YES shares
   - `SELL_NO` - 卖出 NO shares

4. **返回 `SellResult` 包含:**
   - `trade: Trade` - 交易记录
   - `position: Position` - 更新后的持仓
   - `realized_pnl: float` - 已实现盈亏
   - `success: bool` - 是否成功
   - `error_message: str | None` - 错误信息

5. **支持部分卖出:**
   - `shares: float | None = None` - None 表示全部卖出
   - 部分卖出时更新 Position 的 shares，不关闭持仓

6. **支持卖出原因记录:**
   - `reason: str = "manual"` - manual, take_profit, stop_loss, signal

## Tasks / Subtasks

- [x] Task 1: 扩展 TradeType 枚举 (AC: #3)
  - [x] 1.1 在 `src/models/trade.py` 添加 `SELL_YES` 和 `SELL_NO` 枚举值
  - [x] 1.2 更新 Trade 模型的 trade_type 字段验证
  - [x] 1.3 添加单元测试验证新枚举值

- [x] Task 2: 创建 SellResult 数据类 (AC: #4)
  - [x] 2.1 在 `src/trading/live_trading.py` 创建 `SellResult` dataclass
  - [x] 2.2 定义字段: trade, position, realized_pnl, success, error_message
  - [x] 2.3 添加类型注解和文档字符串

- [x] Task 3: 实现 sell_position 方法 (AC: #1, #2, #5, #6)
  - [x] 3.1 在 `LiveTradingExecutor` 添加 `sell_position` 方法签名
  - [x] 3.2 实现参数验证 (position status, shares 有效性)
  - [x] 3.3 实现 token ID 获取逻辑 (根据 outcome 选择正确 token)
  - [x] 3.4 实现份额计算逻辑 (全部或部分)
  - [x] 3.5 调用 Polymarket CLOB API 下卖单
  - [x] 3.6 创建 SELL_YES/SELL_NO Trade 记录
  - [x] 3.7 更新 Position 状态 (CLOSED 或减少 shares)
  - [x] 3.8 更新 ThreadSafeState 资金
  - [x] 3.9 返回 SellResult

- [x] Task 4: 实现部分卖出逻辑 (AC: #5)
  - [x] 4.1 检查 shares 参数是否小于 position.shares
  - [x] 4.2 部分卖出时更新 Position 的 shares 和 current_value
  - [x] 4.3 全部卖出时关闭 Position (status=CLOSED, closed_at=now)
  - [x] 4.4 更新 system_state 的 open_positions 计数

- [x] Task 5: 错误处理 (AC: #4)
  - [x] 5.1 处理 API 调用失败
  - [x] 5.2 处理 position 不存在或已关闭
  - [x] 5.3 处理 shares 超过持仓数量
  - [x] 5.4 返回带有 error_message 的 SellResult

- [x] Task 6: 添加单元测试 (AC: All)
  - [x] 6.1 测试 SELL_YES/SELL_NO 枚举值
  - [x] 6.2 测试全部卖出成功场景
  - [x] 6.3 测试部分卖出成功场景
  - [x] 6.4 测试卖出失败场景 (API 错误、无效参数等)
  - [x] 6.5 测试 Position 状态更新

## Dev Notes

### 现有代码分析

**LiveTradingExecutor (`src/trading/live_trading.py`):**
- 已有 `execute_trade` 方法实现买入逻辑
- 使用 `OrderArgs` 和 `create_and_post_order` 调用 Polymarket API
- 需要扩展添加卖出功能

**TradeType 枚举 (`src/models/trade.py`):**
```python
class TradeType(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    SELL = "SELL"  # 已存在但不区分 YES/NO
```
- 需要将 `SELL` 改为 `SELL_YES` 和 `SELL_NO`

**PositionManager (`src/trading/position_manager.py`):**
- 已有 `close_position` 方法可用于完全卖出
- 需要添加 `reduce_position` 方法用于部分卖出
- 已集成 Telegram 通知支持

### API 调用模式

参考现有买入逻辑:
```python
from py_clob_client.clob_types import OrderArgs

order_args = OrderArgs(
    token_id=token_id,
    price=price,
    size=shares,
    side="SELL",  # 卖出时使用 SELL
)
result = self._client._client.create_and_post_order(order_args)
```

### 卖出份额计算

```python
# 确定卖出份额
if shares is None:
    shares_to_sell = position.shares  # 全部卖出
else:
    shares_to_sell = min(shares, position.shares)  # 部分卖出，不超过持仓

# 计算收入
sell_proceeds = shares_to_sell * price
```

### Token ID 选择逻辑

```python
def _get_sell_token_id(self, position: Position, market: Market) -> str:
    """获取卖出时使用的 token ID"""
    if not market.clob_token_ids or len(market.clob_token_ids) < 2:
        raise ValidationError(f"Market {market.id} does not have CLOB token IDs")

    # 卖出时使用持仓对应的 token
    # clob_token_ids[0] = YES token, clob_token_ids[1] = NO token
    if position.outcome == PositionOutcome.YES:
        return market.clob_token_ids[0]
    else:
        return market.clob_token_ids[1]
```

### 卖出交易类型确定

```python
def _get_sell_trade_type(self, position: Position) -> TradeType:
    """根据持仓类型确定卖出交易类型"""
    if position.outcome == PositionOutcome.YES:
        return TradeType.SELL_YES
    else:
        return TradeType.SELL_NO
```

### Project Structure Notes

- 遵循现有 `src/trading/` 目录结构
- 遵循现有 `src/models/` 目录结构
- 测试放在 `tests/test_trading/` 目录

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] - 数据模型定义
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 10] - Epic 需求
- [Source: src/trading/live_trading.py] - 现有买入实现
- [Source: src/trading/position_manager.py] - 持仓管理
- [Source: src/models/trade.py] - 交易类型枚举

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

- `src/models/trade.py` - 添加 SELL_YES, SELL_NO 枚举值
- `src/trading/live_trading.py` - 添加 sell_position 方法和 SellResult 类
- `tests/test_trading/test_live_trading_sell.py` - 新增测试文件
