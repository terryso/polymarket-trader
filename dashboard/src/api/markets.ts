/**
 * Markets API module.
 *
 * Provides functions to fetch market data including list and detail endpoints.
 *
 * Story 7.6: 前端 API 集成
 */

import { get, getPaginated } from './client';
import type { MarketListItem, MarketResponse, MarketListQueryParams } from './types';

/**
 * Get market list with pagination and filtering.
 *
 * @param params - Query parameters for pagination and filtering
 */
export async function fetchMarkets(
  params: MarketListQueryParams = {}
): Promise<{ items: MarketListItem[]; total: number; page: number; perPage: number }> {
  const response = await getPaginated<MarketListItem>('/api/markets', {
    params: {
      page: params.page ?? 1,
      per_page: params.per_page ?? 20,
      status: params.status,
      category: params.category,
    },
  });
  return {
    items: response.data,
    total: response.meta.total,
    page: response.meta.page,
    perPage: response.meta.per_page,
  };
}

/**
 * Get market details by ID.
 *
 * @param marketId - Market unique identifier
 */
export async function fetchMarket(marketId: string): Promise<MarketResponse> {
  return get<MarketResponse>(`/api/markets/${marketId}`);
}

/**
 * Markets API object with all methods.
 */
export const marketsApi = {
  getList: fetchMarkets,
  getById: fetchMarket,
};
