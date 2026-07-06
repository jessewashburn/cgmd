# SDD — Frontend Data-Table Improvements

**Status:** Implemented 2026-07-06 (design sections below reconciled to as-built; see [As-built notes & deviations](#as-built-notes--deviations)).
**Author:** (generated for review by Jesse Washburn)
**Date:** 2026-07-06
**Scope:** Frontend only (`frontend/src`). No backend/API changes required — the Django trigram search, ordering, and pagination contract stay as-is.

## Overview

The app's list views ([WorkListPage](../frontend/src/pages/WorkListPage.tsx), [ComposerListPage](../frontend/src/pages/ComposerListPage.tsx)) are a **server-side** ("Fork B") data table: sort, filter, search, and page are all sent to Django as query params, and one page of results comes back with a total `count`. The backend half of this is strong — indexed PostgreSQL trigram fuzzy search with weighted ranking and a SQLite fallback ([TrigramSearchFilter](../music/views.py#L27-L123), [migration 0004](../music/migrations/0004_add_trigram_search.py)).

The **frontend** half has gaps typical of a hand-rolled `axios` + `useEffect` + `useState` data layer. This SDD collects the improvements into one plan:

| # | Improvement | Fixes | Effort |
|---|-------------|-------|--------|
| 1 | Adopt TanStack Query for list data | Search races, no caching, no dedup, empty-flash on paging | M |
| 2 | URL-based state (`useSearchParams`) | Views not shareable / refresh-proof / back-button friendly | M |
| 3 | Config-driven sorting (`sortable` on `Column<T>`) | Sort re-implemented per page in header JSX | S |
| 4 | Extract a `useServerTable` hook | WorkList/ComposerList orchestration duplicated | M |
| 5 | Delete dead `fuzzySearch.ts` (Fuse.js) | Redundant client-side search superseded by trigram | XS |

Improvement 1 subsumes two things I'd otherwise list separately — the **race-condition fix** on the table pages and **`keepPreviousData` smooth pagination** — so they're folded into it rather than given their own rows.

## Motivation / current state

### What works today
- **Correct fork.** Server-side is the right call for a works/composers DB that can grow unbounded.
- **Debounced search.** [useDebounce](../frontend/src/hooks/useDebounce.ts), currently tuned per page (500ms works, 150ms composers) — to be standardized to 300ms (decision 2).
- **Page reset on filter/search/sort change.** `setCurrentPage(1)` is called in every mutation path ([WorkListPage.tsx:200](../frontend/src/pages/WorkListPage.tsx#L200), [:212-219](../frontend/src/pages/WorkListPage.tsx#L212-L219), [:71](../frontend/src/pages/WorkListPage.tsx#L71)) — the easy-to-forget failure mode is handled.
- **Config-driven cells.** [`Column<T>`](../frontend/src/components/ui/DataTable/DataTable.tsx#L4-L9) with an `accessor` that is either a field key or a render function — the reusability mechanism is present.
- **Race guard exists — in one place.** [SearchPage](../frontend/src/pages/SearchPage.tsx#L15-L55) uses a `searchCounterRef` to discard stale out-of-order responses.

### Gaps
1. **Search races on the table pages.** [WorkListPage](../frontend/src/pages/WorkListPage.tsx#L125-L186) and [ComposerListPage](../frontend/src/pages/ComposerListPage.tsx) fetch in a `useEffect` with **no** `AbortController` and **no** counter guard. Fast typing can let an earlier response overwrite a newer one. (SearchPage solved this; the tables didn't inherit the fix.)
2. **No caching / dedup / stale-while-revalidate.** Every sort/filter/page is a fresh round trip. Paging 2 → 1 refetches page 1.
3. **Empty-flash on paging.** A hand-rolled `sortLoading` absolute-positioned spinner overlay ([WorkListPage.tsx:238-263](../frontend/src/pages/WorkListPage.tsx#L238-L263)) keeps the table visible during *sorts* only; a page change falls back to `loading`, which unmounts the table and flashes empty.
4. **No URL persistence on tables.** All selections are `useState`; refresh/back/share all lose the view. Only SearchPage persists `?q=`, and only on form submit ([SearchPage.tsx:60](../frontend/src/pages/SearchPage.tsx#L60)).
5. **Sorting is not config-driven.** Each page hand-builds a `<span onClick={...}>Header ↑/↓</span>` per column ([WorkListPage.tsx:76-122](../frontend/src/pages/WorkListPage.tsx#L76-L122)). `DataTable` itself has no sort awareness.
6. **Per-page orchestration is duplicated.** WorkList and ComposerList repeat ~10 state hooks, `handleColumnSort`, the fetch-with-params, and pagination math.
7. **Dead code.** [fuzzySearch.ts](../frontend/src/lib/fuzzySearch.ts) (Fuse.js) is a second, client-side fuzzy search that no page imports — superseded by the server-side trigram search.

## Goals / non-goals

**Goals**
- Eliminate the table-page search race.
- Make list views shareable, refresh-proof, and back-button friendly.
- Make sorting a property of the column config, owned by `DataTable`.
- Collapse the two list pages onto one shared data/state layer.
- Remove dead code.

**Non-goals**
- No backend/API contract changes.
- No switch to client-side ("Fork A") processing — server-side stays.
- No virtualization / infinite scroll (separate future item).
- No visual redesign of the table beyond what sorting/loading states require.

## Proposed design

### 1. Adopt TanStack Query for list data

Add `@tanstack/react-query`, wrap the app in a `QueryClientProvider` (in [main.tsx](../frontend/src/main.tsx)), and replace the manual `works`/`totalCount`/`loading`/`error` state + `fetchWorks` effect with a keyed query.

```ts
// The selections become the query key; the params object mirrors today's fetchWorks.
const { data, isFetching, isLoading, error } = useQuery({
  queryKey: ['works', { search, ordering, page, filters }],
  queryFn: () => fetchWorks({ search, ordering, page, filters }), // same axios call, extracted
  placeholderData: keepPreviousData, // keep the current page visible while the next loads
});
const works = data?.results ?? [];
const totalCount = data?.count ?? 0;
```

What this buys (and what it deletes):
- **Race safety for free** — each in-flight request is tied to its key; a stale response for an old key can't commit. Removes the need to port `searchCounterRef` to the tables. *(Gap 1)*
- **Per-combination caching + dedup** — paging back is instant from cache. *(Gap 2)*
- **`keepPreviousData`** replaces the hand-rolled `sortLoading` overlay; `isFetching` drives a subtle dim/top-loader while rows stay on screen. Delete ~25 lines of inline-styled JSX. *(Gap 3)*

The `axios` instance ([lib/api.ts](../frontend/src/lib/api.ts)) is unchanged — TanStack Query wraps it, it doesn't replace it.

### 2. URL-based state (`useSearchParams`)

Move the selections out of `useState` and into the URL as the source of truth. Read initial state from the URL on mount; every change writes back via `setSearchParams`.

As-built URL (short param names to limit sprawl):

```
/works?q=tarrega&sort=-composer__full_name&page=3&inst=Guitar%20solo&country=Spain&ymin=1800&ymax=1900
```

- Source of truth: `useSearchParams()` from react-router (already a dependency).
- **All selections live in the URL** — `q` (search), `sort` (signed backend ordering field), `page`, and every filter: `inst`, `country`, `ymin`/`ymax` — per resolved decision 1, so a shared link reproduces the full view.
- Parse/serialize is folded into `useServerTable` (no separate `useTableParams` helper — the hook *is* the source of truth). Params at their default value are **omitted** from the URL (a bare `/works` = defaults).
- The `sort` param carries the raw backend ordering string (e.g. `-last_name,first_name`); presence of `sort` ⇒ manual sort.
- The TanStack Query key (Improvement 1) reads from these params, so URL → query is automatic.
- Fixes shareable / refresh-proof / back-button. *(Gap 4)*

This also cleans up SearchPage's drift (URL only written on submit) by making the URL the live source there too.

### 3. Config-driven sorting

Extend `Column<T>` and move sort rendering into [DataTable](../frontend/src/components/ui/DataTable/DataTable.tsx). Sorting becomes a declared property, not per-page header JSX.

```ts
export interface Column<T> {
  header: string | ReactNode;
  accessor: keyof T | ((row: T) => ReactNode);
  sortKey?: string;          // NEW: backend ordering field; presence ⇒ sortable
  width?: string;
  align?: 'left' | 'center' | 'right';
}

// DataTable gains optional sort props:
interface DataTableProps<T> {
  // ...existing...
  sort?: { key: string; dir: 'asc' | 'desc' } | null;
  onSort?: (key: string) => void;   // DataTable renders the ↑/↓ and wires onClick
}
```

`DataTable` renders the clickable header + arrow + `aria-sort` only where `sortKey` is set. The page passes `sort`/`onSort`; the column→backend-field map (`title → title_sort_key`, etc., currently inline at [WorkListPage.tsx:60-64](../frontend/src/pages/WorkListPage.tsx#L60-L64)) moves into the column definitions as `sortKey`. *(Gap 5)*

### 4. Extract `useServerTable`

Collapse the duplicated orchestration into one hook that owns the whole server-table lifecycle:

As-built signature (columns stay with the page/`DataTable`, not the hook; filter param-name differences between endpoints are handled by a `buildFilterParams` function rather than a declarative `filterSchema`):

```ts
const table = useServerTable<WorkListItem>({
  endpoint: '/works/',
  queryKey: 'works',
  defaultOrdering: 'title_sort_key',
  pageSize: 50,
  buildFilterParams,   // (TableFilterState) => backend params; module-level, stable ref
});
// table.rows, table.totalCount, table.totalPages, table.page, table.setPage,
// table.searchInput, table.setSearchInput, table.sort, table.onSort,
// table.filters, table.setInstrumentation/setCountry/setYearRange/clearFilters,
// table.isLoading, table.isFetching, table.isError, table.refetch
```

Internally it composes Improvements 1–3 (query keyed on params, URL sync, sort state). WorkListPage and ComposerListPage shrink to: a `columns`/header array, a `buildFilterParams` function, and JSX. *(Gap 6)*

Ordering nuance to preserve: today, when a search term is present and the user hasn't manually sorted, the backend uses relevance ranking and the frontend sends **no** `ordering` param ([WorkListPage.tsx:165-170](../frontend/src/pages/WorkListPage.tsx#L165-L170)). `useServerTable` must keep this "search-relevance vs. manual-sort" rule.

### 5. Delete dead `fuzzySearch.ts`

Remove [fuzzySearch.ts](../frontend/src/lib/fuzzySearch.ts) and its barrel export in [lib/index.ts](../frontend/src/lib/index.ts). Drop the `fuse.js` dependency from [package.json](../frontend/package.json). It's a redundant client-side search superseded by the server-side trigram search. *(Gap 7)* — verify no remaining imports before deleting.

## Phasing

Ordered by dependency and value. Each phase ships independently.

| Phase | Deliverable | Depends on | Notes |
|-------|-------------|------------|-------|
| 0 | Delete `fuzzySearch.ts` + `fuse.js` dep | — | Trivial cleanup; do first. |
| 1 | TanStack Query on WorkListPage | — | Highest value: kills the race, adds caching, removes the overlay. Prove the pattern on one page. |
| 2 | Config-driven sorting in `DataTable` | — | Independent; can land in parallel with 1. |
| 3 | URL state on WorkListPage | 1 | Query key reads from URL params. |
| 4 | Extract `useServerTable`; migrate ComposerListPage | 1–3 | Generalize once the pattern is proven on Works. |
| 5 | Converge SearchPage onto the shared hook/URL model | 4 | Committed (decision 3); removes the last bespoke fetch loop and its `searchCounterRef`. |

## Risks & mitigations

- **Behavior regressions in the search-relevance vs. manual-sort logic** — it's subtle and currently works. *Mitigation:* pin it down with explicit test cases before refactoring (browse order, search order, search-then-sort, sort-then-search).
- **Bundle size** — TanStack Query adds ~12–15KB gz. *Mitigation:* acceptable; it deletes hand-rolled state and the Fuse.js dep offsets part of it.
- **URL param sprawl** — long, ugly URLs. *Mitigation:* omit params at their defaults when serializing.
- **Back-button + query cache interaction** — ensure a Back navigation restores both URL and results from cache without a flash. *Mitigation:* covered by `keepPreviousData` + cache; verify in the test pass.

## Testing / verification

Status after implementation: `tsc --noEmit` clean, `npm run build` green, `npm run lint` adds no new errors, and the Django API was driven for all param combinations the hook emits (dataset: 73,111 works / 15,082 composers).

- ✅ **Sort:** backend accepts every emitted `ordering` (`title_sort_key`, `-composer__full_name`, `instrumentation_category__name`, `last_name,first_name`, `work_count`, …) → HTTP 200 with correct counts.
- ✅ **Search relevance:** `search=tarrega` (no `ordering`) → 25 works ranked non-alphabetically; manual `ordering` overrides. Verified at the API layer.
- ✅ **Filters:** `composer_country`/`composer_birth_year_*` and `country_name`/`birth_year_*` return expected non-empty counts.
- ✅ **Fallback:** the local drive ran against `db.sqlite3`, exercising the non-PostgreSQL ILIKE ranking path.
- ⏳ **Race / paging / share-refresh / back-button:** logic is covered by build + API contract, but the *interaction* behaviors were **not** browser-driven (no browser tool in the implementation environment). Recommended manual pass: fast-type search (no stale flicker), page forward/back (rows stay on screen), copy a filtered+sorted URL into a new tab (identical view), F5 (preserved).

## As-built notes & deviations

Design choices that differ from the literal proposal above (all intentional):

1. **Sorting owned by `DataTable` — Works only.** WorkListPage uses the config-driven `DataTable` (`sortKey` + `sort`/`onSort`). ComposerListPage renders a custom table (it needs `ExpandableComposerRow`), so its sort is **hook-driven** (`table.onSort`, `table.sort`) but still hand-rendered per `<th>`. Goal met functionally; the header markup is not `DataTable`-owned there.
2. **Short URL param names.** `q`/`sort`/`inst`/`country`/`ymin`/`ymax` instead of the illustrative `search`/`ordering`/`instrumentation`. The `sort` value is the raw backend ordering field, so shareable URLs expose ORM field names (e.g. `sort=-composer__full_name`) — acceptable for an internal tool; revisit if URLs become user-facing.
3. **No standalone `useTableParams`.** URL parse/serialize lives inside `useServerTable`.
4. **Hook takes `buildFilterParams`, not `columns`/`filterSchema`.** Columns are a rendering concern (they stay with the page/`DataTable`); the per-endpoint filter param-name differences are expressed as a small function.
5. **ComposerListPage now shows a default ↑ arrow on "Name"** (sort is always derived from `defaultOrdering`). Previously no arrow showed until first click. Cosmetic, and consistent with WorkListPage's long-standing default-sort arrow.
6. **Additions beyond the SDD:** a `QueryClient` with sane defaults (`staleTime: 30s`, `refetchOnWindowFocus: false`, `retry: 1`) in `main.tsx`; a reusable `FetchingOverlay` component (the SDD only called for deleting the old overlay). Also removed the newly-orphaned `useSort.ts` / `useFilters.ts` hooks.

## Resolved decisions

1. **All selections go in the URL** — sort, search, page, **and** every filter (year range, instrumentation, country). A shared view reproduces the full state. Reflected in Improvement 2 below.
2. **Standardize the debounce** to a single value (**300ms**) across all pages, replacing the current 500ms (works) / 150ms (composers) split. TanStack Query lowers the cost of an extra request (dedup + cache), so a uniform, snappier debounce is fine. Applies to `useServerTable` and SearchPage.
3. **Converge SearchPage** onto the shared `useServerTable` / URL model — Phase 5 is committed, not optional.
