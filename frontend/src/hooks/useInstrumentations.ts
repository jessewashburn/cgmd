import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';

/**
 * Fetch instrumentation category names. This is static reference data, so it's
 * cached indefinitely (staleTime: Infinity) and shared across every page via
 * TanStack Query — navigating between list pages no longer re-fetches it.
 */
export function useInstrumentations() {
  const { data } = useQuery({
    queryKey: ['instrumentations'],
    queryFn: async () => {
      const response = await api.get('/instrumentations/', { params: { page_size: 100 } });
      const categories = response.data.results || response.data;
      return (categories as Array<{ name: string }>).map((cat) => cat.name);
    },
    staleTime: Infinity,
    gcTime: Infinity,
  });

  return data ?? [];
}
