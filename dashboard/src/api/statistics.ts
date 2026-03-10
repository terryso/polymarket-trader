/**
 * Statistics API module.
 *
 * Provides functions to fetch system overview, daily statistics,
 * performance data, system status, and settings.
 *
 * Story 7.6: 前端 API 集成
 */

import { get, getPaginated, post } from './client';
import type {
  OverviewStats,
  DailyStatsItem,
  PerformanceData,
  SystemStatus,
  SanitizedSettings,
} from './types';

/**
 * Get system overview statistics.
 * Aggregates data from multiple sources for dashboard overview.
 */
export async function fetchOverview(): Promise<OverviewStats> {
  return get<OverviewStats>('/api/statistics/overview');
}

/**
 * Get system running status for monitoring.
 * Returns real-time system status including trading state and capital.
 */
export async function fetchSystemStatus(): Promise<SystemStatus> {
  return get<SystemStatus>('/api/statistics/status');
}

/**
 * Get sanitized system settings.
 * Returns configuration values with sensitive data masked.
 */
export async function fetchSettings(): Promise<SanitizedSettings> {
  return get<SanitizedSettings>('/api/statistics/settings');
}

/**
 * Get daily statistics with pagination.
 *
 * @param page - Page number (1-based)
 * @param perPage - Items per page
 */
export async function fetchDailyStats(
  page: number = 1,
  perPage: number = 20
): Promise<{ items: DailyStatsItem[]; total: number }> {
  const response = await getPaginated<DailyStatsItem>('/api/statistics/daily', {
    params: { page, per_page: perPage },
  });
  return {
    items: response.data,
    total: response.meta.total,
  };
}

/**
 * Get performance data for charts.
 *
 * @param days - Number of days to include (default: 30)
 */
export async function fetchPerformance(days: number = 30): Promise<PerformanceData> {
  return get<PerformanceData>('/api/statistics/performance', {
    params: { days },
  });
}

/**
 * Update trading state.
 *
 * @param tradingEnabled - Enable/disable trading (optional)
 * @param dailyPnl - Set daily PnL value (optional)
 */
export async function updateTradingState(
  tradingEnabled?: boolean,
  dailyPnl?: number
): Promise<{ trading_enabled: boolean; daily_pnl: number; current_capital: number; message: string }> {
  const params = new URLSearchParams();
  if (tradingEnabled !== undefined) params.append('trading_enabled', String(tradingEnabled));
  if (dailyPnl !== undefined) params.append('daily_pnl', String(dailyPnl));

  return post<{ trading_enabled: boolean; daily_pnl: number; current_capital: number; message: string }>(
    `/api/statistics/trading-state?${params.toString()}`
  );
}

/**
 * Statistics API object with all methods.
 */
export const statisticsApi = {
  getOverview: fetchOverview,
  getStatus: fetchSystemStatus,
  getSettings: fetchSettings,
  getDaily: fetchDailyStats,
  getPerformance: fetchPerformance,
  updateTradingState,
};
