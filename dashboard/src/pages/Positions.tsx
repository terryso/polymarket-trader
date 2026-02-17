import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { usePositions } from "@/hooks/usePositions";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { Wallet, AlertCircle } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const Positions = () => {
  const { data: positions, isLoading, error } = usePositions();

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

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-foreground">持仓</h2>
          <p className="text-sm text-muted-foreground mt-1">当前持有头寸</p>
        </div>

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
            <Table>
              <TableHeader>
                <TableRow className="border-border hover:bg-transparent">
                  <TableHead className="text-muted-foreground">市场 ID</TableHead>
                  <TableHead className="text-muted-foreground">方向</TableHead>
                  <TableHead className="text-muted-foreground text-right">份额</TableHead>
                  <TableHead className="text-muted-foreground text-right">成本价</TableHead>
                  <TableHead className="text-muted-foreground text-right">当前价值</TableHead>
                  <TableHead className="text-muted-foreground text-right">PnL</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {positions.map((p) => (
                  <TableRow key={p.id} className="border-border hover:bg-accent/50">
                    <TableCell className="font-medium text-foreground">{p.market_id}</TableCell>
                    <TableCell>
                      <span className={p.outcome === "YES" ? "badge-profit" : "badge-loss"}>
                        {p.outcome}
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono">{p.shares.toFixed(2)}</TableCell>
                    <TableCell className="text-right font-mono">${p.avg_price.toFixed(2)}</TableCell>
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
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="p-8 text-center text-muted-foreground" data-testid="empty-state">
              暂无持仓数据
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Positions;
