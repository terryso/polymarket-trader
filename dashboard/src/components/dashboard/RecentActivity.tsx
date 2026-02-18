import { useActivities } from "@/hooks/useActivities";
import { ArrowUpRight, BrainCircuit, Zap, Loader2 } from "lucide-react";
import type { ActivityType } from "@/api/activities";

const typeIcons: Record<ActivityType, React.ReactNode> = {
  trade: <ArrowUpRight className="h-3.5 w-3.5" />,
  prediction: <BrainCircuit className="h-3.5 w-3.5" />,
  system: <Zap className="h-3.5 w-3.5" />,
};

const typeColors: Record<ActivityType, string> = {
  trade: "text-primary bg-primary/10",
  prediction: "text-warning bg-warning/10",
  system: "text-muted-foreground bg-muted",
};

export function RecentActivity() {
  const { data, isLoading, isError, error } = useActivities({ limit: 10 });

  // Loading state
  if (isLoading) {
    return (
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-foreground mb-4">最近活动</h3>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-foreground mb-4">最近活动</h3>
        <div className="text-sm text-muted-foreground py-4 text-center">
          加载失败: {error?.message || "未知错误"}
        </div>
      </div>
    );
  }

  // Empty state
  const activities = data?.items ?? [];
  if (activities.length === 0) {
    return (
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-foreground mb-4">最近活动</h3>
        <div className="text-sm text-muted-foreground py-4 text-center">
          暂无活动记录
        </div>
      </div>
    );
  }

  return (
    <div className="stat-card">
      <h3 className="text-sm font-semibold text-foreground mb-4">最近活动</h3>
      <div className="space-y-3">
        {activities.map((item) => (
          <div key={item.id} className="flex items-center gap-3 py-1">
            <div className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 ${typeColors[item.type]}`}>
              {typeIcons[item.type]}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-foreground truncate">{item.description}</p>
              <p className="text-xs text-muted-foreground">{item.time}</p>
            </div>
            {item.amount !== null && (
              <span className="text-sm font-mono font-medium text-foreground">
                ${item.amount.toFixed(2)}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
