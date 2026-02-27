/**
 * Positions API tests.
 *
 * Tests for the positions API functions including list and detail endpoints.
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from './client';

// Mock the client module
vi.mock('./client', () => ({
  get: vi.fn(),
  getPaginated: vi.fn(),
}));

describe('Positions API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchPositions', () => {
    it('should call the correct endpoint', async () => {
      const mockResponse = {
        positions: [
          {
            id: 1,
            condition_id: 'market-1',
            question: 'Will Bitcoin reach $100k?',
            outcome: 'Yes',
            size: 100,
            avg_price: 0.55,
            current_price: 0.65,
            pnl: 10,
            pnl_pct: 0.1,
          },
          {
            id: 2,
            condition_id: 'market-2',
            question: 'Will Ethereum reach $5k?',
            outcome: 'No',
            size: 50,
            avg_price: 0.7,
            current_price: 0.6,
            pnl: -5,
            pnl_pct: -0.05,
          },
        ],
        cache_freshness: 'FRESH' as const,
        cache_age_seconds: 0,
      };

      vi.mocked(client.get).mockResolvedValue(mockResponse);

      const { fetchPositions } = await import('./positions');
      const result = await fetchPositions();

      expect(client.get).toHaveBeenCalledWith('/api/positions');
      expect(result).toHaveLength(2);
      expect(result[0].condition_id).toBe('market-1');
      expect(result[1].outcome).toBe('No');
    });

    it('should return empty array when no positions', async () => {
      const mockResponse = {
        positions: [],
        cache_freshness: 'FRESH' as const,
        cache_age_seconds: 0,
      };
      vi.mocked(client.get).mockResolvedValue(mockResponse);

      const { fetchPositions } = await import('./positions');
      const result = await fetchPositions();

      expect(result).toHaveLength(0);
    });
  });

  describe('fetchPosition', () => {
    it('should call the correct endpoint for position details', async () => {
      const mockPosition = {
        id: 1,
        condition_id: 'market-1',
        question: 'Will Bitcoin reach $100k?',
        description: 'Detailed description',
        outcome: 'Yes',
        size: 100,
        avg_price: 0.55,
        current_price: 0.65,
        pnl: 10,
        pnl_pct: 0.1,
        opened_at: '2026-02-01T10:00:00Z',
        trades_count: 5,
      };

      vi.mocked(client.get).mockResolvedValue(mockPosition);

      const { fetchPosition } = await import('./positions');
      const result = await fetchPosition(1);

      expect(client.get).toHaveBeenCalledWith('/api/positions/1');
      expect(result.id).toBe(1);
      expect(result.outcome).toBe('Yes');
      expect(result.trades_count).toBe(5);
    });
  });

  describe('positionsApi', () => {
    it('should export all API methods', async () => {
      const { positionsApi } = await import('./positions');

      expect(positionsApi.getList).toBeDefined();
      expect(positionsApi.getById).toBeDefined();
    });
  });
});
