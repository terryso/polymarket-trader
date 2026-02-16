/**
 * React Query hooks tests for predictions.
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock the API functions
vi.mock('../api/predictions', () => ({
  fetchPredictions: vi.fn(),
  fetchPrediction: vi.fn(),
  fetchAccuracy: vi.fn(),
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

describe('usePredictions hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('usePredictions', () => {
    it('should fetch and return predictions list data', async () => {
      // Mock data matches PredictionListItem type from types.ts
      const mockPredictions = {
        items: [
          {
            id: 1,
            market_id: 'market-1',
            predicted_probability: 0.85,
            confidence: 0.85,
            recommendation: 'BUY_YES',
            actual_outcome: 'YES',
            is_correct: true,
            created_at: '2026-02-01T10:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        perPage: 20,
      };

      vi.mocked(await import('../api/predictions')).fetchPredictions = vi
        .fn()
        .mockResolvedValue(mockPredictions);

      const { usePredictions } = await import('./usePredictions');
      const { result } = renderHook(() => usePredictions(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockPredictions);
      expect(result.current.data?.items).toHaveLength(1);
    });

    it('should pass params to fetchPredictions', async () => {
      const mockPredictions = {
        items: [],
        total: 0,
        page: 1,
        perPage: 20,
      };

      const fetchPredictionsMock = vi.fn().mockResolvedValue(mockPredictions);
      vi.mocked(await import('../api/predictions')).fetchPredictions =
        fetchPredictionsMock;

      const { usePredictions } = await import('./usePredictions');
      renderHook(
        () =>
          usePredictions({
            page: 1,
            per_page: 20,
            validated: true,
          }),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(fetchPredictionsMock).toHaveBeenCalled());

      expect(fetchPredictionsMock).toHaveBeenCalledWith({
        page: 1,
        per_page: 20,
        validated: true,
      });
    });
  });

  describe('usePrediction', () => {
    it('should fetch and return prediction detail data', async () => {
      // Mock data matches PredictionResponse type from types.ts
      const mockPrediction = {
        id: 1,
        market_id: 'market-1',
        predicted_probability: 0.85,
        confidence: 0.85,
        reasoning: 'Strong upward trend based on technical analysis',
        key_assumptions: ['Market momentum continues', 'No major regulatory changes'],
        model_used: 'gpt-4',
        recommendation: 'BUY_YES',
        actual_outcome: 'YES',
        is_correct: true,
        validated_at: '2026-02-10T10:00:00Z',
        created_at: '2026-02-01T10:00:00Z',
      };

      vi.mocked(await import('../api/predictions')).fetchPrediction = vi
        .fn()
        .mockResolvedValue(mockPrediction);

      const { usePrediction } = await import('./usePredictions');
      const { result } = renderHook(() => usePrediction(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockPrediction);
    });

    it('should not fetch when predictionId is 0', async () => {
      const fetchPredictionMock = vi.fn().mockResolvedValue({});
      vi.mocked(await import('../api/predictions')).fetchPrediction =
        fetchPredictionMock;

      const { usePrediction } = await import('./usePredictions');
      renderHook(() => usePrediction(0), {
        wrapper: createWrapper(),
      });

      // Wait a bit to ensure no fetch happens
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(fetchPredictionMock).not.toHaveBeenCalled();
    });
  });

  describe('useAccuracy', () => {
    it('should fetch and return accuracy stats', async () => {
      // Mock data matches AccuracyStats type from types.ts
      const mockAccuracy = {
        total_predictions: 100,
        validated_predictions: 80,
        correct_predictions: 65,
        accuracy: 0.8125,
        avg_confidence: 0.78,
        by_category: {
          crypto: { total: 50, correct: 40, accuracy: 0.8 },
          politics: { total: 30, correct: 25, accuracy: 0.833 },
        },
      };

      vi.mocked(await import('../api/predictions')).fetchAccuracy = vi
        .fn()
        .mockResolvedValue(mockAccuracy);

      const { useAccuracy } = await import('./usePredictions');
      const { result } = renderHook(() => useAccuracy(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockAccuracy);
      expect(result.current.data?.accuracy).toBe(0.8125);
    });
  });

  describe('predictionsKeys', () => {
    it('should generate correct query keys', async () => {
      const { predictionsKeys } = await import('./usePredictions');

      expect(predictionsKeys.all).toEqual(['predictions']);
      expect(predictionsKeys.list()).toEqual(['predictions', 'list', undefined]);
      expect(predictionsKeys.list({ page: 1 })).toEqual([
        'predictions',
        'list',
        { page: 1 },
      ]);
      expect(predictionsKeys.detail(1)).toEqual(['predictions', 'detail', 1]);
      expect(predictionsKeys.accuracy()).toEqual(['predictions', 'accuracy']);
    });
  });
});
