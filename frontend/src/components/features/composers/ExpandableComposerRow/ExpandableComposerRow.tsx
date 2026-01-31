import { useState } from 'react';
import { Link } from 'react-router-dom';
import './ExpandableComposerRow.css';

interface Work {
  id: number;
  title: string;
  instrumentation_category: {
    id: number;
    name: string;
  } | null;
}

interface Composer {
  id: number;
  full_name: string;
  birth_year: number | null;
  death_year: number | null;
  is_living: boolean;
  period: string | null;
  country_name: string | null;
  work_count: number;
}

interface ExpandableComposerRowProps {
  composer: Composer;
  onLoadWorks: (composerId: number) => Promise<Work[]>;
}

export default function ExpandableComposerRow({ composer, onLoadWorks }: ExpandableComposerRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [works, setWorks] = useState<Work[]>([]);
  const [loadingWorks, setLoadingWorks] = useState(false);

  const handleToggle = async () => {
    if (!isExpanded && works.length === 0) {
      setLoadingWorks(true);
      try {
        const loadedWorks = await onLoadWorks(composer.id);
        setWorks(loadedWorks);
      } catch (error) {
        console.error('Error loading works:', error);
      } finally {
        setLoadingWorks(false);
      }
    }
    setIsExpanded(!isExpanded);
  };

  const birth = composer.birth_year || '?';
  const death = composer.death_year || (composer.is_living ? 'present' : '?');

  return (
    <>
      <tr
        className={`composer-row ${composer.work_count > 0 ? '' : 'non-clickable'}`}
        onClick={composer.work_count > 0 ? handleToggle : undefined}
      >
        <td>
          {composer.work_count > 0 && (
            <span className="expand-icon">
              {isExpanded ? '▼' : '▶'}
            </span>
          )}
          <Link
            to={`/composers/${composer.id}`}
            className="composer-name-link"
            onClick={(e) => e.stopPropagation()}
          >
            {composer.full_name}
          </Link>
        </td>
        <td className="align-left">
          {composer.country_name || '-'}
        </td>
        <td className="align-center">
          {birth} - {death}
        </td>
        <td className="align-center">
          {composer.work_count}
        </td>
      </tr>
      {isExpanded && (
        <tr className="expanded-works-row">
          <td colSpan={4}>
            <div className="expanded-works-content">
              {loadingWorks ? (
                <p className="loading-works">Loading works...</p>
              ) : works.length > 0 ? (
                <div className="works-list">
                  {works.map((work) => (
                    <div key={work.id} className="work-item">
                      <Link to={`/works/${work.id}`} className="work-link">
                        {work.title}
                      </Link>
                      <span className="work-instrumentation">
                        {work.instrumentation_category?.name || '-'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="no-works">No works found</p>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
