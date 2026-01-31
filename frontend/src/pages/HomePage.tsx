import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { workService, composerService } from '../lib';
import { Work, Composer } from '../types';
import './HomePage.css';

// Generate a random work ID based on today's date
const getDailyWorkId = (totalWorks: number): number => {
  const today = new Date();
  const seed = today.getFullYear() * 10000 + (today.getMonth() + 1) * 100 + today.getDate();
  // Use date as seed for consistent random selection per day
  const random = Math.sin(seed) * 10000;
  const normalized = random - Math.floor(random);
  return Math.floor(normalized * totalWorks) + 1;
};

export default function HomePage() {
  const [highlightedWork, setHighlightedWork] = useState<Work | null>(null);
  const [composer, setComposer] = useState<Composer | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHighlightedWork();
  }, []);

  const loadHighlightedWork = async () => {
    setLoading(true);
    try {
      // Get total count first
      const response = await workService.getAll(1, '');
      const totalWorks = response.count;
      
      // Get today's work ID
      const workId = getDailyWorkId(totalWorks);
      
      // Fetch the highlighted work
      const work = await workService.getById(workId);
      setHighlightedWork(work);
      
      // Fetch full composer details if available
      if (work.composer) {
        const composerData = await composerService.getById(work.composer.id);
        setComposer(composerData);
      }
    } catch (error) {
      console.error('Error loading highlighted work:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="home-page">
      <section className="highlighted-work-section">
        <h2 className="section-title">Today's Highlighted Work</h2>
        {loading ? (
          <div className="highlighted-work-card loading">
            <p>Loading today's work...</p>
          </div>
        ) : highlightedWork ? (
          <div className="highlighted-work-card">
            <div className="work-header">
              <h3 className="work-title">
                <Link to={`/works/${highlightedWork.id}`} className="work-title-link">
                  {highlightedWork.title}
                </Link>
              </h3>
              <p className="work-composer">
                by{' '}
                {highlightedWork.composer ? (
                  <Link to={`/composers/${highlightedWork.composer.id}`} className="composer-link">
                    {highlightedWork.composer.full_name}
                  </Link>
                ) : (
                  <span>Unknown Composer</span>
                )}
              </p>
              {composer && (
                <div className="composer-info">
                  <span className="composer-dates">
                    {composer.birth_year && composer.death_year ? (
                      `${composer.birth_year}–${composer.death_year}`
                    ) : composer.birth_year && composer.is_living ? (
                      `b. ${composer.birth_year}`
                    ) : composer.birth_year ? (
                      composer.birth_year
                    ) : null}
                  </span>
                  {composer.country && (
                    <span className="composer-nationality">{composer.country.name}</span>
                  )}
                </div>
              )}
            </div>

            <dl className="work-details">
              {highlightedWork.catalog_number && (
                <>
                  <dt>Catalog Number:</dt>
                  <dd>{highlightedWork.catalog_number}</dd>
                </>
              )}
              {highlightedWork.instrumentation_detail && (
                <>
                  <dt>Instrumentation:</dt>
                  <dd>{highlightedWork.instrumentation_detail}</dd>
                </>
              )}
              {highlightedWork.duration_minutes && (
                <>
                  <dt>Duration:</dt>
                  <dd>{highlightedWork.duration_minutes} minutes</dd>
                </>
              )}
              {highlightedWork.movements && (
                <>
                  <dt>Movements:</dt>
                  <dd>{highlightedWork.movements}</dd>
                </>
              )}
            </dl>

            {highlightedWork.tags && highlightedWork.tags.length > 0 && (
              <div className="work-tags">
                <strong>Tags:</strong>
                {highlightedWork.tags.map((tag) => (
                  <span key={tag.id} className="work-tag">
                    {tag.name}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="highlighted-work-card error">
            <p>Could not load today's highlighted work</p>
          </div>
        )}
      </section>

      <section className="browse-section">
        <h2 className="section-title">Explore the Database</h2>
        <div className="browse-cards">
          <Link to="/composers" className="browse-card">
            <h3>Browse All Composers</h3>
            <p>Explore our complete collection of classical guitar composers</p>
          </Link>
          <Link to="/works" className="browse-card">
            <h3>Browse All Works</h3>
            <p>Discover thousands of guitar works from across history</p>
          </Link>
        </div>
      </section>
    </div>
  );
}
