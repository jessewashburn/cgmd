import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { composerService } from '../services';
import { Composer, Work } from '../types';
import '../styles/shared/DetailPage.css';

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

  if (loading) return <div className="loading-state">Loading...</div>;
  if (!composer) return <div className="error-state">Composer not found</div>;

  const birth = composer.birth_year || '?';
  const death = composer.death_year || (composer.is_living ? 'present' : '?');

  return (
    <div className="detail-page">
      <header className="detail-header">
        <h1>{composer.full_name}</h1>
        <p className="detail-subtitle">
          {birth} - {death}
        </p>
        
        <div className="detail-info-grid">
          {composer.country && (
            <>
              <span className="detail-info-label">Country:</span>
              <span className="detail-info-value">{composer.country.name}</span>
            </>
          )}
          {composer.period && (
            <>
              <span className="detail-info-label">Period:</span>
              <span className="detail-info-value">{composer.period}</span>
            </>
          )}
          <span className="detail-info-label">Works:</span>
          <span className="detail-info-value">{works.length}</span>
        </div>

        {composer.biography && (
          <div className="detail-biography">
            <p>{composer.biography}</p>
          </div>
        )}
      </header>

      <section className="detail-section">
        <h2>Works ({works.length})</h2>
        <div className="works-grid">
          {works.map((work) => (
            <Link
              key={work.id}
              to={`/works/${work.id}`}
              className="work-card"
            >
              <h3>{work.title}</h3>
              {work.catalog_number && (
                <p className="work-card-meta">
                  Catalog: {work.catalog_number}
                </p>
              )}
              {work.instrumentation_detail && (
                <p className="work-card-meta">
                  {work.instrumentation_detail}
                </p>
              )}
            </Link>
          ))}
        </div>
      </section>

      <Link to="/" className="back-link">← Back to Composers</Link>
    </div>
  );
}
