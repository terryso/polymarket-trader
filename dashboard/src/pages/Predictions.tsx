import { useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { usePredictions, useAccuracy } from "@/hooks/usePredictions";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { BarChart3, CheckCircle2, XCircle, AlertCircle, ExternalLink } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
  PaginationEllipsis,
} from "@/components/ui/pagination";

const PAGE_SIZE = 20;

const Predictions = () => {
  const [page, setPage] = useState(1);
  const { data: predictionsData, isLoading: predictionsLoading, error: predictionsError } = usePredictions({ page, per_page: PAGE_SIZE });
  const { data: accuracy, isLoading: accuracyLoading } = useAccuracy();

  const isLoading = predictionsLoading || accuracyLoading;
  const predictions = predictionsData?.items ?? [];
  const total = predictionsData?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);

  // Calculate stats from accuracy API (more accurate for totals)
  const correct = accuracy?.correct_predictions ?? 0;
  const incorrect = (accuracy?.validated_predictions ?? 0) - correct;

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

  // Generate Polymarket URL from slug
  // Handle different slug patterns:
  // 1. Normal slug: use as-is
  // 2. Market-specific slug with "-by-" and date: extract event slug
  const getPolymarketUrl = (slug: string | null): string | null => {
    if (!slug) return null;

    // Pattern 1: Slug with hash suffix (e.g., "...-2026-393-221-132-...")
    // Extract event slug for markets with "-by-" pattern
    const hashPattern = /-\d{4}(?:-\d{3})+$/;
    if (hashPattern.test(slug) && slug.includes('-by-')) {
      const baseSlug = slug.split('-by-')[0] + '-by';
      return `https://polymarket.com/event/${baseSlug}`;
    }

    // Pattern 2: Slug with date but no hash (e.g., "us-strikes-iran-by-march-31-2026")
    // Extract event slug for "-by-" followed by month names
    const datePattern = /-by-(january|february|march|april|may|june|july|august|september|october|november|december)-/i;
    if (datePattern.test(slug)) {
      const baseSlug = slug.split('-by-')[0] + '-by';
      return `https://polymarket.com/event/${baseSlug}`;
    }

    // Normal slug - use as-is
    return `https://polymarket.com/event/${slug}`;
  };

  // Format prediction display: YES(80%) or NO(20%)
  const formatPrediction = (probability: number): { text: string; className: string } => {
    const pct = (probability * 100).toFixed(0);
    if (probability >= 0.5) {
      return { text: `YES(${pct}%)`, className: "text-green-600 dark:text-green-400" };
    } else {
      return { text: `NO(${pct}%)`, className: "text-red-600 dark:text-red-400" };
    }
  };

  // Truncate title for display
  const truncateTitle = (title: string | null, maxLength: number = 40): string => {
    if (!title) return "未知市场";
    if (title.length <= maxLength) return title;
    return title.slice(0, maxLength) + "...";
  };

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
                  <TableHead className="text-muted-foreground text-right">市场价</TableHead>
                  <TableHead className="text-muted-foreground text-right">LLM 预测</TableHead>
                  <TableHead className="text-muted-foreground text-center">Edge</TableHead>
                  <TableHead className="text-muted-foreground text-center">置信度</TableHead>
                  <TableHead className="text-muted-foreground text-center">可交易</TableHead>
                  <TableHead className="text-muted-foreground text-center">状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {predictions.map((p) => {
                  const confidence = getConfidenceLabel(p.confidence);
                  const status = getStatusDisplay(p.is_correct);
                  const prediction = formatPrediction(p.predicted_probability);
                  // 判断是否可交易: 置信度 >= 65% 且 Edge >= 5%
                  const isTradeable = p.confidence >= 0.65 && (p.edge ?? 0) >= 0.05;
                  // Edge 显示
                  const edgeDisplay = p.edge !== null ? `${(p.edge * 100).toFixed(0)}%` : "-";
                  const edgeColor = p.edge !== null && p.edge >= 0.05 ? "text-green-600 dark:text-green-400" : "text-muted-foreground";
                  return (
                    <TableRow key={p.id} className="border-border hover:bg-accent/50">
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {formatTimestamp(p.created_at)}
                      </TableCell>
                      <TableCell className="font-medium text-foreground">
                        {getPolymarketUrl(p.market_slug) ? (
                          <a
                            href={getPolymarketUrl(p.market_slug)!}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-foreground hover:text-primary flex items-center gap-1 transition-colors"
                            title={p.market_title || p.market_id}
                          >
                            {truncateTitle(p.market_title)}
                            <ExternalLink className="h-3 w-3 flex-shrink-0" />
                          </a>
                        ) : (
                          <span title={p.market_id}>{truncateTitle(p.market_title)}</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-muted-foreground">
                        {p.market_yes_price !== null ? `${(p.market_yes_price * 100).toFixed(0)}%` : "-"}
                      </TableCell>
                      <TableCell className={cn("text-right font-mono font-medium", prediction.className)}>
                        {prediction.text}
                      </TableCell>
                      <TableCell className={cn("text-center font-mono text-sm", edgeColor)}>
                        {edgeDisplay}
                      </TableCell>
                      <TableCell className="text-center">
                        <span className={confidence.color}>{confidence.label}</span>
                      </TableCell>
                      <TableCell className="text-center">
                        {isTradeable ? (
                          <span className="text-green-600 dark:text-green-400">✓</span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
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

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex justify-center">
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className={currentPage <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum: number;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }
                  return (
                    <PaginationItem key={pageNum}>
                      <PaginationLink
                        onClick={() => setPage(pageNum)}
                        isActive={currentPage === pageNum}
                        className="cursor-pointer"
                      >
                        {pageNum}
                      </PaginationLink>
                    </PaginationItem>
                  );
                })}
                {totalPages > 5 && currentPage < totalPages - 2 && (
                  <PaginationItem>
                    <PaginationEllipsis />
                  </PaginationItem>
                )}
                <PaginationItem>
                  <PaginationNext
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    className={currentPage >= totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default Predictions;
