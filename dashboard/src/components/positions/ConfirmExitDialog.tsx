/**
 * Confirm Exit Dialog Component.
 *
 * A confirmation dialog for manually exiting a position.
 * Shows position details and asks for confirmation before proceeding.
 *
 * Story 10.6: Dashboard 退出策略管理
 */

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Loader2, AlertTriangle } from "lucide-react";
import type { PositionListItem } from "@/api/types";
import { cn } from "@/lib/utils";

interface ConfirmExitDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  position: PositionListItem | null;
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

  // Calculate current value and PnL percentage
  const currentValue = position.current_value ?? position.shares * position.avg_price;
  const pnl = position.pnl ?? 0;
  const cost = currentValue - pnl;
  const pnlPct = position.pnl !== null && position.pnl !== undefined && cost !== 0
    ? ((position.pnl / cost) * 100)
    : 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            确认退出持仓
          </DialogTitle>
          <DialogDescription>
            确定要手动退出该持仓吗？此操作不可撤销。
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <div className="space-y-3 text-sm">
            <div className="flex justify-between py-2 border-b border-border">
              <span className="text-muted-foreground">市场 ID</span>
              <span className="font-mono text-foreground truncate max-w-[200px]">
                {position.market_id}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-border">
              <span className="text-muted-foreground">方向</span>
              <span
                className={cn(
                  "px-2 py-0.5 rounded text-xs font-medium",
                  position.outcome === "YES"
                    ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                    : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                )}
              >
                {position.outcome}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-border">
              <span className="text-muted-foreground">份额</span>
              <span className="font-mono text-foreground">
                {position.shares.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-border">
              <span className="text-muted-foreground">成本价</span>
              <span className="font-mono text-foreground">
                ${position.avg_price.toFixed(4)}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-border">
              <span className="text-muted-foreground">当前价值</span>
              <span className="font-mono text-foreground">
                ${currentValue.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-muted-foreground">当前盈亏</span>
              <span
                className={cn(
                  "font-mono font-medium",
                  pnl >= 0 ? "text-green-600" : "text-red-600"
                )}
              >
                {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
                <span className="text-xs ml-1">
                  ({pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(1)}%)
                </span>
              </span>
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            取消
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                处理中...
              </>
            ) : (
              "确认退出"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
