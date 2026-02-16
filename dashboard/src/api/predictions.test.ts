/**
 * Predictions API tests.
 *
 * Tests for the predictions API functions including list, detail, and accuracy endpoints.
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the client module
vi.mock('./client', () => ({
  get: vi.fn(),
  getPaginated: vi.fn(),
}));

describe('Predictions API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchPredictions', () => {
    it('should call the correct endpoint with default params', async () => {
      const mockGetPaginated = vi.fn().mockResolvedValue({
        success: true,
        data: [
          {
            id: 1,
            condition_id: 'market-1',
            question: 'Will Bitcoin reach $100k?',
            predicted_outcome: 'Yes',
            confidence: 0.85,
            reasoning: 'Strong upward trend',
            created_at: '2026-02-01T10:00:00Z',
            validated: true,
            actual_outcome: 'Yes',
          },
        ],
        meta: { total: 1, page: 1, per_page: 20 },
      });

      vi.mocked(await import('./client')).getPaginated = mockGetPaginated;

      const { fetchPredictions } = await import('./predictions');
      const result = await fetchPredictions();

      expect(mockGetPaginated).toHaveBeenCalledWith('/api/predictions', {
        params: {
          page: 1,
          per_page: 20,
          validated: undefined,
        },
      });
      expect(result.items).toHaveLength(1);
      expect(result.total).toBe(1);
      expect(result.items[0].confidence).toBe(0.85);
    });

    it('should filter by validated status', async () => {
      const mockGetPaginated = vi.fn().mockResolvedValue({
        success: true,
        data: [],
        meta: { total: 0, page: 1, per_page: 20 },
      });

      vi.mocked(await import('./client')).getPaginated = mockGetPaginated;

      const { fetchPredictions } = await import('./predictions');
      await fetchPredictions({ page: 1, per_page: 20, validated: true });

      expect(mockGetPaginated).toHaveBeenCalledWith('/api/predictions', {
        params: {
          page: 1,
          per_page: 20,
          validated: true,
        },
      });
    });
  });

  describe('fetchPrediction', () => {
    it('should call the correct endpoint for prediction details', async () => {
      const mockPrediction = {
        id: 1,
        condition_id: 'market-1',
        question: 'Will Bitcoin reach $100k?',
        description: 'Detailed description',
        predicted_outcome: 'Yes',
        confidence: 0.85,
        reasoning: 'Strong upward trend based on technical analysis',
        created_at: '2026-02-01T10:00:00Z',
        validated: true,
        actual_outcome: 'Yes',
        edge: 0.15,
        trade_id: 1,
      };

      const mockGet = vi.fn().mockResolvedValue(mockPrediction);
      vi.mocked(await import('./client')).get = mockGet;

      const { fetchPrediction } = await import('./predictions');
      const result = await fetchPrediction(1);

      expect(mockGet).toHaveBeenCalledWith('/api/predictions/1');
      expect(result.id).toBe(1);
      expect(result.predicted_outcome).toBe('Yes');
      expect(result.edge).toBe(0.15);
    });
  });

  describe('fetchAccuracy', () => {
    it('should call the correct endpoint for accuracy stats', async () => {
      const mockAccuracy = {
        total_predictions: 100,
        validated_predictions: 80,
        correct_predictions: 65,
        accuracy_rate: 0.8125,
        avg_confidence: 0.78,
        by_category: {
          Crypto: { total: 50, correct: 40, accuracy: 0.8 },
          Politics: { total: 30, correct: 25, accuracy: 0.833 },
        },
      };

      const mockGet = vi.fn().mockResolvedValue(mockAccuracy);
      vi.mocked(await import('./client')).get = mockGet;

      const { fetchAccuracy } = await import('./predictions');
      const result = await fetchAccuracy();

      expect(mockGet).toHaveBeenCalledWith('/api/predictions/accuracy');
      expect(result.total_predictions).toBe(100);
      expect(result.accuracy_rate).toBe(0.8125);
    });
  });

  describe('predictionsApi', () => {
    it('should export all API methods', async () => {
      const { predictionsApi } = await import('./predictions');

      expect(predictionsApi.getList).toBeDefined();
      expect(predictionsApi.getById).toBeDefined();
      expect(predictionsApi.getAccuracy).toBeDefined();
    });
  });
});
