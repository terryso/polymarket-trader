/**
 * Settings API module.
 *
 * Provides functions to manage exit strategy settings.
 *
 * Story 10.6: Dashboard 退出策略管理
 */

import { get, put } from './client';
import type { ExitStrategyConfig, ExitStrategyConfigUpdate } from './types';

/**
 * Get exit strategy configuration.
 */
export async function fetchExitStrategyConfig(): Promise<ExitStrategyConfig> {
  return get<ExitStrategyConfig>('/api/settings/exit-strategy');
}

/**
 * Update exit strategy configuration.
 *
 * @param config - Configuration fields to update
 */
export async function updateExitStrategyConfig(
  config: ExitStrategyConfigUpdate
): Promise<ExitStrategyConfig> {
  return put<ExitStrategyConfig, ExitStrategyConfigUpdate>(
    '/api/settings/exit-strategy',
    config
  );
}

/**
 * Settings API object with all methods.
 */
export const settingsApi = {
  getExitStrategy: fetchExitStrategyConfig,
  updateExitStrategy: updateExitStrategyConfig,
};
