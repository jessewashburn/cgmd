import {
  TableFilterState,
  DEFAULT_YEAR_MIN,
  DEFAULT_YEAR_MAX,
} from '../hooks/useServerTable';

/**
 * Map the generic filter state to each list page's backend query params.
 *
 * The two list pages share a filter UI but not a query vocabulary — /composers/
 * filters on the composer directly, /works/ crosses the relation — so each page
 * brings its own builder. They live here, outside the page modules, because a
 * module that exports both a component and a plain function breaks React Fast
 * Refresh; keeping them module-level also gives each a stable reference across
 * renders, which the memoized table depends on.
 */

/** Filter state -> /composers/ query params. */
export function buildComposerFilterParams(filters: TableFilterState): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (filters.instrumentation) params.instrumentation = filters.instrumentation;
  if (filters.country) params.country_name = filters.country;
  const [min, max] = filters.yearRange;
  if (min !== DEFAULT_YEAR_MIN || max !== DEFAULT_YEAR_MAX) {
    params.birth_year_min = min;
    params.birth_year_max = max;
  }
  // CSV, not a repeated param: buildFilterParams' return type holds strings, and
  // axios would serialize an array as eras[]= without a custom paramsSerializer.
  if (filters.eras.length) params.eras = filters.eras.join(',');
  return params;
}

/** Filter state -> /works/ query params. */
export function buildWorkFilterParams(filters: TableFilterState): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (filters.instrumentation) params.instrumentation = filters.instrumentation;
  if (filters.country) params.composer_country = filters.country;
  const [min, max] = filters.yearRange;
  if (min !== DEFAULT_YEAR_MIN || max !== DEFAULT_YEAR_MAX) {
    // Combined year filter: matches composer birth year, falling back to the
    // work's composition year when the composer has no birth year on record.
    params.year_min = min;
    params.year_max = max;
  }
  // Named for the relation it crosses, matching composer_country above.
  if (filters.eras.length) params.composer_eras = filters.eras.join(',');
  // Only the exclude case is sent. Including arrangements is the default, so the common
  // request carries no param at all and the backend skips the filter entirely.
  if (!filters.includeArrangements) params.is_arrangement = 'false';
  return params;
}
