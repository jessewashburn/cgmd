import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'], // exclude Playwright specs under e2e/
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: [
        'src/hooks/**',
        'src/components/ui/DataTable/**',
        'src/pages/WorkListPage.tsx',
        'src/pages/ComposerListPage.tsx',
      ],
      // Gate the refactor's risk core. Raise as coverage grows.
      thresholds: {
        statements: 80,
        branches: 78,
        functions: 80,
        lines: 80,
      },
    },
  },
});
