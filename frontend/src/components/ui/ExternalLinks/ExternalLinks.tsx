import type { WorkLink } from '../../../types';

interface ExternalLinksProps {
  links?: WorkLink[] | null;
  // When set, renders a "Search on YouTube" link built from this query
  // (e.g. "<title> <composer>"). Independent of any stored link.
  youtubeSearchQuery?: string | null;
  variant?: 'default' | 'detailed';
}

// Per-type call-to-action verb; falls back to the link's own label otherwise.
const DETAILED_CTA: Partial<Record<WorkLink['link_type'], string>> = {
  imslp: 'View on IMSLP',
  sheerpluck: 'View on SheerPluck',
  youtube: 'Watch on YouTube',
  score: 'View Score',
};

export default function ExternalLinks({
  links,
  youtubeSearchQuery,
  variant = 'default'
}: ExternalLinksProps) {
  const youtubeSearchUrl = youtubeSearchQuery
    ? `https://www.youtube.com/results?search_query=${encodeURIComponent(youtubeSearchQuery)}`
    : null;

  const items = links ?? [];
  const hasAnyLink = items.length > 0 || youtubeSearchUrl;

  if (!hasAnyLink) return null;

  const containerClass = variant === 'detailed' ? 'external-links' : 'work-links';
  const linkClass = variant === 'detailed' ? 'external-link' : 'work-link';

  return (
    <div className={containerClass}>
      {items.map((link, index) => {
        const label =
          variant === 'detailed' ? DETAILED_CTA[link.link_type] ?? link.label : link.label;
        return (
          <a
            key={link.id ?? `${link.link_type}-${index}`}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className={linkClass}
          >
            {label} →
          </a>
        );
      })}
      {youtubeSearchUrl && (
        <a
          href={youtubeSearchUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={linkClass}
        >
          Search on YouTube →
        </a>
      )}
    </div>
  );
}
