/**
 * React Query hooks for activities API.
 *
 * Story 7.7: 最近活动 API 与前端集成
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { fetchActivities } from '../api/activities';
import type { ActivityListResponse, ActivityQueryParams } from '../api/activities';

// Query keys for cache management
export const activitiesKeys = {
  all: ['activities'] as const,
  list: (params?: ActivityQueryParams) =>
    [...activitiesKeys.all, 'list', params] as const,
};

/**
 * Hook for fetching recent activities.
 * Refreshes every 30 seconds (activities change frequently).
 *
 * @param params - Query parameters for limiting results
 */
export function useActivities(
  params: ActivityQueryParams = {}
): UseQueryResult<ActivityListResponse, Error> {
  return useQuery({
    queryKey: activitiesKeys.list(params),
    queryFn: () => fetchActivities(params),
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 15000,
  });
}
