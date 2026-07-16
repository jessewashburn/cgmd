import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { WorkListItem } from '../types';
import { useInstrumentations } from '../hooks/useInstrumentations';
import { useCountries } from '../hooks/useCountries';
import { useEraFacets } from '../hooks/useEraFacets';
import { useServerTable } from '../hooks/useServerTable';
import { buildWorkFilterParams } from './filterBuilders';
import DataTable, { Column } from '../components/ui/DataTable';
import Pagination from '../components/ui/Pagination';
import SearchBar from '../components/ui/SearchBar';
import AdvancedFilters from '../components/ui/AdvancedFilters';
import FetchingOverlay from '../components/ui/FetchingOverlay';
import SuggestionButton from '../components/features/SuggestionButton';
import '../styles/shared/ListPage.css';

// Module-level stable reference so the memoized DataTable isn't re-rendered on every keystroke.
const getWorkRowKey = (work: WorkListItem) => work.id;

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
    // Sort by surname then given name, matching the Composers page "Name" column.
    // (composer.full_name is stored "Last, First", so this stays visually consistent.)
    sortKey: 'composer__last_name,composer__first_name',
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

  // Counts exclude the era selection itself — a facet that counted its own filter
  // would show every unpicked era as (0). /works/era_facets/ counts *works*, so the
  // chips agree with the table underneath them.
  const eraFacetParams = useMemo(
    () => buildWorkFilterParams({ ...table.filters, eras: [] }),
    [table.filters],
  );
  const eraFacets = useEraFacets('/works/era_facets/', eraFacetParams);

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
        yearRangeLabel="Year (composer b., else composed)"
        yearRange={table.filters.yearRange}
        onYearRangeChange={table.setYearRange}
        selectedInstrumentation={table.filters.instrumentation}
        onInstrumentationChange={table.setInstrumentation}
        instrumentations={instrumentations}
        selectedCountry={table.filters.country}
        onCountryChange={table.setCountry}
        countries={countries}
        onClearFilters={table.clearFilters}
        eraLabel="Composer Era"
        eraCountNoun="works"
        eras={eraFacets}
        selectedEras={table.filters.eras}
        onEraToggle={table.toggleEra}
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
                getRowKey={getWorkRowKey}
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
