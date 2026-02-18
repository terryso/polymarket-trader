# Story 7.7: 最近活动 API 与前端集成

Status: done

## Story

As a **用户**,
I want **Dashboard 首页显示真实的最近活动记录**,
So that **我能够实时了解系统的交易、预测和系统事件**.

## Acceptance Criteria

**Given** Epic 1-6 已完成，Story 7.1-7.6 已实现
**When** 实现最近活动功能
**Then** 后端实现活动记录 API:

- `GET /api/activities` - 获取最近活动列表
- 返回活动类型: trade (交易), prediction (预测), system (系统事件)
- 每条记录包含: id, type, description, time, amount (可选)
- 支持分页和限制返回数量 (默认 10 条)
- 使用统一响应格式

**And** 前端更新 `RecentActivity.tsx`:

- 调用真实 API 替换 mockData
- 处理加载和空数据状态
- 保持现有 UI 样式和交互

**And** 数据来源:

- trade: 来自 trades 表的最近交易记录
- prediction: 来自 predictions 表的最近预测记录
- system: 来自 system_state 表的系统事件 (启动、停止等)

## Tasks / Subtasks

- [ ] Task 1: 定义活动记录数据模型 (AC: 1)
  - [ ] 1.1 在 `src/models/` 创建 `activity.py`
  - [ ] 1.2 定义 `ActivityItem` 模型 (单条活动记录)
  - [ ] 1.3 定义 `ActivityListResponse` 模型 (活动列表响应)
  - [ ] 1.4 定义 `ActivityType` 枚举 (trade, prediction, system)
  - [ ] 1.5 更新 `src/models/__init__.py` 导出新模型

- [ ] Task 2: 实现活动记录 API 端点 (AC: 1)
  - [ ] 2.1 创建 `src/dashboard/routes/activities.py`
  - [ ] 2.2 实现 `GET /api/activities` 路由
  - [ ] 2.3 从 trades 表获取最近交易记录
  - [ ] 2.4 从 predictions 表获取最近预测记录
  - [ ] 2.5 从 system_state 表获取系统事件
  - [ ] 2.6 合并并按时间排序返回最近 N 条
  - [ ] 2.7 在 `app.py` 注册 activities 路由

- [ ] Task 3: 实现前端 API 调用 (AC: 2)
  - [ ] 3.1 在 `dashboard/src/api/` 创建 `activities.ts`
  - [ ] 3.2 定义 ActivityItem 和 ActivityListResponse 类型
  - [ ] 3.3 实现 `getActivities()` API 调用函数
  - [ ] 3.4 更新 `dashboard/src/api/index.ts` 导出

- [ ] Task 4: 创建 React Query hook (AC: 2)
  - [ ] 4.1 在 `dashboard/src/hooks/` 创建 `useActivities.ts`
  - [ ] 4.2 实现 useActivities hook 调用 API
  - [ ] 4.3 更新 `dashboard/src/hooks/index.ts` 导出

- [ ] Task 5: 更新前端组件 (AC: 2)
  - [ ] 5.1 更新 `RecentActivity.tsx` 使用 useActivities hook
  - [ ] 5.2 处理加载状态 (显示 skeleton 或 loading)
  - [ ] 5.3 处理空数据状态
  - [ ] 5.4 处理错误状态
  - [ ] 5.5 保持现有 UI 样式

- [ ] Task 6: 编写单元测试 (AC: All)
  - [ ] 6.1 创建 `tests/test_dashboard/test_routes/test_activities.py`
  - [ ] 6.2 测试 `GET /api/activities` 返回 200
  - [ ] 6.3 测试 `GET /api/activities` 响应格式正确
  - [ ] 6.4 测试 `GET /api/activities` 包含交易活动
  - [ ] 6.5 测试 `GET /api/activities` 包含预测活动
  - [ ] 6.6 测试 `GET /api/activities` 支持分页参数

- [ ] Task 7: 代码质量检查 (AC: All)
  - [ ] 7.1 运行 `mypy src/dashboard/routes/activities.py` 无错误
  - [ ] 7.2 运行 `mypy src/models/activity.py` 无错误
  - [ ] 7.3 运行 `black --check` 通过
  - [ ] 7.4 运行 `isort --check` 通过
  - [ ] 7.5 运行完整测试套件确保通过

## Dev Notes

### 数据来源映射

| 活动类型 | 数据来源 | 描述格式 | 金额 |
|---------|---------|---------|------|
| trade | trades 表 | `{side} {market_title} {outcome} @ ${price}` | amount |
| prediction | predictions 表 | `预测 {market_title} {confidence}% {recommendation}` | null |
| system | system_state 表 | 系统事件描述 (启动、停止等) | null |

### API 响应格式

```json
{
  "success": true,
  "data": [
    {
      "id": "trade-1",
      "type": "trade",
      "description": "买入 特朗普胜选 YES @ $0.65",
      "time": "10:30",
      "amount": 10.0
    },
    {
      "id": "prediction-1",
      "type": "prediction",
      "description": "预测 特朗普胜选 75% YES",
      "time": "09:00",
      "amount": null
    }
  ]
}
```

## Out of Scope

- 活动记录的持久化存储 (使用现有表)
- WebSocket 实时推送
- 活动筛选和搜索
- 活动详情页面
