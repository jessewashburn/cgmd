import { test, expect } from '@playwright/test';

const SEARCH = 'Search for works or composers...';

test.describe('Works table', () => {
  test('default sort is alphabetical by title; toggling reverses it', async ({ page }) => {
    await page.goto('/works');
    await expect(page.locator('tbody tr').first()).toBeVisible();

    // Default ascending by title_sort_key: "Bachianas…" folds to the front of the seed set.
    await expect(page.locator('tbody tr').first()).toContainText('Bachianas Brasileiras No. 5');

    // First click flips to descending → the alphabetically-last seeded title leads.
    await page.getByText('Work Title').click();
    await expect(page).toHaveURL(/sort=-title_sort_key/);
    await expect(page.locator('tbody tr').first()).toContainText('Variations on a Theme by Mozart');
  });

  test('sorting by composer orders by surname', async ({ page }) => {
    await page.goto('/works');
    await page.getByRole('button', { name: 'Composer', exact: true }).click();
    // Ascending by composer last name → Barrios leads the seeded composers.
    await expect(page).toHaveURL(/sort=composer__last_name/);
    await expect(page.locator('tbody tr').first()).toContainText('Barrios');
  });

  test('sorting toggles order, updates the URL, and resets to page 1', async ({ page }) => {
    await page.goto('/works');
    await expect(page.getByRole('heading', { name: 'Works' })).toBeVisible();

    await page.getByRole('button', { name: 'Next' }).click();
    await expect(page).toHaveURL(/page=2/);

    // Default sort is title_sort_key ascending, so the first click flips it to descending.
    await page.getByText('Work Title').click();
    await expect(page).toHaveURL(/sort=-title_sort_key/);
    await expect(page).not.toHaveURL(/page=2/); // page reset on sort

    await page.getByText('Work Title').click(); // toggle back to ascending
    await expect(page).toHaveURL(/sort=title_sort_key/);
    await expect(page).not.toHaveURL(/sort=-title_sort_key/);
  });

  test('pagination keeps rows on screen and updates the URL', async ({ page }) => {
    await page.goto('/works');
    await expect(page.locator('tbody tr').first()).toBeVisible();
    const before = await page.locator('tbody tr').first().textContent();

    await page.getByRole('button', { name: 'Next' }).click();
    await expect(page).toHaveURL(/page=2/);
    await expect(page.locator('tbody tr').first()).toBeVisible(); // never empty
    // keepPreviousData holds page 1 rows visible during the fetch, so poll until the
    // page 2 rows actually render rather than reading textContent in that race window.
    await expect(page.locator('tbody tr').first()).not.toHaveText(before ?? '');
  });

  test('back button steps back through pages', async ({ page }) => {
    await page.goto('/works');
    await page.getByRole('button', { name: 'Next' }).click();
    await expect(page).toHaveURL(/page=2/);
    await page.getByRole('button', { name: 'Next' }).click();
    await expect(page).toHaveURL(/page=3/);

    await page.goBack();
    await expect(page).toHaveURL(/page=2/);
    await page.goBack();
    await expect(page).not.toHaveURL(/page=/); // back to page 1 (param omitted)
  });

  test('a shared URL reproduces search + sort', async ({ page }) => {
    await page.goto('/works?q=sor&sort=-composer__full_name');
    await expect(page.getByPlaceholder(SEARCH)).toHaveValue('sor');
    await expect(page.locator('tbody tr').first()).toBeVisible();
    // reload preserves it
    await page.reload();
    await expect(page.getByPlaceholder(SEARCH)).toHaveValue('sor');
  });

  test('instrumentation filter reflects in the URL', async ({ page }) => {
    await page.goto('/works');
    await page.getByRole('button', { name: /Advanced Filters/ }).click();
    await page.getByRole('button', { name: 'All Instrumentations' }).click();
    // The API serves curated display names; pick the first real option (skip "All …").
    await page.locator('.dropdown-menu .dropdown-option').nth(1).click();
    await expect(page).toHaveURL(/[?&]inst=/);
    await expect(page).not.toHaveURL(/page=/); // filtering resets to page 1
  });
});
