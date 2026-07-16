import { createContext } from 'react';

export interface AuthUser {
  username: string;
  groups: string[];
}

export interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

/**
 * The context object itself, split from both its provider (AuthContext.tsx) and
 * its consumer hook (useAuth.ts): a module that exports a component alongside
 * anything else breaks React Fast Refresh, and provider and hook each need this.
 */
export const AuthContext = createContext<AuthContextType | undefined>(undefined);
