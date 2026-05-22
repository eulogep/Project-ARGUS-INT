import { test, expect } from '@playwright/test';

test.describe('C2 Panel OPSEC Checks', () => {
  test('Panic Mode triggers on 3x Escape keys and redirects to about:blank', async ({ page }) => {
    // 1. Visit frontpage
    await page.goto('http://localhost:3000/');
    
    // 2. Set some test state
    await page.evaluate(() => {
      localStorage.setItem('sensitive_data', 'confidential_intel');
      sessionStorage.setItem('session_key', 'active_analyst_session');
    });

    // 3. Press Escape 3 times quickly
    await page.keyboard.press('Escape');
    await page.keyboard.press('Escape');
    await page.keyboard.press('Escape');

    // 4. Verify local data is fully purged and browser redirected to blank
    await page.waitForTimeout(500);
    const storageEmpty = await page.evaluate(() => localStorage.getItem('sensitive_data') === null);
    
    expect(storageEmpty).toBeTruthy();
    expect(page.url()).toBe('about:blank');
  });
});
