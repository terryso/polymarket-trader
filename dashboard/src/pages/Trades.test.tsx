/**
 * Trades Page Component Tests
 *
 * Tests for the Trades page including:
 * - Loading state rendering
 * - Error state handling
 * - Trade table display
 * - Filtering by type (buy/sell only)
 * - Pagination functionality
 * - Empty state handling
 *
 * Story 7.6: 前端 API 集成
 * Story 7.9: 交易历史按模式实时显示 (移除 Mode 筛选器和同步功能)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import type { TradeListItem } from "@/api/types";

// Mock the hook
vi.mock("@/hooks/useTrades", () => ({
  useTrades: vi.fn(),
}));

// Mock the layout component
vi.mock("@/components/layout/DashboardLayout", () => ({
  DashboardLayout: ({ children }: { children: ReactNode }) => (
    <div data-testid="dashboard-layout">{children}</div>
  ),
}));

// Create wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
};

// Mock trades data
const mockTrades: TradeListItem[] = [
  {
    id: 1,
    market_id: "market-1",
    trade_type: "BUY_YES",
    mode: "PAPER",
    amount: 10.0,
    price: 0.55,
    shares: 18.18,
    status: "FILLED",
    exit_type: null,
    created_at: "2026-02-17T10:00:00Z",
  },
  {
    id: 2,
    market_id: "market-2",
    trade_type: "SELL_NO",
    mode: "PAPER",
    amount: 5.0,
    price: 0.70,
    shares: 7.14,
    status: "FILLED",
    exit_type: null,
    created_at: "2026-02-17T11:00:00Z",
  },
  {
    id: 3,
    market_id: "market-3",
    trade_type: "BUY_NO",
    mode: "LIVE",
    amount: 20.0,
    price: 0.30,
    shares: 66.67,
    status: "PENDING",
    exit_type: null,
    created_at: "2026-02-17T12:00:00Z",
  },
];

describe("Trades Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("should render loading skeletons while data is loading", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: true,
        data: undefined,
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      expect(screen.getByTestId("dashboard-layout")).toBeInTheDocument();

      // Should show loading skeletons
      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe("Error State", () => {
    it("should render error alert when trades fail to load", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: undefined,
        error: new Error("Failed to fetch trades"),
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      expect(screen.getByText("无法加载数据: Failed to fetch trades")).toBeInTheDocument();
    });
  });

  describe("Data Display", () => {
    it("should render page title and record count", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 3 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      expect(screen.getByText("交易历史")).toBeInTheDocument();
      expect(screen.getByText("共 3 条记录")).toBeInTheDocument();
    });

    it("should display trade table with data", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 3 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Check table headers
      expect(screen.getByText("时间")).toBeInTheDocument();
      expect(screen.getByText("市场")).toBeInTheDocument();
      expect(screen.getByText("类型")).toBeInTheDocument();
      expect(screen.getByText("金额")).toBeInTheDocument();

      // Check trade data
      expect(screen.getByText("market-1")).toBeInTheDocument();
      expect(screen.getByText("market-2")).toBeInTheDocument();
      expect(screen.getByText("market-3")).toBeInTheDocument();
    });

    it("should display BUY trade type with correct styling", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 3 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      const buyBadge = screen.getByText("BUY YES");
      expect(buyBadge).toBeInTheDocument();
      expect(buyBadge).toHaveClass("badge-profit");
    });

    it("should display SELL trade type with correct styling", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 3 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      const sellBadge = screen.getByText("SELL NO");
      expect(sellBadge).toBeInTheDocument();
      expect(sellBadge).toHaveClass("badge-loss");
    });

    it("should display PAPER mode with correct styling", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 3 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      const paperBadges = screen.getAllByText("PAPER");
      expect(paperBadges.length).toBeGreaterThan(0);
      expect(paperBadges[0]).toHaveClass("badge-paper");
    });

    it("should display LIVE mode with correct styling", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 3 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      const liveBadge = screen.getByText("LIVE");
      expect(liveBadge).toBeInTheDocument();
      expect(liveBadge).toHaveClass("badge-live");
    });

    it("should display filled status with checkmark", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 3 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Filled trades show ✅
      const checkmarks = screen.getAllByText("✅");
      expect(checkmarks.length).toBe(2); // Two filled trades
    });

    it("should display pending status with hourglass", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 3 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Pending trades show ⏳
      expect(screen.getByText("⏳")).toBeInTheDocument();
    });
  });

  describe("Filtering", () => {
    // Story 7.9: Mode filter removed - only type filter remains
    it("should NOT render mode filter buttons (Paper/Live removed)", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 3 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Mode filter should NOT exist
      expect(screen.queryByTestId("mode-filter")).not.toBeInTheDocument();
      expect(screen.queryByText("Paper")).not.toBeInTheDocument();
      expect(screen.queryByText("Live")).not.toBeInTheDocument();
    });

    it("should render type filter buttons (Story 7.9: only filter remaining)", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 3 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // There is only ONE "全部" button now (type filter only)
      const allButtons = screen.getAllByText("全部");
      expect(allButtons.length).toBe(1);
      expect(screen.getByText("买入")).toBeInTheDocument();
      expect(screen.getByText("卖出")).toBeInTheDocument();
    });

    it("should filter trades by type when 买入 button is clicked", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 3 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Click 买入 filter
      fireEvent.click(screen.getByText("买入"));

      // Should filter to only show BUY trades
      expect(screen.getByText("market-1")).toBeInTheDocument();
      expect(screen.getByText("market-3")).toBeInTheDocument();
      // market-2 is SELL, should not be visible after filter
      expect(screen.queryByText("market-2")).not.toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should display empty state when no trades", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: [], total: 0 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      expect(screen.getByText("暂无交易记录")).toBeInTheDocument();
    });

    it("should display zero record count when no trades", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: [], total: 0 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      expect(screen.getByText("共 0 条记录")).toBeInTheDocument();
    });
  });

  describe("Pagination", () => {
    it("should not show pagination when trades fit on one page", async () => {
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 3 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Only 3 trades, fits on one page (PAGE_SIZE = 20)
      expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    });

    it("should show pagination when trades exceed page size", async () => {
      // Create 25 trades to trigger pagination
      const manyTrades: TradeListItem[] = Array.from({ length: 25 }, (_, i) => ({
        id: i + 1,
        market_id: `market-${i + 1}`,
        trade_type: "BUY_YES" as const,
        mode: "PAPER" as const,
        amount: 10.0,
        price: 0.50,
        shares: 20.0,
        status: "FILLED" as const,
        exit_type: null,
        created_at: `2026-02-17T${10 + i}:00:00Z`,
      }));

      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: manyTrades, total: 25 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Should show pagination
      expect(screen.getByRole("navigation")).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("should handle null created_at timestamp", async () => {
      const tradesWithNullDate: TradeListItem[] = [
        {
          id: 1,
          market_id: "market-1",
          trade_type: "BUY_YES",
          mode: "PAPER",
          amount: 10.0,
          price: 0.55,
          shares: 18.18,
          status: "FILLED",
          exit_type: null,
          created_at: null,
        },
      ];

      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: tradesWithNullDate, total: 1 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Should display "-" for null timestamp
      expect(screen.getByText("-")).toBeInTheDocument();
    });

    it("should handle null shares", async () => {
      const tradesWithNullShares: TradeListItem[] = [
        {
          id: 1,
          market_id: "market-1",
          trade_type: "BUY_YES",
          mode: "PAPER",
          amount: 10.0,
          price: 0.55,
          shares: null,
          status: "FILLED",
          exit_type: null,
          created_at: "2026-02-17T10:00:00Z",
        },
      ];

      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: tradesWithNullShares, total: 1 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Should display "-" for null shares
      expect(screen.getByText("-")).toBeInTheDocument();
    });

    it("should handle failed status", async () => {
      const failedTrades: TradeListItem[] = [
        {
          id: 1,
          market_id: "market-1",
          trade_type: "BUY_YES",
          mode: "PAPER",
          amount: 10.0,
          price: 0.55,
          shares: 18.18,
          status: "FAILED",
          exit_type: null,
          created_at: "2026-02-17T10:00:00Z",
        },
      ];

      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: failedTrades, total: 1 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Failed trades show ❌
      expect(screen.getByText("❌")).toBeInTheDocument();
    });
  });
});
