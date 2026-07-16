import { useContext } from 'react';
import { AuthContext } from './authContextObject';

/** Auth state for the current user. Throws outside an <AuthProvider>. */
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
