import { useState, useEffect, useMemo } from 'react';
import Fuse from 'fuse.js';
import api from '../services/api';
import { useDebounce } from '../hooks/useDebounce';
import { useInstrumentations } from '../hooks/useInstrumentations';
import { useCountries } from '../hooks/useCountries';
import { useSort } from '../hooks/useSort';
import { useFilters } from '../hooks/useFilters';
import Pagination from '../components/Pagination';
import SearchBar from '../components/SearchBar';
import AdvancedFilters from '../components/AdvancedFilters';
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
  const { sortColumn, sortDirection, handleSort } = useSort<'name' | 'country' | 'birth_year' | 'work_count'>();
  const {
    yearRange: birthYearRange,
    setYearRange: setBirthYearRange,
    selectedInstrumentation,
    setSelectedInstrumentation,
    selectedCountry,
    setSelectedCountry,
    clearFilters,
  } = useFilters();
  const instrumentations = useInstrumentations();
  const countries = useCountries();
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
        <p>Browse {loading && totalCount === 0 ? '...' : totalCount.toLocaleString()} classical guitar composers</p>
      </header>

      <SearchBar
        value={searchQuery}
        onChange={(value) => {
          setSearchQuery(value);
          setCurrentPage(1);
        }}
        placeholder="Search for composers..."
      />

      <AdvancedFilters
        yearRangeLabel="Birth Year Range"
        yearRange={birthYearRange}
        onYearRangeChange={setBirthYearRange}
        selectedInstrumentation={selectedInstrumentation}
        onInstrumentationChange={(value) => {
          setSelectedInstrumentation(value);
          setCurrentPage(1);
        }}
        instrumentations={instrumentations}
        selectedCountry={selectedCountry}
        onCountryChange={(value) => {
          setSelectedCountry(value);
          setCurrentPage(1);
        }}
        countries={countries}
        onClearFilters={clearFilters}
      />

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
