import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { fetchAuthSession, signOut as amplifySignOut } from 'aws-amplify/auth';
import { Hub } from 'aws-amplify/utils';
import { cognitoConfigured } from '../lib/amplify';

const ADMIN_GROUP = 'admins';

interface AuthUser {
  username: string;
  groups: string[];
}

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

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

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
