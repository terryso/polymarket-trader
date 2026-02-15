import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { PnLChart } from "@/components/dashboard/PnLChart";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { mockStats } from "@/data/mockData";
import { DollarSign, TrendingUp, Target, Activity } from "lucide-react";

const Index = () => {
  const statusColor =
    mockStats.systemStatus === "running" ? "profit" : mockStats.systemStatus === "paused" ? "muted" : "loss";

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
            value={`$${mockStats.totalCapital.toFixed(2)}`}
            subtitle={`+${mockStats.todayPnLPercent}%`}
            subtitleColor="profit"
          />
          <StatCard
            icon={<TrendingUp className="h-4 w-4" />}
            title="今日 PnL"
            value={`+$${mockStats.todayPnL.toFixed(2)}`}
            subtitle={`+${mockStats.todayPnLPercent}%`}
            subtitleColor="profit"
          />
          <StatCard
            icon={<Target className="h-4 w-4" />}
            title="胜率"
            value={`${mockStats.winRate}%`}
            subtitle={`${mockStats.winningTrades}/${mockStats.totalTrades}`}
          />
          <StatCard
            icon={<Activity className="h-4 w-4" />}
            title="系统状态"
            value="🟢 运行中"
            subtitle={mockStats.uptime}
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
