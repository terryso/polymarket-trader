/**
 * Settings API tests.
 *
 * Tests for the settings API functions.
 *
 * Story 10.6: Dashboard 退出策略管理
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the client module
vi.mock('./client', () => ({
  get: vi.fn(),
  put: vi.fn(),
}));

describe('Settings API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchExitStrategyConfig', () => {
    it('should call the correct endpoint', async () => {
      const mockConfig = {
        take_profit_enabled: true,
        take_profit_pct: 0.8,
        stop_loss_enabled: true,
        stop_loss_pct: 0.3,
        time_exit_enabled: true,
        time_exit_hours: 24,
        signal_exit_enabled: true,
        exit_check_interval_minutes: 5,
      };

      const mockGet = vi.fn().mockResolvedValue(mockConfig);
      vi.mocked(await import('./client')).get = mockGet;

      const { fetchExitStrategyConfig } = await import('./settings');
      const result = await fetchExitStrategyConfig();

      expect(mockGet).toHaveBeenCalledWith('/api/settings/exit-strategy');
      expect(result.take_profit_enabled).toBe(true);
      expect(result.take_profit_pct).toBe(0.8);
    });

    it('should return config with all required fields', async () => {
      const mockConfig = {
        take_profit_enabled: false,
        take_profit_pct: 0.75,
        stop_loss_enabled: false,
        stop_loss_pct: 0.25,
        time_exit_enabled: false,
        time_exit_hours: 48,
        signal_exit_enabled: false,
        exit_check_interval_minutes: 10,
      };

      const mockGet = vi.fn().mockResolvedValue(mockConfig);
      vi.mocked(await import('./client')).get = mockGet;

      const { fetchExitStrategyConfig } = await import('./settings');
      const result = await fetchExitStrategyConfig();

      expect(result).toHaveProperty('take_profit_enabled');
      expect(result).toHaveProperty('take_profit_pct');
      expect(result).toHaveProperty('stop_loss_enabled');
      expect(result).toHaveProperty('stop_loss_pct');
      expect(result).toHaveProperty('time_exit_enabled');
      expect(result).toHaveProperty('time_exit_hours');
      expect(result).toHaveProperty('signal_exit_enabled');
      expect(result).toHaveProperty('exit_check_interval_minutes');
    });
  });

  describe('updateExitStrategyConfig', () => {
    it('should call PUT with correct endpoint and data', async () => {
      const mockUpdatedConfig = {
        take_profit_enabled: true,
        take_profit_pct: 0.9,
        stop_loss_enabled: true,
        stop_loss_pct: 0.2,
        time_exit_enabled: true,
        time_exit_hours: 12,
        signal_exit_enabled: true,
        exit_check_interval_minutes: 5,
      };

      const mockPut = vi.fn().mockResolvedValue(mockUpdatedConfig);
      vi.mocked(await import('./client')).put = mockPut;

      const { updateExitStrategyConfig } = await import('./settings');
      const updateData = { take_profit_pct: 0.9 };
      const result = await updateExitStrategyConfig(updateData);

      expect(mockPut).toHaveBeenCalledWith(
        '/api/settings/exit-strategy',
        updateData
      );
      expect(result.take_profit_pct).toBe(0.9);
    });

    it('should support partial updates', async () => {
      const mockUpdatedConfig = {
        take_profit_enabled: false,
        take_profit_pct: 0.8,
        stop_loss_enabled: true,
        stop_loss_pct: 0.3,
        time_exit_enabled: true,
        time_exit_hours: 24,
        signal_exit_enabled: true,
        exit_check_interval_minutes: 5,
      };

      const mockPut = vi.fn().mockResolvedValue(mockUpdatedConfig);
      vi.mocked(await import('./client')).put = mockPut;

      const { updateExitStrategyConfig } = await import('./settings');
      const result = await updateExitStrategyConfig({ take_profit_enabled: false });

      expect(mockPut).toHaveBeenCalledWith(
        '/api/settings/exit-strategy',
        { take_profit_enabled: false }
      );
      expect(result.take_profit_enabled).toBe(false);
    });
  });

  describe('settingsApi', () => {
    it('should export settingsApi object with correct methods', async () => {
      const mockConfig = {
        take_profit_enabled: true,
        take_profit_pct: 0.8,
        stop_loss_enabled: true,
        stop_loss_pct: 0.3,
        time_exit_enabled: true,
        time_exit_hours: 24,
        signal_exit_enabled: true,
        exit_check_interval_minutes: 5,
      };

      const mockGet = vi.fn().mockResolvedValue(mockConfig);
      const mockPut = vi.fn().mockResolvedValue(mockConfig);
      vi.mocked(await import('./client')).get = mockGet;
      vi.mocked(await import('./client')).put = mockPut;

      const { settingsApi } = await import('./settings');

      // Test getExitStrategy
      await settingsApi.getExitStrategy();
      expect(mockGet).toHaveBeenCalledWith('/api/settings/exit-strategy');

      // Test updateExitStrategy
      await settingsApi.updateExitStrategy({ take_profit_pct: 0.9 });
      expect(mockPut).toHaveBeenCalledWith('/api/settings/exit-strategy', {
        take_profit_pct: 0.9,
      });
    });
  });
});
