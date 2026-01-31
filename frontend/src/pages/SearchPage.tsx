import { useState, useEffect, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { searchService } from '../lib';
import { Work, Composer } from '../types';
import { useDebounce } from '../hooks/useDebounce';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const debouncedQuery = useDebounce(query, 300); // Wait 300ms after user stops typing
  const [works, setWorks] = useState<Work[]>([]);
  const [composers, setComposers] = useState<Composer[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const searchCounterRef = useRef(0);

  useEffect(() => {
    if (debouncedQuery.trim()) {
      performSearch(debouncedQuery);
    } else {
      setWorks([]);
      setComposers([]);
      setError(null);
      setLoading(false);
    }
  }, [debouncedQuery]);

  const performSearch = async (searchQuery: string) => {
    // Increment counter for this search
    const currentSearchId = ++searchCounterRef.current;
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await searchService.fuzzySearchAll(searchQuery);
      
      // Only update state if this is still the most recent search
      if (currentSearchId === searchCounterRef.current) {
        setWorks(result.works);
        setComposers(result.composers);
        setLoading(false);
      }
    } catch (error) {
      // Only update error state if this is still the most recent search
      if (currentSearchId === searchCounterRef.current) {
        console.error('Error searching:', error);
        setError('Failed to search. Make sure the backend server is running at http://localhost:8000');
        setLoading(false);
      }
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams({ q: query });
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '2rem' }}>
        <h1>Search</h1>
        <form onSubmit={handleSearch} style={{ marginTop: '1rem' }}>
          <input
            type="search"
            placeholder="Search for works, composers, titles..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              width: '100%',
              maxWidth: '600px',
              padding: '0.75rem',
              fontSize: '1rem',
              borderRadius: '4px',
              border: '1px solid #ccc',
            }}
          />
          <button
            type="submit"
            style={{
              marginLeft: '1rem',
              padding: '0.75rem 2rem',
              fontSize: '1rem',
              cursor: 'pointer',
            }}
          >
            Search
          </button>
        </form>
      </header>

      {error && (
        <div style={{
          padding: '1rem',
          background: '#fee',
          border: '1px solid #fcc',
          borderRadius: '8px',
          marginBottom: '1rem',
          color: '#c00',
        }}>
          {error}
        </div>
      )}

      {loading ? (
        <p>Searching... (Loading initial results)</p>
      ) : query ? (
        <>
          <p style={{ marginBottom: '1rem', color: '#666' }}>
            Found {composers.length} composers and {works.length} works
          </p>

          {composers.length > 0 && (
            <section style={{ marginBottom: '2rem' }}>
              <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>Composers</h2>
              <div style={{ display: 'grid', gap: '1rem' }}>
                {composers.map((composer) => (
                  <Link
                    key={composer.id}
                    to={`/composers/${composer.id}`}
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
                    <div style={{
                      padding: '1rem',
                      background: '#e8f4f8',
                      borderRadius: '8px',
                      cursor: 'pointer',
                    }}>
                      <h3 style={{ margin: '0 0 0.5rem 0' }}>{composer.full_name}</h3>
                      <p style={{ margin: '0.25rem 0', color: '#666' }}>
                        {composer.period} {composer.country && `• ${composer.country.name}`}
                      </p>
                      <p style={{ margin: '0.25rem 0', color: '#666', fontSize: '0.9rem' }}>
                        {composer.work_count} works
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {works.length > 0 && (
            <section>
              <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>Works</h2>
              <div style={{ display: 'grid', gap: '1rem' }}>
                {works.map((work) => (
                  <Link
                    key={work.id}
                    to={`/works/${work.id}`}
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
                <div style={{
                  padding: '1rem',
                  background: '#f5f5f5',
                  borderRadius: '8px',
                  cursor: 'pointer',
                }}>
                  <h3 style={{ margin: '0 0 0.5rem 0' }}>{work.title}</h3>
                  {work.composer ? (
                    <p style={{ margin: '0.25rem 0', color: '#666' }}>
                      by{' '}
                      <Link
                        to={`/composers/${work.composer.id}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        {work.composer.full_name}
                      </Link>
                    </p>
                  ) : (
                    <p style={{ margin: '0.25rem 0', color: '#666' }}>
                      by Unknown Composer
                    </p>
                  )}
                  {work.instrumentation_detail && (
                    <p style={{ margin: '0.25rem 0', fontSize: '0.9rem', color: '#888' }}>
                      {work.instrumentation_detail}
                    </p>
                  )}
                </div>
              </Link>
            ))}
              </div>
            </section>
          )}

          {composers.length === 0 && works.length === 0 && (
            <p>No results found</p>
          )}
        </>
      ) : (
        <p>Enter a search query to find composers and works</p>
      )}

      <div style={{ marginTop: '2rem' }}>
        <Link to="/">← Back to Home</Link>
      </div>
    </div>
  );
}
