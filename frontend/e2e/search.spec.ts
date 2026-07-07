import { test, expect } from '@playwright/test';

const SEARCH = 'Search for works or composers...';

test('fast typing never shows stale results (race safety)', async ({ page }) => {
  // Delay short (early) queries far more than longer ones, forcing responses
  // to resolve out of order. TanStack Query must still show the final term.
  await page.route('**/api/works/**', async (route) => {
    const term = new URL(route.request().url()).searchParams.get('search') ?? '';
    await new Promise((r) => setTimeout(r, term.length > 0 && term.length < 3 ? 700 : 120));
    await route.continue();
  });

  await page.goto('/works');
  await page.getByPlaceholder(SEARCH).pressSequentially('sor', { delay: 90 });

  // Final term 'sor' matches works by Fernando Sor.
  await expect(page.getByText('Estudio No. 1')).toBeVisible({ timeout: 8_000 });
});

test('search ranks by relevance until a header is clicked', async ({ page }) => {
  await page.goto('/works?q=sor');
  await expect(page.locator('tbody tr').first()).toBeVisible();
  await expect(page).not.toHaveURL(/sort=/); // relevance: no ordering param

  // Click a non-default column so the assertion is unambiguous (asc).
  await page.getByText('Composer', { exact: true }).click();
  await expect(page).toHaveURL(/sort=composer__full_name/); // manual sort overrides relevance
});
