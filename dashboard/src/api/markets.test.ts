/**
 * Markets API tests.
 *
 * Tests for the markets API functions including list and detail endpoints.
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the client module
vi.mock('./client', () => ({
  get: vi.fn(),
  getPaginated: vi.fn(),
}));

describe('Markets API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchMarkets', () => {
    it('should call the correct endpoint with default params', async () => {
      const mockGetPaginated = vi.fn().mockResolvedValue({
        success: true,
        data: [
          {
            condition_id: 'market-1',
            question: 'Will Bitcoin reach $100k?',
            category: 'Crypto',
            status: 'OPEN',
            current_price: 0.65,
          },
        ],
        meta: { total: 1, page: 1, per_page: 20 },
      });

      vi.mocked(await import('./client')).getPaginated = mockGetPaginated;

      const { fetchMarkets } = await import('./markets');
      const result = await fetchMarkets();

      expect(mockGetPaginated).toHaveBeenCalledWith('/api/markets', {
        params: {
          page: 1,
          per_page: 20,
          status: undefined,
          category: undefined,
        },
      });
      expect(result.items).toHaveLength(1);
      expect(result.total).toBe(1);
      expect(result.page).toBe(1);
      expect(result.perPage).toBe(20);
    });

    it('should pass query params correctly', async () => {
      const mockGetPaginated = vi.fn().mockResolvedValue({
        success: true,
        data: [],
        meta: { total: 0, page: 2, per_page: 10 },
      });

      vi.mocked(await import('./client')).getPaginated = mockGetPaginated;

      const { fetchMarkets } = await import('./markets');
      await fetchMarkets({ page: 2, per_page: 10, status: 'OPEN', category: 'Crypto' });

      expect(mockGetPaginated).toHaveBeenCalledWith('/api/markets', {
        params: {
          page: 2,
          per_page: 10,
          status: 'OPEN',
          category: 'Crypto',
        },
      });
    });
  });

  describe('fetchMarket', () => {
    it('should call the correct endpoint for market details', async () => {
      const mockMarket = {
        condition_id: 'market-1',
        question: 'Will Bitcoin reach $100k?',
        description: 'Detailed description',
        category: 'Crypto',
        status: 'OPEN',
        outcomes: ['Yes', 'No'],
        current_price: 0.65,
        volume: 10000,
      };

      const mockGet = vi.fn().mockResolvedValue(mockMarket);
      vi.mocked(await import('./client')).get = mockGet;

      const { fetchMarket } = await import('./markets');
      const result = await fetchMarket('market-1');

      expect(mockGet).toHaveBeenCalledWith('/api/markets/market-1');
      expect(result.condition_id).toBe('market-1');
      expect(result.question).toBe('Will Bitcoin reach $100k?');
    });
  });

  describe('marketsApi', () => {
    it('should export all API methods', async () => {
      const { marketsApi } = await import('./markets');

      expect(marketsApi.getList).toBeDefined();
      expect(marketsApi.getById).toBeDefined();
    });
  });
});
