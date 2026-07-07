import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import {
  useServerTable,
  TableFilterState,
  DEFAULT_YEAR_MIN,
  DEFAULT_YEAR_MAX,
} from './useServerTable';
import { makeHarness } from '../test/utils';
import { lastRequestUrl, resetRequestLog } from '../test/handlers';

// Stable module-level builder (mirrors the /works/ mapping).
function buildFilterParams(f: TableFilterState): Record<string, string | number> {
  const p: Record<string, string | number> = {};
  if (f.instrumentation) p.instrumentation = f.instrumentation;
  if (f.country) p.country_name = f.country;
  const [min, max] = f.yearRange;
  if (min !== DEFAULT_YEAR_MIN || max !== DEFAULT_YEAR_MAX) {
    p.year_min = min;
    p.year_max = max;
  }
  return p;
}

const config = {
  endpoint: '/works/',
  queryKey: 'works',
  defaultOrdering: 'title_sort_key',
  pageSize: 50,
  buildFilterParams,
};

const reqParams = () => new URL(lastRequestUrl()!).searchParams;
const urlParams = (search: string) => new URLSearchParams(search);

beforeEach(() => resetRequestLog());

describe('useServerTable', () => {
  it('sends defaults and keeps the URL clean on first load', async () => {
    const { wrapper, location } = makeHarness(['/works']);
    renderHook(() => useServerTable(config), { wrapper });

    await waitFor(() => expect(lastRequestUrl()).toBeDefined());
    expect(reqParams().get('page')).toBe('1');
    expect(reqParams().get('page_size')).toBe('50');
    expect(reqParams().get('ordering')).toBe('title_sort_key');
    expect(location.search).toBe(''); // defaults omitted from URL
  });

  it('toggles sort into the URL and resets the page', async () => {
    const { wrapper, location } = makeHarness(['/works?page=3']);
    const { result } = renderHook(() => useServerTable(config), { wrapper });
    await waitFor(() => expect(lastRequestUrl()).toBeDefined());

    act(() => result.current.onSort('composer__full_name'));
    await waitFor(() =>
      expect(urlParams(location.search).get('sort')).toBe('composer__full_name'),
    );
    expect(urlParams(location.search).get('page')).toBeNull(); // page reset

    act(() => result.current.onSort('composer__full_name')); // same key → desc
    await waitFor(() =>
      expect(urlParams(location.search).get('sort')).toBe('-composer__full_name'),
    );
  });

  it('omits ordering while searching until the user sorts (relevance vs manual)', async () => {
    const { wrapper } = makeHarness(['/works?q=tarrega']);
    const { result } = renderHook(() => useServerTable(config), { wrapper });

    await waitFor(() => expect(lastRequestUrl()).toBeDefined());
    await waitFor(() => expect(reqParams().has('ordering')).toBe(false));
    expect(reqParams().get('search')).toBe('tarrega');

    act(() => result.current.onSort('composer__full_name'));
    await waitFor(() => expect(reqParams().get('ordering')).toBe('composer__full_name'));
    expect(reqParams().get('search')).toBe('tarrega');
  });

  it('drops manual sort when the search term changes', async () => {
    const { wrapper, location } = makeHarness(['/works?sort=composer__full_name']);
    const { result } = renderHook(() => useServerTable(config), { wrapper });
    await waitFor(() => expect(lastRequestUrl()).toBeDefined());

    act(() => result.current.setSearchInput('sor'));
    await waitFor(() => expect(urlParams(location.search).get('q')).toBe('sor'));
    expect(urlParams(location.search).get('sort')).toBeNull();
  });

  it('writes filters to the URL, resets the page, and clears them', async () => {
    const { wrapper, location } = makeHarness(['/works?page=4']);
    const { result } = renderHook(() => useServerTable(config), { wrapper });
    await waitFor(() => expect(lastRequestUrl()).toBeDefined());

    act(() => result.current.setInstrumentation('Guitar solo'));
    await waitFor(() =>
      expect(urlParams(location.search).get('inst')).toBe('Guitar solo'),
    );
    expect(urlParams(location.search).get('page')).toBeNull();

    act(() => result.current.setCountry('Spain'));
    await waitFor(() => expect(urlParams(location.search).get('country')).toBe('Spain'));

    act(() => result.current.clearFilters());
    await waitFor(() => expect(urlParams(location.search).get('inst')).toBeNull());
    expect(urlParams(location.search).get('country')).toBeNull();
  });

  it('reproduces a shared URL: parses state and maps filters to backend params', async () => {
    const { wrapper } = makeHarness([
      '/works?q=sor&inst=Guitar%20solo&country=Spain&ymin=1800&ymax=1900&sort=-composer__full_name&page=2',
    ]);
    const { result } = renderHook(() => useServerTable(config), { wrapper });
    await waitFor(() => expect(lastRequestUrl()).toBeDefined());

    // Outgoing request carries the mapped backend params.
    expect(reqParams().get('search')).toBe('sor');
    expect(reqParams().get('page')).toBe('2');
    expect(reqParams().get('ordering')).toBe('-composer__full_name'); // manual sort present
    expect(reqParams().get('instrumentation')).toBe('Guitar solo');
    expect(reqParams().get('country_name')).toBe('Spain');
    expect(reqParams().get('year_min')).toBe('1800');
    expect(reqParams().get('year_max')).toBe('1900');

    // Hook exposes the parsed selection state.
    expect(result.current.sort).toEqual({ key: 'composer__full_name', dir: 'desc' });
    expect(result.current.filters).toEqual({
      instrumentation: 'Guitar solo',
      country: 'Spain',
      yearRange: [1800, 1900],
    });
    expect(result.current.page).toBe(2);
  });

  it('setPage writes/omits the page param (default 1 omitted)', async () => {
    const { wrapper, location } = makeHarness(['/works']);
    const { result } = renderHook(() => useServerTable(config), { wrapper });
    await waitFor(() => expect(lastRequestUrl()).toBeDefined());

    act(() => result.current.setPage(3));
    await waitFor(() => expect(urlParams(location.search).get('page')).toBe('3'));
    await waitFor(() => expect(reqParams().get('page')).toBe('3'));

    act(() => result.current.setPage(1));
    await waitFor(() => expect(urlParams(location.search).get('page')).toBeNull());
  });

  it('exposes rows and totalCount from the response', async () => {
    const { wrapper } = makeHarness(['/works']);
    const { result } = renderHook(() => useServerTable(config), { wrapper });
    await waitFor(() => expect(result.current.rows.length).toBe(1));
    expect(result.current.totalCount).toBe(1);
    expect(result.current.totalPages).toBe(1);
  });
});
