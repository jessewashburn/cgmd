import { useState } from 'react';
import { Link } from 'react-router-dom';

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
        style={{
          borderBottom: '1px solid #eee',
          cursor: composer.work_count > 0 ? 'pointer' : 'default',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = '#f9f9f9')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'white')}
        onClick={composer.work_count > 0 ? handleToggle : undefined}
      >
        <td style={{ padding: '1rem', color: '#666' }}>
          {composer.work_count > 0 && (
            <span style={{ marginRight: '0.5rem', fontSize: '0.8rem' }}>
              {isExpanded ? '▼' : '▶'}
            </span>
          )}
          <Link
            to={`/composers/${composer.id}`}
            style={{ textDecoration: 'none', color: '#1976d2', fontWeight: '500' }}
            onClick={(e) => e.stopPropagation()}
          >
            {composer.full_name}
          </Link>
        </td>
        <td style={{ padding: '1rem', textAlign: 'left', color: '#666' }}>
          {composer.period || '-'}
        </td>
        <td style={{ padding: '1rem', textAlign: 'left', color: '#666' }}>
          {composer.country_name || '-'}
        </td>
        <td style={{ padding: '1rem', textAlign: 'center', color: '#666' }}>
          {birth} - {death}
        </td>
        <td style={{ padding: '1rem', textAlign: 'center', color: '#666' }}>
          {composer.work_count}
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={5} style={{ padding: 0, background: '#f9f9f9' }}>
            <div style={{ padding: '1rem 2rem' }}>
              {loadingWorks ? (
                <p style={{ color: '#666', fontStyle: 'italic' }}>Loading works...</p>
              ) : works.length > 0 ? (
                <div style={{ display: 'grid', gap: '0.5rem' }}>
                  {works.map((work) => (
                    <div
                      key={work.id}
                      style={{
                        padding: '0.5rem',
                        background: 'white',
                        borderRadius: '4px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <Link
                        to={`/works/${work.id}`}
                        style={{ textDecoration: 'none', color: '#1976d2' }}
                      >
                        {work.title}
                      </Link>
                      <span style={{ fontSize: '0.9rem', color: '#666' }}>
                        {work.instrumentation_category?.name || '-'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: '#666', fontStyle: 'italic' }}>No works found</p>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
