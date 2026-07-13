import { useState, memo } from 'react';
import { Link } from 'react-router-dom';
import { ComposerListItem } from '../../../../types';
import SuggestionButton from '../../SuggestionButton';
import './ExpandableComposerRow.css';

// Minimal work type for composer's works list
interface ComposerWork {
  id: number;
  title: string;
  instrumentation_category: {
    id: number;
    name: string;
  } | null;
}

interface ExpandableComposerRowProps {
  composer: ComposerListItem;
  onLoadWorks: (composerId: number) => Promise<ComposerWork[]>;
}

function ExpandableComposerRow({ composer, onLoadWorks }: ExpandableComposerRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [works, setWorks] = useState<ComposerWork[]>([]);
  const [loadingWorks, setLoadingWorks] = useState(false);

  const handleToggle = async () => {
    // Prevent multiple clicks while loading
    if (loadingWorks) return;
    
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
        className={`composer-row ${composer.work_count > 0 ? '' : 'non-clickable'} ${loadingWorks ? 'loading' : ''}`}
        onClick={composer.work_count > 0 && !loadingWorks ? handleToggle : undefined}
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
          <span onClick={(e) => e.stopPropagation()}>
            <SuggestionButton itemType="composer" itemData={composer} />
          </span>
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
                      <Link to={`/works/${work.id}`} className="work-title">
                        {work.title}
                      </Link>
                      <span className="work-instrumentation">
                        {work.instrumentation_category?.name || '-'}
                      </span>
                      <SuggestionButton itemType="work" itemData={work} />
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

// Memoized so re-rendering the composer list (e.g. on every search keystroke) doesn't
// re-render all 50 rows. Relies on stable `composer` (from the query rows) and `onLoadWorks`.
export default memo(ExpandableComposerRow);
