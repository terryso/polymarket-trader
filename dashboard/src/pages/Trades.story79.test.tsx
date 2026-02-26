/**
 * Trades Page Story 7.9 Component Tests
 *
 * Tests for the Trades page mode-based data source feature:
 * - Sync button removed
 * - Mode filter removed
 * - Type filter kept
 * - Loading state works
 *
 * Story 7.9: 交易历史按模式实时显示
 *
 * RED PHASE: These tests will fail until the feature is implemented.
 * Run with: cd dashboard && npm test -- Trades.story79.test.tsx
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
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

// Mock the trades API
vi.mock("@/api/trades", () => ({
  tradesApi: {
    getSyncStatus: vi.fn(),
    sync: vi.fn(),
  },
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
    created_at: "2026-02-27T10:00:00Z",
  },
  {
    id: 2,
    market_id: "market-2",
    trade_type: "SELL_NO",
    mode: "LIVE",
    amount: 5.0,
    price: 0.70,
    shares: 7.14,
    status: "FILLED",
    exit_type: null,
    created_at: "2026-02-27T11:00:00Z",
  },
];

describe("Trades Page - Story 7.9", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ========================================================================
  // TEST: Sync Button Removed (P1)
  // ========================================================================

  describe("Sync Button Removal", () => {
    it.skip("should not render sync button", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 2 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Sync button should NOT exist
      expect(screen.queryByTestId("sync-button")).not.toBeInTheDocument();
      expect(screen.queryByText("同步")).not.toBeInTheDocument();
    });

    it.skip("should not render sync status display", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 2 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Sync status display should NOT exist
      expect(screen.queryByText(/最后同步/)).not.toBeInTheDocument();
    });

    it.skip("should not render sync result alert", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 2 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Sync result alert should NOT exist
      expect(screen.queryByTestId("sync-result")).not.toBeInTheDocument();
      expect(screen.queryByText(/同步完成/)).not.toBeInTheDocument();
    });
  });

  // ========================================================================
  // TEST: Mode Filter Removed (P1)
  // ========================================================================

  describe("Mode Filter Removal", () => {
    it.skip("should not render mode filter", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 2 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Mode filter should NOT exist
      expect(screen.queryByTestId("mode-filter")).not.toBeInTheDocument();
    });

    it.skip("should not render Paper/Live filter buttons", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 2 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Paper/Live buttons should NOT exist as filters
      // Note: "Paper" and "Live" might still appear in table data
      const filterSection = screen.queryByTestId("mode-filter");
      expect(filterSection).not.toBeInTheDocument();
    });

    it.skip("should not call useTrades with mode parameter", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { useTrades } = await import("@/hooks/useTrades");
      const mockUseTrades = vi.mocked(useTrades);
      mockUseTrades.mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 2 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // useTrades should be called WITHOUT mode parameter
      // (mode is now determined by backend settings, not frontend)
      const calls = mockUseTrades.mock.calls;
      const lastCall = calls[calls.length - 1]?.[0];

      // Should not pass mode to useTrades
      expect(lastCall?.mode).toBeUndefined();
    });
  });

  // ========================================================================
  // TEST: Type Filter Kept (P1)
  // ========================================================================

  describe("Type Filter Retained", () => {
    it.skip("should render type filter buttons", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 2 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Type filter should still exist
      expect(screen.getByTestId("type-filter")).toBeInTheDocument();
    });

    it.skip("should render 买入 and 卖出 buttons", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 2 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Buy/Sell filter buttons should exist
      expect(screen.getByText("买入")).toBeInTheDocument();
      expect(screen.getByText("卖出")).toBeInTheDocument();
    });

    it.skip("should have only one filter group (type)", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 2 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // There should be exactly one filter group (type filter)
      const filterGroups = document.querySelectorAll('[data-testid$="-filter"]');
      expect(filterGroups.length).toBe(1);

      // That one filter should be the type filter
      expect(screen.getByTestId("type-filter")).toBeInTheDocument();
    });
  });

  // ========================================================================
  // TEST: Loading State (P2)
  // ========================================================================

  describe("Loading State", () => {
    it.skip("should show loading skeleton while data is loading", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: true,
        data: undefined,
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Loading skeleton should be shown
      expect(screen.getByTestId("loading-skeleton")).toBeInTheDocument();
    });

    it.skip("should not show loading skeleton when data is loaded", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 2 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Loading skeleton should NOT be shown
      expect(screen.queryByTestId("loading-skeleton")).not.toBeInTheDocument();
    });
  });

  // ========================================================================
  // TEST: Error State (P2)
  // ========================================================================

  describe("Error State", () => {
    it.skip("should show error message when API fails", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: undefined,
        error: new Error("API error"),
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Error alert should be shown
      expect(screen.getByTestId("error-alert")).toBeInTheDocument();
    });
  });

  // ========================================================================
  // TEST: No Sync API Calls (P2)
  // ========================================================================

  describe("No Sync API Calls", () => {
    it.skip("should not call getSyncStatus on mount", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { tradesApi } = await import("@/api/trades");
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 2 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Should NOT call getSyncStatus
      expect(tradesApi.getSyncStatus).not.toHaveBeenCalled();
    });

    it.skip("should not call sync on any interaction", async () => {
      // RED PHASE: This test will fail until feature is implemented
      const { tradesApi } = await import("@/api/trades");
      const { useTrades } = await import("@/hooks/useTrades");
      vi.mocked(useTrades).mockReturnValue({
        isLoading: false,
        data: { items: mockTrades, total: 2 },
        error: null,
      } as ReturnType<typeof useTrades>);

      const { default: Trades } = await import("./Trades");
      render(<Trades />, { wrapper: createWrapper() });

      // Should NOT call sync
      expect(tradesApi.sync).not.toHaveBeenCalled();
    });
  });
});
