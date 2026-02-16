/**
 * React Query hooks tests for positions.
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock the API functions
vi.mock('../api/positions', () => ({
  fetchPositions: vi.fn(),
  fetchPosition: vi.fn(),
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

describe('usePositions hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('usePositions', () => {
    it('should fetch and return positions list data', async () => {
      // Mock data matches PositionListItem type from types.ts
      const mockPositions = [
        {
          id: 1,
          market_id: 'market-1',
          outcome: 'YES' as const,
          shares: 100,
          avg_price: 0.55,
          current_value: 65,
          pnl: 10,
          status: 'open' as const,
          opened_at: '2026-02-01T10:00:00Z',
        },
        {
          id: 2,
          market_id: 'market-2',
          outcome: 'NO' as const,
          shares: 50,
          avg_price: 0.7,
          current_value: 30,
          pnl: -5,
          status: 'open' as const,
          opened_at: '2026-02-02T10:00:00Z',
        },
      ];

      vi.mocked(await import('../api/positions')).fetchPositions = vi
        .fn()
        .mockResolvedValue(mockPositions);

      const { usePositions } = await import('./usePositions');
      const { result } = renderHook(() => usePositions(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockPositions);
      expect(result.current.data).toHaveLength(2);
    });

    it('should return empty array when no positions', async () => {
      vi.mocked(await import('../api/positions')).fetchPositions = vi
        .fn()
        .mockResolvedValue([]);

      const { usePositions } = await import('./usePositions');
      const { result } = renderHook(() => usePositions(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual([]);
    });
  });

  describe('usePosition', () => {
    it('should fetch and return position detail data', async () => {
      // Mock data matches PositionResponse type from types.ts
      const mockPosition = {
        id: 1,
        market_id: 'market-1',
        outcome: 'YES' as const,
        shares: 100,
        avg_price: 0.55,
        initial_value: 55,
        current_value: 65,
        pnl: 10,
        status: 'open' as const,
        opened_at: '2026-02-01T10:00:00Z',
        closed_at: null,
      };

      vi.mocked(await import('../api/positions')).fetchPosition = vi
        .fn()
        .mockResolvedValue(mockPosition);

      const { usePosition } = await import('./usePositions');
      const { result } = renderHook(() => usePosition(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockPosition);
    });

    it('should not fetch when positionId is 0', async () => {
      const fetchPositionMock = vi.fn().mockResolvedValue({});
      vi.mocked(await import('../api/positions')).fetchPosition = fetchPositionMock;

      const { usePosition } = await import('./usePositions');
      renderHook(() => usePosition(0), {
        wrapper: createWrapper(),
      });

      // Wait a bit to ensure no fetch happens
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(fetchPositionMock).not.toHaveBeenCalled();
    });
  });

  describe('positionsKeys', () => {
    it('should generate correct query keys', async () => {
      const { positionsKeys } = await import('./usePositions');

      expect(positionsKeys.all).toEqual(['positions']);
      expect(positionsKeys.list()).toEqual(['positions', 'list']);
      expect(positionsKeys.detail(1)).toEqual(['positions', 'detail', 1]);
      expect(positionsKeys.detail(42)).toEqual(['positions', 'detail', 42]);
    });
  });
});
