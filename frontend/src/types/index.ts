export interface Composer {
  id: number;
  full_name: string;
  first_name: string;
  last_name: string;
  birth_year: number | null;
  death_year: number | null;
  is_living: boolean;
  period: string | null;
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
