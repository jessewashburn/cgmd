import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { workService } from '../services';
import { Work } from '../types';

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

  if (loading) return <div style={{ padding: '2rem' }}>Loading...</div>;
  if (!work) return <div style={{ padding: '2rem' }}>Work not found</div>;

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '2rem' }}>
        <h1>{work.title}</h1>
        <p style={{ fontSize: '1.2rem' }}>
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

      <section>
        <h2>Details</h2>
        <dl style={{ lineHeight: '2' }}>
          {work.catalog_number && (
            <>
              <dt style={{ fontWeight: 'bold' }}>Catalog Number:</dt>
              <dd>{work.catalog_number}</dd>
            </>
          )}
          {work.year_composed && (
            <>
              <dt style={{ fontWeight: 'bold' }}>Year Composed:</dt>
              <dd>{work.year_composed}</dd>
            </>
          )}
          {work.instrumentation_detail && (
            <>
              <dt style={{ fontWeight: 'bold' }}>Instrumentation:</dt>
              <dd>{work.instrumentation_detail}</dd>
            </>
          )}
          {work.duration_minutes && (
            <>
              <dt style={{ fontWeight: 'bold' }}>Duration:</dt>
              <dd>{work.duration_minutes} minutes</dd>
            </>
          )}
          {work.difficulty_level && (
            <>
              <dt style={{ fontWeight: 'bold' }}>Difficulty:</dt>
              <dd>{work.difficulty_level}/10</dd>
            </>
          )}
          {work.movements && (
            <>
              <dt style={{ fontWeight: 'bold' }}>Movements:</dt>
              <dd>{work.movements}</dd>
            </>
          )}
        </dl>

        {work.tags && work.tags.length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            <strong>Tags: </strong>
            {work.tags.map((tag) => (
              <span
                key={tag.id}
                style={{
                  display: 'inline-block',
                  padding: '0.25rem 0.75rem',
                  margin: '0.25rem',
                  background: '#e0e0e0',
                  borderRadius: '12px',
                  fontSize: '0.9rem',
                }}
              >
                {tag.name}
              </span>
            ))}
          </div>
        )}
      </section>

      <div style={{ marginTop: '2rem' }}>
        {work.composer && (
          <Link to={`/composers/${work.composer.id}`}>← Back to Composer</Link>
        )}
      </div>
    </div>
  );
}
