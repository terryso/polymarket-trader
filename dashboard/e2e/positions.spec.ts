/**
 * E2E Tests for Positions Page
 *
 * Tests critical user journeys for the positions page.
 *
 * Story 7.6: 前端 API 集成
 */

import { test, expect } from '@playwright/test';

test.describe('Positions Page', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the API response - match full URL
    // API returns data wrapped in { success: true, data: [...] }
    await page.route('http://localhost:8000/api/positions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 1,
              market_id: 'market-1',
              outcome: 'YES',
              shares: 100,
              avg_price: 0.55,
              current_value: 65,
              pnl: 10,
              status: 'open',
              opened_at: '2026-02-01T10:00:00Z',
            },
            {
              id: 2,
              market_id: 'market-2',
              outcome: 'NO',
              shares: 50,
              avg_price: 0.70,
              current_value: 30,
              pnl: -5,
              status: 'open',
              opened_at: '2026-02-02T10:00:00Z',
            },
          ],
        }),
      });
    });
  });

  test('should display positions page with data', async ({ page }) => {
    await page.goto('/positions');

    // Check page title
    await expect(page.getByRole('heading', { name: '持仓' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('当前持有头寸')).toBeVisible();
  });

  test('should display total value stat card', async ({ page }) => {
    await page.goto('/positions');

    // Wait for data to load
    await expect(page.getByTestId('stat-total-value')).toBeVisible({ timeout: 10000 });

    // Check value (65 + 30 = 95)
    await expect(page.getByTestId('stat-total-value-value')).toContainText('$95.00');
  });

  test('should display total PnL stat card', async ({ page }) => {
    await page.goto('/positions');

    // Wait for data to load
    await expect(page.getByTestId('stat-total-pnl')).toBeVisible({ timeout: 10000 });

    // Check value (10 + (-5) = 5)
    await expect(page.getByTestId('stat-total-pnl-value')).toContainText('+$5.00');
  });

  test('should display positions table', async ({ page }) => {
    await page.goto('/positions');

    // Wait for table to load
    await expect(page.getByTestId('positions-table')).toBeVisible({ timeout: 10000 });

    // Check table headers
    await expect(page.getByRole('columnheader', { name: '市场 ID' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: '方向' })).toBeVisible();
  });

  test('should display position data in table', async ({ page }) => {
    await page.goto('/positions');

    // Wait for table to load
    await expect(page.getByTestId('positions-table')).toBeVisible({ timeout: 10000 });

    // Check first position data
    await expect(page.getByRole('cell', { name: 'market-1' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'YES' })).toBeVisible();
  });

  test('should show empty state when no positions', async ({ page }) => {
    // Override to return empty array
    await page.route('http://localhost:8000/api/positions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [],
        }),
      });
    });

    await page.goto('/positions');

    // Should show empty state
    await expect(page.getByTestId('empty-state')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('暂无持仓数据')).toBeVisible();
  });

  test('should handle API error gracefully', async ({ page }) => {
    // Override to return an error
    await page.route('http://localhost:8000/api/positions', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' }),
      });
    });

    await page.goto('/positions');

    // Should show error alert
    await expect(page.getByTestId('error-alert')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/无法加载数据/)).toBeVisible();
  });
});
