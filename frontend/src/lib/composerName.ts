// Composer `full_name` arrives in two shapes: the Sheerpluck import format
// "Last, First" (e.g. "Poser, Hans") and plain "First Last". YouTube uploads
// title works the natural way, so flip on the first comma for the search query
// only — the page still displays whatever is stored. Matches
// parse_composer_name() in music/utils.py; the pattern needs text on both sides
// of the comma, so natural-order names and mononyms fall through untouched.
export function youtubeSearchQuery(
  title?: string | null,
  composerFullName?: string | null
): string {
  const parts = composerFullName?.trim().match(/^([^,]+),\s*(.+)$/);
  const composer = parts ? `${parts[2]} ${parts[1]}` : composerFullName;
  return [title, composer].filter(Boolean).join(' ');
}
