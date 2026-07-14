import type { WorkLink } from '../../../types';
import './ExternalLinks.css';

interface ExternalLinksProps {
  links?: WorkLink[] | null;
  // When set, renders a "Search on YouTube" link built from this query
  // (e.g. "<title> <composer>"). Independent of any stored link.
  youtubeSearchQuery?: string | null;
  // Selects the call-to-action label style, not the visual style — both
  // variants render the same button (see ExternalLinks.css).
  variant?: 'default' | 'detailed';
}

// Per-type call-to-action verb; falls back to the link's own label otherwise.
const DETAILED_CTA: Partial<Record<WorkLink['link_type'], string>> = {
  imslp: 'View on IMSLP',
  sheerpluck: 'View on SheerPluck',
  youtube: 'Watch on YouTube',
  score: 'View Score',
};

// A single button-styled external link. Stays an <a> (link semantics); the
// arrow is decorative (aria-hidden) and the accessible name notes the new tab.
function ExternalLinkButton({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="external-link-btn"
      aria-label={`${label} (opens in new tab)`}
    >
      <span className="external-link-btn__label">{label}</span>
      <span className="external-link-btn__arrow" aria-hidden="true">
        →
      </span>
    </a>
  );
}

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

  return (
    <div className="external-link-list">
      {items.map((link, index) => {
        const label =
          variant === 'detailed' ? DETAILED_CTA[link.link_type] ?? link.label : link.label;
        return (
          <ExternalLinkButton
            key={link.id ?? `${link.link_type}-${index}`}
            href={link.url}
            label={label}
          />
        );
      })}
      {youtubeSearchUrl && (
        <ExternalLinkButton href={youtubeSearchUrl} label="Search on YouTube" />
      )}
    </div>
  );
}
