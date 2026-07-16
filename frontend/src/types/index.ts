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
export interface WorkLink {
  id: number | null;
  label: string;
  url: string;
  link_type:
    | 'imslp'
    | 'sheerpluck'
    | 'youtube'
    | 'score'
    | 'publisher'
    | 'recording'
    | 'commission'
    | 'other';
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
  /** As the API serves them (objects), or as names once normalized for editing. */
  alternate_instrumentations?: Array<string | { name: string }>;
  /** Structurally DraftLink (see LinkListEditor); spelled out so this module
   *  stays free of component imports. `WorkLink[]` satisfies it. */
  links?: Array<Pick<WorkLink, 'label' | 'url'> & { link_type?: string }>;
}
