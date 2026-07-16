import { useState, useEffect, useCallback, ReactNode } from 'react';
import { fetchAuthSession, signOut as amplifySignOut } from 'aws-amplify/auth';
import { Hub } from 'aws-amplify/utils';
import { cognitoConfigured } from '../lib/amplify';
import { AuthContext, AuthUser } from './authContextObject';

const ADMIN_GROUP = 'admins';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!cognitoConfigured) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const { tokens } = await fetchAuthSession();
      const accessToken = tokens?.accessToken;
      if (!accessToken) {
        setUser(null);
        return;
      }
      const payload = accessToken.payload;
      const groups = (payload['cognito:groups'] as string[] | undefined) ?? [];
      const username = (payload['username'] as string | undefined) ?? '';
      setUser({ username, groups });
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      if (cognitoConfigured) {
        await amplifySignOut();
      }
    } finally {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refresh();
    if (!cognitoConfigured) return;
    // Keep context in sync with Amplify sign-in / sign-out / token refresh.
    const unsubscribe = Hub.listen('auth', ({ payload }) => {
      if (['signedIn', 'signedOut', 'tokenRefresh'].includes(payload.event)) {
        refresh();
      }
    });
    return unsubscribe;
  }, [refresh]);

  const isAuthenticated = !!user;
  const isAdmin = !!user && user.groups.includes(ADMIN_GROUP);

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated, isAdmin, isLoading, refresh, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}
