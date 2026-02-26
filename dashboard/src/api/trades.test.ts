/**
 * Trades API tests.
 *
 * Tests for the trades API functions including list and detail endpoints.
 *
 * Story 7.6: 前端 API 集成
 * Story 7.9: 交易历史按模式实时显示 (mode parameter deprecated)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { TradeListItem, TradeResponse } from './types';

// Mock the client module
vi.mock('./client', () => ({
  get: vi.fn(),
  getPaginated: vi.fn(),
}));

describe('Trades API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchTrades', () => {
    it('should call the correct endpoint with default params', async () => {
      const mockTradeItem: TradeListItem = {
        id: 1,
        market_id: 'market-1',
        trade_type: 'BUY_YES',
        mode: 'PAPER',
        amount: 30,
        price: 0.6,
        shares: 50,
        status: 'FILLED',
        exit_type: null,
        created_at: '2026-02-01T10:00:00Z',
      };

      const mockGetPaginated = vi.fn().mockResolvedValue({
        success: true,
        data: [mockTradeItem],
        meta: { total: 1, page: 1, per_page: 20 },
      });

      vi.mocked(await import('./client')).getPaginated = mockGetPaginated;

      const { fetchTrades } = await import('./trades');
      const result = await fetchTrades();

      expect(mockGetPaginated).toHaveBeenCalledWith('/api/trades', {
        params: {
          page: 1,
          per_page: 20,
          type_filter: undefined,
        },
      });
      expect(result.items).toHaveLength(1);
      expect(result.total).toBe(1);
      expect(result.items[0].trade_type).toBe('BUY_YES');
    });

    it('should pass type_filter query param correctly (Story 7.9)', async () => {
      const mockGetPaginated = vi.fn().mockResolvedValue({
        success: true,
        data: [],
        meta: { total: 0, page: 1, per_page: 20 },
      });

      vi.mocked(await import('./client')).getPaginated = mockGetPaginated;

      const { fetchTrades } = await import('./trades');
      await fetchTrades({ page: 1, per_page: 20, type_filter: 'buy' });

      expect(mockGetPaginated).toHaveBeenCalledWith('/api/trades', {
        params: {
          page: 1,
          per_page: 20,
          type_filter: 'buy',
        },
      });
    });
  });

  describe('fetchTrade', () => {
    it('should call the correct endpoint for trade details', async () => {
      const mockTrade: TradeResponse = {
        id: 1,
        market_id: 'market-1',
        trade_type: 'BUY_YES',
        mode: 'PAPER',
        amount: 30,
        price: 0.6,
        shares: 50,
        status: 'FILLED',
        llm_prediction_id: 123,
        position_id: null,
        exit_type: null,
        created_at: '2026-02-01T10:00:00Z',
      };

      const mockGet = vi.fn().mockResolvedValue(mockTrade);
      vi.mocked(await import('./client')).get = mockGet;

      const { fetchTrade } = await import('./trades');
      const result = await fetchTrade(1);

      expect(mockGet).toHaveBeenCalledWith('/api/trades/1');
      expect(result.id).toBe(1);
      expect(result.trade_type).toBe('BUY_YES');
      expect(result.llm_prediction_id).toBe(123);
    });
  });

  describe('tradesApi', () => {
    it('should export all API methods', async () => {
      const { tradesApi } = await import('./trades');

      expect(tradesApi.getList).toBeDefined();
      expect(tradesApi.getById).toBeDefined();
    });
  });
});
