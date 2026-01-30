import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { searchService } from '../services';
import { Work, PaginatedResponse } from '../types';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [data, setData] = useState<PaginatedResponse<Work> | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (query) {
      performSearch();
    }
  }, [page, query]);

  const performSearch = async () => {
    setLoading(true);
    try {
      const result = await searchService.search(query, page);
      setData(result);
    } catch (error) {
      console.error('Error searching:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
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

      {loading ? (
        <p>Searching...</p>
      ) : data ? (
        <>
          <p style={{ marginBottom: '1rem', color: '#666' }}>
            Found {data.count} results
          </p>
          <div style={{ display: 'grid', gap: '1rem' }}>
            {data.results.map((work) => (
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
                  <p style={{ margin: '0.25rem 0', color: '#666' }}>
                    by{' '}
                    <Link
                      to={`/composers/${work.composer.id}`}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {work.composer.full_name}
                    </Link>
                  </p>
                  {work.instrumentation_detail && (
                    <p style={{ margin: '0.25rem 0', fontSize: '0.9rem', color: '#888' }}>
                      {work.instrumentation_detail}
                    </p>
                  )}
                </div>
              </Link>
            ))}
          </div>

          {data.count > 50 && (
            <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center', gap: '1rem' }}>
              <button
                onClick={() => setPage(page - 1)}
                disabled={!data.previous}
                style={{ padding: '0.5rem 1rem' }}
              >
                Previous
              </button>
              <span style={{ padding: '0.5rem 1rem' }}>Page {page}</span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={!data.next}
                style={{ padding: '0.5rem 1rem' }}
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : query ? (
        <p>No results found</p>
      ) : (
        <p>Enter a search query to find works</p>
      )}

      <div style={{ marginTop: '2rem' }}>
        <Link to="/">← Back to Home</Link>
      </div>
    </div>
  );
}
