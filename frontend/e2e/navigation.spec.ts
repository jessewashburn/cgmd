import { test, expect } from '@playwright/test';

test('works list → work detail → back', async ({ page }) => {
  await page.goto('/works');
  const firstLink = page.locator('tbody tr a').first();
  await expect(firstLink).toBeVisible();
  await firstLink.click();
  await expect(page).toHaveURL(/\/works\/\d+/);
  await page.goBack();
  await expect(page).toHaveURL(/\/works(\?|$)/);
});

test('composers list renders and sorts by a column', async ({ page }) => {
  await page.goto('/composers');
  await expect(page.getByRole('heading', { name: 'Composers' })).toBeVisible();
  await expect(page.locator('tbody tr').first()).toBeVisible();
  await page.getByText('Country', { exact: false }).first().click();
  await expect(page).toHaveURL(/sort=country__name/);
});

test('global search page returns works and composers', async ({ page }) => {
  await page.goto('/search?q=tarrega');
  await expect(page.getByText(/Found/i)).toBeVisible();
});
