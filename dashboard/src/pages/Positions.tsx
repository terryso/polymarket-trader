/**
 * Positions Page.
 *
 * Displays list of open positions with exit functionality.
 *
 * Story 7.6: 前端 API 集成
 * Story 5.7: 同步实际持仓
 * Story 10.6: Dashboard 退出策略管理 - 手动退出按钮
 */

import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { usePositions } from "@/hooks/usePositions";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { Wallet, AlertCircle, RefreshCw, CheckCircle2, XCircle, LogOut, Clock } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { positionsApi } from "@/api/positions";
import type { PositionSyncStatus, PositionSyncResult, PositionListItem, ManualExitResponse } from "@/api/types";
import { ConfirmExitDialog } from "@/components/positions/ConfirmExitDialog";

const Positions = () => {
  const { toast } = useToast();
  const { data: positions, isLoading, error } = usePositions();
  const [syncStatus, setSyncStatus] = useState<PositionSyncStatus | null>(null);
  const [syncResult, setSyncResult] = useState<PositionSyncResult | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);

  // Exit dialog state
  const [exitDialogOpen, setExitDialogOpen] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<PositionListItem | null>(null);
  const [isExiting, setIsExiting] = useState(false);

  const queryClient = useQueryClient();

  // Fetch sync status on mount
  useEffect(() => {
    positionsApi.getSyncStatus().then(setSyncStatus).catch(console.error);
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="space-y-6" data-testid="loading-skeleton">
          <div>
            <Skeleton className="h-7 w-24" />
            <Skeleton className="h-5 w-36 mt-1" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
          <Skeleton className="h-64" />
        </div>
      </DashboardLayout>
    );
  }

  // Error state
  if (error) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-bold text-foreground">持仓</h2>
            <p className="text-sm text-muted-foreground mt-1">当前持有头寸</p>
          </div>
          <Alert variant="destructive" data-testid="error-alert">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              无法加载数据: {error.message}
            </AlertDescription>
          </Alert>
        </div>
      </DashboardLayout>
    );
  }

  // Calculate totals
  const totalValue = (positions ?? []).reduce(
    (s, p) => s + (p.current_value ?? p.shares * p.avg_price),
    0
  );
  const totalPnL = (positions ?? []).reduce((s, p) => s + (p.pnl ?? 0), 0);

  // Handle sync
  const handleSync = async () => {
    if (isSyncing || !syncStatus?.can_sync) return;

    setIsSyncing(true);
    setSyncResult(null);

    try {
      const result = await positionsApi.sync();
      setSyncResult(result);
      // Refresh positions list
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      // Update sync status
      const status = await positionsApi.getSyncStatus();
      setSyncStatus(status);
    } catch (err) {
      setSyncResult({
        new_positions: 0,
        updated_positions: 0,
        closed_positions: 0,
        unchanged_positions: 0,
        total_fetched: 0,
        last_sync_at: new Date().toISOString(),
        error: err instanceof Error ? err.message : '同步失败',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  // Handle exit button click
  const handleExitClick = (position: PositionListItem) => {
    setSelectedPosition(position);
    setExitDialogOpen(true);
  };

  // Handle exit confirmation
  const handleExitConfirm = async () => {
    if (!selectedPosition) return;

    setIsExiting(true);

    try {
      const result: ManualExitResponse = await positionsApi.exit(selectedPosition.id);

      if (result.success) {
        toast({
          title: "退出成功",
          description: `已卖出 ${result.shares_sold.toFixed(2)} 份额，价值 $${result.total_value.toFixed(2)}${
            result.realized_pnl !== null
              ? `，盈亏 ${result.realized_pnl >= 0 ? '+' : ''}$${result.realized_pnl.toFixed(2)}`
              : ''
          }`,
        });
        // Refresh positions list
        queryClient.invalidateQueries({ queryKey: ['positions'] });
        queryClient.invalidateQueries({ queryKey: ['trades'] });
      } else {
        toast({
          title: "退出失败",
          description: "操作未能完成",
          variant: "destructive",
        });
      }
    } catch (err) {
      toast({
        title: "退出失败",
        description: err instanceof Error ? err.message : "发生未知错误",
        variant: "destructive",
      });
    } finally {
      setIsExiting(false);
      setExitDialogOpen(false);
      setSelectedPosition(null);
    }
  };

  // Format sync time
  const formatSyncTime = (ts: string | null): string => {
    if (!ts) return "从未同步";
    try {
      const d = new Date(ts);
      return d.toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return ts;
    }
  };

  // Format holding duration
  const formatHoldingDuration = (openedAt: string | null): string => {
    if (!openedAt) return "-";
    try {
      const opened = new Date(openedAt);
      const now = new Date();
      const diffMs = now.getTime() - opened.getTime();
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffHours / 24);

      if (diffDays > 0) {
        return `${diffDays}天 ${diffHours % 24}小时`;
      } else if (diffHours > 0) {
        return `${diffHours}小时`;
      } else {
        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        return `${diffMinutes}分钟`;
      }
    } catch {
      return "-";
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-foreground">持仓</h2>
            <p className="text-sm text-muted-foreground mt-1">当前持有头寸</p>
          </div>

          {/* Sync Section */}
          <div className="flex items-center gap-3">
            {syncStatus && (
              <div className="text-xs text-muted-foreground">
                <span>最后同步: {formatSyncTime(syncStatus.last_sync_at)}</span>
              </div>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleSync}
              disabled={isSyncing || !syncStatus?.can_sync}
              className="h-8"
              data-testid="sync-button"
            >
              {isSyncing ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  同步中...
                </>
              ) : (
                <>
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                  同步
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Sync Result Alert */}
        {syncResult && (
          <Alert variant={syncResult.error ? "destructive" : "default"} data-testid="sync-result">
            {syncResult.error ? (
              <XCircle className="h-4 w-4" />
            ) : (
              <CheckCircle2 className="h-4 w-4" />
            )}
            <AlertDescription>
              {syncResult.error ? (
                syncResult.error
              ) : (
                <span>
                  同步完成: {syncResult.new_positions} 个新增, {syncResult.updated_positions} 个更新, {syncResult.closed_positions} 个关闭
                </span>
              )}
            </AlertDescription>
          </Alert>
        )}

        {/* Can't sync warning */}
        {syncStatus && !syncStatus.can_sync && (
          <Alert variant="default" className="bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800">
            <AlertCircle className="h-4 w-4 text-yellow-600" />
            <AlertDescription className="text-yellow-700 dark:text-yellow-400">
              需要配置 Polymarket API 凭证才能同步持仓。
              请在 .env 文件中设置 PK 和 YOUR_PROXY_WALLET。
            </AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <StatCard
            icon={<Wallet className="h-4 w-4" />}
            title="总持仓价值"
            value={`$${totalValue.toFixed(2)}`}
            testId="stat-total-value"
          />
          <StatCard
            icon={<Wallet className="h-4 w-4" />}
            title="总浮动盈亏"
            value={`${totalPnL >= 0 ? "+" : ""}$${totalPnL.toFixed(2)}`}
            subtitleColor={totalPnL >= 0 ? "profit" : "loss"}
            testId="stat-total-pnl"
          />
        </div>

        <div className="stat-card overflow-hidden p-0" data-testid="positions-table">
          {positions && positions.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead className="text-muted-foreground">市场 ID</TableHead>
                    <TableHead className="text-muted-foreground">方向</TableHead>
                    <TableHead className="text-muted-foreground text-right">份额</TableHead>
                    <TableHead className="text-muted-foreground text-right">成本价</TableHead>
                    <TableHead className="text-muted-foreground text-right">当前价值</TableHead>
                    <TableHead className="text-muted-foreground text-right">PnL</TableHead>
                    <TableHead className="text-muted-foreground text-right hidden md:table-cell">持有时间</TableHead>
                    <TableHead className="text-muted-foreground text-center">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {positions.map((p) => (
                    <TableRow key={p.id} className="border-border hover:bg-accent/50">
                      <TableCell className="font-medium text-foreground max-w-[150px] truncate">{p.market_id}</TableCell>
                      <TableCell>
                        <span className={p.outcome === "YES" ? "badge-profit" : "badge-loss"}>
                          {p.outcome}
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono">{p.shares.toFixed(2)}</TableCell>
                      <TableCell className="text-right font-mono">${p.avg_price.toFixed(4)}</TableCell>
                      <TableCell className="text-right font-mono">
                        ${(p.current_value ?? p.shares * p.avg_price).toFixed(2)}
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-right font-mono font-medium",
                          (p.pnl ?? 0) >= 0 ? "profit-text" : "loss-text"
                        )}
                      >
                        {(p.pnl ?? 0) >= 0 ? "+" : ""}${(p.pnl ?? 0).toFixed(2)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground hidden md:table-cell">
                        <div className="flex items-center justify-end gap-1">
                          <Clock className="h-3 w-3" />
                          {formatHoldingDuration(p.opened_at)}
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleExitClick(p)}
                          className="h-7 text-xs"
                          data-testid={`exit-button-${p.id}`}
                        >
                          <LogOut className="h-3 w-3 mr-1" />
                          退出
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground" data-testid="empty-state">
              暂无持仓数据
            </div>
          )}
        </div>
      </div>

      {/* Exit Confirmation Dialog */}
      <ConfirmExitDialog
        open={exitDialogOpen}
        onOpenChange={setExitDialogOpen}
        position={selectedPosition}
        onConfirm={handleExitConfirm}
        isLoading={isExiting}
      />
    </DashboardLayout>
  );
};

export default Positions;
