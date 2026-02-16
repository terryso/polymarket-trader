/**
 * Trades API tests.
 *
 * Tests for the trades API functions including list and detail endpoints.
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

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
      const mockGetPaginated = vi.fn().mockResolvedValue({
        success: true,
        data: [
          {
            id: 1,
            condition_id: 'market-1',
            question: 'Will Bitcoin reach $100k?',
            outcome: 'Yes',
            side: 'BUY',
            size: 50,
            price: 0.6,
            total_cost: 30,
            timestamp: '2026-02-01T10:00:00Z',
            mode: 'PAPER',
          },
        ],
        meta: { total: 1, page: 1, per_page: 20 },
      });

      vi.mocked(await import('./client')).getPaginated = mockGetPaginated;

      const { fetchTrades } = await import('./trades');
      const result = await fetchTrades();

      expect(mockGetPaginated).toHaveBeenCalledWith('/api/trades', {
        params: {
          page: 1,
          per_page: 20,
          mode: undefined,
        },
      });
      expect(result.items).toHaveLength(1);
      expect(result.total).toBe(1);
      expect(result.items[0].side).toBe('BUY');
    });

    it('should pass query params correctly', async () => {
      const mockGetPaginated = vi.fn().mockResolvedValue({
        success: true,
        data: [],
        meta: { total: 0, page: 1, per_page: 20 },
      });

      vi.mocked(await import('./client')).getPaginated = mockGetPaginated;

      const { fetchTrades } = await import('./trades');
      await fetchTrades({ page: 1, per_page: 20, mode: 'PAPER' });

      expect(mockGetPaginated).toHaveBeenCalledWith('/api/trades', {
        params: {
          page: 1,
          per_page: 20,
          mode: 'PAPER',
        },
      });
    });
  });

  describe('fetchTrade', () => {
    it('should call the correct endpoint for trade details', async () => {
      const mockTrade = {
        id: 1,
        condition_id: 'market-1',
        question: 'Will Bitcoin reach $100k?',
        description: 'Detailed description',
        outcome: 'Yes',
        side: 'BUY',
        size: 50,
        price: 0.6,
        total_cost: 30,
        fee: 0.1,
        timestamp: '2026-02-01T10:00:00Z',
        mode: 'PAPER',
        prediction_id: 123,
      };

      const mockGet = vi.fn().mockResolvedValue(mockTrade);
      vi.mocked(await import('./client')).get = mockGet;

      const { fetchTrade } = await import('./trades');
      const result = await fetchTrade(1);

      expect(mockGet).toHaveBeenCalledWith('/api/trades/1');
      expect(result.id).toBe(1);
      expect(result.side).toBe('BUY');
      expect(result.prediction_id).toBe(123);
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
