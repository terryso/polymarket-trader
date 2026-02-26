/**
 * Positions Page.
 *
 * Displays list of open positions with exit functionality.
 * Positions are auto-synced from Polymarket.
 *
 * Story 7.6: 前端 API 集成
 * Story 5.7: 同步实际持仓
 * Story 10.6: Dashboard 退出策略管理 - 手动退出按钮
 */

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { usePositions } from "@/hooks/usePositions";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { Wallet, AlertCircle, LogOut, Clock, Info } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { positionsApi } from "@/api/positions";
import type { PositionListItem, ManualExitResponse } from "@/api/types";
import { ConfirmExitDialog } from "@/components/positions/ConfirmExitDialog";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { useQuery } from "@tanstack/react-query";

// Minimum shares threshold to display (filter out dust positions)
const MIN_SHARES_THRESHOLD = 0.1;

// Cache status type
interface CacheStatus {
  cache_freshness: string;
  cache_age_seconds: number;
  total_positions: number;
}

const Positions = () => {
  const { toast } = useToast();
  const { data: positions, isLoading, error } = usePositions();

  // Get cache status
  const { data: cacheStatus } = useQuery({
    queryKey: ['positions', 'cache', 'status'],
    queryFn: async (): Promise<CacheStatus> => {
      const response = await fetch('/api/positions/cache/status');
      if (!response.ok) throw new Error('Failed to fetch cache status');
      const json = await response.json();
      return json.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Exit dialog state
  const [exitDialogOpen, setExitDialogOpen] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<PositionListItem | null>(null);
  const [isExiting, setIsExiting] = useState(false);

  const queryClient = useQueryClient();

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

  // Filter out dust positions (shares < threshold)
  const significantPositions = (positions ?? []).filter(p => p.shares >= MIN_SHARES_THRESHOLD);
  const dustCount = (positions ?? []).length - significantPositions.length;

  // Calculate totals for significant positions only
  const totalValue = significantPositions.reduce(
    (s, p) => s + (p.current_value ?? p.shares * p.avg_price),
    0
  );
  const totalPnL = significantPositions.reduce((s, p) => s + (p.pnl ?? 0), 0);

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

  // Format cache freshness
  const formatFreshness = (freshness: string, ageSeconds: number): string => {
    if (freshness === "FRESH") return "新鲜";
    if (freshness === "STALE") return `过期 ${ageSeconds}s`;
    return "无缓存";
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
            <p className="text-sm text-muted-foreground mt-1">
              当前持有头寸
              {cacheStatus && (
                <span className="ml-2 text-xs">
                  (数据状态: {formatFreshness(cacheStatus.cache_freshness, cacheStatus.cache_age_seconds)})
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Dust positions info */}
        {dustCount > 0 && (
          <Alert variant="default" className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
            <Info className="h-4 w-4 text-blue-600" />
            <AlertDescription className="text-blue-700 dark:text-blue-400">
              已隐藏 {dustCount} 个小额持仓（&lt; {MIN_SHARES_THRESHOLD} 份额）
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
          {significantPositions.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead className="text-muted-foreground">市场 ID</TableHead>
                    <TableHead className="text-muted-foreground">方向</TableHead>
                    <TableHead className="text-muted-foreground text-right">份额</TableHead>
                    <TableHead className="text-muted-foreground text-right">成本价</TableHead>
                    <TableHead className="text-muted-foreground text-right">当前价</TableHead>
                    <TableHead className="text-muted-foreground text-right">当前价值</TableHead>
                    <TableHead className="text-muted-foreground text-right">PnL</TableHead>
                    <TableHead className="text-muted-foreground text-right hidden md:table-cell">持有时间</TableHead>
                    <TableHead className="text-muted-foreground text-center">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {significantPositions.map((p) => (
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
                        {p.cur_price !== null && p.cur_price !== undefined ? `$${p.cur_price.toFixed(4)}` : '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        ${(p.current_value ?? p.shares * (p.cur_price ?? p.avg_price)).toFixed(2)}
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
