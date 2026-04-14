import { test, expect } from './fixtures';

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('App loads at http://localhost:3000', async ({ page }) => {
    await expect(page).toHaveTitle(/Agent Orchestrator/i);
    await expect(page.locator('header')).toBeVisible();
  });

  test('Dashboard nav link works', async ({ page }) => {
    await page.click('button:has-text("Dashboard")');
    await expect(page.locator('h2:has-text("Dashboard")')).toBeVisible();
  });

  test('Agents nav link works', async ({ page }) => {
    await page.click('button:has-text("Agents")');
    await expect(page.locator('h2:has-text("Agents")')).toBeVisible();
  });

  test('Workflows nav link works', async ({ page }) => {
    await page.click('button:has-text("Workflows")');
    await expect(page.locator('h2:has-text("Workflows")')).toBeVisible();
  });

  test('Tasks nav link works', async ({ page }) => {
    await page.click('button:has-text("Tasks")');
    await expect(page.locator('h2:has-text("Tasks")')).toBeVisible();
  });

  test('Events nav link works', async ({ page }) => {
    await page.click('button:has-text("Events")');
    await expect(page.locator('h2:has-text("Event Stream")')).toBeVisible();
  });

  test('Active nav item is highlighted', async ({ page }) => {
    // Dashboard should be active by default
    const dashboardBtn = page.locator('button:has-text("Dashboard")');
    await expect(dashboardBtn).toHaveClass(/active/);

    // Click Agents and verify it's now active
    await page.click('button:has-text("Agents")');
    await expect(page.locator('button:has-text("Agents")')).toHaveClass(/active/);
    await expect(dashboardBtn).not.toHaveClass(/active/);
  });

  test('Page titles match expected values', async ({ page }) => {
    // Check each page title
    const expectedTitles = [
      { nav: 'Dashboard', title: 'Dashboard' },
      { nav: 'Agents', title: 'Agents' },
      { nav: 'Workflows', title: 'Workflows' },
      { nav: 'Tasks', title: 'Tasks' },
      { nav: 'Events', title: 'Event Stream' },
    ];

    for (const { nav, title } of expectedTitles) {
      await page.click(`button:has-text("${nav}")`);
      await page.waitForLoadState('networkidle');
      await expect(page.locator(`h2:has-text("${title}")`).first()).toBeVisible({ timeout: 10000 });
    }
  });
});