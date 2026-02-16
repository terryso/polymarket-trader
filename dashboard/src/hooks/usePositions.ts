/**
 * React Query hooks for positions API.
 *
 * Story 7.6: 前端 API 集成
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { fetchPositions, fetchPosition } from '../api/positions';
import type { PositionListItem, PositionResponse } from '../api/types';

// Query keys for cache management
export const positionsKeys = {
  all: ['positions'] as const,
  list: () => [...positionsKeys.all, 'list'] as const,
  detail: (id: number) => [...positionsKeys.all, 'detail', id] as const,
};

/**
 * Hook for fetching list of open positions.
 * Refreshes every 30 seconds.
 */
export function usePositions(): UseQueryResult<PositionListItem[], Error> {
  return useQuery({
    queryKey: positionsKeys.list(),
    queryFn: fetchPositions,
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 15000,
  });
}

/**
 * Hook for fetching position details by ID.
 *
 * @param positionId - Position unique identifier
 */
export function usePosition(positionId: number): UseQueryResult<PositionResponse, Error> {
  return useQuery({
    queryKey: positionsKeys.detail(positionId),
    queryFn: () => fetchPosition(positionId),
    enabled: !!positionId, // Only fetch if positionId is provided
    staleTime: 30000,
  });
}
