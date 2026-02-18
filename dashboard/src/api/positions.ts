/**
 * Positions API module.
 *
 * Provides functions to fetch position data including list and detail endpoints.
 *
 * Story 7.6: 前端 API 集成
 * Story 5.7: 同步实际持仓
 */

import { get, post } from './client';
import type { PositionListItem, PositionResponse, PositionSyncStatus, PositionSyncResult } from './types';

/**
 * Get list of open positions.
 */
export async function fetchPositions(): Promise<PositionListItem[]> {
  return get<PositionListItem[]>('/api/positions');
}

/**
 * Get position details by ID.
 *
 * @param positionId - Position unique identifier
 */
export async function fetchPosition(positionId: number): Promise<PositionResponse> {
  return get<PositionResponse>(`/api/positions/${positionId}`);
}

/**
 * Get position sync status.
 *
 * Story 5.7: 同步实际持仓
 */
export async function fetchPositionSyncStatus(): Promise<PositionSyncStatus> {
  return get<PositionSyncStatus>('/api/positions/sync/status');
}

/**
 * Sync positions from Polymarket.
 *
 * Story 5.7: 同步实际持仓
 */
export async function syncPositions(): Promise<PositionSyncResult> {
  return post<PositionSyncResult>('/api/positions/sync');
}

/**
 * Positions API object with all methods.
 */
export const positionsApi = {
  getList: fetchPositions,
  getById: fetchPosition,
  getSyncStatus: fetchPositionSyncStatus,
  sync: syncPositions,
};
