import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { composerService } from '../lib';
import { Composer, Work } from '../types';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorMessage from '../components/ui/ErrorMessage';
import MetadataList from '../components/ui/MetadataList';
import SuggestionButton from '../components/features/SuggestionButton';
import '../styles/shared/DetailPage.css';

export default function ComposerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [composer, setComposer] = useState<Composer | null>(null);
  const [works, setWorks] = useState<Work[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadComposer();
  }, [id]);

  const loadComposer = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [composerData, worksData] = await Promise.all([
        composerService.getById(parseInt(id)),
        composerService.getWorks(parseInt(id)),
      ]);
      setComposer(composerData);
      setWorks(Array.isArray(worksData) ? worksData : []);
    } catch (error) {
      console.error('Error loading composer:', error);
      setError('Failed to load composer details. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage title="Error Loading Composer" message={error} />;
  if (!composer) return <ErrorMessage title="Composer Not Found" message="The requested composer could not be found." />;

  const hasDates = composer.birth_year || composer.death_year || composer.is_living;
  const dateDisplay = composer.is_living || !composer.death_year 
    ? `b.${composer.birth_year || '?'}`
    : `${composer.birth_year || '?'} – ${composer.death_year}`;

  const metadataItems = [
    composer.country && { label: 'Country', value: composer.country.name },
    composer.period && { label: 'Period', value: composer.period },
    { label: 'Works', value: works.length },
  ].filter(Boolean) as Array<{ label: string; value: string | number }>;

  return (
    <div className="page page--wide">
      <Link to="/composers" className="back-link">← Back to Composers</Link>
      
      <header className="detail-header">
        <div className="detail-title-row">
          <h1>{composer.full_name}</h1>
          <SuggestionButton itemType="composer" itemData={composer} />
        </div>
        {hasDates && (
          <p className="detail-subtitle">
            {dateDisplay}
          </p>
        )}
        
        <MetadataList items={metadataItems} />

        {composer.biography && (
          <div className="detail-biography">
            <p>{composer.biography}</p>
          </div>
        )}
      </header>

      <section className="detail-section">
        <h2>Works ({works.length})</h2>
        {works.length > 0 ? (
          <div className="works-grid card-grid">
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
        ) : (
          <p className="empty-state">No works found for this composer.</p>
        )}
      </section>
    </div>
  );
}
