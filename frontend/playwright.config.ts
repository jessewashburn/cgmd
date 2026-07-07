import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(dirname, '..');

// Local dev uses the repo venv; CI (no venv) sets E2E_PYTHON to a plain interpreter.
const venvPython =
  process.platform === 'win32'
    ? path.join(repoRoot, 'venv', 'Scripts', 'python.exe')
    : path.join(repoRoot, 'venv', 'bin', 'python');
const python = process.env.E2E_PYTHON || venvPython;

// Django E2E server: migrate + seed a deterministic dataset, then serve.
const djangoCmd =
  `"${python}" manage.py migrate --noinput && ` +
  `"${python}" manage.py seed_e2e --force && ` +
  `"${python}" manage.py runserver 8000 --noreload`;

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 7_000 },
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: djangoCmd,
      cwd: repoRoot,
      env: { DJANGO_SETTINGS_MODULE: 'cgmd_backend.settings_e2e' },
      url: 'http://localhost:8000/api/works/?page_size=1',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: 'npm run dev',
      cwd: dirname,
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
