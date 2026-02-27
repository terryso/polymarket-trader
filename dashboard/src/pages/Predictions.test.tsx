/**
 * Predictions page tests.
 *
 * Tests for the Predictions page component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock the hooks
vi.mock('@/hooks/usePredictions', () => ({
  usePredictions: vi.fn(),
  useAccuracy: vi.fn(),
}));

// Mock DashboardLayout
vi.mock('@/components/layout/DashboardLayout', () => ({
  DashboardLayout: ({ children }: { children: ReactNode }) => (
    <div data-testid="dashboard-layout">{children}</div>
  ),
}));

// Mock PredictionDetailSheet
vi.mock('@/components/predictions/PredictionDetailSheet', () => ({
  PredictionDetailSheet: ({
    open,
    onOpenChange,
  }: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
  }) =>
    open ? (
      <div data-testid="prediction-sheet">
        <button onClick={() => onOpenChange(false)}>Close</button>
      </div>
    ) : null,
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

describe('Predictions Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading skeleton while fetching', async () => {
      vi.mocked(await import('@/hooks/usePredictions')).usePredictions = vi
        .fn()
        .mockReturnValue({ isLoading: true, data: undefined });
      vi.mocked(await import('@/hooks/usePredictions')).useAccuracy = vi
        .fn()
        .mockReturnValue({ isLoading: true, data: undefined });

      const { default: Predictions } = await import('./Predictions');
      render(<Predictions />, { wrapper: createWrapper() });

      // Check for loading skeleton
      expect(screen.getByTestId('dashboard-layout')).toBeInTheDocument();
      const skeletons = document.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe('Error State', () => {
    it('should show error alert when fetching fails', async () => {
      vi.mocked(await import('@/hooks/usePredictions')).usePredictions = vi
        .fn()
        .mockReturnValue({
          isLoading: false,
          error: new Error('Network error'),
          data: undefined,
        });
      vi.mocked(await import('@/hooks/usePredictions')).useAccuracy = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: undefined });

      const { default: Predictions } = await import('./Predictions');
      render(<Predictions />, { wrapper: createWrapper() });

      expect(screen.getByText(/无法加载数据/)).toBeInTheDocument();
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    it('should render predictions table with data', async () => {
      const mockPredictions = {
        items: [
          {
            id: 1,
            market_id: 'market-1',
            market_title: 'Test Market',
            market_slug: 'test-market',
            market_yes_price: 0.65,
            predicted_probability: 0.8,
            confidence: 0.75,
            edge: 0.15,
            recommendation: 'BUY_YES',
            actual_outcome: null,
            is_correct: null,
            created_at: '2024-01-15T10:00:00Z',
          },
        ],
        total: 1,
      };

      const mockAccuracy = {
        total_predictions: 10,
        validated_predictions: 5,
        correct_predictions: 3,
        accuracy: 0.6,
        avg_confidence: 0.7,
        by_category: {},
      };

      vi.mocked(await import('@/hooks/usePredictions')).usePredictions = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: mockPredictions, error: null });
      vi.mocked(await import('@/hooks/usePredictions')).useAccuracy = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: mockAccuracy });

      const { default: Predictions } = await import('./Predictions');
      render(<Predictions />, { wrapper: createWrapper() });

      // Check title
      expect(screen.getByText('预测记录')).toBeInTheDocument();

      // Check stats
      expect(screen.getByText('总预测')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument(); // total_predictions from accuracy

      // Check market title in table
      expect(screen.getByText('Test Market')).toBeInTheDocument();
    });

    it('should show empty state when no predictions', async () => {
      vi.mocked(await import('@/hooks/usePredictions')).usePredictions = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: { items: [], total: 0 }, error: null });
      vi.mocked(await import('@/hooks/usePredictions')).useAccuracy = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: null });

      const { default: Predictions } = await import('./Predictions');
      render(<Predictions />, { wrapper: createWrapper() });

      expect(screen.getByText('暂无预测记录')).toBeInTheDocument();
    });

    it('should display correct prediction status', async () => {
      const mockPredictions = {
        items: [
          {
            id: 1,
            market_id: 'market-1',
            market_title: 'Test',
            market_slug: null,
            market_yes_price: 0.5,
            predicted_probability: 0.7,
            confidence: 0.8,
            edge: null,
            recommendation: null,
            actual_outcome: 'YES',
            is_correct: true,
            created_at: '2024-01-15T10:00:00Z',
          },
          {
            id: 2,
            market_id: 'market-2',
            market_title: 'Test 2',
            market_slug: null,
            market_yes_price: 0.5,
            predicted_probability: 0.3,
            confidence: 0.6,
            edge: null,
            recommendation: null,
            actual_outcome: 'YES',
            is_correct: false,
            created_at: '2024-01-15T10:00:00Z',
          },
        ],
        total: 2,
      };

      vi.mocked(await import('@/hooks/usePredictions')).usePredictions = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: mockPredictions, error: null });
      vi.mocked(await import('@/hooks/usePredictions')).useAccuracy = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: null });

      const { default: Predictions } = await import('./Predictions');
      render(<Predictions />, { wrapper: createWrapper() });

      // Check correct status
      expect(screen.getByText('✅ 正确')).toBeInTheDocument();
      expect(screen.getByText('❌ 错误')).toBeInTheDocument();
    });
  });

  describe('Pagination', () => {
    it('should show pagination when total exceeds page size', async () => {
      const mockPredictions = {
        items: Array.from({ length: 20 }, (_, i) => ({
          id: i + 1,
          market_id: `market-${i}`,
          market_title: `Market ${i}`,
          market_slug: null,
          market_yes_price: 0.5,
          predicted_probability: 0.5,
          confidence: 0.5,
          edge: null,
          recommendation: null,
          actual_outcome: null,
          is_correct: null,
          created_at: '2024-01-15T10:00:00Z',
        })),
        total: 50, // More than PAGE_SIZE (20)
      };

      vi.mocked(await import('@/hooks/usePredictions')).usePredictions = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: mockPredictions, error: null });
      vi.mocked(await import('@/hooks/usePredictions')).useAccuracy = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: null });

      const { default: Predictions } = await import('./Predictions');
      render(<Predictions />, { wrapper: createWrapper() });

      // Pagination should be visible
      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });
  });
});
