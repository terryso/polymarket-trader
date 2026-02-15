import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { mockPositions } from "@/data/mockData";
import { cn } from "@/lib/utils";
import { Wallet } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const Positions = () => {
  const totalValue = mockPositions.reduce((s, p) => s + p.shares * p.currentPrice, 0);
  const totalPnL = mockPositions.reduce((s, p) => s + p.pnl, 0);

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
          />
          <StatCard
            icon={<Wallet className="h-4 w-4" />}
            title="总浮动盈亏"
            value={`${totalPnL >= 0 ? "+" : ""}$${totalPnL.toFixed(2)}`}
            subtitleColor={totalPnL >= 0 ? "profit" : "loss"}
          />
        </div>

        <div className="stat-card overflow-hidden p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="text-muted-foreground">市场名称</TableHead>
                <TableHead className="text-muted-foreground">方向</TableHead>
                <TableHead className="text-muted-foreground text-right">份额</TableHead>
                <TableHead className="text-muted-foreground text-right">成本价</TableHead>
                <TableHead className="text-muted-foreground text-right">当前价</TableHead>
                <TableHead className="text-muted-foreground text-right">PnL</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockPositions.map((p) => (
                <TableRow key={p.id} className="border-border hover:bg-accent/50">
                  <TableCell className="font-medium text-foreground">{p.market}</TableCell>
                  <TableCell>
                    <span className={p.outcome === "YES" ? "badge-profit" : "badge-loss"}>
                      {p.outcome}
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono">{p.shares}</TableCell>
                  <TableCell className="text-right font-mono">${p.avgPrice.toFixed(2)}</TableCell>
                  <TableCell className="text-right font-mono">${p.currentPrice.toFixed(2)}</TableCell>
                  <TableCell className={cn("text-right font-mono font-medium", p.pnl >= 0 ? "profit-text" : "loss-text")}>
                    {p.pnl >= 0 ? "+" : ""}${p.pnl.toFixed(2)} ({p.pnl >= 0 ? "+" : ""}{p.pnlPercent.toFixed(1)}%)
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Positions;
