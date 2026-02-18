# Story 5.6: 交易历史同步

Status: done

## Story

As a **用户**,
I want **能够从 Polymarket 同步真实交易历史到本地数据库**,
So that **我能够查看账号的真实交易记录，确保本地数据与链上一致**.

## 背景

当前系统的交易历史来自本地数据库，不是从 Polymarket 获取的真实链上交易。这导致：
- Live 模式下可能出现本地记录和链上实际状态不一致
- 用户无法查看账号的完整交易历史
- 数据准确性无法验证

## Acceptance Criteria

### AC1: 同步 API 端点
**Given** 系统已配置 Polymarket API 凭证
**When** 调用 `POST /api/trades/sync`
**Then** 系统从 Polymarket 获取交易历史
**And** 将交易记录同步到本地数据库
**And** 返回同步结果（新增数量、更新数量、一致数量）

### AC2: 同步状态显示
**Given** 交易历史页面已加载
**When** 页面显示时
**Then** 显示"最后同步时间"
**And** 显示同步状态（已同步/未同步/同步中）
**And** 提供"同步"按钮触发手动同步

### AC3: 数据对账
**Given** 同步完成后
**When** 检查本地数据与 API 数据
**Then** 对比每笔交易的金额、价格、状态
**And** 标记不一致的记录
**And** 返回对账报告

### AC4: 错误处理
**Given** 同步过程中发生错误
**When** API 调用失败或数据解析错误
**Then** 记录错误日志
**And** 返回友好的错误信息
**And** 不影响现有本地数据

### AC5: Paper 模式提示
**Given** 系统运行在 Paper 模式
**When** 尝试同步交易历史
**Then** 返回提示信息"Paper 模式无真实交易历史"
**And** 不执行同步操作

## 技术方案

### 后端实现

#### 1. 扩展 PolymarketClient (src/api/polymarket.py)

```python
@dataclass
class OrderHistoryItem:
    """订单历史项"""
    order_id: str
    market_id: str
    side: str  # BUY/SELL
    outcome: str  # YES/NO
    price: float
    size: float
    status: str
    created_at: datetime
    executed_at: datetime | None

def get_order_history(
    self,
    limit: int = 100,
    before: datetime | None = None
) -> list[OrderHistoryItem]:
    """获取订单历史"""
    # 使用 py-clob-client 的 get_orders API
```

#### 2. 同步服务 (src/trading/trade_sync.py)

```python
class TradeSyncService:
    """交易同步服务"""

    async def sync_trades(self) -> SyncResult:
        """同步交易历史"""
        # 1. 从 Polymarket 获取订单历史
        # 2. 转换为本地 Trade 模型
        # 3. 对比本地数据
        # 4. 插入新记录 / 更新现有记录
        # 5. 返回同步结果
```

#### 3. API 端点 (src/dashboard/routes/trades.py)

```python
@router.post("/sync")
async def sync_trades() -> ApiResponse[SyncResult]:
    """同步交易历史"""
    result = await trade_sync_service.sync_trades()
    return ApiResponse(success=True, data=result)

@router.get("/sync/status")
async def get_sync_status() -> ApiResponse[SyncStatus]:
    """获取同步状态"""
```

### 前端实现

#### 1. 类型定义 (dashboard/src/api/types.ts)

```typescript
export interface SyncResult {
  new_trades: number;
  updated_trades: number;
  consistent_trades: number;
  inconsistent_trades: number;
  last_sync_at: string;
}

export interface SyncStatus {
  last_sync_at: string | null;
  is_syncing: boolean;
  can_sync: boolean;  // Live 模式才能同步
}
```

#### 2. 交易历史页面更新

- 添加同步按钮
- 显示最后同步时间
- 显示同步状态

## 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/api/polymarket.py` | 修改 | 添加 get_order_history 方法 |
| `src/trading/trade_sync.py` | 新建 | 交易同步服务 |
| `src/dashboard/routes/trades.py` | 修改 | 添加同步 API 端点 |
| `dashboard/src/api/types.ts` | 修改 | 添加同步相关类型 |
| `dashboard/src/pages/Trades.tsx` | 修改 | 添加同步 UI |
| `tests/test_trading/test_trade_sync.py` | 新建 | 同步服务测试 |
| `tests/test_dashboard/test_routes/test_trades.py` | 修改 | 添加同步 API 测试 |

## 测试计划

1. **单元测试**
   - TradeSyncService.sync_trades() 逻辑测试
   - 数据转换和对比逻辑测试
   - 错误处理测试

2. **集成测试**
   - API 端点测试
   - 数据库操作测试

3. **手动测试**
   - Live 模式下同步真实交易
   - Paper 模式下验证提示信息

## 依赖

- py-clob-client 的 get_orders API (需要 Level 2 认证)
- 如果没有 API Credentials，则返回提示"需要配置 API 凭证"

## 风险

| 风险 | 缓解措施 |
|------|----------|
| API 凭证未配置 | 返回友好提示，引导用户配置 |
| API 调用频率限制 | 添加缓存，限制同步频率 |
| 数据量过大 | 分页获取，后台异步同步 |

## Story Points

估计: 3 SP
