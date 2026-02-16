import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { PnLChart } from "@/components/dashboard/PnLChart";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { useOverview, useSystemStatus } from "@/hooks/useStatistics";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { DollarSign, TrendingUp, Target, Activity, AlertCircle } from "lucide-react";

const Index = () => {
  const { data: overview, isLoading: overviewLoading, error: overviewError } = useOverview();
  const { data: status, isLoading: statusLoading } = useSystemStatus();

  const isLoading = overviewLoading || statusLoading;

  // Loading state
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
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
          <Alert variant="destructive">
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
  const todayPnL = status?.daily_pnl ?? 0;
  const todayPnLPercent = overview?.initial_capital
    ? (todayPnL / overview.initial_capital) * 100
    : 0;
  const statusColor =
    status?.trading_enabled ? "profit" : "muted";

  // Format uptime
  const formatUptime = (hours: number | null | undefined): string => {
    if (hours === null || hours === undefined) return "-";
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return `${h}h ${m}m`;
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-foreground">Dashboard</h2>
          <p className="text-sm text-muted-foreground mt-1">系统运行概览</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={<DollarSign className="h-4 w-4" />}
            title="总资金"
            value={`$${(overview?.current_capital ?? 0).toFixed(2)}`}
            subtitle={todayPnLPercent >= 0 ? `+${todayPnLPercent.toFixed(1)}%` : `${todayPnLPercent.toFixed(1)}%`}
            subtitleColor={todayPnLPercent >= 0 ? "profit" : "loss"}
          />
          <StatCard
            icon={<TrendingUp className="h-4 w-4" />}
            title="今日 PnL"
            value={`${todayPnL >= 0 ? "+" : ""}$${todayPnL.toFixed(2)}`}
            subtitle={todayPnLPercent >= 0 ? `+${todayPnLPercent.toFixed(1)}%` : `${todayPnLPercent.toFixed(1)}%`}
            subtitleColor={todayPnL >= 0 ? "profit" : "loss"}
          />
          <StatCard
            icon={<Target className="h-4 w-4" />}
            title="胜率"
            value={`${((overview?.win_rate ?? 0) * 100).toFixed(1)}%`}
            subtitle={overview ? `${overview.winning_trades}/${overview.total_trades}` : "-"}
          />
          <StatCard
            icon={<Activity className="h-4 w-4" />}
            title="系统状态"
            value={status?.trading_enabled ? "🟢 运行中" : "🟡 已暂停"}
            subtitle={formatUptime(status?.uptime_hours)}
            subtitleColor={statusColor as "profit" | "loss" | "muted"}
          />
        </div>

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
