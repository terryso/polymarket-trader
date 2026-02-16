/**
 * React Query hooks tests for trades.
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock the API functions
vi.mock('../api/trades', () => ({
  fetchTrades: vi.fn(),
  fetchTrade: vi.fn(),
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

describe('useTrades hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useTrades', () => {
    it('should fetch and return trades list data', async () => {
      // Mock data matches TradeListItem type from types.ts
      const mockTrades = {
        items: [
          {
            id: 1,
            market_id: 'market-1',
            trade_type: 'BUY_YES' as const,
            mode: 'PAPER' as const,
            amount: 30,
            price: 0.6,
            shares: 50,
            status: 'filled' as const,
            created_at: '2026-02-01T10:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        perPage: 20,
      };

      vi.mocked(await import('../api/trades')).fetchTrades = vi
        .fn()
        .mockResolvedValue(mockTrades);

      const { useTrades } = await import('./useTrades');
      const { result } = renderHook(() => useTrades(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockTrades);
      expect(result.current.data?.items).toHaveLength(1);
    });

    it('should pass params to fetchTrades', async () => {
      const mockTrades = {
        items: [],
        total: 0,
        page: 1,
        perPage: 20,
      };

      const fetchTradesMock = vi.fn().mockResolvedValue(mockTrades);
      vi.mocked(await import('../api/trades')).fetchTrades = fetchTradesMock;

      const { useTrades } = await import('./useTrades');
      renderHook(
        () =>
          useTrades({
            page: 1,
            per_page: 20,
            mode: 'PAPER',
          }),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(fetchTradesMock).toHaveBeenCalled());

      expect(fetchTradesMock).toHaveBeenCalledWith({
        page: 1,
        per_page: 20,
        mode: 'PAPER',
      });
    });
  });

  describe('useTrade', () => {
    it('should fetch and return trade detail data', async () => {
      // Mock data matches TradeResponse type from types.ts
      const mockTrade = {
        id: 1,
        market_id: 'market-1',
        trade_type: 'BUY_YES' as const,
        mode: 'PAPER' as const,
        amount: 30,
        price: 0.6,
        shares: 50,
        status: 'filled' as const,
        llm_prediction_id: 123,
        position_id: 1,
        created_at: '2026-02-01T10:00:00Z',
      };

      vi.mocked(await import('../api/trades')).fetchTrade = vi
        .fn()
        .mockResolvedValue(mockTrade);

      const { useTrade } = await import('./useTrades');
      const { result } = renderHook(() => useTrade(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockTrade);
    });

    it('should not fetch when tradeId is 0', async () => {
      const fetchTradeMock = vi.fn().mockResolvedValue({});
      vi.mocked(await import('../api/trades')).fetchTrade = fetchTradeMock;

      const { useTrade } = await import('./useTrades');
      renderHook(() => useTrade(0), {
        wrapper: createWrapper(),
      });

      // Wait a bit to ensure no fetch happens
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(fetchTradeMock).not.toHaveBeenCalled();
    });
  });

  describe('tradesKeys', () => {
    it('should generate correct query keys', async () => {
      const { tradesKeys } = await import('./useTrades');

      expect(tradesKeys.all).toEqual(['trades']);
      expect(tradesKeys.list()).toEqual(['trades', 'list', undefined]);
      expect(tradesKeys.list({ page: 1 })).toEqual(['trades', 'list', { page: 1 }]);
      expect(tradesKeys.detail(1)).toEqual(['trades', 'detail', 1]);
      expect(tradesKeys.detail(42)).toEqual(['trades', 'detail', 42]);
    });
  });
});
