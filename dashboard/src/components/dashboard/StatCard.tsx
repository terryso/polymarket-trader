import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  icon: ReactNode;
  title: string;
  value: string;
  subtitle?: string;
  subtitleColor?: "profit" | "loss" | "muted";
  className?: string;
  testId?: string;
}

export function StatCard({ icon, title, value, subtitle, subtitleColor = "muted", className, testId }: StatCardProps) {
  const subtitleClasses = {
    profit: "profit-text",
    loss: "loss-text",
    muted: "text-muted-foreground",
  };

  return (
    <div className={cn("stat-card", className)} data-testid={testId}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-muted-foreground">{icon}</span>
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{title}</span>
      </div>
      <div className="text-2xl font-bold font-mono text-foreground" data-testid={testId ? `${testId}-value` : undefined}>{value}</div>
      {subtitle && (
        <div className={cn("text-xs mt-1 font-medium", subtitleClasses[subtitleColor])} data-testid={testId ? `${testId}-subtitle` : undefined}>
          {subtitle}
        </div>
      )}
    </div>
  );
}
