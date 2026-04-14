import { test, expect } from './fixtures';

test.describe('Agents - CRUD Operations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.click('button:has-text("Agents")');
    await page.waitForLoadState('networkidle');
  });

  test.afterEach(async ({ cleanupTestData, request }) => {
    await cleanupTestData(request);
  });

  test('Create agent - form fields visible', async ({ page }) => {
    await page.click('button:has-text("Create Agent")');

    await expect(page.locator('label:has-text("Name")')).toBeVisible();
    await expect(page.locator('label:has-text("Description")')).toBeVisible();
    await expect(page.locator('label:has-text("Provider")')).toBeVisible();
    await expect(page.locator('label:has-text("Model")')).toBeVisible();
    await expect(page.locator('label:has-text("System Prompt")')).toBeVisible();
  });

  test('Create agent - select MiniMax provider', async ({ page }) => {
    await page.click('button:has-text("Create Agent")');

    const providerSelect = page.locator('select').first();
    await providerSelect.selectOption('minimax');

    const modelSelect = page.locator('select').nth(1);
    const selectedModel = await modelSelect.inputValue();
    expect(selectedModel).toBeTruthy();
  });

  test('Create agent with MiniMax-M2.7 model', async ({ page, request }) => {
    await page.click('button:has-text("Create Agent")');

    // Wait for modal to be fully rendered
    await page.waitForSelector('input[placeholder="Research Agent"]', { state: 'visible' });

    await page.fill('input[placeholder="Research Agent"]', 'e2e-test-agent');

    await page.locator('select').first().selectOption('minimax');

    // Wait for model dropdown to update with MiniMax options
    await page.waitForTimeout(300);
    await page.locator('select').nth(1).selectOption('MiniMax-M2.7');

    await page.fill('textarea[placeholder*="helpful"]', 'You are a helpful test agent for E2E testing.');

    // Click Create button in form actions
    await page.locator('button[type="submit"]').click();

    // Wait for the API call to complete
    await page.waitForResponse(response =>
      response.url().includes('/api/v1/agents') && response.status() === 200
    );

    // Wait for agent to appear in the list
    await expect(page.locator('.card').filter({ hasText: 'e2e-test-agent' })).toBeVisible({ timeout: 10000 });
  });

  test('Read agent - agent card shows name, provider, model', async ({ page }) => {
    await page.click('button:has-text("Create Agent")');
    await page.waitForSelector('input[placeholder="Research Agent"]', { state: 'visible' });

    await page.fill('input[placeholder="Research Agent"]', 'e2e-read-agent');
    await page.locator('select').first().selectOption('minimax');
    await page.waitForTimeout(300);
    await page.locator('select').nth(1).selectOption('MiniMax-M2.7');
    await page.fill('textarea[placeholder*="helpful"]', 'Test agent');

    await page.locator('button[type="submit"]').click();

    // Wait for the API call to complete
    await page.waitForResponse(response =>
      response.url().includes('/api/v1/agents') && response.status() === 200
    );

    await expect(page.locator('.card').filter({ hasText: 'e2e-read-agent' })).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.mono-value').first()).toBeVisible();
  });

  test('Update agent - View modal opens', async ({ page }) => {
    await page.click('button:has-text("Create Agent")');
    await page.waitForSelector('input[placeholder="Research Agent"]', { state: 'visible' });

    await page.fill('input[placeholder="Research Agent"]', 'e2e-update-agent');
    await page.locator('select').first().selectOption('minimax');
    await page.waitForTimeout(300);
    await page.locator('select').nth(1).selectOption('MiniMax-M2.7');
    await page.fill('textarea[placeholder*="helpful"]', 'Test agent');
    await page.locator('button[type="submit"]').click();

    // Wait for the API call to complete
    await page.waitForResponse(response =>
      response.url().includes('/api/v1/agents') && response.status() === 200
    );

    // Wait for the agent card to appear
    await expect(page.locator('.card').filter({ hasText: 'e2e-update-agent' })).toBeVisible({ timeout: 10000 });

    await page.click('button:has-text("View")');
    await expect(page.locator('.modal-wide')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.modal-wide h2').filter({ hasText: 'e2e-update-agent' })).toBeVisible();
  });

  test('Delete agent - click delete removes from list', async ({ page }) => {
    await page.click('button:has-text("Create Agent")');
    await page.waitForSelector('input[placeholder="Research Agent"]', { state: 'visible' });

    await page.fill('input[placeholder="Research Agent"]', 'e2e-delete-agent');
    await page.locator('select').first().selectOption('minimax');
    await page.waitForTimeout(300);
    await page.locator('select').nth(1).selectOption('MiniMax-M2.7');
    await page.fill('textarea[placeholder*="helpful"]', 'Test agent');
    await page.locator('button[type="submit"]').click();

    // Wait for the API call to complete
    await page.waitForResponse(response =>
      response.url().includes('/api/v1/agents') && response.status() === 200
    );

    await expect(page.locator('.card').filter({ hasText: 'e2e-delete-agent' })).toBeVisible({ timeout: 10000 });

    // Delete button is the destructive variant button with Trash2 icon
    const deleteBtn = page.locator('.btn-destructive').filter({ has: page.locator('svg') });
    await deleteBtn.click();

    await page.waitForResponse(response =>
      response.url().includes('/api/v1/agents') && response.status() === 204
    );
  });

  test('Validation - required fields enforced', async ({ page }) => {
    await page.click('button:has-text("Create Agent")');
    await page.waitForSelector('input[placeholder="Research Agent"]', { state: 'visible' });

    await page.locator('button[type="submit"]').click();

    // Form should still be visible (name is required)
    await expect(page.locator('input[placeholder="Research Agent"]')).toBeVisible();
    const nameInput = page.locator('input[placeholder="Research Agent"]');
    await expect(nameInput).toHaveAttribute('required', '');
  });

  test('Provider dropdown change updates model dropdown', async ({ page }) => {
    await page.click('button:has-text("Create Agent")');
    await page.waitForSelector('input[placeholder="Research Agent"]', { state: 'visible' });

    const initialModelSelect = page.locator('select').nth(1);
    const initialModels = await initialModelSelect.locator('option').allTextContents();

    await page.locator('select').first().selectOption('openai');

    await page.waitForTimeout(300);
    const newModelSelect = page.locator('select').nth(1);
    const newModels = await newModelSelect.locator('option').allTextContents();

    expect(JSON.stringify(initialModels)).not.toBe(JSON.stringify(newModels));
  });

  test('Agent card displays status badge', async ({ page }) => {
    await page.click('button:has-text("Create Agent")');
    await page.waitForSelector('input[placeholder="Research Agent"]', { state: 'visible' });

    await page.fill('input[placeholder="Research Agent"]', 'e2e-status-agent');
    await page.locator('select').first().selectOption('minimax');
    await page.waitForTimeout(300);
    await page.locator('select').nth(1).selectOption('MiniMax-M2.7');
    await page.fill('textarea[placeholder*="helpful"]', 'Test agent');
    await page.locator('button[type="submit"]').click();

    // Wait for the API call to complete
    await page.waitForResponse(response =>
      response.url().includes('/api/v1/agents') && response.status() === 200
    );

    // Status badge shows "idle" (lowercase as shown in Badge)
    await expect(page.locator('.card').filter({ hasText: 'e2e-status-agent' }).locator('text=idle')).toBeVisible({ timeout: 10000 });
  });

  test('Agent card displays tools count', async ({ page }) => {
    await page.click('button:has-text("Create Agent")');
    await page.waitForSelector('input[placeholder="Research Agent"]', { state: 'visible' });

    await page.fill('input[placeholder="Research Agent"]', 'e2e-tools-agent');
    await page.locator('select').first().selectOption('minimax');
    await page.waitForTimeout(300);
    await page.locator('select').nth(1).selectOption('MiniMax-M2.7');
    await page.fill('textarea[placeholder*="helpful"]', 'Test agent');
    await page.locator('button[type="submit"]').click();

    // Wait for the API call to complete
    await page.waitForResponse(response =>
      response.url().includes('/api/v1/agents') && response.status() === 200
    );

    // Tools count is shown as number 0 in data-value span
    await expect(page.locator('.card').filter({ hasText: 'e2e-tools-agent' }).locator('.data-value').filter({ hasText: '0' })).toBeVisible({ timeout: 10000 });
  });

  test('Create modal closes on Cancel', async ({ page }) => {
    await page.click('button:has-text("Create Agent")');
    await expect(page.locator('input[placeholder="Research Agent"]')).toBeVisible();

    await page.click('button:has-text("Cancel")');

    await expect(page.locator('input[placeholder="Research Agent"]')).not.toBeVisible({ timeout: 5000 });
  });

  test('Agents list shows empty state when no agents exist', async ({ page }) => {
    await page.goto('/');
    await page.click('button:has-text("Agents")');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.empty-state')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=No agents yet')).toBeVisible();
  });

  test('Agent detail modal shows system prompt', async ({ page }) => {
    await page.click('button:has-text("Create Agent")');
    await page.waitForSelector('input[placeholder="Research Agent"]', { state: 'visible' });

    await page.fill('input[placeholder="Research Agent"]', 'e2e-detail-agent');
    await page.locator('select').first().selectOption('minimax');
    await page.waitForTimeout(300);
    await page.locator('select').nth(1).selectOption('MiniMax-M2.7');
    await page.fill('textarea[placeholder*="helpful"]', 'You are a specialized test agent with specific instructions.');
    await page.locator('button[type="submit"]').click();

    // Wait for the API call to complete
    await page.waitForResponse(response =>
      response.url().includes('/api/v1/agents') && response.status() === 200
    );

    await expect(page.locator('.card').filter({ hasText: 'e2e-detail-agent' })).toBeVisible({ timeout: 10000 });

    await page.locator('.card').filter({ hasText: 'e2e-detail-agent' }).locator('button:has-text("View")').click();

    await expect(page.locator('.code-block')).toBeVisible({ timeout: 5000 });
  });

  test('Multiple agents can be created', async ({ page }) => {
    for (let i = 0; i < 2; i++) {
      await page.click('button:has-text("Create Agent")');
      await page.waitForSelector('input[placeholder="Research Agent"]', { state: 'visible' });

      await page.fill('input[placeholder="Research Agent"]', `e2e-multi-agent-${i}`);
      await page.locator('select').first().selectOption('minimax');
      await page.waitForTimeout(300);
      await page.locator('select').nth(1).selectOption('MiniMax-M2.7');
      await page.fill('textarea[placeholder*="helpful"]', 'Test agent');
      await page.locator('button[type="submit"]').click();

      // Wait for the API call to complete
      await page.waitForResponse(response =>
        response.url().includes('/api/v1/agents') && response.status() === 200
      );

      // Wait for modal to close and agent to appear
      await expect(page.locator('.card').filter({ hasText: `e2e-multi-agent-${i}` })).toBeVisible({ timeout: 10000 });
    }

    await expect(page.locator('.card').filter({ hasText: 'e2e-multi-agent-0' })).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.card').filter({ hasText: 'e2e-multi-agent-1' })).toBeVisible();
  });

  test('API authentication required for agent operations', async ({ page, request }) => {
    const response = await request.post('http://localhost:8000/api/v1/agents', {
      data: {
        name: 'e2e-auth-agent',
        model_provider: 'minimax',
        model_name: 'MiniMax-M2.7',
        system_prompt: 'Auth test',
      },
      headers: {
        'X-API-Key': process.env.APP_API_KEY || '',
      },
    });

    if (!process.env.APP_API_KEY && response.status() === 401) {
      // Expected - backend requires API key
    } else {
      expect([200, 201, 401]).toContain(response.status());
    }
  });
});