import { useState, useEffect, useMemo } from 'react';
import Fuse from 'fuse.js';
import api from '../services/api';
import { useDebounce } from '../hooks/useDebounce';
import Pagination from '../components/Pagination';
import ExpandableComposerRow from '../components/ExpandableComposerRow';

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
  const [sortColumn, setSortColumn] = useState<'name' | 'period' | 'country' | 'birth_year' | 'work_count' | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [birthYearRange, setBirthYearRange] = useState<[number, number]>([1400, 2025]);
  const [selectedInstrumentation, setSelectedInstrumentation] = useState<string>('');
  const [instrumentations, setInstrumentations] = useState<string[]>([]);
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
  }, [debouncedSearch, currentPage, birthYearRange, selectedInstrumentation]);

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

  // Fetch instrumentation categories
  useEffect(() => {
    const fetchInstrumentations = async () => {
      try {
        const response = await api.get('/instrumentations/', {
          params: { page_size: 500 }
        });
        const categories = response.data.results || response.data;
        
        // Filter for real instrumentation categories (not titles or junk)
        // Common patterns: "guitar", "Guitar", specific ensembles, proper instrumentation terms
        const validInstrumentations = categories
          .map((cat: any) => cat.name)
          .filter((name: string) => {
            if (!name || name.length < 3) return false;
            
            const lower = name.toLowerCase();
            
            // Include if it contains key instrumentation terms
            const hasValidTerms = 
              lower.includes('guitar') ||
              lower.includes('ensemble') ||
              lower.includes('orchestra') ||
              lower.includes('voice') ||
              lower.includes('choir') ||
              lower.includes('percussion') ||
              lower.includes('strings') ||
              lower.includes('wind') ||
              lower.includes('brass') ||
              (lower === 'solo') ||
              (lower === 'duo') ||
              (lower === 'trio') ||
              (lower === 'quartet') ||
              (lower === 'quintet');
            
            // Exclude if it looks like a title (has certain patterns)
            const looksLikeTitle = 
              lower.includes('op.') ||
              lower.includes('for ') ||
              lower.includes(' - ') ||
              lower.includes('bagatelle') ||
              lower.includes('study') ||
              lower.includes('etude') ||
              name.includes('#') ||
              /^\d+$/.test(name) || // Just a number
              name.length > 50; // Too long to be an instrumentation
            
            return hasValidTerms && !looksLikeTitle;
          })
          .sort((a: string, b: string) => a.localeCompare(b));
        
        setInstrumentations(validInstrumentations);
      } catch (err) {
        console.error('Error fetching instrumentations:', err);
      }
    };
    fetchInstrumentations();
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

  const handleSort = (column: 'name' | 'period' | 'country' | 'birth_year' | 'work_count') => {
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
        case 'period':
          aVal = a.period?.toLowerCase() || '';
          bVal = b.period?.toLowerCase() || '';
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
  }, [composers, sortColumn, sortDirection, birthYearRange, selectedInstrumentation, allComposers.length]);

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
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      <header style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>
          Composers
        </h1>
        <p style={{ fontSize: '1rem', color: '#666' }}>
          Browse {(totalCount || 0).toLocaleString()} classical guitar composers
        </p>
      </header>

      {/* Search Bar */}
      <div style={{ marginBottom: '1rem', maxWidth: '800px', margin: '0 auto 1rem' }}>
        <input
          type="text"
          placeholder="Search for composers..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setCurrentPage(1);
          }}
          style={{
            width: '100%',
            padding: '1rem',
            fontSize: '1rem',
            border: '2px solid #ddd',
            borderRadius: '8px',
            outline: 'none',
          }}
          onFocus={(e) => (e.target.style.borderColor = '#4CAF50')}
          onBlur={(e) => (e.target.style.borderColor = '#ddd')}
        />
      </div>

      {/* Advanced Filters Toggle */}
      <div style={{ maxWidth: '800px', margin: '0 auto 1rem', textAlign: 'center' }}>
        <button
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          style={{
            background: 'none',
            border: 'none',
            color: '#4CAF50',
            cursor: 'pointer',
            fontSize: '0.9rem',
            fontWeight: '500',
            padding: '0.5rem',
          }}
        >
          {showAdvancedFilters ? '▲' : '▼'} Advanced Filters
        </button>
      </div>

      {/* Advanced Filters Panel */}
      {showAdvancedFilters && (
        <div
          style={{
            maxWidth: '800px',
            margin: '0 auto 2rem',
            padding: '1.5rem',
            background: '#f9f9f9',
            borderRadius: '8px',
            border: '1px solid #ddd',
          }}
        >
          {/* Birth Year Range Slider */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label
              style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '600',
                color: '#333',
              }}
            >
              Birth Year Range: {birthYearRange[0]} - {birthYearRange[1]}
            </label>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <input
                type="range"
                min="1400"
                max="2025"
                value={birthYearRange[0]}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  setBirthYearRange([Math.min(val, birthYearRange[1]), birthYearRange[1]]);
                }}
                style={{ flex: 1 }}
              />
              <input
                type="range"
                min="1400"
                max="2025"
                value={birthYearRange[1]}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  setBirthYearRange([birthYearRange[0], Math.max(val, birthYearRange[0])]);
                }}
                style={{ flex: 1 }}
              />
            </div>
          </div>

          {/* Instrumentation Dropdown */}
          <div style={{ marginBottom: '1rem' }}>
            <label
              style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '600',
                color: '#333',
              }}
            >
              Instrumentation
            </label>
            <select
              value={selectedInstrumentation}
              onChange={(e) => {
                setSelectedInstrumentation(e.target.value);
                setCurrentPage(1);
              }}
              style={{
                width: '100%',
                padding: '0.75rem',
                fontSize: '1rem',
                border: '2px solid #ddd',
                borderRadius: '8px',
                outline: 'none',
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

          {/* Clear Filters Button */}
          <button
            onClick={() => {
              setBirthYearRange([1400, 2025]);
              setSelectedInstrumentation('');
            }}
            style={{
              padding: '0.5rem 1rem',
              background: '#666',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.9rem',
            }}
          >
            Clear Filters
          </button>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#d32f2f' }}>
          <p>{error}</p>
          <button
            onClick={fetchComposers}
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              background: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Composers List */}
      {!error && !loading && (
        <>
          <div style={{ marginBottom: '2rem', overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                background: 'white',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              }}
            >
              <thead>
                <tr style={{ background: '#f5f5f5', borderBottom: '2px solid #ddd' }}>
                  <th 
                    onClick={() => handleSort('name')}
                    style={{ 
                      padding: '1rem', 
                      textAlign: 'left', 
                      fontWeight: '600',
                      cursor: 'pointer',
                      userSelect: 'none'
                    }}
                  >
                    Name {sortColumn === 'name' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th 
                    onClick={() => handleSort('period')}
                    style={{ 
                      padding: '1rem', 
                      textAlign: 'left', 
                      fontWeight: '600',
                      cursor: 'pointer',
                      userSelect: 'none'
                    }}
                  >
                    Period {sortColumn === 'period' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th 
                    onClick={() => handleSort('country')}
                    style={{ 
                      padding: '1rem', 
                      textAlign: 'left', 
                      fontWeight: '600',
                      cursor: 'pointer',
                      userSelect: 'none'
                    }}
                  >
                    Country {sortColumn === 'country' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th 
                    onClick={() => handleSort('birth_year')}
                    style={{ 
                      padding: '1rem', 
                      textAlign: 'center', 
                      fontWeight: '600', 
                      width: '150px',
                      cursor: 'pointer',
                      userSelect: 'none'
                    }}
                  >
                    Years {sortColumn === 'birth_year' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th 
                    onClick={() => handleSort('work_count')}
                    style={{ 
                      padding: '1rem', 
                      textAlign: 'center', 
                      fontWeight: '600', 
                      width: '100px',
                      cursor: 'pointer',
                      userSelect: 'none'
                    }}
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
        <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
          <p>Loading composers...</p>
        </div>
      )}

      {/* No Results */}
      {!loading && !error && composers.length === 0 && (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
          <p>No composers found. Try adjusting your search.</p>
        </div>
      )}
    </div>
  );
}
