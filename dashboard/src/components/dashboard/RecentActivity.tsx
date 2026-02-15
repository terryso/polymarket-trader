import { mockRecentActivity } from "@/data/mockData";
import { ArrowUpRight, BrainCircuit, Zap } from "lucide-react";

const typeIcons = {
  trade: <ArrowUpRight className="h-3.5 w-3.5" />,
  prediction: <BrainCircuit className="h-3.5 w-3.5" />,
  system: <Zap className="h-3.5 w-3.5" />,
};

const typeColors = {
  trade: "text-primary bg-primary/10",
  prediction: "text-warning bg-warning/10",
  system: "text-muted-foreground bg-muted",
};

export function RecentActivity() {
  return (
    <div className="stat-card">
      <h3 className="text-sm font-semibold text-foreground mb-4">最近活动</h3>
      <div className="space-y-3">
        {mockRecentActivity.map((item) => (
          <div key={item.id} className="flex items-center gap-3 py-1">
            <div className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 ${typeColors[item.type]}`}>
              {typeIcons[item.type]}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-foreground truncate">{item.description}</p>
              <p className="text-xs text-muted-foreground">{item.time}</p>
            </div>
            {item.amount && (
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
