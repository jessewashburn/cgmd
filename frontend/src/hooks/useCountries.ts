import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';

/**
 * Fetch and sort country names. Static reference data — cached indefinitely
 * (staleTime: Infinity) and shared across pages via TanStack Query, so it isn't
 * re-fetched on every list-page visit.
 */
export function useCountries() {
  const { data } = useQuery({
    queryKey: ['countries'],
    queryFn: async () => {
      const response = await api.get('/countries/', { params: { page_size: 500 } });
      const countryList = response.data.results || response.data;
      return (countryList as Array<{ name: string }>)
        .map((country) => country.name)
        .sort((a, b) => a.localeCompare(b));
    },
    staleTime: Infinity,
    gcTime: Infinity,
  });

  return data ?? [];
}
