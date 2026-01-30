import { useState, useEffect, useMemo } from 'react';
import Fuse from 'fuse.js';
import api from '../services/api';
import { useDebounce } from '../hooks/useDebounce';
import { useInstrumentations } from '../hooks/useInstrumentations';
import Pagination from '../components/Pagination';
import ExpandableComposerRow from '../components/ExpandableComposerRow';
import '../styles/shared/ListPage.css';

interface Work {
  id: number;
  title: string;
  instrumentation_category: {
    id: number;
    name: string;
  } | null;
}

interface Composer {
  id: number;
  full_name: string;
  birth_year: number | null;
  death_year: number | null;
  is_living: boolean;
  period: string | null;
  country_name: string | null;
  work_count: number;
}

export default function ComposerListPage() {
  const [composers, setComposers] = useState<Composer[]>([]);
  const [allComposers, setAllComposers] = useState<Composer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [sortColumn, setSortColumn] = useState<'name' | 'country' | 'birth_year' | 'work_count' | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [birthYearRange, setBirthYearRange] = useState<[number, number]>([1400, 2025]);
  const [selectedInstrumentation, setSelectedInstrumentation] = useState<string>('');
  const instrumentations = useInstrumentations();
  const [selectedCountry, setSelectedCountry] = useState<string>('');
  const [countries, setCountries] = useState<string[]>([]);
  const debouncedSearch = useDebounce(searchQuery, 300);
  
  const pageSize = 200;

  // Memoized Fuse instance - only recreate when allComposers changes
  const fuse = useMemo(() => {
    if (allComposers.length === 0) return null;
    return new Fuse<Composer>(allComposers, {
      keys: ['full_name'],
      threshold: 0.4,
      includeScore: true,
      minMatchCharLength: 2,
      ignoreLocation: true,
      distance: 100,
    });
  }, [allComposers]);

  useEffect(() => {
    fetchComposers();
  }, [debouncedSearch, currentPage, birthYearRange, selectedInstrumentation, selectedCountry]);

  // Pre-load all composers in the background for instant fuzzy search
  useEffect(() => {
    const preloadComposers = async () => {
      if (allComposers.length === 0) {
        try {
          const response = await api.get('/composers/', {
            params: { page_size: 20000, ordering: 'last_name,first_name' },
          });
          const loadedComposers = response.data.results || response.data;
          setAllComposers(loadedComposers);
        } catch (err) {
          console.error('Error preloading composers:', err);
        }
      }
    };
    
    // Preload after a short delay to not block initial render
    const timer = setTimeout(preloadComposers, 500);
    return () => clearTimeout(timer);
  }, []);

  // Fetch countries
  useEffect(() => {
    const fetchCountries = async () => {
      try {
        const response = await api.get('/countries/', {
          params: { page_size: 500 }
        });
        const countryList = response.data.results || response.data;
        const countryNames = countryList
          .map((country: any) => country.name)
          .sort((a: string, b: string) => a.localeCompare(b));
        setCountries(countryNames);
      } catch (err) {
        console.error('Error fetching countries:', err);
      }
    };
    fetchCountries();
  }, []);

  const fetchComposers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      if (debouncedSearch) {
        if (allComposers.length > 0 && fuse) {
          // Fast substring search first (works well since data is presorted)
          const searchLower = debouncedSearch.toLowerCase();
          const substringMatches = allComposers.filter(c => 
            c.full_name.toLowerCase().includes(searchLower)
          );
          
          let matches: Composer[];
          if (substringMatches.length > 0) {
            // Use substring matches if found (faster)
            matches = substringMatches;
          } else {
            // Fall back to fuzzy search for typos
            const fuseResults = fuse.search(debouncedSearch);
            matches = fuseResults.map((result) => result.item);
          }
          
          setComposers(matches.slice(0, pageSize));
          setTotalCount(matches.length);
        } else {
          // Fallback: load composers if not preloaded yet
          const response = await api.get('/composers/', {
            params: { page_size: 20000, ordering: 'last_name,first_name' },
          });
          const loadedComposers = response.data.results || response.data;
          setAllComposers(loadedComposers);
        }
      } else {
        // No search query - use regular pagination with filters
        const params: any = {
          page: currentPage,
          page_size: pageSize,
          ordering: 'last_name,first_name',
        };
        
        // Add instrumentation filter if selected
        if (selectedInstrumentation) {
          params.instrumentation = selectedInstrumentation;
        }
        
        // Add country filter if selected
        if (selectedCountry) {
          params.country_name = selectedCountry;
        }
        
        // Add birth year filters if set
        if (birthYearRange[0] > 1400) {
          params.birth_year_min = birthYearRange[0];
        }
        if (birthYearRange[1] < 2025) {
          params.birth_year_max = birthYearRange[1];
        }

        const response = await api.get('/composers/', { params });
        setComposers(response.data.results || response.data);
        setTotalCount(response.data.count || response.data.length);
      }
    } catch (err) {
      console.error('Error fetching composers:', err);
      setError('Failed to load composers. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (column: 'name' | 'country' | 'birth_year' | 'work_count') => {
    if (sortColumn === column) {
      // Toggle direction if same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New column, default to ascending
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  // Apply sorting and advanced filters to displayed composers
  const sortedComposers = useMemo(() => {
    let filtered = composers;
    
    // Apply birth year filter (only when not searching, as search uses allComposers)
    if (!debouncedSearch && (birthYearRange[0] > 1400 || birthYearRange[1] < 2025)) {
      filtered = filtered.filter(c => {
        const birthYear = c.birth_year || c.death_year || 1700;
        return birthYear >= birthYearRange[0] && birthYear <= birthYearRange[1];
      });
    }
    
    if (!sortColumn) return filtered;
    
    const sorted = [...filtered].sort((a, b) => {
      let aVal: any;
      let bVal: any;
      
      switch (sortColumn) {
        case 'name':
          aVal = a.full_name.toLowerCase();
          bVal = b.full_name.toLowerCase();
          break;
        case 'country':
          aVal = a.country_name?.toLowerCase() || '';
          bVal = b.country_name?.toLowerCase() || '';
          break;
        case 'birth_year':
          aVal = a.birth_year || 9999;
          bVal = b.birth_year || 9999;
          break;
        case 'work_count':
          aVal = a.work_count;
          bVal = b.work_count;
          break;
      }
      
      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
    
    return sorted;
  }, [composers, sortColumn, sortDirection, birthYearRange, selectedInstrumentation, selectedCountry, allComposers.length]);

  const loadComposerWorks = async (composerId: number): Promise<Work[]> => {
    try {
      const response = await api.get(`/composers/${composerId}/works/`);
      return response.data.results || response.data;
    } catch (error) {
      console.error('Error loading composer works:', error);
      return [];
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="list-page">
      <header className="page-header">
        <h1>Composers</h1>
        <p>Browse {(totalCount || 0).toLocaleString()} classical guitar composers</p>
      </header>

      {/* Search Bar */}
      <div className="search-container">
        <input
          type="text"
          className="search-input"
          placeholder="Search for composers..."
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
          {/* Birth Year Range Slider */}
          <div className="filter-group">
            <label className="filter-label">
              Birth Year Range: {birthYearRange[0]} - {birthYearRange[1]}
            </label>
            <div className="slider-container">
              <input
                type="range"
                className="range-slider"
                min="1400"
                max="2025"
                value={birthYearRange[0]}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  setBirthYearRange([Math.min(val, birthYearRange[1]), birthYearRange[1]]);
                }}
              />
              <input
                type="range"
                className="range-slider"
                min="1400"
                max="2025"
                value={birthYearRange[1]}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  setBirthYearRange([birthYearRange[0], Math.max(val, birthYearRange[0])]);
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
            <label className="filter-label">Country</label>
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
          <button
            className="clear-filters-button"
            onClick={() => {
              setBirthYearRange([1400, 2025]);
              setSelectedInstrumentation('');
              setSelectedCountry('');
            }}
          >
            Clear Filters
          </button>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="error-state">
          <p>{error}</p>
          <button className="btn btn-primary" onClick={fetchComposers}>
            Retry
          </button>
        </div>
      )}

      {/* Composers List */}
      {!error && !loading && (
        <>
          <div className="composers-table-container">
            <table className="composers-table">
              <thead>
                <tr>
                  <th 
                    className="sortable"
                    onClick={() => handleSort('name')}
                  >
                    Name {sortColumn === 'name' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th 
                    className="sortable"
                    onClick={() => handleSort('country')}
                  >
                    Country {sortColumn === 'country' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th 
                    className="sortable align-center years-column"
                    onClick={() => handleSort('birth_year')}
                  >
                    Years {sortColumn === 'birth_year' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th 
                    className="sortable align-center works-column"
                    onClick={() => handleSort('work_count')}
                  >
                    Works {sortColumn === 'work_count' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedComposers.map((composer) => (
                  <ExpandableComposerRow
                    key={composer.id}
                    composer={composer}
                    onLoadWorks={loadComposerWorks}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {composers.length > 0 && (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              totalCount={totalCount}
              onPageChange={setCurrentPage}
              itemName="composers"
            />
          )}
        </>
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-state">
          <p>Loading composers...</p>
        </div>
      )}

      {/* No Results */}
      {!loading && !error && composers.length === 0 && (
        <div className="empty-state">
          <p>No composers found. Try adjusting your search.</p>
        </div>
      )}
    </div>
  );
}
