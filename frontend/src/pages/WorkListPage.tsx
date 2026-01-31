import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useDebounce } from '../hooks/useDebounce';
import { useInstrumentations } from '../hooks/useInstrumentations';
import { useCountries } from '../hooks/useCountries';
import { useSort } from '../hooks/useSort';
import { stripLeadingSymbols } from '../utils/fuzzySearch';
import DataTable, { Column } from '../components/DataTable';
import Pagination from '../components/Pagination';
import '../styles/shared/ListPage.css';

interface Work {
  id: number;
  title: string;
  composer: {
    id: number;
    full_name: string;
  } | null;
  instrumentation_category: {
    id: number;
    name: string;
  } | null;
  difficulty_level: number | null;
  composition_year: number | null;
}

export default function WorkListPage() {
  const [works, setWorks] = useState<Work[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const { sortColumn, sortDirection, handleSort } = useSort<'title' | 'composer' | 'instrumentation'>();
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [compositionYearRange, setCompositionYearRange] = useState<[number, number]>([1400, 2025]);
  const [selectedInstrumentation, setSelectedInstrumentation] = useState<string>('');
  const instrumentations = useInstrumentations();
  const [selectedCountry, setSelectedCountry] = useState<string>('');
  const countries = useCountries();
  const debouncedSearch = useDebounce(searchQuery, 300);
  
  const pageSize = 200;

  const clearFilters = () => {
    setCompositionYearRange([1400, 2025]);
    setSelectedInstrumentation('');
    setSelectedCountry('');
  };

  // Apply sorting to displayed works
  const sortedWorks = useMemo(() => {
    if (!sortColumn) return works;
    
    const sorted = [...works].sort((a, b) => {
      let aVal: string;
      let bVal: string;
      
      switch (sortColumn) {
        case 'title':
          aVal = stripLeadingSymbols(a.title.toLowerCase());
          bVal = stripLeadingSymbols(b.title.toLowerCase());
          break;
        case 'composer':
          aVal = a.composer?.full_name.toLowerCase() || '';
          bVal = b.composer?.full_name.toLowerCase() || '';
          break;
        case 'instrumentation':
          aVal = a.instrumentation_category?.name.toLowerCase() || '';
          bVal = b.instrumentation_category?.name.toLowerCase() || '';
          break;
        default:
          return 0;
      }
      
      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
    
    return sorted;
  }, [works, sortColumn, sortDirection]);

  const columns: Column<Work>[] = [
    {
      header: (
        <span 
          onClick={() => handleSort('title')} 
          className="sort-header"
        >
          Work Title {sortColumn === 'title' && (sortDirection === 'asc' ? '↑' : '↓')}
        </span>
      ),
      accessor: (work) => (
        <Link to={`/works/${work.id}`} className="link-primary">
          {work.title}
        </Link>
      ),
    },
    {
      header: (
        <span 
          onClick={() => handleSort('composer')} 
          className="sort-header"
        >
          Composer {sortColumn === 'composer' && (sortDirection === 'asc' ? '↑' : '↓')}
        </span>
      ),
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
      header: (
        <span 
          onClick={() => handleSort('instrumentation')} 
          className="sort-header"
        >
          Instrumentation {sortColumn === 'instrumentation' && (sortDirection === 'asc' ? '↑' : '↓')}
        </span>
      ),
      accessor: (work) => work.instrumentation_category?.name || '-',
    },
  ];

  useEffect(() => {
    fetchWorks();
  }, [debouncedSearch, currentPage, compositionYearRange, selectedInstrumentation, selectedCountry]);

  const fetchWorks = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params: any = {
        page: currentPage,
        page_size: pageSize,
        ordering: 'title',
      };

      if (debouncedSearch) {
        params.search = debouncedSearch;
      }

      // Add instrumentation filter if selected
      if (selectedInstrumentation) {
        params.instrumentation = selectedInstrumentation;
      }

      // Add country filter if selected
      if (selectedCountry) {
        params.composer_country = selectedCountry;
      }

      // Add composition year filters if set
      if (compositionYearRange[0] > 1400) {
        params.composition_year_min = compositionYearRange[0];
      }
      if (compositionYearRange[1] < 2025) {
        params.composition_year_max = compositionYearRange[1];
      }

      const response = await api.get('/works/', { params });
      setWorks(response.data.results || response.data);
      setTotalCount(response.data.count || response.data.length);
    } catch (err) {
      console.error('Error fetching works:', err);
      setError('Failed to load works. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="list-page">
      <header className="page-header">
        <h1>Classical Guitar Music Database</h1>
        <p>Browse {loading && totalCount === 0 ? '...' : totalCount.toLocaleString()} guitar works</p>
      </header>

      {/* Search Bar */}
      <div className="search-container">
        <input
          type="text"
          className="search-input"
          placeholder="Search for works or composers..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setCurrentPage(1);
          }}
        />
      </div>

      {/* Advanced Filters Toggle */}
      <div className="advanced-filters-toggle">
        <button
          className="toggle-button"
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
        >
          {showAdvancedFilters ? '▲' : '▼'} Advanced Filters
        </button>
      </div>

      {/* Advanced Filters Panel */}
      {showAdvancedFilters && (
        <div className="advanced-filters-panel">
          {/* Composition Year Range Slider */}
          <div className="filter-group">
            <label className="filter-label">
              Composition Year Range: {compositionYearRange[0]} - {compositionYearRange[1]}
            </label>
            <div className="slider-container">
              <input
                type="range"
                className="range-slider"
                min="1400"
                max="2025"
                value={compositionYearRange[0]}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  setCompositionYearRange([Math.min(val, compositionYearRange[1]), compositionYearRange[1]]);
                }}
              />
              <input
                type="range"
                className="range-slider"
                min="1400"
                max="2025"
                value={compositionYearRange[1]}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  setCompositionYearRange([compositionYearRange[0], Math.max(val, compositionYearRange[0])]);
                }}
              />
            </div>
          </div>

          {/* Instrumentation Dropdown */}
          <div className="filter-group">
            <label className="filter-label">Instrumentation</label>
            <select
              className="filter-select"
              value={selectedInstrumentation}
              onChange={(e) => {
                setSelectedInstrumentation(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">All Instrumentations</option>
              {instrumentations.map((inst) => (
                <option key={inst} value={inst}>
                  {inst}
                </option>
              ))}
            </select>
          </div>

          {/* Country Dropdown */}
          <div className="filter-group">
            <label className="filter-label">Composer Country</label>
            <select
              className="filter-select"
              value={selectedCountry}
              onChange={(e) => {
                setSelectedCountry(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">All Countries</option>
              {countries.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </div>

          {/* Clear Filters Button */}
          <button className="clear-filters-button" onClick={clearFilters}>
            Clear Filters
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-state">
          <p>Loading works...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="error-state">
          <p>{error}</p>
          <button className="btn btn-primary" onClick={fetchWorks}>
            Retry
          </button>
        </div>
      )}

      {/* Works List */}
      {!error && (
        <>
          <DataTable
            data={sortedWorks}
            columns={columns}
            getRowKey={(work) => work.id}
            loading={loading}
            emptyMessage="No works found. Try adjusting your search."
          />

          {!loading && works.length > 0 && (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              totalCount={totalCount}
              onPageChange={setCurrentPage}
              itemName="total works"
            />
          )}
        </>
      )}
    </div>
  );
}
