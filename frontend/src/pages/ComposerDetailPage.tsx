import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { composerService } from '../services';
import { Composer, Work } from '../types';

export default function ComposerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [composer, setComposer] = useState<Composer | null>(null);
  const [works, setWorks] = useState<Work[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadComposer();
  }, [id]);

  const loadComposer = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [composerData, worksData] = await Promise.all([
        composerService.getById(parseInt(id)),
        composerService.getWorks(parseInt(id)),
      ]);
      setComposer(composerData);
      setWorks(worksData);
    } catch (error) {
      console.error('Error loading composer:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div style={{ padding: '2rem' }}>Loading...</div>;
  if (!composer) return <div style={{ padding: '2rem' }}>Composer not found</div>;

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '2rem' }}>
        <h1>{composer.full_name}</h1>
        <p style={{ fontSize: '1.2rem', color: '#666' }}>
          {composer.birth_year || '?'} - {composer.death_year || (composer.is_living ? 'present' : '?')}
        </p>
        {composer.country && <p>Country: {composer.country.name}</p>}
        {composer.period && <p>Period: {composer.period}</p>}
        {composer.biography && (
          <div style={{ marginTop: '1rem', lineHeight: '1.6' }}>
            <p>{composer.biography}</p>
          </div>
        )}
      </header>

      <section>
        <h2>Works ({works.length})</h2>
        <div style={{ display: 'grid', gap: '1rem', marginTop: '1rem' }}>
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
                {work.catalog_number && (
                  <p style={{ margin: '0.25rem 0', color: '#666' }}>
                    Catalog: {work.catalog_number}
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

      <div style={{ marginTop: '2rem' }}>
        <Link to="/composers">← Back to Composers</Link>
      </div>
    </div>
  );
}
