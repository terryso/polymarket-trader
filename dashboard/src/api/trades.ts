/**
 * Trades API module.
 *
 * Provides functions to fetch trade history including list and detail endpoints.
 *
 * Story 7.6: 前端 API 集成
 */

import { getPaginated, get } from './client';
import type { TradeListItem, TradeResponse, TradeListQueryParams } from './types';

/**
 * Get trade history with pagination and filtering.
 *
 * @param params - Query parameters for pagination and filtering
 */
export async function fetchTrades(
  params: TradeListQueryParams = {}
): Promise<{ items: TradeListItem[]; total: number; page: number; perPage: number }> {
  const response = await getPaginated<TradeListItem>('/api/trades', {
    params: {
      page: params.page ?? 1,
      per_page: params.per_page ?? 20,
      mode: params.mode,
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
 * Get trade details by ID.
 *
 * @param tradeId - Trade unique identifier
 */
export async function fetchTrade(tradeId: number): Promise<TradeResponse> {
  return get<TradeResponse>(`/api/trades/${tradeId}`);
}

/**
 * Trades API object with all methods.
 */
export const tradesApi = {
  getList: fetchTrades,
  getById: fetchTrade,
};
