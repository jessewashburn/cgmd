import { Link } from 'react-router-dom';
import { WorkListItem } from '../types';
import { useInstrumentations } from '../hooks/useInstrumentations';
import { useCountries } from '../hooks/useCountries';
import {
  useServerTable,
  TableFilterState,
  DEFAULT_YEAR_MIN,
  DEFAULT_YEAR_MAX,
} from '../hooks/useServerTable';
import DataTable, { Column } from '../components/ui/DataTable';
import Pagination from '../components/ui/Pagination';
import SearchBar from '../components/ui/SearchBar';
import AdvancedFilters from '../components/ui/AdvancedFilters';
import FetchingOverlay from '../components/ui/FetchingOverlay';
import SuggestionButton from '../components/features/SuggestionButton';
import '../styles/shared/ListPage.css';

// Map the generic filter state to the /works/ backend query params.
// Module-level so the reference is stable across renders.
function buildWorkFilterParams(filters: TableFilterState): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (filters.instrumentation) params.instrumentation = filters.instrumentation;
  if (filters.country) params.composer_country = filters.country;
  const [min, max] = filters.yearRange;
  if (min !== DEFAULT_YEAR_MIN || max !== DEFAULT_YEAR_MAX) {
    params.composer_birth_year_min = min;
    params.composer_birth_year_max = max;
  }
  return params;
}

const columns: Column<WorkListItem>[] = [
  {
    header: 'Work Title',
    sortKey: 'title_sort_key',
    accessor: (work) => (
      <>
        <Link to={`/works/${work.id}`} state={{ from: 'works' }} className="link-primary">
          {work.title}
        </Link>
        {' '}
        <SuggestionButton itemType="work" itemData={work} />
      </>
    ),
  },
  {
    header: 'Composer',
    sortKey: 'composer__full_name',
    accessor: (work) =>
      work.composer ? (
        <Link to={`/composers/${work.composer.id}`} className="link-secondary">
          {work.composer.full_name}
        </Link>
      ) : (
        '-'
      ),
  },
  {
    header: 'Instrumentation',
    sortKey: 'instrumentation_category__name',
    accessor: (work) => work.instrumentation_category?.name || '-',
  },
];

export default function WorkListPage() {
  const instrumentations = useInstrumentations();
  const countries = useCountries();

  const table = useServerTable<WorkListItem>({
    endpoint: '/works/',
    queryKey: 'works',
    defaultOrdering: 'title_sort_key',
    pageSize: 50,
    buildFilterParams: buildWorkFilterParams,
  });

  return (
    <div className="list-page">
      <header className="page-header">
        <h1>Works</h1>
      </header>

      <SearchBar
        value={table.searchInput}
        onChange={table.setSearchInput}
        placeholder="Search for works or composers..."
      />

      <AdvancedFilters
        yearRangeLabel="Composer Dates Range"
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
            <p>Failed to load works. Please try again.</p>
            <button className="btn btn-primary" onClick={() => table.refetch()}>
              Retry
            </button>
          </div>
        )}

        {!table.isError && table.isLoading && (
          <div className="loading-state">
            <p>Loading works...</p>
          </div>
        )}

        {!table.isError && !table.isLoading && (
          <>
            <FetchingOverlay active={table.isFetching}>
              <DataTable
                data={table.rows}
                columns={columns}
                getRowKey={(work) => work.id}
                sort={table.sort}
                onSort={table.onSort}
                emptyMessage="No works found. Try adjusting your search."
              />
            </FetchingOverlay>

            {table.rows.length > 0 && (
              <Pagination
                currentPage={table.page}
                totalPages={table.totalPages}
                totalCount={table.totalCount}
                onPageChange={table.setPage}
                itemName="total works"
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
