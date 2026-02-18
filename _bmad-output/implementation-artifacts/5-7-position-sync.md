# Story 5.7: 同步实际持仓

Status: done

## Story

As a **用户**,
I want **能够从 Polymarket 同步钱包实际持仓到本地数据库**,
So that **我能够查看账号的真实持仓状态，确保本地数据与链上一致**.

## 背景

当前系统的持仓数据来自本地数据库，不是从 Polymarket 获取的真实链上持仓。这导致：
- 用户在 Polymarket 网站上手动交易后，本地持仓不会更新
- Live 模式下可能出现本地记录和链上实际持仓不一致
- 用户无法查看钱包的真实持仓情况
- 数据恢复时无法从链上重建持仓

## Acceptance Criteria

### AC1: 同步 API 端点
**Given** 系统已配置 Polymarket API 凭证
**When** 调用 `POST /api/positions/sync`
**Then** 系统从 Polymarket 获取钱包实际持仓
**And** 将持仓记录同步到本地数据库
**And** 返回同步结果（新增数量、更新数量、关闭数量）

### AC2: 持仓同步状态显示
**Given** 持仓页面已加载
**When** 页面显示时
**Then** 显示"最后同步时间"
**And** 显示同步状态（已同步/未同步/同步中）
**And** 提供"同步持仓"按钮触发手动同步

### AC3: 持仓对比与更新
**Given** 同步获取到链上持仓
**When** 与本地持仓对比
**Then** 新增链上有但本地没有的持仓
**And** 更新本地已有持仓的 shares 数量
**And** 关闭本地有但链上没有的持仓（卖出/结算）

### AC4: 错误处理
**Given** 同步过程中发生错误
**When** API 调用失败或数据解析错误
**Then** 记录错误日志
**And** 返回友好的错误信息
**And** 不影响现有本地数据

### AC5: Paper 模式提示
**Given** 系统运行在 Paper 模式
**When** 尝试同步持仓
**Then** 返回提示信息"Paper 模式无真实持仓"
**And** 不执行同步操作

## 技术方案

### 后端实现

#### 1. 扩展 PolymarketClient (src/api/polymarket.py)

```python
@dataclass
class BalanceItem:
    """持仓余额项"""
    condition_id: str
    outcome: str  # YES/NO
    shares: float
    market_title: str | None = None

def get_balances(self) -> list[BalanceItem]:
    """获取钱包持仓余额"""
    # 使用 CLOB API 的 /balances 端点
    # GET https://clob.polymarket.com/balances
```

#### 2. 持仓同步服务 (src/trading/position_sync.py)

```python
@dataclass
class PositionSyncResult:
    """持仓同步结果"""
    new_positions: int
    updated_positions: int
    closed_positions: int
    unchanged_positions: int
    last_sync_at: datetime

class PositionSyncService:
    """持仓同步服务"""

    async def sync_positions(self) -> PositionSyncResult:
        """同步持仓"""
        # 1. 从 Polymarket 获取钱包余额
        # 2. 获取本地所有 OPEN 状态的持仓
        # 3. 对比两边数据
        # 4. 新增/更新/关闭持仓
        # 5. 返回同步结果
```

#### 3. API 端点 (src/dashboard/routes/positions.py)

```python
@router.post("/sync")
async def sync_positions() -> ApiResponse[PositionSyncResult]:
    """同步持仓"""
    result = await position_sync_service.sync_positions()
    return ApiResponse(success=True, data=result)

@router.get("/sync/status")
async def get_position_sync_status() -> ApiResponse[PositionSyncStatus]:
    """获取持仓同步状态"""
```

### 前端实现

#### 1. 类型定义 (dashboard/src/api/types.ts)

```typescript
export interface PositionSyncResult {
  new_positions: number;
  updated_positions: number;
  closed_positions: number;
  unchanged_positions: number;
  last_sync_at: string;
}

export interface PositionSyncStatus {
  last_sync_at: string | null;
  is_syncing: boolean;
  can_sync: boolean;  // Live 模式才能同步
}
```

#### 2. 持仓页面更新

- 添加"同步持仓"按钮
- 显示最后同步时间
- 显示同步状态
- 同步完成后刷新持仓列表

## 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/api/polymarket.py` | 修改 | 添加 get_balances 方法 |
| `src/trading/position_sync.py` | 新建 | 持仓同步服务 |
| `src/dashboard/routes/positions.py` | 修改 | 添加同步 API 端点 |
| `src/models/position.py` | 可能修改 | 添加同步相关字段 |
| `dashboard/src/api/types.ts` | 修改 | 添加同步相关类型 |
| `dashboard/src/pages/Positions.tsx` | 修改 | 添加同步 UI |
| `tests/test_trading/test_position_sync.py` | 新建 | 同步服务测试 |
| `tests/test_dashboard/test_routes/test_positions.py` | 修改 | 添加同步 API 测试 |

## 测试计划

1. **单元测试**
   - PositionSyncService.sync_positions() 逻辑测试
   - 持仓对比和更新逻辑测试
   - 错误处理测试

2. **集成测试**
   - API 端点测试
   - 数据库操作测试

3. **手动测试**
   - Live 模式下同步真实持仓
   - Paper 模式下验证提示信息
   - 在 Polymarket 网站交易后同步验证

## 依赖

- CLOB API 的 `/balances` 端点
- 钱包地址配置 (YOUR_PROXY_WALLET)

## 风险

| 风险 | 缓解措施 |
|------|----------|
| API 调用失败 | 返回友好提示，支持重试 |
| 大量持仓 | 分页处理，后台异步同步 |
| 持仓已结算 | 正确处理已结算市场的持仓 |

## Story Points

估计: 3 SP
