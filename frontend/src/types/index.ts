export interface Composer {
  id: number;
  full_name: string;
  first_name: string;
  last_name: string;
  birth_year: number | null;
  death_year: number | null;
  is_living: boolean;
  period: string | null;
  /** Era labels, chronological. Derived from birth/death years, so a composer can
   *  hold several ("Romantic", "Modern") and an undated one holds none. */
  eras: string[];
  country: Country | null;
  biography: string;
  work_count: number;
  created_at: string;
  updated_at: string;
}

// Lightweight type for composer lists (matches ComposerListSerializer)
export interface ComposerListItem {
  id: number;
  full_name: string;
  birth_year: number | null;
  death_year: number | null;
  is_living: boolean;
  period: string | null;
  eras: string[];
  country_name: string | null;
  work_count: number;
}

export interface Work {
  id: number;
  composer: {
    id: number;
    full_name: string;
    birth_year: number | null;
    death_year: number | null;
    is_living: boolean;
    country_name?: string | null;
  } | null;
  title: string;
  catalog_number: string | null;
  composition_year: number | null;
  instrumentation_category: InstrumentationCategory | null;
  instrumentation_detail: string;
  /** Other ways the work can be played, beyond its notated instrumentation.
   *  Detail view only — the Works table's column means the primary. */
  alternate_instrumentations: Array<{ id: number; name: string; note: string }>;
  /** Arranged for guitar rather than written for it. See WorkListItem.is_arrangement. */
  is_arrangement: boolean;
  duration_minutes: number | null;
  difficulty_level: number | null;
  movements: number | null;
  imslp_url: string | null;
  sheerpluck_url: string | null;
  youtube_url: string | null;
  score_url: string | null;
  links: WorkLink[];
  tags: Tag[];
  created_at: string;
  updated_at: string;
}

// A bespoke external link on a work. `id` is null for links synthesized from
// the legacy fixed URL columns (imslp/sheerpluck/youtube/score).
//
// `label` is DERIVED SERVER-SIDE from the link's host (see music/publishers.py) — free
// score sources get "View Score", paid ones "Buy Score". Render it as-is; don't remap it
// client-side or the two will drift.
export interface WorkLink {
  id: number | null;
  label: string;
  url: string;
  link_type:
    | 'imslp'
    | 'sheerpluck'
    | 'youtube'
    | 'score'      // a free score source
    | 'purchase'   // a paid one
    | 'publisher'
    | 'recording'
    | 'commission'
    | 'other';
  // Which source this came from ("IMSLP", "Bärenreiter"). Null when the host isn't a
  // recognised source. Necessary, not decorative: a work with an IMSLP *and* a Mutopia
  // score renders two buttons both reading "View Score", and this is what tells them
  // apart.
  source: string | null;
  sort_order: number;
}

// Lightweight type for work lists (matches WorkListSerializer)
export interface WorkListItem {
  id: number;
  title: string;
  composer: {
    id: number;
    full_name: string;
  } | null;
  catalog_number: string | null;
  composition_year: number | null;
  instrumentation_category: {
    id: number;
    name: string;
  } | null;
  instrumentation_detail: string;
  duration_minutes: number | null;
  difficulty_level: number | null;
  // Arranged for guitar rather than written for it. The list renders a badge from this:
  // an arrangement row carries the *original* work's title, so without the badge
  // "Violin Partita No.2" just looks misfiled.
  is_arrangement: boolean;
}

export interface Country {
  id: number;
  name: string;
  code: string | null;
}

export interface InstrumentationCategory {
  id: number;
  name: string;
}

export interface Tag {
  id: number;
  name: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * A composer or work record the suggestion form can be opened on.
 *
 * Every field is optional because callers pass whatever shape they already hold:
 * full `Composer` / `Work` records from the detail pages, and the lighter rows
 * list views carry (`ComposerListItem`, a composer's works). The modal re-fetches
 * the canonical work before editing one, so the fields here are what it can rely
 * on being *possibly* present — not a promise that any of them are.
 *
 * Number-ish fields also admit `string`: they are bound to <input> elements,
 * which hand back raw strings that go to the API as typed.
 */
export interface SuggestionTarget {
  id?: number;
  // Composer fields
  full_name?: string;
  birth_year?: number | string | null;
  death_year?: number | string | null;
  country_name?: string | null;
  // Work fields
  title?: string;
  composer?: { full_name?: string } | null;
  instrumentation_detail?: string;
  composition_year?: number | string | null;
  instrumentation_category?: { name?: string } | null;
  /** Arranged for guitar rather than written for it. Submitting it only *suggests* the
   *  tag — it lands as `arrangement_basis='suggested'` when an admin applies the
   *  suggestion, never straight from the public form. */
  is_arrangement?: boolean;
  /** As the API serves them (objects), or as names once normalized for editing. */
  alternate_instrumentations?: Array<string | { name: string }>;
  /** Structurally DraftLink (see LinkListEditor); spelled out so this module
   *  stays free of component imports. `WorkLink[]` satisfies it. */
  links?: Array<Pick<WorkLink, 'label' | 'url'> & { link_type?: string }>;
}
