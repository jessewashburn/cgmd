import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { workService } from '../lib';
import { youtubeSearchQuery } from '../lib/composerName';
import { Work } from '../types';
import SuggestionButton from '../components/features/SuggestionButton';
import ExternalLinks from '../components/ui/ExternalLinks';
import './HomePage.css';

export default function HomePage() {
  const [highlightedWork, setHighlightedWork] = useState<Work | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    loadHighlightedWork();
  }, []);

  const loadHighlightedWork = async () => {
    setLoading(true);
    try {
      const work = await workService.getHighlighted();
      setHighlightedWork(work);
    } catch (error) {
      console.error('Error loading highlighted work:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page page--wide home-page">
      <section className="highlighted-work-section">
        <h2 className="section-title">Today's Highlighted Work</h2>
        <p className="section-description">
          Each day we highlight a randomly selected work from our collection.
        </p>
        {loading ? (
          <div className="highlighted-work-card loading">
            <p>Loading today's work...</p>
          </div>
        ) : highlightedWork ? (
          <div className="highlighted-work-card">
            <div className="work-header">
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <h3 className="work-title" style={{ flex: 1 }}>
                  <Link to={`/works/${highlightedWork.id}`} className="work-title-link">
                    {highlightedWork.title}
                  </Link>
                </h3>
                <SuggestionButton itemType="work" itemData={highlightedWork} />
              </div>
              <div className="work-composer">
                <span className="composer-by">by </span>
                {highlightedWork.composer ? (
                  <>
                    <Link to={`/composers/${highlightedWork.composer.id}`} className="composer-link">
                      {highlightedWork.composer.full_name}
                    </Link>
                    {(highlightedWork.composer.birth_year || highlightedWork.composer.death_year) && (
                      <span className="composer-dates">
                        {' '}({highlightedWork.composer.is_living || !highlightedWork.composer.death_year ? `b.${highlightedWork.composer.birth_year || '?'}` : `${highlightedWork.composer.birth_year || '?'}–${highlightedWork.composer.death_year}`})
                      </span>
                    )}
                  </>
                ) : (
                  <span>Unknown Composer</span>
                )}
              </div>
              {highlightedWork.composer && (
                <div className="composer-metadata">
                  {highlightedWork.composer.birth_year && (
                    <div className="composer-meta-item">
                      <span className="meta-label">Born</span>
                      <span className="meta-value">
                        {highlightedWork.composer.death_year
                          ? `${highlightedWork.composer.birth_year}–${highlightedWork.composer.death_year}`
                          : `b.${highlightedWork.composer.birth_year}`}
                      </span>
                    </div>
                  )}
                  {highlightedWork.composer.country_name && (
                    <div className="composer-meta-item">
                      <span className="meta-label">Country</span>
                      <span className="meta-value">{highlightedWork.composer.country_name}</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="work-metadata">
              {highlightedWork.instrumentation_detail && (
                <div className="metadata-item">
                  <span className="metadata-label">Instrumentation</span>
                  <span className="metadata-value">{highlightedWork.instrumentation_detail}</span>
                </div>
              )}
              {highlightedWork.catalog_number && (
                <div className="metadata-item">
                  <span className="metadata-label">Catalog Number</span>
                  <span className="metadata-value">{highlightedWork.catalog_number}</span>
                </div>
              )}
              {highlightedWork.duration_minutes && (
                <div className="metadata-item">
                  <span className="metadata-label">Duration</span>
                  <span className="metadata-value">{highlightedWork.duration_minutes} min</span>
                </div>
              )}
              {highlightedWork.movements && (
                <div className="metadata-item">
                  <span className="metadata-label">Movements</span>
                  <span className="metadata-value">{highlightedWork.movements}</span>
                </div>
              )}
            </div>

            {highlightedWork.tags && highlightedWork.tags.length > 0 && (
              <div className="work-tags">
                <strong>Tags:</strong>
                {(highlightedWork.tags as unknown as string[]).map((tag, index) => (
                  <span key={index} className="work-tag">
                    {tag}
                  </span>
                ))}
              </div>
            )}

            <ExternalLinks
              links={highlightedWork.links}
              youtubeSearchQuery={youtubeSearchQuery(highlightedWork.title, highlightedWork.composer?.full_name)}
              variant="default"
            />
          </div>
        ) : (
          <div className="highlighted-work-card error">
            <p>Could not load today's highlighted work</p>
          </div>
        )}
      </section>

      <section className="browse-section">
        <h2 className="section-title">Explore the Database</h2>
        <p className="section-description">
          Our database features tens of thousands of guitar composers and works, spanning centuries of music from around the world.
        </p>
        <div className="browse-cards">
          <Link to="/composers" className="browse-card">
            <h3>Browse Composers</h3>
          </Link>
          <Link to="/works" className="browse-card">
            <h3>Browse Works</h3>
          </Link>
        </div>
      </section>
    </div>
  );
}
