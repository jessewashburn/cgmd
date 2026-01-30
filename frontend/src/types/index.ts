export interface Composer {
  id: number;
  full_name: string;
  first_name: string;
  last_name: string;
  birth_year: number | null;
  death_year: number | null;
  is_living: boolean;
  period: string;
  country: Country | null;
  biography: string;
  work_count: number;
  created_at: string;
  updated_at: string;
}

export interface Work {
  id: number;
  composer: {
    id: number;
    full_name: string;
  } | null;
  title: string;
  catalog_number: string | null;
  year_composed: number | null;
  instrumentation_category: InstrumentationCategory | null;
  instrumentation_detail: string;
  duration_minutes: number | null;
  difficulty_level: number | null;
  movements: number | null;
  tags: Tag[];
  created_at: string;
  updated_at: string;
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
