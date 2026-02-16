/**
 * Statistics API tests.
 *
 * Tests for the statistics API functions.
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the client module
vi.mock('./client', () => ({
  get: vi.fn(),
  getPaginated: vi.fn(),
}));

describe('Statistics API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchOverview', () => {
    it('should call the correct endpoint', async () => {
      const mockGet = vi.fn().mockResolvedValue({
        current_capital: 200,
        initial_capital: 100,
        total_pnl: 100,
        total_pnl_pct: 1,
        win_rate: 0.65,
        total_trades: 50,
        winning_trades: 33,
        losing_trades: 17,
        open_positions: 4,
        trading_enabled: true,
        mode: 'PAPER',
      });

      vi.mocked(await import('./client')).get = mockGet;

      const { fetchOverview } = await import('./statistics');
      const result = await fetchOverview();

      expect(mockGet).toHaveBeenCalledWith('/api/statistics/overview');
      expect(result.current_capital).toBe(200);
    });
  });

  describe('fetchSystemStatus', () => {
    it('should call the correct endpoint', async () => {
      const mockGet = vi.fn().mockResolvedValue({
        trading_enabled: true,
        mode: 'PAPER',
        current_capital: 200,
        daily_pnl: 5.5,
        open_positions: 4,
        consecutive_losses: 0,
        reduced_mode: false,
        last_market_fetch: null,
        uptime_hours: 2.5,
      });

      vi.mocked(await import('./client')).get = mockGet;

      const { fetchSystemStatus } = await import('./statistics');
      const result = await fetchSystemStatus();

      expect(mockGet).toHaveBeenCalledWith('/api/statistics/status');
      expect(result.trading_enabled).toBe(true);
    });
  });

  describe('fetchSettings', () => {
    it('should call the correct endpoint', async () => {
      const mockGet = vi.fn().mockResolvedValue({
        trading_mode: 'PAPER',
        initial_capital: 200,
        trade_unit: 10,
        max_single_ratio: 0.2,
        min_confidence: 0.75,
        min_edge: 0.05,
        daily_loss_limit: 0.15,
        max_open_markets: 5,
        llm_model: 'gpt-4',
        llm_api_base: 'https://api.openai.com',
        llm_api_key: 'sk-x****',
        polymarket_pk: '[REDACTED]',
        proxy_wallet: '0x1234...5678',
      });

      vi.mocked(await import('./client')).get = mockGet;

      const { fetchSettings } = await import('./statistics');
      const result = await fetchSettings();

      expect(mockGet).toHaveBeenCalledWith('/api/statistics/settings');
      expect(result.trading_mode).toBe('PAPER');
    });
  });
});
