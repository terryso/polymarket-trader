/**
 * React Query hooks for statistics API.
 *
 * Provides hooks for fetching overview, status, and settings data
 * with automatic caching and error handling.
 *
 * Story 7.6: 前端 API 集成
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import {
  fetchOverview,
  fetchSystemStatus,
  fetchSettings,
  fetchDailyStats,
  fetchPerformance,
} from '../api/statistics';
import type {
  OverviewStats,
  SystemStatus,
  SanitizedSettings,
  DailyStatsItem,
  PerformanceData,
} from '../api/types';

// Query keys for cache management
export const statisticsKeys = {
  all: ['statistics'] as const,
  overview: () => [...statisticsKeys.all, 'overview'] as const,
  status: () => [...statisticsKeys.all, 'status'] as const,
  settings: () => [...statisticsKeys.all, 'settings'] as const,
  daily: (page?: number, perPage?: number) =>
    [...statisticsKeys.all, 'daily', { page, perPage }] as const,
  performance: (days?: number) =>
    [...statisticsKeys.all, 'performance', { days }] as const,
};

/**
 * Hook for fetching system overview statistics.
 * Refreshes every 30 seconds.
 */
export function useOverview(): UseQueryResult<OverviewStats, Error> {
  return useQuery({
    queryKey: statisticsKeys.overview(),
    queryFn: fetchOverview,
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 10000, // Consider data stale after 10 seconds
  });
}

/**
 * Hook for fetching system running status.
 * Refreshes every 10 seconds for real-time monitoring.
 */
export function useSystemStatus(): UseQueryResult<SystemStatus, Error> {
  return useQuery({
    queryKey: statisticsKeys.status(),
    queryFn: fetchSystemStatus,
    refetchInterval: 10000, // Refresh every 10 seconds for real-time status
    staleTime: 5000,
  });
}

/**
 * Hook for fetching sanitized settings.
 * Settings rarely change, so no auto-refresh.
 */
export function useSettings(): UseQueryResult<SanitizedSettings, Error> {
  return useQuery({
    queryKey: statisticsKeys.settings(),
    queryFn: fetchSettings,
    staleTime: 60000, // Settings rarely change
  });
}

/**
 * Hook for fetching daily statistics.
 *
 * @param page - Page number (1-based)
 * @param perPage - Items per page
 */
export function useDailyStats(
  page: number = 1,
  perPage: number = 20
): UseQueryResult<{ items: DailyStatsItem[]; total: number }, Error> {
  return useQuery({
    queryKey: statisticsKeys.daily(page, perPage),
    queryFn: () => fetchDailyStats(page, perPage),
    staleTime: 30000,
  });
}

/**
 * Hook for fetching performance data for charts.
 *
 * @param days - Number of days to include
 */
export function usePerformance(
  days: number = 30
): UseQueryResult<PerformanceData, Error> {
  return useQuery({
    queryKey: statisticsKeys.performance(days),
    queryFn: () => fetchPerformance(days),
    staleTime: 60000, // Performance data changes slowly
  });
}
