/**
 * E2E Tests for Trades Page
 *
 * Tests critical user journeys for the trades page including
 * filtering and pagination.
 *
 * Story 7.6: 前端 API 集成
 */

import { test, expect } from '@playwright/test';

test.describe('Trades Page', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the API response - match full URL (trades has query params)
    // PaginatedResponse format: { success: true, data: [...], meta: { total, page, per_page } }
    await page.route('http://localhost:8000/api/trades**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 1,
              market_id: 'market-1',
              trade_type: 'BUY_YES',
              mode: 'PAPER',
              amount: 10.0,
              price: 0.55,
              shares: 18.18,
              status: 'filled',
              created_at: '2026-02-17T10:00:00Z',
            },
            {
              id: 2,
              market_id: 'market-2',
              trade_type: 'SELL_NO',
              mode: 'PAPER',
              amount: 5.0,
              price: 0.70,
              shares: 7.14,
              status: 'filled',
              created_at: '2026-02-17T11:00:00Z',
            },
            {
              id: 3,
              market_id: 'market-3',
              trade_type: 'BUY_NO',
              mode: 'LIVE',
              amount: 20.0,
              price: 0.30,
              shares: 66.67,
              status: 'pending',
              created_at: '2026-02-17T12:00:00Z',
            },
          ],
          meta: {
            total: 3,
            page: 1,
            per_page: 20,
          },
        }),
      });
    });
  });

  test('should display trades page with data', async ({ page }) => {
    await page.goto('/trades');

    // Check page title
    await expect(page.getByRole('heading', { name: '交易历史' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('共 3 条记录')).toBeVisible();
  });

  test('should display filter buttons', async ({ page }) => {
    await page.goto('/trades');

    // Wait for data to load
    await expect(page.getByTestId('mode-filter')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('type-filter')).toBeVisible();

    // Check mode filter buttons
    await expect(page.getByTestId('mode-filter').getByRole('button', { name: '全部' })).toBeVisible();
    await expect(page.getByTestId('mode-filter').getByRole('button', { name: 'Paper' })).toBeVisible();
    await expect(page.getByTestId('mode-filter').getByRole('button', { name: 'Live' })).toBeVisible();

    // Check type filter buttons
    await expect(page.getByTestId('type-filter').getByRole('button', { name: '全部' })).toBeVisible();
    await expect(page.getByTestId('type-filter').getByRole('button', { name: '买入' })).toBeVisible();
    await expect(page.getByTestId('type-filter').getByRole('button', { name: '卖出' })).toBeVisible();
  });

  test('should display trades table', async ({ page }) => {
    await page.goto('/trades');

    // Wait for table to load
    await expect(page.getByTestId('trades-table')).toBeVisible({ timeout: 10000 });

    // Check table headers
    await expect(page.getByRole('columnheader', { name: '时间' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: '市场' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: '类型' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: '金额' })).toBeVisible();
  });

  test('should display trade data in table', async ({ page }) => {
    await page.goto('/trades');

    // Wait for table to load
    await expect(page.getByTestId('trades-table')).toBeVisible({ timeout: 10000 });

    // Check trade data
    await expect(page.getByRole('cell', { name: 'market-1' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'market-2' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'market-3' })).toBeVisible();
  });

  test('should filter by mode when clicking Paper button', async ({ page }) => {
    await page.goto('/trades');

    // Wait for data to load
    await expect(page.getByTestId('mode-filter')).toBeVisible({ timeout: 10000 });

    // Click Paper filter
    await page.getByTestId('mode-filter').getByRole('button', { name: 'Paper' }).click();

    // Verify filter is applied (button should have active styling)
    const paperButton = page.getByTestId('mode-filter').getByRole('button', { name: 'Paper' });
    await expect(paperButton).toHaveAttribute('class', /bg-primary/);
  });

  test('should show empty state when no trades', async ({ page }) => {
    // Override to return empty array
    await page.route('http://localhost:8000/api/trades**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [],
          meta: {
            total: 0,
            page: 1,
            per_page: 20,
          },
        }),
      });
    });

    await page.goto('/trades');

    // Should show empty state
    await expect(page.getByTestId('empty-state')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('暂无交易记录')).toBeVisible();
  });

  test('should handle API error gracefully', async ({ page }) => {
    // Override to return an error
    await page.route('http://localhost:8000/api/trades**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' }),
      });
    });

    await page.goto('/trades');

    // Should show error alert
    await expect(page.getByTestId('error-alert')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/无法加载数据/)).toBeVisible();
  });
});
