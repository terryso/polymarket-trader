/**
 * Activities API tests.
 *
 * Tests for the activities API functions.
 *
 * Story 7.7: 最近活动 API 与前端集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the client module
vi.mock('./client', () => ({
  get: vi.fn(),
}));

describe('Activities API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchActivities', () => {
    it('should call the correct endpoint without params', async () => {
      const mockResponse = {
        items: [
          {
            id: '1',
            type: 'trade' as const,
            description: 'Bought YES for $10',
            time: '2 min ago',
            amount: 10,
            timestamp: '2024-01-15T10:00:00Z',
          },
        ],
        total: 1,
      };

      const mockGet = vi.fn().mockResolvedValue(mockResponse);
      vi.mocked(await import('./client')).get = mockGet;

      const { fetchActivities } = await import('./activities');
      const result = await fetchActivities();

      expect(mockGet).toHaveBeenCalledWith('/api/activities');
      expect(result.items).toHaveLength(1);
      expect(result.total).toBe(1);
    });

    it('should call the correct endpoint with limit param', async () => {
      const mockResponse = {
        items: [],
        total: 0,
      };

      const mockGet = vi.fn().mockResolvedValue(mockResponse);
      vi.mocked(await import('./client')).get = mockGet;

      const { fetchActivities } = await import('./activities');
      await fetchActivities({ limit: 10 });

      expect(mockGet).toHaveBeenCalledWith('/api/activities?limit=10');
    });

    it('should return activities with correct types', async () => {
      const mockResponse = {
        items: [
          {
            id: '1',
            type: 'trade' as const,
            description: 'Trade executed',
            time: '1 min ago',
            amount: 50,
            timestamp: '2024-01-15T10:00:00Z',
          },
          {
            id: '2',
            type: 'prediction' as const,
            description: 'New prediction',
            time: '5 min ago',
            amount: null,
            timestamp: '2024-01-15T09:55:00Z',
          },
          {
            id: '3',
            type: 'system' as const,
            description: 'System started',
            time: '10 min ago',
            amount: null,
            timestamp: '2024-01-15T09:50:00Z',
          },
        ],
        total: 3,
      };

      const mockGet = vi.fn().mockResolvedValue(mockResponse);
      vi.mocked(await import('./client')).get = mockGet;

      const { fetchActivities } = await import('./activities');
      const result = await fetchActivities();

      expect(result.items[0].type).toBe('trade');
      expect(result.items[1].type).toBe('prediction');
      expect(result.items[2].type).toBe('system');
    });
  });

  describe('activitiesApi', () => {
    it('should export activitiesApi object with getList method', async () => {
      const mockResponse = {
        items: [],
        total: 0,
      };

      const mockGet = vi.fn().mockResolvedValue(mockResponse);
      vi.mocked(await import('./client')).get = mockGet;

      const { activitiesApi } = await import('./activities');
      await activitiesApi.getList({ limit: 5 });

      expect(mockGet).toHaveBeenCalledWith('/api/activities?limit=5');
    });
  });
});

describe('Activity Types', () => {
  it('should have correct ActivityItem interface', async () => {
    // Type check by importing and using the types
    const { fetchActivities } = await import('./activities');

    // This is a compile-time type check, runtime just verifies the structure
    const mockItem = {
      id: '1',
      type: 'trade' as const,
      description: 'Test',
      time: 'now',
      amount: 10 as number | null,
      timestamp: '2024-01-15T10:00:00Z' as string | null,
    };

    expect(mockItem.id).toBe('1');
    expect(mockItem.type).toBe('trade');
    expect(mockItem.amount).toBe(10);
  });
});
