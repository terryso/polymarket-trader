/**
 * API module unified exports.
 *
 * This module provides a central export point for all API functions.
 *
 * Story 7.6: 前端 API 集成
 * Story 10.6: Dashboard 退出策略管理
 */

// Client utilities
export { client, API_BASE_URL, get, getPaginated, post, put, del } from './client';
export type { ApiError, ApiResponse, ApiErrorResponse, PaginatedResponse } from './client';

// Type definitions
export * from './types';

// API modules
export { statisticsApi, fetchOverview, fetchSystemStatus, fetchSettings, fetchDailyStats, fetchPerformance } from './statistics';
export { marketsApi, fetchMarkets, fetchMarket } from './markets';
export { positionsApi, fetchPositions, fetchPosition } from './positions';
export { tradesApi, fetchTrades, fetchTrade } from './trades';
export { predictionsApi, fetchPredictions, fetchPrediction, fetchAccuracy } from './predictions';
export { activitiesApi, fetchActivities } from './activities';
export { settingsApi, fetchExitStrategyConfig, updateExitStrategyConfig } from './settings';
export type { ActivityItem, ActivityType, ActivityListResponse, ActivityQueryParams } from './activities';
