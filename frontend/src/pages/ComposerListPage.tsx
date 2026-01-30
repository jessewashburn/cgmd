import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
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
  const debouncedSearch = useDebounce(searchQuery, 300);
  
  const pageSize = 200;

  // Fuse.js configuration for fuzzy search
  const fuseOptions = {
    keys: ['full_name'], // Only search on full_name since that's what the API provides
    threshold: 0.4, // Lower = stricter (0.0 = exact, 1.0 = match anything) - 0.4 catches typos
    includeScore: true,
    minMatchCharLength: 2,
    ignoreLocation: true,
  };

  useEffect(() => {
    fetchComposers();
  }, [debouncedSearch, currentPage]);

  const fetchComposers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      if (debouncedSearch) {
        // Always use fuzzy search for queries to catch typos
        // Load all composers if not already loaded
        if (allComposers.length === 0) {
          const response = await api.get('/composers/', {
            params: { page_size: 20000, ordering: 'last_name,first_name' },
          });
          const loadedComposers = response.data.results || response.data;
          setAllComposers(loadedComposers);
          
          // Perform fuzzy search
          const fuse = new Fuse<Composer>(loadedComposers, fuseOptions);
          const results = fuse.search(debouncedSearch);
          const matches: Composer[] = results.map((result) => result.item);
          
          setComposers(matches.slice(0, pageSize));
          setTotalCount(matches.length);
        } else {
          // Use already loaded composers for fuzzy search
          const fuse = new Fuse<Composer>(allComposers, fuseOptions);
          const results = fuse.search(debouncedSearch);
          const matches: Composer[] = results.map((result) => result.item);
          
          setComposers(matches.slice(0, pageSize));
          setTotalCount(matches.length);
        }
      } else {
        // No search query - use regular pagination
        const params: any = {
          page: currentPage,
          page_size: pageSize,
          ordering: 'last_name,first_name',
        };

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
      <div style={{ marginBottom: '2rem', maxWidth: '800px', margin: '0 auto 2rem' }}>
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

      {/* Quick Links */}
      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginBottom: '2rem' }}>
        <Link to="/works" style={{ textDecoration: 'none', color: '#4CAF50', fontWeight: '500' }}>
          Browse Works
        </Link>
        <span style={{ color: '#ddd' }}>|</span>
        <Link to="/search" style={{ textDecoration: 'none', color: '#4CAF50', fontWeight: '500' }}>
          Advanced Search
        </Link>
      </div>

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
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600' }}>Name</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600' }}>Period</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600' }}>Country</th>
                  <th style={{ padding: '1rem', textAlign: 'center', fontWeight: '600', width: '150px' }}>
                    Years
                  </th>
                  <th style={{ padding: '1rem', textAlign: 'center', fontWeight: '600', width: '100px' }}>
                    Works
                  </th>
                </tr>
              </thead>
              <tbody>
                {composers.map((composer) => (
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
