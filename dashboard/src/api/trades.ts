/**
 * Trades API module.
 *
 * Provides functions to fetch trade history including list and detail endpoints.
 *
 * Story 7.6: 前端 API 集成
 * Story 7.9: 交易历史按模式实时显示
 */

import { getPaginated, get, post } from './client';
import type { TradeListItem, TradeResponse, TradeListQueryParams, SyncStatus, SyncResult } from './types';

/**
 * Get trade history with pagination and filtering.
 *
 * Note: Trading mode (paper/live) is now determined by backend TRADING_MODE setting.
 *
 * @param params - Query parameters for pagination and type filtering
 */
export async function fetchTrades(
  params: TradeListQueryParams = {}
): Promise<{ items: TradeListItem[]; total: number; page: number; perPage: number }> {
  const response = await getPaginated<TradeListItem>('/api/trades', {
    params: {
      page: params.page ?? 1,
      per_page: params.per_page ?? 20,
      type_filter: params.type_filter,
      // Note: mode parameter is deprecated - backend uses TRADING_MODE setting
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
 * Get trade sync status.
 *
 * @deprecated Sync is now automatic based on trading mode. See Story 7.9.
 * Story 5.6: 交易历史同步
 */
export async function fetchSyncStatus(): Promise<SyncStatus> {
  return get<SyncStatus>('/api/trades/sync/status');
}

/**
 * Sync trades from Polymarket.
 *
 * @deprecated Sync is now automatic based on trading mode. See Story 7.9.
 * Story 5.6: 交易历史同步
 */
export async function syncTrades(): Promise<SyncResult> {
  return post<SyncResult>('/api/trades/sync');
}

/**
 * Trades API object with all methods.
 */
export const tradesApi = {
  getList: fetchTrades,
  getById: fetchTrade,
  /** @deprecated Sync is now automatic */
  getSyncStatus: fetchSyncStatus,
  /** @deprecated Sync is now automatic */
  sync: syncTrades,
};
