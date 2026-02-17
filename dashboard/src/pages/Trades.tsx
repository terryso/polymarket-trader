import { useState, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useTrades } from "@/hooks/useTrades";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Pagination, PaginationContent, PaginationItem, PaginationLink,
  PaginationNext, PaginationPrevious, PaginationEllipsis,
} from "@/components/ui/pagination";
import { AlertCircle, RefreshCw, CheckCircle2, XCircle } from "lucide-react";
import { tradesApi } from "@/api/trades";
import type { TradeMode, SyncStatus, SyncResult } from "@/api/types";

type ModeFilter = "all" | "paper" | "live";
type TypeFilter = "all" | "buy" | "sell";
const PAGE_SIZE = 20;

const Trades = () => {
  const [modeFilter, setModeFilter] = useState<ModeFilter>("all");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [page, setPage] = useState(1);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const queryClient = useQueryClient();

  // Fetch trades with mode filter
  const { data, isLoading, error } = useTrades({
    mode: modeFilter === "all" ? undefined : (modeFilter.toUpperCase() as TradeMode),
  });

  // Fetch sync status on mount
  useMemo(() => {
    tradesApi.getSyncStatus().then(setSyncStatus).catch(console.error);
  }, []);

  // Filter by type in memory (backend doesn't support this filter)
  const filtered = useMemo(() => {
    const trades = data?.items ?? [];
    return trades.filter((t) => {
      if (typeFilter === "buy" && !t.trade_type.startsWith("BUY")) return false;
      if (typeFilter === "sell" && !t.trade_type.startsWith("SELL")) return false;
      return true;
    });
  }, [data?.items, typeFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const paged = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  // Reset page when filters change
  const handleModeFilter = (m: ModeFilter) => { setModeFilter(m); setPage(1); };
  const handleTypeFilter = (t: TypeFilter) => { setTypeFilter(t); setPage(1); };

  const FilterButton = ({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) => (
    <Button variant="ghost" size="sm" onClick={onClick}
      className={cn("text-xs h-8 px-3 rounded-md", active ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground")}>
      {children}
    </Button>
  );

  // Handle sync
  const handleSync = async () => {
    if (isSyncing || !syncStatus?.can_sync) return;

    setIsSyncing(true);
    setSyncResult(null);

    try {
      const result = await tradesApi.sync();
      setSyncResult(result);
      // Refresh trades list
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      // Update sync status
      const status = await tradesApi.getSyncStatus();
      setSyncStatus(status);
    } catch (err) {
      setSyncResult({
        new_trades: 0,
        updated_trades: 0,
        consistent_trades: 0,
        inconsistent_trades: 0,
        total_fetched: 0,
        last_sync_at: new Date().toISOString(),
        error: err instanceof Error ? err.message : '同步失败',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  // Format sync time
  const formatSyncTime = (ts: string | null): string => {
    if (!ts) return "从未同步";
    try {
      const d = new Date(ts);
      return d.toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return ts;
    }
  };

  const pageNumbers = useMemo(() => {
    const pages: (number | "ellipsis")[] = [];
    if (totalPages <= 5) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (currentPage > 3) pages.push("ellipsis");
      for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) pages.push(i);
      if (currentPage < totalPages - 2) pages.push("ellipsis");
      pages.push(totalPages);
    }
    return pages;
  }, [currentPage, totalPages]);

  // Loading state
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="space-y-6" data-testid="loading-skeleton">
          <div>
            <Skeleton className="h-7 w-32" />
            <Skeleton className="h-5 w-24 mt-1" />
          </div>
          <Skeleton className="h-12 w-72" />
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
            <h2 className="text-xl font-bold text-foreground">交易历史</h2>
            <p className="text-sm text-muted-foreground mt-1">交易记录</p>
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
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-foreground">交易历史</h2>
            <p className="text-sm text-muted-foreground mt-1">共 {filtered.length} 条记录</p>
          </div>

          {/* Sync Section */}
          <div className="flex items-center gap-3">
            {syncStatus && (
              <div className="text-xs text-muted-foreground">
                <span>最后同步: {formatSyncTime(syncStatus.last_sync_at)}</span>
              </div>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleSync}
              disabled={isSyncing || !syncStatus?.can_sync}
              className="h-8"
              data-testid="sync-button"
            >
              {isSyncing ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  同步中...
                </>
              ) : (
                <>
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                  同步
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Sync Result Alert */}
        {syncResult && (
          <Alert variant={syncResult.error ? "destructive" : "default"} data-testid="sync-result">
            {syncResult.error ? (
              <XCircle className="h-4 w-4" />
            ) : (
              <CheckCircle2 className="h-4 w-4" />
            )}
            <AlertDescription>
              {syncResult.error ? (
                syncResult.error
              ) : (
                <span>
                  同步完成: {syncResult.new_trades} 条新增, {syncResult.updated_trades} 条更新
                  {syncResult.inconsistent_trades > 0 && (
                    <span className="text-yellow-600 ml-2">
                      ({syncResult.inconsistent_trades} 条不一致)
                    </span>
                  )}
                </span>
              )}
            </AlertDescription>
          </Alert>
        )}

        {/* Can't sync warning */}
        {syncStatus && !syncStatus.can_sync && (
          <Alert variant="default" className="bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800">
            <AlertCircle className="h-4 w-4 text-yellow-600" />
            <AlertDescription className="text-yellow-700 dark:text-yellow-400">
              需要配置 Polymarket API 凭证才能同步交易历史。
              请在 .env 文件中设置 POLYMARKET_API_KEY, POLYMARKET_API_SECRET, 和 POLYMARKET_API_PASSPHRASE。
            </AlertDescription>
          </Alert>
        )}

        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-1 bg-card border border-border rounded-lg p-1" data-testid="mode-filter">
            <FilterButton active={modeFilter === "all"} onClick={() => handleModeFilter("all")}>全部</FilterButton>
            <FilterButton active={modeFilter === "paper"} onClick={() => handleModeFilter("paper")}>Paper</FilterButton>
            <FilterButton active={modeFilter === "live"} onClick={() => handleModeFilter("live")}>Live</FilterButton>
          </div>
          <div className="flex items-center gap-1 bg-card border border-border rounded-lg p-1" data-testid="type-filter">
            <FilterButton active={typeFilter === "all"} onClick={() => handleTypeFilter("all")}>全部</FilterButton>
            <FilterButton active={typeFilter === "buy"} onClick={() => handleTypeFilter("buy")}>买入</FilterButton>
            <FilterButton active={typeFilter === "sell"} onClick={() => handleTypeFilter("sell")}>卖出</FilterButton>
          </div>
        </div>

        <div className="stat-card overflow-hidden p-0" data-testid="trades-table">
          {paged.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead className="text-muted-foreground">时间</TableHead>
                    <TableHead className="text-muted-foreground">市场</TableHead>
                    <TableHead className="text-muted-foreground">类型</TableHead>
                    <TableHead className="text-muted-foreground hidden sm:table-cell">模式</TableHead>
                    <TableHead className="text-muted-foreground text-right">金额</TableHead>
                    <TableHead className="text-muted-foreground text-right hidden md:table-cell">价格</TableHead>
                    <TableHead className="text-muted-foreground text-right hidden md:table-cell">份额</TableHead>
                    <TableHead className="text-muted-foreground text-center hidden sm:table-cell">状态</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paged.map((t) => (
                    <TableRow key={t.id} className="border-border hover:bg-accent/50">
                      <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                        {formatTimestamp(t.created_at)}
                      </TableCell>
                      <TableCell className="font-medium text-foreground max-w-[120px] truncate">{t.market_id}</TableCell>
                      <TableCell>
                        <span className={t.trade_type.startsWith("BUY") ? "badge-profit" : "badge-loss"}>
                          {t.trade_type.replace("_", " ")}
                        </span>
                      </TableCell>
                      <TableCell className="hidden sm:table-cell">
                        <span className={t.mode === "PAPER" ? "badge-paper" : "badge-live"}>{t.mode}</span>
                      </TableCell>
                      <TableCell className="text-right font-mono">${t.amount.toFixed(2)}</TableCell>
                      <TableCell className="text-right font-mono hidden md:table-cell">${t.price.toFixed(2)}</TableCell>
                      <TableCell className="text-right font-mono hidden md:table-cell">
                        {t.shares ? t.shares.toFixed(2) : "-"}
                      </TableCell>
                      <TableCell className="text-center hidden sm:table-cell">
                        {t.status === "FILLED" ? "✅" : t.status === "CANCELLED" ? "❌" : "⏳"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground" data-testid="empty-state">
              暂无交易记录
            </div>
          )}
        </div>

        {totalPages > 1 && (
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className={cn("cursor-pointer", currentPage === 1 && "pointer-events-none opacity-50")}
                />
              </PaginationItem>
              {pageNumbers.map((n, i) =>
                n === "ellipsis" ? (
                  <PaginationItem key={`e${i}`}><PaginationEllipsis /></PaginationItem>
                ) : (
                  <PaginationItem key={n}>
                    <PaginationLink isActive={n === currentPage} onClick={() => setPage(n)} className="cursor-pointer">
                      {n}
                    </PaginationLink>
                  </PaginationItem>
                )
              )}
              <PaginationItem>
                <PaginationNext
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className={cn("cursor-pointer", currentPage === totalPages && "pointer-events-none opacity-50")}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        )}
      </div>
    </DashboardLayout>
  );
};

export default Trades;
