import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { PnLChart } from "@/components/dashboard/PnLChart";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { TradingControl } from "@/components/dashboard/TradingControl";
import { useOverview, useSystemStatus } from "@/hooks/useStatistics";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { DollarSign, TrendingUp, Target, Activity, AlertCircle, Wallet, PiggyBank, BarChart3 } from "lucide-react";

const Index = () => {
  const { data: overview, isLoading: overviewLoading, error: overviewError } = useOverview();
  const { data: status, isLoading: statusLoading } = useSystemStatus();

  const isLoading = overviewLoading || statusLoading;

  // Loading state
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="space-y-6" data-testid="loading-skeleton">
          <div>
            <Skeleton className="h-7 w-32" />
            <Skeleton className="h-5 w-48 mt-1" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Skeleton className="lg:col-span-2 h-64" />
            <Skeleton className="h-64" />
          </div>
        </div>
      </DashboardLayout>
    );
  }

  // Error state
  if (overviewError) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-bold text-foreground">Dashboard</h2>
            <p className="text-sm text-muted-foreground mt-1">系统运行概览</p>
          </div>
          <Alert variant="destructive" data-testid="error-alert">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              无法加载数据: {overviewError.message}
            </AlertDescription>
          </Alert>
        </div>
      </DashboardLayout>
    );
  }

  // Calculate derived values
  const totalPnL = overview?.total_pnl ?? 0;
  const totalPnLPercent = (overview?.total_pnl_pct ?? 0) * 100;
  const positionPnL = overview?.position_pnl ?? 0;
  const statusColor = status?.trading_enabled ? "profit" : "muted";

  // Format uptime
  const formatUptime = (hours: number | null | undefined): string => {
    if (hours === null || hours === undefined) return "-";
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return `${h}h ${m}m`;
  };

  // Format currency
  const formatCurrency = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return "-";
    return `$${value.toFixed(2)}`;
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-foreground">Dashboard</h2>
          <p className="text-sm text-muted-foreground mt-1">系统运行概览</p>
        </div>

        {/* Capital Overview Row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard
            icon={<PiggyBank className="h-4 w-4" />}
            title="初始资本"
            value={formatCurrency(overview?.initial_capital)}
            subtitle="投入金额"
            subtitleColor="muted"
            testId="stat-initial-capital"
          />
          <StatCard
            icon={<Wallet className="h-4 w-4" />}
            title="钱包余额"
            value={formatCurrency(overview?.wallet_balance)}
            subtitle="真实 USDC"
            subtitleColor="muted"
            testId="stat-wallet-balance"
          />
          <StatCard
            icon={<BarChart3 className="h-4 w-4" />}
            title="持仓价值"
            value={formatCurrency(overview?.position_value)}
            subtitle={positionPnL >= 0 ? `+$${positionPnL.toFixed(2)}` : `-$${Math.abs(positionPnL).toFixed(2)}`}
            subtitleColor={positionPnL >= 0 ? "profit" : "loss"}
            testId="stat-position-value"
          />
          <StatCard
            icon={<DollarSign className="h-4 w-4" />}
            title="当前资本"
            value={formatCurrency(overview?.current_capital)}
            subtitle="钱包 + 持仓"
            subtitleColor="muted"
            testId="stat-current-capital"
          />
          <StatCard
            icon={<TrendingUp className="h-4 w-4" />}
            title="总盈亏"
            value={`${totalPnL >= 0 ? "+" : ""}$${totalPnL.toFixed(2)}`}
            subtitle={`${totalPnLPercent >= 0 ? "+" : ""}${totalPnLPercent.toFixed(1)}%`}
            subtitleColor={totalPnL >= 0 ? "profit" : "loss"}
            testId="stat-total-pnl"
          />
          <StatCard
            icon={<Activity className="h-4 w-4" />}
            title="系统状态"
            value={status?.trading_enabled ? "🟢 运行中" : "🟡 已暂停"}
            subtitle={formatUptime(status?.uptime_hours)}
            subtitleColor={statusColor as "profit" | "loss" | "muted"}
            testId="stat-system-status"
          />
        </div>

        {/* Secondary Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            icon={<Target className="h-4 w-4" />}
            title="胜率"
            value={`${((overview?.win_rate ?? 0) * 100).toFixed(1)}%`}
            subtitle={overview ? `${overview.winning_trades}/${overview.total_trades} 胜` : "-"}
            testId="stat-win-rate"
          />
          <StatCard
            icon={<BarChart3 className="h-4 w-4" />}
            title="持仓数量"
            value={`${overview?.open_positions ?? 0}`}
            subtitle="个仓位"
            subtitleColor="muted"
            testId="stat-open-positions"
          />
          <StatCard
            icon={<Activity className="h-4 w-4" />}
            title="交易模式"
            value={overview?.mode === "LIVE" ? "🔴 实盘" : "🟢 模拟"}
            subtitle={overview?.mode ?? "-"}
            subtitleColor="muted"
            testId="stat-trading-mode"
          />
        </div>

        {/* Trading Control Panel */}
        <TradingControl />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <PnLChart />
          </div>
          <RecentActivity />
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Index;
