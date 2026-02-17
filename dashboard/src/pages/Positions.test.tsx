/**
 * Positions Page Component Tests
 *
 * Tests for the Positions page including:
 * - Loading state rendering
 * - Error state handling
 * - Position table display
 * - Total value and PnL calculations
 * - Empty state handling
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import type { PositionListItem } from "@/api/types";

// Mock the hook
vi.mock("@/hooks/usePositions", () => ({
  usePositions: vi.fn(),
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

// Mock positions data
const mockPositions: PositionListItem[] = [
  {
    id: 1,
    market_id: "market-1",
    outcome: "YES",
    shares: 100,
    avg_price: 0.55,
    current_value: 65,
    pnl: 10,
    status: "open",
    opened_at: "2026-02-01T10:00:00Z",
  },
  {
    id: 2,
    market_id: "market-2",
    outcome: "NO",
    shares: 50,
    avg_price: 0.70,
    current_value: 30,
    pnl: -5,
    status: "open",
    opened_at: "2026-02-02T10:00:00Z",
  },
];

describe("Positions Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("should render loading skeletons while data is loading", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: true,
        data: undefined,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      expect(screen.getByTestId("dashboard-layout")).toBeInTheDocument();

      // Should show loading skeletons
      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe("Error State", () => {
    it("should render error alert when positions fail to load", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: undefined,
        error: new Error("Failed to fetch positions"),
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      expect(screen.getByText("无法加载数据: Failed to fetch positions")).toBeInTheDocument();
    });
  });

  describe("Data Display", () => {
    it("should render page title and description", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: mockPositions,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      expect(screen.getByText("持仓")).toBeInTheDocument();
      expect(screen.getByText("当前持有头寸")).toBeInTheDocument();
    });

    it("should display total position value", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: mockPositions,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      // Total value: 65 + 30 = 95
      expect(screen.getByText("$95.00")).toBeInTheDocument();
    });

    it("should display total PnL", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: mockPositions,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      // Total PnL: 10 + (-5) = 5
      expect(screen.getByText("+$5.00")).toBeInTheDocument();
    });

    it("should display negative total PnL", async () => {
      const negativePnLPositions: PositionListItem[] = [
        {
          id: 1,
          market_id: "market-1",
          outcome: "YES",
          shares: 100,
          avg_price: 0.55,
          current_value: 45,
          pnl: -10,
          status: "open",
          opened_at: "2026-02-01T10:00:00Z",
        },
      ];

      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: negativePnLPositions,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      // Both total PnL card and table show $-10.00
      const negativeValues = screen.getAllByText("$-10.00");
      expect(negativeValues.length).toBeGreaterThanOrEqual(1);
    });

    it("should display position table with data", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: mockPositions,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      // Check table headers
      expect(screen.getByText("市场 ID")).toBeInTheDocument();
      expect(screen.getByText("方向")).toBeInTheDocument();
      expect(screen.getByText("份额")).toBeInTheDocument();
      expect(screen.getByText("成本价")).toBeInTheDocument();
      expect(screen.getByText("当前价值")).toBeInTheDocument();
      expect(screen.getByText("PnL")).toBeInTheDocument();

      // Check position data
      expect(screen.getByText("market-1")).toBeInTheDocument();
      expect(screen.getByText("market-2")).toBeInTheDocument();
    });

    it("should display YES outcome with correct styling", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: mockPositions,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      const yesBadge = screen.getByText("YES");
      expect(yesBadge).toBeInTheDocument();
      expect(yesBadge).toHaveClass("badge-profit");
    });

    it("should display NO outcome with correct styling", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: mockPositions,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      const noBadge = screen.getByText("NO");
      expect(noBadge).toBeInTheDocument();
      expect(noBadge).toHaveClass("badge-loss");
    });

    it("should display positive PnL with profit styling", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: mockPositions,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      // First position has +$10.00 PnL
      const positivePnL = screen.getByText("+$10.00");
      expect(positivePnL).toBeInTheDocument();
      expect(positivePnL).toHaveClass("profit-text");
    });

    it("should display negative PnL with loss styling", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: mockPositions,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      // Second position has $-5.00 PnL (component renders as $-5.00)
      const negativePnL = screen.getByText("$-5.00");
      expect(negativePnL).toBeInTheDocument();
      expect(negativePnL).toHaveClass("loss-text");
    });
  });

  describe("Empty State", () => {
    it("should display empty state when no positions", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: [],
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      expect(screen.getByText("暂无持仓数据")).toBeInTheDocument();
    });

    it("should display zero total value when no positions", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: [],
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      // Total value should be $0.00 (at least one for total value)
      const zeroValues = screen.getAllByText("$0.00");
      expect(zeroValues.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("Edge Cases", () => {
    it("should handle null current_value by calculating from shares * avg_price", async () => {
      const positionsWithNullValue: PositionListItem[] = [
        {
          id: 1,
          market_id: "market-1",
          outcome: "YES",
          shares: 100,
          avg_price: 0.50,
          current_value: null, // Should use shares * avg_price = 50
          pnl: 5,
          status: "open",
          opened_at: "2026-02-01T10:00:00Z",
        },
      ];

      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: positionsWithNullValue,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      // Should show $50.00 (100 * 0.50) - may appear multiple times (table + total)
      const fiftyValues = screen.getAllByText("$50.00");
      expect(fiftyValues.length).toBeGreaterThanOrEqual(1);
    });

    it("should handle null PnL", async () => {
      const positionsWithNullPnL: PositionListItem[] = [
        {
          id: 1,
          market_id: "market-1",
          outcome: "YES",
          shares: 100,
          avg_price: 0.50,
          current_value: 50,
          pnl: null,
          status: "open",
          opened_at: "2026-02-01T10:00:00Z",
        },
      ];

      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: positionsWithNullPnL,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      // Should show +$0.00 for null PnL (0 >= 0, so prefix is +)
      // May appear multiple times
      const zeroPnL = screen.getAllByText("+$0.00");
      expect(zeroPnL.length).toBeGreaterThanOrEqual(1);
    });

    it("should handle undefined data", async () => {
      const { usePositions } = await import("@/hooks/usePositions");
      vi.mocked(usePositions).mockReturnValue({
        isLoading: false,
        data: undefined,
        error: null,
      } as ReturnType<typeof usePositions>);

      const { default: Positions } = await import("./Positions");
      render(<Positions />, { wrapper: createWrapper() });

      // Should show empty state
      expect(screen.getByText("暂无持仓数据")).toBeInTheDocument();
    });
  });
});
