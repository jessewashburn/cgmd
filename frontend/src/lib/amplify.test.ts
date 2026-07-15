import { describe, it, expect } from 'vitest';
import { cognitoConfigured } from './amplify';

// Regression guard: the Cognito IDs must be compiled in from source defaults, not
// from a shell/env var. A build without them still succeeds but ships an admin
// login that says "isn't configured yet" (happened 2026-07-14). This test runs
// with no VITE_COGNITO_* set, so it fails if the defaults are ever removed.
describe('amplify config', () => {
  it('is configured without any VITE_COGNITO_* env vars', () => {
    expect(import.meta.env.VITE_COGNITO_USER_POOL_ID).toBeUndefined();
    expect(cognitoConfigured).toBe(true);
  });
});
