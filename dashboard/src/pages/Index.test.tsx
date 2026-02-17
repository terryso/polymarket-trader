/**
 * Index Page Component Tests
 *
 * Tests for the main Dashboard page including:
 * - Loading state rendering
 * - Error state handling
 * - Data display with statistics
 * - Derived value calculations
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// Mock the hooks
vi.mock("@/hooks/useStatistics", () => ({
  useOverview: vi.fn(),
  useSystemStatus: vi.fn(),
}));

// Mock the layout component
vi.mock("@/components/layout/DashboardLayout", () => ({
  DashboardLayout: ({ children }: { children: ReactNode }) => (
    <div data-testid="dashboard-layout">{children}</div>
  ),
}));

// Mock child components
vi.mock("@/components/dashboard/PnLChart", () => ({
  PnLChart: () => <div data-testid="pnl-chart">PnL Chart</div>,
}));

vi.mock("@/components/dashboard/RecentActivity", () => ({
  RecentActivity: () => <div data-testid="recent-activity">Recent Activity</div>,
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

describe("Index Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("should render loading skeletons while data is loading", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: true,
        data: undefined,
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: true,
        data: undefined,
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      // Should show layout
      expect(screen.getByTestId("dashboard-layout")).toBeInTheDocument();

      // Should show loading skeletons (using Skeleton component)
      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe("Error State", () => {
    it("should render error alert when overview fails to load", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: undefined,
        error: new Error("Network error"),
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: undefined,
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      expect(screen.getByText("无法加载数据: Network error")).toBeInTheDocument();
    });

    it("should still render when system status fails but overview succeeds", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: {
          current_capital: 200,
          initial_capital: 200,
          total_pnl: 0,
          total_pnl_pct: 0,
          win_rate: 0.75,
          total_trades: 10,
          winning_trades: 7,
          losing_trades: 3,
          open_positions: 2,
          trading_enabled: true,
          mode: "PAPER",
        },
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: undefined,
        error: new Error("Status error"),
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      // Should render dashboard content
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });
  });

  describe("Data Display", () => {
    it("should render page title and description", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: {
          current_capital: 200,
          initial_capital: 200,
          total_pnl: 0,
          total_pnl_pct: 0,
          win_rate: 0.75,
          total_trades: 10,
          winning_trades: 7,
          losing_trades: 3,
          open_positions: 2,
          trading_enabled: true,
          mode: "PAPER",
        },
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: {
          trading_enabled: true,
          mode: "PAPER",
          current_capital: 200,
          daily_pnl: 10,
          open_positions: 2,
          consecutive_losses: 0,
          reduced_mode: false,
          last_market_fetch: "2026-02-17T10:00:00Z",
          uptime_hours: 24.5,
        },
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      expect(screen.getByText("Dashboard")).toBeInTheDocument();
      expect(screen.getByText("系统运行概览")).toBeInTheDocument();
    });

    it("should display total capital correctly", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: {
          current_capital: 250.50,
          initial_capital: 200,
          total_pnl: 50.50,
          total_pnl_pct: 0.2525,
          win_rate: 0.75,
          total_trades: 10,
          winning_trades: 7,
          losing_trades: 3,
          open_positions: 2,
          trading_enabled: true,
          mode: "PAPER",
        },
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: {
          trading_enabled: true,
          mode: "PAPER",
          current_capital: 250.50,
          daily_pnl: 10.25,
          open_positions: 2,
          consecutive_losses: 0,
          reduced_mode: false,
          last_market_fetch: "2026-02-17T10:00:00Z",
          uptime_hours: 24.5,
        },
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      expect(screen.getByText("$250.50")).toBeInTheDocument();
    });

    it("should display today PnL with positive values", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: {
          current_capital: 210,
          initial_capital: 200,
          total_pnl: 10,
          total_pnl_pct: 0.05,
          win_rate: 0.75,
          total_trades: 10,
          winning_trades: 7,
          losing_trades: 3,
          open_positions: 2,
          trading_enabled: true,
          mode: "PAPER",
        },
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: {
          trading_enabled: true,
          mode: "PAPER",
          current_capital: 210,
          daily_pnl: 15.50,
          open_positions: 2,
          consecutive_losses: 0,
          reduced_mode: false,
          last_market_fetch: "2026-02-17T10:00:00Z",
          uptime_hours: 24.5,
        },
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      expect(screen.getByText("+$15.50")).toBeInTheDocument();
    });

    it("should display today PnL with negative values", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: {
          current_capital: 190,
          initial_capital: 200,
          total_pnl: -10,
          total_pnl_pct: -0.05,
          win_rate: 0.5,
          total_trades: 10,
          winning_trades: 5,
          losing_trades: 5,
          open_positions: 2,
          trading_enabled: true,
          mode: "PAPER",
        },
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: {
          trading_enabled: true,
          mode: "PAPER",
          current_capital: 190,
          daily_pnl: -5.25,
          open_positions: 2,
          consecutive_losses: 2,
          reduced_mode: false,
          last_market_fetch: "2026-02-17T10:00:00Z",
          uptime_hours: 24.5,
        },
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      expect(screen.getByText("$-5.25")).toBeInTheDocument();
    });

    it("should display win rate percentage", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: {
          current_capital: 200,
          initial_capital: 200,
          total_pnl: 0,
          total_pnl_pct: 0,
          win_rate: 0.75,
          total_trades: 10,
          winning_trades: 7,
          losing_trades: 3,
          open_positions: 2,
          trading_enabled: true,
          mode: "PAPER",
        },
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: {
          trading_enabled: true,
          mode: "PAPER",
          current_capital: 200,
          daily_pnl: 0,
          open_positions: 2,
          consecutive_losses: 0,
          reduced_mode: false,
          last_market_fetch: "2026-02-17T10:00:00Z",
          uptime_hours: 24.5,
        },
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      expect(screen.getByText("75.0%")).toBeInTheDocument();
    });

    it("should display trading status as running when enabled", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: {
          current_capital: 200,
          initial_capital: 200,
          total_pnl: 0,
          total_pnl_pct: 0,
          win_rate: 0.75,
          total_trades: 10,
          winning_trades: 7,
          losing_trades: 3,
          open_positions: 2,
          trading_enabled: true,
          mode: "PAPER",
        },
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: {
          trading_enabled: true,
          mode: "PAPER",
          current_capital: 200,
          daily_pnl: 0,
          open_positions: 2,
          consecutive_losses: 0,
          reduced_mode: false,
          last_market_fetch: "2026-02-17T10:00:00Z",
          uptime_hours: 24.5,
        },
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      expect(screen.getByText(/运行中/)).toBeInTheDocument();
    });

    it("should display trading status as paused when disabled", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: {
          current_capital: 200,
          initial_capital: 200,
          total_pnl: 0,
          total_pnl_pct: 0,
          win_rate: 0.75,
          total_trades: 10,
          winning_trades: 7,
          losing_trades: 3,
          open_positions: 2,
          trading_enabled: false,
          mode: "PAPER",
        },
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: {
          trading_enabled: false,
          mode: "PAPER",
          current_capital: 200,
          daily_pnl: 0,
          open_positions: 2,
          consecutive_losses: 0,
          reduced_mode: false,
          last_market_fetch: "2026-02-17T10:00:00Z",
          uptime_hours: 24.5,
        },
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      expect(screen.getByText(/已暂停/)).toBeInTheDocument();
    });

    it("should render PnLChart component", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: {
          current_capital: 200,
          initial_capital: 200,
          total_pnl: 0,
          total_pnl_pct: 0,
          win_rate: 0.75,
          total_trades: 10,
          winning_trades: 7,
          losing_trades: 3,
          open_positions: 2,
          trading_enabled: true,
          mode: "PAPER",
        },
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: {
          trading_enabled: true,
          mode: "PAPER",
          current_capital: 200,
          daily_pnl: 0,
          open_positions: 2,
          consecutive_losses: 0,
          reduced_mode: false,
          last_market_fetch: "2026-02-17T10:00:00Z",
          uptime_hours: 24.5,
        },
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      expect(screen.getByTestId("pnl-chart")).toBeInTheDocument();
    });

    it("should render RecentActivity component", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: {
          current_capital: 200,
          initial_capital: 200,
          total_pnl: 0,
          total_pnl_pct: 0,
          win_rate: 0.75,
          total_trades: 10,
          winning_trades: 7,
          losing_trades: 3,
          open_positions: 2,
          trading_enabled: true,
          mode: "PAPER",
        },
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: {
          trading_enabled: true,
          mode: "PAPER",
          current_capital: 200,
          daily_pnl: 0,
          open_positions: 2,
          consecutive_losses: 0,
          reduced_mode: false,
          last_market_fetch: "2026-02-17T10:00:00Z",
          uptime_hours: 24.5,
        },
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      expect(screen.getByTestId("recent-activity")).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("should handle zero values gracefully", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: {
          current_capital: 0,
          initial_capital: 0,
          total_pnl: 0,
          total_pnl_pct: 0,
          win_rate: 0,
          total_trades: 0,
          winning_trades: 0,
          losing_trades: 0,
          open_positions: 0,
          trading_enabled: false,
          mode: "PAPER",
        },
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: {
          trading_enabled: false,
          mode: "PAPER",
          current_capital: 0,
          daily_pnl: 0,
          open_positions: 0,
          consecutive_losses: 0,
          reduced_mode: false,
          last_market_fetch: null,
          uptime_hours: null,
        },
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      expect(screen.getByText("$0.00")).toBeInTheDocument();
      expect(screen.getByText("0.0%")).toBeInTheDocument();
    });

    it("should handle null uptime hours", async () => {
      const { useOverview, useSystemStatus } = await import("@/hooks/useStatistics");
      vi.mocked(useOverview).mockReturnValue({
        isLoading: false,
        data: {
          current_capital: 200,
          initial_capital: 200,
          total_pnl: 0,
          total_pnl_pct: 0,
          win_rate: 0.75,
          total_trades: 10,
          winning_trades: 7,
          losing_trades: 3,
          open_positions: 2,
          trading_enabled: true,
          mode: "PAPER",
        },
        error: null,
      } as ReturnType<typeof useOverview>);
      vi.mocked(useSystemStatus).mockReturnValue({
        isLoading: false,
        data: {
          trading_enabled: true,
          mode: "PAPER",
          current_capital: 200,
          daily_pnl: 0,
          open_positions: 2,
          consecutive_losses: 0,
          reduced_mode: false,
          last_market_fetch: null,
          uptime_hours: null,
        },
        error: null,
      } as ReturnType<typeof useSystemStatus>);

      const { default: Index } = await import("./Index");
      render(<Index />, { wrapper: createWrapper() });

      // Should display "-" for null uptime
      expect(screen.getByText("-")).toBeInTheDocument();
    });
  });
});
