import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { mockPredictions } from "@/data/mockData";
import { cn } from "@/lib/utils";
import { BarChart3, CheckCircle2, XCircle } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const Predictions = () => {
  const total = mockPredictions.length;
  const correct = mockPredictions.filter((p) => p.status === "correct").length;
  const incorrect = mockPredictions.filter((p) => p.status === "incorrect").length;

  const confidenceColors = {
    high: "badge-profit",
    medium: "badge-paper",
    low: "badge-loss",
  };

  const statusLabels = {
    pending: { text: "待验证", class: "text-muted-foreground" },
    correct: { text: "✅ 正确", class: "profit-text" },
    incorrect: { text: "❌ 错误", class: "loss-text" },
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-foreground">预测记录</h2>
          <p className="text-sm text-muted-foreground mt-1">LLM 预测分析与准确率追踪</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            icon={<BarChart3 className="h-4 w-4" />}
            title="总预测"
            value={total.toString()}
          />
          <StatCard
            icon={<CheckCircle2 className="h-4 w-4" />}
            title="正确"
            value={correct.toString()}
            subtitle={total > 0 ? `${((correct / total) * 100).toFixed(0)}%` : "0%"}
            subtitleColor="profit"
          />
          <StatCard
            icon={<XCircle className="h-4 w-4" />}
            title="错误"
            value={incorrect.toString()}
            subtitle={total > 0 ? `${((incorrect / total) * 100).toFixed(0)}%` : "0%"}
            subtitleColor="loss"
          />
        </div>

        <div className="stat-card overflow-hidden p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="text-muted-foreground">时间</TableHead>
                <TableHead className="text-muted-foreground">市场</TableHead>
                <TableHead className="text-muted-foreground text-right">LLM 预测</TableHead>
                <TableHead className="text-muted-foreground text-right">市场价格</TableHead>
                <TableHead className="text-muted-foreground text-center">置信度</TableHead>
                <TableHead className="text-muted-foreground text-center">状态</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockPredictions.map((p) => (
                <TableRow key={p.id} className="border-border hover:bg-accent/50">
                  <TableCell className="font-mono text-xs text-muted-foreground">{p.timestamp}</TableCell>
                  <TableCell className="font-medium text-foreground">{p.market}</TableCell>
                  <TableCell className="text-right font-mono">{(p.llmProbability * 100).toFixed(0)}% YES</TableCell>
                  <TableCell className="text-right font-mono">{(p.marketPrice * 100).toFixed(0)}% YES</TableCell>
                  <TableCell className="text-center">
                    <span className={confidenceColors[p.confidence]}>{p.confidence === "high" ? "高" : p.confidence === "medium" ? "中" : "低"}</span>
                  </TableCell>
                  <TableCell className={cn("text-center text-sm", statusLabels[p.status].class)}>
                    {statusLabels[p.status].text}
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

export default Predictions;
