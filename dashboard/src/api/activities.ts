/**
 * Activities API module.
 *
 * Provides functions to fetch recent activities including trades, predictions,
 * and system events for dashboard display.
 *
 * Story 7.7: 最近活动 API 与前端集成
 */

import { get } from './client';

// ============================================================================
// Activity Types
// ============================================================================

/**
 * Activity type enumeration.
 */
export type ActivityType = 'trade' | 'prediction' | 'system';

/**
 * Single activity item for dashboard display.
 */
export interface ActivityItem {
  id: string;
  type: ActivityType;
  description: string;
  time: string;
  amount: number | null;
  timestamp: string | null;
}

/**
 * Activity list response from API.
 */
export interface ActivityListResponse {
  items: ActivityItem[];
  total: number;
}

/**
 * Activity query parameters.
 */
export interface ActivityQueryParams {
  limit?: number;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get recent activities.
 *
 * Fetches recent trades, predictions, and system events,
 * merged and sorted by timestamp.
 *
 * @param params - Query parameters
 * @returns Promise<ActivityListResponse>
 *
 * @example
 * const activities = await fetchActivities({ limit: 10 });
 * console.log(activities.items); // Array of ActivityItem
 */
export async function fetchActivities(
  params: ActivityQueryParams = {}
): Promise<ActivityListResponse> {
  const queryParams = new URLSearchParams();
  if (params.limit !== undefined) {
    queryParams.set('limit', String(params.limit));
  }

  const url = `/api/activities${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  return get<ActivityListResponse>(url);
}

/**
 * Activities API object with all methods.
 */
export const activitiesApi = {
  getList: fetchActivities,
};
