import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { composerService } from '../services';
import { Composer, PaginatedResponse } from '../types';

export default function ComposerListPage() {
  const [data, setData] = useState<PaginatedResponse<Composer> | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    loadComposers();
  }, [page, search]);

  const loadComposers = async () => {
    setLoading(true);
    try {
      const result = await composerService.getAll(page, search);
      setData(result);
    } catch (error) {
      console.error('Error loading composers:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '2rem' }}>
        <h1>Composers</h1>
        <div style={{ marginTop: '1rem' }}>
          <input
            type="search"
            placeholder="Search composers..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            style={{
              width: '100%',
              maxWidth: '400px',
              padding: '0.5rem',
              fontSize: '1rem',
              borderRadius: '4px',
              border: '1px solid #ccc',
            }}
          />
        </div>
      </header>

      {loading ? (
        <p>Loading...</p>
      ) : data ? (
        <>
          <div style={{ display: 'grid', gap: '1rem' }}>
            {data.results.map((composer) => (
              <Link
                key={composer.id}
                to={`/composers/${composer.id}`}
                style={{ textDecoration: 'none', color: 'inherit' }}
              >
                <div style={{
                  padding: '1rem',
                  background: '#f5f5f5',
                  borderRadius: '8px',
                  cursor: 'pointer',
                }}>
                  <h3 style={{ margin: '0 0 0.5rem 0' }}>{composer.full_name}</h3>
                  <p style={{ margin: 0, color: '#666' }}>
                    {composer.birth_year || '?'} - {composer.death_year || (composer.is_living ? 'present' : '?')}
                    {composer.country && ` • ${composer.country.name}`}
                    {composer.period && ` • ${composer.period}`}
                  </p>
                  <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.9rem', color: '#888' }}>
                    {composer.work_count} works
                  </p>
                </div>
              </Link>
            ))}
          </div>

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
        </>
      ) : (
        <p>No composers found</p>
      )}

      <div style={{ marginTop: '2rem' }}>
        <Link to="/">← Back to Home</Link>
      </div>
    </div>
  );
}
