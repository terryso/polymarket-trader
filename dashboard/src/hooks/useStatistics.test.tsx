/**
 * React Query hooks tests for statistics.
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock the API functions
vi.mock('../api/statistics', () => ({
  fetchOverview: vi.fn(),
  fetchSystemStatus: vi.fn(),
  fetchSettings: vi.fn(),
  fetchDailyStats: vi.fn(),
  fetchPerformance: vi.fn(),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
};

describe('useStatistics hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useOverview', () => {
    it('should fetch and return overview data', async () => {
      const mockOverview = {
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
      };

      vi.mocked(await import('../api/statistics')).fetchOverview = vi
        .fn()
        .mockResolvedValue(mockOverview);

      const { useOverview } = await import('./useStatistics');
      const { result } = renderHook(() => useOverview(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockOverview);
    });
  });

  describe('useSystemStatus', () => {
    it('should fetch and return system status data', async () => {
      const mockStatus = {
        trading_enabled: true,
        mode: 'PAPER',
        current_capital: 200,
        daily_pnl: 5.5,
        open_positions: 4,
        consecutive_losses: 0,
        reduced_mode: false,
        last_market_fetch: null,
        uptime_hours: 2.5,
      };

      vi.mocked(await import('../api/statistics')).fetchSystemStatus = vi
        .fn()
        .mockResolvedValue(mockStatus);

      const { useSystemStatus } = await import('./useStatistics');
      const { result } = renderHook(() => useSystemStatus(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockStatus);
    });
  });

  describe('useSettings', () => {
    it('should fetch and return settings data', async () => {
      const mockSettings = {
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
      };

      vi.mocked(await import('../api/statistics')).fetchSettings = vi
        .fn()
        .mockResolvedValue(mockSettings);

      const { useSettings } = await import('./useStatistics');
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockSettings);
    });
  });
});

describe('statisticsKeys', () => {
  it('should generate correct query keys', async () => {
    const { statisticsKeys } = await import('./useStatistics');

    expect(statisticsKeys.all).toEqual(['statistics']);
    expect(statisticsKeys.overview()).toEqual(['statistics', 'overview']);
    expect(statisticsKeys.status()).toEqual(['statistics', 'status']);
    expect(statisticsKeys.settings()).toEqual(['statistics', 'settings']);
    expect(statisticsKeys.daily(1, 20)).toEqual([
      'statistics',
      'daily',
      { page: 1, perPage: 20 },
    ]);
    expect(statisticsKeys.performance(30)).toEqual([
      'statistics',
      'performance',
      { days: 30 },
    ]);
  });
});
