import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { workService } from '../services';
import { Work } from '../types';
import '../styles/shared/DetailPage.css';

export default function WorkDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [work, setWork] = useState<Work | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWork();
  }, [id]);

  const loadWork = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await workService.getById(parseInt(id));
      setWork(data);
    } catch (error) {
      console.error('Error loading work:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading-state">Loading...</div>;
  if (!work) return <div className="error-state">Work not found</div>;

  return (
    <div className="detail-page">
      <header className="detail-header">
        <h1>{work.title}</h1>
        <p className="detail-subtitle">
          by{' '}
          {work.composer ? (
            <Link to={`/composers/${work.composer.id}`}>
              {work.composer.full_name}
            </Link>
          ) : (
            <span>Unknown Composer</span>
          )}
        </p>
      </header>

      <section className="detail-section">
        <h2>Details</h2>
        <dl className="detail-list">
          {work.catalog_number && (
            <>
              <dt>Catalog Number:</dt>
              <dd>{work.catalog_number}</dd>
            </>
          )}
          {work.year_composed && (
            <>
              <dt>Year Composed:</dt>
              <dd>{work.year_composed}</dd>
            </>
          )}
          {work.instrumentation_detail && (
            <>
              <dt>Instrumentation:</dt>
              <dd>{work.instrumentation_detail}</dd>
            </>
          )}
          {work.duration_minutes && (
            <>
              <dt>Duration:</dt>
              <dd>{work.duration_minutes} minutes</dd>
            </>
          )}
          {work.difficulty_level && (
            <>
              <dt>Difficulty:</dt>
              <dd>{work.difficulty_level}/10</dd>
            </>
          )}
          {work.movements && (
            <>
              <dt>Movements:</dt>
              <dd>{work.movements}</dd>
            </>
          )}
        </dl>

        {work.tags && work.tags.length > 0 && (
          <div className="detail-tags">
            <strong>Tags:</strong>
            {work.tags.map((tag) => (
              <span key={tag.id} className="detail-tag">
                {tag.name}
              </span>
            ))}
          </div>
        )}
      </section>

      {work.composer && (
        <Link to={`/composers/${work.composer.id}`} className="back-link">
          ← Back to Composer
        </Link>
      )}
    </div>
  );
}
