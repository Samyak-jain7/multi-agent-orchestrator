import { FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0]?.use?.baseURL || 'http://localhost:3000';

  try {
    const response = await fetch(baseURL, { method: 'HEAD' });
    if (!response.ok) {
      console.warn(`Warning: Frontend at ${baseURL} returned status ${response.status}`);
    }
  } catch (error) {
    console.warn(`Warning: Frontend at ${baseURL} is not accessible. Ensure dev server is running.`);
  }
}

export default globalSetup;