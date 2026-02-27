/**
 * Exit Strategy Settings component tests.
 *
 * Tests for the ExitStrategySettings component.
 *
 * Story 10.6: Dashboard 退出策略管理
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock the API
vi.mock('@/api/settings', () => ({
  settingsApi: {
    getExitStrategy: vi.fn(),
    updateExitStrategy: vi.fn(),
  },
}));

// Mock useToast
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
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

const mockConfig = {
  take_profit_enabled: true,
  take_profit_pct: 0.8,
  stop_loss_enabled: true,
  stop_loss_pct: -0.3,
  time_exit_enabled: true,
  time_exit_hours: 24,
  signal_exit_enabled: true,
  exit_check_interval_minutes: 5,
};

describe('ExitStrategySettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading spinner while fetching config', async () => {
    vi.mocked(await import('@/api/settings')).settingsApi.getExitStrategy = vi
        .fn()
        .mockImplementation(() => new Promise(() => {})); // Never resolves

      const { ExitStrategySettings } = await import('./ExitStrategySettings');
      render(<ExitStrategySettings />, { wrapper: createWrapper() });

      expect(screen.getByText('加载中...')).toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    it('should render the exit strategy card', async () => {
      vi.mocked(await import('@/api/settings')).settingsApi.getExitStrategy = vi
        .fn()
        .mockResolvedValue(mockConfig);

      const { ExitStrategySettings } = await import('./ExitStrategySettings');
      render(<ExitStrategySettings />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('退出策略')).toBeInTheDocument();
      });
    });

    it('should display current config values', async () => {
      vi.mocked(await import('@/api/settings')).settingsApi.getExitStrategy = vi
        .fn()
        .mockResolvedValue(mockConfig);

      const { ExitStrategySettings } = await import('./ExitStrategySettings');
      render(<ExitStrategySettings />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByDisplayValue('80')).toBeInTheDocument(); // take_profit_pct * 100
      });
      expect(screen.getByDisplayValue('30')).toBeInTheDocument(); // stop_loss_pct * 100 (absolute)
      expect(screen.getByDisplayValue('24')).toBeInTheDocument(); // time_exit_hours
    });

    it('should have save button present', async () => {
      vi.mocked(await import('@/api/settings')).settingsApi.getExitStrategy = vi
        .fn()
        .mockResolvedValue(mockConfig);

      const { ExitStrategySettings } = await import('./ExitStrategySettings');
      render(<ExitStrategySettings />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /保存设置/i })).toBeInTheDocument();
      });
    });

    it('should display strategy descriptions', async () => {
      vi.mocked(await import('@/api/settings')).settingsApi.getExitStrategy = vi
        .fn()
        .mockResolvedValue(mockConfig);

      const { ExitStrategySettings } = await import('./ExitStrategySettings');
      render(<ExitStrategySettings />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('配置自动和手动退出策略参数')).toBeInTheDocument();
      });
    });
  });
});
