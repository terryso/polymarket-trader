/**
 * RecentActivity component tests.
 *
 * Story 7.7: 最近活动 API 与前端集成
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// Mock data matching ActivityItem type
const mockActivities = {
  items: [
    {
      id: "trade-1",
      type: "trade" as const,
      description: "买入 特朗普胜选 YES @ $0.60",
      time: "10:30",
      amount: 10.0,
      timestamp: "2026-02-18T10:30:00Z",
    },
    {
      id: "trade-2",
      type: "trade" as const,
      description: "买入 比特币 > $100k NO @ $0.65",
      time: "09:15",
      amount: 8.0,
      timestamp: "2026-02-18T09:15:00Z",
    },
    {
      id: "prediction-1",
      type: "prediction" as const,
      description: "预测 特朗普胜选 75% BUY_YES",
      time: "09:00",
      amount: null,
      timestamp: "2026-02-18T09:00:00Z",
    },
    {
      id: "prediction-2",
      type: "prediction" as const,
      description: "预测 比特币 > $100k 35% NO_TRADE",
      time: "08:30",
      amount: null,
      timestamp: "2026-02-18T08:30:00Z",
    },
    {
      id: "system-1",
      type: "system" as const,
      description: "系统启动，开始扫描市场",
      time: "08:00",
      amount: null,
      timestamp: null,
    },
  ],
  total: 5,
};

// Mock the useActivities hook
const mockUseActivities = vi.fn();
vi.mock("@/hooks/useActivities", () => ({
  useActivities: () => mockUseActivities(),
}));

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

// Import component after mocks are set up
import { RecentActivity } from "./RecentActivity";

describe("RecentActivity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("with successful data", () => {
    beforeEach(() => {
      mockUseActivities.mockReturnValue({
        data: mockActivities,
        isLoading: false,
        isError: false,
        error: null,
      });
    });

    it("renders the component title", () => {
      render(<RecentActivity />, { wrapper: createWrapper() });
      expect(screen.getByText("最近活动")).toBeInTheDocument();
    });

    it("renders activity items from data", () => {
      render(<RecentActivity />, { wrapper: createWrapper() });
      // Check for some known activity descriptions
      expect(screen.getByText(/买入 特朗普胜选 YES/)).toBeInTheDocument();
      expect(screen.getByText(/买入 比特币 > \$100k NO/)).toBeInTheDocument();
      expect(screen.getByText(/预测 特朗普胜选 75%/)).toBeInTheDocument();
    });

    it("renders time for each activity", () => {
      render(<RecentActivity />, { wrapper: createWrapper() });
      // Check for known times from mock data
      expect(screen.getByText("10:30")).toBeInTheDocument();
      expect(screen.getByText("09:15")).toBeInTheDocument();
      expect(screen.getByText("09:00")).toBeInTheDocument();
    });

    it("renders amounts for trade activities", () => {
      render(<RecentActivity />, { wrapper: createWrapper() });
      // Check for amount display ($10.00 and $8.00)
      expect(screen.getByText("$10.00")).toBeInTheDocument();
      expect(screen.getByText("$8.00")).toBeInTheDocument();
    });

    it("renders all activity items", () => {
      render(<RecentActivity />, { wrapper: createWrapper() });
      // mockActivities has 5 items
      const activityItems = screen.getAllByText(/\d{2}:\d{2}/);
      expect(activityItems).toHaveLength(5);
    });

    it("renders system activity without amount", () => {
      render(<RecentActivity />, { wrapper: createWrapper() });
      expect(screen.getByText(/系统启动，开始扫描市场/)).toBeInTheDocument();
    });

    it("renders prediction activity without amount", () => {
      render(<RecentActivity />, { wrapper: createWrapper() });
      expect(screen.getByText(/预测 比特币 > \$100k 35%/)).toBeInTheDocument();
    });
  });

  describe("loading state", () => {
    it("shows loading spinner when loading", () => {
      mockUseActivities.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      });

      render(<RecentActivity />, { wrapper: createWrapper() });

      expect(screen.getByText("最近活动")).toBeInTheDocument();
      // Check for loader icon (Loader2 with animate-spin class)
      const loader = document.querySelector(".animate-spin");
      expect(loader).toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("shows error message when fetch fails", () => {
      mockUseActivities.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error("Network error"),
      });

      render(<RecentActivity />, { wrapper: createWrapper() });

      expect(screen.getByText(/加载失败:/)).toBeInTheDocument();
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });
  });

  describe("empty state", () => {
    it("shows empty message when no activities", () => {
      mockUseActivities.mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
        isError: false,
        error: null,
      });

      render(<RecentActivity />, { wrapper: createWrapper() });

      expect(screen.getByText("暂无活动记录")).toBeInTheDocument();
    });
  });
});
