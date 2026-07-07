import { useState } from 'react';
import api from '../lib/api';
import { ComposerListItem } from '../types';
import { useInstrumentations } from '../hooks/useInstrumentations';
import { useCountries } from '../hooks/useCountries';
import {
  useServerTable,
  TableFilterState,
  DEFAULT_YEAR_MIN,
  DEFAULT_YEAR_MAX,
} from '../hooks/useServerTable';
import Pagination from '../components/ui/Pagination';
import SearchBar from '../components/ui/SearchBar';
import AdvancedFilters from '../components/ui/AdvancedFilters';
import FetchingOverlay from '../components/ui/FetchingOverlay';
import ExpandableComposerRow from '../components/features/composers/ExpandableComposerRow';
import '../styles/shared/ListPage.css';

// Work type for composer's works list (minimal fields)
interface ComposerWork {
  id: number;
  title: string;
  instrumentation_category: {
    id: number;
    name: string;
  } | null;
}

// Map the generic filter state to the /composers/ backend query params. Module-level = stable ref.
export function buildComposerFilterParams(filters: TableFilterState): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (filters.instrumentation) params.instrumentation = filters.instrumentation;
  if (filters.country) params.country_name = filters.country;
  const [min, max] = filters.yearRange;
  if (min !== DEFAULT_YEAR_MIN || max !== DEFAULT_YEAR_MAX) {
    params.birth_year_min = min;
    params.birth_year_max = max;
  }
  return params;
}

// Column header -> backend ordering field
const SORT_FIELDS = {
  name: 'last_name,first_name',
  country: 'country__name',
  birth_year: 'birth_year',
  work_count: 'work_count',
} as const;

export default function ComposerListPage() {
  const instrumentations = useInstrumentations();
  const countries = useCountries();

  const table = useServerTable<ComposerListItem>({
    endpoint: '/composers/',
    queryKey: 'composers',
    defaultOrdering: SORT_FIELDS.name,
    pageSize: 50,
    buildFilterParams: buildComposerFilterParams,
  });

  // Cache loaded works to prevent unnecessary API calls
  const [loadedWorksCache, setLoadedWorksCache] = useState<Record<number, ComposerWork[]>>({});

  const sortArrow = (field: string) =>
    table.sort.key === field ? (table.sort.dir === 'asc' ? ' ↑' : ' ↓') : '';

  const loadComposerWorks = async (composerId: number): Promise<ComposerWork[]> => {
    if (loadedWorksCache[composerId]) {
      return loadedWorksCache[composerId];
    }

    try {
      const response = await api.get(`/composers/${composerId}/works/`);
      const works = response.data.results || response.data;
      setLoadedWorksCache((prev) => ({ ...prev, [composerId]: works }));
      return works;
    } catch (error) {
      console.error('Error loading composer works:', error);
      return [];
    }
  };

  return (
    <div className="list-page">
      <header className="page-header">
        <h1>Composers</h1>
      </header>

      <SearchBar
        value={table.searchInput}
        onChange={table.setSearchInput}
        placeholder="Search for composers..."
      />

      <AdvancedFilters
        yearRangeLabel="Birth Year Range"
        yearRange={table.filters.yearRange}
        onYearRangeChange={table.setYearRange}
        selectedInstrumentation={table.filters.instrumentation}
        onInstrumentationChange={table.setInstrumentation}
        instrumentations={instrumentations}
        selectedCountry={table.filters.country}
        onCountryChange={table.setCountry}
        countries={countries}
        onClearFilters={table.clearFilters}
      />

      <div className="content-area">
        {table.isError && (
          <div className="error-state">
            <p>Failed to load composers. Please try again.</p>
            <button className="btn btn-primary" onClick={() => table.refetch()}>
              Retry
            </button>
          </div>
        )}

        {!table.isError && table.isLoading && (
          <div className="loading-state">
            <p>Loading composers...</p>
          </div>
        )}

        {!table.isError && !table.isLoading && (
          <>
            <FetchingOverlay active={table.isFetching}>
              <div className="composers-table-container">
                <table className="composers-table">
                  <thead>
                    <tr>
                      <th className="sortable" onClick={() => table.onSort(SORT_FIELDS.name)}>
                        Name{sortArrow(SORT_FIELDS.name)}
                      </th>
                      <th className="sortable" onClick={() => table.onSort(SORT_FIELDS.country)}>
                        Country{sortArrow(SORT_FIELDS.country)}
                      </th>
                      <th
                        className="sortable align-center years-column"
                        onClick={() => table.onSort(SORT_FIELDS.birth_year)}
                      >
                        Years{sortArrow(SORT_FIELDS.birth_year)}
                      </th>
                      <th
                        className="sortable align-center works-column"
                        onClick={() => table.onSort(SORT_FIELDS.work_count)}
                      >
                        Works{sortArrow(SORT_FIELDS.work_count)}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.map((composer) => (
                      <ExpandableComposerRow
                        key={composer.id}
                        composer={composer}
                        onLoadWorks={loadComposerWorks}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </FetchingOverlay>

            {table.rows.length === 0 && (
              <div className="empty-state">
                <p>No composers found. Try adjusting your search.</p>
              </div>
            )}

            {table.rows.length > 0 && (
              <Pagination
                currentPage={table.page}
                totalPages={table.totalPages}
                totalCount={table.totalCount}
                onPageChange={table.setPage}
                itemName="composers"
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
