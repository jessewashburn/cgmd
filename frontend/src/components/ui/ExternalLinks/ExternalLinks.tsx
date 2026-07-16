import type { WorkLink } from '../../../types';
import './ExternalLinks.css';

interface ExternalLinksProps {
  links?: WorkLink[] | null;
  // When set, renders a "Search on YouTube" link built from this query
  // (e.g. "<title> <composer>"). Independent of any stored link.
  youtubeSearchQuery?: string | null;
  // 'detailed' additionally shows each link's source under its label. Labels themselves
  // are server-derived and identical in both variants.
  variant?: 'default' | 'detailed';
}

// A single button-styled external link. Stays an <a> (link semantics); the
// accessible name notes that it opens a new tab.
//
// `source` renders as a subtitle under the verb. It has to: labels are derived from the
// host, so a work with two free score links shows "View Score" twice, and the source is
// the only thing distinguishing them. It joins the accessible name for the same reason.
function ExternalLinkButton({
  href,
  label,
  source,
}: {
  href: string;
  label: string;
  source?: string | null;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="external-link-btn"
      aria-label={`${label}${source ? ` on ${source}` : ''} (opens in new tab)`}
    >
      <span className="external-link-label">{label}</span>
      {source && <span className="external-link-source">{source}</span>}
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
      {items.map((link, index) => (
        <ExternalLinkButton
          key={link.id ?? `${link.link_type}-${index}`}
          href={link.url}
          label={link.label}
          // The compact homepage listing shows the verb only; the work page has room
          // to disambiguate two same-verb links.
          source={variant === 'detailed' ? link.source : null}
        />
      ))}
      {youtubeSearchUrl && (
        <ExternalLinkButton href={youtubeSearchUrl} label="Search on YouTube" />
      )}
    </div>
  );
}
