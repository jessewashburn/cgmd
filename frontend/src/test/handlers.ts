import { http, HttpResponse } from 'msw';

/** Every intercepted list request URL, in order. Reset with `resetRequestLog()`. */
export const requestUrls: string[] = [];

export function resetRequestLog() {
  requestUrls.length = 0;
}

/** The most recent list request URL (or undefined). */
export function lastRequestUrl(): string | undefined {
  return requestUrls[requestUrls.length - 1];
}

// A row shaped to satisfy both WorkListItem and ComposerListItem consumers.
const sampleRow = {
  id: 1,
  title: 'Row One',
  full_name: 'Row One',
  composer: { id: 1, full_name: 'A Composer' },
  catalog_number: null,
  composition_year: null,
  instrumentation_category: null,
  instrumentation_detail: '',
  duration_minutes: null,
  difficulty_level: null,
  birth_year: 1850,
  death_year: null,
  is_living: false,
  country_name: 'Spain',
  period: null,
  work_count: 1,
};

function listResolver({ request }: { request: Request }) {
  requestUrls.push(request.url);
  return HttpResponse.json({ count: 1, next: null, previous: null, results: [sampleRow] });
}

export const handlers = [
  http.get('*/api/works/', listResolver),
  http.get('*/api/composers/', listResolver),
  http.get('*/api/instrumentations/', () =>
    HttpResponse.json({ count: 1, next: null, previous: null, results: [{ id: 1, name: 'Guitar solo' }] }),
  ),
  http.get('*/api/countries/', () =>
    HttpResponse.json({ count: 1, next: null, previous: null, results: [{ id: 1, name: 'Spain' }] }),
  ),
  http.get('*/api/stats/summary/', () =>
    HttpResponse.json({ total_composers: 15082, total_works: 73111 }),
  ),
];
