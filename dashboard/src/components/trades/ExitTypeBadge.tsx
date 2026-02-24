/**
 * Exit Type Badge Component.
 *
 * Displays a colored badge indicating the type of exit for a trade.
 *
 * Story 10.6: Dashboard 退出策略管理
 *
 * Exit Types:
 * - take_profit (止盈): Green badge
 * - stop_loss (止损): Red badge
 * - time_exit (时间退出): Yellow badge
 * - signal_exit (信号反转): Blue badge
 * - manual (手动退出): Gray badge
 */

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const EXIT_TYPE_CONFIG: Record<string, { label: string; className: string }> = {
  take_profit: {
    label: "止盈",
    className: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  },
  stop_loss: {
    label: "止损",
    className: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  },
  time_exit: {
    label: "时间退出",
    className: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  },
  signal_exit: {
    label: "信号反转",
    className: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  },
  manual: {
    label: "手动退出",
    className: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
  },
};

interface ExitTypeBadgeProps {
  exitType: string | null | undefined;
  className?: string;
}

export function ExitTypeBadge({ exitType, className }: ExitTypeBadgeProps) {
  if (!exitType) return null;

  const config = EXIT_TYPE_CONFIG[exitType] || {
    label: exitType,
    className: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
  };

  return (
    <Badge
      variant="secondary"
      className={cn("font-normal text-xs", config.className, className)}
    >
      {config.label}
    </Badge>
  );
}
