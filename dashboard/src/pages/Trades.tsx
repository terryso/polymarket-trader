import { useState, useMemo } from "react";
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
import { AlertCircle } from "lucide-react";
import type { TradeMode } from "@/api/types";

type ModeFilter = "all" | "paper" | "live";
type TypeFilter = "all" | "buy" | "sell";
const PAGE_SIZE = 20;

const Trades = () => {
  const [modeFilter, setModeFilter] = useState<ModeFilter>("all");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [page, setPage] = useState(1);

  // Fetch trades with mode filter
  const { data, isLoading, error } = useTrades({
    mode: modeFilter === "all" ? undefined : (modeFilter.toUpperCase() as TradeMode),
  });

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
        <div className="space-y-6">
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
          <Alert variant="destructive">
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
        <div>
          <h2 className="text-xl font-bold text-foreground">交易历史</h2>
          <p className="text-sm text-muted-foreground mt-1">共 {filtered.length} 条记录</p>
        </div>

        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-1 bg-card border border-border rounded-lg p-1">
            <FilterButton active={modeFilter === "all"} onClick={() => handleModeFilter("all")}>全部</FilterButton>
            <FilterButton active={modeFilter === "paper"} onClick={() => handleModeFilter("paper")}>Paper</FilterButton>
            <FilterButton active={modeFilter === "live"} onClick={() => handleModeFilter("live")}>Live</FilterButton>
          </div>
          <div className="flex items-center gap-1 bg-card border border-border rounded-lg p-1">
            <FilterButton active={typeFilter === "all"} onClick={() => handleTypeFilter("all")}>全部</FilterButton>
            <FilterButton active={typeFilter === "buy"} onClick={() => handleTypeFilter("buy")}>买入</FilterButton>
            <FilterButton active={typeFilter === "sell"} onClick={() => handleTypeFilter("sell")}>卖出</FilterButton>
          </div>
        </div>

        <div className="stat-card overflow-hidden p-0">
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
                        {t.status === "filled" ? "✅" : t.status === "failed" ? "❌" : "⏳"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground">
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
