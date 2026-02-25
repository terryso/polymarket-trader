# Story 10.6: Dashboard 退出策略管理

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **用户**,
I want **在 Dashboard 上查看和配置退出策略**,
So that **我能够方便地调整退出参数和查看历史退出记录**.

## Acceptance Criteria

**Given** Epic 7 Dashboard 已实现
**When** 扩展 Dashboard 添加退出策略功能
**Then** 在设置页面添加退出策略配置:

1. **设置页面退出策略配置表单:**
   - 止盈开关 + 百分比输入 (如 50%)
   - 止损开关 + 百分比输入 (如 -30%)
   - 时间退出开关 + 小时数输入 (如 72h)
   - 信号退出开关
   - 保存按钮 -> 调用 PUT /api/settings/exit-strategy

2. **持仓列表增强:**
   - 显示当前价格距离止盈/止损的百分比距离
   - 显示持仓已持续时间
   - 添加"手动退出"按钮 (调用 POST /api/positions/{id}/exit)
   - 退出确认对话框

3. **后端 API:**
   - `GET /api/settings/exit-strategy` - 获取退出策略配置
   - `PUT /api/settings/exit-strategy` - 更新退出策略配置
   - `POST /api/positions/{id}/exit` - 手动退出指定持仓

4. **交易历史中标记退出类型:**
   - 止盈 (take_profit) -> 绿色标签
   - 止损 (stop_loss) -> 红色标签
   - 时间退出 (time_exit) -> 黄色标签
   - 信号反转 (signal_exit) -> 蓝色标签
   - 手动退出 (manual) -> 灰色标签

5. **响应式设计:**
   - 移动端适配
   - 表单在移动端垂直排列
   - 表格在小屏幕上水平滚动

## Tasks / Subtasks

- [x] Task 1: 创建退出策略 API 路由 (AC: #3)
  - [x] 1.1 创建 `src/dashboard/routes/settings.py`
  - [x] 1.2 实现 `GET /api/settings/exit-strategy` 端点
  - [x] 1.3 实现 `PUT /api/settings/exit-strategy` 端点
  - [x] 1.4 创建 `ExitStrategyConfigRequest` 和 `ExitStrategyConfigResponse` 模型
  - [x] 1.5 在 `app.py` 中注册 settings 路由

- [x] Task 2: 实现手动退出持仓 API (AC: #3)
  - [x] 2.1 在 `src/dashboard/routes/positions.py` 添加 `POST /{position_id}/exit` 端点
  - [x] 2.2 创建 `ManualExitRequest` 和 `ManualExitResponse` 模型
  - [x] 2.3 调用 `LiveTradingExecutor.sell_position` 执行卖出
  - [x] 2.4 更新持仓状态为 CLOSED
  - [x] 2.5 记录退出原因为 "manual"

- [x] Task 3: 扩展交易历史 API 显示退出类型 (AC: #4)
  - [x] 3.1 在 `TradeResponse` 模型中添加 `exit_type` 字段
  - [x] 3.2 从关联的 position 获取 exit_reason
  - [x] 3.3 更新 `src/dashboard/routes/trades.py` 返回退出类型

- [x] Task 4: 创建退出策略设置前端组件 (AC: #1, #5)
  - [x] 4.1 创建 `dashboard/src/components/settings/ExitStrategySettings.tsx`
  - [x] 4.2 创建 `ExitStrategyForm` 组件 (止盈/止损/时间/信号开关和输入)
  - [x] 4.3 使用 shadcn/ui Switch, Input, Button 组件
  - [x] 4.4 实现表单验证 (百分比范围、必填项)
  - [x] 4.5 集成 TanStack Query 进行 API 调用
  - [x] 4.6 添加加载状态和错误处理
  - [x] 4.7 添加保存成功/失败的 Toast 提示

- [x] Task 5: 增强持仓列表组件 (AC: #2, #5)
  - [x] 5.1 在 `Positions.tsx` 添加退出距离列
  - [x] 5.2 添加持仓持续时间列
  - [x] 5.3 添加"手动退出"按钮
  - [x] 5.4 创建 `ConfirmExitDialog` 确认对话框组件
  - [x] 5.5 实现手动退出 API 调用
  - [x] 5.6 添加退出成功/失败的 Toast 提示

- [x] Task 6: 更新交易历史显示退出类型标签 (AC: #4, #5)
  - [x] 6.1 在 `Trades.tsx` 添加退出类型列
  - [x] 6.2 创建 `ExitTypeBadge` 组件 (不同颜色标签)
  - [x] 6.3 实现退出类型中文映射

- [x] Task 7: 更新设置页面集成退出策略组件 (AC: #1)
  - [x] 7.1 修改 `Settings.tsx` 添加退出策略部分
  - [x] 7.2 使用 Tabs 或 Sections 组织设置内容
  - [x] 7.3 保持现有设置内容不变

- [x] Task 8: 创建前端类型定义 (AC: All)
  - [x] 8.1 创建 `dashboard/src/types/exitStrategy.ts`
  - [x] 8.2 定义 `ExitStrategyConfig` 接口
  - [x] 8.3 定义 `ManualExitRequest` 接口
  - [x] 8.4 定义 `ManualExitResponse` 接口

- [x] Task 9: 创建自定义 Hooks (AC: All)
  - [x] 9.1 创建 `useExitStrategyConfig` hook
  - [x] 9.2 创建 `useManualExit` hook
  - [x] 9.3 使用 TanStack Query 的 useMutation 和 useQuery

- [ ] Task 10: 编写测试 (AC: All)
  - [ ] 10.1 创建 `tests/test_dashboard/test_settings_routes.py`
  - [ ] 10.2 测试 GET/PUT 退出策略配置 API
  - [ ] 10.3 扩展 `test_positions_routes.py` 测试手动退出 API
  - [ ] 10.4 创建 `ExitStrategySettings.test.tsx`
  - [ ] 10.5 创建 `ConfirmExitDialog.test.tsx`
  - [ ] 10.6 扩展 `Positions.test.tsx` 测试退出按钮

- [ ] Task 11: 代码质量检查 (AC: All)
  - [ ] 11.1 运行 `mypy src/dashboard/` 无错误
  - [ ] 11.2 运行 `black --check src/` 通过
  - [ ] 11.3 运行 `isort --check src/` 通过
  - [ ] 11.4 运行 `npm run lint` (dashboard/) 通过
  - [ ] 11.5 运行完整测试套件确保通过

## Dev Notes

### 现有代码分析

**Settings 页面 (`dashboard/src/pages/Settings.tsx`):**
- 当前只显示配置查看（脱敏）
- 需要扩展为可编辑的设置页面
- 使用 Card 组件组织内容

**Positions 页面 (`dashboard/src/pages/Positions.tsx`):**
- 显示当前持仓列表
- 使用 Table 组件
- 已有 PnL 显示

**ExitStrategySettings 配置 (`src/config.py`):**
```python
class ExitStrategySettings(BaseEnvSettings):
    take_profit_enabled: bool = True
    take_profit_pct: float = Field(default=0.50, ge=0, le=1)
    stop_loss_enabled: bool = True
    stop_loss_pct: float = Field(default=-0.30, ge=-1, le=0)
    time_exit_enabled: bool = True
    time_exit_hours: int = Field(default=72, ge=1)
    signal_exit_enabled: bool = True
    exit_check_interval_minutes: int = Field(default=1, ge=1)
```

**ExitReason 枚举 (`src/trading/exit_checker.py`):**
```python
class ExitReason(str, Enum):
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TIME_EXIT = "time_exit"
    SIGNAL_EXIT = "signal_exit"
```

**LiveTradingExecutor (`src/trading/live_trading.py`):**
- 已有 `sell_position` 方法
- 接收 `reason` 参数记录退出原因

### 实现模板

**后端 API - Settings Routes:**

```python
# src/dashboard/routes/settings.py
"""Settings API routes.

Story 10.6: Dashboard 退出策略管理
"""

from __future__ import annotations

__all__ = ["router"]

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.config import settings, ExitStrategySettings
from src.models.api_response import ApiResponse

router = APIRouter()


class ExitStrategyConfigResponse(BaseModel):
    """Exit strategy configuration response."""

    take_profit_enabled: bool
    take_profit_pct: float
    stop_loss_enabled: bool
    stop_loss_pct: float
    time_exit_enabled: bool
    time_exit_hours: int
    signal_exit_enabled: bool
    exit_check_interval_minutes: int


class ExitStrategyConfigRequest(BaseModel):
    """Exit strategy configuration update request."""

    take_profit_enabled: bool | None = None
    take_profit_pct: float | None = Field(default=None, ge=0, le=1)
    stop_loss_enabled: bool | None = None
    stop_loss_pct: float | None = Field(default=None, ge=-1, le=0)
    time_exit_enabled: bool | None = None
    time_exit_hours: int | None = Field(default=None, ge=1)
    signal_exit_enabled: bool | None = None
    exit_check_interval_minutes: int | None = Field(default=None, ge=1)


@router.get(
    "/exit-strategy",
    response_model=ApiResponse[ExitStrategyConfigResponse],
    summary="Get exit strategy configuration",
)
async def get_exit_strategy_config() -> ApiResponse[ExitStrategyConfigResponse]:
    """Get current exit strategy configuration."""
    config = settings.exit_strategy
    response = ExitStrategyConfigResponse(
        take_profit_enabled=config.take_profit_enabled,
        take_profit_pct=config.take_profit_pct,
        stop_loss_enabled=config.stop_loss_enabled,
        stop_loss_pct=config.stop_loss_pct,
        time_exit_enabled=config.time_exit_enabled,
        time_exit_hours=config.time_exit_hours,
        signal_exit_enabled=config.signal_exit_enabled,
        exit_check_interval_minutes=config.exit_check_interval_minutes,
    )
    return ApiResponse(success=True, data=response, error=None)


@router.put(
    "/exit-strategy",
    response_model=ApiResponse[ExitStrategyConfigResponse],
    summary="Update exit strategy configuration",
)
async def update_exit_strategy_config(
    request: ExitStrategyConfigRequest,
) -> ApiResponse[ExitStrategyConfigResponse]:
    """Update exit strategy configuration.

    Note: This updates runtime settings. For persistent changes,
    update the .env file.
    """
    # Update runtime settings
    config = settings.exit_strategy
    update_data = request.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if value is not None and hasattr(config, key):
            setattr(config, key, value)

    response = ExitStrategyConfigResponse(
        take_profit_enabled=config.take_profit_enabled,
        take_profit_pct=config.take_profit_pct,
        stop_loss_enabled=config.stop_loss_enabled,
        stop_loss_pct=config.stop_loss_pct,
        time_exit_enabled=config.time_exit_enabled,
        time_exit_hours=config.time_exit_hours,
        signal_exit_enabled=config.signal_exit_enabled,
        exit_check_interval_minutes=config.exit_check_interval_minutes,
    )
    return ApiResponse(success=True, data=response, error=None)
```

**后端 API - Manual Exit:**

```python
# src/dashboard/routes/positions.py (additions)

class ManualExitResponse(BaseModel):
    """Manual exit response model."""

    success: bool
    position_id: int
    market_id: str
    shares_sold: float
    avg_price: float
    total_value: float
    realized_pnl: float | None = None
    exit_type: str = "manual"


@router.post(
    "/{position_id}/exit",
    response_model=ApiResponse[ManualExitResponse],
    summary="Manually exit a position",
    description="Sell all shares of a position at current market price.",
)
async def manual_exit_position(
    position_id: int,
    repo: PositionRepository = Depends(get_position_repository),
) -> ApiResponse[ManualExitResponse]:
    """Manually exit a position.

    Args:
        position_id: Position ID to exit
        repo: PositionRepository dependency

    Returns:
        Exit result with sale details
    """
    from src.trading.live_trading import LiveTradingExecutor
    from src.trading.exit_checker import ExitReason

    logger.info(f"💰 Manual exit requested for position {position_id}")

    # Get position
    position = await repo.get_by_id(position_id)
    if position is None:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.NOT_FOUND,
                    "message": f"Position not found: {position_id}",
                },
            },
        )

    if position.status != PositionStatus.OPEN:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR,
                    "message": f"Position {position_id} is not open (status: {position.status})",
                },
            },
        )

    # Execute sell
    try:
        executor = LiveTradingExecutor()
        result = await executor.sell_position(
            position=position,
            reason=ExitReason.MANUAL.value if hasattr(ExitReason, 'MANUAL') else "manual",
        )

        response = ManualExitResponse(
            success=result.success,
            position_id=position_id,
            market_id=position.market_id,
            shares_sold=position.shares,
            avg_price=position.avg_price,
            total_value=result.total_value,
            realized_pnl=result.realized_pnl,
            exit_type="manual",
        )

        if result.success:
            logger.info(f"💰 Manual exit successful for position {position_id}")
            return ApiResponse(success=True, data=response, error=None)
        else:
            logger.warning(f"💰 Manual exit failed for position {position_id}: {result.error_message}")
            return ApiResponse(
                success=False,
                data=response,
                error=ErrorDetail(
                    code=ErrorCode.TRADING_ERROR,
                    message=result.error_message or "Exit failed",
                ),
            )
    except Exception as e:
        logger.error(f"💰 Manual exit error for position {position_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": str(e),
                },
            },
        )
```

**前端 - Exit Strategy Settings 组件:**

```typescript
// dashboard/src/components/settings/ExitStrategySettings.tsx
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { fetchExitStrategyConfig, updateExitStrategyConfig } from "@/api/settings";
import type { ExitStrategyConfig } from "@/types/exitStrategy";

export function ExitStrategySettings() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ["exitStrategyConfig"],
    queryFn: fetchExitStrategyConfig,
  });

  const mutation = useMutation({
    mutationFn: updateExitStrategyConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["exitStrategyConfig"] });
      toast({ title: "设置已保存", description: "退出策略配置已更新" });
    },
    onError: (error) => {
      toast({
        title: "保存失败",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // ... form state and handlers

  return (
    <Card>
      <CardHeader>
        <CardTitle>退出策略</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Take Profit */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label>止盈</Label>
            <p className="text-sm text-muted-foreground">
              盈利达到指定百分比时自动卖出
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={config?.take_profit_enabled}
              onCheckedChange={/* handler */}
            />
            <Input
              type="number"
              value={config?.take_profit_pct * 100}
              className="w-20"
              suffix="%"
            />
          </div>
        </div>

        {/* Stop Loss */}
        {/* Time Exit */}
        {/* Signal Exit */}
        {/* Save Button */}
      </CardContent>
    </Card>
  );
}
```

**前端 - Confirm Exit Dialog:**

```typescript
// dashboard/src/components/positions/ConfirmExitDialog.tsx
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { Position } from "@/types/position";

interface ConfirmExitDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  position: Position | null;
  onConfirm: () => void;
  isLoading: boolean;
}

export function ConfirmExitDialog({
  open,
  onOpenChange,
  position,
  onConfirm,
  isLoading,
}: ConfirmExitDialogProps) {
  if (!position) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>确认退出持仓</DialogTitle>
          <DialogDescription>
            确定要手动退出该持仓吗？此操作不可撤销。
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">市场</span>
              <span>{position.market_title}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">方向</span>
              <span>{position.outcome}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">份额</span>
              <span>{position.shares.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">当前盈亏</span>
              <span className={position.pnl >= 0 ? "text-green-600" : "text-red-600"}>
                {position.pnl >= 0 ? "+" : ""}{position.pnl.toFixed(2)} ({position.pnl_pct?.toFixed(1)}%)
              </span>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? "处理中..." : "确认退出"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

**前端 - Exit Type Badge:**

```typescript
// dashboard/src/components/trades/ExitTypeBadge.tsx
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const EXIT_TYPE_CONFIG: Record<string, { label: string; className: string }> = {
  take_profit: { label: "止盈", className: "bg-green-100 text-green-800" },
  stop_loss: { label: "止损", className: "bg-red-100 text-red-800" },
  time_exit: { label: "时间退出", className: "bg-yellow-100 text-yellow-800" },
  signal_exit: { label: "信号反转", className: "bg-blue-100 text-blue-800" },
  manual: { label: "手动退出", className: "bg-gray-100 text-gray-800" },
};

interface ExitTypeBadgeProps {
  exitType: string | null | undefined;
}

export function ExitTypeBadge({ exitType }: ExitTypeBadgeProps) {
  if (!exitType) return null;

  const config = EXIT_TYPE_CONFIG[exitType] || {
    label: exitType,
    className: "bg-gray-100 text-gray-800",
  };

  return (
    <Badge variant="secondary" className={cn("font-normal", config.className)}>
      {config.label}
    </Badge>
  );
}
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增文件:**
```
src/dashboard/routes/
└── settings.py           # 新增: 设置 API 路由

dashboard/src/components/
├── settings/
│   └── ExitStrategySettings.tsx  # 新增: 退出策略设置组件
├── positions/
│   └── ConfirmExitDialog.tsx     # 新增: 退出确认对话框
└── trades/
    └── ExitTypeBadge.tsx         # 新增: 退出类型标签

dashboard/src/types/
└── exitStrategy.ts       # 新增: 退出策略类型定义

dashboard/src/hooks/
├── useExitStrategyConfig.ts  # 新增: 退出策略配置 hook
└── useManualExit.ts          # 新增: 手动退出 hook

dashboard/src/api/
└── settings.ts           # 新增: 设置 API 函数
```

**修改文件:**
```
src/dashboard/app.py                    # 注册 settings 路由
src/dashboard/routes/positions.py       # 添加手动退出端点
src/dashboard/routes/trades.py          # 返回退出类型
dashboard/src/pages/Settings.tsx        # 集成退出策略设置
dashboard/src/pages/Positions.tsx       # 添加退出按钮和距离显示
dashboard/src/pages/Trades.tsx          # 显示退出类型标签
```

### 依赖关系

**本故事依赖:**
- Epic 7: Dashboard 后端 API (FastAPI, 路由模式)
- Story 10.1: 卖出执行器 (LiveTradingExecutor.sell_position)
- Story 10.2: 退出策略配置 (ExitStrategySettings)
- Story 10.3: 退出条件检查器 (ExitReason 枚举)

### 实现注意事项

**关键点:**

1. **配置更新是运行时的**: PUT API 只更新内存中的配置，持久化需要修改 .env
2. **手动退出需要确认**: 使用 Dialog 组件确认，防止误操作
3. **退出类型颜色编码**: 止盈(绿)、止损(红)、时间(黄)、信号(蓝)、手动(灰)
4. **响应式设计**: 移动端需要垂直布局，表格需要水平滚动
5. **错误处理**: API 调用失败显示 Toast 错误提示
6. **乐观更新**: 考虑使用 TanStack Query 的乐观更新提升用户体验

**与现有代码的集成:**
- 使用现有的 ApiResponse 格式
- 使用现有的 shadcn/ui 组件
- 遵循现有的路由命名规范

### 测试策略

**后端测试:**
```python
# tests/test_dashboard/test_settings_routes.py
"""Tests for settings API routes.

Story 10.6: Dashboard 退出策略管理
"""

import pytest
from httpx import AsyncClient
from src.dashboard.app import create_app


@pytest.fixture
async def client():
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestExitStrategySettings:
    """Tests for exit strategy settings API."""

    @pytest.mark.asyncio
    async def test_get_exit_strategy_config(self, client: AsyncClient):
        """Test getting exit strategy configuration."""
        response = await client.get("/api/settings/exit-strategy")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "take_profit_enabled" in data["data"]

    @pytest.mark.asyncio
    async def test_update_exit_strategy_config(self, client: AsyncClient):
        """Test updating exit strategy configuration."""
        response = await client.put(
            "/api/settings/exit-strategy",
            json={"take_profit_pct": 0.60},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["take_profit_pct"] == 0.60
```

**前端测试:**
```typescript
// ExitStrategySettings.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ExitStrategySettings } from "./ExitStrategySettings";

const wrapper = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("ExitStrategySettings", () => {
  it("renders exit strategy settings card", () => {
    render(<ExitStrategySettings />, { wrapper });
    expect(screen.getByText("退出策略")).toBeInTheDocument();
  });

  it("shows take profit toggle and input", () => {
    render(<ExitStrategySettings />, { wrapper });
    expect(screen.getByText("止盈")).toBeInTheDocument();
  });
});
```

### References

- [Source: epics.md#Story 10.6] - 原始 Story 定义
- [Source: src/config.py#ExitStrategySettings] - 退出策略配置类
- [Source: src/trading/exit_checker.py#ExitReason] - 退出原因枚举
- [Source: src/trading/live_trading.py] - LiveTradingExecutor
- [Source: src/dashboard/routes/positions.py] - Positions API 模式参考
- [Source: dashboard/src/pages/Settings.tsx] - 现有设置页面
- [Source: dashboard/src/pages/Positions.tsx] - 现有持仓页面
- [Source: architecture.md#Frontend Architecture] - 前端技术栈和组件库
- [Source: architecture.md#API & Communication Patterns] - API 响应格式
- [Source: project-context.md] - 代码规范和模式

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

