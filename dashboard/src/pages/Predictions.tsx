import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { usePredictions, useAccuracy } from "@/hooks/usePredictions";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { BarChart3, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const Predictions = () => {
  const { data: predictionsData, isLoading: predictionsLoading, error: predictionsError } = usePredictions();
  const { data: accuracy, isLoading: accuracyLoading } = useAccuracy();

  const isLoading = predictionsLoading || accuracyLoading;
  const predictions = predictionsData?.items ?? [];

  // Calculate stats from predictions
  const total = predictions.length;
  const correct = predictions.filter((p) => p.is_correct === true).length;
  const incorrect = predictions.filter((p) => p.is_correct === false).length;

  const confidenceColors: Record<string, string> = {
    high: "badge-profit",
    medium: "badge-paper",
    low: "badge-loss",
  };

  const getConfidenceLabel = (conf: number): { label: string; color: string } => {
    if (conf >= 0.8) return { label: "高", color: "badge-profit" };
    if (conf >= 0.5) return { label: "中", color: "badge-paper" };
    return { label: "低", color: "badge-loss" };
  };

  const getStatusDisplay = (isCorrect: boolean | null): { text: string; className: string } => {
    if (isCorrect === null) return { text: "待验证", className: "text-muted-foreground" };
    if (isCorrect) return { text: "✅ 正确", className: "profit-text" };
    return { text: "❌ 错误", className: "loss-text" };
  };

  // Loading state
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <Skeleton className="h-7 w-32" />
            <Skeleton className="h-5 w-56 mt-1" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
          <Skeleton className="h-64" />
        </div>
      </DashboardLayout>
    );
  }

  // Error state
  if (predictionsError) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-bold text-foreground">预测记录</h2>
            <p className="text-sm text-muted-foreground mt-1">LLM 预测分析与准确率追踪</p>
          </div>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              无法加载数据: {predictionsError.message}
            </AlertDescription>
          </Alert>
        </div>
      </DashboardLayout>
    );
  }

  // Format timestamp
  const formatTimestamp = (ts: string | null): string => {
    if (!ts) return "-";
    try {
      const d = new Date(ts);
      return d.toLocaleString("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).replace(/\//g, "-");
    } catch {
      return ts;
    }
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
            value={(accuracy?.total_predictions ?? total).toString()}
          />
          <StatCard
            icon={<CheckCircle2 className="h-4 w-4" />}
            title="正确"
            value={(accuracy?.correct_predictions ?? correct).toString()}
            subtitle={
              accuracy
                ? `${(accuracy.accuracy * 100).toFixed(0)}%`
                : total > 0
                  ? `${((correct / total) * 100).toFixed(0)}%`
                  : "0%"
            }
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
          {predictions.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow className="border-border hover:bg-transparent">
                  <TableHead className="text-muted-foreground">时间</TableHead>
                  <TableHead className="text-muted-foreground">市场</TableHead>
                  <TableHead className="text-muted-foreground text-right">LLM 预测</TableHead>
                  <TableHead className="text-muted-foreground text-center">置信度</TableHead>
                  <TableHead className="text-muted-foreground text-center">状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {predictions.map((p) => {
                  const confidence = getConfidenceLabel(p.confidence);
                  const status = getStatusDisplay(p.is_correct);
                  return (
                    <TableRow key={p.id} className="border-border hover:bg-accent/50">
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {formatTimestamp(p.created_at)}
                      </TableCell>
                      <TableCell className="font-medium text-foreground">{p.market_id}</TableCell>
                      <TableCell className="text-right font-mono">
                        {(p.predicted_probability * 100).toFixed(0)}%
                      </TableCell>
                      <TableCell className="text-center">
                        <span className={confidence.color}>{confidence.label}</span>
                      </TableCell>
                      <TableCell className={cn("text-center text-sm", status.className)}>
                        {status.text}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <div className="p-8 text-center text-muted-foreground">
              暂无预测记录
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Predictions;
