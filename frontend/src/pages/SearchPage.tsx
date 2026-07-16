import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { workService, composerService } from '../lib';
import { useDebounce } from '../hooks/useDebounce';
import SearchBar from '../components/ui/SearchBar';
import '../styles/shared/DetailPage.css';
import './SearchPage.css';

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
    <div className="page page--content">
      <header className="page-header">
        <h1>Search</h1>
      </header>

      <SearchBar
        value={query}
        onChange={setQuery}
        placeholder="Search for works, composers, titles..."
      />

      {isError && (
        <div className="error-state">
          <p>Failed to search. Please try again in a moment.</p>
        </div>
      )}

      {trimmed && isFetching && works.length === 0 && composers.length === 0 ? (
        <p className="loading-state">Searching...</p>
      ) : trimmed ? (
        <>
          <p className="search-results-summary">
            Found {composers.length} composers and {works.length} works
          </p>

          {composers.length > 0 && (
            <section className="detail-section">
              <h2>Composers</h2>
              <div className="card-grid">
                {composers.map((composer) => (
                  <Link
                    key={composer.id}
                    to={`/composers/${composer.id}`}
                    className="work-card"
                  >
                    <h3>{composer.full_name}</h3>
                    <p className="work-card-meta">
                      {[composer.period, composer.country?.name].filter(Boolean).join(' • ') || '—'}
                    </p>
                    <p className="work-card-meta">{composer.work_count} works</p>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {works.length > 0 && (
            <section className="detail-section">
              <h2>Works</h2>
              <div className="card-grid">
                {works.map((work) => (
                  <Link
                    key={work.id}
                    to={`/works/${work.id}`}
                    state={{ from: 'works' }}
                    className="work-card"
                  >
                    <h3>{work.title}</h3>
                    <p className="work-card-meta">
                      by {work.composer ? work.composer.full_name : 'Unknown Composer'}
                    </p>
                    {work.instrumentation_detail && (
                      <p className="work-card-meta">{work.instrumentation_detail}</p>
                    )}
                  </Link>
                ))}
              </div>
            </section>
          )}

          {!isFetching && composers.length === 0 && works.length === 0 && (
            <p className="empty-state">No results found</p>
          )}
        </>
      ) : (
        <p className="empty-state">Enter a search query to find composers and works</p>
      )}

      <Link to="/" className="back-link search-back-link">Back to Home</Link>
    </div>
  );
}
