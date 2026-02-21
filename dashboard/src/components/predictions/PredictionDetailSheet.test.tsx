/**
 * Tests for PredictionDetailSheet component.
 *
 * Story 7.8: 预测详情抽屉组件
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// Mock data matching PredictionResponse type
const mockPrediction = {
  id: 1,
  market_id: "market-1",
  market_title: "Will Bitcoin reach $100k by end of 2026?",
  predicted_probability: 0.75,
  confidence: 0.85,
  reasoning:
    "Based on current market trends and institutional adoption, Bitcoin shows strong momentum. Technical indicators suggest continued upward movement with key support levels holding firm.",
  key_assumptions: [
    "Institutional adoption continues at current pace",
    "No major regulatory changes in key markets",
    "Macroeconomic conditions remain favorable",
  ],
  model_used: "gpt-4-turbo",
  recommendation: "BUY_YES",
  actual_outcome: null,
  is_correct: null,
  validated_at: null,
  created_at: "2026-02-15T10:30:00Z",
};

const mockValidatedPrediction = {
  ...mockPrediction,
  actual_outcome: "YES",
  is_correct: true,
  validated_at: "2026-02-20T10:30:00Z",
};

// Mock the usePrediction hook
const mockUsePrediction = vi.fn();
vi.mock("@/hooks/usePredictions", () => ({
  usePrediction: (id: number) => mockUsePrediction(id),
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
import { PredictionDetailSheet } from "./PredictionDetailSheet";

describe("PredictionDetailSheet", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("should show loading skeleton when loading", () => {
      mockUsePrediction.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      // Check for skeleton elements
      const skeletons = screen.getAllByRole("generic").filter((el) =>
        el.className.includes("animate-pulse") ||
        el.className.includes("bg-muted")
      );
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe("Data Display", () => {
    it("should display prediction details correctly", () => {
      mockUsePrediction.mockReturnValue({
        data: mockPrediction,
        isLoading: false,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      // Check market title
      expect(
        screen.getByText("Will Bitcoin reach $100k by end of 2026?")
      ).toBeInTheDocument();

      // Check model
      expect(screen.getByText("gpt-4-turbo")).toBeInTheDocument();

      // Check probability (YES 75%)
      expect(screen.getByText(/YES \(75%\)/)).toBeInTheDocument();

      // Check confidence
      expect(screen.getByText("85%")).toBeInTheDocument();

      // Check reasoning
      expect(
        screen.getByText(/Based on current market trends/)
      ).toBeInTheDocument();

      // Check key assumptions
      expect(
        screen.getByText("Institutional adoption continues at current pace")
      ).toBeInTheDocument();

      // Check recommendation
      expect(screen.getByText("BUY_YES")).toBeInTheDocument();
    });

    it("should display validated prediction result correctly", () => {
      mockUsePrediction.mockReturnValue({
        data: mockValidatedPrediction,
        isLoading: false,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      // Check validation result
      expect(screen.getByText("预测正确")).toBeInTheDocument();
      expect(screen.getByText(/验证时间:/)).toBeInTheDocument();
      expect(screen.getByText("YES")).toBeInTheDocument();
    });

    it("should display NO prediction correctly", () => {
      const noPrediction = {
        ...mockPrediction,
        predicted_probability: 0.25,
        recommendation: "BUY_NO",
      };

      mockUsePrediction.mockReturnValue({
        data: noPrediction,
        isLoading: false,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText(/NO \(25%\)/)).toBeInTheDocument();
      expect(screen.getByText("BUY_NO")).toBeInTheDocument();
    });

    it("should handle prediction without key assumptions", () => {
      const predictionNoAssumptions = {
        ...mockPrediction,
        key_assumptions: null,
      };

      mockUsePrediction.mockReturnValue({
        data: predictionNoAssumptions,
        isLoading: false,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      // Key assumptions section should not be present
      expect(screen.queryByText("关键假设")).not.toBeInTheDocument();
    });

    it("should handle prediction without reasoning", () => {
      const predictionNoReasoning = {
        ...mockPrediction,
        reasoning: null,
      };

      mockUsePrediction.mockReturnValue({
        data: predictionNoReasoning,
        isLoading: false,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      // Reasoning section should not be present
      expect(screen.queryByText("分析过程")).not.toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should display error message when loading fails", () => {
      mockUsePrediction.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error("Network error"),
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText(/加载预测详情失败/)).toBeInTheDocument();
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });

    it("should display not found message when no data and no error", () => {
      mockUsePrediction.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("未找到预测数据")).toBeInTheDocument();
    });
  });

  describe("Sheet Visibility", () => {
    it("should not fetch when predictionId is null", () => {
      mockUsePrediction.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={null}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      // Should not call with a valid ID (0 would be the fallback)
      // The hook's enabled condition should prevent fetching
      expect(mockUsePrediction).toHaveBeenCalledWith(0);
    });
  });

  describe("Confidence Display", () => {
    it("should display high confidence correctly", () => {
      const highConfidencePrediction = {
        ...mockPrediction,
        confidence: 0.9,
      };

      mockUsePrediction.mockReturnValue({
        data: highConfidencePrediction,
        isLoading: false,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("90%")).toBeInTheDocument();
      expect(screen.getByText("高")).toBeInTheDocument();
    });

    it("should display medium confidence correctly", () => {
      const mediumConfidencePrediction = {
        ...mockPrediction,
        confidence: 0.65,
      };

      mockUsePrediction.mockReturnValue({
        data: mediumConfidencePrediction,
        isLoading: false,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("65%")).toBeInTheDocument();
      expect(screen.getByText("中")).toBeInTheDocument();
    });

    it("should display low confidence correctly", () => {
      const lowConfidencePrediction = {
        ...mockPrediction,
        confidence: 0.35,
      };

      mockUsePrediction.mockReturnValue({
        data: lowConfidencePrediction,
        isLoading: false,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("35%")).toBeInTheDocument();
      expect(screen.getByText("低")).toBeInTheDocument();
    });
  });

  describe("Validation Result Display", () => {
    it("should display incorrect prediction result", () => {
      const incorrectPrediction = {
        ...mockPrediction,
        actual_outcome: "NO",
        is_correct: false,
        validated_at: "2026-02-20T10:30:00Z",
      };

      mockUsePrediction.mockReturnValue({
        data: incorrectPrediction,
        isLoading: false,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("预测错误")).toBeInTheDocument();
      expect(screen.getByText(/验证时间:/)).toBeInTheDocument();
    });

    it("should not show validation section for pending predictions", () => {
      mockUsePrediction.mockReturnValue({
        data: mockPrediction,
        isLoading: false,
        error: null,
      });

      render(
        <PredictionDetailSheet
          predictionId={1}
          open={true}
          onOpenChange={() => {}}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.queryByText("验证结果")).not.toBeInTheDocument();
    });
  });
});
