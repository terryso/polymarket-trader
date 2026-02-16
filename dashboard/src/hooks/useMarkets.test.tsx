/**
 * React Query hooks tests for markets.
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock the API functions
vi.mock('../api/markets', () => ({
  fetchMarkets: vi.fn(),
  fetchMarket: vi.fn(),
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

describe('useMarkets hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useMarkets', () => {
    it('should fetch and return market list data', async () => {
      // Mock data matches MarketListItem type from types.ts
      const mockMarkets = {
        items: [
          {
            id: 'market-1',
            title: 'Will Bitcoin reach $100k?',
            category: 'crypto' as const,
            yes_price: 0.65,
            no_price: 0.35,
            liquidity: 50000,
            deadline: '2026-12-31T23:59:59Z',
            resolution_status: null,
          },
        ],
        total: 1,
        page: 1,
        perPage: 20,
      };

      vi.mocked(await import('../api/markets')).fetchMarkets = vi
        .fn()
        .mockResolvedValue(mockMarkets);

      const { useMarkets } = await import('./useMarkets');
      const { result } = renderHook(() => useMarkets(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockMarkets);
    });

    it('should pass params to fetchMarkets', async () => {
      const mockMarkets = {
        items: [],
        total: 0,
        page: 2,
        perPage: 10,
      };

      const fetchMarketsMock = vi.fn().mockResolvedValue(mockMarkets);
      vi.mocked(await import('../api/markets')).fetchMarkets = fetchMarketsMock;

      const { useMarkets } = await import('./useMarkets');
      renderHook(
        () =>
          useMarkets({
            page: 2,
            per_page: 10,
            status: 'active',
          }),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(fetchMarketsMock).toHaveBeenCalled());

      expect(fetchMarketsMock).toHaveBeenCalledWith({
        page: 2,
        per_page: 10,
        status: 'active',
      });
    });
  });

  describe('useMarket', () => {
    it('should fetch and return market detail data', async () => {
      // Mock data matches MarketResponse type from types.ts
      const mockMarket = {
        id: 'market-1',
        title: 'Will Bitcoin reach $100k?',
        description: 'Detailed description',
        category: 'crypto' as const,
        yes_price: 0.65,
        no_price: 0.35,
        liquidity: 50000,
        deadline: '2026-12-31T23:59:59Z',
        resolution_status: null,
        resolution_outcome: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-02-01T00:00:00Z',
      };

      vi.mocked(await import('../api/markets')).fetchMarket = vi
        .fn()
        .mockResolvedValue(mockMarket);

      const { useMarket } = await import('./useMarkets');
      const { result } = renderHook(() => useMarket('market-1'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockMarket);
    });

    it('should not fetch when marketId is empty', async () => {
      const fetchMarketMock = vi.fn().mockResolvedValue({});
      vi.mocked(await import('../api/markets')).fetchMarket = fetchMarketMock;

      const { useMarket } = await import('./useMarkets');
      renderHook(() => useMarket(''), {
        wrapper: createWrapper(),
      });

      // Wait a bit to ensure no fetch happens
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(fetchMarketMock).not.toHaveBeenCalled();
    });
  });

  describe('marketsKeys', () => {
    it('should generate correct query keys', async () => {
      const { marketsKeys } = await import('./useMarkets');

      expect(marketsKeys.all).toEqual(['markets']);
      expect(marketsKeys.list()).toEqual(['markets', 'list', undefined]);
      expect(marketsKeys.list({ page: 1 })).toEqual(['markets', 'list', { page: 1 }]);
      expect(marketsKeys.detail('market-1')).toEqual(['markets', 'detail', 'market-1']);
    });
  });
});
