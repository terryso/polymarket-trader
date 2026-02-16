/**
 * React Query hooks for trades API.
 *
 * Story 7.6: 前端 API 集成
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { fetchTrades, fetchTrade } from '../api/trades';
import type { TradeListItem, TradeResponse, TradeListQueryParams } from '../api/types';

// Query keys for cache management
export const tradesKeys = {
  all: ['trades'] as const,
  list: (params?: TradeListQueryParams) =>
    [...tradesKeys.all, 'list', params] as const,
  detail: (id: number) => [...tradesKeys.all, 'detail', id] as const,
};

/**
 * Hook for fetching trade history with pagination and filtering.
 * Refreshes every 60 seconds (trades change slowly).
 *
 * @param params - Query parameters for pagination and filtering
 */
export function useTrades(
  params: TradeListQueryParams = {}
): UseQueryResult<
  { items: TradeListItem[]; total: number; page: number; perPage: number },
  Error
> {
  return useQuery({
    queryKey: tradesKeys.list(params),
    queryFn: () => fetchTrades(params),
    refetchInterval: 60000, // Refresh every 60 seconds
    staleTime: 30000,
  });
}

/**
 * Hook for fetching trade details by ID.
 *
 * @param tradeId - Trade unique identifier
 */
export function useTrade(tradeId: number): UseQueryResult<TradeResponse, Error> {
  return useQuery({
    queryKey: tradesKeys.detail(tradeId),
    queryFn: () => fetchTrade(tradeId),
    enabled: !!tradeId, // Only fetch if tradeId is provided
    staleTime: 60000,
  });
}
