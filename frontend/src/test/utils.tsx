import { ReactNode } from 'react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

export interface Harness {
  wrapper: ({ children }: { children: ReactNode }) => JSX.Element;
  /** Live view of the router location, updated on every render. */
  location: { search: string; pathname: string };
}

/**
 * Build a test wrapper that provides TanStack Query + a MemoryRouter at `initialEntries`,
 * and exposes the current router location so tests can assert on URL state.
 */
export function makeHarness(initialEntries: string[] = ['/works']): Harness {
  const location = { search: '', pathname: '' };
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  function LocationProbe() {
    const loc = useLocation();
    location.search = loc.search;
    location.pathname = loc.pathname;
    return null;
  }

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <LocationProbe />
        {children}
      </MemoryRouter>
    </QueryClientProvider>
  );

  return { wrapper, location };
}
