/**
 * Prediction Detail Sheet Component.
 *
 * A side drawer that displays the full LLM analysis process for a prediction.
 *
 * Story 7.8: 预测详情抽屉组件
 */

import { usePrediction } from "@/hooks/usePredictions";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { CheckCircle2, XCircle, Clock, Brain, Target, Lightbulb } from "lucide-react";

interface PredictionDetailSheetProps {
  /** Prediction ID to fetch and display */
  predictionId: number | null;
  /** Whether the sheet is open */
  open: boolean;
  /** Callback when sheet open state changes */
  onOpenChange: (open: boolean) => void;
}

/**
 * Formats a probability value for display.
 * Values >= 0.5 show as YES, values < 0.5 show as NO.
 */
const formatProbability = (probability: number): { text: string; className: string } => {
  const pct = (probability * 100).toFixed(0);
  if (probability >= 0.5) {
    return { text: `YES (${pct}%)`, className: "text-green-600 dark:text-green-400" };
  }
  return { text: `NO (${pct}%)`, className: "text-red-600 dark:text-red-400" };
};

/**
 * Formats a confidence level for display.
 */
const formatConfidence = (confidence: number): { label: string; color: string } => {
  if (confidence >= 0.8) return { label: "高", color: "bg-green-500" };
  if (confidence >= 0.5) return { label: "中", color: "bg-yellow-500" };
  return { label: "低", color: "bg-red-500" };
};

/**
 * Formats a timestamp for display.
 */
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
    }).replace(/\//g, "-");
  } catch {
    return ts;
  }
};

/**
 * Loading skeleton for the prediction detail sheet.
 */
const LoadingSkeleton = () => (
  <div className="space-y-6 mt-4">
    <div className="space-y-2">
      <Skeleton className="h-4 w-20" />
      <Skeleton className="h-6 w-32" />
    </div>
    <div className="grid grid-cols-2 gap-4">
      <div className="space-y-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-8 w-24" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-8 w-24" />
      </div>
    </div>
    <div className="space-y-2">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-32 w-full" />
    </div>
    <div className="space-y-2">
      <Skeleton className="h-4 w-20" />
      <Skeleton className="h-6 w-full" />
      <Skeleton className="h-6 w-3/4" />
      <Skeleton className="h-6 w-1/2" />
    </div>
  </div>
);

/**
 * Prediction Detail Sheet Component.
 *
 * Displays complete LLM analysis details in a side drawer.
 */
export function PredictionDetailSheet({
  predictionId,
  open,
  onOpenChange,
}: PredictionDetailSheetProps) {
  const { data: prediction, isLoading, error } = usePrediction(predictionId || 0);

  // Reset query when sheet closes
  const handleOpenChange = (newOpen: boolean) => {
    onOpenChange(newOpen);
  };

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-left">
            {isLoading ? (
              <Skeleton className="h-6 w-48" />
            ) : prediction?.market_title ? (
              <span className="line-clamp-2">{prediction.market_title}</span>
            ) : (
              "预测详情"
            )}
          </SheetTitle>
        </SheetHeader>

        {isLoading && <LoadingSkeleton />}

        {error && (
          <div className="mt-4 p-4 bg-destructive/10 rounded-lg text-destructive">
            加载预测详情失败: {error.message}
          </div>
        )}

        {!isLoading && !error && prediction && (
          <div className="mt-4 space-y-6">
            {/* Basic Info Section */}
            <div className="grid grid-cols-2 gap-4">
              {/* Model Used */}
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Brain className="h-3 w-3" />
                  <span>LLM 模型</span>
                </div>
                <div className="font-mono text-sm font-medium truncate" title={prediction.model_used || "-"}>
                  {prediction.model_used || "-"}
                </div>
              </div>

              {/* Created At */}
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  <span>创建时间</span>
                </div>
                <div className="font-mono text-sm">
                  {formatTimestamp(prediction.created_at)}
                </div>
              </div>
            </div>

            {/* Probability & Confidence */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Target className="h-3 w-3" />
                  <span>预测概率</span>
                </div>
                <div className={cn("text-lg font-bold", formatProbability(prediction.predicted_probability).className)}>
                  {formatProbability(prediction.predicted_probability).text}
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  置信度
                </div>
                <div className="flex items-center gap-2">
                  <div className={cn("w-2 h-2 rounded-full", formatConfidence(prediction.confidence).color)} />
                  <span className="text-lg font-bold">
                    {(prediction.confidence * 100).toFixed(0)}%
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {formatConfidence(prediction.confidence).label}
                  </Badge>
                </div>
              </div>
            </div>

            {/* Reasoning Section - Main Content */}
            {prediction.reasoning && (
              <div className="space-y-2">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                  分析过程
                </h3>
                <div className="bg-muted/50 rounded-lg p-4 text-sm leading-relaxed whitespace-pre-wrap">
                  {prediction.reasoning}
                </div>
              </div>
            )}

            {/* Key Assumptions Section */}
            {prediction.key_assumptions && prediction.key_assumptions.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                  <Lightbulb className="h-4 w-4" />
                  关键假设
                </h3>
                <ul className="space-y-2">
                  {prediction.key_assumptions.map((assumption, index) => (
                    <li
                      key={index}
                      className="flex items-start gap-2 text-sm"
                    >
                      <span className="text-primary mt-0.5">-</span>
                      <span>{assumption}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Validation Result Section */}
            {prediction.is_correct !== null && (
              <div className="space-y-2">
                <h3 className="text-sm font-semibold">验证结果</h3>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/30">
                  {prediction.is_correct ? (
                    <>
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                      <div>
                        <div className="font-medium text-green-600 dark:text-green-400">
                          预测正确
                        </div>
                        {prediction.validated_at && (
                          <div className="text-xs text-muted-foreground">
                            验证时间: {formatTimestamp(prediction.validated_at)}
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-5 w-5 text-red-500" />
                      <div>
                        <div className="font-medium text-red-600 dark:text-red-400">
                          预测错误
                        </div>
                        {prediction.validated_at && (
                          <div className="text-xs text-muted-foreground">
                            验证时间: {formatTimestamp(prediction.validated_at)}
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
                {prediction.actual_outcome && (
                  <div className="text-sm text-muted-foreground">
                    实际结果: <span className="font-medium text-foreground">{prediction.actual_outcome}</span>
                  </div>
                )}
              </div>
            )}

            {/* Recommendation Badge */}
            {prediction.recommendation && (
              <div className="pt-2 border-t border-border">
                <div className="text-xs text-muted-foreground mb-1">交易建议</div>
                <Badge variant={prediction.recommendation.includes("BUY") ? "default" : "secondary"}>
                  {prediction.recommendation}
                </Badge>
              </div>
            )}
          </div>
        )}

        {!isLoading && !error && !prediction && predictionId && (
          <div className="mt-4 p-4 bg-muted rounded-lg text-muted-foreground text-center">
            未找到预测数据
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

export default PredictionDetailSheet;
