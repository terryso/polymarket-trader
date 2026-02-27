/**
 * Settings page tests.
 *
 * Tests for the Settings page component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock the hooks
vi.mock('@/hooks/useStatistics', () => ({
  useSettings: vi.fn(),
  useSystemStatus: vi.fn(),
  statisticsKeys: {
    status: () => ['statistics', 'status'],
  },
}));

// Mock the API
vi.mock('@/api/statistics', () => ({
  enableTrading: vi.fn(),
  disableTrading: vi.fn(),
}));

// Mock DashboardLayout
vi.mock('@/components/layout/DashboardLayout', () => ({
  DashboardLayout: ({ children }: { children: ReactNode }) => (
    <div data-testid="dashboard-layout">{children}</div>
  ),
}));

// Mock ExitStrategySettings
vi.mock('@/components/settings/ExitStrategySettings', () => ({
  ExitStrategySettings: () => (
    <div data-testid="exit-strategy-settings">Exit Strategy Settings</div>
  ),
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

describe('Settings Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading skeleton while fetching', async () => {
      vi.mocked(await import('@/hooks/useStatistics')).useSettings = vi
        .fn()
        .mockReturnValue({ isLoading: true, data: undefined });
      vi.mocked(await import('@/hooks/useStatistics')).useSystemStatus = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: undefined });

      const { default: Settings } = await import('./Settings');
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByTestId('dashboard-layout')).toBeInTheDocument();
      const skeletons = document.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe('Error State', () => {
    it('should show error alert when fetching fails', async () => {
      vi.mocked(await import('@/hooks/useStatistics')).useSettings = vi
        .fn()
        .mockReturnValue({
          isLoading: false,
          error: new Error('Failed to load settings'),
          data: undefined,
        });
      vi.mocked(await import('@/hooks/useStatistics')).useSystemStatus = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: undefined });

      const { default: Settings } = await import('./Settings');
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText(/无法加载数据/)).toBeInTheDocument();
      expect(screen.getByText(/Failed to load settings/)).toBeInTheDocument();
    });
  });

  describe('Success State', () => {
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
      llm_api_key: 'sk-****',
      polymarket_pk: '[REDACTED]',
      proxy_wallet: '0x1234...5678',
    };

    const mockSystemStatus = {
      trading_enabled: true,
      mode: 'PAPER',
      current_capital: 200,
      daily_pnl: 5.5,
      open_positions: 2,
      consecutive_losses: 0,
      reduced_mode: false,
      last_market_fetch: null,
      uptime_hours: 2.5,
      wallet_balance: null,
      wallet_balance_error: null,
    };

    it('should render settings sections with data', async () => {
      vi.mocked(await import('@/hooks/useStatistics')).useSettings = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: mockSettings, error: null });
      vi.mocked(await import('@/hooks/useStatistics')).useSystemStatus = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: mockSystemStatus });

      const { default: Settings } = await import('./Settings');
      render(<Settings />, { wrapper: createWrapper() });

      // Check title
      expect(screen.getByText('设置')).toBeInTheDocument();

      // Check risk control section
      expect(screen.getByText('风险控制')).toBeInTheDocument();
      expect(screen.getByText('$200')).toBeInTheDocument(); // initial_capital

      // Check API config section
      expect(screen.getByText('API 配置')).toBeInTheDocument();
      expect(screen.getByText('PAPER')).toBeInTheDocument(); // trading_mode
    });

    it('should show ExitStrategySettings component', async () => {
      vi.mocked(await import('@/hooks/useStatistics')).useSettings = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: mockSettings, error: null });
      vi.mocked(await import('@/hooks/useStatistics')).useSystemStatus = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: mockSystemStatus });

      const { default: Settings } = await import('./Settings');
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByTestId('exit-strategy-settings')).toBeInTheDocument();
    });

    it('should display trading control with enabled state', async () => {
      vi.mocked(await import('@/hooks/useStatistics')).useSettings = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: mockSettings, error: null });
      vi.mocked(await import('@/hooks/useStatistics')).useSystemStatus = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: mockSystemStatus });

      const { default: Settings } = await import('./Settings');
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText('自动交易')).toBeInTheDocument();
      expect(screen.getByText('交易已启用')).toBeInTheDocument();
    });

    it('should display trading control with disabled state', async () => {
      vi.mocked(await import('@/hooks/useStatistics')).useSettings = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: mockSettings, error: null });
      vi.mocked(await import('@/hooks/useStatistics')).useSystemStatus = vi
        .fn()
        .mockReturnValue({
          isLoading: false,
          data: { ...mockSystemStatus, trading_enabled: false },
        });

      const { default: Settings } = await import('./Settings');
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText('交易已暂停')).toBeInTheDocument();
    });

    it('should call enableTrading when clicking enable button', async () => {
      const mockEnableTrading = vi.fn().mockResolvedValue({ message: 'Trading enabled' });

      vi.mocked(await import('@/hooks/useStatistics')).useSettings = vi
        .fn()
        .mockReturnValue({ isLoading: false, data: mockSettings, error: null });
      vi.mocked(await import('@/hooks/useStatistics')).useSystemStatus = vi
        .fn()
        .mockReturnValue({
          isLoading: false,
          data: { ...mockSystemStatus, trading_enabled: false },
        });
      vi.mocked(await import('@/api/statistics')).enableTrading = mockEnableTrading;

      const { default: Settings } = await import('./Settings');
      render(<Settings />, { wrapper: createWrapper() });

      const enableButton = screen.getByRole('button', { name: /启用/i });
      fireEvent.click(enableButton);

      await waitFor(() => {
        expect(mockEnableTrading).toHaveBeenCalled();
      });
    });
  });
});
