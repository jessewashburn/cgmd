import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { PaginatedResponse } from '../types';
import { SortState } from '../components/ui/DataTable';
import { useDebounce } from './useDebounce';

export const DEFAULT_YEAR_MIN = 1400;
export const DEFAULT_YEAR_MAX = 2025;
const DEFAULT_PAGE = 1;
const DEBOUNCE_MS = 300; // standardized across all list pages

export interface TableFilterState {
  instrumentation: string;
  country: string;
  yearRange: [number, number];
  /** Selected era slugs, e.g. ['romantic', 'modern']. Empty = no era filter. */
  eras: string[];
}

/**
 * Normalize an ?eras= CSV the same way the backend's parse_era_filter does:
 * lowercase, trimmed, de-duplicated, order preserved.
 *
 * Without this the two disagree on a hand-edited URL — ?eras=MODERN filters
 * correctly server-side (it lowercases) while the Modern chip stays unlit, and
 * clicking it appends a second copy. Unknown slugs are left in: the frontend has no
 * static era vocabulary, and the backend already drops them.
 */
function parseEras(param: string): string[] {
  const seen = new Set<string>();
  for (const raw of param.split(',')) {
    const slug = raw.trim().toLowerCase();
    if (slug) seen.add(slug);
  }
  return [...seen];
}

export interface ServerTableConfig {
  /** API path, e.g. '/works/'. */
  endpoint: string;
  /** Stable prefix for the TanStack Query key, e.g. 'works'. */
  queryKey: string;
  /** Backend ordering field used when browsing (no manual sort), e.g. 'title_sort_key'. */
  defaultOrdering: string;
  pageSize?: number;
  /**
   * Map the generic filter state to this endpoint's backend query params.
   * Must be a stable reference (define at module scope or memoize).
   */
  buildFilterParams: (filters: TableFilterState) => Record<string, string | number>;
}

export interface ServerTableResult<Row> {
  rows: Row[];
  totalCount: number;
  totalPages: number;
  page: number;
  setPage: (page: number) => void;

  isLoading: boolean;   // true only until first data arrives
  isFetching: boolean;  // true during background refetches (drives the dim overlay)
  isError: boolean;
  error: unknown;
  refetch: () => void;

  /** Raw (un-debounced) search input, for a controlled <input>. */
  searchInput: string;
  setSearchInput: (value: string) => void;

  /** Effective sort for header display (parsed from the URL / default). */
  sort: SortState;
  onSort: (key: string) => void;

  filters: TableFilterState;
  setInstrumentation: (value: string) => void;
  setCountry: (value: string) => void;
  setYearRange: (range: [number, number]) => void;
  /** Add/remove one era slug from the selection. */
  toggleEra: (slug: string) => void;
  clearFilters: () => void;
}

/**
 * Server-side data table state: URL is the source of truth for sort/search/page/filters,
 * TanStack Query is keyed on the request params (per-combination caching, race safety,
 * keepPreviousData paging). Preserves the "search-relevance vs. manual-sort" rule:
 * while a search term is active and the user has not manually sorted, no `ordering`
 * param is sent so the backend can rank by relevance.
 */
export function useServerTable<Row>(config: ServerTableConfig): ServerTableResult<Row> {
  const { endpoint, queryKey, defaultOrdering, buildFilterParams } = config;
  const pageSize = config.pageSize ?? 50;

  const [searchParams, setSearchParams] = useSearchParams();

  // --- Read current state from the URL ---
  const page = parseInt(searchParams.get('page') || '', 10) || DEFAULT_PAGE;
  const sortParam = searchParams.get('sort'); // signed backend ordering string, or null
  const urlSearch = searchParams.get('q') || '';
  const instrumentation = searchParams.get('inst') || '';
  const country = searchParams.get('country') || '';
  const ymin = parseInt(searchParams.get('ymin') || '', 10) || DEFAULT_YEAR_MIN;
  const ymax = parseInt(searchParams.get('ymax') || '', 10) || DEFAULT_YEAR_MAX;
  // Kept as the raw CSV string, not an array: splitting here would allocate a new
  // array every render and bust the `filters` memo below (and every React.memo under
  // it). The split happens inside the memo, keyed on this string.
  const erasParam = searchParams.get('eras') || '';

  const manualSort = sortParam != null;
  const effectiveOrdering = sortParam ?? defaultOrdering;
  // Memoized so the `sort` reference is stable across unrelated re-renders (e.g. every
  // search keystroke). A fresh object here would bust React.memo on the consuming table.
  const sort: SortState = useMemo(
    () => ({
      key: effectiveOrdering.replace(/^-/, ''),
      dir: effectiveOrdering.startsWith('-') ? 'desc' : 'asc',
    }),
    [effectiveOrdering],
  );

  const updateParams = useCallback(
    (mutate: (next: URLSearchParams) => void, opts?: { replace?: boolean }) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          mutate(next);
          return next;
        },
        opts,
      );
    },
    [setSearchParams],
  );

  // --- Rapidly-changing inputs kept in local state, debounced before hitting the URL/query ---
  const [searchInput, setSearchInput] = useState(urlSearch);
  const [yearRange, setYearRangeLocal] = useState<[number, number]>([ymin, ymax]);
  const debouncedSearch = useDebounce(searchInput, DEBOUNCE_MS);
  const debouncedYear = useDebounce(yearRange, DEBOUNCE_MS);

  const lastWrittenSearch = useRef(urlSearch);
  const lastWrittenYear = useRef<[number, number]>([ymin, ymax]);

  // Commit debounced search to the URL (reset page, drop manual sort so search ranks by relevance).
  useEffect(() => {
    if (debouncedSearch === lastWrittenSearch.current) return;
    lastWrittenSearch.current = debouncedSearch;
    updateParams((next) => {
      if (debouncedSearch) next.set('q', debouncedSearch);
      else next.delete('q');
      next.delete('sort');
      next.delete('page');
    }, { replace: true });
  }, [debouncedSearch, updateParams]);

  // Sync URL search -> local input on external navigation (back/forward, shared link).
  useEffect(() => {
    if (urlSearch !== lastWrittenSearch.current) {
      lastWrittenSearch.current = urlSearch;
      setSearchInput(urlSearch);
    }
  }, [urlSearch]);

  // Commit debounced year range to the URL (omit defaults, reset page).
  useEffect(() => {
    const [lo, hi] = debouncedYear;
    if (lo === lastWrittenYear.current[0] && hi === lastWrittenYear.current[1]) return;
    lastWrittenYear.current = [lo, hi];
    updateParams((next) => {
      if (lo !== DEFAULT_YEAR_MIN) next.set('ymin', String(lo));
      else next.delete('ymin');
      if (hi !== DEFAULT_YEAR_MAX) next.set('ymax', String(hi));
      else next.delete('ymax');
      next.delete('page');
    }, { replace: true });
  }, [debouncedYear, updateParams]);

  // Sync URL year range -> local on external navigation.
  useEffect(() => {
    if (ymin !== lastWrittenYear.current[0] || ymax !== lastWrittenYear.current[1]) {
      lastWrittenYear.current = [ymin, ymax];
      setYearRangeLocal([ymin, ymax]);
    }
  }, [ymin, ymax]);

  const setPage = useCallback(
    (p: number) => {
      updateParams((next) => {
        if (p <= 1) next.delete('page');
        else next.set('page', String(p));
      });
    },
    [updateParams],
  );

  const onSort = useCallback(
    (key: string) => {
      const currentKey = effectiveOrdering.replace(/^-/, '');
      const currentDir = effectiveOrdering.startsWith('-') ? 'desc' : 'asc';
      const nextDir = currentKey === key && currentDir === 'asc' ? 'desc' : 'asc';
      const signed = nextDir === 'desc' ? `-${key}` : key;
      updateParams((next) => {
        next.set('sort', signed);
        next.delete('page');
      });
    },
    [effectiveOrdering, updateParams],
  );

  const setInstrumentation = useCallback(
    (value: string) => {
      updateParams((next) => {
        if (value) next.set('inst', value);
        else next.delete('inst');
        next.delete('page');
      });
    },
    [updateParams],
  );

  const setCountry = useCallback(
    (value: string) => {
      updateParams((next) => {
        if (value) next.set('country', value);
        else next.delete('country');
        next.delete('page');
      });
    },
    [updateParams],
  );

  const setYearRange = useCallback((range: [number, number]) => {
    setYearRangeLocal(range);
  }, []);

  // Discrete control, so it goes straight to the URL — no debounce, same as the dropdowns.
  const toggleEra = useCallback(
    (slug: string) => {
      updateParams((next) => {
        // Parse before comparing so a hand-edited ?eras=MODERN toggles off rather
        // than appending a lowercase duplicate.
        const current = parseEras(next.get('eras') || '');
        const updated = current.includes(slug)
          ? current.filter((s) => s !== slug)
          : [...current, slug];
        if (updated.length) next.set('eras', updated.join(','));
        else next.delete('eras');
        next.delete('page');
      });
    },
    [updateParams],
  );

  const clearFilters = useCallback(() => {
    lastWrittenYear.current = [DEFAULT_YEAR_MIN, DEFAULT_YEAR_MAX];
    setYearRangeLocal([DEFAULT_YEAR_MIN, DEFAULT_YEAR_MAX]);
    updateParams((next) => {
      next.delete('inst');
      next.delete('country');
      next.delete('ymin');
      next.delete('ymax');
      next.delete('eras');
      next.delete('page');
    });
  }, [updateParams]);

  // --- Build the request params + query ---
  // Stable reference so consumers/children memoized on `filters` aren't re-rendered needlessly.
  const filters = useMemo<TableFilterState>(
    () => ({
      instrumentation,
      country,
      yearRange,
      eras: parseEras(erasParam),
    }),
    [instrumentation, country, yearRange, erasParam],
  );

  const orderingToSend = debouncedSearch && !manualSort ? undefined : effectiveOrdering;

  const queryParams = useMemo(() => {
    const p: Record<string, string | number> = { page, page_size: pageSize };
    if (debouncedSearch) p.search = debouncedSearch;
    if (orderingToSend) p.ordering = orderingToSend;
    Object.assign(
      p,
      buildFilterParams({
        instrumentation,
        country,
        yearRange: debouncedYear,
        eras: parseEras(erasParam),
      }),
    );
    return p;
  }, [page, pageSize, debouncedSearch, orderingToSend, instrumentation, country, debouncedYear, erasParam, buildFilterParams]);

  const query = useQuery({
    queryKey: [queryKey, queryParams],
    queryFn: async () => {
      const res = await api.get<PaginatedResponse<Row>>(endpoint, { params: queryParams });
      return res.data;
    },
    placeholderData: keepPreviousData,
  });

  const totalCount = query.data?.count ?? 0;

  return {
    rows: query.data?.results ?? [],
    totalCount,
    totalPages: Math.max(1, Math.ceil(totalCount / pageSize)),
    page,
    setPage,

    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,

    searchInput,
    setSearchInput,

    sort,
    onSort,

    filters,
    setInstrumentation,
    setCountry,
    setYearRange,
    toggleEra,
    clearFilters,
  };
}
