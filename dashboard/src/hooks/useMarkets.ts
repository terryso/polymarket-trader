/**
 * React Query hooks for markets API.
 *
 * Story 7.6: 前端 API 集成
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { fetchMarkets, fetchMarket } from '../api/markets';
import type { MarketListItem, MarketResponse, MarketListQueryParams } from '../api/types';

// Query keys for cache management
export const marketsKeys = {
  all: ['markets'] as const,
  list: (params?: MarketListQueryParams) =>
    [...marketsKeys.all, 'list', params] as const,
  detail: (id: string) => [...marketsKeys.all, 'detail', id] as const,
};

/**
 * Hook for fetching market list with pagination and filtering.
 *
 * @param params - Query parameters for pagination and filtering
 */
export function useMarkets(
  params: MarketListQueryParams = {}
): UseQueryResult<
  { items: MarketListItem[]; total: number; page: number; perPage: number },
  Error
> {
  return useQuery({
    queryKey: marketsKeys.list(params),
    queryFn: () => fetchMarkets(params),
    staleTime: 60000, // Market list changes slowly
  });
}

/**
 * Hook for fetching market details by ID.
 *
 * @param marketId - Market unique identifier
 */
export function useMarket(marketId: string): UseQueryResult<MarketResponse, Error> {
  return useQuery({
    queryKey: marketsKeys.detail(marketId),
    queryFn: () => fetchMarket(marketId),
    enabled: !!marketId, // Only fetch if marketId is provided
    staleTime: 60000,
  });
}
