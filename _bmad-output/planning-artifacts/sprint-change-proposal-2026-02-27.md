# Sprint Change Proposal: 持仓功能废弃代码清理

**日期**: 2026-02-27
**项目**: polymarket-trader
**提案人**: Nick
**状态**: 待审批

---

## 1. 问题摘要

### 1.1 问题描述

持仓功能已完成架构调整（Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源），但代码中仍保留了废弃的同步相关端点和函数，需要清理以提高代码可维护性。

### 1.2 发现背景

- **触发来源**: 代码审查
- **相关 Story**: 5-7-position-sync (同步实际持仓)
- **相关 Tech-Spec**: 持仓数据源重构 - Polymarket 作为单一数据源

### 1.3 证据

| 位置 | 废弃代码 | 说明 |
|------|----------|------|
| `src/dashboard/routes/positions.py` | `/sync`, `/sync/status` 端点 | 已标记 `deprecated=True` |
| `dashboard/src/api/positions.ts` | `syncPositions()`, `fetchPositionSyncStatus()` | 不再被前端页面使用 |
| `dashboard/src/api/types.ts` | `PositionSyncStatus`, `PositionSyncResult` | 持仓同步专用类型 |

---

## 2. 影响分析

### 2.1 Epic 影响

| Epic | 状态 | 影响 |
|------|------|------|
| Epic 5: Paper Trading | Done | 无 - 功能已完成 |
| Epic 7: Dashboard 后端 API | Done | 无 - 功能已完成 |

**结论**: 不需要重新开放任何 Epic，这是代码清理工作。

### 2.2 文档冲突

| 文档 | 影响 | 需要更新 |
|------|------|----------|
| PRD | 无冲突 | 否 |
| Architecture | API 设计部分 | 是 - 更新端点列表 |
| UI/UX | 无冲突 | 否 |

### 2.3 技术影响

| 组件 | 变更类型 | 风险 |
|------|----------|------|
| 后端 API 路由 | 移除废弃端点 | 低 |
| 前端 API 模块 | 移除废弃函数 | 低 |
| 前端类型定义 | 移除废弃类型 | 低 |
| 测试文件 | 可能需要更新 | 低 |

---

## 3. 推荐方案

### 3.1 选择方案

**直接调整** - 移除废弃代码，保持现有功能不变

### 3.2 理由

1. **工作量低** - 仅需修改 3-4 个文件
2. **风险低** - 移除的代码已标记为废弃且未被使用
3. **无功能影响** - 前端页面已不使用这些端点
4. **提高可维护性** - 减少代码复杂度

---

## 4. 详细变更提案

### 4.1 后端变更

#### 文件: `src/dashboard/routes/positions.py`

**移除以下代码:**

```python
# Lines 271-300: 废弃的响应模型
class PositionSyncStatusResponse(BaseModel):
    """Position sync status response model. Deprecated."""
    last_sync_at: str | None = None
    is_syncing: bool = False
    can_sync: bool = False
    last_error: str | None = None
    total_positions: int = 0

class PositionSyncResultResponse(BaseModel):
    """Position sync result response model. Deprecated."""
    new_positions: int = 0
    updated_positions: int = 0
    closed_positions: int = 0
    unchanged_positions: int = 0
    total_fetched: int = 0
    last_sync_at: str
    error: str | None = None

# Lines 685-773: 废弃的端点
@router.get("/sync/status", deprecated=True)
async def get_position_sync_status(): ...

@router.post("/sync", deprecated=True)
async def sync_positions(): ...
```

**保留的替代端点:**

- `GET /api/positions/cache/status` - 获取缓存状态
- `POST /api/positions/refresh` - 刷新缓存

---

### 4.2 前端变更

#### 文件: `dashboard/src/api/positions.ts`

**移除以下代码:**

```typescript
/**
 * Get position sync status.
 * Story 5.7: 同步实际持仓
 */
export async function fetchPositionSyncStatus(): Promise<PositionSyncStatus> {
  return get<PositionSyncStatus>('/api/positions/sync/status');
}

/**
 * Sync positions from Polymarket.
 * Story 5.7: 同步实际持仓
 */
export async function syncPositions(): Promise<PositionSyncResult> {
  return post<PositionSyncResult>('/api/positions/sync');
}
```

**更新 positionsApi 对象:**

```typescript
// 旧
export const positionsApi = {
  getList: fetchPositions,
  getById: fetchPosition,
  getSyncStatus: fetchPositionSyncStatus,  // 移除
  sync: syncPositions,                      // 移除
  exit: exitPosition,
};

// 新
export const positionsApi = {
  getList: fetchPositions,
  getById: fetchPosition,
  exit: exitPosition,
};
```

#### 文件: `dashboard/src/api/types.ts`

**移除以下代码:**

```typescript
// ============================================================================
// Position Sync Types (Story 5.7)
// ============================================================================

export interface PositionSyncStatus {
  last_sync_at: string | null;
  is_syncing: boolean;
  can_sync: boolean;
  last_error: string | null;
  total_positions: number;
}

export interface PositionSyncResult {
  new_positions: number;
  updated_positions: number;
  closed_positions: number;
  unchanged_positions: number;
  total_fetched: number;
  last_sync_at: string;
  error: string | null;
}
```

**注意**: `SyncStatus` 和 `SyncResult` (Trade Sync Types, Story 5.6) **保留** - 仍用于交易历史同步。

---

### 4.3 导入更新

#### 文件: `dashboard/src/api/positions.ts`

```typescript
// 旧
import type { PositionListItem, PositionListResponse, PositionResponse, PositionSyncStatus, PositionSyncResult, ManualExitResponse } from './types';

// 新
import type { PositionListItem, PositionListResponse, PositionResponse, ManualExitResponse } from './types';
```

---

## 5. 实施交接

### 5.1 变更范围分类

**Minor** - 可由开发团队直接实施

### 5.2 交接接收人

| 角色 | 负责人 | 职责 |
|------|--------|------|
| 开发团队 | 开发者 | 实施代码变更 |

### 5.3 实施步骤

1. **后端清理**
   - [ ] 移除 `PositionSyncStatusResponse` 和 `PositionSyncResultResponse` 模型
   - [ ] 移除 `/sync/status` 和 `/sync` 端点
   - [ ] 运行后端测试: `pytest tests/ -v`

2. **前端清理**
   - [ ] 移除 `fetchPositionSyncStatus()` 和 `syncPositions()` 函数
   - [ ] 更新 `positionsApi` 对象
   - [ ] 移除 `PositionSyncStatus` 和 `PositionSyncResult` 类型
   - [ ] 更新导入语句
   - [ ] 运行前端测试: `cd dashboard && npm test`

3. **验证**
   - [ ] 确认持仓页面正常加载
   - [ ] 确认缓存状态显示正常
   - [ ] 确认刷新功能正常工作
   - [ ] 确认退出持仓功能正常

### 5.4 成功标准

- [ ] 所有测试通过
- [ ] 持仓页面功能正常
- [ ] 无废弃代码残留
- [ ] TypeScript 编译无错误

---

## 6. 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 遗留引用导致编译错误 | 低 | 低 | TypeScript 编译检查 |
| 测试失败 | 低 | 低 | 完整测试套件覆盖 |
| 功能回归 | 低 | 低 | 手动验证持仓页面 |

---

## 7. 附录

### 7.1 相关文件清单

| 文件 | 变更类型 |
|------|----------|
| `src/dashboard/routes/positions.py` | 修改 - 移除代码 |
| `dashboard/src/api/positions.ts` | 修改 - 移除代码 |
| `dashboard/src/api/types.ts` | 修改 - 移除类型 |

### 7.2 不变更的文件

| 文件 | 原因 |
|------|------|
| `src/trading/position_sync.py` | 保留 - 仍提供缓存服务 |
| `dashboard/src/pages/Positions.tsx` | 保留 - 已不使用 sync 函数 |
| `dashboard/src/api/trades.ts` | 保留 - Trade sync 仍需要 |
| `dashboard/src/api/types.ts` (SyncStatus/SyncResult) | 保留 - Trade sync 仍需要 |

---

*Generated by BMAD Correct Course Workflow*
*Date: 2026-02-27*
