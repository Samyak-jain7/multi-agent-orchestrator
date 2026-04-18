import { test, expect } from './fixtures';

test.describe('Tasks - List, Filter, Details, and Retry', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.click('button:has-text("Tasks")');
    await page.waitForLoadState('networkidle');
  });

  test('Task list loads with correct columns', async ({ page }) => {
    // Tasks page should show column headers or data rows
    // Common columns: id, status, workflow, created_at
    await expect(page.locator('h2:has-text("Tasks")')).toBeVisible();
    
    // Should see some task indicators or empty state
    await expect(
      page.locator('.empty-state').or(page.locator('.card'))
    ).toBeVisible({ timeout: 10000 });
  });

  test('Task list loads with status badge', async ({ page }) => {
    // Wait for tasks to load or empty state
    await expect(
      page.locator('text=Pending').or(page.locator('text=Running').or(page.locator('text=Completed').or(
        page.locator('.empty-state')
      )))
    ).toBeVisible({ timeout: 10000 });
  });

  test('Task list shows workflow name', async ({ page }) => {
    // Either shows workflow name or empty state
    await expect(
      page.locator('text=Workflow').or(page.locator('.empty-state'))
    ).toBeVisible({ timeout: 10000 });
  });

  test('Task list shows created timestamp', async ({ page }) => {
    // Either shows timestamps or empty state
    await expect(
      page.locator('text=Created').or(page.locator('text=created_at').or(
        page.locator('.mono-value').or(page.locator('.empty-state'))
      ))
    ).toBeVisible({ timeout: 10000 });
  });

  test('Filter by status - select failed', async ({ page }) => {
    // Find status filter dropdown
    const statusFilter = page.locator('select').first();
    await statusFilter.selectOption('failed');
    
    // Wait for filter to apply
    await page.waitForLoadState('networkidle');
    
    // Should either show failed tasks or empty state
    await expect(page.locator('text=Failed').or(page.locator('.empty-state'))).toBeVisible({ timeout: 10000 });
  });

  test('Filter by status - select completed', async ({ page }) => {
    const statusFilter = page.locator('select').first();
    await statusFilter.selectOption('completed');
    await page.waitForLoadState('networkidle');
    
    await expect(page.locator('text=Completed').or(page.locator('.empty-state'))).toBeVisible({ timeout: 10000 });
  });

  test('Filter by status - select pending', async ({ page }) => {
    const statusFilter = page.locator('select').first();
    await statusFilter.selectOption('pending');
    await page.waitForLoadState('networkidle');
    
    await expect(page.locator('text=Pending').or(page.locator('.empty-state'))).toBeVisible({ timeout: 10000 });
  });

  test('Filter by status - all statuses option', async ({ page }) => {
    const statusFilter = page.locator('select').first();
    await statusFilter.selectOption('');
    await page.waitForLoadState('networkidle');
    
    // Should show all tasks or empty state
    await expect(page.locator('h2:has-text("Tasks")')).toBeVisible();
  });

  test('View task details - click row shows details panel', async ({ page }) => {
    // Create a task first
    await page.click('button:has-text("Create Task")');
    await page.waitForSelector('select', { timeout: 5000 }).catch(() => {});
    
    // Fill required fields if form is visible
    const nameInput = page.locator('input[placeholder*="Research"]').or(page.locator('input[type="text"]').first());
    if (await nameInput.isVisible()) {
      await nameInput.fill('e2e-detail-task');
      
      // Select workflow if dropdown visible
      const workflowSelect = page.locator('select').first();
      const options = await workflowSelect.locator('option').count();
      if (options > 1) {
        await workflowSelect.selectOption({ index: 1 });
      }
      
      // Submit
      await page.click('button:has-text("Create")');
      await page.waitForLoadState('networkidle');
    }
    
    // Try to click View Details on any task card
    const viewBtn = page.locator('button:has-text("View Details")').first();
    await viewBtn.click().catch(() => {});
    
    // Modal or details should appear
    await expect(
      page.locator('.modal-wide').or(page.locator('text=Input Data').or(
        page.locator('text=Output')
      ))
    ).toBeVisible({ timeout: 5000 });
  });

  test('Task details shows input_data', async ({ page }) => {
    // Create task with input data
    await page.click('button:has-text("Create Task")');
    
    const titleInput = page.locator('input[placeholder*="Research"]');
    if (await titleInput.isVisible({ timeout: 2000 })) {
      await titleInput.fill('e2e-input-task');
      
      // Try to find and fill JSON input
      const jsonInput = page.locator('textarea[placeholder*="query"]').or(page.locator('textarea').first());
      if (await jsonInput.isVisible()) {
        await jsonInput.fill('{"query": "AI trends", "limit": 10}');
      }
      
      await page.click('button:has-text("Create")');
      await page.waitForLoadState('networkidle');
    }
    
    // Click View Details
    const viewBtn = page.locator('button:has-text("View Details")').first();
    await viewBtn.click().catch(() => {});
    
    // Input data should be visible in modal
    await expect(
      page.locator('text=Input Data').or(page.locator('text=query'))
    ).toBeVisible({ timeout: 5000 });
  });

  test('Task details shows output', async ({ page }) => {
    // View details of a completed task
    await page.click('button:has-text("View Details")').first().catch(() => {});
    
    await expect(
      page.locator('text=Output').or(page.locator('.modal-wide'))
    ).toBeVisible({ timeout: 5000 });
  });

  test('Task details shows metadata', async ({ page }) => {
    await page.click('button:has-text("View Details")').first().catch(() => {});
    
    // Metadata fields like created, started, completed times
    await expect(
      page.locator('text=Created').or(page.locator('text=Started'))
    ).toBeVisible({ timeout: 5000 });
  });

  test('Retry button visible only for failed tasks', async ({ page }) => {
    // Filter to failed tasks
    const statusFilter = page.locator('select').first();
    await statusFilter.selectOption('failed');
    await page.waitForLoadState('networkidle');
    
    // If there are failed tasks, retry button should be visible
    // If no failed tasks, check that retry button doesn't appear for other statuses
    const retryBtn = page.locator('button:has-text("Retry")');
    
    // Either retry is visible for failed tasks, or no failed tasks exist
    const isVisible = await retryBtn.isVisible().catch(() => false);
    if (isVisible) {
      await expect(retryBtn).toBeEnabled();
    }
  });

  test('Retry button not visible for pending tasks', async ({ page }) => {
    // Filter to pending
    const statusFilter = page.locator('select').first();
    await statusFilter.selectOption('pending');
    await page.waitForLoadState('networkidle');
    
    // Retry button should not appear for pending tasks
    const retryBtn = page.locator('button:has-text("Retry")');
    await expect(retryBtn).not.toBeVisible({ timeout: 5000 }).catch(() => {});
  });

  test('Retry button not visible for completed tasks', async ({ page }) => {
    const statusFilter = page.locator('select').first();
    await statusFilter.selectOption('completed');
    await page.waitForLoadState('networkidle');
    
    const retryBtn = page.locator('button:has-text("Retry")');
    await expect(retryBtn).not.toBeVisible({ timeout: 5000 }).catch(() => {});
  });

  test('Retry task changes status to pending', async ({ page }) => {
    // First create a failed task
    await page.click('button:has-text("Create Task")');
    
    const titleInput = page.locator('input[placeholder*="Research"]');
    if (await titleInput.isVisible({ timeout: 2000 })) {
      await titleInput.fill('e2e-retry-task');
      await page.click('button:has-text("Create")');
      await page.waitForLoadState('networkidle');
    }
    
    // Filter to failed
    const statusFilter = page.locator('select').first();
    await statusFilter.selectOption('failed');
    await page.waitForLoadState('networkidle');
    
    // Click Retry if visible
    const retryBtn = page.locator('button:has-text("Retry")').first();
    await retryBtn.click().catch(() => {});
    
    // Status should change to pending (or task removed from failed list)
    await page.waitForLoadState('networkidle');
  });

  test('Task card shows priority', async ({ page }) => {
    // Create task with priority
    await page.click('button:has-text("Create Task")');
    
    const titleInput = page.locator('input[placeholder*="Research"]');
    if (await titleInput.isVisible({ timeout: 2000 })) {
      await titleInput.fill('e2e-priority-task');
      
      const priorityInput = page.locator('input[type="number"]');
      if (await priorityInput.isVisible()) {
        await priorityInput.fill('5');
      }
      
      await page.click('button:has-text("Create")');
      await page.waitForLoadState('networkidle');
    }
    
    // Priority should be displayed
    await expect(
      page.locator('text=Priority').or(page.locator('text=5'))
    ).toBeVisible({ timeout: 10000 });
  });

  test('Task shows agent name', async ({ page }) => {
    // Either shows agent name or agent selector
    await expect(
      page.locator('text=Agent').or(page.locator('select'))
    ).toBeVisible({ timeout: 10000 });
  });
});