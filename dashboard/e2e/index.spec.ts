/**
 * E2E Tests for Index (Dashboard) Page
 *
 * Tests critical user journeys for the main dashboard page.
 *
 * Story 7.6: 前端 API 集成
 */

import { test, expect } from '@playwright/test';

test.describe('Dashboard Index Page', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the API responses - match full URL including host
    // API returns data wrapped in { success: true, data: {...} }
    await page.route('http://localhost:8000/api/statistics/overview', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            current_capital: 250.50,
            initial_capital: 200,
            total_pnl: 50.50,
            total_pnl_pct: 0.2525,
            win_rate: 0.75,
            total_trades: 10,
            winning_trades: 7,
            losing_trades: 3,
            open_positions: 2,
            trading_enabled: true,
            mode: 'PAPER',
          },
        }),
      });
    });

    await page.route('http://localhost:8000/api/statistics/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            trading_enabled: true,
            mode: 'PAPER',
            current_capital: 250.50,
            daily_pnl: 15.50,
            open_positions: 2,
            consecutive_losses: 0,
            reduced_mode: false,
            last_market_fetch: '2026-02-17T10:00:00Z',
            uptime_hours: 24.5,
          },
        }),
      });
    });
  });

  test('should display dashboard page with statistics', async ({ page }) => {
    await page.goto('/');

    // Wait for loading to complete and data to appear
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('系统运行概览')).toBeVisible();
  });

  test('should display total capital stat card', async ({ page }) => {
    await page.goto('/');

    // Wait for data to load
    await expect(page.getByTestId('stat-total-capital')).toBeVisible({ timeout: 10000 });

    // Check value
    await expect(page.getByTestId('stat-total-capital-value')).toContainText('$250.50');
  });

  test('should display today PnL stat card', async ({ page }) => {
    await page.goto('/');

    // Wait for data to load
    await expect(page.getByTestId('stat-today-pnl')).toBeVisible({ timeout: 10000 });

    // Check value
    await expect(page.getByTestId('stat-today-pnl-value')).toContainText('+$15.50');
  });

  test('should display win rate stat card', async ({ page }) => {
    await page.goto('/');

    // Wait for data to load
    await expect(page.getByTestId('stat-win-rate')).toBeVisible({ timeout: 10000 });

    // Check value
    await expect(page.getByTestId('stat-win-rate-value')).toContainText('75.0%');
  });

  test('should display system status stat card', async ({ page }) => {
    await page.goto('/');

    // Wait for data to load
    await expect(page.getByTestId('stat-system-status')).toBeVisible({ timeout: 10000 });

    // Check value shows running status
    await expect(page.getByTestId('stat-system-status-value')).toContainText('运行中');
  });

  test('should handle API error gracefully', async ({ page }) => {
    // Override the route to return an error
    await page.route('http://localhost:8000/api/statistics/overview', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' }),
      });
    });

    await page.goto('/');

    // Should show error alert
    await expect(page.getByTestId('error-alert')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/无法加载数据/)).toBeVisible();
  });
});
