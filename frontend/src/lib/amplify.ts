import { Amplify } from 'aws-amplify';

// AWS Cognito admin auth (see AWS_DEPLOYMENT.md → "Frontend deploy").
//
// These IDs are PUBLIC identifiers, not secrets — they ship inside the client
// bundle regardless, and the pool is protected by SRP + the `admins` group, not
// by hiding them. They are hardcoded here ON PURPOSE so that *every* build bakes
// them in.
//
// Why not a build-time env var / .env file: we tried that, and a plain
// `npm run build` (without the vars exported in the shell) silently produced a
// bundle where admin login rendered "Admin login isn't configured yet" — a broken
// prod login with a green build. Config that only exists in someone's shell is
// not config. `scripts/deploy-frontend.sh` also hard-fails if the pool id is
// missing from the built bundle.
//
// The env vars still take precedence, so a build can be pointed at another pool
// (e.g. a staging pool) without touching code.
const DEFAULT_USER_POOL_ID = 'us-east-1_dKVMYPC8c';
const DEFAULT_APP_CLIENT_ID = '23orpavq4u24ivt8ckrvhbushb';

const userPoolId =
  (import.meta.env.VITE_COGNITO_USER_POOL_ID as string | undefined) || DEFAULT_USER_POOL_ID;
const userPoolClientId =
  (import.meta.env.VITE_COGNITO_APP_CLIENT_ID as string | undefined) || DEFAULT_APP_CLIENT_ID;

export const cognitoConfigured = Boolean(userPoolId && userPoolClientId);

if (cognitoConfigured) {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId,
        // The pool signs in with email — present an "Email" field, not "Username".
        loginWith: { email: true },
      },
    },
  });
}
