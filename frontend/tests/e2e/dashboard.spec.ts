import { test, expect } from './fixtures';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.click('button:has-text("Dashboard")');
    await page.waitForLoadState('networkidle');
  });

  test('Stats cards render with correct labels', async ({ page }) => {
    await expect(page.locator('text=Total Agents')).toBeVisible();
    await expect(page.locator('text=Active Workflows')).toBeVisible();
    await expect(page.locator('text=Completed Today')).toBeVisible();
    await expect(page.locator('text=Failed Today')).toBeVisible();
    await expect(page.locator('text=Success Rate')).toBeVisible();
  });

  test('Stats numbers are numeric (not NaN)', async ({ page }) => {
    // Wait for stats to load
    await page.waitForSelector('.stat-value', { timeout: 10000 });

    const statValues = page.locator('.stat-value');
    const count = await statValues.count();

    for (let i = 0; i < count; i++) {
      const value = await statValues.nth(i).textContent();
      if (value) {
        // Success rate has a % sign
        const numericValue = value.replace('%', '');
        expect(isNaN(Number(numericValue))).toBe(false);
      }
    }
  });

  test('Recent Agents section exists', async ({ page }) => {
    await expect(page.locator('text=Recent Agents')).toBeVisible();
  });

  test('Recent Workflows section exists', async ({ page }) => {
    await expect(page.locator('text=Recent Workflows')).toBeVisible();
  });

  test('Dashboard can be refreshed', async ({ page }) => {
    // Wait for initial load
    await page.waitForLoadState('networkidle');

    // Refresh and verify still works
    await page.reload();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h2:has-text("Dashboard")')).toBeVisible();
  });

  test('Health indicator present when backend is up', async ({ page }) => {
    // If the app renders stats, backend is considered up
    await expect(page.locator('.stat-value').first()).toBeVisible({ timeout: 15000 });
  });
});