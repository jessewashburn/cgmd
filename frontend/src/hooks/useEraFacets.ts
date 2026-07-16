import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';

export interface EraFacet {
  slug: string;
  label: string;
  start_year: number;
  end_year: number;
  /** Birth years that can place a composer in this era. Served by the backend so the
   *  creative-age/lifespan constants aren't duplicated (and left to drift) here. */
  implied_birth_min: number;
  implied_birth_max: number;
  /** Composers in this era under the *other* active filters (never the era filter). */
  count: number;
}

/**
 * Era chips with live counts.
 *
 * Unlike useInstrumentations/useCountries, this is not static reference data: the
 * counts move with the other filters, which is the whole point. Era tags are derived
 * from birth years, so the era chips and the birth-year slider are two views of one
 * axis and can silently contradict each other. Live counts let the UI dim a chip that
 * would return nothing ("Baroque (0)") instead of letting the user click into an
 * empty table.
 *
 * `params` must be the caller's already-memoized filter params minus the era
 * selection; the backend excludes the era filter from these counts on its side too
 * (a facet that counted itself would drive every other chip to zero).
 */
export function useEraFacets(params: Record<string, string | number>) {
  const { data } = useQuery({
    queryKey: ['era-facets', params],
    queryFn: async () => {
      const res = await api.get<EraFacet[]>('/composers/era_facets/', { params });
      return res.data;
    },
    // Reference-ish data that only shifts when filters do; keep the previous counts
    // on screen while refetching rather than flashing the chips empty.
    placeholderData: (previous) => previous,
    staleTime: 5 * 60 * 1000,
  });

  return data ?? [];
}
