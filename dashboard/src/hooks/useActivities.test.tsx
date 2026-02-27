/**
 * React Query hooks tests for activities.
 *
 * Story 7.7: 最近活动 API 与前端集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock the API functions
vi.mock('../api/activities', () => ({
  fetchActivities: vi.fn(),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
};

describe('useActivities hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useActivities', () => {
    it('should fetch and return activities data', async () => {
      const mockActivities = {
        items: [
          {
            id: '1',
            type: 'trade' as const,
            description: 'Bought YES for $10',
            time: '2 min ago',
            amount: 10,
            timestamp: '2024-01-15T10:00:00Z',
          },
          {
            id: '2',
            type: 'prediction' as const,
            description: 'New prediction made',
            time: '5 min ago',
            amount: null,
            timestamp: '2024-01-15T09:55:00Z',
          },
        ],
        total: 2,
      };

      vi.mocked(await import('../api/activities')).fetchActivities = vi
        .fn()
        .mockResolvedValue(mockActivities);

      const { useActivities } = await import('./useActivities');
      const { result } = renderHook(() => useActivities(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockActivities);
      expect(result.current.data?.items).toHaveLength(2);
      expect(result.current.data?.total).toBe(2);
    });

    it('should pass query params to fetchActivities', async () => {
      const mockActivities = {
        items: [],
        total: 0,
      };

      const mockFetch = vi.fn().mockResolvedValue(mockActivities);
      vi.mocked(await import('../api/activities')).fetchActivities = mockFetch;

      const { useActivities } = await import('./useActivities');
      renderHook(() => useActivities({ limit: 5 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(mockFetch).toHaveBeenCalledWith({ limit: 5 }));
    });

    it('should handle empty activities list', async () => {
      const mockActivities = {
        items: [],
        total: 0,
      };

      vi.mocked(await import('../api/activities')).fetchActivities = vi
        .fn()
        .mockResolvedValue(mockActivities);

      const { useActivities } = await import('./useActivities');
      const { result } = renderHook(() => useActivities(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.items).toEqual([]);
      expect(result.current.data?.total).toBe(0);
    });

    it('should handle error state', async () => {
      vi.mocked(await import('../api/activities')).fetchActivities = vi
        .fn()
        .mockRejectedValue(new Error('Network error'));

      const { useActivities } = await import('./useActivities');
      const { result } = renderHook(() => useActivities(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeInstanceOf(Error);
    });
  });
});

describe('activitiesKeys', () => {
  it('should generate correct query keys', async () => {
    const { activitiesKeys } = await import('./useActivities');

    expect(activitiesKeys.all).toEqual(['activities']);
    expect(activitiesKeys.list()).toEqual(['activities', 'list', undefined]);
    expect(activitiesKeys.list({ limit: 10 })).toEqual([
      'activities',
      'list',
      { limit: 10 },
    ]);
  });

  it('should generate unique keys for different params', async () => {
    const { activitiesKeys } = await import('./useActivities');

    const key1 = activitiesKeys.list({ limit: 5 });
    const key2 = activitiesKeys.list({ limit: 10 });
    const key3 = activitiesKeys.list();

    expect(key1).not.toEqual(key2);
    expect(key1).not.toEqual(key3);
    expect(key2).not.toEqual(key3);
  });
});
