# Story 7.8: 预测详情抽屉组件 - 展示 LLM 分析过程

Status: done

## Story

As a **用户**,
I want **在预测记录页面点击某条预测时，能看到完整的 LLM 分析过程**,
So that **我能够理解 LLM 为什么做出这个预测，包括分析理由和关键假设**.

## Acceptance Criteria

**Given** Story 7.4 预测与统计 API 已实现
**When** 实现预测详情展示功能
**Then** 创建预测详情抽屉组件 `dashboard/src/components/predictions/PredictionDetailSheet.tsx`:

- 使用 Sheet 组件（侧边抽屉）
- 点击预测行的"详情"按钮时打开
- 调用 `usePrediction(id)` 获取完整预测详情
- 展示内容包含:
  - 市场标题
  - LLM 模型名称 (`model_used`)
  - 预测概率和置信度
  - **分析过程** (`reasoning`) - 主要内容，长文本格式化展示
  - **关键假设** (`key_assumptions`) - 列表形式展示
  - 验证结果（如有）

**And** 修改预测列表页面 `dashboard/src/pages/Predictions.tsx`:

- 添加状态管理: `selectedPredictionId` 和 `sheetOpen`
- 在表格操作列添加"详情"按钮（Eye 图标）
- 集成 `PredictionDetailSheet` 组件

**And** 处理加载状态:

- Sheet 打开时显示骨架屏
- 数据加载完成后渲染内容

**And** 添加单元测试:

- 测试组件渲染
- 测试数据加载状态
- 测试空数据处理

## Tasks / Subtasks

- [x] Task 1: 创建预测详情抽屉组件 (AC: 1)
  - [x] 1.1 创建 `dashboard/src/components/predictions/PredictionDetailSheet.tsx`
  - [x] 1.2 使用 Sheet 组件创建侧边抽屉
  - [x] 1.3 定义组件 props (predictionId, open, onOpenChange)
  - [x] 1.4 实现骨架屏加载状态
  - [x] 1.5 展示市场标题
  - [x] 1.6 展示 LLM 模型名称
  - [x] 1.7 展示预测概率和置信度
  - [x] 1.8 格式化展示分析过程 (reasoning)
  - [x] 1.9 列表形式展示关键假设 (key_assumptions)
  - [x] 1.10 展示验证结果 (如有)

- [x] Task 2: 确保预测详情 API 支持 (AC: 1)
  - [x] 2.1 检查 `GET /api/predictions/{id}` 端点是否返回完整字段
  - [x] 2.2 确保 API 返回包含: reasoning, key_assumptions, model_used
  - [x] 2.3 如有必要，更新前端 API 类型定义

- [x] Task 3: 更新预测列表页面 (AC: 2)
  - [x] 3.1 在 `Predictions.tsx` 添加 selectedPredictionId 状态
  - [x] 3.2 添加 sheetOpen 状态
  - [x] 3.3 在表格操作列添加"详情"按钮 (Eye 图标)
  - [x] 3.4 点击按钮时设置 predictionId 并打开 sheet
  - [x] 3.5 集成 PredictionDetailSheet 组件

- [x] Task 4: 更新 API 和 hooks (AC: 1)
  - [x] 4.1 检查 `usePrediction(id)` hook 是否存在
  - [x] 4.2 如不存在，创建 usePrediction hook
  - [x] 4.3 更新类型定义确保包含所有必要字段

- [x] Task 5: 编写单元测试 (AC: 4)
  - [x] 5.1 创建 `dashboard/src/components/predictions/PredictionDetailSheet.test.tsx`
  - [x] 5.2 测试组件正常渲染
  - [x] 5.3 测试加载状态显示骨架屏
  - [x] 5.4 测试空数据处理
  - [x] 5.5 测试完整数据展示

- [x] Task 6: 代码质量检查 (AC: All)
  - [x] 6.1 运行 `npm run lint` 通过
  - [x] 6.2 运行 `npm run type-check` 通过
  - [x] 6.3 运行 `npm test` 通过

## Dev Notes

### UI 设计参考

使用 shadcn/ui Sheet 组件作为侧边抽屉：

```tsx
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
```

### 数据结构

预测详情 API 应返回：

```typescript
interface PredictionDetail {
  id: number;
  market_id: string;
  market_title: string;
  predicted_probability: number;
  confidence: number;
  reasoning: string;  // LLM 分析过程 (重点)
  key_assumptions: string[];  // 关键假设列表
  model_used: string;
  recommendation: string;
  actual_outcome?: string;
  is_correct?: boolean;
  validated_at?: string;
  created_at: string;
}
```

### 组件结构

```
PredictionDetailSheet
├── SheetHeader (市场标题)
├── 骨架屏 (加载中)
├── 内容区域
│   ├── 基本信息 (模型、概率、置信度)
│   ├── 分析过程 (reasoning) - 重点突出
│   ├── 关键假设 (列表)
│   └── 验证结果 (如有)
```

### 样式建议

- 分析过程使用白色背景卡片，适当内边距
- 关键假设使用 Bullet 列表
- 验证结果使用 Badge 显示正确/错误

## Out of Scope

- 编辑预测内容
- 删除预测
- 导出预测详情
- 分享预测链接
