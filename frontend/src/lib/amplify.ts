import { Amplify } from 'aws-amplify';

// Cognito identifiers are public (not secrets) and injected at build time via Vite env.
// When unset (e.g. local dev without a pool), `cognitoConfigured` is false and the app
// degrades gracefully: admin login shows a "not configured" notice and API calls stay
// anonymous.
const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID as string | undefined;
const userPoolClientId = import.meta.env.VITE_COGNITO_APP_CLIENT_ID as string | undefined;

export const cognitoConfigured = Boolean(userPoolId && userPoolClientId);

if (cognitoConfigured) {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: userPoolId as string,
        userPoolClientId: userPoolClientId as string,
      },
    },
  });
}
