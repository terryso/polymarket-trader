/**
 * Positions API module.
 *
 * Provides functions to fetch position data including list and detail endpoints.
 *
 * Story 7.6: 前端 API 集成
 */

import { get } from './client';
import type { PositionListItem, PositionResponse } from './types';

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
 * Positions API object with all methods.
 */
export const positionsApi = {
  getList: fetchPositions,
  getById: fetchPosition,
};
