import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../test/server';
import { composerService } from './index';

/**
 * composerService.getWorks must return EVERY work, not the first page.
 *
 * It used to issue one unparameterised request and return `results` — 100 rows — while the
 * composer page rendered that as the complete list and as the total. 29 composers have more
 * than 100 works (Carulli 219, Kleynjans 210, Bach 168), so their pages silently hid the
 * remainder: Bach's Violin Partita No.2 (BWV 1004 — the Chaconne) sorts under "V", landed on
 * page 4, and was invisible.
 *
 * Uses the project's shared MSW server (src/test/setup.ts already listens/resets it) —
 * standing up a second setupServer here fights it.
 */

let requestedPages: string[] = [];

// 50 per page — what the endpoint actually serves; it ignores ?page_size.
const pageOf = (n: number, total: number, size = 50) => {
  const start = (n - 1) * size;
  const results = Array.from({ length: Math.max(0, Math.min(size, total - start)) }, (_, i) => ({
    id: start + i + 1,
    title: `Work ${start + i + 1}`,
  }));
  return {
    count: total,
    // Absolute and http:// on purpose — that is what the API really returns, and an
    // https:// page would refuse to follow it as mixed content.
    next:
      start + results.length < total
        ? `http://api.solmuapp.com/api/composers/1/works/?page=${n + 1}`
        : null,
    previous: null,
    results,
  };
};

const serveTotal = (total: number) =>
  server.use(
    http.get('*/api/composers/:id/works/', ({ request }) => {
      const page = new URL(request.url).searchParams.get('page') ?? '1';
      requestedPages.push(page);
      return HttpResponse.json(pageOf(Number(page), total));
    }),
  );

beforeEach(() => {
  requestedPages = [];
});

describe('composerService.getWorks', () => {
  it('returns every work across pages, not just the first', async () => {
    serveTotal(168); // Bach
    const works = await composerService.getWorks(1);
    expect(works).toHaveLength(168);
    // Not .at(-1): this project's tsconfig lib predates ES2022, so it typechecks in
    // vitest but breaks `npm run build`.
    expect(works[works.length - 1]).toMatchObject({ title: 'Work 168' });
  });

  it('follows pagination by page number, not the absolute `next` url', async () => {
    serveTotal(168);
    await composerService.getWorks(1);
    // Bach: 50+50+50+18. BWV 1004 sorts under "V" and is on that last page — the one the
    // old single-request version never asked for.
    expect(requestedPages).toEqual(['1', '2', '3', '4']);
  });

  it('stops when a single page covers the composer', async () => {
    serveTotal(12);
    const works = await composerService.getWorks(1);
    expect(works).toHaveLength(12);
    expect(requestedPages).toEqual(['1']); // no pointless second request
  });
});
