import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { workService, composerService } from '../lib';
import { useDebounce } from '../hooks/useDebounce';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const debouncedQuery = useDebounce(query, 300);
  const trimmed = debouncedQuery.trim();

  // Keep the URL in sync with the (debounced) query so results are shareable/refresh-proof.
  useEffect(() => {
    const current = searchParams.get('q') || '';
    if (trimmed === current) return;
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (trimmed) next.set('q', trimmed);
        else next.delete('q');
        return next;
      },
      { replace: true },
    );
  }, [trimmed, searchParams, setSearchParams]);

  // TanStack Query keys on the term, so out-of-order responses can't clobber newer ones.
  const { data, isFetching, isError } = useQuery({
    queryKey: ['global-search', trimmed],
    queryFn: async () => {
      const [worksResponse, composersResponse] = await Promise.all([
        workService.getAll(1, trimmed),
        composerService.getAll(1, trimmed),
      ]);
      return { works: worksResponse.results, composers: composersResponse.results };
    },
    enabled: trimmed.length > 0,
  });

  const works = data?.works ?? [];
  const composers = data?.composers ?? [];

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '2rem' }}>
        <h1>Search</h1>
        <form onSubmit={(e) => e.preventDefault()} style={{ marginTop: '1rem' }}>
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
        </form>
      </header>

      {isError && (
        <div style={{
          padding: '1rem',
          background: '#fee',
          border: '1px solid #fcc',
          borderRadius: '8px',
          marginBottom: '1rem',
          color: '#c00',
        }}>
          Failed to search. Make sure the backend server is running at http://localhost:8000
        </div>
      )}

      {trimmed && isFetching && works.length === 0 && composers.length === 0 ? (
        <p>Searching...</p>
      ) : trimmed ? (
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

          {!isFetching && composers.length === 0 && works.length === 0 && (
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
