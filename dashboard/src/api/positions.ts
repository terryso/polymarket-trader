/**
 * Positions API module.
 *
 * Provides functions to fetch position data including list and detail endpoints.
 *
 * Story 7.6: 前端 API 集成
 * Story 5.7: 同步实际持仓 (已重构为缓存模式)
 * Story 10.6: 手动退出持仓
 */

import { get, post } from './client';
import type { PositionListItem, PositionListResponse, PositionResponse, ManualExitResponse } from './types';

/**
 * Get list of open positions.
 */
export async function fetchPositions(): Promise<PositionListItem[]> {
  const response = await get<PositionListResponse>('/api/positions');
  return response.positions;
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
 * Manually exit a position.
 *
 * Story 10.6: Dashboard 退出策略管理
 *
 * @param positionId - Position ID to exit
 */
export async function exitPosition(positionId: number): Promise<ManualExitResponse> {
  return post<ManualExitResponse>(`/api/positions/${positionId}/exit`);
}

/**
 * Positions API object with all methods.
 */
export const positionsApi = {
  getList: fetchPositions,
  getById: fetchPosition,
  exit: exitPosition,
};
